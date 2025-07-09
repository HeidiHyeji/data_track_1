

import time
from pyspark.sql import SparkSession, Window
from pyspark.sql.functions import col, row_number, current_timestamp, expr
from prometheus_client import start_http_server, Gauge

# --- 설정 ---
S3_DATA_PATH = "s3a://awsprelab1/fms/analytics_parquet/data"
PROMETHEUS_PORT = 9990  # 이전 스크립트와 다른 포트 사용
REFRESH_INTERVAL_SECONDS = 10  # 10초마다 데이터 갱신

# --- 프로메테우스 메트릭 정의 ---
# 'device_id'를 라벨로 사용하여 장비별 최신 값을 구분
LATEST_METRICS = {
    'latest_sensor1': Gauge('fms_latest_sensor1', 'Latest value of sensor1 for a device', ['device_id']),
    'latest_sensor2': Gauge('fms_latest_sensor2', 'Latest value of sensor2 for a device', ['device_id']),
    'latest_sensor3': Gauge('fms_latest_sensor3', 'Latest value of sensor3 for a device', ['device_id']),
    'latest_motor1': Gauge('fms_latest_motor1', 'Latest value of motor1 for a device', ['device_id']),
    'latest_motor2': Gauge('fms_latest_motor2', 'Latest value of motor2 for a device', ['device_id']),
    'latest_motor3': Gauge('fms_latest_motor3', 'Latest value of motor3 for a device', ['device_id']),
}

def update_latest_metrics(spark):
    """S3에서 데이터를 읽고, 장비별 최신 값을 찾아 프로메테우스 메트릭을 업데이트합니다."""
    print(f"🔄 최신 데이터를 찾습니다... (경로: {S3_DATA_PATH})")
    
    try:
        # 1. S3에서 Parquet 데이터 읽기
        df = spark.read.parquet(S3_DATA_PATH)

        # 2. 각 DeviceId 내에서 time 컬럼을 기준으로 최신 레코드 찾기
        window_spec = Window.partitionBy("DeviceId").orderBy(col("time").desc())
        df_latest = df.withColumn("rank", row_number().over(window_spec)) \
                      .filter(col("rank") == 1) \
                      .drop("rank")
        
        df_recent = df_latest.filter(
            (col("ts") >= current_timestamp() - expr("INTERVAL 5 MINUTE"))
        )

        # 3. 찾은 최신 값을 프로메테우스 게이지에 반영
        for row in df_recent.collect():
            device_id = str(row["DeviceId"])
            for metric_name, gauge in LATEST_METRICS.items():
                # 'latest_' 접두사를 제외한 컬럼명으로 값을 가져옴
                col_name = metric_name.replace('latest_', '')
                if row[col_name] is not None:
                    gauge.labels(device_id=device_id).set(row[col_name])
        
        print(f"✅ {df_recent.count()}개 장비의 최신 메트릭을 성공적으로 업데이트했습니다.")

    except Exception as e:
        print(f"❌ 데이터 처리 중 오류가 발생했습니다: {e}")

def main():
    """메인 함수: Spark 세션 생성, 프로메테우스 서버 시작 및 메트릭 업데이트 루프 실행"""
    # Spark 세션 생성
    spark = SparkSession.builder \
        .appName("FMS S3 Latest to Prometheus") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.aws.credentials.provider", "com.amazonaws.auth.DefaultAWSCredentialsProviderChain") \
        .getOrCreate()

    # Spark 로그 레벨 설정
    spark.sparkContext.setLogLevel("ERROR")

    print(f"🚀 프로메테우스 메트릭 서버를 시작합니다. (포트: {PROMETHEUS_PORT})")
    start_http_server(PROMETHEUS_PORT)
    print(f"🔗 메트릭 확인: http://<your-spark-driver-ip>:{PROMETHEUS_PORT}")

    try:
        while True:
            update_latest_metrics(spark)
            print(f"🕒 다음 업데이트까지 {REFRESH_INTERVAL_SECONDS}초 대기합니다...")
            time.sleep(REFRESH_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\n🛑 스크립트를 종료합니다.")
    finally:
        spark.stop()

if __name__ == "__main__":
    main()

