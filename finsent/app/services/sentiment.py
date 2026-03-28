from __future__ import annotations

from finsent.app.config.settings import settings
from finsent.app.models.schemas import SentimentResult


LABEL_MAP = {
    "positive": "positive",
    "negative": "negative",
    "neutral": "neutral",
}


class FinBERTSentimentService:
    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.model_name
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.torch = __import__("torch")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
        self.model.eval()

    def predict(self, text: str) -> SentimentResult:
        cleaned_text = (text or "").strip()
        if not cleaned_text:
            return SentimentResult(
                label="neutral",
                score=0.0,
                positive=0.0,
                negative=0.0,
                neutral=1.0,
            )

        encoded = self.tokenizer(
            cleaned_text,
            return_tensors="pt",
            truncation=True,
            max_length=256,
        )
        with self.torch.no_grad():
            logits = self.model(**encoded).logits
            probs = self.torch.nn.functional.softmax(logits, dim=-1)[0].tolist()

        labels = [self.model.config.id2label[idx].lower() for idx in range(len(probs))]
        score_map = {LABEL_MAP.get(label, label): float(score) for label, score in zip(labels, probs)}
        label = max(score_map, key=score_map.get)

        return SentimentResult(
            label=label,
            score=self._normalize_score(score_map),
            positive=score_map.get("positive", 0.0),
            negative=score_map.get("negative", 0.0),
            neutral=score_map.get("neutral", 0.0),
        )

    @staticmethod
    def _normalize_score(score_map: dict[str, float]) -> float:
        return round(score_map.get("positive", 0.0) - score_map.get("negative", 0.0), 6)
