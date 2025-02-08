import copy
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


from doc_agent.types import (
    Parameter,
    ParameterDataType,
    StepConfig,
    WorkflowStepResult,
    WorkflowStepStatus,
)

logger = logging.getLogger(__name__)


class ValueReferenceError(Exception):
    def __init__(
        self, step_name: str, incorrect_variable: str, available_variables: List[str]
    ):
        self.step_name = step_name
        self.incorrect_variable = incorrect_variable
        self.available_variables = available_variables
        return super().__init__(
            f"Value for {step_name}.{incorrect_variable} not found, "
            f"available variables are: {', '.join(available_variables)}"
        )


def fill_value(value: Any, context: dict, current_step_name: str = "") -> str:
    """
    This function will fill the value string formatted as @{step_name.parameter_name}
    with the actual value from the context.

    Args:
    - value_str: str
    - context: dict
    - current_step_name: str
        is used for ValueReferenceError, which will be raised if the value is not found
    """
    if not isinstance(value, str):
        # if the value is not a string, return it as is
        return value

    value_str = value
    while True:
        # use regex to find the next match
        # the step name and parameter name can only contain letters, numbers, and underscores
        match = re.search(
            r"@{[\ ]*([a-zA-Z0-9_]+)[\ ]*\.[\ ]*([a-zA-Z0-9_]+)[\ ]*}", value_str
        )
        if match is None:
            break

        step_name = match.group(1)
        parameter_name = match.group(2)

        # get the value from the context
        value = context.get(f"{step_name}.{parameter_name}")
        if value is None:
            raise ValueReferenceError(
                step_name=current_step_name,
                incorrect_variable=f"{step_name}.{parameter_name}",
                available_variables=[k for k in context.keys()],
            )
        value_str = value_str.replace(match.group(0), str(value))
    return value_str


class BaseStep:
    allow_dynamic_outputs = False  # Default to not allowing dynamic outputs
    registered_names: List[str] = []
    input_parameters: List[Parameter] = []
    output_parameters: List[Parameter] = []
    description: str = ""
    required_integrations: List[str] = []

    def __init__(self, name: str, output_names: Optional[List[str]] = None, **kwargs):
        logger.info(f"Creating step {name}")

        self.name = name
        self.context: Dict[str, str] = kwargs["context"] if "context" in kwargs else {}

        # Handle dynamic output parameters if allowed
        if self.allow_dynamic_outputs and output_names:
            self.output_parameters = [
                Parameter(name=name, data_type=ParameterDataType.STRING)
                for name in output_names
            ]

        self.inputs: Dict[str, Parameter] = {
            # TODO: this is bad & buggy design
            # parameters are mutable and shared across all instances of the the step
            # In the future the Parameter should be redesigned as ParameterClass
            k.name: copy.deepcopy(k)
            for k in self.input_parameters
        }
        # initialize all input values to None
        for k in self.inputs.keys():
            self.inputs[k].value = None

        self.outputs: Dict[str, Parameter] = {
            # TODO: this is bad & buggy design
            # parameters are mutable and shared across all instances of the the step
            k.name: copy.deepcopy(k)
            for k in self.output_parameters
        }
        # initialize all output values to None
        for k in self.outputs.keys():
            self.outputs[k].value = None

        # set the input values
        for k in self.inputs.keys():
            if k in kwargs:
                self.inputs[k].value = kwargs[k]
            else:
                # if the input is not optional, raise an error
                logger.debug("self.inputs[k]= %s", self.inputs[k])
                if not self.inputs[k].optional:
                    raise ValueError(f"Missing required input parameter {k}")
                elif self.inputs[k].default is not None:
                    logger.debug(
                        f"Setting default value for {k} to {self.inputs[k].default}, with type {type(self.inputs[k].default)}"
                    )
                    self.inputs[k].value = self.inputs[k].default
                    logger.debug(
                        f"now the value is in type {type(self.inputs[k].value)}"
                    )

        # validation: no duplicate names in inputs and outputs
        for k in self.inputs.keys():
            if k in self.outputs:
                raise ValueError(f"Duplicate parameter name {k}")

    def process(self, dry_run: bool = False) -> Dict:
        raise NotImplementedError()

    def run(
        self,
        context: dict,
        *,
        dry_run: bool = False,
    ) -> WorkflowStepResult:

        logger.info(f"Running step {self.name}")
        context.update(self.context)
        start_time = datetime.now(timezone.utc)

        try:
            # fill the input values with the actual values from the context
            for k, v in self.inputs.items():
                if v.value is not None:
                    v.value = fill_value(v.value, context, self.name)
                    context[f"{self.name}.{k}"] = v.value
            logger.debug(f"Input values: {self.inputs}")
            #############################
            # run the step
            result = self.process(dry_run=dry_run)
            #############################
            logger.info(f"Output values: {result}")
            logger.debug(f"Context: {context}")
            # update the context with the output values
            for k, v in result.items():
                if k in self.outputs:
                    self.outputs[k].value = v
                    context[f"{self.name}.{k}"] = v
                else:
                    logger.warning(f"Output parameter {k} not found in the output list")
                    logger.warning(f"Output value: {v}")

            # build ouput parameters
            _outputs: List[Parameter] = []
            for k, v in result.items():
                if k in self.outputs:
                    _p = copy.copy(self.outputs[k])
                    _p.value = v
                    _outputs.append(_p)

            return WorkflowStepResult(
                step_name=self.name,
                step_type=self.__class__.__name__,
                status=WorkflowStepStatus.SUCCESS,
                inputs=[_s for _s in self.inputs.values() if _s.value is not None],
                outputs=_outputs,
                started_at=str(start_time),
                finished_at=str(datetime.now(timezone.utc)),
            )
        except Exception as e:
            if dry_run:
                raise e
            logger.exception(e)
            return WorkflowStepResult(
                step_name=self.name,
                step_type=self.__class__.__name__,
                status=WorkflowStepStatus.FAILURE,
                inputs=[v for _, v in self.inputs.items() if v.value is not None],
                outputs=[
                    Parameter(
                        name="error", value=str(e), data_type=ParameterDataType.STRING
                    )
                ],
                started_at=str(start_time),
                finished_at=str(datetime.now(timezone.utc)),
            )

    @classmethod
    def get_step_info(cls):
        logger.debug(f"Getting step info for {cls}")
        logger.debug(f"With the following input parameters: {cls.input_parameters}")
        return StepConfig(
            type_name=cls.registered_names[0],
            description=cls.description,
            input_parameters=cls.input_parameters,
            output_parameters=cls.output_parameters,
        )

    def __str__(self):
        return f"{self.name}: {self.description}"
