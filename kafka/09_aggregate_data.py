import pandas as pd
import boto3
import s3fs
import datetime
import sys

def process_device(device_id, ymdh, bucket, base_prefix, output_prefix, s3, fs):
    yyyy = ymdh[:4]
    mm = ymdh[4:6]
    dd = ymdh[6:8]
    hh = ymdh[8:]

    prefix = f"{base_prefix}{yyyy}/{mm}/{dd}/{hh}/{device_id}/"
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    if 'Contents' not in resp:
        print(f"[WARN] Device {device_id} 경로에 파일 없음: {prefix}")
        return False

    parquet_files = [obj['Key'] for obj in resp['Contents'] if obj['Key'].endswith('.parquet')]
    if not parquet_files:
        print(f"[WARN] Device {device_id} 경로에 parquet 파일 없음: {prefix}")
        return False

    dfs = []
    for key in parquet_files:
        with fs.open(f"s3://{bucket}/{key}", "rb") as f:
            df = pd.read_parquet(f)
            dfs.append(df)
    device_df = pd.concat(dfs)

    agg = device_df[["sensor1", "sensor2", "sensor3", "motor1", "motor2", "motor3"]].mean()

    ymdh_date = ymdh[:8]  # YYYYMMDD
    ymdh_hour = ymdh[8:]   # HH

    lines = [f"[집계 데이터 : {ymdh_date} - {ymdh_hour}]"]
    lines.append(f"motor1_avg : {round(agg['motor1'], 2)}")
    lines.append(f"motor2_avg : {round(agg['motor2'], 2)}")
    lines.append(f"motor3_avg : {round(agg['motor3'], 2)}")
    lines.append(f"sensor1_avg : {round(agg['sensor1'], 2)}")
    lines.append(f"sensor2_avg : {round(agg['sensor2'], 2)}")
    lines.append(f"sensor3_avg : {round(agg['sensor3'], 2)}")
    content = "\n".join(lines)

    filename = f"aggregate_device_{device_id}.text"
    key = f"{output_prefix}/{ymdh_date}/{ymdh_hour}/{filename}"

    s3.put_object(Bucket=bucket, Key=key, Body=content.encode("utf-8"))
    print(f"[INFO] Device {device_id} 집계 완료 및 저장: s3://{bucket}/{key}")

    return True

def main(ymdh):
    if len(ymdh) != 10 or not ymdh.isdigit():
        print(f"[ERROR] ymdh 형식 오류: {ymdh} (예: 2025070906)")
        sys.exit(1)

    bucket = "awsprelab1"
    base_prefix = "fms/analytics_parquet/data/"
    output_prefix = "fms/analytics_aggregate"

    s3 = boto3.client("s3")
    fs = s3fs.S3FileSystem()

    print(f"[INFO] 집계 대상 시간대: {ymdh}")

    processed_count = 0
    for device_id in range(1, 101):
        success = process_device(device_id, ymdh, bucket, base_prefix, output_prefix, s3, fs)
        if success:
            processed_count += 1

    print(f"[INFO] 전체 디바이스 중 집계 완료한 디바이스 수: {processed_count}")

if __name__ == "__main__":
    if len(sys.argv) == 2:
        ymdh = sys.argv[1]
    else:
        now = datetime.datetime.utcnow()
        prev_hour = now - datetime.timedelta(hours=1)
        ymdh = prev_hour.strftime("%Y%m%d%H")
        print(f"[INFO] 인자 없어서 자동으로 1시간 전({ymdh}) 데이터 집계")

    main(ymdh)
