시스템 아키텍처
 ``` ┌──────────────────────────────────┐ 
 │ i1 : Ansible, Terraform, kafka │
└──────────────────────────────────┘
│ │ │
▼ ▼ ▼
┌────┐ ┌────┐ ┌────┐
│ s1 │ │ s2 │ │ s3 │
└────┘ └────┘ └────┘ ``

1. 환경변수 설정
   ```
   export TF_VAR_AWS_ACCESS_KEY= Access key 입력 
   export TF_VAR_AWS_SECRET_KEY= Secret key 입력
   ```
2. i1 키 생성
   ```
   ssh-keygen -f ~/.ssh/id_rsa -N ''
   ```
3. Terraform 실행
   ```
     cd /home/ec2-user/data_track_1/Terraform
     terraform init
     terraform apply --auto-approve
   ```


4. Host 세팅
   ```
     ./doSetHosts.sh
   ```
