"""AI Hub 전문 의학지식 JSON을 로컬 SQLite FTS 인덱스로 변환한다.

원본 JSON은 변경하지 않는다.
"""

import json
import sqlite3
from pathlib import Path

from local_rag import index_path, knowledge_path


def source_metadata(path: Path, root: Path) -> tuple[str, str, str]:
    relative = path.relative_to(root)
    if relative.parts[0] == "TL_라벨링데이터":
        return "전문 QA", relative.parts[1] if len(relative.parts) > 1 else "기타", str(relative)
    return "원천 문서", relative.parts[0], str(relative)


def document_text(payload: dict, source_type: str) -> tuple[str, str]:
    if source_type == "전문 QA":
        question = str(payload.get("question", "")).strip()
        answer = str(payload.get("answer", "")).strip()
        return str(payload.get("domain", "")), f"질문: {question}\n답변: {answer}"
    return str(payload.get("domain", "")), str(payload.get("content", "")).strip()


def chunks(text: str, size: int = 1100, overlap: int = 180):
    text = " ".join(text.split())
    if len(text) <= size:
        yield text
        return
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        # 문장 끝을 우선해 근거 문장이 잘리지 않도록 한다.
        if end < len(text):
            boundary = max(text.rfind(". ", start, end), text.rfind("다. ", start, end))
            if boundary > start + size // 2:
                end = boundary + 1
        yield text[start:end]
        if end == len(text):
            break
        start = max(end - overlap, start + 1)


def main():
    root = knowledge_path()
    database = index_path()
    if not root.exists():
        raise FileNotFoundError(f"전문 의학지식 폴더를 찾지 못했습니다: {root}")

    if database.exists():
        database.unlink()

    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY,
                source_type TEXT NOT NULL,
                domain TEXT,
                source_name TEXT NOT NULL,
                source_path TEXT NOT NULL,
                content TEXT NOT NULL
            );
            CREATE VIRTUAL TABLE documents_fts USING fts5(content);
            """
        )
        count = 0
        skipped = 0
        for path in root.rglob("*.json"):
            source_type, source_name, relative_path = source_metadata(path, root)
            try:
                payload = json.loads(path.read_text(encoding="utf-8-sig"))
                domain, text = document_text(payload, source_type)
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                skipped += 1
                continue
            if not text:
                skipped += 1
                continue
            for chunk in chunks(text):
                cursor = connection.execute(
                    """
                    INSERT INTO documents (source_type, domain, source_name, source_path, content)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (source_type, domain, source_name, relative_path, chunk),
                )
                connection.execute(
                    "INSERT INTO documents_fts (rowid, content) VALUES (?, ?)",
                    (cursor.lastrowid, chunk),
                )
                count += 1
            if count and count % 5000 == 0:
                connection.commit()
                print(f"인덱싱: {count:,}개 문서 조각")

        connection.commit()
    print(f"완료: {database}")
    print(f"검색 문서 조각: {count:,}개, 건너뜀: {skipped:,}개")


if __name__ == "__main__":
    main()
