"""Eval runner — validates AI output quality for every registered prompt.

Run locally:
    python -m evals.runner

Run in CI:
    python -m evals.runner --ci    (exits non-zero if any case fails)

Add eval cases to each Prompt in prompts/registry.py.
"""
from __future__ import annotations

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


def _check(prompt: Prompt, case: EvalCase, output: str) -> tuple[bool, str]:
    for phrase in case.must_contain:
        if phrase.lower() not in output.lower():
            return False, f"Missing expected phrase: '{phrase}'"
    for phrase in case.must_not_contain:
        if phrase.lower() in output.lower():
            return False, f"Forbidden phrase present: '{phrase}'"
    if len(output) < case.min_length:
        return False, f"Output too short: {len(output)} chars (min {case.min_length})"
    if case.max_length and len(output) > case.max_length:
        return False, f"Output too long: {len(output)} chars (max {case.max_length})"
    return True, ""


async def run_case(prompt: Prompt, case: EvalCase) -> EvalResult:
    try:
        result = await llm.generate(prompt.name, case.input)
        output = result.text
    except Exception as e:                              # noqa: BLE001
        return EvalResult(
            prompt_name=prompt.name,
            prompt_version=prompt.version,
            case_description=case.description,
            passed=False,
            output="",
            failure_reason=f"LLM call failed: {e}",
        )

    passed, reason = _check(prompt, case, output)
    return EvalResult(
        prompt_name=prompt.name,
        prompt_version=prompt.version,
        case_description=case.description,
        passed=passed,
        output=output,
        failure_reason=reason,
    )


async def run_all(ci_mode: bool = False) -> bool:
    prompts = list_prompts()
    results: list[EvalResult] = []
    warnings: list[str] = []

    for prompt in prompts:
        if not prompt.eval_cases:
            warnings.append(f"WARN: {prompt.name} v{prompt.version} has no eval cases")
            continue

        print(f"\n-- {prompt.name} v{prompt.version} ({len(prompt.eval_cases)} cases)")
        prompt_results = await asyncio.gather(*(run_case(prompt, c) for c in prompt.eval_cases))

        for result in prompt_results:
            icon = "PASS" if result.passed else "FAIL"
            print(f"   [{icon}] {result.case_description}")
            if not result.passed:
                print(f"          reason: {result.failure_reason}")
                if result.output:
                    print(f"          output: {result.output[:200]}")
            results.append(result)

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed

    print(f"\n{'='*50}")
    print(f"Results: {passed}/{total} passed" + ("  (all passed)" if failed == 0 else f"  ({failed} FAILED)"))
    for w in warnings:
        print(w)

    if ci_mode and failed > 0:
        return False
    return failed == 0


def main() -> None:
    ci_mode = "--ci" in sys.argv
    sys.exit(0 if asyncio.run(run_all(ci_mode=ci_mode)) else 1)


if __name__ == "__main__":
    main()
