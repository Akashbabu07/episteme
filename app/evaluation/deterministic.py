from dataclasses import dataclass

from app.observability.models import StepRecord


@dataclass
class DeterministicScores:
    completeness: float
    tool_usage_efficiency: float
    source_quality: float
    contradiction_handling: float
    notes: list[str]


def evaluate_deterministic(
    steps: list[StepRecord],
    task_count: int,
    task_success_count: int,
    max_steps_budget: int,
    final_answer: str,
) -> DeterministicScores:
    notes: list[str] = []
 
    completeness = task_success_count / task_count if task_count > 0 else 0.0
    if completeness < 1.0:
        notes.append(f"{task_count - task_success_count} of {task_count} tasks failed to complete.")

 
    tool_calls = [s for s in steps if s.step_type == "tool_call"]
    model_calls = [s for s in steps if s.step_type == "model_call"]
    total_llm_steps = len(model_calls)

    if total_llm_steps == 0:
        tool_usage_efficiency = 0.0
        notes.append("No model calls recorded — cannot assess efficiency.")
    else:
        
        efficiency_ratio = 1.0 - (total_llm_steps / max(max_steps_budget * task_count, 1))
        tool_usage_efficiency = max(0.0, min(1.0, efficiency_ratio))

 
    web_search_calls = [s for s in tool_calls if s.tool_name == "web_search"]
    if len(web_search_calls) == 0:
        source_quality = 0.3  # not zero — calculator-only tasks are legitimately fine
        notes.append("No web_search calls found — answer may rely only on model knowledge.")
    else:
        source_quality = min(1.0, 0.5 + 0.1 * len(web_search_calls))

 
    challenge_steps = [s for s in steps if s.step_type == "challenge"]
    if not challenge_steps:
        contradiction_handling = 0.5  # neutral — V6 stage wasn't used, not necessarily bad
        notes.append("No challenge stage found in this run.")
    else:
        
        signal_words = ["however", "revised", "uncertain", "counter", "although", "but"]
        addressed = any(word in final_answer.lower() for word in signal_words)
        contradiction_handling = 1.0 if addressed else 0.4
        if not addressed:
            notes.append("A challenge was raised but the final answer shows no clear sign it was addressed.")

    return DeterministicScores(
        completeness=round(completeness, 2),
        tool_usage_efficiency=round(tool_usage_efficiency, 2),
        source_quality=round(source_quality, 2),
        contradiction_handling=round(contradiction_handling, 2),
        notes=notes,
    )