"""의료국가시험 연습 앱.

실행:
    python app.py

선택 사항:
    MEDICAL_LORA_ADAPTER=/path/to/adapter python app.py
"""

import os
import random
import re
import socket
from copy import deepcopy
from functools import lru_cache
from pathlib import Path

# `.env`를 가장 먼저 읽어, 데이터셋·모델 라이브러리도 프록시와 토큰 설정을 사용하게 한다.
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

import gradio as gr

import truststore
truststore.inject_into_ssl()

from datasets import load_dataset
from local_rag import (
    RagNotReadyError,
    format_sources,
    normalize_medical_text,
    query_terms,
    search_medical_knowledge,
)


JOBS = {
    "의사": "doctor",
    "간호사": "nurse",
    "약사": "pharm",
    "치과의사": "dentist",
}
CHOICE_KEYS = ["A", "B", "C", "D", "E"]
DATASET_ID = os.getenv("KORMED_DATASET_ID", "sean0042/KorMedMCQA")
HF_TOKEN = os.getenv("HF_TOKEN") or None
SAFETY_NOTICE = (
    "⚠️ 교육·시험 대비용 서비스입니다. 실제 진단, 처방, 투약 또는 응급 판단에 사용하지 마세요."
)


def app_server_settings() -> tuple[str, int]:
    """같은 Wi-Fi 접속에 사용할 Gradio 서버 주소와 포트를 반환한다.

    0.0.0.0은 PC의 모든 네트워크 인터페이스에서 요청을 받는다는 뜻이다.
    Gradio 공개 공유 링크는 launch()에서 별도로 끈 상태이므로, 이 설정만으로
    인터넷 외부 공개가 활성화되지는 않는다.
    """
    host = os.getenv("APP_HOST", "0.0.0.0").strip() or "0.0.0.0"
    raw_port = os.getenv("APP_PORT", "7860").strip()
    try:
        port = int(raw_port)
    except ValueError as error:
        raise ValueError(f"APP_PORT는 숫자여야 합니다: {raw_port!r}") from error
    if not 1 <= port <= 65535:
        raise ValueError(f"APP_PORT는 1~65535 범위여야 합니다: {port}")
    return host, port


def lan_access_urls(port: int) -> list[str]:
    """모바일 브라우저에 입력할 수 있는 이 PC의 사설 IPv4 주소를 찾는다."""
    addresses: set[str] = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = info[4][0]
            if not address.startswith(("127.", "169.254.")):
                addresses.add(address)
    except socket.gaierror:
        # 주소 자동 탐색 실패가 앱 실행 자체를 막지는 않게 한다.
        return []
    return [f"http://{address}:{port}" for address in sorted(addresses)]


def print_mobile_access_guide(host: str, port: int) -> None:
    """15단계인 같은 Wi-Fi 모바일 접속 방법을 터미널에 안내한다."""
    print(f"PC에서 접속: http://127.0.0.1:{port}")
    if host == "0.0.0.0":
        urls = lan_access_urls(port)
        if urls:
            print("같은 Wi-Fi의 모바일 브라우저에서 다음 주소 중 하나를 여세요:")
            for url in urls:
                print(f"  {url}")
        else:
            print("모바일 주소를 자동으로 찾지 못했습니다. `ipconfig`의 IPv4 주소를 확인하세요.")
        print("접속이 안 되면 Windows 방화벽에서 Python을 '개인 네트워크'에 허용하세요.")
    else:
        print(f"현재 APP_HOST={host!r}입니다. 모바일 접속에는 보통 APP_HOST=0.0.0.0을 사용합니다.")


@lru_cache(maxsize=4)
def get_dataset(job: str):
    """직종 데이터셋을 한 번만 내려받아 메모리에 보관한다."""
    return load_dataset(DATASET_ID, JOBS[job], token=HF_TOKEN)


def row_year(row: dict) -> str:
    """데이터셋의 연도 값이 숫자/문자열 어느 쪽이어도 비교한다."""
    return str(row.get("year", "")).strip()


@lru_cache(maxsize=4)
def questions_by_year(job: str) -> dict[str, list[dict]]:
    """평가용 분할까지 포함해, 실제로 존재하는 연도별 문항을 만든다."""
    grouped: dict[str, list[dict]] = {}
    dataset_dict = get_dataset(job)
    for split in ("train", "dev", "test"):
        for row in dataset_dict[split]:
            question = dict(row)
            grouped.setdefault(row_year(question), []).append(question)
    return grouped


def available_years(job: str) -> list[str]:
    return sorted(questions_by_year(job), key=int)


def random_question(job: str, year: str):
    """선택한 직종·연도에 있는 모든 분할의 문항 중 하나를 반환한다."""
    candidates = questions_by_year(job).get(str(year), [])
    if not candidates:
        return None
    return random.choice(candidates)


def question_markdown(row: dict) -> str:
    choices = "\n".join(
        f"**{index}.** {row.get(key, '')}" for index, key in enumerate(CHOICE_KEYS, start=1)
    )
    return f"### 문제\n\n{row.get('question', '')}\n\n{choices}"


def answer_number(row: dict) -> int:
    """KorMedMCQA의 1~5 정답 값을 정수로 정규화한다."""
    return int(str(row["answer"]).strip())


@lru_cache(maxsize=1)
def get_explainer():
    """필요할 때만 해설 생성 모델을 불러온다.

    MEDICAL_LORA_ADAPTER 환경 변수가 있으면 사용자가 제공한 의료 LoRA 어댑터를
    기본 Qwen 모델 위에 연결한다. 4비트 bitsandbytes 양자화는 사용하지 않아
    CUDA/bitsandbytes 버전 충돌을 피한다.
    """
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

    model_id = os.getenv("MEDICAL_BASE_MODEL", "Qwen/Qwen2.5-1.5B-Instruct")
    trust_remote_code = os.getenv("MEDICAL_TRUST_REMOTE_CODE", "false").lower() in {
        "1", "true", "yes", "on"
    }
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    tokenizer = AutoTokenizer.from_pretrained(
        model_id, trust_remote_code=trust_remote_code
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        dtype=dtype,
        device_map="auto" if torch.cuda.is_available() else None,
        trust_remote_code=trust_remote_code,
    )

    adapter_path = os.getenv("MEDICAL_LORA_ADAPTER")
    if adapter_path:
        from peft import PeftModel

        model = PeftModel.from_pretrained(model, adapter_path)

    return pipeline("text-generation", model=model, tokenizer=tokenizer)


def fit_prompt_to_model(prompt_without_sources: str, sources: str, tokenizer, max_new_tokens: int) -> str:
    """생성 여유를 남기고 검색 근거를 모델의 컨텍스트 크기에 맞춘다."""
    model_limit = getattr(tokenizer, "model_max_length", 2048)
    # 일부 토크나이저는 사실상 무한대를 뜻하는 매우 큰 값을 사용한다.
    if not isinstance(model_limit, int) or model_limit > 100_000:
        model_limit = 2048
    # 채팅 템플릿이 추가하는 시스템 토큰을 위한 여유도 확보한다.
    input_limit = max(256, model_limit - max_new_tokens - 128)
    prefix_ids = tokenizer.encode(prompt_without_sources, add_special_tokens=False)
    available = max(0, input_limit - len(prefix_ids))
    source_ids = tokenizer.encode(
        sources,
        add_special_tokens=False,
        truncation=True,
        max_length=max(1, available),
    ) if available else []
    fitted_sources = tokenizer.decode(source_ids, skip_special_tokens=True)
    return f"{prompt_without_sources}{fitted_sources}"


def apply_chat_template(prompt: str, tokenizer) -> str:
    """Instruct 모델이면 해당 모델이 학습한 대화 형식으로 프롬프트를 감싼다."""
    if not getattr(tokenizer, "chat_template", None):
        return prompt
    return tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}],
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )


def invalid_explanation(text: str) -> bool:
    """짧거나 같은 단어·구절을 되풀이하는 퇴행성 출력을 걸러낸다."""
    normalized = " ".join(text.split())
    if len(normalized) < 80:
        return True
    if normalized.count("정답 근거") + normalized.count("정답:") > 4:
        return True

    words = normalized.split()
    if len(words) >= 10:
        dominant_word_count = max((words.count(word) for word in set(words)), default=0)
        if dominant_word_count / len(words) > 0.35:
            return True
        # 두 단어 이상으로 된 같은 구절이 연달아 반복되는 경우를 잡는다.
        for width in range(2, min(9, len(words) // 3 + 1)):
            for start in range(len(words) - width * 3 + 1):
                phrase = words[start : start + width]
                if (
                    words[start + width : start + width * 2] == phrase
                    and words[start + width * 2 : start + width * 3] == phrase
                ):
                    return True

    # 토크나이저가 공백 없이 같은 긴 문자열을 붙여 내보내는 경우도 포함한다.
    return re.search(r"(.{12,}?)\1{2,}", normalized) is not None


class GuardrailViolation(ValueError):
    """근거 품질 또는 생성 결과 안전성 검사를 통과하지 못한 상태."""


def assess_evidence_quality(evidence: list[dict], correct_text: str) -> tuple[bool, str]:
    """검색 결과가 정답 해설을 생성할 만큼 직접적인지 보수적으로 검사한다."""
    if not evidence:
        return False, "검색된 근거가 없습니다."

    answer_terms = query_terms(correct_text, limit=12)
    evidence_text = normalize_medical_text(
        " ".join(str(item.get("content", "")) for item in evidence)
    )
    answer_matches = [term for term in answer_terms if term in evidence_text]
    best_matched_count = max(
        (len(item.get("matched_terms", [])) for item in evidence), default=0
    )
    best_semantic_score = max(
        (
            float(item["semantic_score"])
            for item in evidence
            if item.get("semantic_score") is not None
        ),
        default=0.0,
    )
    semantic_threshold = float(os.getenv("RAG_GUARDRAIL_MIN_SEMANTIC", "0.86"))

    # 정답이 숫자뿐이라 핵심어를 만들 수 없는 경우에는 문제 전체의 검색 일치도를 사용한다.
    answer_supported = not answer_terms or bool(answer_matches)
    retrieval_supported = (
        best_matched_count >= 2
        or (best_matched_count >= 1 and best_semantic_score >= semantic_threshold)
    )
    if not answer_supported:
        return False, "검색 근거에서 정답 보기의 핵심 개념을 확인하지 못했습니다."
    if not retrieval_supported:
        return (
            False,
            "검색어 일치와 의미 유사도가 해설을 생성하기에 충분하지 않습니다. "
            f"(최대 핵심어 일치 {best_matched_count}개, 최고 의미 유사도 {best_semantic_score:.3f})",
        )
    return (
        True,
        f"정답 핵심어 {len(answer_matches)}개 일치, 최대 검색 핵심어 {best_matched_count}개 일치, "
        f"최고 의미 유사도 {best_semantic_score:.3f}",
    )


MEASUREMENT_PATTERN = re.compile(
    # `250mL이다`, `3개월간`처럼 단위 뒤에 조사가 붙는 한국어 문장도 포착한다.
    r"\d+(?:\.\d+)?\s*(?:%|mg|mcg|g|kg|ml|l|mmhg|mm|cm|시간|일|주|개월|년)",
    re.IGNORECASE,
)
UNSAFE_ADVICE_PATTERNS = (
    r"(?:당신|사용자|현재 증상).{0,20}(?:진단|복용|투여|중단|증량|감량)",
    r"(?:즉시\s*)?(?:119|응급실).{0,12}(?:연락|신고|가세요|가야)",
    r"(?:약|약물|처방약).{0,20}(?:복용하세요|중단하세요|늘리세요|줄이세요)",
)


def validate_generated_explanation(
    text: str,
    sources: str,
    allowed_context: str,
    correct: int,
    evidence_count: int,
) -> list[str]:
    """생성문이 근거 범위와 시험 학습 목적을 벗어났는지 사후 검사한다."""
    problems: list[str] = []
    if invalid_explanation(text):
        problems.append("해설이 지나치게 짧거나 같은 표현을 반복합니다.")
    if f"{correct}번" not in text:
        problems.append("생성된 해설의 정답 번호를 확인할 수 없습니다.")

    for pattern in UNSAFE_ADVICE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
            problems.append("개별 사용자를 대상으로 한 진료·투약 지시가 포함되었습니다.")
            break

    citations = [int(number) for number in re.findall(r"\[근거\s*(\d+)\]", text)]
    if any(number < 1 or number > evidence_count for number in citations):
        problems.append("검색 결과에 존재하지 않는 근거 번호를 인용했습니다.")

    source_terms = set(query_terms(sources, limit=80))
    generated_terms = set(query_terms(text, limit=80))
    if len(source_terms & generated_terms) < 2:
        problems.append("생성된 해설과 검색 근거 사이의 핵심 개념 연결이 부족합니다.")

    allowed_measurements = {
        normalize_medical_text(value)
        for value in MEASUREMENT_PATTERN.findall(f"{allowed_context} {sources}")
    }
    generated_measurements = {
        normalize_medical_text(value) for value in MEASUREMENT_PATTERN.findall(text)
    }
    unsupported_measurements = sorted(generated_measurements - allowed_measurements)
    if unsupported_measurements:
        problems.append(
            "검색 근거에 없는 수치가 포함되었습니다: " + ", ".join(unsupported_measurements)
        )
    return problems


def make_explanation(row: dict, selected: int) -> str:
    """로컬 전문 의학지식 근거를 검색해 교육용 해설을 생성한다."""
    correct = answer_number(row)
    correct_text = row.get(CHOICE_KEYS[correct - 1], "")
    selected_text = row.get(CHOICE_KEYS[selected - 1], "")
    # 정답을 입증할 근거가 사용자의 오답 문구에 끌려가지 않도록
    # 문제와 정답 보기만 검색한다. 선택한 오답은 아래 해설 프롬프트에서 별도로 분석한다.
    search_query = " ".join([str(row.get("question", "")), correct_text])

    try:
        evidence = search_medical_knowledge(search_query)
    except RagNotReadyError as error:
        return (
            f"정답은 **{correct}번: {correct_text}**입니다.\n\n"
            f"로컬 전문 의학지식 검색을 아직 준비하지 못했습니다. {error}\n\n{SAFETY_NOTICE}"
        )

    if not evidence:
        return (
            f"정답은 **{correct}번: {correct_text}**입니다.\n\n"
            "관련 전문 의학지식 근거를 찾지 못했습니다. 다른 문제를 선택하거나 검색 인덱스를 다시 만드세요.\n\n"
            f"{SAFETY_NOTICE}"
        )

    sources = format_sources(evidence)
    evidence_is_sufficient, evidence_quality = assess_evidence_quality(evidence, correct_text)
    if not evidence_is_sufficient:
        return (
            f"## 정답\n\n**{correct}번: {correct_text}**\n\n"
            "## 가드레일: 해설 생성 중단\n\n"
            f"{evidence_quality} 검색 근거만으로 정답을 입증하기 어려워 생성 모델을 실행하지 않았습니다.\n\n"
            f"## 검색된 전문 의학지식 근거\n\n{sources}\n\n{SAFETY_NOTICE}"
        )

    choices_text = chr(10).join(
        f"{i}. {row.get(key, '')}" for i, key in enumerate(CHOICE_KEYS, start=1)
    )
    prompt_without_sources = f"""당신은 한국 의료국가시험의 교육용 해설자입니다.
아래의 [검색 근거]만 사용해 다음 객관식 문제의 해설을 한국어로 작성하세요.
정답은 {correct}번이며, 학습자가 고른 답은 {selected}번입니다.

검색 근거 밖의 사전 지식이나 추측은 사용하지 마세요.
근거가 부족하면 부족하다고 명시하고 새로운 사실을 만들어 보완하지 마세요.
의학적 설명에는 가능한 한 해당 출처 번호를 [근거 1] 형식으로 표시하세요.
존재하지 않는 근거 번호를 만들지 마세요.

문제: {row.get('question', '')}
보기:
{choices_text}

반드시 다음 순서로 간결하게 답하세요.
1. 정답: {correct}번
2. 정답 근거: 시험 학습에 필요한 의학적 원리
3. 오답 분석: 학습자가 고른 {selected}번이 맞지 않는 이유
4. 핵심 암기 포인트

검색 근거에 없는 의학적 사실을 추정하거나 추가하지 마세요. 개별 환자에 대한 진단·치료 지시는 하지 마세요.
이 출력은 실제 진료가 아니라 시험 학습용 해설입니다.

[검색 근거]
"""
    try:
        explainer = get_explainer()
        max_new_tokens = 300
        prompt = fit_prompt_to_model(
            prompt_without_sources, sources, explainer.tokenizer, max_new_tokens
        )
        prompt = apply_chat_template(prompt, explainer.tokenizer)
        # 일부 모델에는 기본 max_length=20이 들어 있다. 생성 인자를 따로
        # 넘기지 않고 복사한 GenerationConfig 하나만 사용해 Transformers의
        # 중복 설정 경고와 max_length 충돌을 피한다.
        generation_config = deepcopy(explainer.model.generation_config)
        generation_config.max_new_tokens = max_new_tokens
        generation_config.max_length = None
        generation_config.do_sample = False
        generated = explainer(
            prompt,
            generation_config=generation_config,
            return_full_text=False,
        )[0]["generated_text"].strip()
        allowed_context = f"{row.get('question', '')}\n{choices_text}"
        guardrail_problems = validate_generated_explanation(
            generated,
            sources,
            allowed_context,
            correct,
            len(evidence),
        )
        if guardrail_problems:
            raise GuardrailViolation(" ".join(guardrail_problems))
        return (
            f"{generated}\n\n---\n\n"
            f"## 검색 품질 검사\n\n통과: {evidence_quality}\n\n"
            f"## 참고 근거\n\n{sources}\n\n{SAFETY_NOTICE}"
        )
    except Exception as error:  # 모델 미설치·GPU 부족 상황에서도 정답은 보여 준다.
        if isinstance(error, GuardrailViolation):
            model_message = (
                "생성 결과가 안전성·근거 일치 검사를 통과하지 못해 해설을 표시하지 않았습니다. "
                f"검사 내용: {error}"
            )
        elif isinstance(error, ValueError):
            model_message = (
                "연결한 해설 모델이 한국어 시험 해설 형식에 맞는 응답을 만들지 못했습니다. "
                "더 적합한 한국어 의료 모델을 설정한 뒤 다시 시도하세요."
            )
        else:
            model_message = (
                "해설 생성 중 오류가 발생했습니다. 앱을 다시 시작한 뒤에도 반복되면 "
                "모델 설정과 설치 상태를 확인하세요. CPU에서도 실행할 수 있지만 시간이 더 걸릴 수 있습니다."
            )
        return (
            f"## 정답\n\n**{correct}번: {correct_text}**\n\n"
            f"선택한 답: {selected}번: {selected_text}\n\n"
            f"{model_message}\n\n"
            f"## 검색된 전문 의학지식 근거\n\n{sources}\n\n"
            f"기술 정보: `{type(error).__name__}`\n\n{SAFETY_NOTICE}"
        )


def select_job(job: str):
    """직종을 선택하면 데이터에 실제 있는 연도만 연도 선택기에 넣는다."""
    button_updates = [
        gr.update(variant="primary" if name == job else "secondary")
        for name in JOBS
    ]
    try:
        years = available_years(job)
        return (
            job,
            gr.update(choices=years, value=years[-1], interactive=True),
            f"**{job}** 기출문제에서 선택 가능한 연도: {', '.join(years)}",
            *button_updates,
        )
    except Exception as error:
        return (
            job,
            gr.update(choices=[], value=None, interactive=False),
            f"{job} 데이터를 불러오지 못했습니다: `{type(error).__name__}`",
            *button_updates,
        )


def begin_quiz(job: str | None, year: str | None):
    if not job or not year:
        return (
            None,
            "먼저 직종 카드를 누르고 출제 연도를 선택하세요.",
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(value="", visible=False),
            gr.update(visible=False),
            gr.update(value="", visible=False),
        )
    row = random_question(job, year)
    if row is None:
        return (
            None,
            "선택한 연도의 문항을 찾지 못했습니다. 다른 연도를 선택하세요.",
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(value="", visible=False),
            gr.update(visible=False),
            gr.update(value="", visible=False),
        )
    return (
        row,
        question_markdown(row),
        gr.update(value=None, visible=True),
        gr.update(visible=True),
        gr.update(value="", visible=False),
        gr.update(visible=False),
        gr.update(value="", visible=False),
    )


def grade_answer(row: dict | None, selected: str):
    if not row:
        return (
            gr.update(value="먼저 직종과 연도를 선택해 문제를 불러오세요.", visible=True),
            gr.update(visible=False),
            gr.update(value="", visible=False),
        )
    if not selected:
        return (
            gr.update(value="답안을 하나 선택하세요.", visible=True),
            gr.update(visible=False),
            gr.update(value="", visible=False),
        )

    picked = int(selected[0])
    correct = answer_number(row)
    if picked == correct:
        return (
            gr.update(value="### 정답입니다! 🎉\n\n해설이 필요하면 **정답 해설 보기**를 누르세요.", visible=True),
            gr.update(visible=True),
            gr.update(value="", visible=False),
        )
    return (
        gr.update(
            value=(
                f"### 오답입니다. 정답은 **{correct}번**입니다.\n\n"
                "해설이 필요하면 **정답 해설 보기**를 누르세요."
            ),
            visible=True,
        ),
        gr.update(visible=True),
        gr.update(value="", visible=False),
    )


def show_explanation(row: dict | None, selected: str):
    if not row or not selected:
        yield (
            gr.update(value="문제와 답안을 먼저 선택하세요.", visible=True),
            gr.update(value="정답 해설 보기", interactive=True, elem_classes=[]),
        )
        return

    # 첫 번째 응답을 즉시 보내 버튼을 잠그고 테두리 애니메이션을 시작한다.
    yield (
        gr.update(value="", visible=False),
        gr.update(value="해설 생성 중...", interactive=False, elem_classes=["explanation-loading"]),
    )

    try:
        explanation_text = make_explanation(row, int(selected[0]))
    except Exception as exc:
        print(f"[해설 생성 오류] {exc}")
        explanation_text = (
            "해설을 생성하는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
        )

    # 검색·생성이 끝나면 결과를 표시하고 버튼을 원래 상태로 복구한다.
    yield (
        gr.update(value=explanation_text, visible=True),
        gr.update(value="정답 해설 보기", interactive=True, elem_classes=[]),
    )


with gr.Blocks(title="의료국가시험 랜덤 문제") as demo:
    gr.Markdown("# 의료국가시험 랜덤 문제\n직종과 연도를 고르고, 실제 시험처럼 문제를 풀어보세요.")
    gr.Markdown(SAFETY_NOTICE)

    question_state = gr.State(None)
    selected_job = gr.State(None)

    with gr.Column(elem_id="home-screen"):
        gr.Markdown("## 직종을 선택하세요")
        with gr.Row(elem_id="job-cards"):
            job_buttons = {
                job: gr.Button(job, variant="secondary", elem_classes=["job-card"])
                for job in JOBS
            }
        year = gr.Radio([], label="출제 연도", interactive=False)
        selection_status = gr.Markdown("직종 카드를 선택하면 해당 직종에 있는 연도만 표시됩니다.")
        start = gr.Button("무작위 문제 시작", variant="primary")

    gr.Markdown("---")
    problem = gr.Markdown("직종과 연도를 선택한 뒤 문제를 시작하세요.")
    answer = gr.Radio([f"{number}번" for number in range(1, 6)], label="내 답안", visible=False)
    submit = gr.Button("정답 확인", variant="primary", visible=False)
    result = gr.Markdown(visible=False)
    # 해설 생성 중인 버튼에만 로딩 애니메이션을 적용하기 위한 전용 id이다.
    explanation = gr.Button("정답 해설 보기", visible=False, elem_id="explanation-button")
    explanation_output = gr.Markdown(visible=False)

    for job, button in job_buttons.items():
        button.click(
            lambda value=job: select_job(value),
            outputs=[selected_job, year, selection_status, *job_buttons.values()],
        )

    start.click(
        begin_quiz,
        inputs=[selected_job, year],
        outputs=[question_state, problem, answer, submit, result, explanation, explanation_output],
    )
    submit.click(
        grade_answer,
        inputs=[question_state, answer],
        outputs=[result, explanation, explanation_output],
    )
    explanation.click(
        show_explanation,
        inputs=[question_state, answer],
        outputs=[explanation_output, explanation],
        show_progress="hidden",
        trigger_mode="once",
    )

    gr.HTML(
        """<style>
        #job-cards { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
        .job-card { min-height: 132px; font-size: 1.1rem !important; border-radius: 18px !important; }
        #explanation-button.explanation-loading button {
          cursor: wait !important;
          animation: explanation-border-shadow 1.15s ease-in-out infinite;
        }
        @keyframes explanation-border-shadow {
          0%, 100% {
            border-color: #9ca3af;
            box-shadow: 0 0 0 1px rgba(107, 114, 128, 0.25),
                        0 0 4px rgba(107, 114, 128, 0.3);
          }
          50% {
            border-color: #6b7280;
            box-shadow: 0 0 0 3px rgba(107, 114, 128, 0.42),
                        0 0 13px rgba(75, 85, 99, 0.58);
          }
        }
        @media (prefers-reduced-motion: reduce) {
          #explanation-button.explanation-loading button {
            animation: none;
            border-color: #6b7280;
            box-shadow: 0 0 0 3px rgba(107, 114, 128, 0.4);
          }
        }
        @media (max-width: 600px) {
          #job-cards { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }
        </style>"""
    )


if __name__ == "__main__":
    server_host, server_port = app_server_settings()
    print_mobile_access_guide(server_host, server_port)
    demo.launch(
        server_name=server_host,
        server_port=server_port,
        # 16단계의 외부 공개 링크는 아직 활성화하지 않는다.
        share=False,
        theme=gr.themes.Soft(),
    )
