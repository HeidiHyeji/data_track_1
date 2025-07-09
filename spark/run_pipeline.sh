#!/bin/bash

# 1. Producer (i1)
tmux has-session -t producer 2>/dev/null
if [ $? == 0 ]; then
  echo "🔄 producer 세션이 이미 존재합니다. 재시작합니다..."
  tmux kill-session -t producer
fi

echo "📦 aiohttp 설치 확인 중..."
pip show aiohttp > /dev/null 2>&1
if [ $? != 0 ]; then
  echo "🔧 aiohttp가 설치되어 있지 않아 설치합니다..."
  pip install aiohttp
fi

echo "🚀 producer 세션 시작 중..."
tmux new-session -d -s producer "python3 /home/ec2-user/data_track_1/spark/pipeline/fms_producer.py"

# 2. Consumer (s1)
ssh s1 "
  tmux has-session -t consumer 2>/dev/null
  if [ \$? == 0 ]; then
    echo '🔄 consumer 세션이 이미 존재합니다. 재시작합니다...'
    tmux kill-session -t consumer
  fi

  echo '🚀 consumer 세션 시작 중...'
  tmux new-session -d -s consumer 'python3 /home/ec2-user/data_track_1/spark/pipeline/consumer.py'
"

# 3. Spark 전처리 (s1)
ssh s1 "
  tmux has-session -t spark_preprocess 2>/dev/null
  if [ \$? == 0 ]; then
    echo '🔄 spark_preprocess 세션이 이미 존재합니다. 재시작합니다...'
    tmux kill-session -t spark_preprocess
  fi

  echo '🚀 spark_preprocess 세션 시작 중...'
  tmux new-session -d -s spark_preprocess '
    spark-submit \
      --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.0,org.apache.hadoop:hadoop-aws:3.3.4 \
      /home/ec2-user/data_track_1/spark/pipeline/spark_preprocessing_streaming.py
  '
"

# 4. 메트릭 (s1)
ssh s1 "
  tmux has-session -t sensor_metric 2>/dev/null
  if [ \$? == 0 ]; then
    echo '🔄 sensor_metric 세션이 이미 존재합니다. 재시작합니다...'
    tmux kill-session -t sensor_metric
  fi

  echo '🚀 sensor_metric 세션 시작 중...'
  tmux new-session -d -s sensor_metric '
    spark-submit \
      --packages org.apache.hadoop:hadoop-aws:3.3.4 \
      /home/ec2-user/data_track_1/spark/pipeline/spark_s3_latest_to_prometheus.py
  '
"

# 5. 메트릭 - raw (s1)
ssh s1 "
  tmux has-session -t sensor_metric_raw 2>/dev/null
  if [ \$? == 0 ]; then
    echo '🔄 sensor_metric_raw 세션이 이미 존재합니다. 재시작합니다...'
    tmux kill-session -t sensor_metric_raw
  fi

  echo '🚀 sensor_metric_raw 세션 시작 중...'
  tmux new-session -d -s sensor_metric_raw '
    spark-submit \
      --packages org.apache.hadoop:hadoop-aws:3.3.4 \
      /home/ec2-user/data_track_1/spark/pipeline/spark_s3_raw_to_prometheus.py
  '
"