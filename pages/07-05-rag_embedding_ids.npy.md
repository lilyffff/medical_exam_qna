# `rag_embedding_ids.npy` 해설집

## 무엇인가요?

`rag_embeddings.npy`의 각 행이 SQLite의 어떤 문서인지 알려 주는 22,508개의 정수 ID 배열입니다.

```text
벡터 0번째 행 → ID 배열 0번째 값 → documents.id
벡터 1번째 행 → ID 배열 1번째 값 → documents.id
```

성적표의 각 줄 옆에 학생 이름 대신 학번을 적어 둔 것과 같습니다.

## 실습

```powershell
python -c "import numpy as np; ids=np.load('rag_embedding_ids.npy',mmap_mode='r'); print(ids.shape,ids.dtype,ids[:5])"
```

첫 번째 ID가 가리키는 SQLite 문서를 확인할 수 있습니다.

```powershell
python -c "import sqlite3,numpy as np; i=int(np.load('rag_embedding_ids.npy',mmap_mode='r')[0]); c=sqlite3.connect('file:rag_index.sqlite3?mode=ro',uri=True); print(c.execute('select id,source_type,source_name from documents where id=?',(i,)).fetchone())"
```

## 주의

벡터 파일과 ID 파일의 행 수가 다르면 잘못된 문서를 가리킬 수 있습니다. `local_rag.py`는 실행 전에 두 모양이 맞는지 검사합니다.
