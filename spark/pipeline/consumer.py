#!/usr/bin/env python3
"""
FMS Consumer for Real Data Processing
Kafka로부터 FMS 센서 데이터를 수신하고, 30초마다 파일을 저장하여 S3에 업로드 (파일명은 타임스탬프 기반)
"""
import json
import os
import tempfile
import subprocess
import time
from datetime import datetime
from confluent_kafka import Consumer, KafkaError
import logging

# Kafka 설정
BROKER = "s1:9092,s2:9092,s3:9092,i1:9092"
TOPIC = "fms-sensor-data"
GROUP_ID = "fms-data-processor"

# S3 경로 설정
S3_BUCKET = "awsprelab1"
S3_PREFIX = "fms/raw-data/"
S3_URI = f"s3://{S3_BUCKET}/{S3_PREFIX}"

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FMSDataConsumer:
    def __init__(self):
        self.consumer = Consumer({
            'bootstrap.servers': BROKER,
            'group.id': GROUP_ID,
            'auto.offset.reset': 'earliest'
        })
        self.buffer = []
        self.last_flush_time = time.time()

    def write_buffer_to_s3(self):
        """버퍼 내용을 타임스탬프 파일로 S3에 저장"""
        if not self.buffer:
            return

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sensor-data-{timestamp_str}.json"
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
            logger.info(f"📤 S3 업로드 완료: {s3_path}")
        except subprocess.CalledProcessError as e:
            logger.error(f"S3 업로드 실패: {e.stderr.strip()}")
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass
            self.buffer.clear()
            self.last_flush_time = time.time()

    def process_message(self, msg):
        try:
            raw_value = msg.value().decode('utf-8')
            logger.info(f"[RAW INPUT] {raw_value}")
            data = json.loads(raw_value)
            self.buffer.append(data)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 오류: {e}")
        except Exception as e:
            logger.error(f"메시지 처리 오류: {e}")

    def run(self):
        logger.info("FMS Data Consumer 시작... (S3 업로드 모드)")
        logger.info(f"구독 토픽: {TOPIC}")

        self.consumer.subscribe([TOPIC])

        try:
            while True:
                msg = self.consumer.poll(1.0)

                if msg is None:
                    continue
                elif msg.error():
                    if msg.error().code() != KafkaError._PARTITION_EOF:
                        logger.error(f"Consumer error: {msg.error()}")
                else:
                    self.process_message(msg)

                if time.time() - self.last_flush_time >= 30:
                    self.write_buffer_to_s3()

        except KeyboardInterrupt:
            logger.info("사용자에 의해 중단됨")
        finally:
            self.write_buffer_to_s3()
            self.consumer.close()
            logger.info("Consumer 종료")

if __name__ == "__main__":
    consumer = FMSDataConsumer()
    consumer.run()
