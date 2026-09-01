---
language: en
license: mit
base_model: EleutherAI/gpt-neo-125M
pipeline_tag: text-generation
tags:
- text-generation
- medical
- question-answering
- lora
- peft
- gpt-neo
datasets:
- medalpaca/medical_meadow_medqa
---

# 🏥 GPT-Neo 125M — Medical QA LoRA Fine-tune

## Model Description
موديل GPT-Neo 125M تم عمله Fine-tuning على داتا أسئلة وأجوبة طبية (USMLE style) باستخدام LoRA.

- **Developed by:** Hazem Galal

- **License:** MIT
- **Base Model:** EleutherAI/gpt-neo-125M

## المواصفات

| المواصفة | القيمة |
|-----------|--------|
| Base Model | EleutherAI/gpt-neo-125M |
| Dataset | medalpaca/medical_meadow_medqa |
| LoRA Rank (r) | 8 |
| LoRA Alpha | 16 |
| Block Size | 256 |
| Epochs | 3 |
| Learning Rate | 2e-4 |

## طريقة الاستخدام

    from transformers import AutoTokenizer, AutoModelForCausalLM
    
    model = AutoModelForCausalLM.from_pretrained("hazemgalal1/gptneo125m-medical-qa-merged")
    tokenizer = AutoTokenizer.from_pretrained("hazemgalal1/gptneo125m-medical-qa-merged")
    
    prompt = (
        "### Instruction:\nAnswer the following medical question.\n\n"
        "### Question:\nWhat is the first-line treatment for hypertension?\n\n"
        "### Answer:\n"
    )
    
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(**inputs, max_new_tokens=100, do_sample=True, temperature=0.7)
    print(tokenizer.decode(outputs[0], skip_special_tokens=True))

## تنبيه
هذا الموديل للأغراض التعليمية فقط، وليس بديلاً عن الاستشارة الطبية المتخصصة.
