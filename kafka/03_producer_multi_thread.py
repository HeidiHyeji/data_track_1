#!/usr/bin/env python3
"""
FMS Real Data Producer
실제 API에서 FMS 센서 데이터를 수집하여 Kafka로 전송 (10개 병렬 처리)
"""
import json
import time
import requests
from confluent_kafka import Producer
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Kafka 설정
BROKER = "s1:9092,s2:9092,s3:9092"
TOPIC = "fms-sensor-data"

# FMS API 설정
API_BASE_URL = "http://finfra.iptime.org:9872"
DEVICE_IDS = list(range(1, 101))  # 1~100번 장비
FETCH_INTERVAL = 10  # 10초 간격
MAX_WORKERS = 5  # 병렬 스레드 수

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FMSDataProducer:
    def __init__(self):
        self.producer = Producer({
            'bootstrap.servers': BROKER,
            'compression.type': 'gzip',
            'batch.size': 16384,
            'linger.ms': 10
        })

    def fetch_device_data(self, device_id):
        """특정 장비의 데이터를 API에서 가져오기"""
        try:
            url = f"{API_BASE_URL}/{device_id}/"
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                data = response.json()
                data['collected_at'] = datetime.now().isoformat()
                return data
            else:
                logger.error(f"Device {device_id}: HTTP {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Device {device_id} API error: {e}")
            return None

    def validate_data(self, data):
        """데이터 유효성 검사"""
        required_fields = ['time', 'DeviceId', 'sensor1', 'sensor2', 'sensor3',
                           'motor1', 'motor2', 'motor3', 'isFail']

        if not all(field in data for field in required_fields):
            return False

        if not (0 <= data['sensor1'] <= 100):
            return False
        if not (0 <= data['sensor2'] <= 100):
            return False
        if not (0 <= data['sensor3'] <= 100):
            return False

        return True

    def send_to_kafka(self, data):
        """Kafka로 데이터 전송"""
        try:
            key = str(data['DeviceId'])
            value = json.dumps(data, ensure_ascii=False)

            self.producer.produce(
                topic=TOPIC,
                key=key,
                value=value,
                callback=self.delivery_callback
            )
            self.producer.poll(0)
        except Exception as e:
            logger.error(f"Kafka send error: {e}")

    def delivery_callback(self, err, msg):
        """메시지 전송 결과 콜백"""
        if err:
            logger.error(f'Message delivery failed: {err}')
        else:
            logger.info(f'Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}')

    def run_continuous(self):
        """연속적으로 데이터 수집 및 전송"""
        logger.info("FMS Data Producer 시작...")
        logger.info(f"수집 대상: 장비 {DEVICE_IDS}")
        logger.info(f"수집 주기: {FETCH_INTERVAL}초, 병렬 스레드 수: {MAX_WORKERS}")

        try:
            while True:
                collection_start = time.time()

                with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    future_to_id = {executor.submit(self.fetch_device_data, i): i for i in DEVICE_IDS}
                    for future in as_completed(future_to_id):
                        device_id = future_to_id[future]
                        try:
                            data = future.result()
                            if data:
                                self.send_to_kafka(data)
                                logger.info(f"Device {device_id}: 데이터 전송 완료")
                            else:
                                logger.warning(f"Device {device_id}: 수집 실패")
                        except Exception as e:
                            logger.error(f"Device {device_id}: 에러 발생: {e}")

                self.producer.flush()

                elapsed = time.time() - collection_start
                sleep_time = max(0, FETCH_INTERVAL - elapsed)

                if sleep_time > 0:
                    logger.info(f"다음 수집까지 {sleep_time:.1f}초 대기...")
                    time.sleep(sleep_time)
                else:
                    logger.warning(f"수집 시간이 {elapsed:.1f}초로 설정된 주기를 초과했습니다.")

        except KeyboardInterrupt:
            logger.info("사용자에 의해 중단됨")
        except Exception as e:
            logger.error(f"예상치 못한 오류: {e}")
        finally:
            self.producer.flush()
            logger.info("Producer 종료")

    def run_once(self):
        """한 번만 데이터 수집 (테스트용)"""
        logger.info("FMS Data Producer 테스트 실행...")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_id = {executor.submit(self.fetch_device_data, i): i for i in DEVICE_IDS}
            for future in as_completed(future_to_id):
                device_id = future_to_id[future]
                try:
                    data = future.result()
                    print(f"\n=== Device {device_id} ===")
                    if data:
                        print(json.dumps(data, indent=2, ensure_ascii=False))
                        if self.validate_data(data):
                            self.send_to_kafka(data)
                            print("✅ Kafka 전송 완료")
                        else:
                            print("❌ 데이터 유효성 검사 실패")
                    else:
                        print("❌ 데이터 수집 실패")
                except Exception as e:
                    print(f"❌ Device {device_id} 에러: {e}")

        self.producer.flush()

def main():
    import sys

    producer = FMSDataProducer()

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        producer.run_once()
    else:
        producer.run_continuous()

if __name__ == "__main__":
    main()

