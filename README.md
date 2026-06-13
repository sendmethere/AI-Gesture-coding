# AI Gesture Coding for Microteaching

A research-support tool that automatically analyzes a teacher's gestures in
microteaching videos and produces time-stamped gesture codes.
<br>마이크로티칭 영상에서 교사의 제스처를 자동으로 분석하여 시간대별 제스처 코드를
생성하는 연구 지원 도구입니다.

## Demo Video / 데모 영상

[![Demo video](https://img.youtube.com/vi/ZcG5vBY9zgw/maxresdefault.jpg)](https://youtu.be/ZcG5vBY9zgw)

> Click the thumbnail to play on YouTube. (GitHub READMEs do not support inline
> video playback, so a thumbnail-link is used.)
> <br>썸네일을 클릭하면 YouTube에서 재생됩니다. (GitHub README는 인라인 영상
> 재생을 지원하지 않아 썸네일 링크 방식을 사용합니다.)

## Features / 주요 기능

- Load videos (mp4 / mov / avi / mkv) and play them in the built-in player.
  <br>영상 불러오기 (mp4 / mov / avi / mkv) + 내장 플레이어 재생
- Extract frames every 0.5s → combine 6 frames (=3s) horizontally into a strip → analyze with an LLM vision model.
  <br>0.5초 간격 프레임 추출 → 6프레임(=3초) 수평 결합(strip) → LLM Vision 분석
- YOLO-based automatic teacher detection/cropping (10% padding on each side; falls back to the full frame if not installed).
  <br>YOLO 기반 교사 자동 검출/크롭 (상하좌우 10% 여유 패딩, 미설치 시 전체 프레임으로 자동 대체)
- Real-time results and progress (polling-based).
  <br>실시간 분석 결과/진행률 표시 (폴링 방식)
- **Click-to-edit results interface** so researchers can correct the auto-coded output.
  <br>**분석 결과 클릭 수정 인터페이스** (자동 코딩 결과를 연구자가 직접 보정)
- **Overview modal**: review the strip images sent to the AI together with their codes in one scrollable view.
  <br>**Overview 모달**: AI에 보낸 strip 이미지 + 코드를 한눈에 스크롤 검토
- Per-row 🖼 button to preview a single segment's strip.
  <br>행별 🖼 버튼으로 해당 구간 strip 단독 미리보기
- User-definable gesture schema (JSON), editable in-app and applied immediately.
  <br>제스처 분류체계(JSON) 사용자 정의 (앱 안에서 편집, 즉시 반영)
- Analysis-range control: **start point (min:sec)**, **length limit (sec)**, **min confidence (below → None)**.
  <br>분석 범위 제어: **시작 지점(분:초)**, **길이 제한(초)**, **최소 신뢰도(이하 None 처리)**
- CSV export (with optional confidence column).
  <br>CSV 내보내기 (confidence 옵션 포함)
- Choose an LLM provider: **Mock (no key) / OpenAI / Anthropic / Gemini**.
  <br>LLM Provider 선택: **Mock(키 불필요) / OpenAI / Anthropic / Gemini**
- **Korean/English GUI toggle** (top-right) and automatic API-key saving.
  <br>**GUI 한국어/영어 토글** (우측 상단), API Key 자동 저장
- The prompt sent to the LLM is entirely in English (including gesture descriptions).
  <br>LLM에 보내는 프롬프트는 전부 영어 (제스처 설명 포함)

## Tech Stack / 기술 스택

- Backend: Python + FastAPI (analysis runs in a background thread; results stream via polling).
  <br>백엔드: Python + FastAPI (분석은 백그라운드 스레드, 결과는 폴링으로 스트리밍)
- Desktop window: pywebview (native window, automatic browser fallback).
  <br>데스크톱 창: pywebview (네이티브 창, 실패 시 브라우저 자동 대체)
- Vision/Video: OpenCV, Pillow, (optional) Ultralytics YOLO.
  <br>비전/영상: OpenCV, Pillow, (선택) Ultralytics YOLO
- Frontend: build-free vanilla HTML/CSS/JS (built-in i18n).
  <br>프론트엔드: 빌드 불필요한 순수 HTML/CSS/JS (i18n 내장)

## Installation / 설치

```bash
cd teacher-gesture-coder
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt

# (Optional, recommended) YOLO teacher detection / (선택·권장) 교사 자동 검출(YOLO)
pip install -r requirements-yolo.txt   # downloads yolov8n.pt on first run / 첫 실행 시 yolov8n.pt 자동 다운로드
```

> Note: `pywebview` is included in `requirements.txt`. If it is not installed,
> the app automatically falls back to the browser instead of a native window.
> <br>참고: `requirements.txt`에 `pywebview`가 포함됩니다. 설치하지 않으면 네이티브
> 창 대신 자동으로 브라우저로 폴백합니다.

## Run / 실행

```bash
python run.py                 # native window (browser fallback) / 네이티브 창 (실패 시 브라우저)
python run.py --browser       # force the browser / 브라우저로 강제 실행
python run.py --no-window     # server only (http://127.0.0.1:8765) / 서버만 실행
```

## Quick Start (test without an API key) / 빠른 시작 (API 키 없이 테스트)

1. Launch the app. / 앱을 실행합니다.
2. Under **2. LLM Settings → Provider = "Mock"** (no key needed). / **2. LLM 설정 → Provider = "Mock"** 으로 둡니다. (키 불필요)
3. Load a microteaching video via **Select Video**. / **영상 선택**으로 마이크로티칭 영상을 불러옵니다.
4. Adjust start point / length / min confidence in **Analysis Options** (default: first 60s). / **분석 옵션**에서 시작 지점/길이/최소 신뢰도를 조정합니다. (기본: 처음 60초)
5. **Start** → the results tab on the right fills in real time. / **분석 시작** → 우측 결과 탭이 실시간으로 채워집니다.
6. Click a Gesture cell to edit the codes; use 🖼 / **Overview** to see the images sent to the AI. / 결과의 Gesture 셀을 클릭하면 분류를 수정할 수 있고, 🖼 / **Overview** 로 AI 입력 이미지를 볼 수 있습니다.
7. Save with **Export CSV** → `results/gesture_result.csv`. / **CSV 내보내기**로 `results/gesture_result.csv` 저장.

For real analysis, switch the provider to OpenAI/Anthropic/Gemini, enter the API
key (auto-saved) and the model name, then proceed the same way.
<br>실제 분석은 Provider를 OpenAI/Anthropic/Gemini로 바꾸고 API Key(자동 저장)와
모델명을 입력한 뒤 동일하게 진행합니다.

### Recommended Models (vision-capable) / 권장 모델 (비전 지원)

- OpenAI: `gpt-4o-mini` (testing), `gpt-4o` / `gpt-4o-mini`(테스트), `gpt-4o`
- Anthropic: `claude-sonnet-4-6`, etc. / `claude-sonnet-4-6` 등
- Gemini: `gemini-1.5-flash`, etc. / `gemini-1.5-flash` 등

> If the model ID is wrong or a parameter is rejected, the actual provider error
> (e.g., `openai 400: ...`) is shown verbatim in the right-side **Log tab**.
> <br>모델 ID가 틀리거나 파라미터가 안 맞으면 우측 **로그 탭**에 공급자가 보낸 실제
> 에러 메시지(예: `openai 400: ...`)가 그대로 표시됩니다.

## Editing the Gesture Schema / 제스처 분류체계 편집

Edit `config/gesture_schema.json` directly, or use **3. Gesture Schema → Edit
JSON** in the app. Changes apply immediately. Each `description` is fed verbatim
into the LLM prompt, so clearer distinguishing descriptions yield better accuracy.
<br>`config/gesture_schema.json` 을 직접 수정하거나, 앱의 **3. 제스처 분류체계 →
JSON 편집**에서 추가/변경할 수 있습니다. 저장 즉시 반영됩니다. 설명(description)은
그대로 LLM 프롬프트에 들어가므로, 구분 기준을 설명에 명확히 적을수록 정확해집니다.

```json
{ "gestures": [ { "name": "PointScreen", "description": "Pointing at a specific part of the screen/board." } ] }
```

Current default schema (16 codes) / 현재 기본 분류체계(16종): `Deictic, PointScreen,
PointAudience, Beat, Iconic, Metaphoric, Emblematic, OpenPalm, OpenPalmAudience,
RaiseHand, Writing, LookAtScreen, TurnBack, Cohesive, Nodding, HeadShake`

## Directory Structure / 디렉토리 구조

```
teacher-gesture-coder/
├── run.py                  # entry point: server + native window / 실행 진입점 (서버 + 네이티브 창)
├── requirements.txt
├── requirements-yolo.txt   # optional: YOLO teacher detection / 선택: YOLO 교사 검출
├── README.md
├── backend/
│   ├── app.py              # FastAPI endpoints (+ video range streaming) / FastAPI 엔드포인트 (+ 영상 range streaming)
│   ├── pipeline.py         # analysis pipeline + job manager (background thread) / 분석 파이프라인 + 잡 매니저(백그라운드 스레드)
│   ├── detector.py         # YOLO teacher detection (graceful fallback, 10% pad) / YOLO 교사 검출 (graceful fallback, 10% 패딩)
│   ├── llm.py              # OpenAI/Anthropic/Gemini/Mock vision calls (English prompt) / 비전 호출(영어 프롬프트)
│   ├── schema_store.py     # load/save gesture schema / 제스처 분류체계 로드/저장
│   ├── settings_store.py   # settings persistence / 설정 저장
│   ├── csv_export.py       # CSV output / CSV 출력
│   └── paths.py
├── frontend/               # index.html / styles.css / app.js (i18n built in / i18n 내장)
├── config/
│   ├── gesture_schema.json
│   └── settings.json       # created at runtime; stores API key locally; git-ignored / 실행 시 생성, API Key 로컬 저장, git-ignored
├── videos/  crops/  strips/  results/  logs/   # created at runtime / 실행 시 생성
```

## Notes / 참고

- `config/settings.json` stores the provider/model/analysis options and the API key locally (git-ignored).
  <br>`config/settings.json` 에 Provider/Model/분석옵션 및 API Key가 로컬 저장됩니다(.gitignore 처리).
- Teacher detection uses a "largest person box = teacher" heuristic; it can mis-detect when a student appears larger (future work: person tracking).
  <br>교사 검출은 "화면에서 가장 큰 사람 박스 = 교사" 휴리스틱입니다. 학생이 더 크게 잡히는 구간에선 오검출 가능 (향후 인물 추적으로 개선 여지).
- Roadmap: confidence visualization, gesture-frequency analysis, multi-coder comparison, automatic Cohen's Kappa, etc.
  <br>향후 계획: Confidence 시각화, 제스처 빈도 분석, 다중 코더 비교, Cohen's Kappa 자동 계산 등.
