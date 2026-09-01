"""검색 품질·생성 결과 가드레일의 단위 테스트."""

import unittest

from app import assess_evidence_quality, validate_generated_explanation


class EvidenceQualityGuardrailTests(unittest.TestCase):
    def test_accepts_answer_terms_with_strong_retrieval(self):
        evidence = [
            {
                "content": "출혈성 쇼크에서는 신장 관류와 신장혈류량이 감소하여 소변량이 줄어든다.",
                "matched_terms": ["출혈", "쇼크", "신장", "소변량"],
                "semantic_score": 0.90,
            }
        ]
        accepted, reason = assess_evidence_quality(evidence, "신장혈류량 저하")
        self.assertTrue(accepted, reason)

    def test_rejects_evidence_without_answer_concept(self):
        evidence = [
            {
                "content": "폐결핵은 비말핵을 통해 전파될 수 있다.",
                "matched_terms": ["폐결핵", "비말핵"],
                "semantic_score": 0.92,
            }
        ]
        accepted, reason = assess_evidence_quality(evidence, "신장혈류량 저하")
        self.assertFalse(accepted)
        self.assertIn("정답 보기", reason)


class GeneratedAnswerGuardrailTests(unittest.TestCase):
    def setUp(self):
        self.sources = (
            "[근거 1] 출혈성 쇼크에서는 신장 관류와 신장혈류량이 감소하고 "
            "24시간 소변량이 250mL로 감소할 수 있다."
        )
        self.context = "복강내출혈 환자의 24시간 소변량은 250mL이다. 정답은 신장혈류량 저하이다."

    def test_accepts_grounded_educational_explanation(self):
        text = (
            "1. 정답: 3번입니다. 2. 정답 근거: 출혈성 쇼크로 신장 관류와 신장혈류량이 "
            "감소하면 소변량도 감소합니다 [근거 1]. 3. 오답 분석: 다른 선택지는 이 병태생리와 "
            "직접 연결되지 않습니다. 4. 핵심 암기 포인트: 출혈, 신장 관류, 소변량의 관계입니다."
        )
        self.assertEqual(
            validate_generated_explanation(text, self.sources, self.context, 3, 1), []
        )

    def test_rejects_nonexistent_citation_and_unsupported_measurement(self):
        text = (
            "1. 정답: 3번입니다. 출혈성 쇼크에서는 신장 관류와 신장혈류량이 감소합니다. "
            "소변량이 500mL라는 기준을 적용합니다 [근거 9]. 이 내용은 시험 학습을 위한 "
            "설명이며 핵심은 출혈과 신장 관류의 관계를 이해하는 것입니다."
        )
        problems = validate_generated_explanation(text, self.sources, self.context, 3, 1)
        self.assertTrue(any("근거 번호" in problem for problem in problems))
        self.assertTrue(any("500ml" in problem for problem in problems))


if __name__ == "__main__":
    unittest.main()
