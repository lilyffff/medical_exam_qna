# `tokenizer.json`·`tokenizer_config.json` 해설집

## 무엇인가요?

토크나이저는 사람이 쓴 문장을 모델이 읽는 토큰 번호로 바꾸고 다시 글자로 돌리는 **문장 분해·조립 사전**입니다.

- `tokenizer.json`: 어휘와 문장을 나누는 실제 규칙을 담은 큰 사전
- `tokenizer_config.json`: 특수 토큰, 최대 길이 등 사용 설정을 담은 안내서

현재 두 파일은 GPT-Neo 125M LoRA 실험 폴더에 보관되어 있습니다. 현재 MediKo 앱은 Hugging Face에서 MediKo에 맞는 토크나이저를 별도로 불러오므로 이 파일들을 사용하지 않습니다.

## 왜 모델과 토크나이저를 맞춰야 하나요?

같은 문장도 사전마다 다른 번호로 나뉩니다. 영어 교과서의 쪽 번호를 국어 교과서에 그대로 적용하면 엉뚱한 문장이 나오는 것과 같습니다.

## 실습

설정 키만 확인합니다.

```powershell
python -c "import json; p='models/gptneo125m-medical-qa-lora-adapter/tokenizer_config.json'; d=json.load(open(p,encoding='utf-8')); print(sorted(d.keys()))"
```

파일이 크므로 전체 내용을 터미널에 출력할 필요는 없습니다.
