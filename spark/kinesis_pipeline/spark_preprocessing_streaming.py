from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, to_timestamp, date_format
from pyspark.sql.types import StructType, StringType, IntegerType, DoubleType, BooleanType

# 1. Spark 세션 생성
spark = SparkSession.builder \
    .appName("FMS_S3_Streaming_Preprocessing") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.hadoop.fs.s3a.aws.credentials.provider", "com.amazonaws.auth.DefaultAWSCredentialsProviderChain") \
    .getOrCreate()

# 2. 메시지 스키마 정의 (JSON)
schema = StructType() \
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

# 3. S3에서 JSON 스트림 읽기
df_raw = spark.readStream \
    .format("json") \
    .schema(schema) \
    .option("maxFilesPerTrigger", 1) \
    .load("s3a://awsprelab1/fms/raw-data/")

# 4. 전처리 컬럼 추가
df = df_raw \
    .withColumn("ts", to_timestamp(col("collected_at"))) \
    .withColumn("ymdh", date_format(col("ts"), "yyyyMMddHH"))

# 5. 유효성 조건 정의
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

# 6. 조건별 분기
df_fail     = df.filter(col("isFail") == True)
df_dataerr  = df.filter((col("isFail") == False) & (~valid_range))
df_correct  = df.filter((col("isFail") == False) & valid_range)

# 7. 저장 함수 정의
def write_stream(target_df, base_path):
    return target_df \
        .writeStream \
        .format("parquet") \
        .outputMode("append") \
        .option("path", base_path) \
        .option("checkpointLocation", base_path + "_checkpoint") \
        .option("compression", "snappy") \
        .partitionBy("DeviceId", "ymdh") \
        .trigger(processingTime="30 seconds") \
        .start()

# 8. 각 분기 저장 실행
query_fail = write_stream(df_fail,    "s3a://awsprelab1/fms/analytics_parquet/fail")
query_err  = write_stream(df_dataerr, "s3a://awsprelab1/fms/analytics_parquet/dataerr")
query_ok   = write_stream(df_correct, "s3a://awsprelab1/fms/analytics_parquet/data")

# 9. 스트리밍 유지
query_fail.awaitTermination()
query_err.awaitTermination()
query_ok.awaitTermination()
