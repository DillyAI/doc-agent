from typing import Dict

from doc_agent.types import ParameterDataType, Parameter

from .base import BaseStep


class DummyStep(BaseStep):
    registered_names = ["dummy"]
    input_parameters = [
        Parameter(name="input", data_type=ParameterDataType.STRING),
    ]
    output_parameters = [
        Parameter(name="output", data_type=ParameterDataType.STRING),
    ]
    description = (
        "This is a dummy step, which takes an input and returns the same as output."
        "This is useful for testing purposes."
    )

    def process(self, dry_run: bool = False) -> Dict[str, str]:
        input_value = self.inputs["input"].value
        if input_value is None:
            raise ValueError("Input is not provided")
        return {"output": input_value}
