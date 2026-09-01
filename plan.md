# 의료국가시험 RAG·Embedding 전체 흐름도

## 업데이트 003. 고등학생을 위한 파일 연결 지도

아래 한 장은 의료 원문이 검색 DB와 의미 벡터로 바뀌고, 학생이 해설 버튼을 눌렀을 때 정답 근거가 화면에 나오기까지의 전체 흐름입니다.

```mermaid
flowchart TD
    %% 1. 미리 준비하는 데이터 구축 영역
    subgraph BUILD[1. 미리 한 번 준비하는 검색 자료 만들기]
        RAW["의료 원문 *.json<br/>교과서·전문 QA·가이드라인·논문"]
        CONCEPT["medical_concepts.json<br/>동의어·관련 병태생리 규칙 4개"]
        BUILD_SQL["build_rag_index.py<br/>긴 글을 겹치는 작은 조각으로 나눔"]
        SQLITE[("rag_index.sqlite3<br/>문서 조각 99,742개<br/>documents + FTS5")]
        BUILD_VEC["build_embedding_index.py<br/>전문 자료 22,508개 선별"]
        E5_BUILD["embedding_model.py<br/>multilingual-E5로<br/>문장을 숫자 벡터로 변환"]
        VECS[("rag_embeddings.npy<br/>22,508 × 384 의미 벡터")]
        IDS[("rag_embedding_ids.npy<br/>벡터 ↔ SQLite 문서 ID")]
        META["rag_embeddings.meta.json<br/>모델·차원·문서 수·DB 크기"]

        RAW --> BUILD_SQL --> SQLITE
        SQLITE --> BUILD_VEC --> E5_BUILD
        E5_BUILD --> VECS
        BUILD_VEC --> IDS
        BUILD_VEC --> META
    end

    %% 2. 학생이 앱을 사용하는 영역
    subgraph RUN[2. 학생이 app.py를 실행하고 문제를 푸는 과정]
        APP["app.py<br/>Gradio 웹 화면과 전체 진행 담당"]
        DATASET["KorMedMCQA<br/>의사·간호사·약사·치과의사 문제"]
        PHONE["PC 또는 휴대폰 브라우저<br/>직종·연도 선택"]
        QUESTION["무작위 문제 1개와<br/>보기 1~5번 표시"]
        GRADE["Python이 데이터셋 정답 번호로<br/>즉시 정답·오답 판정"]
        CLICK["정답 해설 보기 클릭<br/>버튼 테두리 로딩 애니메이션"]

        APP --> PHONE
        DATASET --> APP
        PHONE --> QUESTION --> GRADE --> CLICK
    end

    %% 3. RAG 검색 영역
    subgraph SEARCH[3. local_rag.py가 정답을 뒷받침할 근거 찾기]
        QUERY["문제 본문 + 정답 보기<br/>선택한 오답은 검색에서 제외"]
        CLEAN["HTML·공백·숫자 단위 정리<br/>Kiwi 형태소로 핵심어 추출"]
        EXPAND["의료 개념 확장<br/>예: 출혈 → 쇼크·신장 관류"]
        FTS["빠른 글자 검색<br/>SQLite FTS5 + BM25"]
        QUERY_VEC["의미 검색<br/>질문을 E5 벡터로 변환"]
        COS["질문 벡터와 문서 벡터의<br/>코사인 유사도 계산"]
        RRF["RRF 순위 결합<br/>글자 검색 + 의미 검색"]
        TOP4["중복 원본 제거 후 상위 4개<br/>일치어·유사도·출처 포함"]

        QUERY --> CLEAN --> EXPAND
        EXPAND --> FTS
        EXPAND --> QUERY_VEC --> COS
        FTS --> RRF
        COS --> RRF --> TOP4
    end

    CLICK --> QUERY
    CONCEPT -. "확장 규칙" .-> EXPAND
    SQLITE -. "문장과 핵심어" .-> FTS
    SQLITE -. "문서 내용·출처" .-> TOP4
    VECS -. "문서 의미 벡터" .-> COS
    IDS -. "찾은 벡터의 문서 번호" .-> COS
    META -. "파일끼리 같은 버전인지 검사" .-> QUERY_VEC
    E5_BUILD -. "같은 E5 변환 방법 재사용" .-> QUERY_VEC

    %% 4. 안전한 생성과 결과 영역
    subgraph EXPLAIN[4. 근거를 검사하고 안전하게 해설 만들기]
        QUALITY{"검색 품질 가드레일<br/>정답 핵심어가 실제 근거에 있고<br/>일치도·유사도가 충분한가?"}
        STOP1["생성 모델 실행 중단<br/>정답 + 부족 이유 + 검색 원문만 표시"]
        PROMPT["근거 제한 프롬프트<br/>근거 밖 사실·진료 지시 금지"]
        MEDIKO["현재 생성 모델<br/>MediKo-1.1B-A0.6B-inst"]
        CHECK{"생성 결과 가드레일<br/>정답 번호·가짜 근거·새 수치·<br/>위험 지시·반복 출력 검사"}
        STOP2["부적절한 생성문 숨김<br/>차단 이유 + 검색 원문 표시"]
        RESULT["최종 화면<br/>정답 해설 + 검색 품질 + 근거 1~4<br/>파일 출처 + 시험용 안전 고지"]

        QUALITY -- "부족" --> STOP1
        QUALITY -- "충분" --> PROMPT --> MEDIKO --> CHECK
        CHECK -- "실패" --> STOP2
        CHECK -- "통과" --> RESULT
    end

    TOP4 --> QUALITY

    %% 5. 현재 미사용인 과거 LoRA와 테스트
    subgraph OPTIONAL[5. 보관 자료와 자동 시험]
        ADAPTER_CFG["adapter_config.json<br/>기반: GPT-Neo 125M<br/>LoRA r=8, alpha=16"]
        ADAPTER_BIN["adapter_model.safetensors<br/>과거 Medical QA LoRA 가중치"]
        TOKEN_JSON["tokenizer.json·tokenizer_config.json<br/>과거 토크나이저 설정"]
        UNUSED["현재 MEDICAL_LORA_ADAPTER가 빈 값<br/>MediKo 실행에는 연결하지 않음"]
        TEST_RAG["test_local_rag.py<br/>형태소·개념·하이브리드 검색 시험"]
        TEST_SAFE["test_guardrails.py<br/>근거 부족·가짜 인용·새 수치 차단 시험"]

        ADAPTER_CFG --> UNUSED
        ADAPTER_BIN --> UNUSED
        TOKEN_JSON --> UNUSED
        TEST_RAG -. "검색 회귀 검사" .-> SEARCH
        TEST_SAFE -. "안전 회귀 검사" .-> EXPLAIN
    end

    classDef data fill:#e8f1ff,stroke:#3973ac,color:#102a43;
    classDef code fill:#e9f8ef,stroke:#2f855a,color:#173d2a;
    classDef guard fill:#fff4d6,stroke:#b7791f,color:#5f370e;
    classDef stop fill:#ffe8e8,stroke:#c53030,color:#681b1b;
    classDef old fill:#f1f1f1,stroke:#777,color:#444,stroke-dasharray:5 5;

    class RAW,CONCEPT,SQLITE,VECS,IDS,META,DATASET data;
    class BUILD_SQL,BUILD_VEC,E5_BUILD,APP,CLEAN,EXPAND,FTS,QUERY_VEC,COS,RRF,MEDIKO code;
    class QUALITY,CHECK,PROMPT guard;
    class STOP1,STOP2 stop;
    class ADAPTER_CFG,ADAPTER_BIN,TOKEN_JSON,UNUSED old;
```

## 그림을 읽는 핵심 세 문장

1. **RAG**는 AI가 바로 추측하게 하지 않고, `rag_index.sqlite3`와 임베딩 파일에서 먼저 참고 자료를 찾는 과정입니다.
2. **Embedding**은 문장의 뜻을 384개의 숫자로 바꿔서 표현이 달라도 의미가 비슷한 문서를 찾는 기술입니다.
3. 검색 근거가 부족하거나 생성문이 근거 밖으로 벗어나면 **가드레일**이 해설을 차단하고 원문 근거만 보여 줍니다.

> 이 앱은 의료국가시험 학습용입니다. 실제 진단, 처방, 투약 또는 응급 판단에 사용하지 않습니다.
