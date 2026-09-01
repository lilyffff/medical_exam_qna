"""추가 네이티브 DLL 없이 Transformers와 PyTorch만으로 E5 임베딩을 계산한다."""

from functools import lru_cache

import numpy as np
import torch
import torch.nn.functional as functional
from transformers import AutoModel, AutoTokenizer

from local_rag import embedding_model_id


@lru_cache(maxsize=2)
def load_embedding_model(device: str = "cpu"):
    model_name = embedding_model_id()
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name).to(device)
    model.eval()
    return tokenizer, model, device


def encode_embeddings(
    texts: list[str], device: str = "cpu", batch_size: int = 32, max_length: int = 256
) -> np.ndarray:
    """E5 모델 카드의 attention-mask 평균 풀링 후 L2 정규화를 적용한다."""
    tokenizer, model, device = load_embedding_model(device)
    batches: list[np.ndarray] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        inputs = tokenizer(
            batch,
            max_length=max_length,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )
        inputs = {name: value.to(device) for name, value in inputs.items()}
        with torch.inference_mode():
            output = model(**inputs).last_hidden_state
            mask = inputs["attention_mask"].unsqueeze(-1).bool()
            masked = output.masked_fill(~mask, 0.0)
            pooled = masked.sum(dim=1) / mask.sum(dim=1).clamp(min=1)
            normalized = functional.normalize(pooled, p=2, dim=1)
        batches.append(normalized.cpu().numpy().astype(np.float32, copy=False))
    if not batches:
        dimension = int(getattr(model.config, "hidden_size", 0))
        return np.empty((0, dimension), dtype=np.float32)
    return np.concatenate(batches, axis=0)
