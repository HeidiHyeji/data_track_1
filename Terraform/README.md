# IaC를 위한 시스템 아키텍처
 ``` ┌──────────────────────────────────┐ 
     │ i1 : Ansible, Terraform          │
     └──────────────────────────────────┘
                │      │      │
                ▼      ▼      ▼
             ┌────┐ ┌────┐ ┌────┐
             │ s1 │ │ s2 │ │ s3 │                
             └────┘ └────┘ └────┘
```

1. 공통 스펙
  리전: ap-northeast-1 (아시아 도쿄)
  AMI: ami-03598bf9d15814511 (Amazon Linux 2023)
  키페어: key01.pem
  보안 그룹: sg-05eae1c95fcd567c8 (ssh-allow)
  인스턴스 유형: t2.large (2 vCPU, 8GB RAM)
  스토리지: EBS 100GB
  네트워크: 퍼블릭 IP 할당됨

# 수행 프로세스
  1) 환경변수 설정
   ```
   export TF_VAR_AWS_ACCESS_KEY= Access key 입력 
   export TF_VAR_AWS_SECRET_KEY= Secret key 입력
   ```
  2) i1 키 생성
   ```
   ssh-keygen -f ~/.ssh/id_rsa -N ''
   ```
  3). Terraform 실행
   ```
     cd /home/ec2-user/data_track_1/Terraform
     terraform init
     terraform apply --auto-approve
  ```

 4) Host 세팅
   ```
     ./doSetHosts.sh
   ```


