# **11. 시각화 및 모니터링**

## 개요
인스턴스의 상태와 센서 값을 모니터링

## 인스턴스에 Node Exporter 설치
```bash
git clone git@github.com:HeidiHyeji/data_track_1.git
ansible-playbook -i /home/ec2-user/data_track_1/Ansible/df/i1/ansible-node_exporter/hosts /home/ec2-user/data_track_1/Ansible/df/i1 ansible-node_exporter/node_exporter_install.yml
```

## 코드 실행 방법
```bash
git clone git@github.com:HeidiHyeji/data_track_1.git
cd visualization
terraform init
terraform apply
```