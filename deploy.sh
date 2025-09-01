#!/bin/bash
set -e

APP_DIR="$HOME/erp"
VENV_DIR="$APP_DIR/.venv"
DB_FILE="$APP_DIR/erp.db"
PORT=9090
LOG_FILE="$APP_DIR/erp.log"

echo "[1/6] 프로젝트 디렉토리 확인"
mkdir -p "$APP_DIR"
cd "$APP_DIR"

echo "[2/6] 가상환경 설정"
if [ ! -d "$VENV_DIR" ]; then
python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install flask flask_sqlalchemy gunicorn

echo "[3/6] DB 초기화"
if [ ! -f "$DB_FILE" ]; then
python3 - <<PYCODE
from app import db
db.create_all()
print("DB 생성 완료")
PYCODE
else
echo "DB 이미 존재: $DB_FILE"
fi

echo "[4/6] Gunicorn 실행 (포트 $PORT)"
pkill -f "gunicorn.*:$PORT" || true
nohup "$VENV_DIR/bin/gunicorn" -w 4 -b 0.0.0.0:$PORT app:app > "$LOG_FILE" 2>&1 &

echo "[5/6] 상태 확인"
sleep 2
if curl -sf http://127.0.0.1:$PORT
 >/dev/null; then
echo "✅ ERP 실행 성공: http://<서버IP>:$PORT"
else
echo "❌ 실행 실패. tail -n 50 $LOG_FILE 확인"
fi

echo "[6/6] 완료"
