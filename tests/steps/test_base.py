from unittest import TestCase
from doc_agent.steps.base import BaseStep
from doc_agent.types import WorkflowStepResult, WorkflowStepStatus


class TestBaseStep(TestCase):
    def test_base_step(self) -> None:
        step = BaseStep("test")
        wf_step_result: WorkflowStepResult = step.run(context={})
        self.assertEqual(wf_step_result.status, WorkflowStepStatus.FAILURE)
