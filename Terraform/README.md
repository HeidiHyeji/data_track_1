# AWS 인프라 자동화 가이드 (Terraform & Ansible)

이 문서는 Terraform과 Ansible을 활용한 AWS 인프라 구축 및 운영 자동화 절차를 안내합니다.

## 아키텍처 개요
```
 ┌──────────────────────────────────┐ 
 │ i1 : Ansible, Terraform          │
 └──────────────────────────────────┘
            │      │      │
            ▼      ▼      ▼
         ┌────┐ ┌────┐ ┌────┐
         │ s1 │ │ s2 │ │ s3 │                
         └────┘ └────┘ └────┘
```

### 공통 인프라 사양
- **리전**: ap-northeast-1 (도쿄)
- **AMI**: ami-03598bf9d15814511 (Amazon Linux 2023)
- **키페어**: key01.pem
- **보안 그룹**: sg-05eae1c95fcd567c8 (SSH 허용)
- **인스턴스 타입**: t2.large (2 vCPU, 8GB RAM)
- **스토리지**: EBS 100GB
- **네트워크**: 퍼블릭 IP 할당

---

## 구축 및 운영 절차

1. **AWS 인증 정보 환경변수 설정**
   ```bash
   export TF_VAR_AWS_ACCESS_KEY=AccessKey값
   export TF_VAR_AWS_SECRET_KEY=SecretKey값
   ```

2. **SSH 키 생성**
   ```bash
   ssh-keygen -f ~/.ssh/id_rsa -N ''
   ```

3. **Terraform을 통한 인프라 생성**
   ```bash
   cd /home/ec2-user/data_track_1/Terraform
   terraform init
   terraform apply --auto-approve
   ```

4. **호스트 정보 세팅**
   ```bash
   ./doSetHosts.sh
   ```

---
