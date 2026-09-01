# `rag_embeddings.meta.json` 해설집

## 무엇인가요?

임베딩 파일의 **제품 설명서와 봉인 확인표**입니다. 작은 JSON이지만 서로 다른 버전의 SQLite와 벡터를 잘못 섞는 것을 막습니다.

## 현재 주요 값

| 항목 | 값 | 뜻 |
|---|---|---|
| `model` | `intfloat/multilingual-e5-small` | 벡터를 만든 모델 |
| `document_count` | `22508` | 벡터 문서 수 |
| `dimension` | `384` | 한 문서의 숫자 개수 |
| `dtype` | `float32` | 숫자 저장 형식 |
| `normalized` | `true` | 벡터 길이를 1로 맞춤 |
| `query_prefix` | `query:` | 질문 앞에 붙이는 E5 표지 |
| `passage_prefix` | `passage:` | 문서 앞에 붙이는 E5 표지 |
| `max_length` | `256` | 모델에 넣을 최대 토큰 수 |
| `database_size` | `599347200` | 생성 당시 SQLite 파일 크기 |

## 실습

```powershell
python -c "import json; m=json.load(open('rag_embeddings.meta.json',encoding='utf-8')); print(m['model'],m['document_count'],m['dimension'])"
```

현재 SQLite 크기와 비교:

```powershell
python -c "import json,os; m=json.load(open('rag_embeddings.meta.json',encoding='utf-8')); print(m['database_size']==os.path.getsize('rag_index.sqlite3'))"
```

`False`이면 `local_rag.py`는 의미 검색을 끄고 FTS로 대체합니다.
