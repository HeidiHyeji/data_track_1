# Kafka/Spark 스트리밍 연동

## 코드 실행 요구사항

```bash
# s1에 pyspark 설치 필요
ssh s1 pip install pyspark
ssh s1 pip install prometheus_client
```

## 스트리밍 코드 실행방법

```bash
# [주의] git clone 후 실행해야 함
scp ~/bigd6_prelab_team3/Pipeline/kafka-spark-streaming.py s1:\kafka-spark-streaming.py
scp ~/bigd6_prelab_team3/Pipeline/prometheus_exporter.py s1:\prometheus_exporter.py
scp ~/bigd6_prelab_team3/Pipeline/HDFSStorageManager.py s1:\HDFSStorageManager.py
ssh s1 tmux kill-session -t raw-data-stream
ssh s1 tmux new-session -d -s raw-data-stream 'spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0,io.delta:delta-core_2.12:2.4.0 kafka-spark-streaming.py'
```

## RAW 데이터 체크

```bash
scp ~/bigd6_prelab_team3/Pipeline/check-raw-data.py s1:\check-raw-data.py
ssh s1 spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0 check-raw-data.py
```

## 전처리된 데이터 체크

```bash
scp ~/bigd6_prelab_team3/Pipeline/check-processed-data.py s1:\check-processed-data.py
ssh s1 spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0,io.delta:delta-core_2.12:2.4.0 check-processed-data.py
```

## 주의사항

* 사전에 zookeeper, kafka, spark가 실행되고 있어야 함
