# 의료국가시험 랜덤 문제 앱

의사·간호사·약사·치과의사 국가시험 문제를 직종과 연도별로 무작위 출제하고, 정답 확인과 교육용 해설을 제공하는 로컬 Gradio 앱입니다.

> ⚠️ 시험 학습·연구용입니다. 실제 진단, 처방, 투약 또는 응급 판단에 사용하지 마세요.

## 현재 구현 상태

- 직종 카드 4개와 모바일 2행 × 2열 레이아웃
- 선택한 직종 카드 강조 표시
- KorMedMCQA의 실제 연도만 자동 표시
- `train`·`dev`·`test` 전체에서 해당 연도의 문제를 무작위 출제
- 정답 확인 즉시 결과 표시, 해설은 별도 요청 시 생성
- 같은 Wi-Fi에 연결된 모바일 브라우저에서 로컬 PC 앱 접속
- Hugging Face 접속에 Windows 인증서 저장소를 사용하는 `truststore` 적용
- AI Hub 전문 의학지식 데이터를 PC에 보관하고, RAG 해설 기능을 연결할 준비 완료

## 지금까지 작업한 순서

1. `pages`의 Markdown 코드 블록을 동일 이름의 Jupyter 노트북(`.ipynb`)으로 변환했습니다.
2. `02`~`12` 노트북의 코드 셀을 순서대로 합친 `summary.ipynb`를 만들었습니다.
3. Gradio 기반 웹앱 `app.py`를 만들고, 직종·연도·무작위 문제·채점·해설 흐름을 구현했습니다.
4. `.env`와 `.env.example`을 추가해 Hugging Face 토큰, 프록시, 모델·LoRA 경로를 환경별로 설정할 수 있게 했습니다.
5. 기관 네트워크의 자체 서명 인증서 문제를 해결하기 위해 `truststore`를 앱 시작 단계에서 적용했습니다.
6. KorMedMCQA의 분할별 연도 범위에 맞춰 직종 선택 시 사용 가능한 연도를 자동으로 표시하도록 바꿨습니다.
7. AI Hub 전문 의학지식 데이터의 Training 원천·라벨링 데이터를 로컬에 해제했습니다.
8. 로컬 SQLite FTS 검색 인덱스를 만들고, 오답 해설에 전문 의학지식 근거와 파일 출처를 연결했습니다.

## 실행

```powershell
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

브라우저에 표시된 로컬 주소를 엽니다. 처음 직종을 선택할 때 KorMedMCQA 데이터셋을 내려받습니다.

### 같은 Wi-Fi에서 모바일로 접속

PC와 스마트폰을 같은 Wi-Fi에 연결한 뒤 PC에서 앱을 실행합니다.

```powershell
python app.py
```

터미널에 다음과 비슷한 모바일 접속 주소가 표시됩니다.

```text
같은 Wi-Fi의 모바일 브라우저에서 다음 주소 중 하나를 여세요:
  http://192.168.0.10:7860
```

표시된 주소를 스마트폰의 Chrome 또는 Safari 주소창에 입력합니다. 접속되지 않으면 다음을 확인합니다.

1. PC와 스마트폰이 동일한 Wi-Fi에 연결되어 있는지 확인합니다.
2. Windows 보안 경고가 나타나면 Python을 **개인 네트워크**에 허용합니다.
3. 터미널에서 `ipconfig`를 실행해 Wi-Fi 어댑터의 IPv4 주소가 안내 주소와 같은지 확인합니다.
4. 게스트 Wi-Fi의 기기 간 통신 차단 기능이 켜져 있지 않은지 확인합니다.

이 단계에서는 Gradio 외부 공유 링크를 `share=False`로 끕니다. 인터넷 외부 접속, 포트포워딩 및 공개 터널은 16단계에서 인증과 HTTPS를 함께 적용한 뒤 다룹니다.

## 환경 변수

실제 설정은 `.env`에 저장합니다. 이 파일은 `.gitignore`로 Git 추적에서 제외됩니다.

```env
# 공개 데이터만 쓴다면 비워 둬도 됩니다.
HF_TOKEN=

KORMED_DATASET_ID=sean0042/KorMedMCQA
MEDICAL_BASE_MODEL=Qwen/Qwen2.5-1.5B-Instruct
MEDICAL_LORA_ADAPTER=
MEDICAL_TRUST_REMOTE_CODE=false

# 같은 Wi-Fi 모바일 접속
APP_HOST=0.0.0.0
APP_PORT=7860

# 기관 프록시를 사용해야 할 때만 설정합니다.
# HTTPS_PROXY=http://proxy.example.com:8080
# HTTP_PROXY=http://proxy.example.com:8080
```

`MEDICAL_LORA_ADAPTER`는 반드시 해당 LoRA가 학습된 기본 모델과 짝을 맞춰야 합니다. 예를 들어 GPT-Neo용 LoRA는 Qwen 기본 모델에 연결할 수 없습니다.

MediKo처럼 사용자 정의 모델 코드를 포함한 모델은 `MEDICAL_TRUST_REMOTE_CODE=true`가
필요합니다. 이 설정은 내려받은 저장소의 Python 코드를 실행하므로 신뢰할 수 있는 모델에만
사용하세요.

## KorMedMCQA 문제 데이터

앱은 [KorMedMCQA](https://huggingface.co/datasets/sean0042/KorMedMCQA)를 사용합니다. 이 데이터는 문제·5개 선택지·정답 번호 중심의 시험 데이터이므로, 오답의 전문 근거를 제공하려면 별도의 의료지식 데이터가 필요합니다.

## 로컬 전문 의학지식 데이터

AI Hub의 `전문 의학지식 데이터`는 외부로 업로드하지 않고 다음 폴더에서 사용합니다.

```text
medical_knowledge_data/
├─ TS_국문_온라인 의료 정보 제공 사이트/  # 원천 문서 34,484개
├─ TS_국문_학회 가이드라인/                # 원천 문서 1,298개
├─ TS_국문_의학 교과서/                     # 원천 문서 159개
├─ TS_국문_학술 논문 및 저널/               # 원천 문서 970개
├─ TS_국문_기타/                            # 원천 문서 4,890개
└─ TL_라벨링데이터/                         # 전문 QA 12,228개
```

`Validation` 자료는 해설 품질 평가용으로 보관하고 RAG 검색 인덱스에는 넣지 않습니다. 원본 ZIP 파일도 삭제하지 않고 보관합니다.

AI Hub 데이터는 승인 조건 및 이용정책을 준수해야 합니다. 특히 별도 승인 없이 외부 저장소·해외 클라우드에 업로드하지 않습니다. 자세한 조건은 [AI Hub 데이터 이용정책](https://aihub.or.kr/intrcn/guid/usagepolicy.do?currMenu=151&topMenu=105)을 확인하세요.

## 로컬 RAG 기반 오답 해설

```text
KorMedMCQA 오답 또는 해설 요청
  → 전문 의학지식 문서를 문단 단위로 검색
  → 관련 근거 4개 선택
  → 해설 모델에 근거 전달
  → 정답 근거 / 선택한 오답이 틀린 이유 / 핵심 암기 / 출처 표시
```

현재 구현은 외부 검색 서비스 없이 실행되는 로컬 하이브리드 검색입니다.

1. Kiwi가 한국어 조사·어미를 분리하고 핵심 형태소를 추출합니다.
2. `medical_concepts.json`이 여러 문제에서 재사용할 의료 개념과 동의어를 확장합니다.
3. SQLite FTS5가 정확한 질환명·약물명·검사명을 검색합니다.
4. multilingual-E5가 문장의 의미가 가까운 의료 자료를 검색합니다.
5. 두 순위를 Reciprocal Rank Fusion으로 결합하고 같은 원본의 중복 조각을 제거합니다.

`build_rag_index.py`는 JSON 문서를 검색 가능한 조각으로 변환해 `rag_index.sqlite3`에 저장합니다. `build_embedding_index.py`는 전문 QA와 학회 가이드라인·교과서·학술논문·기타 원천 문서의 의미 벡터를 생성합니다.

```powershell
# 전문 의학지식 JSON을 추가하거나 변경한 뒤 한 번 실행합니다.
python build_rag_index.py

# SQLite 인덱스를 만든 뒤 한 번 실행합니다. CPU에서는 수 분~수십 분 걸릴 수 있습니다.
python build_embedding_index.py
```

생성되는 의미 검색 파일은 다음과 같습니다.

```text
rag_embeddings.npy          # 정규화된 384차원 문서 벡터
rag_embedding_ids.npy       # 벡터와 SQLite 문서 ID 연결
rag_embeddings.meta.json    # 모델·문서 수·토큰 길이 메타데이터
```

임베딩 파일이나 모델을 읽지 못하면 앱은 중단되지 않고 형태소 기반 SQLite FTS 검색으로 자동 전환됩니다. 첫 의미 검색은 E5 모델을 메모리에 올리느라 더 오래 걸리며, 이후 검색은 같은 모델을 재사용합니다.

검색 인덱스와 AI Hub 원문은 Git 추적에서 제외됩니다. Supabase Cloud 사용은 데이터의 외부 제공·국외 이전 권한을 확인한 뒤에만 검토합니다.
