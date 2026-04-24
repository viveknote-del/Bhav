"""
Eval runner — validates AI output quality for all registered prompts.

Run locally:
    python -m evals.runner

Run in CI:
    python -m evals.runner --ci    (exits non-zero if score < threshold)

Add eval cases to each Prompt definition in prompts/registry.py.
No eval cases on a prompt = warning, not failure (some prompts are hard to eval cheaply).

Scoring:
  Each eval case is pass/fail.
  Overall score = passed / total.
  CI threshold: 100% (all cases must pass).
  Rationale: prompts are deterministic enough that any failure is a real regression.
  If a case is flaky, fix the must_contain criteria — don't lower the threshold.
"""
import asyncio
import sys
from dataclasses import dataclass

from prompts import list_prompts
from prompts.base import EvalCase, Prompt
from providers import llm


@dataclass
class EvalResult:
    prompt_name: str
    prompt_version: str
    case_description: str
    passed: bool
    output: str
    failure_reason: str = ""


async def run_case(prompt: Prompt, case: EvalCase) -> EvalResult:
    try:
        output = await llm.complete(
            prompt=case.input,
            system=prompt.system,
            model=prompt.model,
            max_tokens=prompt.max_tokens,
            cache_system=False,  # don't pollute prod cache during evals
        )
    except Exception as e:
        return EvalResult(
            prompt_name=prompt.name,
            prompt_version=prompt.version,
            case_description=case.description,
            passed=False,
            output="",
            failure_reason=f"LLM call failed: {e}",
        )

    # Check must_contain
    for phrase in case.must_contain:
        if phrase.lower() not in output.lower():
            return EvalResult(
                prompt_name=prompt.name,
                prompt_version=prompt.version,
                case_description=case.description,
                passed=False,
                output=output,
                failure_reason=f"Missing expected phrase: '{phrase}'",
            )

    # Check must_not_contain
    for phrase in case.must_not_contain:
        if phrase.lower() in output.lower():
            return EvalResult(
                prompt_name=prompt.name,
                prompt_version=prompt.version,
                case_description=case.description,
                passed=False,
                output=output,
                failure_reason=f"Forbidden phrase present: '{phrase}'",
            )

    # Check length
    if len(output) < case.min_length:
        return EvalResult(
            prompt_name=prompt.name,
            prompt_version=prompt.version,
            case_description=case.description,
            passed=False,
            output=output,
            failure_reason=f"Output too short: {len(output)} chars (min {case.min_length})",
        )

    if case.max_length and len(output) > case.max_length:
        return EvalResult(
            prompt_name=prompt.name,
            prompt_version=prompt.version,
            case_description=case.description,
            passed=False,
            output=output,
            failure_reason=f"Output too long: {len(output)} chars (max {case.max_length})",
        )

    return EvalResult(
        prompt_name=prompt.name,
        prompt_version=prompt.version,
        case_description=case.description,
        passed=True,
        output=output,
    )


async def run_all(ci_mode: bool = False) -> bool:
    prompts = list_prompts()
    results: list[EvalResult] = []
    warnings: list[str] = []

    for prompt in prompts:
        if not prompt.eval_cases:
            warnings.append(f"⚠  {prompt.name} v{prompt.version} — no eval cases defined")
            continue

        print(f"\n── {prompt.name} v{prompt.version} ({len(prompt.eval_cases)} cases)")

        tasks = [run_case(prompt, case) for case in prompt.eval_cases]
        prompt_results = await asyncio.gather(*tasks)

        for result in prompt_results:
            icon = "✓" if result.passed else "✗"
            desc = result.case_description or result.case_description
            print(f"   {icon} {desc}")
            if not result.passed:
                print(f"     Reason: {result.failure_reason}")
                if result.output:
                    print(f"     Output: {result.output[:200]}")
            results.append(result)

    # Summary
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed

    print(f"\n{'='*50}")
    print(f"Results: {passed}/{total} passed", end="")
    if failed:
        print(f"  ({failed} FAILED)")
    else:
        print("  ✓ all passed")

    for w in warnings:
        print(w)

    if ci_mode and failed > 0:
        print("\n[CI] Eval failures block this PR. Fix the prompts or update eval criteria.")
        return False

    return failed == 0


def main():
    ci_mode = "--ci" in sys.argv
    success = asyncio.run(run_all(ci_mode=ci_mode))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
