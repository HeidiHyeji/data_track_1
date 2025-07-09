

import time
from datetime import datetime, timedelta
from pyspark.sql import SparkSession, Window
from pyspark.sql.functions import col, from_json, row_number, lit, to_timestamp, date_format
from pyspark.sql.types import StructType, StringType, IntegerType, DoubleType, BooleanType
from prometheus_client import start_http_server, Gauge

# --- 설정 ---
S3_RAW_DATA_PATH = "s3a://awsprelab1/fms/raw-data"
PROMETHEUS_PORT = 9993  # 다른 스크립트와 충돌하지 않는 새 포트
REFRESH_INTERVAL_SECONDS = 30
DATA_RETENTION_MINUTES = 60  # 60분 이내의 데이터만 사용

# --- 프로메테우스 메트릭 정의 ---
METRIC_LABELS = ['device_id']
RAW_METRICS = {
    'sensor1': Gauge('fms_raw_latest_sensor1', 'Latest raw value of sensor1', METRIC_LABELS),
    'sensor2': Gauge('fms_raw_latest_sensor2', 'Latest raw value of sensor2', METRIC_LABELS),
    'sensor3': Gauge('fms_raw_latest_sensor3', 'Latest raw value of sensor3', METRIC_LABELS),
    'motor1': Gauge('fms_raw_latest_motor1', 'Latest raw value of motor1', METRIC_LABELS),
    'motor2': Gauge('fms_raw_latest_motor2', 'Latest raw value of motor2', METRIC_LABELS),
    'motor3': Gauge('fms_raw_latest_motor3', 'Latest raw value of motor3', METRIC_LABELS),
}

# --- JSON 데이터 스키마 ---
JSON_SCHEMA = StructType() \
    .add("time", StringType()) \
    .add("DeviceId", IntegerType()) \
    .add("sensor1", DoubleType()) \
    .add("sensor2", DoubleType()) \
    .add("sensor3", DoubleType()) \
    .add("motor1", DoubleType()) \
    .add("motor2", DoubleType()) \
    .add("motor3", DoubleType()) \
    .add("isFail", BooleanType()) \
    .add("collected_at", StringType())

def update_raw_metrics(spark):
    """S3의 raw JSON 데이터를 읽고, 장비별 최신 값을 찾아 프로메테우스 메트릭을 업데이트합니다."""
    print(f"🔄 최신 'raw' 데이터를 찾습니다... (경로: {S3_RAW_DATA_PATH})")
    
    try:
        # 1. S3 경로의 JSON 파일 읽기
        df_raw = spark.read.text(S3_RAW_DATA_PATH)
        
        # 2. JSON 파싱 및 컬럼 추출
        df_parsed = df_raw.select(from_json(col("value"), JSON_SCHEMA).alias("data")).select("data.*")

        # 3. 타임스탬프 생성 및 60분 이내 데이터 필터링
        df_with_ts = df_parsed.withColumn("ts", to_timestamp(col("collected_at")))
        time_threshold = datetime.now() - timedelta(minutes=DATA_RETENTION_MINUTES)
        df_recent = df_with_ts.filter(col("ts") >= lit(time_threshold).cast("timestamp"))

        if df_recent.rdd.isEmpty():
            print("✅ 처리할 최신 'raw' 데이터가 없습니다.")
            for gauge in RAW_METRICS.values():
                gauge.clear()
            return

        # 4. 각 DeviceId 내에서 time 컬럼을 기준으로 최신 레코드 찾기
        window_spec = Window.partitionBy("DeviceId").orderBy(col("time").desc())
        df_latest = df_recent.withColumn("rank", row_number().over(window_spec)) \
                             .filter(col("rank") == 1) \
                             .select("DeviceId", "sensor1", "sensor2", "sensor3", "motor1", "motor2", "motor3")

        # 5. 찾은 최신 값을 프로메테우스 게이지에 반영
        for gauge in RAW_METRICS.values():
            gauge.clear()
            
        for row in df_latest.collect():
            labels = {"device_id": str(row["DeviceId"])}
            for metric_name, gauge in RAW_METRICS.items():
                value = row[metric_name]
                if value is not None:
                    gauge.labels(**labels).set(float(value))
        
        print(f"✅ {df_latest.count()}개 'raw' 장비의 최신 메트릭을 성공적으로 업데이트했습니다.")

    except Exception as e:
        if "Path does not exist" in str(e):
            print(f"⚠️ S3 경로를 찾을 수 없습니다: {S3_RAW_DATA_PATH}. 'raw' 데이터가 아직 없을 수 있습니다.")
        else:
            print(f"❌ 데이터 처리 중 오류가 발생했습니다: {e}")

def main():
    """메인 함수: Spark 세션 생성, 프로메테우스 서버 시작 및 메트릭 업데이트 루프 실행"""
    spark = SparkSession.builder \
        .appName("FMS S3 Raw to Prometheus") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.aws.credentials.provider", "com.amazonaws.auth.DefaultAWSCredentialsProviderChain") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("ERROR")

    print(f"🚀 'raw' 데이터 프로메테우스 메트릭 서버를 시작합니다. (포트: {PROMETHEUS_PORT})")
    start_http_server(PROMETHEUS_PORT)
    print(f"🔗 메트릭 확인: http://<your-spark-driver-ip>:{PROMETHEUS_PORT}")

    try:
        while True:
            update_raw_metrics(spark)
            print(f"🕒 다음 업데이트까지 {REFRESH_INTERVAL_SECONDS}초 대기합니다...")
            time.sleep(REFRESH_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\n🛑 스크립트를 종료합니다.")
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
