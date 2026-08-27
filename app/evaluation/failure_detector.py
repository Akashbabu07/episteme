from dataclasses import dataclass

from app.observability.models import EvaluationRecord
FAILURE_THRESHOLD = 0.6


@dataclass
class FlaggedFailure:
    dimension: str
    score: float


def detect_failures(evaluation: EvaluationRecord) -> list[FlaggedFailure]:
    dimensions = {
        "completeness": evaluation.completeness,
        "tool_usage_efficiency": evaluation.tool_usage_efficiency,
        "source_quality": evaluation.source_quality,
        "contradiction_handling": evaluation.contradiction_handling,
        "factual_accuracy": evaluation.factual_accuracy,
        "reasoning_quality": evaluation.reasoning_quality,
    }

    flagged = [
        FlaggedFailure(dimension=name, score=score)
        for name, score in dimensions.items()
        if score < FAILURE_THRESHOLD
    ]
    # Worst first — analyze the biggest problem first if there are several.
    flagged.sort(key=lambda f: f.score)
    return flagged