"""형태소·임베딩 하이브리드 RAG의 핵심 회귀 테스트."""

import os
import unittest
from pathlib import Path
from unittest.mock import patch

import local_rag


class TextProcessingTests(unittest.TestCase):
    def test_normalization_and_morphology(self):
        text = "&#x20; 복강내출혈 환자의 소변량이 250 mL입니다."
        normalized = local_rag.normalize_medical_text(text)
        self.assertNotIn("&#x20;", normalized)
        self.assertIn("250 ml", normalized)
        terms = local_rag.query_terms(text)
        self.assertIn("출혈", terms)
        self.assertIn("소변", terms)
        self.assertNotIn("250", terms)
        self.assertNotIn("ml", terms)

    def test_concept_expansion_requires_enough_clues(self):
        _, concepts = local_rag.expand_medical_query("작은 상처에서 출혈이 발생했다")
        self.assertNotIn("저혈량성·출혈성 쇼크와 장기 저관류", concepts)
        expanded, concepts = local_rag.expand_medical_query(
            "복강내출혈 외상 환자에게 소변량 감소가 나타났다"
        )
        self.assertIn("저혈량성·출혈성 쇼크와 장기 저관류", concepts)
        self.assertIn("신장 관류 감소", expanded)


@unittest.skipUnless(
    Path("rag_embeddings.npy").exists() and Path("rag_embedding_ids.npy").exists(),
    "로컬 임베딩 인덱스가 없어서 통합 검색 테스트를 건너뜁니다.",
)
class HybridSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        local_rag._embedding_index.cache_clear()
        local_rag._embedding_model.cache_clear()

    def test_anaphylaxis_prioritizes_epinephrine_evidence(self):
        results = local_rag.search_medical_knowledge(
            "페니실린 투여 직후 호흡곤란과 저혈압이 발생했다. 아나필락시스 에피네프린"
        )
        top_two = " ".join(result["content"] for result in results[:2])
        self.assertIn("에피네프린", top_two)

    def test_tuberculosis_prioritizes_airborne_evidence(self):
        results = local_rag.search_medical_knowledge(
            "객담 도말 양성 폐결핵 환자의 감염관리 공기주의 격리"
        )
        self.assertIn("비말핵", results[0]["content"])

    def test_hemorrhage_combines_shock_and_renal_evidence(self):
        results = local_rag.search_medical_knowledge(
            "복강내출혈 외상 환자의 소변량 250mL 신장혈류량 저하"
        )
        evidence = " ".join(result["content"] for result in results)
        self.assertIn("쇼크", evidence)
        self.assertTrue("신장" in evidence or "소변량" in evidence)
        self.assertEqual(len({result["source_path"] for result in results}), len(results))

    def test_missing_embedding_falls_back_to_fts(self):
        with patch.dict(os.environ, {"RAG_EMBEDDING_PATH": "missing-test-index.npy"}):
            local_rag._embedding_index.cache_clear()
            results = local_rag.search_medical_knowledge("폐결핵 공기주의 격리")
        local_rag._embedding_index.cache_clear()
        self.assertTrue(results)
        self.assertTrue(all("의미 임베딩" not in result["search_method"] for result in results))


if __name__ == "__main__":
    unittest.main()
