# CLAUDE.md

## Docs sync rule (필수)

이 저장소에서 **기능 개선·동작 변경·주요 편집**을 했으면, 커밋 전에 아래 문서들을
한 번씩 훑어 **사실과 어긋난 곳을 고친다**. 관련 없으면 그냥 넘어간다 — 확인 자체가 규칙.

무엇이 "주요 변경"인가: 파이프라인 흐름·프레임 처리·LLM 입력 방식·기본 설정값
(interval/segment_frames 등)·제스처 스키마(코드 추가/삭제/정의)·API 엔드포인트·
UI 동작. 오타/리팩토링/내부 헬퍼는 대상 아님.

문서별 담당 범위 (하나라도 건드렸으면 그 문서 확인):

| 문서 | 커버 | git |
|---|---|---|
| `README.md` | 작동 방식 5단계, 제스처 코드표, 설정, 사용법 | tracked (public) |
| `COMMAND.md` | 실행 명령 | tracked (public) |
| `HANDOFF.md` | 아키텍처·데이터흐름·설정 기본값·API 목록 | gitignored (internal) |
| `docs/*.md` | 논문 초안(서론/시스템 개발/결론/신뢰도) — 설명이 코드와 어긋나면 수정 | gitignored (internal) |

주의: `docs/`, `HANDOFF.md`, `plan*.md`, `overview-of-development.md`는 gitignored라
**푸시되지 않는다** — 그래도 로컬 정확성을 위해 갱신은 한다. 커밋에 실제 포함되는
문서는 `README.md`·`COMMAND.md`뿐.

## 코드 지향

- 파이프라인: `backend/pipeline.py` `AnalysisJob`. 프레임은 **개별 이미지**로 LLM에 전송
  (strip은 저장·미리보기용 concat). LLM 진입점 `llm.analyze_frames`.
- 스키마 기본값: `backend/schema_store.py DEFAULT_SCHEMA` + `config/gesture_schema.json`
  (GT-D/I/M/B/X 5종, 서로 동기 유지).
