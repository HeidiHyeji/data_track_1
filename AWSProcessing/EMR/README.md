# EMR 구성

## (1) EMR 클러스터 사양
- 클러스터 이름: spark-cluster_new  
- EMR 버전: emr-6.15.0  
- 리전: ap-northeast-1 (아시아 도쿄)  
- 애플리케이션: Spark, Hadoop, Zeppelin, Livy  
- 키 페어 이름: key01  
- 로깅 위치: s3://awsprelab1/logs/  
- Bootstrap: Script s3://awsprelab1/bootstrap/bootstrap.sh  
- 설정 파일: /home/ec2-user/emr/configurations.json  

## (2) 인스턴스 사양

| 역할   | 인스턴스 타입 | 개수 | EBS 용량 (gp3)     |
|--------|---------------|------|--------------------|
| Master | c4.xlarge     | 1    | 32GB               |
| Core   | c4.xlarge     | 2    | 64GB (각 인스턴스) |

