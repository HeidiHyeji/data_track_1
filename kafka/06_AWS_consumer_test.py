import boto3
import json
import time

STREAM_NAME = 'fms-sensor-data-kinesis'
REGION = 'ap-northeast-1'

client = boto3.client('kinesis', region_name=REGION)

# 모든 샤드 가져오기
shards = client.describe_stream(StreamName=STREAM_NAME)['StreamDescription']['Shards']

# 각 샤드마다 이터레이터 생성
iterators = {}
for shard in shards:
    shard_id = shard['ShardId']
    iterator = client.get_shard_iterator(
        StreamName=STREAM_NAME,
        ShardId=shard_id,
        ShardIteratorType='LATEST'  # or 'TRIM_HORIZON'
    )['ShardIterator']
    iterators[shard_id] = iterator

print("Kinesis 모든 샤드에서 데이터 수신 시작...")

while True:
    for shard_id, iterator in iterators.items():
        out = client.get_records(ShardIterator=iterator, Limit=100)
        records = out['Records']

        for record in records:
            try:
                data = json.loads(record['Data'].decode('utf-8'))
                print(f"[{shard_id}] ✅ 수신: {data}")
            except Exception as e:
                print(f"[{shard_id}] ❌ 디코딩 실패: {e}")

        # 다음 iterator로 갱신
        iterators[shard_id] = out['NextShardIterator']

    time.sleep(1)

