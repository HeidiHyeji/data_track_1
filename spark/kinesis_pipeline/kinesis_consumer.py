#!/usr/bin/env python3
"""
FMS Kinesis Consumer (멀티 샤드 실시간 S3 업로드)
모든 샤드에서 데이터를 병렬로 수신하여 S3에 업로드
"""
import json
import os
import tempfile
import subprocess
import time
import threading
from datetime import datetime
import boto3
import logging

# 설정
STREAM_NAME = "fms-sensor-data-kinesis"
REGION_NAME = "ap-northeast-1"
S3_BUCKET = "awsprelab1"
S3_PREFIX = "fms/raw-data/"
S3_URI = f"s3://{S3_BUCKET}/{S3_PREFIX}"
UPLOAD_BATCH_SIZE = 10  # 이 수 만큼 모이면 바로 S3 업로드

# 로깅
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ShardConsumer(threading.Thread):
    def __init__(self, shard_id, kinesis_client):
        super().__init__()
        self.shard_id = shard_id
        self.kinesis = kinesis_client
        self.buffer = []

    def write_buffer_to_s3(self):
        if not self.buffer:
            return

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"sensor-data-shard-{self.shard_id}-{timestamp_str}.json"
        s3_path = os.path.join(S3_URI, filename)

        try:
            with tempfile.NamedTemporaryFile('w', delete=False) as tmp:
                for record in self.buffer:
                    tmp.write(json.dumps(record) + '\n')
                tmp_path = tmp.name

            subprocess.run(
                ["aws", "s3", "cp", tmp_path, s3_path],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            logger.info(f"📤 [{self.shard_id}] S3 업로드 완료: {s3_path}")
        except subprocess.CalledProcessError as e:
            logger.error(f"[{self.shard_id}] S3 업로드 실패: {e.stderr.strip()}")
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass
            self.buffer.clear()

    def process_records(self, records):
        for record in records:
            try:
                payload = record["Data"].decode("utf-8")
                logger.info(f"[{self.shard_id}] [RAW] {payload}")
                data = json.loads(payload)
                self.buffer.append(data)
                if len(self.buffer) >= UPLOAD_BATCH_SIZE:
                    self.write_buffer_to_s3()
            except Exception as e:
                logger.error(f"[{self.shard_id}] 레코드 처리 오류: {e}")

    def run(self):
        try:
            shard_iterator = self.kinesis.get_shard_iterator(
                StreamName=STREAM_NAME,
                ShardId=self.shard_id,
                ShardIteratorType="LATEST"
            )["ShardIterator"]

            while True:
                response = self.kinesis.get_records(
                    ShardIterator=shard_iterator,
                    Limit=100
                )
                records = response["Records"]
                shard_iterator = response["NextShardIterator"]

                self.process_records(records)

                time.sleep(0.5)
        except Exception as e:
            logger.error(f"[{self.shard_id}] 소비 중 예외 발생: {e}")
        finally:
            self.write_buffer_to_s3()
            logger.info(f"[{self.shard_id}] ✅ ShardConsumer 종료")

class FMSKinesisMultiShardConsumer:
    def __init__(self):
        self.kinesis = boto3.client("kinesis", region_name=REGION_NAME)

    def run(self):
        logger.info("🚀 FMS Kinesis Consumer 시작 (모든 샤드 대상)")
        shards = self.kinesis.describe_stream(StreamName=STREAM_NAME)["StreamDescription"]["Shards"]

        threads = []
        for shard in shards:
            shard_id = shard["ShardId"]
            consumer = ShardConsumer(shard_id, self.kinesis)
            consumer.start()
            threads.append(consumer)

        # 모든 쓰레드가 종료될 때까지 대기
        for t in threads:
            t.join()

if __name__ == "__main__":
    consumer = FMSKinesisMultiShardConsumer()
    consumer.run()
