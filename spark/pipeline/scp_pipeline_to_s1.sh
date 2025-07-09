#!/bin/bash

# 로컬 경로 (i1)
SRC_DIR="/home/ec2-user/data_track_1/spark/pipeline"

# 원격 정보
REMOTE_HOST="s1"
REMOTE_DIR="/home/ec2-user/data_track_1/spark/pipeline"

echo "📦 복사 시작: ${SRC_DIR}/*.py → ${REMOTE_HOST}:${REMOTE_DIR}"

# 원격 디렉토리 생성 (없으면)
ssh $REMOTE_HOST "mkdir -p $REMOTE_DIR"

# .py 파일만 복사
scp ${SRC_DIR}/*.py ${REMOTE_HOST}:${REMOTE_DIR}

if [ $? -eq 0 ]; then
  echo "✅ 파일 전송 완료"
else
  echo "❌ 파일 전송 실패"
fi

