import boto3
import re

REGION = "ap-northeast-1"
RESULT_BUCKET = "awsprelab1/athena-query-results/"
S3_BUCKET = "awsprelab1"

# 테이블별 파라미터 정의
TABLES = [
    {
        "table": "fms_data",
        "database": "fms_analytics",
        "prefix": "fms/analytics_parquet/data/"
    },
    {
        "table": "fms_dataerr",
        "database": "fms_analytics",
        "prefix": "fms/analytics_parquet/dataerr/"
    },
    {
        "table": "fms_fail",
        "database": "fms_analytics",
        "prefix": "fms/analytics_parquet/fail/"
    }
]

# Athena 쿼리 실행 함수
def run_athena_query(query, database):
    client = boto3.client("athena", region_name=REGION)
    response = client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": database},
        ResultConfiguration={"OutputLocation": f"s3://{RESULT_BUCKET}"}
    )
    print(f"🔎 쿼리 실행: {query}")
    return response["QueryExecutionId"]

# S3 파티션 경로 탐색
def list_partitions(s3_prefix):
    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    partitions = set()

    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=s3_prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            match = re.search(r"DeviceId=(\d+)/ymdh=(\d+)", key)
            if match:
                device_id = int(match.group(1))
                ymdh = match.group(2)
                partitions.add((device_id, ymdh))
    return sorted(partitions)

# 각 테이블마다 파티션 추가
def add_all_partitions():
    for entry in TABLES:
        table = entry["table"]
        db = entry["database"]
        prefix = entry["prefix"]
        partitions = list_partitions(prefix)

        print(f"\n📌 테이블 `{table}`에 파티션 추가 중... (총 {len(partitions)}개)")

        for device_id, ymdh in partitions:
            stmt = (
                f"ALTER TABLE {table} ADD IF NOT EXISTS "
                f"PARTITION (DeviceId={device_id}, ymdh='{ymdh}') "
                f"LOCATION 's3://{S3_BUCKET}/{prefix}DeviceId={device_id}/ymdh={ymdh}/'"
            )
            run_athena_query(stmt, db)

if __name__ == "__main__":
    print("🚀 Athena 모든 파티션 자동 등록 시작")
    add_all_partitions()
    print("✅ 완료")
