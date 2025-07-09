from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, to_timestamp, date_format
from pyspark.sql.types import StructType, StringType, IntegerType, BooleanType, FloatType

# S3 경로 변경
S3_BUCKET = "s3a://awsprelab1/jaeyeop_test/fms"

# Kinesis 설정
KINESIS_STREAM_NAME = "fms-sensor-data-kinesis"
AWS_REGION = "ap-northeast-1"

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

spark = SparkSession.builder.appName("KinesisSensorProcessor") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.hadoop.fs.s3a.aws.credentials.provider", "com.amazonaws.auth.DefaultAWSCredentialsProviderChain") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

# Kinesis 스트림에서 읽기
df_raw = spark.readStream.format("kinesis") \
    .option("streamName", KINESIS_STREAM_NAME) \
    .option("region", AWS_REGION) \
    .option("startingposition", "LATEST") \
    .load()

# raw 데이터 저장
raw_path = f"{S3_BUCKET}/rawdata/"
df_raw.selectExpr("CAST(data AS STRING) as json") \
    .writeStream \
    .format("json") \
    .option("path", raw_path) \
    .option("checkpointLocation", raw_path + "_chk") \
    .outputMode("append") \
    .start()

# JSON 파싱 및 컬럼 변환
df = df_raw.selectExpr("CAST(data AS STRING) as json") \
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

write_stream(df_fail, f"{S3_BUCKET}/analytics/fail/")
write_stream(df_dataerr, f"{S3_BUCKET}/analytics/dataerr/")
write_stream(df_correct, f"{S3_BUCKET}/analytics/data/")

spark.streams.awaitAnyTermination()
