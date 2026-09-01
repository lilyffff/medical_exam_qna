# `build_embedding_index.py` 코드 해설집

## 역할

SQLite의 의료 문서 중 신뢰도가 비교적 높은 자료를 골라 E5 의미 벡터로 바꾸는 **도서관 책 주제 좌표 만들기 작업**입니다.

## 쉬운 용어 사전

| 전문용어 | 쉬운 설명 |
|---|---|
| Quality filter | 어떤 자료를 벡터로 만들지 정한 입장 기준 |
| Memmap | 큰 배열을 RAM에 전부 올리지 않고 디스크에 바로 쓰는 방식 |
| Temporary file | 완성 전까지 사용하는 임시 답안지 |
| Metadata | 데이터 파일을 설명하는 이름표 |
| Atomic replace | 완성된 임시 파일을 마지막에 진짜 파일로 교체 |

## 코드 흐름

1. `rag_index.sqlite3`가 있는지 검사합니다.
2. E5 모델, 배치 크기, 최대 토큰 길이와 CPU/GPU 설정을 읽습니다.
3. 전문 QA·학회 가이드라인·의학 교과서·논문·기타 전문 자료만 고릅니다.
4. 현재 기준으로 22,508개 문서를 선택합니다.
5. `passage:` 접두사를 붙여 배치 단위로 384차원 벡터를 만듭니다.
6. 벡터는 임시 `.building.npy`, 문서 ID는 별도 임시 배열에 씁니다.
7. 모델·개수·차원·SQLite 크기를 JSON 메타데이터로 기록합니다.
8. 모두 성공했을 때만 임시 파일을 최종 파일명으로 바꿉니다.

## 만들어지는 세 파일

```text
rag_embeddings.npy       각 문서의 384개 의미 숫자
rag_embedding_ids.npy    각 벡터가 가리키는 documents.id
rag_embeddings.meta.json 모델과 파일이 서로 맞는지 확인하는 이름표
```

## 실습

```powershell
python build_embedding_index.py
```

배열 모양 확인:

```powershell
python -c "import numpy as np; print(np.load('rag_embeddings.npy',mmap_mode='r').shape); print(np.load('rag_embedding_ids.npy',mmap_mode='r').shape)"
```

예상 결과:

```text
(22508, 384)
(22508,)
```

## 주의

- CPU에서는 시간이 오래 걸립니다.
- SQLite를 다시 만들었다면 메타데이터의 DB 크기가 달라지므로 임베딩도 다시 만들어야 합니다.
- `.building` 파일은 작업 중간 산출물이며 정상 완료 후 최종 파일로 교체됩니다.
