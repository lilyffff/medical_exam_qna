# `adapter_model.safetensors` 해설집

## 무엇인가요?

전체 언어 모델을 다시 저장하지 않고, Medical QA 학습으로 달라진 작은 LoRA 가중치만 보관한 파일입니다. 교과서 전체가 아니라 선생님이 붙인 **의료 문제 풀이 보충 포스트잇**과 비슷합니다.

현재 파일은 약 1.19MB이며 기반 모델은 GPT-Neo 125M입니다. `safetensors` 형식은 임의 Python 객체 실행 없이 텐서를 저장하도록 설계된 모델 가중치 형식입니다.

## 현재 앱에서 사용하나요?

아니요. 현재 `.env`는 MediKo 모델을 사용하고 `MEDICAL_LORA_ADAPTER=`가 비어 있습니다. GPT-Neo용 어댑터를 MediKo에 연결하면 기반 모델이 달라 정상 호환되지 않습니다.

## 안전한 확인

파일 존재와 크기만 확인합니다.

```powershell
Get-Item -LiteralPath "models\gptneo125m-medical-qa-lora-adapter\adapter_model.safetensors" | Select-Object Name,Length
```

바이너리 파일이므로 메모장으로 열지 않습니다.
