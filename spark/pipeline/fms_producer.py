import asyncio
import aiohttp
import json
import logging
from datetime import datetime
from confluent_kafka import Producer

# 설정
BROKER = "s1:9092,s2:9092,s3:9092,i1:9092"
TOPIC = "fms-sensor-data"
API_BASE_URL = "http://finfra.iptime.org:9872"
DEVICE_IDS = list(range(1, 101))  # 1~100번 장비
FETCH_INTERVAL = 10
MAX_CONCURRENCY = 10  # 동시에 요청할 최대 장비 수

# 로깅
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AsyncFMSProducer:
    def __init__(self):
        self.producer = Producer({'bootstrap.servers': BROKER})

    async def fetch_and_send(self, session, device_id):
        url = f"{API_BASE_URL}/{device_id}/"
        async with self.semaphore:
            try:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        data["collected_at"] = datetime.now().isoformat()
                        self.send_to_kafka(data)
                        logger.info(f"✅ Device {device_id}: 전송 완료")
                    else:
                        logger.warning(f"⚠️ Device {device_id}: HTTP {response.status}")
            except Exception as e:
                logger.error(f"❌ Device {device_id}: 요청 실패 - {e}")

    def send_to_kafka(self, data):
        try:
            self.producer.produce(
                topic=TOPIC,
                key=str(data.get("DeviceId")),
                value=json.dumps(data),
                callback=self.delivery_callback
            )
            self.producer.poll(0)
        except Exception as e:
            logger.error(f"Kafka 전송 실패: {e}")

    def delivery_callback(self, err, msg):
        if err:
            logger.error(f"❌ 메시지 실패: {err}")
        else:
            logger.debug(f"📨 메시지 전송됨 {msg.topic()} [{msg.partition()}] @ {msg.offset()}")

    async def run_loop(self):
        logger.info("📡 Async FMS Producer 시작")

        
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
        
        while True:
            start = datetime.now()
            async with aiohttp.ClientSession() as session:
                tasks = [self.fetch_and_send(session, device_id) for device_id in DEVICE_IDS]
                await asyncio.gather(*tasks)

            self.producer.flush()

            elapsed = (datetime.now() - start).total_seconds()
            sleep_time = max(0, FETCH_INTERVAL - elapsed)
            logger.info(f"🕒 다음 수집까지 {sleep_time:.1f}초 대기...")
            await asyncio.sleep(sleep_time)

def main():
    producer = AsyncFMSProducer()
    asyncio.run(producer.run_loop())

if __name__ == "__main__":
    main()
