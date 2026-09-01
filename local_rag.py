"""로컬 의료지식용 한국어 형태소 + SQLite FTS + 임베딩 하이브리드 검색."""

import html
import json
import os
import re
import sqlite3
import unicodedata
from functools import lru_cache
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = PROJECT_DIR / "medical_knowledge_data"
DEFAULT_INDEX_PATH = PROJECT_DIR / "rag_index.sqlite3"
DEFAULT_EMBEDDING_PATH = PROJECT_DIR / "rag_embeddings.npy"
DEFAULT_EMBEDDING_IDS_PATH = PROJECT_DIR / "rag_embedding_ids.npy"
DEFAULT_EMBEDDING_META_PATH = PROJECT_DIR / "rag_embeddings.meta.json"
DEFAULT_EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
DEFAULT_CONCEPT_PATH = PROJECT_DIR / "medical_concepts.json"
TOKEN_PATTERN = re.compile(r"[가-힣A-Za-z0-9]+(?:[./-][가-힣A-Za-z0-9]+)*")
SPACE_PATTERN = re.compile(r"\s+")
UNIT_PATTERN = re.compile(r"(?<=\d)\s+(?=(?:ml|mg|g|kg|mmhg|cm|mm|l)\b)", re.IGNORECASE)
CONTENT_WORD_TAGS = {"NNG", "NNP", "NNB", "SL", "VV", "VA", "XR"}
MEASUREMENT_UNITS = {"ml", "mg", "g", "kg", "l", "mm", "cm", "mmhg", "시간", "일", "개월", "년"}
KOREAN_PARTICLES = ("에서", "으로", "에게", "까지", "부터", "보다", "처럼", "의", "이", "가", "은", "는", "을", "를", "에", "로", "와", "과", "도")
COMMON_TERMS = {
    "환자", "대한", "다음", "것", "무엇", "설명", "경우", "가장", "적절", "옳", "아니",
    "위하", "있", "하", "되", "때", "수", "번", "보기", "정답", "선택", "추정", "심하",
    "시간", "하루", "일일", "정도", "이상", "이하",
    "있는", "것은", "심한", "추정할", "ml일", "mg일", "환자",
}


class RagNotReadyError(RuntimeError):
    """로컬 검색 인덱스가 아직 만들어지지 않은 상태."""


def knowledge_path() -> Path:
    return Path(os.getenv("MEDICAL_KNOWLEDGE_PATH", DEFAULT_DATA_DIR))


def index_path() -> Path:
    return Path(os.getenv("RAG_INDEX_PATH", DEFAULT_INDEX_PATH))


def embedding_path() -> Path:
    return Path(os.getenv("RAG_EMBEDDING_PATH", DEFAULT_EMBEDDING_PATH))


def embedding_meta_path() -> Path:
    return Path(os.getenv("RAG_EMBEDDING_META_PATH", DEFAULT_EMBEDDING_META_PATH))


def embedding_ids_path() -> Path:
    return Path(os.getenv("RAG_EMBEDDING_IDS_PATH", DEFAULT_EMBEDDING_IDS_PATH))


def embedding_model_id() -> str:
    return os.getenv("RAG_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)


def concept_path() -> Path:
    return Path(os.getenv("RAG_CONCEPT_PATH", DEFAULT_CONCEPT_PATH))


def normalize_medical_text(text: str) -> str:
    """HTML 엔티티·유니코드·공백·숫자 단위를 검색에 안정적인 형태로 바꾼다."""
    normalized = html.unescape(str(text or ""))
    normalized = unicodedata.normalize("NFKC", normalized).lower()
    normalized = UNIT_PATTERN.sub("", normalized)
    return SPACE_PATTERN.sub(" ", normalized).strip()


@lru_cache(maxsize=1)
def _medical_concepts() -> list[dict]:
    path = concept_path()
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return []
    return payload if isinstance(payload, list) else []


def expand_medical_query(text: str) -> tuple[str, list[str]]:
    """개념 사전에서 충분한 단서가 발견되면 관련 병태생리·동의어를 확장한다."""
    normalized = normalize_medical_text(text)
    compact = normalized.replace(" ", "")
    additions: list[str] = []
    concepts: list[str] = []
    for group in _medical_concepts():
        triggers = [normalize_medical_text(term).replace(" ", "") for term in group.get("triggers", [])]
        matches = sum(bool(trigger and trigger in compact) for trigger in triggers)
        if matches < int(group.get("min_matches", 1)):
            continue
        concepts.append(str(group.get("concept", "의료 개념")))
        for expansion in group.get("expansions", []):
            value = normalize_medical_text(expansion)
            if value and value not in normalized and value not in additions:
                additions.append(value)
    expanded = " ".join([normalized, *additions]).strip()
    return expanded, concepts


@lru_cache(maxsize=1)
def _kiwi():
    """Kiwi는 첫 검색 때만 로딩한다. 설치 실패 시 정규식 검색으로 자동 대체한다."""
    try:
        from kiwipiepy import Kiwi

        return Kiwi()
    except (ImportError, OSError):
        return None


def query_terms(text: str, limit: int = 18) -> list[str]:
    """형태소 원형과 원문 핵심어를 조합해 FTS 검색어를 만든다."""
    normalized = normalize_medical_text(text)
    terms: list[str] = []

    def add(term: str) -> None:
        value = term.strip().lower()
        if (
            len(value) < 2
            or value.isdigit()
            or value in MEASUREMENT_UNITS
            or value in COMMON_TERMS
            or value in terms
        ):
            return
        terms.append(value)

    kiwi = _kiwi()
    if kiwi is not None:
        try:
            for token in kiwi.tokenize(normalized, normalize_coda=True):
                if token.tag in CONTENT_WORD_TAGS:
                    add(token.form)
                if len(terms) >= limit:
                    return terms
        except (RuntimeError, ValueError):
            # 형태소 분석이 특정 비정상 입력에서 실패해도 기존 정규식 검색은 계속한다.
            pass

    # 복합 의학용어는 형태소로 분해된 단어와 원형 전체를 모두 보존한다.
    for term in TOKEN_PATTERN.findall(normalized):
        # 수치 표현은 의미 검색 문장에는 남기되 FTS 순위를 지배하지 않게 한다.
        if any(character.isdigit() for character in term):
            continue
        stripped = term
        for particle in KOREAN_PARTICLES:
            if stripped.endswith(particle) and len(stripped) - len(particle) >= 2:
                stripped = stripped[: -len(particle)]
                break
        add(stripped)
        if len(terms) >= limit:
            break
    return terms


def _snippet(text: str, limit: int = 600) -> str:
    compact = " ".join(str(text).split())
    return compact if len(compact) <= limit else compact[:limit].rstrip() + "…"


def _fts_candidates(connection: sqlite3.Connection, terms: list[str], limit: int) -> list[sqlite3.Row]:
    if not terms:
        return []
    safe_terms = [term.replace('"', "") for term in terms if term.replace('"', "")]
    fts_query = " OR ".join(f'"{term}"' for term in safe_terms)
    broad_rows = connection.execute(
        """
        SELECT d.id, d.source_type, d.domain, d.source_name, d.source_path, d.content,
               bm25(documents_fts) AS lexical_score
        FROM documents_fts
        JOIN documents AS d ON d.id = documents_fts.rowid
        WHERE documents_fts MATCH ?
        ORDER BY lexical_score
        LIMIT ?
        """,
        (fts_query, limit),
    ).fetchall()
    rows_by_id = {int(row["id"]): row for row in broad_rows}
    # 긴 복합 의학용어는 OR 검색의 흔한 단어에 밀릴 수 있어 개별 검색 후보도 확보한다.
    for term in sorted(terms, key=len, reverse=True)[:8]:
        rows = connection.execute(
            """
            SELECT d.id, d.source_type, d.domain, d.source_name, d.source_path, d.content,
                   bm25(documents_fts) AS lexical_score
            FROM documents_fts
            JOIN documents AS d ON d.id = documents_fts.rowid
            WHERE documents_fts MATCH ?
            ORDER BY lexical_score
            LIMIT 10
            """,
            (f'"{term.replace(chr(34), "")}"',),
        ).fetchall()
        rows_by_id.update((int(row["id"]), row) for row in rows)
    return list(rows_by_id.values())


@lru_cache(maxsize=1)
def _embedding_model():
    from embedding_model import load_embedding_model

    device = os.getenv("RAG_EMBEDDING_DEVICE", "cpu")
    return load_embedding_model(device)


@lru_cache(maxsize=1)
def _embedding_index():
    """벡터 파일을 메모리 매핑해 전체 파일을 RAM에 복사하지 않는다."""
    import numpy as np

    vectors_file = embedding_path()
    ids_file = embedding_ids_path()
    metadata_file = embedding_meta_path()
    if not vectors_file.exists() or not ids_file.exists() or not metadata_file.exists():
        return None
    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    if metadata.get("model") != embedding_model_id():
        return None
    database = index_path()
    if not database.exists() or metadata.get("database_size") != database.stat().st_size:
        # SQLite를 다시 만들었는데 벡터만 예전 상태인 경우 조용히 FTS로 전환한다.
        return None
    vectors = np.load(vectors_file, mmap_mode="r")
    document_ids = np.load(ids_file, mmap_mode="r")
    if (
        vectors.ndim != 2
        or document_ids.ndim != 1
        or vectors.shape[0] != metadata.get("document_count")
        or document_ids.shape[0] != vectors.shape[0]
    ):
        return None
    return vectors, document_ids, metadata


def _semantic_candidates(
    connection: sqlite3.Connection, query: str, limit: int
) -> tuple[list[sqlite3.Row], dict[int, float]]:
    index = _embedding_index()
    if index is None:
        return [], {}

    import numpy as np

    vectors, document_ids, metadata = index
    from embedding_model import encode_embeddings

    device = os.getenv("RAG_EMBEDDING_DEVICE", "cpu")
    max_length = int(os.getenv("RAG_EMBEDDING_MAX_LENGTH", "256"))
    _embedding_model()
    query_vector = encode_embeddings(
        [f"query: {normalize_medical_text(query)}"],
        device=device,
        batch_size=1,
        max_length=max_length,
    )[0]
    scores = np.asarray(vectors @ query_vector)
    candidate_count = min(limit, scores.size)
    if candidate_count == 0:
        return [], {}
    positions = np.argpartition(scores, -candidate_count)[-candidate_count:]
    positions = positions[np.argsort(scores[positions])[::-1]]
    ids = [int(document_ids[position]) for position in positions]
    score_by_id = {document_id: float(scores[position]) for document_id, position in zip(ids, positions)}
    placeholders = ",".join("?" for _ in ids)
    rows = connection.execute(
        f"""
        SELECT id, source_type, domain, source_name, source_path, content
        FROM documents
        WHERE id IN ({placeholders})
        """,
        ids,
    ).fetchall()
    row_by_id = {int(row["id"]): row for row in rows}
    return [row_by_id[document_id] for document_id in ids if document_id in row_by_id], score_by_id


def _matched_terms(content: str, terms: list[str]) -> list[str]:
    normalized = normalize_medical_text(content)
    return [term for term in terms if term in normalized]


def search_medical_knowledge(question: str, top_k: int = 4) -> list[dict]:
    """형태소 FTS와 의미 임베딩 결과를 결합해 설명 가능한 근거를 반환한다."""
    database = index_path()
    if not database.exists():
        raise RagNotReadyError(
            "로컬 RAG 인덱스가 없습니다. `python build_rag_index.py`를 한 번 실행하세요."
        )

    normalized_query, expanded_concepts = expand_medical_query(question)
    terms = query_terms(normalized_query)
    if not terms and not normalized_query:
        return []

    candidate_limit = int(os.getenv("RAG_CANDIDATE_LIMIT", "100"))
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        lexical_rows = _fts_candidates(connection, terms, candidate_limit)
        lexical_rows = sorted(
            lexical_rows,
            key=lambda row: (
                -sum(len(term) ** 2 for term in _matched_terms(row["content"], terms)),
                -len(_matched_terms(row["content"], terms)),
                float(row["lexical_score"]),
            ),
        )
        try:
            semantic_rows, semantic_scores = _semantic_candidates(
                connection, normalized_query, candidate_limit
            )
        except (ImportError, OSError, RuntimeError, ValueError):
            semantic_rows, semantic_scores = [], {}

    # Reciprocal Rank Fusion으로 BM25와 코사인 유사도의 서로 다른 척도를 순위 결합한다.
    fusion: dict[int, float] = {}
    rows_by_id: dict[int, sqlite3.Row] = {}
    methods: dict[int, set[str]] = {}
    rrf_k = 60
    for rank, row in enumerate(lexical_rows, start=1):
        document_id = int(row["id"])
        rows_by_id[document_id] = row
        fusion[document_id] = fusion.get(document_id, 0.0) + 1.0 / (rrf_k + rank)
        methods.setdefault(document_id, set()).add("형태소·키워드")
    for rank, row in enumerate(semantic_rows, start=1):
        document_id = int(row["id"])
        rows_by_id[document_id] = row
        fusion[document_id] = fusion.get(document_id, 0.0) + 1.2 / (rrf_k + rank)
        methods.setdefault(document_id, set()).add("의미 임베딩")

    ranked_ids = sorted(fusion, key=fusion.get, reverse=True)
    results: list[dict] = []
    used_paths: set[str] = set()
    for document_id in ranked_ids:
        row = rows_by_id[document_id]
        source_path = str(row["source_path"])
        if source_path in used_paths:
            continue
        matched = _matched_terms(row["content"], terms)
        results.append(
            {
                "source_type": row["source_type"],
                "domain": row["domain"],
                "source_name": row["source_name"],
                "source_path": source_path,
                "content": _snippet(row["content"]),
                "search_method": " + ".join(sorted(methods[document_id])),
                "matched_terms": matched[:8],
                "semantic_score": semantic_scores.get(document_id),
                "fusion_score": fusion[document_id],
                "expanded_concepts": expanded_concepts,
            }
        )
        used_paths.add(source_path)
        if len(results) == top_k:
            break
    return results


def format_sources(results: list[dict]) -> str:
    if not results:
        return "검색된 전문 의학지식 근거가 없습니다."

    blocks = []
    for number, result in enumerate(results, start=1):
        label = f"{result['source_type']} · {result['source_name']}"
        matched = ", ".join(result.get("matched_terms", [])) or "의미 유사성"
        semantic_score = result.get("semantic_score")
        score_text = f" · 의미 유사도 {semantic_score:.3f}" if semantic_score is not None else ""
        concepts = ", ".join(result.get("expanded_concepts", []))
        concept_text = f"\n확장 의료 개념: {concepts}" if concepts else ""
        blocks.append(
            f"[근거 {number}: {label}]\n"
            f"선정 방식: {result.get('search_method', '키워드')} · 일치 개념: {matched}{score_text}"
            f"{concept_text}\n"
            f"{result['content']}\n파일: `{result['source_path']}`"
        )
    return "\n\n".join(blocks)
