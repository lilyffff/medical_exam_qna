"""SQLite 의료 문서 조각을 multilingual-E5 벡터 인덱스로 변환한다."""

import json
import os
import sqlite3

import numpy as np
import truststore

from embedding_model import encode_embeddings, load_embedding_model
from local_rag import (
    embedding_meta_path,
    embedding_model_id,
    embedding_ids_path,
    embedding_path,
    index_path,
    normalize_medical_text,
)


truststore.inject_into_ssl()


def main() -> None:
    database = index_path()
    if not database.exists():
        raise FileNotFoundError(
            f"SQLite RAG 인덱스가 없습니다: {database}. 먼저 `python build_rag_index.py`를 실행하세요."
        )

    output = embedding_path()
    ids_output = embedding_ids_path()
    metadata_output = embedding_meta_path()
    temporary_output = output.with_name(output.stem + ".building.npy")
    temporary_ids = ids_output.with_name(ids_output.stem + ".building.npy")
    temporary_metadata = metadata_output.with_suffix(metadata_output.suffix + ".building")
    batch_size = int(os.getenv("RAG_EMBEDDING_BATCH_SIZE", "32"))
    max_length = int(os.getenv("RAG_EMBEDDING_MAX_LENGTH", "256"))
    device = os.getenv("RAG_EMBEDDING_DEVICE", "cpu")
    model_name = embedding_model_id()
    _, model, _ = load_embedding_model(device)
    dimension = int(model.config.hidden_size)

    with sqlite3.connect(database) as connection:
        quality_filter = """
            source_type = '전문 QA'
            OR source_name IN (
                'TS_국문_학회 가이드라인',
                'TS_국문_의학 교과서',
                'TS_국문_학술 논문 및 저널',
                'TS_국문_기타'
            )
        """
        count = connection.execute(
            f"SELECT COUNT(*) FROM documents WHERE {quality_filter}"
        ).fetchone()[0]
        if not count:
            raise RuntimeError("임베딩할 고품질 의료 문서를 찾지 못했습니다.")

        vectors = np.lib.format.open_memmap(
            temporary_output,
            mode="w+",
            dtype=np.float32,
            shape=(count, dimension),
        )
        document_ids = np.lib.format.open_memmap(
            temporary_ids, mode="w+", dtype=np.int64, shape=(count,)
        )
        processed = 0
        cursor = connection.execute(
            f"SELECT id, content FROM documents WHERE {quality_filter} ORDER BY id"
        )
        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break
            passages = [f"passage: {normalize_medical_text(row[1])}" for row in rows]
            batch_vectors = encode_embeddings(
                passages, device=device, batch_size=batch_size, max_length=max_length
            )
            vectors[processed : processed + len(rows)] = batch_vectors
            document_ids[processed : processed + len(rows)] = [row[0] for row in rows]
            processed += len(rows)
            if processed % 1000 < len(rows):
                vectors.flush()
                print(f"임베딩: {processed:,}/{count:,} 문서")
        vectors.flush()
        document_ids.flush()
        del vectors
        del document_ids

    metadata = {
        "model": model_name,
        "document_count": count,
        "dimension": dimension,
        "dtype": "float32",
        "normalized": True,
        "query_prefix": "query: ",
        "passage_prefix": "passage: ",
        "max_length": max_length,
        "corpus": "전문 QA + 학회 가이드라인 + 의학 교과서 + 학술 논문 및 저널 + 기타 원천 문서",
        "database_size": database.stat().st_size,
    }
    temporary_metadata.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary_output.replace(output)
    temporary_ids.replace(ids_output)
    temporary_metadata.replace(metadata_output)
    print(f"완료: {output} ({count:,}개 문서, {dimension}차원)")
    print(f"문서 ID: {ids_output}")
    print(f"메타데이터: {metadata_output}")


if __name__ == "__main__":
    main()
