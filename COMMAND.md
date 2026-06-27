# 실행 명령어

백엔드(FastAPI)와 프론트엔드는 한 프로세스입니다 — `run.py`가 둘 다 띄웁니다.

## 한 줄 실행 (가상환경 활성화 + 실행)

macOS / Linux:

```bash
source .venv/bin/activate && python run.py
```

Windows (PowerShell):

```powershell
.venv\Scripts\activate; python run.py
```

## 옵션

```bash
python run.py            # 네이티브 창 (실패 시 브라우저로 폴백)
python run.py --browser  # 브라우저로 강제 실행
python run.py --no-window # 서버만 → http://127.0.0.1:8765
```

> 처음이라면 먼저 설치: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt` (자세한 건 README.md).
