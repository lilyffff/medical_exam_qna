# `embedding_model.py` 코드 해설집

## 역할

이 파일은 문장을 E5 모델에 넣어 **384개의 숫자로 된 의미 좌표**로 바꿉니다. 학교 도서관의 책마다 주제 좌표를 붙여 가까운 책을 찾는 것과 비슷합니다.

## 핵심 전문용어

| 전문용어 | 학생용 설명 |
|---|---|
| Tokenizer | 문장을 모델이 읽을 작은 조각과 번호로 바꾸는 번역기 |
| Batch | 여러 문장을 한 묶음으로 처리하는 학습지 한 세트 |
| Padding | 길이가 다른 문장을 같은 칸 수로 맞추는 빈칸 |
| Truncation | 최대 길이를 넘는 뒤쪽 내용을 자르는 것 |
| Attention mask | 진짜 글자와 빈칸을 구별하는 표시 |
| Mean pooling | 유효한 토큰 벡터의 평균을 내 문장 하나의 벡터로 만드는 과정 |
| L2 정규화 | 벡터 길이를 1로 맞춰 방향만 공정하게 비교하는 과정 |
| inference mode | 학습하지 않고 계산만 해서 메모리를 절약하는 모드 |

## 코드 흐름

1. `load_embedding_model()`이 `.env`의 E5 모델 이름을 읽습니다.
2. 토크나이저와 모델을 CPU 또는 GPU로 옮깁니다.
3. `encode_embeddings()`이 문장들을 배치로 나눕니다.
4. 토크나이저가 길이를 맞추고 너무 긴 부분을 자릅니다.
5. 모델이 각 토큰의 벡터를 만듭니다.
6. 빈칸을 제외하고 평균을 냅니다.
7. 길이를 1로 정규화해 `float32` NumPy 배열로 반환합니다.

`@lru_cache(maxsize=2)`는 같은 CPU/GPU 모델을 다시 불러오지 않게 합니다.

## 왜 Sentence Transformers 대신 직접 계산하나?

현재 구현은 Transformers와 PyTorch만 사용합니다. Windows에서 추가 네이티브 DLL 의존성을 줄이면서 E5 모델 카드의 평균 풀링 규칙을 직접 적용하기 위해서입니다.

## 실습

두 문장의 벡터 모양과 유사도를 확인합니다.

```powershell
python -c "from embedding_model import encode_embeddings; import numpy as np; v=encode_embeddings(['query: 신장 혈류 감소','query: 소변량 저하']); print(v.shape); print(float(v[0]@v[1]))"
```

- `(2, 384)`는 두 문장이 각각 384개 숫자로 바뀌었다는 뜻입니다.
- 내적 값이 클수록 의미 방향이 비슷합니다.

첫 실행은 모델을 내려받고 메모리에 올리므로 오래 걸릴 수 있습니다.
