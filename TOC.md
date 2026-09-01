# 의료국가시험 RAG 앱 문서 목차

## 업데이트 003. 현재 구현 기준 목차와 통합 흐름도

이 목차는 초기 Colab·Qwen 학습 계획이 아니라, 2026-09-01 현재 완성된 **로컬 의료국가시험 문제 풀이 + 하이브리드 RAG + MediKo 해설 앱**을 기준으로 정리했습니다.

## 업데이트 004. 중학생용 코드·데이터 해설집

실행 코드와 데이터·인덱스·모델 파일을 전문용어와 학교생활 비유로 함께 설명하고, 직접 실행할 수 있는 안전한 실습 및 영역별 Mermaid 흐름도를 연결했습니다.

## 업데이트 005. 부모·자식 문서 번호 체계

`05-실행코드-흐름도.md` 아래의 코드 해설집은 `05-01`~`05-05`, `07-데이터-인덱스-모델-흐름도.md` 아래의 파일 해설집은 `07-01`~`07-09` 접두사로 정렬했습니다.

## 1. 처음 읽을 문서

1. [README.md](README.md)
   - 프로젝트 목적과 안전 고지
   - 설치, 실행, 데이터 및 모델 구성
2. [plan.md](plan.md)
   - Python, JSON, SQLite, 임베딩, LoRA 파일이 연결되는 전체 Mermaid 흐름도 한 장
3. [플로우챠트.md](플로우챠트.md)
   - 화면 조작부터 채점·검색·해설까지 단계별 상세 흐름

## 2. 설명 가능한 AI와 검색

4. [설명가능한ai.md](설명가능한ai.md)
   - 문제와 정답 보기를 함께 검색하는 이유
   - 형태소 분석, 의료 개념 확장, 임베딩과 RRF
   - 검색 품질 검사와 생성 결과 가드레일
5. [sqllite사용설명서.md](sqllite사용설명서.md)
   - SQLite를 고등학생 눈높이로 설명
   - `rag_index.sqlite3`의 `documents`와 FTS5 구조
   - SQLite와 `.npy` 임베딩 파일의 연결

## 3. 환경설정과 오류 해결

6. [환경변수.md](환경변수.md)
   - 실제 사용 환경변수와 우선순위
   - 토큰을 기록하지 않는 보안 원칙
   - RAG·임베딩·가드레일·LAN 설정
7. [에러해결파워쉘명렁어.md](에러해결파워쉘명렁어.md)
   - 조사와 검증에 사용한 PowerShell 명령
   - 실행 정책, 포트 충돌, 경로 및 Git 점검

## 4. 다른 PC와 휴대폰에서 실행

8. [노트북으로이사.md](노트북으로이사.md)
   - GitHub에는 소스코드만 push
   - Google Drive에는 비공개 `.env`, 의료 원문, SQLite와 임베딩 보관
   - 노트북 clone, 가상환경, 같은 Wi-Fi 및 외부 테스트 절차

## 5. 실행 코드

먼저 [실행 코드 전체 흐름도](pages/05-실행코드-흐름도.md)를 보면 다섯 파일의 연결을 한눈에 볼 수 있습니다.

| 파일·해설집 | 역할 |
|---|---|
| [`05-01 app.py`](pages/05-01-app.py.md) | Gradio 화면, 문제 출제, 채점, 가드레일, MediKo 해설 및 LAN 서버 |
| [`05-02 local_rag.py`](pages/05-02-local_rag.py.md) | 텍스트 정규화, Kiwi 형태소, 개념 확장, FTS·임베딩 검색, RRF 결합 |
| [`05-03 embedding_model.py`](pages/05-03-embedding_model.py.md) | multilingual-E5 모델 로딩과 정규화된 벡터 생성 |
| [`05-04 build_rag_index.py`](pages/05-04-build_rag_index.py.md) | 의료 JSON을 조각내 SQLite `documents`와 `documents_fts` 생성 |
| [`05-05 build_embedding_index.py`](pages/05-05-build_embedding_index.py.md) | SQLite 문서 중 전문 자료를 E5 벡터로 변환해 `.npy` 생성 |

## 6. 테스트 코드

| 파일 | 검사 내용 |
|---|---|
| `test_local_rag.py` | 정규화, 형태소, 개념 확장, 결핵·아나필락시스·출혈 검색, FTS 대체 동작 |
| `test_guardrails.py` | 검색 근거 충분성, 정답 개념, 허위 근거 번호와 근거 없는 수치 차단 |

전체 테스트 실행:

```powershell
python -m unittest test_local_rag.py test_guardrails.py
```

## 7. 데이터·인덱스·모델 파일

먼저 [데이터·인덱스·모델 전체 흐름도](pages/07-데이터-인덱스-모델-흐름도.md)를 보면 파일들이 한 세트로 움직이는 이유를 알 수 있습니다.

| 파일·해설집 | 현재 상태와 의미 |
|---|---|
| [`07-01 의료 원문 *.json`](pages/07-01-의료원문.json.md) | 전문 QA·교과서·가이드라인·논문 원문 |
| [`07-02 medical_concepts.json`](pages/07-02-medical_concepts.json.md) | 반복적으로 중요한 의료 동의어·병태생리 확장 규칙 4개 |
| [`07-03 rag_index.sqlite3`](pages/07-03-rag_index.sqlite3.md) | 99,742개 의료 문서 조각과 FTS5 검색 인덱스 |
| [`07-04 rag_embeddings.npy`](pages/07-04-rag_embeddings.npy.md) | 선별 문서 22,508개의 384차원 float32 의미 벡터 |
| [`07-05 rag_embedding_ids.npy`](pages/07-05-rag_embedding_ids.npy.md) | 각 벡터와 SQLite `documents.id`를 연결하는 22,508개 ID |
| [`07-06 rag_embeddings.meta.json`](pages/07-06-rag_embeddings.meta.json.md) | E5 모델, 차원, 문서 수, DB 크기와 접두사 등 무결성 정보 |
| [`07-07 adapter_model.safetensors`](pages/07-07-adapter_model.safetensors.md) | GPT-Neo 125M용 과거 Medical QA LoRA 가중치 |
| [`07-08 adapter_config.json`](pages/07-08-adapter_config.json.md) | LoRA의 기반 모델, rank, alpha, 대상 모듈 설정 |
| [`07-09 tokenizer.json`·`tokenizer_config.json`](pages/07-09-tokenizer.json.md) | 과거 GPT-Neo 어댑터 실험의 토크나이저 정보 |

현재 앱은 `.env`의 `MEDICAL_BASE_MODEL=MediKo/MediKo-1.1B-A0.6B-inst`를 사용하고 `MEDICAL_LORA_ADAPTER`가 비어 있으므로, 보관된 GPT-Neo LoRA 파일은 로딩하지 않습니다.

## 8. 현재 실행 순서

```powershell
.\.venv\Scripts\Activate.ps1
python app.py
```

1. 직종 선택
2. 연도 선택
3. 무작위 문제 출제
4. 답안 선택과 즉시 채점
5. 문제와 정답 보기로 근거 검색
6. 검색 품질 가드레일
7. MediKo 근거 기반 해설
8. 생성 결과 가드레일
9. 해설, 검색 품질, 원문 출처와 안전 고지 표시

## 9. 보안상 GitHub에 올리지 않는 파일

```text
.env
medical_knowledge_data/
08.전문 의학지식 데이터/
rag_index.sqlite3
rag_embeddings.npy
rag_embedding_ids.npy
rag_embeddings.meta.json
```

`HF_TOKEN` 등 이미 화면이나 채팅에 노출된 인증정보는 폐기하고 새 토큰으로 교체해야 합니다.

## 10. 문서 업데이트 규칙

코드 업데이트는 같은 번호와 제목을 다음 다섯 문서에 함께 기록합니다.

1. `설명가능한ai.md`
2. `에러해결파워쉘명렁어.md`
3. `플로우챠트.md`
4. `환경변수.md`
5. `sqllite사용설명서.md`

`업데이트 003`은 현재 상태 목차와 통합 그림을 만들었고, `업데이트 004`는 중학생용 파일별 해설집과 영역별 흐름도를 추가했습니다. 두 업데이트 모두 소스코드와 데이터 자체는 변경하지 않았습니다.
