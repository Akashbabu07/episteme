from collections import defaultdict

from app.experiments.benchmark import BenchmarkResult


def print_report(results: list[BenchmarkResult]) -> None:
    print("\n" + "=" * 70)
    print("BENCHMARK REPORT")
    print("=" * 70)

    by_strategy_scores: dict[str, list[float]] = defaultdict(list)

    for r in results:
        score_str = f"{r.overall_score:.3f}" if r.overall_score is not None else "ERROR"
        print(f"\n[{r.strategy}] {r.question}")
        print(f"  run_id: {r.run_id}")
        print(f"  score:  {score_str}")
        if r.error:
            print(f"  error:  {r.error}")
        else:
            print(f"  answer: {r.final_answer[:150]}...")

        if r.overall_score is not None:
            by_strategy_scores[r.strategy].append(r.overall_score)

    print("\n" + "-" * 70)
    print("AVERAGE SCORE BY STRATEGY")
    print("-" * 70)
    for strategy, scores in by_strategy_scores.items():
        avg = sum(scores) / len(scores) if scores else 0.0
        print(f"  {strategy}: {avg:.3f}  (n={len(scores)})")

    error_count = sum(1 for r in results if r.error)
    if error_count:
        print(f"\n⚠ {error_count} of {len(results)} runs errored — see details above.")