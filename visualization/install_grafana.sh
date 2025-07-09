#!/bin/bash

set -e

echo "=== Grafana 설치 시작 (Amazon Linux 2) ==="

# Grafana 저장소 설정
sudo tee /etc/yum.repos.d/grafana.repo <<EOF
[grafana]
name=Grafana OSS
baseurl=https://packages.grafana.com/oss/rpm
repo_gpgcheck=1
enabled=1
gpgcheck=1
gpgkey=https://packages.grafana.com/gpg.key
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
EOF

# 패키지 캐시 업데이트
sudo yum -y update

# Grafana 설치
sudo yum install -y grafana

# Grafana 서비스 활성화 및 시작
sudo systemctl enable grafana-server
sudo systemctl start grafana-server

# 상태 확인
sudo systemctl status grafana-server --no-pager

echo "✅ Grafana 설치 완료!"
echo "👉 웹 브라우저에서 접속: http://<서버_IP>:3000"
echo "🔑 기본 로그인: admin / admin"
