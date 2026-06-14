# AI Gesture Coding for Microteaching

A research-support desktop tool that automatically analyzes a teacher's gestures
in microteaching videos and produces time-stamped, McNeill-typed gesture codes —
with a skeleton-based motion pre-filter that saves AI tokens and optional
per-window speech transcription.
<br>마이크로티칭 영상에서 교사의 제스처를 자동 분석해 시간대별 McNeill 유형 코드를
생성하는 연구 지원 데스크톱 도구입니다. 골격 기반 모션 사전필터로 AI 토큰을 절감하고,
윈도우별 발화 전사(STT)를 선택적으로 제공합니다.

## Demo Video / 데모 영상

[![Demo video](https://img.youtube.com/vi/ZcG5vBY9zgw/maxresdefault.jpg)](https://youtu.be/ZcG5vBY9zgw)

> Click the thumbnail to play on YouTube. (GitHub READMEs do not support inline
> video playback, so a thumbnail-link is used.)
> <br>썸네일을 클릭하면 YouTube에서 재생됩니다. (GitHub README는 인라인 영상 재생을
> 지원하지 않아 썸네일 링크 방식을 사용합니다.)

---

## How It Works / 작동 방식

The video is split into fixed-length **windows** (N frames at a set interval).
Each window is processed in this order:
<br>영상을 고정 길이 **윈도우**(일정 간격 N프레임)로 나눠 각 윈도우를 다음 순서로
처리합니다:

1. **Detect + crop the teacher** (YOLO, 20% padding) and stitch the frames into one horizontal **strip** image.
   <br>**교사 검출·크롭**(YOLO, 20% 패딩) 후 프레임을 가로로 이어 **strip** 이미지 생성
2. **Measure hand motion** (YOLO-pose): wrist displacement normalized by shoulder width, median-smoothed to remove keypoint jitter. A **colorbar + value** are drawn under each frame.
   <br>**손 이동량 측정**(YOLO-pose): 어깨너비로 정규화한 손목 이동량을 median 평활화로 지터 제거 후 계산. 프레임 하단에 **컬러바·수치** 표기
3. **Grade the window** and decide whether the AI is needed:
   <br>**등급 판정** 후 AI 호출 여부 결정:
   - **C (still)** — no frame reaches the *start threshold* → auto-coded *no gesture* (`GT-N`), **AI skipped → token saving**.
     <br>**C(정지)** — *시작 임계값*에 도달하는 프레임이 없음 → *제스처 없음*(`GT-N`) 자동 코딩, **AI 생략 → 토큰 절감**
   - **B** — pose tracking failed → AI judges (flagged for review). / 골격 추적 실패 → AI 판단(검토 플래그)
   - **A** — real motion present → AI classifies. / 실제 움직임 있음 → AI 분류
4. **(Optional) Transcribe speech** for the window (faster-whisper) and attach the sentence/words.
   <br>**(선택) 발화 전사**(faster-whisper)로 윈도우 발화 문장/단어 부착
5. **AI vision call** (A/B only): the AI receives the **strip image + motion colorbar + the window's speech text** and returns gesture codes + confidence. **Review flags** mark windows worth a manual check.
   <br>**AI 비전 호출**(A·B만): AI가 **strip 이미지 + 모션 컬러바 + 해당 윈도우 발화 텍스트**를 받아 코드+신뢰도 산출. **검토 플래그**로 수동 확인 권장 구간 표시

Colorbar legend / 컬러바 범례: **gray** still 정지 · **yellow** preparing 준비 ·
**green** gesture start 시작 · **blue** in motion 진행. The number is the
normalized hand displacement. / 숫자는 정규화 손 이동량입니다.

> Token saving is content-dependent: gesture-heavy stretches skip little; lessons
> with much standing/listening/board-writing skip far more.
> <br>토큰 절감률은 내용에 따라 다릅니다 — 제스처가 많은 구간은 거의 안 건너뛰고,
> 서서 설명·경청·판서가 많은 수업일수록 절감이 큽니다.

## Gesture Codes (McNeill typology) / 제스처 코드 (McNeill 유형)

| Code | Type | AI judgment basis / AI 판단 근거 |
|---|---|---|
| `GT-D` | Deictic / 지시적 | Fingertip/hand extends toward a target and holds / 손끝이 특정 방향·대상으로 뻗고 정지 |
| `GT-I` | Iconic / 상징적 | Depicts a concrete object's shape, **size**, or motion (e.g. hands/body widening for "big", hunching for "small") / 구체적 대상의 형태·**크기**·움직임 모방(예: 큼=몸·손 벌리기, 작음=움츠리기) |
| `GT-M` | Metaphoric / 은유적 | Gives an abstract idea spatial form (palm-presenting, left/right contrast, up=more, weighing options) / 추상 개념에 공간적 형태 부여(손바닥 제시, 좌우 대비, 위=증가, 저울질 등) |
| `GT-B` | Beat / 박자적 | Short, repeated strokes in rhythm with speech / 발화 리듬에 맞춘 짧고 반복적 동작 |
| `GT-E` | Emblematic / 관습적 | Culturally fixed sign (raised hand, thumbs-up, OK) / 문화적으로 표준화된 사인(손들기 등) |
| `GT-N` | No gesture / 제스처 없음 | No meaningful hand/arm movement → empty list `[]` / 유의미한 손·팔 움직임 미감지 → 빈 리스트 |
| `GT-X` | Unclassifiable / 판별 불가 | Clear movement but type undetermined / 움직임 있으나 유형 미분류 |

> Size cue / 크기 표현: depicting a **real object's** size (enlarging or
> shrinking the hands/body) is **GT-I (Iconic)**; an **abstract** magnitude with
> no real referent (a "big" problem, great importance) is **GT-M (Metaphoric)**.
> <br>**실물 대상**의 크기를 손·몸으로 키우거나 줄여 표현하면 **GT-I(상징적)**,
> 실물 없이 **추상적 크기**(예: "큰" 문제, 중요성)를 표현하면 **GT-M(은유적)**.

The codes are a user-editable schema (`config/gesture_schema.json`); see
[Editing the Gesture Schema](#editing-the-gesture-schema--제스처-분류체계-편집).
<br>코드는 사용자가 편집 가능한 분류체계(`config/gesture_schema.json`)입니다.

---

## Getting Started / 빠른 시작

### ① Before install — setup / 설치 전 — 설치

```bash
cd teacher-gesture-coder
python3 -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate

# Required core / 필수 코어
pip install -r requirements.txt

# Optional, recommended — teacher detection + skeleton motion pre-filter
# 선택·권장 — 교사 검출 + 골격 모션 사전필터 (YOLO / YOLO-pose)
pip install -r requirements-yolo.txt   # weights auto-download on first run / 가중치 첫 실행 시 자동 다운로드

# Optional — per-window speech transcription (STT)
# 선택 — 윈도우별 발화 전사 (STT)
pip install -r requirements-stt.txt    # Whisper model auto-downloads on first run / Whisper 모델 첫 실행 시 자동 다운로드
```

> Optional parts degrade gracefully: without YOLO it uses the full frame + a
> coarse frame-difference motion estimate; without faster-whisper, STT is off.
> <br>선택 항목은 graceful fallback: YOLO 미설치 시 전체 프레임 + 거친 프레임차분
> 모션 추정으로, faster-whisper 미설치 시 STT는 자동 비활성으로 동작합니다.

### ② After install — run / 설치 후 — 실행

```bash
source .venv/bin/activate              # if not already active / 아직 활성화 안 했다면

python run.py                          # native window (browser fallback) / 네이티브 창 (실패 시 브라우저)
python run.py --browser                # force the browser / 브라우저로 강제 실행
python run.py --no-window              # server only → http://127.0.0.1:8765 / 서버만 실행
```

> `pywebview` is in `requirements.txt`; if unavailable the app auto-falls back to
> the browser. You can run the whole flow with **Provider = Mock** (no API key).
> <br>`pywebview`는 `requirements.txt`에 포함되며, 없으면 자동으로 브라우저로 폴백합니다.
> **Provider = Mock**(API 키 불필요)으로 전체 흐름을 바로 돌려볼 수 있습니다.

---

## Using the App / 사용법

1. **Select Video** to load an mp4/mov/avi/mkv; it plays in the built-in player.
   <br>**영상 선택**으로 mp4/mov/avi/mkv 불러오기 → 내장 플레이어로 재생
2. **2. LLM Settings** — pick a provider. **Mock** needs no key (random codes, for testing); for real analysis choose **OpenAI / Anthropic / Gemini**, enter the API key (auto-saved) and a vision-capable model name.
   <br>**2. LLM 설정** — Provider 선택. **Mock**은 키 불필요(테스트용 임의 코드), 실제 분석은 **OpenAI/Anthropic/Gemini** + API Key(자동 저장) + 비전 지원 모델명 입력
3. **3. Gesture Schema** — view/edit the codes (JSON). / 제스처 분류체계 보기·편집(JSON)
4. **4. Analysis Options** — set the range and filters (see below). / 분석 범위·필터 설정(아래 참고)
5. **Start** → the right **Results** tab fills in real time; the player playhead follows the window being coded. / **분석 시작** → 우측 **결과** 탭 실시간 채움, 플레이헤드가 코딩 중 윈도우를 따라감
6. In Results: **click a timestamp to jump the video there**, **click a Gesture cell to edit codes**, **🖼** to preview that window's strip, and **Overview** to scroll all strips + codes (+ speech). / 결과창에서 **시간 클릭=해당 시점 이동**, **Gesture 셀 클릭=코드 수정**, **🖼**=해당 strip 미리보기, **Overview**=전체 strip·코드(·발화) 스크롤 검토
7. **Export CSV** → `results/{video-title}_{YYYYMMDD_HHMMSS}.csv`. / **CSV 내보내기** → `results/{영상제목}_{날짜시간}.csv`

### Analysis Options / 분석 옵션

- **Start point (min:sec)** / 분석 시작 지점, **Length limit (sec, 0 = to end)** / 분석 길이 제한
- **Min confidence** — below it the AI code is forced to None (0 = off) / 최소 신뢰도(이하 None, 0=끔)
- **Motion pre-filter** on/off + **Still / Start thresholds** (defaults **0.25 / 0.25**) / 모션 사전필터 + 정지/시작 임계값(기본 0.25/0.25)
- **STT** on/off + **model** (tiny…large-v3) + **language** (auto/ko/en). STT transcribes **only the analyzed range** and shows a loading indicator on the first run. / STT 켜기 + 모델 + 언어. **분석 구간만** 전사하며 첫 실행 시 로딩 표시
- **Include confidence in CSV** / CSV에 confidence 포함

### Recommended models (vision-capable) / 권장 모델 (비전 지원)

- OpenAI: `gpt-4o`, `gpt-4o-mini` (testing) — any vision-capable model works.
- Anthropic: `claude-sonnet-4-6`, etc.
- Gemini: `gemini-1.5-flash`, etc.

> Wrong model IDs or rejected parameters surface the provider's real error
> (e.g. `openai 400: ...`) verbatim in the right-side **Log tab**.
> <br>모델 ID 오류·파라미터 거부 시 우측 **로그 탭**에 공급자 실제 에러가 그대로 표시됩니다.

---

## Output / CSV / 출력

Saved as `results/{video-title}_{YYYYMMDD_HHMMSS}.csv`. Columns (extra columns
are added automatically when the data is present): / `results/{영상제목}_{날짜시간}.csv`로
저장됩니다. 열 구성(데이터가 있을 때 추가 열 자동 포함):

| Column | Meaning / 의미 |
|---|---|
| `no`, `timestamp` | window index + start time / 윈도우 번호·시작 시각 |
| `gesture` | list of codes, e.g. `["GT-D"]` (`[]` = GT-N) / 코드 리스트 |
| `confidence` | AI certainty (if enabled) / AI 신뢰도(옵션) |
| `grade` | A / B / C window grade / 윈도우 등급 |
| `motion` | peak normalized hand displacement / 정규화 손 이동량 최댓값 |
| `source` | `yolo-pose` · `frame-diff` · `skeleton_fail` / 모션 신호 출처 |
| `review_flag` | 1 = recommended for manual review / 수동 검토 권장 |
| `speech` | transcribed speech for the window (if STT on) / 윈도우 발화(STT 켰을 때) |

> Grade/motion/review/speech appear in the CSV and **Overview** but are kept out
> of the right-side results table to keep it readable.
> <br>등급·모션·검토·발화는 CSV와 **Overview**에 표시되며, 결과 테이블은 가독성을 위해
> 제외합니다.

## Editing the Gesture Schema / 제스처 분류체계 편집

Edit `config/gesture_schema.json` directly, or use **3. Gesture Schema → Edit
JSON** in the app — changes apply immediately. Each `description` is fed verbatim
into the English LLM prompt, so clearer distinguishing descriptions yield better
accuracy. When the codes start with `GT-`, the prompt also adds a detailed
McNeill decision guide (with a strict metaphoric gate).
<br>`config/gesture_schema.json`을 직접 수정하거나 앱의 **3. 제스처 분류체계 → JSON
편집**에서 변경하면 즉시 반영됩니다. 설명(description)은 영어 프롬프트에 그대로 들어가므로
구분 기준을 명확히 적을수록 정확해집니다. 코드가 `GT-`로 시작하면 프롬프트에 McNeill
단계별 판별 가이드(메타포 엄격 게이트 포함)가 자동 추가됩니다.

```json
{ "gestures": [ { "name": "GT-D", "description": "Deictic: a fingertip/hand extends toward a specific target and holds." } ] }
```

> `GT-N` (no gesture) is represented by an empty list `[]`, so it is not a
> selectable code in the schema. / `GT-N`은 빈 리스트로 표현되어 스키마의 선택 코드에는
> 포함되지 않습니다.

---

## Tech Stack / 기술 스택

- **Backend**: Python + FastAPI (analysis runs in a background thread; results stream via polling). / 백엔드: Python + FastAPI(백그라운드 스레드 분석, 폴링 스트리밍)
- **Desktop window**: pywebview (native window, automatic browser fallback). / pywebview(네이티브 창, 브라우저 자동 폴백)
- **Vision/Video**: OpenCV, Pillow, (optional) Ultralytics YOLO + YOLO-pose. / 비전·영상
- **Speech**: (optional) faster-whisper — audio decoded via PyAV, no external ffmpeg. / 음성: faster-whisper(PyAV 디코딩, ffmpeg 불필요)
- **Frontend**: build-free vanilla HTML/CSS/JS with built-in i18n (Korean/English toggle). / 빌드 불필요 순수 HTML/CSS/JS, i18n 내장(한/영 토글)
- **LLM prompt** is entirely in English (including gesture descriptions). / 프롬프트는 전부 영어

## Directory Structure / 디렉토리 구조

```
teacher-gesture-coder/
├── run.py                  # entry point: server + native window / 실행 진입점
├── requirements.txt
├── requirements-yolo.txt   # optional: YOLO detection + YOLO-pose motion / 선택
├── requirements-stt.txt    # optional: faster-whisper transcription / 선택
├── backend/
│   ├── app.py              # FastAPI endpoints (+ video range streaming) / 엔드포인트
│   ├── pipeline.py         # analysis pipeline + background job manager / 파이프라인·잡 매니저
│   ├── detector.py         # YOLO teacher detection/crop (20% pad, fallback) / 교사 검출·크롭
│   ├── motion.py           # YOLO-pose motion pre-filter + grading (frame-diff fallback) / 모션 사전필터·등급
│   ├── stt.py              # faster-whisper transcription + per-window slicing / 전사·윈도우 분할
│   ├── llm.py              # OpenAI/Anthropic/Gemini/Mock vision calls (English prompt) / 비전 호출
│   ├── schema_store.py     # load/save gesture schema / 분류체계 로드·저장
│   ├── settings_store.py   # settings persistence / 설정 저장
│   ├── csv_export.py       # CSV output / CSV 출력
│   └── paths.py
├── frontend/               # index.html / styles.css / app.js (i18n built in)
├── config/
│   ├── gesture_schema.json
│   └── settings.json       # runtime; stores API key locally; git-ignored / 실행 시 생성, API Key 로컬 저장
└── videos/ crops/ strips/ results/ logs/ transcripts/   # created at runtime / 실행 시 생성
```

## Notes & Limitations / 참고 및 한계

- `config/settings.json` stores provider/model/options and the API key locally (git-ignored). / Provider·모델·옵션·API Key를 로컬 저장(.gitignore)
- Teacher detection uses a "largest person box = teacher" heuristic; it can mis-detect when a student appears larger. / "가장 큰 사람=교사" 휴리스틱이라 학생이 더 크게 잡히면 오검출 가능
- Motion thresholds may need tuning per recording (camera distance, how animated the teacher is). Watch the colorbar/Overview and adjust the still/start thresholds. / 촬영 환경·교사 활동성에 따라 임계값 조정 필요 — 컬러바·Overview 보며 조정
- Windows are currently non-overlapping; sliding-window overlap and multi-axis SFMDA codes (MF/SY/WR) are future work. / 현재 윈도우는 비중첩 — 슬라이딩 중첩·다축 SFMDA 코드(MF/SY/WR)는 향후 과제
- Roadmap: gesture-frequency analysis, multi-coder comparison, automatic Cohen's Kappa, gesture–speech (SY) synchronization. / 향후: 빈도 분석, 다중 코더 비교, Cohen's Kappa, 제스처-발화 동기화(SY)
