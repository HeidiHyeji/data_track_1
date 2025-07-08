#!/bin/bash

# 이 스크립트는 'ec2:DescribeInstances' 권한을 가진 IAM 역할을 생성하고,
# 'Name=m1' 태그가 지정된 EC2 인스턴스에 연결합니다.

# --- 설정 ---
INSTANCE_NAME="m1"
ROLE_NAME="M1DescribeInstancesRole"
POLICY_NAME="M1DescribeInstancesPolicy"
INSTANCE_PROFILE_NAME="M1DescribeInstancesInstanceProfile"
TRUST_POLICY_FILE="ec2-trust-policy.json"
PERMISSION_POLICY_FILE="ec2-describe-policy.json"

# --- 1단계: EC2에 대한 신뢰 정책 생성 ---
echo "신뢰 정책 파일 생성 중: ${TRUST_POLICY_FILE}"
cat > ${TRUST_POLICY_FILE} <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "ec2.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# --- 2단계: IAM 역할 생성 ---
echo "IAM 역할 생성 중: ${ROLE_NAME}"
aws iam create-role \
  --role-name "${ROLE_NAME}" \
  --assume-role-policy-document file://${TRUST_POLICY_FILE}

# --- 3단계: 권한 정책 생성 ---
echo "권한 정책 파일 생성 중: ${PERMISSION_POLICY_FILE}"
cat > ${PERMISSION_POLICY_FILE} <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "ec2:DescribeInstances",
            "Resource": "*"
        }
    ]
}
EOF

# --- 4단계: IAM 정책 생성 및 ARN 가져오기 ---
echo "IAM 정책 생성 중: ${POLICY_NAME}"
POLICY_ARN=$(aws iam create-policy \
  --policy-name "${POLICY_NAME}" \
  --policy-document file://${PERMISSION_POLICY_FILE} \
  --query 'Policy.Arn' --output text)

if [ -z "${POLICY_ARN}" ]; then
    echo "IAM 정책 생성에 실패했습니다. 종료합니다."
    exit 1
fi
echo "정책 ARN: ${POLICY_ARN}"

# --- 5단계: 역할을 정책에 연결 ---
echo "역할에 정책 연결 중"
aws iam attach-role-policy \
  --role-name "${ROLE_NAME}" \
  --policy-arn "${POLICY_ARN}"

# --- 6단계: 인스턴스 프로파일 생성 ---
echo "인스턴스 프로파일 생성 중: ${INSTANCE_PROFILE_NAME}"
aws iam create-instance-profile \
  --instance-profile-name "${INSTANCE_PROFILE_NAME}"

# --- 7단계: 인스턴스 프로파일에 역할 추가 ---
echo "인스턴스 프로파일에 역할 추가 중"
aws iam add-role-to-instance-profile \
  --instance-profile-name "${INSTANCE_PROFILE_NAME}" \
  --role-name "${ROLE_NAME}"

# --- 8단계: 인스턴스 ID 가져오기 ---
echo "Name=${INSTANCE_NAME} 태그가 지정된 인스턴스의 ID를 가져오는 중"
INSTANCE_ID=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=${INSTANCE_NAME}" \
  --query "Reservations[].Instances[].InstanceId" \
  --output text)

if [ -z "${INSTANCE_ID}" ]; then
    echo "Name=${INSTANCE_NAME} 태그를 가진 인스턴스를 찾을 수 없습니다. 종료합니다."
    # 생성된 리소스 정리
    aws iam detach-role-policy --role-name "${ROLE_NAME}" --policy-arn "${POLICY_ARN}"
    aws iam delete-policy --policy-arn "${POLICY_ARN}"
    aws iam remove-role-from-instance-profile --instance-profile-name "${INSTANCE_PROFILE_NAME}" --role-name "${ROLE_NAME}"
    aws iam delete-instance-profile --instance-profile-name "${INSTANCE_PROFILE_NAME}"
    aws iam delete-role --role-name "${ROLE_NAME}"
    rm ${TRUST_POLICY_FILE} ${PERMISSION_POLICY_FILE}
    exit 1
fi
echo "인스턴스 ID: ${INSTANCE_ID}"

# --- 9단계: EC2 인스턴스와 인스턴스 프로파일 연결 ---
# 인스턴스 프로파일이 사용 가능해질 때까지 잠시 대기해야 합니다.
echo "인스턴스 프로파일이 준비될 때까지 대기 중..."
sleep 10

echo "인스턴스에 인스턴스 프로파일 연결 중"
aws ec2 associate-iam-instance-profile \
  --instance-id "${INSTANCE_ID}" \
  --iam-instance-profile Name="${INSTANCE_PROFILE_NAME}"

# --- 10단계: 임시 파일 정리 ---
echo "임시 정책 파일 정리 중"
rm ${TRUST_POLICY_FILE} ${PERMISSION_POLICY_FILE}

echo "성공적으로 IAM 역할을 생성하고 ${INSTANCE_NAME} 인스턴스에 연결했습니다."
