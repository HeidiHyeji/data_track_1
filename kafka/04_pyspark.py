# spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.0,org.apache.hadoop:hadoop-aws:3.3.4 ${filename}.py

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, to_timestamp, date_format
from pyspark.sql.types import StructType, StringType, IntegerType, BooleanType, FloatType

S3_BUCKET = "s3a://awsprelab1"

# Kafka 브로커 및 토픽
KAFKA_BOOTSTRAP_SERVERS = "s1:9092,s2:9092,s3:9092"
KAFKA_TOPIC = "fms-sensor-data"

# 메시지 스키마 정의
schema = StructType() \
    .add("DeviceId", IntegerType()) \
    .add("collected_at", StringType()) \
    .add("isFail", BooleanType()) \
    .add("motor1", FloatType()) \
    .add("motor2", FloatType()) \
    .add("motor3", FloatType()) \
    .add("sensor1", FloatType()) \
    .add("sensor2", FloatType()) \
    .add("sensor3", FloatType()) \
    .add("time", StringType())

spark = SparkSession.builder.appName("KafkaSensorProcessor").getOrCreate()
spark.sparkContext.setLogLevel("ERROR")
# spark.sparkContext.setLogLevel("WARN")

# Kafka에서 스트리밍 데이터 읽기
df_raw = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
    .option("subscribe", KAFKA_TOPIC) \
    .option("startingOffsets", "latest") \
    .load()

# 원본(raw) 데이터 저장
raw_path = f"{S3_BUCKET}/fms/rawdata/"
df_raw.selectExpr("CAST(value AS STRING) as json") \
    .writeStream \
    .format("json") \
    .option("path", raw_path) \
    .option("checkpointLocation", raw_path + "_chk") \
    .outputMode("append") \
    .start()

# JSON 파싱 및 컬럼 변환
df = df_raw.selectExpr("CAST(value AS STRING) as json") \
    .select(from_json(col("json"), schema).alias("data")) \
    .select("data.*") \
    .withColumn("ts", to_timestamp("collected_at")) \
    .withColumn("ymdh", date_format(col("ts"), "yyyy/MM/dd/HH"))

# 유효값 조건
valid_range = (
    (col("sensor1").between(0, 100)) &
    (col("sensor2").between(0, 100)) &
    (col("sensor3").between(0, 150)) &
    (col("motor1").between(0, 2000)) &
    (col("motor2").between(0, 1500)) &
    (col("motor3").between(0, 1800)) &
    (col("DeviceId").between(1, 100)) &
    (col("isFail").isin(True, False))
)

# 필터링
df_fail = df.filter(col("isFail") == True)
df_dataerr = df.filter((col("isFail") == False) & (~valid_range))
df_correct = df.filter((col("isFail") == False) & valid_range)

def write_stream(target_df, path):
    return target_df.writeStream \
        .format("json") \
        .option("path", path) \
        .option("checkpointLocation", path + "_chk") \
        .partitionBy("DeviceId", "ymdh") \
        .outputMode("append") \
        .start()

write_stream(df_fail, f"{S3_BUCKET}/fms/analytics/fail/")
write_stream(df_dataerr, f"{S3_BUCKET}/fms/analytics/dataerr/")
write_stream(df_correct, f"{S3_BUCKET}/fms/analytics/data/")

spark.streams.awaitAnyTermination()
