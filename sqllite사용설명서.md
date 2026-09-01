# SQLite 사용설명서

> 정확한 제품 이름은 `SQLite`입니다. 이 문서는 요청한 파일명에 맞춰 `sqllite사용설명서.md`로 저장했습니다.

## 1. SQLite는 로컬 데이터베이스인가?

네. SQLite는 보통 **내 컴퓨터에 파일 하나로 저장해서 사용하는 로컬 데이터베이스**입니다.

이 프로젝트에서는 다음 파일이 SQLite 데이터베이스입니다.

```text
D:\medical_exam_qna\rag_index.sqlite3
```

MySQL이나 PostgreSQL은 보통 별도의 데이터베이스 서버를 실행하고 네트워크로 접속합니다. SQLite는 별도 서버가 필요 없습니다. Python 프로그램이 `rag_index.sqlite3` 파일을 직접 열어 데이터를 읽고 씁니다.

쉽게 비유하면 다음과 같습니다.

- Excel 파일: 표 형태의 데이터를 파일로 보관
- SQLite 파일: 여러 표와 검색 기능을 하나의 파일에 보관
- MySQL 서버: 여러 사람이 접속할 수 있는 별도의 데이터 관리 프로그램

SQLite 파일은 메모장용 텍스트 파일이 아니라 **바이너리 데이터베이스 파일**입니다. 따라서 VS Code의 일반 텍스트 편집기로 열리지 않거나 글자가 깨져 보이는 것이 정상입니다. SQLite Viewer, DB Browser for SQLite 또는 Python의 `sqlite3` 같은 전용 도구로 읽어야 합니다.

## 2. 데이터베이스의 기본 개념

### 데이터베이스

관련된 데이터를 체계적으로 보관하는 공간입니다. 이 프로젝트의 데이터베이스에는 의료 지식 문서 조각과 검색 인덱스가 들어 있습니다.

### 테이블

Excel의 시트와 비슷합니다. 행과 열로 데이터를 보관합니다.

예를 들어 학생 정보를 저장한다면 다음과 같은 테이블을 만들 수 있습니다.

| id | name | score |
|---:|---|---:|
| 1 | 민수 | 90 |
| 2 | 지수 | 85 |

### 행과 열

- 행(row): 학생 한 명처럼 하나의 데이터 항목
- 열(column): 이름, 점수처럼 각 항목의 속성

### SQL

데이터베이스에 명령을 내리는 언어입니다. SQL을 사용해 표를 만들고, 데이터를 추가하고, 찾고, 수정하고, 삭제할 수 있습니다.

## 3. 가장 기본적인 SQL 사용법

### 테이블 만들기

```sql
CREATE TABLE students (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    score INTEGER
);
```

### 데이터 추가하기

```sql
INSERT INTO students (name, score)
VALUES ('민수', 90);
```

### 데이터 읽기

```sql
SELECT id, name, score
FROM students;
```

점수가 90점 이상인 학생만 찾을 수도 있습니다.

```sql
SELECT name, score
FROM students
WHERE score >= 90;
```

### 데이터 수정하기

```sql
UPDATE students
SET score = 95
WHERE name = '민수';
```

### 데이터 삭제하기

```sql
DELETE FROM students
WHERE name = '민수';
```

`UPDATE`나 `DELETE`에서 `WHERE`를 빠뜨리면 모든 행이 변경되거나 삭제될 수 있으므로 특히 주의해야 합니다.

## 4. Python에서 SQLite 사용하기

Python에는 SQLite를 사용할 수 있는 `sqlite3` 모듈이 기본으로 포함되어 있습니다. 별도 데이터베이스 서버를 설치할 필요가 없습니다.

```python
import sqlite3

connection = sqlite3.connect("example.sqlite3")
cursor = connection.execute(
    "SELECT name, score FROM students WHERE score >= ?",
    (90,),
)

for row in cursor:
    print(row)

connection.close()
```

SQL 문자열 안에 값을 직접 붙이지 않고 `?` 자리에 별도로 전달하는 것이 중요합니다.

```python
# 권장 방식
connection.execute(
    "SELECT * FROM students WHERE name = ?",
    (student_name,),
)
```

이 방식을 **매개변수 바인딩**이라고 합니다. 따옴표 오류를 줄이고 SQL 삽입 공격도 예방합니다.

## 5. 이 프로젝트의 SQLite 파일

이 프로젝트의 `rag_index.sqlite3`는 앱의 사용자 계정이나 시험 점수를 저장하는 데이터베이스가 아닙니다. 의료 지식 문서를 빠르게 검색하기 위한 **RAG 검색 인덱스**입니다.

현재 확인된 데이터는 다음과 같습니다.

| 항목 | 개수 |
|---|---:|
| 전체 의료 문서 조각 | 99,742개 |
| 원천 문서 조각 | 87,514개 |
| 전문 QA 조각 | 12,228개 |
| FTS 검색 대상 행 | 99,742개 |

파일 크기는 약 599MB입니다.

## 6. 이 프로젝트의 테이블 구조

### `documents` 테이블

검색 결과로 사용자에게 보여줄 실제 의료 문서 조각을 저장합니다.

| 열 | 의미 |
|---|---|
| `id` | 문서 조각의 고유 번호 |
| `source_type` | `원천 문서` 또는 `전문 QA` |
| `domain` | 의료 분야 |
| `source_name` | 자료 종류나 자료 이름 |
| `source_path` | 원본 JSON 파일의 상대 경로 |
| `content` | 검색과 해설에 사용할 실제 내용 |

프로젝트에서 만드는 SQL은 다음과 같습니다.

```sql
CREATE TABLE documents (
    id INTEGER PRIMARY KEY,
    source_type TEXT NOT NULL,
    domain TEXT,
    source_name TEXT NOT NULL,
    source_path TEXT NOT NULL,
    content TEXT NOT NULL
);
```

### `documents_fts` 가상 테이블

`documents.content`를 빠르게 검색하기 위한 FTS5 전문 검색 인덱스입니다.

```sql
CREATE VIRTUAL TABLE documents_fts USING fts5(content);
```

FTS는 Full-Text Search의 약자입니다. 문서가 수만 개 있어도 모든 내용을 Python으로 하나씩 검사하지 않고, SQLite가 미리 만들어 둔 검색용 색인을 이용해 빠르게 후보를 찾습니다.

책 뒤쪽의 찾아보기를 생각하면 쉽습니다. 책을 처음부터 끝까지 읽는 대신 찾아보기에서 단어가 등장하는 페이지를 바로 찾는 것과 비슷합니다.

## 7. 데이터베이스가 만들어지는 과정

`build_rag_index.py`가 다음 순서로 데이터베이스를 만듭니다.

```text
medical_knowledge_data의 JSON 파일
  → 질문·답변 또는 본문 추출
  → 약 1,100자 크기의 문서 조각으로 분리
  → documents 테이블에 저장
  → documents_fts 검색 인덱스에 등록
  → rag_index.sqlite3 완성
```

문서 조각은 최대 약 1,100자이며, 앞뒤 문맥이 너무 많이 끊기지 않도록 인접 조각이 약 180자 겹칩니다. 가능하면 문장 끝에서 나눕니다.

인덱스를 처음 만들거나 원본 의료 JSON이 변경되었을 때 다음 명령을 실행합니다.

```powershell
python build_rag_index.py
```

주의할 점이 있습니다. 현재 `build_rag_index.py`는 기존 `rag_index.sqlite3`가 있으면 먼저 삭제한 뒤 처음부터 다시 만듭니다. 인덱스를 만드는 도중 강제로 종료하면 완성되지 않은 파일이 남을 수 있으므로, 재생성이 필요할 때만 실행해야 합니다.

## 8. 앱에서 검색되는 과정

사용자가 문제의 해설을 요청하면 다음 과정이 진행됩니다.

```text
시험 문제 + 정답 보기 + 사용자가 고른 보기
  → 최대 12개의 검색어 추출
  → 검색어를 OR 조건으로 연결
  → SQLite FTS5에서 최대 80개 후보 검색
  → 검색어 중복 정도와 BM25 점수로 재정렬
  → 상위 4개 문서 조각 선택
  → 해설 생성 모델에 참고 근거로 전달
  → 정답 근거, 오답 분석, 출처 표시
```

검색은 `local_rag.py`에서 수행됩니다. 핵심 SQL은 다음과 같은 구조입니다.

```sql
SELECT d.source_type,
       d.domain,
       d.source_name,
       d.source_path,
       d.content,
       bm25(documents_fts) AS rank
FROM documents_fts
JOIN documents AS d
  ON d.id = documents_fts.rowid
WHERE documents_fts MATCH ?
ORDER BY rank
LIMIT 80;
```

각 부분의 뜻은 다음과 같습니다.

- `SELECT`: 결과로 가져올 열을 선택
- `FROM`: 검색할 테이블 지정
- `JOIN`: 검색 인덱스와 실제 문서 연결
- `MATCH ?`: 입력된 검색어와 일치하는 문서 검색
- `bm25(...)`: 관련도가 높은 문서를 계산
- `ORDER BY rank`: 관련도 순서로 정렬
- `LIMIT 80`: 후보를 최대 80개로 제한

`?`에는 Python에서 만든 검색문을 매개변수로 안전하게 전달합니다.

## 9. 데이터베이스 내용을 안전하게 확인하는 방법

일반 편집기로 파일을 직접 열지 말고 SQLite 전용 프로그램을 사용하는 것이 좋습니다.

사용 가능한 도구:

- VS Code의 SQLite Viewer 확장
- DB Browser for SQLite
- SQLiteStudio
- Python의 `sqlite3` 모듈

Python으로 테이블 목록을 확인하는 예시는 다음과 같습니다.

```powershell
python -c 'import sqlite3; con=sqlite3.connect("file:rag_index.sqlite3?mode=ro", uri=True); print(con.execute("SELECT name FROM sqlite_master").fetchall())'
```

문서 개수 확인:

```powershell
python -c 'import sqlite3; con=sqlite3.connect("file:rag_index.sqlite3?mode=ro", uri=True); print(con.execute("SELECT COUNT(*) FROM documents").fetchone())'
```

처음 3개 문서의 정보 확인:

```sql
SELECT id, source_type, source_name, source_path
FROM documents
LIMIT 3;
```

`mode=ro`는 read only, 즉 읽기 전용이라는 뜻입니다. 내용을 실수로 변경하지 않고 확인할 때 권장합니다.

## 10. 현재 SQLite가 담당하지 않는 것

현재 `rag_index.sqlite3`에는 다음 정보가 저장되지 않습니다.

- 사용자가 선택한 직종과 연도
- 사용자의 답안
- 정답 또는 오답 기록
- 학습 점수와 통계
- 로그인 계정
- 해설 생성 결과 캐시

이 정보들은 현재 Gradio의 실행 상태나 메모리에서만 처리되고, 앱을 종료하면 유지되지 않습니다.

## 11. 앞으로 사용할 수 있는 방향

프로젝트 문서에서 확정된 현재 용도는 **로컬 의료 지식 FTS 검색**입니다. 아래 항목은 아직 구현되었다는 뜻이 아니라, 향후 SQLite로 구현할 수 있는 개선 방향입니다.

### 학습 이력 저장

사용자가 언제 어떤 문제를 풀었고 어떤 답을 골랐는지 저장할 수 있습니다.

```sql
CREATE TABLE quiz_history (
    id INTEGER PRIMARY KEY,
    job TEXT NOT NULL,
    year TEXT NOT NULL,
    question_id TEXT,
    selected_answer INTEGER,
    correct_answer INTEGER,
    is_correct INTEGER,
    answered_at TEXT NOT NULL
);
```

이 데이터가 있으면 직종별 정답률, 연도별 정답률, 자주 틀리는 문제를 계산할 수 있습니다.

### 오답 노트

틀린 문제와 해설을 저장하고 나중에 다시 풀도록 만들 수 있습니다.

### 해설 캐시

같은 문제에 대해 이미 만든 AI 해설을 저장하면 모델을 매번 실행하지 않아도 되어 응답 시간이 줄어듭니다.

### 검색 품질 평가

어떤 검색어로 어떤 근거가 선택되었는지 기록하면 관련성이 낮은 문서가 선택된 원인을 분석할 수 있습니다.

### 언제 다른 DB가 필요한가?

한 대의 PC에서 개인적으로 사용하는 현재 구조에는 SQLite가 잘 맞습니다. 하지만 다음 상황이라면 PostgreSQL 같은 서버형 데이터베이스를 검토할 수 있습니다.

- 많은 사용자가 동시에 데이터를 작성할 때
- 여러 컴퓨터가 하나의 데이터베이스를 함께 사용해야 할 때
- 사용자 계정과 권한을 정교하게 관리해야 할 때
- 웹 서버를 여러 대 운영해야 할 때

의료 원문을 외부 데이터베이스나 클라우드에 올리려면 AI Hub 데이터 이용정책과 외부 제공·국외 이전 조건을 먼저 확인해야 합니다.

## 12. 핵심 정리

- SQLite는 별도 서버 없이 파일 하나로 사용하는 데이터베이스입니다.
- `rag_index.sqlite3`가 일반 편집기에서 열리지 않는 것은 정상입니다.
- 이 프로젝트에서는 약 10만 개의 의료 문서 조각을 빠르게 검색하는 데 사용합니다.
- `documents`에는 실제 내용이, `documents_fts`에는 빠른 검색용 색인이 들어 있습니다.
- 사용자가 해설을 요청하면 관련 근거 4개를 골라 생성 모델에 전달합니다.
- 현재는 학습 이력을 저장하지 않지만, 앞으로 오답 노트와 통계 등을 SQLite로 확장할 수 있습니다.

## 업데이트 001. SQLite와 임베딩 하이브리드 검색 및 노트북 이전

초기 구현에서는 `rag_index.sqlite3`의 FTS5 검색 결과만 사용했지만, 현재는 다음 두 검색 결과를 결합합니다.

```text
rag_index.sqlite3       형태소·핵심어 FTS5 검색
rag_embeddings.npy      문서 의미 벡터
rag_embedding_ids.npy   벡터 행과 SQLite documents.id 연결
```

두 순위는 Reciprocal Rank Fusion으로 결합됩니다. SQLite는 여전히 원문 조각과 출처 정보의 기준 저장소이며, `.npy` 파일은 SQLite 문서 ID를 가리키는 보조 검색 인덱스입니다. 따라서 SQLite만 새로 만들었거나 파일 크기가 바뀌면 기존 임베딩 메타데이터와 맞지 않아 의미 검색이 자동으로 비활성화될 수 있습니다.

### 노트북에서 Google Drive로 사용할 때

다음 네 파일을 같은 `runtime` 폴더에 함께 보관합니다.

```text
rag_index.sqlite3
rag_embeddings.npy
rag_embedding_ids.npy
rag_embeddings.meta.json
```

`.env`에는 각각의 실제 Google Drive 경로를 지정합니다. 실행 중 동기화 지연으로 파일이 사라진 것처럼 보이지 않도록 `runtime` 폴더를 오프라인 사용 가능 상태로 두는 것이 좋습니다. 여러 PC에서 같은 SQLite 파일을 동시에 다시 구축하거나 쓰지 않습니다. 현재 앱의 검색은 읽기 중심이지만 인덱스 구축 스크립트는 파일을 교체할 수 있습니다.

### 검색 품질 가드레일과 SQLite

가드레일은 SQLite 내용을 수정하지 않습니다. 검색 결과의 `matched_terms`와 임베딩 유사도를 읽어 정답 해설을 생성할 만큼 충분한지만 판단합니다. 근거가 부족하면 모델 실행을 중단하지만 검색된 SQLite 원문은 사용자가 검토할 수 있도록 표시합니다.

### 문서 기록 규칙

앞으로 코드 업데이트가 SQLite 테이블, FTS 검색, 인덱스 파일 또는 경로에 영향을 주면 `업데이트 NNN. 제목` 형식으로 기록합니다. SQLite 영향이 없는 변경도 같은 번호로 `영향 없음`을 남깁니다.
