from typing import Dict, List, Type


from doc_agent.types import WorkflowStepResult
from .base import BaseStep
from .dummy import DummyStep
from .llm import LLMStep

active_steps: List[Type[BaseStep]] = [
    DummyStep,
    LLMStep,
]

registered_steps: Dict[str, Type[BaseStep]] = {
    step_name: step_class
    for step_class in active_steps
    for step_name in step_class.registered_names
}


def run_step(
    step_name: str,
    step_type: str,
    parameters: dict,
    context: dict,
    dry_run: bool = False,
) -> WorkflowStepResult:
    step_class = registered_steps.get(step_type)
    if not step_class:
        raise ValueError(f"Unknown step type: {step_type}")

    step: BaseStep = step_class(step_name, **parameters)

    return step.run(context, dry_run=dry_run)
