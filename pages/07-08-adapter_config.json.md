# `adapter_config.json` 해설집

## 무엇인가요?

LoRA 가중치를 어느 기반 모델의 어느 부분에 연결할지 알려 주는 **조립 설명서**입니다.

## 현재 주요 설정

| 항목 | 값 | 쉬운 뜻 |
|---|---|---|
| `base_model_name_or_path` | `EleutherAI/gpt-neo-125M` | 포스트잇을 붙일 원래 교과서 |
| `peft_type` | `LORA` | 작은 추가 가중치 학습 방식 |
| `r` | `8` | 추가 학습 통로의 크기 |
| `lora_alpha` | `16` | LoRA 변화의 배율 |
| `lora_dropout` | `0.05` | 학습 중 일부를 쉬게 해 과적합 방지 |
| `target_modules` | `q_proj`, `v_proj` | 어댑터를 붙인 모델 부품 |
| `task_type` | `CAUSAL_LM` | 앞 문맥으로 다음 토큰을 만드는 모델 |
| `inference_mode` | `true` | 현재는 학습보다 실행용 |

## 실습

```powershell
python -c "import json; p='models/gptneo125m-medical-qa-lora-adapter/adapter_config.json'; d=json.load(open(p,encoding='utf-8')); print(d['base_model_name_or_path'],d['r'],d['target_modules'])"
```

이 설정은 과거 GPT-Neo 실험 설명이며 현재 MediKo 구성과 섞지 않습니다.
