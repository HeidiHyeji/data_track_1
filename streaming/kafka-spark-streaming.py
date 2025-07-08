#!/usr/bin/env python3
"""
Spark Streaming with Kafka Integration
Kafka에서 데이터를 수신하여 실시간 분석
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, FloatType, BooleanType
from pyspark.sql.window import Window
from HDFSStorageManager import HDFSStorageManager
from prometheus_exporter import (
    start_prometheus_exporter, fms_device_online, fms_sensor1_value, fms_sensor2_value, fms_sensor3_value,
    fms_motor1_rpm, fms_motor2_rpm, fms_motor3_rpm,
    fms_failure_rate, fms_data_quality_score
)

# outlier_detection_rules.py에서 이상치 탐지 규칙 로드
OUTLIER_DETECTION_RULES = {
    "method": "IQR",  
    "window_size": 100,  
    "threshold": 1.5,
    "sensor_specific": {
        "sensor1": {"min": 0, "max": 100, "z_score": 3},
        "sensor2": {"min": 0, "max": 100, "z_score": 3},
        "sensor3": {"min": 0, "max": 150, "z_score": 3},
        "motor1": {"min": 0, "max": 2000, "z_score": 2.5},
        "motor2": {"min": 0, "max": 1500, "z_score": 2.5},
        "motor3": {"min": 0, "max": 1800, "z_score": 2.5}
    }
}

#null handling : seonsor 보간은 스트리밍에서 처리하기 어려우므로 DEFAULT_0으로 대체
NULL_HANDLING_RULES = {
    "time": "REJECT",           # 타임스탬프 NULL 시 데이터 거부
    "DeviceId": "REJECT",       # 장비 ID NULL 시 데이터 거부
    "sensor1": "DEFAULT_0",     # 이전 값으로 보간 => 기본값 0으로 설정
    "sensor2": "DEFAULT_0",     # 이전 값으로 보간 => 기본값 0으로 설정
    "sensor3": "DEFAULT_0",     # 이전 값으로 보간 => 기본값 0으로 설정
    "motor1": "DEFAULT_0",      # 기본값 0으로 설정
    "motor2": "DEFAULT_0",      # 기본값 0으로 설정
    "motor3": "DEFAULT_0",      # 기본값 0으로 설정
    "isFail": "DEFAULT_FALSE"   # 기본값 false로 설정
}

# type_validation_rules.py에서 타입 검증 규칙 로드
TYPE_VALIDATION_RULES = {
    "time": {
        "target_type": "timestamp",
        "format": "ISO8601",
        "error_action": "REJECT"
    },
    "DeviceId": {
        "target_type": "int",
        "range": [1, 5],
        "error_action": "REJECT"
    },
    "sensor1": {
        "target_type": "float",
        "precision": 2,
        "range": [0.00, 100.00],
        "error_action": "CONVERT_OR_REJECT"
    },
    "sensor2": {
        "target_type": "float",
        "precision": 2,
        "range": [0.00, 100.00],
        "error_action": "CONVERT_OR_REJECT"
    },
    "sensor3": {
        "target_type": "float",
        "precision": 2,
        "range": [0.00, 150.00],
        "error_action": "CONVERT_OR_REJECT"
    },
    "motor1": {
        "target_type": "int",
        "range": [0, 2000],
        "error_action": "CONVERT_OR_REJECT"
    },
    "motor2": {
        "target_type": "int",
        "range": [0, 1500],
        "error_action": "CONVERT_OR_REJECT"
    },
    "motor3": {
        "target_type": "int",
        "range": [0, 1800],
        "error_action": "CONVERT_OR_REJECT"
    },
    "isFail": {
        "target_type": "boolean",
        "error_action": "CONVERT_OR_DEFAULT"
    }
}

# 타입 검증 함수
def validate_types(df):
    def validate_column(col_name, target_type, rules):
        if target_type == "timestamp":
            return when(col(col_name).cast("timestamp").isNotNull(), col(col_name)) \
                .otherwise(None)
        elif target_type == "int":
            return when(col(col_name).cast("int").between(rules["range"][0], rules["range"][1]), col(col_name)) \
                .otherwise(None)
        elif target_type == "float":
            return when(col(col_name).cast("float").between(rules["range"][0], rules["range"][1]), col(col_name)) \
                .otherwise(None)
        elif target_type == "boolean":
            return when(col(col_name).cast("boolean").isNotNull(), col(col_name)) \
                .otherwise(None)
        else:
            return col(col_name)
    for column, rules in TYPE_VALIDATION_RULES.items():
        df = df.withColumn(column, validate_column(column, rules['target_type'], rules))
    return df

# 이상치 탐지 (IQR 방법) 처리 함수
def detect_outliers(df):
    def apply_outlier_detection(sensor, min_val, max_val, z_score_thresh):
        q1 = df.approxQuantile(sensor, [0.25], 0.01)[0]
        q3 = df.approxQuantile(sensor, [0.75], 0.01)[0]
        iqr = q3 - q1
        lower_bound = q1 - OUTLIER_DETECTION_RULES["threshold"] * iqr
        upper_bound = q3 + OUTLIER_DETECTION_RULES["threshold"] * iqr
        return when((col(sensor) < lower_bound) | (col(sensor) > upper_bound), "FLAG").otherwise("NORMAL")
    for sensor, rules in OUTLIER_DETECTION_RULES["sensor_specific"].items():
        df = df.withColumn(f"{sensor}_outlier", apply_outlier_detection(sensor, rules['min'], rules['max'], rules['z_score']))
    return df

# null 처리
def handle_nulls(df):
    # 먼저 reject 대상 컬럼이 NULL인 행은 제거
    reject_columns = [col for col, rule in NULL_HANDLING_RULES.items() if rule == "REJECT"]
    for column in reject_columns:
        df = df.filter(col(column).isNotNull())
    # 나머지 처리
    for column, rule in NULL_HANDLING_RULES.items():
        if rule == "DEFAULT_0":
            df = df.withColumn(column, when(col(column).isNull(), lit(0)).otherwise(col(column)))
        elif rule == "DEFAULT_FALSE":
            df = df.withColumn(column, when(col(column).isNull(), lit(False)).otherwise(col(column)))
        elif rule == "INTERPOLATE":
            # 이전 값으로 보간
            window_spec = Window.orderBy("time").rowsBetween(-1, -1)
            df = df.withColumn(column, when(col(column).isNull(), last(col(column), ignorenulls=True).over(window_spec)).otherwise(col(column)))
        # "REJECT"는 위에서 처리했으므로 무시
    return df

def update_prometheus_metrics(batch_df, batch_id):
    if batch_df.isEmpty():
        return

    # 장비 ID별 최신 상태 추출
    latest_df = batch_df.groupBy("DeviceId").agg(
        max("time").alias("latest_time"),
        avg("sensor1").alias("sensor1"),
        avg("sensor2").alias("sensor2"),
        avg("sensor3").alias("sensor3"),
        avg("motor1").alias("motor1"),
        avg("motor2").alias("motor2"),
        avg("motor3").alias("motor3"),
        avg(col("isFail").cast("int")).alias("fail_rate")
    )

    stats = latest_df.collect()
    for row in stats:
        device_id = str(row["DeviceId"])

        # 장비 상태: 최근에 데이터가 있으면 online
        fms_device_online.labels(device_id=device_id).set(1)

        # 센서 값
        if row["sensor1"] is not None:
            fms_sensor1_value.labels(device_id=device_id).set(row["sensor1"])
        if row["sensor2"] is not None:
            fms_sensor2_value.labels(device_id=device_id).set(row["sensor2"])
        if row["sensor3"] is not None:
            fms_sensor3_value.labels(device_id=device_id).set(row["sensor3"])

        # 모터 값
        if row["motor1"] is not None:
            fms_motor1_rpm.labels(device_id=device_id).set(row["motor1"])
        if row["motor2"] is not None:
            fms_motor2_rpm.labels(device_id=device_id).set(row["motor2"])
        if row["motor3"] is not None:
            fms_motor3_rpm.labels(device_id=device_id).set(row["motor3"])

        # 장애율
        if row["fail_rate"] is not None:
            fms_failure_rate.labels(device_id=device_id).set(row["fail_rate"] * 100)

def create_spark_session():
    return SparkSession.builder \
        .appName("KafkaSparkStreaming") \
        .master("spark://s1:7077") \
        .config("spark.sql.streaming.checkpointLocation", "/tmp/checkpoint") \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
        .config("spark.executor.memory", "700m") \
        .config("spark.executor.instances", "1") \
        .getOrCreate()

def kafka_stream_processing():
    spark = create_spark_session()
    hdfs = HDFSStorageManager()

    # 여기에서 exporter 실행 (s1에서 8000 포트 오픈)
    start_prometheus_exporter(port=8000)

    schema = StructType([
            StructField("time", StringType(), True),
            StructField("DeviceId", IntegerType(), True),
            StructField("sensor1", FloatType(), True),
            StructField("sensor2", FloatType(), True), 
            StructField("sensor3", FloatType(), True),
            StructField("motor1", FloatType(), True),
            StructField("motor2", FloatType(), True),
            StructField("motor3", FloatType(), True),
            StructField("isFail", BooleanType(), True)
        ])
    
    # Kafka 스트림 읽기
    df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "s1:9092") \
        .option("subscribe", "fms-sensor-data") \
        .load()
    
    # 데이터프레임에서 json 데이터 치환하기
    df = df.selectExpr("CAST(value AS STRING) as json_data") \
           .withColumn("parsed", from_json(col("json_data"), schema)) \
           .select("parsed.*")  # JSON 내부 데이터만 선택

    # time이나 deviceId가 null인 데이터는 처리하지 않음
    # df_null = df[df['time'].isnull() | df['DeviceId'].isnull()]

    # df_not_null = df[df['time'].notnull() & df['DeviceId'].notnull()]
    df_not_null = df.filter(df['time'].isNotNull() & df['DeviceId'].isNotNull())

    # motor1~3 Float => Integer 형변환
    df_not_null = df_not_null.withColumn("motor1", col("motor1").cast(IntegerType())) \
        .withColumn("motor2", col("motor2").cast(IntegerType())) \
        .withColumn("motor3", col("motor3").cast(IntegerType())) \
        .withColumn("date", to_date(col("time"))) \
        .withColumn("year", year(col("date"))) \
        .withColumn("month", month(col("date"))) \
        .withColumn("day", dayofmonth(col("date"))) \
        .drop("date")

    # raw-data를 스트리밍 데이터를 HDFS에 저장
    query = hdfs.save_raw_data(df_not_null)

    # 타입 검증
    processed_df = validate_types(df_not_null)

    # 이상치 탐지
    # processed_df = detect_outliers(processed_df)

    # null값 처리
    processed_df = handle_nulls(processed_df)

    # 처리된 데이터를 HDFS에 저장
    query_processed = hdfs.save_processed_data(processed_df)

    # 경고용 데이터를 HDFS에 저장
    # query_alert = hdfs.save_alerts(df_null)

    # Prometheus 연동 스트림 추가
    query_metrics = processed_df.writeStream \
        .outputMode("update") \
        .foreachBatch(update_prometheus_metrics) \
        .start()

    spark.streams.awaitAnyTermination()

if __name__ == "__main__":
    kafka_stream_processing()