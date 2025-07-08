#!/bin/bash

# sleep until cloud-init is finished
until [ -f /var/lib/cloud/instance/boot-finished ]; do
  sleep 1
done

# install net-tools (Amazon Linux uses yum or dnf)
dnf update -y
dnf install -y net-tools vim

# install prometheus
wget https://github.com/prometheus/prometheus/releases/download/v3.4.2/prometheus-3.4.2.linux-amd64.tar.gz
tar -xzf prometheus-3.4.2.linux-amd64.tar.gz
mv prometheus-3.4.2.linux-amd64 prometheus
cd prometheus

tmux new-session -d -s prometheus ./prometheus --config.file=prometheus.yml

# install grafana
wget https://dl.grafana.com/oss/release/grafana-12.0.2.linux-amd64.tar.gz
tar -zxf grafana-12.0.2.linux-amd64.tar.gz
mv grafana-v12.0.2 grafana
cd grafana

tmux new-session -d -s grafana ./bin/grafana-server web

# bashrc에 명령 추가 (원래 목적이 root shell 진입이면 다음과 같이 수정 필요함)
# echo "sudo -i" >> /home/ec2-user/.bashrc