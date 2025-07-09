#!/bin/bash

# === [1] 변수 설정 ===
LOCAL_FILE="spark_preprocessing_streaming.py"
S3_BUCKET="awsprelab1"
S3_KEY="scripts/spark_preprocessing_streaming.py"
S3_URI="s3://${S3_BUCKET}/${S3_KEY}"
PARTITION_SCRIPT="add_all_partitions_to_athena.py"
PARTITION_S3_KEY="scripts/${PARTITION_SCRIPT}"
PARTITION_S3_URI="s3://${S3_BUCKET}/${PARTITION_S3_KEY}"

# === [2] EMR 클러스터 ID 수동 입력 받기 ===
echo "📝 EMR 클러스터 ID를 입력하세요 (예: j-XXXXXXXXXXXXX):"
read -r CLUSTER_ID

if [ -z "$CLUSTER_ID" ]; then
  echo "❌ 클러스터 ID가 입력되지 않았습니다. 종료합니다."
  exit 1
fi

echo "✅ 입력된 클러스터 ID: $CLUSTER_ID"

# === [3] S3 업로드 ===
echo "📤 S3로 스크립트 업로드 중: $LOCAL_FILE → $S3_URI"
aws s3 cp "$LOCAL_FILE" "$S3_URI"

if [ $? -ne 0 ]; then
  echo "❌ S3 업로드 실패"
  exit 1
fi

echo "📤 S3로 파티션 스크립트 업로드 중: $PARTITION_SCRIPT → $PARTITION_S3_URI"
aws s3 cp "$PARTITION_SCRIPT" "$PARTITION_S3_URI"

if [ $? -ne 0 ]; then
  echo "❌ 파티션 스크립트 S3 업로드 실패"
  exit 1
fi

# === [4] EMR Spark Step 등록 ===
echo "🚀 EMR Spark Step 등록 중..."

aws emr add-steps \
  --cluster-id "$CLUSTER_ID" \
  --steps Type=Spark,Name="FMS_Streaming",ActionOnFailure=CONTINUE,\
Args=[--deploy-mode,cluster,--master,yarn,\
--packages,org.apache.hadoop:hadoop-aws:3.3.4,\
${S3_URI}]

if [ $? -eq 0 ]; then
  echo "✅ Spark 스트리밍 Step 등록 완료"
else
  echo "❌ Spark Step 등록 실패"
  exit 1
fi

# === [5] Athena 파티션 자동 등록 Step ===
echo "🚀 Athena 파티션 등록 Step 추가 중..."

aws emr add-steps \
  --cluster-id "$CLUSTER_ID" \
  --steps Type=CUSTOM_JAR,Name="AddAllAthenaPartitions",ActionOnFailure=CONTINUE,\
Jar=command-runner.jar,Args=["bash","-c","aws s3 cp ${PARTITION_S3_URI} /home/hadoop/${PARTITION_SCRIPT} && python3 /home/hadoop/${PARTITION_SCRIPT}"]

if [ $? -eq 0 ]; then
  echo "✅ Athena 파티션 Step 등록 완료"
else
  echo "❌ Athena 파티션 Step 등록 실패"
  exit 1
fi
