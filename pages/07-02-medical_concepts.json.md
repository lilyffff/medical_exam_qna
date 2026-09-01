# `medical_concepts.json` 해설집

## 무엇인가요?

문제에 나온 표현만 검색하면 의학적으로 연결된 다른 표현을 놓칠 수 있습니다. 이 JSON은 **별명·관련 개념 사전**처럼 검색어를 확장합니다.

예를 들어 `복강내출혈`, `외상`, `소변량 감소`가 함께 발견되면 `출혈성 쇼크`, `신장 관류 감소` 같은 관련 표현을 검색에 더합니다.

## JSON 구조

```json
{
  "concept": "개념 이름",
  "min_matches": 2,
  "triggers": ["문제에서 찾을 단서"],
  "expansions": ["검색에 추가할 동의어와 병태생리"]
}
```

| 항목 | 학교생활 비유 |
|---|---|
| `concept` | 단원 제목 |
| `triggers` | 이 단원인지 알아보는 핵심 단어 |
| `min_matches` | 오답을 줄이기 위해 필요한 최소 단서 수 |
| `expansions` | 함께 찾아볼 교과서 색인어 |

현재 규칙은 4개이며 `local_rag.py`가 읽습니다. 너무 흔한 단어 하나만 trigger로 쓰면 엉뚱한 검색이 늘 수 있으므로 `min_matches`를 2 이상으로 두는 것이 안전합니다.

## 실습

```powershell
python -c "import json; d=json.load(open('medical_concepts.json',encoding='utf-8')); print(len(d)); print([x['concept'] for x in d])"
```

규칙을 바꾼 뒤에는 `test_local_rag.py`를 실행해 기존 검색이 나빠지지 않았는지 확인합니다.
