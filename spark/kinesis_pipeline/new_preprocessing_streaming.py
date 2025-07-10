from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_timestamp, year, month, dayofmonth, hour, from_utc_timestamp
from pyspark.sql.types import StructType, StringType, IntegerType, DoubleType, BooleanType

# Spark 세션 생성
spark = SparkSession.builder \
    .appName("FMS_Custom_S3_Path") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.hadoop.fs.s3a.aws.credentials.provider", "com.amazonaws.auth.DefaultAWSCredentialsProviderChain") \
    .getOrCreate()

# 스키마 정의
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

# 스트림 입력
df_raw = spark.readStream \
    .format("json") \
    .schema(schema) \
    .option("maxFilesPerTrigger", 1) \
    .load("s3a://awsprelab1/fms/raw-data/*/*/*/*/*.json")

# 시간 및 파티션용 컬럼 생성 (KST 기준)
df = df_raw \
    .withColumn("ts_utc", to_timestamp(col("time"))) \
    .withColumn("ts", to_timestamp(col("time"))) \
    .withColumn("year", year(col("ts"))) \
    .withColumn("month", month(col("ts"))) \
    .withColumn("day", dayofmonth(col("ts"))) \
    .withColumn("hour", hour(col("ts")))

# 유효성 조건 정의
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

# 데이터 분기
df_correct = df.filter((col("isFail") == False) & valid_range)
df_dataerr = df.filter((col("isFail") == False) & (~valid_range))
df_fail = df.filter(col("isFail") == True)
# 배치 저장 함수: 디렉토리 직접 구성
def write_batch_to_custom_path(batch_df, batch_id, category):
    batch_df_local = batch_df.withColumn("YYYY", col("year")) \
                             .withColumn("MM", col("month")) \
                             .withColumn("DD", col("day")) \
                             .withColumn("HH", col("hour")) \
                             .withColumn("ID", col("DeviceId"))

    partitions = batch_df_local.select("YYYY", "MM", "DD", "HH", "ID").distinct().collect()

    for row in partitions:
        yyyy = int(row["YYYY"])
        mm = int(row["MM"])
        dd = int(row["DD"])
        hh = int(row["HH"])
        device_id = int(row["ID"])

        path = f"s3a://awsprelab1/fms/analytics_parquet/{category}/{yyyy:04d}/{mm:02d}/{dd:02d}/{hh:02d}/{device_id:02d}/"

        print(f"📦 [{category}] Writing to: {path}")

        batch_df_local \
            .filter(
                (col("year") == yyyy) &
                (col("month") == mm) &
                (col("day") == dd) &
                (col("hour") == hh) &
                (col("DeviceId") == device_id)
            ) \
            .drop("YYYY", "MM", "DD", "HH", "ID") \
            .write.mode("append").parquet(path)


# 스트리밍 시작
query_data = df_correct.writeStream \
    .foreachBatch(lambda df, id: write_batch_to_custom_path(df, id, "data")) \
    .outputMode("append") \
    .option("checkpointLocation", "s3a://awsprelab1/fms/analytics_parquet/data_checkpoint") \
    .start()

query_dataerr = df_dataerr.writeStream \
    .foreachBatch(lambda df, id: write_batch_to_custom_path(df, id, "dataerr")) \
    .outputMode("append") \
    .option("checkpointLocation", "s3a://awsprelab1/fms/analytics_parquet/dataerr_checkpoint") \
    .start()

query_fail = df_fail.writeStream \
    .foreachBatch(lambda df, id: write_batch_to_custom_path(df, id, "fail")) \
    .outputMode("append") \
    .option("checkpointLocation", "s3a://awsprelab1/fms/analytics_parquet/fail_checkpoint") \
    .start()

# 실행 대기
query_data.awaitTermination()
query_dataerr.awaitTermination()
query_fail.awaitTermination()
