#!/bin/bash

# 1. Producer (i1)
tmux has-session -t producer 2>/dev/null
if [ $? != 0 ]; then
  tmux new-session -d -s producer "python3 /home/ec2-user/data_track_1/spark/pipeline/fms_producer.py"
else
  echo "⚠️ producer 세션이 이미 존재합니다. 건너뜁니다."
fi

# 2. Consumer (s1)
ssh s1 "
  tmux has-session -t consumer 2>/dev/null
  if [ \$? != 0 ]; then
    tmux new-session -d -s consumer 'python3 /home/ec2-user/data_track_1/spark/pipeline/consumer.py'
  else
    echo '⚠️ consumer 세션이 이미 존재합니다. 건너뜁니다.'
  fi
"

# 3. Spark 전처리 (s1)
ssh s1 "
  tmux has-session -t spark_preprocess 2>/dev/null
  if [ \$? != 0 ]; then
    tmux new-session -d -s spark_preprocess '
      spark-submit \
        --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.0,org.apache.hadoop:hadoop-aws:3.3.4 \
        /home/ec2-user/data_track_1/spark/pipeline/spark_preprocessing_streaming.py
    '
  else
    echo '⚠️ spark_preprocess 세션이 이미 존재합니다. 건너뜁니다.'
  fi
"
