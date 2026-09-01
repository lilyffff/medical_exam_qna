# 의료국가시험 랜덤 문제 앱

직종 카드를 고르면 KorMedMCQA의 `train`·`dev`·`test` 분할에 실제 존재하는 연도만 자동으로 표시하고, 해당 연도의 문제 한 개를 무작위로 보여 주는 Gradio 앱입니다.

휴대폰 화면에서는 직종 카드가 2행 2열로 표시됩니다.

## 실행

```bash
pip install -r requirements.txt
copy .env.example .env
python app.py
```

브라우저에 표시된 로컬 주소를 엽니다. 처음 문제를 불러올 때 KorMedMCQA 데이터셋을 내려받습니다.

`.env`에는 Hugging Face 토큰, 모델·LoRA 경로, 기관 프록시처럼 환경마다 다른 값을 넣습니다. `.env`는 Git에 포함되지 않습니다. 인터넷 접속이 제한된 기관망이라면 관리자에게 `huggingface.co` 접속 허용을 요청하거나, 제공된 프록시 주소를 `HTTPS_PROXY`와 `HTTP_PROXY`에 입력하세요.

## 의료 해설 모델

코드의 기본 해설 모델은 `Qwen/Qwen2.5-1.5B-Instruct`입니다.
현재 `.env` 설정에 따라 `EleutherAI/gpt-neo-125M`과 의료 QA LoRA 어댑터를 사용합니다. 더 전문화한 LoRA 어댑터가 있다면 다음처럼 설정할 수 있습니다.

```powershell
$env:MEDICAL_LORA_ADAPTER = 'D:\path\to\your\adapter'
python app.py
```

기본 모델을 바꾸려면 `MEDICAL_BASE_MODEL` 환경 변수를 설정합니다. 해설은 시험 학습 보조용이며 실제 의료 판단에 사용하면 안 됩니다.

KorMedMCQA의 데이터 필드도 문제·선택지·정답 중심입니다. KorMedMCQA 데이터 설명

## 전문의료지식 기반 오답 해설을 넣으려면 다음 구조가 좋습니다.

```
기출문제 + 정답
   ↓
전문 의료지식 문서 검색(RAG)
   ↓
근거 문단·출처를 모델에 전달
   ↓
정답 근거 / 선택한 오답이 틀린 이유 / 참고 출처 출력
```

## 따라서 현재의 작은 GPT‑Neo 의료 모델처럼 단순 생성하는 방식보다, 국내 진료지침·교과서 허가 범위의 문서·전문의 QA 데이터 등 별도의 근거 데이터가 필요합니다. 그러면 해설에 “전문지식 답변”뿐 아니라 출처도 함께 표시할 수 있습니다.

## [전문의료지식 기반 오답 해설에 매우 적합](https://www.aihub.or.kr/aihubdata/data/view.do?currMenu=115&topMenu=100&&srchDataRealmCode=REALM006&aihubDataSe=data&dataSetSn=71874)

```
AI Hub 설명상 전문 의학 말뭉치 약 1.2억 토큰과 질의응답 15,286쌍을 제공하며, 질문·답변·진료 분야를 JSON으로 구성합니다. 객관식 QA도 11,556쌍 포함되어 있고, 해당 프로젝트의 테스트 데이터로 KorMedMCQA를 사용한다고 명시돼 있습니다. AI Hub 전문 의학지식 데이터
구현 방식은 이렇게 바꾸는 것이 좋습니다.

KorMedMCQA 기출문제에서 오답 발생
        ↓
전문 의학지식 데이터에서 관련 근거 검색
        ↓
근거 문서 2~3개와 정답·선택한 오답을 모델에 전달
        ↓
정답 근거 / 오답 이유 / 핵심 암기 / 참고 출처 출력
```

즉, 단순히 작은 모델에게 해설을 “생성”시키는 방식보다 훨씬 근거 있는 해설을 만들 수 있습니다.
다만 이 데이터는 AI Hub 다운로드 승인 후 이용해야 하고, 페이지 안내상 의료 데이터는 안심존·IRB 등 별도 이용 절차가 적용될 수 있습니다. 또한 다운로드 파일을 받아 실제 JSON 구조와 이용 조건을 확인한 뒤에만 앱에 넣어야 합니다. AI Hub 이용 절차 안내
승인·다운로드한 데이터 폴더가 준비되면, 그 로컬 경로를 기준으로 RAG 검색과 출처 표시 기능을 앱에 구현할 수 있습니다.

```powershell
cd D:\medical_exam_qna
pip install -r requirements.txt
python app.py
```

터미널에 나온 주소(보통 http://127.0.0.1:7860)를 브라우저에서 엽니다.
사용 순서:

1. 의사·간호사·약사·치과의사 카드 중 하나 선택
2. 표시된 출제 연도 선택
3. 무작위 문제 시작
4. 답 선택 후 정답 확인
5. 오답은 전문의학지식 근거를 포함한 해설이 바로 표시됨
6. 정답은 정답 해설 보기를 눌러 해설 확인
   처음 실행 전 rag_index.sqlite3가 없다면 한 번만 생성하세요.

```powershell
python build_rag_index.py
```

.env에서 MEDICAL_KNOWLEDGE_PATH=medical_knowledge_data, RAG_INDEX_PATH=rag_index.sqlite3가 비어 있지 않은지도 확인하면 됩니다.

회사·학교 네트워크의 보안 프록시가 자체 서명 인증서를 끼워 넣어서, hf 명령이 Hugging Face의 인증서를 신뢰하지 못한 상황입니다. 인터넷 연결 자체의 문제는 아닙니다.
먼저 PowerShell에서 다음을 실행해 보세요.

```powershell
py -m pip install --upgrade huggingface_hub truststore certifi
$env:SSL_CERT_FILE = (py -c "import certifi; print(certifi.where())")
$env:REQUESTS_CA_BUNDLE = $env:SSL_CERT_FILE
```

```
가장 쉬운 해결 방법은 Python이 Windows 인증서 저장소를 사용하게 하는 것입니다. PowerShell에서 실행하세요.
py -m pip install pip-system-certs
설치가 끝나면 PowerShell과 VS Code 터미널을 모두 닫고 새로 연 뒤 다시 실행합니다.
cd D:\medical_exam_qna

hf download hazemgalal1/gptneo125m-medical-qa-lora-adapter --local-dir .\models\gptneo125m-medical-qa-lora-adapter
성공 여부는 다음 파일들이 생성되는지로 확인할 수 있습니다.
models\
└─ gptneo125m-medical-qa-lora-adapter\
   ├─ adapter_config.json
   └─ adapter_model.safetensors
그래도 실패하면 네트워크의 자체 인증서를 Windows에도 신뢰시키지 않은 상태일 수 있습니다. 이 경우 기관 IT 담당자에게 “Hugging Face/Python HTTPS 접속용 프록시 루트 인증서(PEM 또는 CRT)”를 요청해 설치해야 합니다. 인증서 검증을 끄는 우회 방식은 사용하지 않는 편이 안전합니다.
```
