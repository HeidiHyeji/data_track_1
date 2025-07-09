#!/bin/bash

GRAFANA_URL="http://localhost:3000"
GRAFANA_USER="admin"
GRAFANA_PASSWORD="admin"  # 필요시 수정
SERVICE_ACCOUNT_NAME="auto-import-sa"
JSON_FILES=("1860_rev41.json" "fms_dashboard.json")
FOLDER_ID=0
OVERWRITE=true

# jq 설치 확인
if ! command -v jq &> /dev/null; then
  echo "❗ 'jq'가 설치되어 있지 않습니다. 설치 후 다시 실행하세요."
  exit 1
fi

echo "[1] Check or Create Service Account..."
EXISTING_SA=$(curl -s -u "$GRAFANA_USER:$GRAFANA_PASSWORD" "$GRAFANA_URL/api/serviceaccounts" \
  | jq -r ".[] | select(.name==\"$SERVICE_ACCOUNT_NAME\")")

if [[ -n "$EXISTING_SA" ]]; then
  SA_ID=$(echo "$EXISTING_SA" | jq -r '.id')
  echo "🔁 기존 서비스 계정 사용 (ID: $SA_ID)"
else
  SA_RESPONSE=$(curl -s -X POST "$GRAFANA_URL/api/serviceaccounts" \
    -u "$GRAFANA_USER:$GRAFANA_PASSWORD" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"$SERVICE_ACCOUNT_NAME\", \"role\": \"Admin\"}")
  
  SA_ID=$(echo "$SA_RESPONSE" | jq -r '.id')
  
  if [[ -z "$SA_ID" || "$SA_ID" == "null" ]]; then
    echo "❌ 서비스 계정 생성 실패"
    echo "응답: $SA_RESPONSE"
    exit 1
  fi
  echo "✅ 새 서비스 계정 생성 완료 (ID: $SA_ID)"
fi

echo "[2] Create API Token for Service Account..."
TOKEN_RESPONSE=$(curl -s -X POST "$GRAFANA_URL/api/serviceaccounts/$SA_ID/tokens" \
  -u "$GRAFANA_USER:$GRAFANA_PASSWORD" \
  -H "Content-Type: application/json" \
  -d '{"name":"auto-import-token"}')

API_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.key')

if [[ -z "$API_TOKEN" || "$API_TOKEN" == "null" ]]; then
  echo "❌ 토큰 생성 실패"
  echo "응답: $TOKEN_RESPONSE"
  exit 1
fi

echo "✅ 토큰 생성 완료"

echo "[3] Import Dashboards..."

for JSON_FILE in "${JSON_FILES[@]}"; do
  echo "📄 대시보드 파일: $JSON_FILE 임포트 중..."

  if [[ ! -f "$JSON_FILE" ]]; then
    echo "❗ 파일이 존재하지 않습니다: $JSON_FILE"
    continue
  fi

  jq -n \
    --slurpfile dashboard "$JSON_FILE" \
    --argjson folderId "$FOLDER_ID" \
    --argjson overwrite "$OVERWRITE" \
    '{dashboard: $dashboard[0], folderId: $folderId, overwrite: $overwrite}' > /tmp/dashboard_post.json

  IMPORT_RESPONSE=$(curl -s -X POST "$GRAFANA_URL/api/dashboards/db" \
    -H "Authorization: Bearer $API_TOKEN" \
    -H "Content-Type: application/json" \
    -d @/tmp/dashboard_post.json)

  if echo "$IMPORT_RESPONSE" | grep -q '"status":"success"'; then
    echo "✅ $JSON_FILE 임포트 성공"
  else
    echo "❌ $JSON_FILE 임포트 실패"
    echo "응답: $IMPORT_RESPONSE"
  fi
done
