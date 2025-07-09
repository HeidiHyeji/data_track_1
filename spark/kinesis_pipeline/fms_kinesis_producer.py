import asyncio
import aiohttp
import json
import logging
from datetime import datetime
import boto3
import botocore.exceptions

# 설정
STREAM_NAME = "fms-sensor-data-kinesis"
API_BASE_URL = "http://finfra.iptime.org:9872"
DEVICE_IDS = list(range(1, 101))  # 1~100번 장비
MAX_CONCURRENCY = 10  # 동시에 실행할 fetch 요청 개수 제한

# 로깅
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AsyncFMSKinesisProducer:
    def __init__(self):
        self.kinesis = boto3.client("kinesis", region_name="ap-northeast-1")

    async def fetch_and_send_forever(self, session, device_id):
        url = f"{API_BASE_URL}/{device_id}/"
        while True:
            async with self.semaphore:
                try:
                    async with session.get(url, timeout=5) as response:
                        if response.status == 200:
                            data = await response.json()
                            data["collected_at"] = datetime.now().isoformat()
                            self.send_to_kinesis(data)
                            logger.info(f"✅ Device {device_id}: 전송 완료")
                        else:
                            logger.warning(f"⚠️ Device {device_id}: HTTP {response.status}")
                except Exception as e:
                    logger.error(f"❌ Device {device_id}: 요청 실패 - {e}")
            await asyncio.sleep(0.1)  # 각 장비 요청 간 0.1초 간격

    def send_to_kinesis(self, data):
        try:
            partition_key = str(data.get("DeviceId", "unknown"))
            self.kinesis.put_record(
                StreamName=STREAM_NAME,
                Data=json.dumps(data),
                PartitionKey=partition_key
            )
        except botocore.exceptions.BotoCoreError as e:
            logger.error(f"Kinesis 전송 실패: {e}")

    async def run_loop(self):
        logger.info("🚀 FMS Kinesis 실시간 Producer 시작")
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

        async with aiohttp.ClientSession() as session:
            tasks = [
                asyncio.create_task(self.fetch_and_send_forever(session, device_id))
                for device_id in DEVICE_IDS
            ]
            await asyncio.gather(*tasks)

def main():
    producer = AsyncFMSKinesisProducer()
    asyncio.run(producer.run_loop())

if __name__ == "__main__":
    main()
