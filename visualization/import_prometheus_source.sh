#!/bin/bash

GRAFANA_URL="http://localhost:3000"
GRAFANA_USER="admin"
GRAFANA_PASS="admin"

DATASOURCE_NAME="Prometheus"
PROMETHEUS_URL="http://localhost:9090"

# 데이터소스가 이미 있는지 체크
EXISTING_DS_ID=$(curl -s -u $GRAFANA_USER:$GRAFANA_PASS "$GRAFANA_URL/api/datasources" | jq -r ".[] | select(.name==\"$DATASOURCE_NAME\") | .id")

if [ -n "$EXISTING_DS_ID" ]; then
  echo "데이터소스 '$DATASOURCE_NAME' 이(가) 이미 존재합니다. ID: $EXISTING_DS_ID"
  exit 0
fi

# 새 데이터소스 JSON 생성
read -r -d '' DS_JSON <<EOF
{
  "name": "$DATASOURCE_NAME",
  "type": "prometheus",
  "access": "proxy",
  "url": "$PROMETHEUS_URL",
  "basicAuth": false,
  "isDefault": true,
  "version": 1,
  "editable": true
}
EOF

# 데이터소스 추가 API 호출
response=$(curl -s -w "\n%{http_code}" -u $GRAFANA_USER:$GRAFANA_PASS -X POST \
  -H "Content-Type: application/json" \
  -d "$DS_JSON" \
  "$GRAFANA_URL/api/datasources")

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n -1)

if [ "$http_code" = "200" ]; then
  echo "데이터소스 '$DATASOURCE_NAME' 가 성공적으로 추가되었습니다."
else
  echo "데이터소스 추가 실패. HTTP 상태코드: $http_code"
  echo "응답 본문: $body"
fi
