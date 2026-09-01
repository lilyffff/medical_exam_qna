# `rag_index.sqlite3` 해설집

## 무엇인가요?

별도 DB 서버 없이 파일 하나로 쓰는 SQLite 의료 자료 도서관입니다. 일반 메모장으로 열리지 않는 것이 정상입니다.

## 내부 구조

| 테이블 | 역할 | 학교 비유 |
|---|---|---|
| `documents` | 자료 종류, 분야, 이름, 원본 경로, 내용 저장 | 도서관의 책과 책 정보 |
| `documents_fts` | 내용의 FTS5 검색 인덱스 | 책 뒤의 빠른 찾아보기 |
| 같은 `rowid` | 두 테이블의 같은 문서 연결 | 학생부와 시험지의 같은 학번 |

현재 약 599MB이며 99,742개 문서 조각을 가집니다. `build_rag_index.py`가 만들고 `local_rag.py`가 읽습니다.

## 왜 글을 조각내나요?

책 전체보다 관련 문단을 검색해야 모델에게 필요한 부분만 전달할 수 있습니다. 기본 조각은 약 1,100자이고 다음 조각과 180자가 겹쳐 문맥 손실을 줄입니다.

## 읽기 전용 실습

```powershell
python -c "import sqlite3; c=sqlite3.connect('file:rag_index.sqlite3?mode=ro',uri=True); print(c.execute('select count(*) from documents').fetchone())"
```

테이블 확인:

```powershell
python -c "import sqlite3; c=sqlite3.connect('file:rag_index.sqlite3?mode=ro',uri=True); print(c.execute('select name from sqlite_master where type=?',('table',)).fetchall())"
```

`mode=ro`는 실수로 내용을 바꾸지 않는 읽기 전용 모드입니다.

## 중요한 연결

임베딩 메타데이터는 이 파일의 크기를 기록합니다. SQLite를 다시 만들면 기존 임베딩과 짝이 달라지므로 `build_embedding_index.py`도 다시 실행해야 합니다.
