# AI Gesture Coding for Microteaching

마이크로티칭 영상에서 교사의 제스처를 자동으로 분석하여 시간대별 제스처 코드를
생성하는 연구 지원 도구입니다. (plan.md 기반 구현)

## 주요 기능

- 영상 불러오기 (mp4 / mov / avi / mkv) + 내장 플레이어 재생
- 0.5초 간격 프레임 추출 → 6프레임(=3초) 수평 결합(strip) → LLM Vision 분석
- YOLO 기반 교사 자동 검출/크롭 (상하좌우 10% 여유 패딩, 미설치 시 전체 프레임으로 자동 대체)
- 실시간 분석 결과/진행률 표시 (폴링 방식)
- **분석 결과 클릭 수정 인터페이스** (자동 코딩 결과를 연구자가 직접 보정)
- **Overview 모달**: AI에 보낸 strip 이미지 + 코드를 한눈에 스크롤 검토
- 행별 🖼 버튼으로 해당 구간 strip 단독 미리보기
- 제스처 분류체계(JSON) 사용자 정의 (앱 안에서 편집, 즉시 반영)
- 분석 범위 제어: **시작 지점(분:초)**, **길이 제한(초)**, **최소 신뢰도(이하 None 처리)**
- CSV 내보내기 (confidence 옵션 포함)
- LLM Provider 선택: **Mock(키 불필요) / OpenAI / Anthropic / Gemini**
- **GUI 한국어/영어 토글** (우측 상단), API Key 자동 저장
- LLM에 보내는 프롬프트는 전부 영어 (제스처 설명 포함)

## 기술 스택

- 백엔드: Python + FastAPI (분석은 백그라운드 스레드, 결과는 폴링으로 스트리밍)
- 데스크톱 창: pywebview (네이티브 창, 실패 시 브라우저 자동 대체)
- 비전/영상: OpenCV, Pillow, (선택) Ultralytics YOLO
- 프론트엔드: 빌드 불필요한 순수 HTML/CSS/JS (i18n 내장)

## 설치

```bash
cd teacher-gesture-coder
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# (선택·권장) 교사 자동 검출(YOLO):
pip install -r requirements-yolo.txt   # 첫 실행 시 yolov8n.pt 자동 다운로드
```

> 참고: `requirements.txt`에 `pywebview`가 포함됩니다. 설치하지 않으면 네이티브 창
> 대신 자동으로 브라우저로 폴백합니다.

## 실행

```bash
python run.py                 # 네이티브 창으로 실행 (실패 시 브라우저)
python run.py --browser       # 브라우저로 강제 실행
python run.py --no-window     # 서버만 실행 (http://127.0.0.1:8765)
```

## 빠른 시작 (API 키 없이 테스트)

1. 앱을 실행합니다.
2. **2. LLM 설정 → Provider = "Mock"** 으로 둡니다. (키 불필요)
3. **영상 선택**으로 마이크로티칭 영상을 불러옵니다.
4. **분석 옵션**에서 시작 지점/길이/최소 신뢰도를 조정합니다. (기본: 처음 60초)
5. **분석 시작** → 우측 결과 탭이 실시간으로 채워집니다.
6. 결과의 Gesture 셀을 클릭하면 분류를 수정할 수 있고, 🖼 / **Overview** 로 AI 입력 이미지를 볼 수 있습니다.
7. **CSV 내보내기**로 `results/gesture_result.csv` 저장.

실제 분석은 Provider를 OpenAI/Anthropic/Gemini로 바꾸고 API Key(자동 저장)와
모델명을 입력한 뒤 동일하게 진행합니다.

### 권장 모델 (비전 지원)

- OpenAI: `gpt-4o-mini`(테스트), `gpt-4o`
- Anthropic: `claude-sonnet-4-6` 등
- Gemini: `gemini-1.5-flash` 등

> 모델 ID가 틀리거나 파라미터가 안 맞으면 우측 **로그 탭**에 공급자가 보낸 실제
> 에러 메시지(예: `openai 400: ...`)가 그대로 표시됩니다.

## 제스처 분류체계 편집

`config/gesture_schema.json` 을 직접 수정하거나, 앱의 **3. 제스처 분류체계 →
JSON 편집**에서 추가/변경할 수 있습니다. 저장 즉시 반영됩니다. 설명(description)은
그대로 LLM 프롬프트에 들어가므로, 구분 기준을 설명에 명확히 적을수록 정확해집니다.

```json
{ "gestures": [ { "name": "PointScreen", "description": "Pointing at a specific part of the screen/board." } ] }
```

현재 기본 분류체계(16종): `Deictic, PointScreen, PointAudience, Beat, Iconic,
Metaphoric, Emblematic, OpenPalm, OpenPalmAudience, RaiseHand, Writing,
LookAtScreen, TurnBack, Cohesive, Nodding, HeadShake`

## 디렉토리 구조

```
teacher-gesture-coder/
├── run.py                  # 실행 진입점 (서버 + 네이티브 창)
├── requirements.txt
├── requirements-yolo.txt   # 선택: YOLO 교사 검출
├── README.md  /  HANDOFF.md  /  plan.md
├── backend/
│   ├── app.py              # FastAPI 엔드포인트 (+ 영상 range streaming)
│   ├── pipeline.py         # 분석 파이프라인 + 잡 매니저(백그라운드 스레드)
│   ├── detector.py         # YOLO 교사 검출 (graceful fallback, 10% 패딩)
│   ├── llm.py              # OpenAI/Anthropic/Gemini/Mock 비전 호출(영어 프롬프트)
│   ├── schema_store.py     # 제스처 분류체계 로드/저장
│   ├── settings_store.py   # 설정 저장
│   ├── csv_export.py       # CSV 출력
│   └── paths.py
├── frontend/               # index.html / styles.css / app.js (i18n 내장)
├── config/
│   ├── gesture_schema.json
│   └── settings.json       # (실행 시 생성, API Key 로컬 저장, git-ignored)
├── videos/  crops/  strips/  results/  logs/   (실행 시 생성)
```

## 참고

- `config/settings.json` 에 Provider/Model/분석옵션 및 API Key가 로컬 저장됩니다(.gitignore 처리).
- 교사 검출은 "화면에서 가장 큰 사람 박스 = 교사" 휴리스틱입니다. 학생이 더 크게
  잡히는 구간에선 오검출 가능 (향후 인물 추적으로 개선 여지).
- 향후 계획(Confidence 시각화, 빈도 분석, 다중 코더 비교, Cohen's Kappa 등)은
  plan.md 12절 및 HANDOFF.md 참고.
