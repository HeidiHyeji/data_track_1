#!/bin/bash

# EMR 클러스터 생성 스크립트
# Usage: ./create-emr-cluster.sh [cluster-name] [key-pair-name] [subnet-id]

set -e

CLUSTER_NAME=${1:-"spark-cluster"}
KEY_NAME=${2:-"key01"}
SUBNET_ID=${3:-"subnet-0a756fb6fd771404a"}
LOG_BUCKET=${4:-"awsprelab1"}

echo "Creating EMR cluster: $CLUSTER_NAME"

aws emr create-cluster \
  --applications Name=Hadoop Name=Spark Name=Zeppelin Name=Livy \
  --ec2-attributes KeyName=$KEY_NAME,InstanceProfile=EMR_EC2_DefaultRole,SubnetId=$SUBNET_ID \
  --service-role EMR_DefaultRole \
  --enable-debugging \
  --log-uri s3://$LOG_BUCKET/logs/ \
  --name "$CLUSTER_NAME" \
  --instance-groups '[
    {
      "InstanceCount": 1,
      "EbsConfiguration": {
        "EbsBlockDeviceConfigs": [{
          "VolumeSpecification": {
            "SizeInGB": 32,
            "VolumeType": "gp3"
          },
          "VolumesPerInstance": 1
        }]
      },
      "InstanceGroupType": "MASTER",
      "InstanceType": "c4.xlarge",
      "Name": "masterGroup"
    },
    {
      "InstanceCount": 2,
      "EbsConfiguration": {
        "EbsBlockDeviceConfigs": [{
          "VolumeSpecification": {
            "SizeInGB": 64,
            "VolumeType": "gp3"
          },
          "VolumesPerInstance": 1
        }]
      },
      "InstanceGroupType": "CORE",
      "InstanceType": "c4.xlarge",
      "Name": "coreGroup"
    }
  ]' \
  --configurations file:///home/ec2-user/emr/configurations.json \
  --bootstrap-actions Path=s3://$LOG_BUCKET/bootstrap/bootstrap.sh,Name="Custom Bootstrap" \
  --region ap-northeast-1 \
  --release-label emr-6.15.0

echo "EMR cluster creation initiated. Check AWS console for status."
