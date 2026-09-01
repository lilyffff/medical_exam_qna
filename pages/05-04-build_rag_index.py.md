# `build_rag_index.py` 코드 해설집

## 역할

많은 의료 JSON 파일을 읽어 검색하기 좋은 작은 문서 조각으로 나누고 `rag_index.sqlite3`에 저장하는 **도서관 책 정리 작업**입니다. `app.py`를 실행할 때마다 하는 일이 아니라 원문이 바뀌었을 때 별도로 실행합니다.

## 전문용어를 쉽게

| 전문용어 | 학교생활 비유 |
|---|---|
| 인덱스 | 교과서 맨 뒤의 찾아보기 |
| Chunk | 긴 교과서를 공부하기 좋은 몇 문단으로 나눈 것 |
| Overlap | 앞 조각의 마지막 부분을 다음 조각에도 조금 복사 |
| Transaction/commit | 작성 중인 내용을 확인하고 DB에 확정 저장 |
| FTS 가상 테이블 | 검색을 빠르게 해 주는 별도 찾아보기 표 |

## 코드 흐름

1. `source_metadata()`가 폴더명으로 전문 QA와 원천 문서를 구분합니다.
2. `document_text()`가 QA는 `질문 + 답변`, 원천 문서는 `content`를 꺼냅니다.
3. `chunks()`가 긴 글을 기본 1,100자, 180자 겹침으로 나눕니다.
4. 가능하면 문장 끝에서 잘라 의미가 중간에 끊기지 않게 합니다.
5. 기존 DB가 있으면 새 인덱스를 만들기 위해 삭제합니다.
6. `documents`와 `documents_fts` 테이블을 만듭니다.
7. 모든 JSON을 읽어 두 테이블에 같은 `rowid`로 넣습니다.
8. 5,000개마다 저장하고 진행 상황을 출력합니다.

## 두 테이블의 관계

```text
documents      원문·자료 종류·분야·파일 경로를 보관하는 학생부
documents_fts  내용 검색을 빠르게 하는 찾아보기 카드
같은 rowid     두 기록이 같은 문서임을 연결하는 학번
```

## 실습

실행 전 `.env`의 `MEDICAL_KNOWLEDGE_PATH`가 압축을 푼 JSON 폴더인지 확인합니다.

```powershell
python build_rag_index.py
```

문서 수 확인:

```powershell
python -c "import sqlite3; c=sqlite3.connect('file:rag_index.sqlite3?mode=ro',uri=True); print(c.execute('select count(*) from documents').fetchone()[0])"
```

현재 DB는 99,742개 조각입니다.

## 주의

이 스크립트는 기존 `rag_index.sqlite3`를 지우고 새로 만듭니다. 실행 전 경로와 백업을 확인해야 합니다. DB가 바뀌면 임베딩도 다시 만들어야 합니다.
