"""
Example of a workflow yaml file:

name: test_workflow
steps:
- name: get_stock_price
  type: stockPrice
  input:
    symbol: "AAPL"
- name: step1
  type: llm
  input:
    prompt: "Please generate a text for based on the stock price of AAPL, which is @{get_stock_price.price}"
    model: "gpt4"
- name: step2
  type: tweetPost
  input:
    tweet: "@{step1.result}"
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Self, Type
from uuid import UUID

import pydantic
import yaml
from pydantic_core import PydanticCustomError

from doc_agent.steps.base import BaseStep, ValueReferenceError

from doc_agent.steps import registered_steps
from .types import (
    InputParameter,
    WorkflowRunResult,
    WorkflowRunStatus,
    ValidationError,
    WorkflowStepResult,
    WorkflowStepStatus,
)

logger = logging.getLogger(__name__)


class WorkflowStep(pydantic.BaseModel):
    name: str
    type: str
    description: Optional[str] = None
    inputs: Dict[str, Any] = {}
    skip_validation: bool = pydantic.Field(
        default=False, exclude=True, init=False, init_var=False, repr=False
    )
    _step_class: Optional[Type[BaseStep]] = None
    _step: BaseStep

    def __init__(self, **data):
        logger.info(f"Creating step {data.get('name')}")
        logger.debug(f"Step data: {data}")
        skip_validation = data.get("skip_validation", False)
        logger.debug(f"current skip_validation: {skip_validation}")
        super().__init__(**data)
        if not skip_validation:
            logger.debug(f"starting validation for step {self.name}")
            self.init_input()

    def init_input(self):
        logger.debug(f"Initializing input for step {self.name}")
        self._step_class = registered_steps.get(self.type)
        if self._step_class is not None:
            self._step = self._step_class(self.name, **self.inputs)

    def run(
        self,
        context: dict,
        *,
        dry_run: bool = False,
    ) -> WorkflowStepResult:
        if self._step is None:
            raise RuntimeError(f"Step {self.name} with type {self.type} not found")
        return self._step.run(context, dry_run=dry_run)

    @pydantic.field_validator("type")
    def validate_type(cls, v):
        if v not in registered_steps:
            raise PydanticCustomError(
                "invalid_step_type",
                "Step type {wrong_type} not found",
                dict(wrong_type=v),
            )
        return v

    @pydantic.field_validator("name")
    def validate_name(cls, v):
        if v == "input":
            raise PydanticCustomError(
                "reserved_step_name",
                (
                    "Step type `{wrong_type}` cannot be used. "
                    "It is a reserved keyword for workflow inputs"
                ),
                dict(wrong_type=v),
            )
        return v

    @pydantic.model_validator(mode="after")
    def validate_input(self) -> Self:
        step_input: Dict[str, str] = {}
        if hasattr(self, "inputs") and self.inputs is not None:
            step_input = self.inputs
        step_class = registered_steps.get(self.type)

        if not self.skip_validation:
            if step_class is None:
                raise PydanticCustomError(
                    "invalid_step_type",
                    "Step type `{wrong_type}` not found",
                    dict(wrong_type=self.type),
                )

            # check for missing fields
            for _input in step_class.input_parameters:
                if _input.name not in step_input:
                    if not _input.optional:
                        raise PydanticCustomError(
                            "missing_input",
                            "Step input value `{missing}` required",
                            dict(missing=_input.name),
                        )

            # check for extra fields
            necessary_inputs = set(
                [_input.name for _input in step_class.input_parameters]
            )
            extra_inputs = set(step_input.keys()) - necessary_inputs
            if extra_inputs:
                raise PydanticCustomError(
                    "extra_input",
                    "Extra input fields `{extra}` found",
                    dict(extra=", ".join(extra_inputs)),
                )

        return self


class WorkflowDef(pydantic.BaseModel):
    name: str
    description: Optional[str] = None
    inputs: List[InputParameter] = []
    steps: List[WorkflowStep]
    layout_attributes: Optional[Dict[str, Any]] = None
    skip_validation: bool = pydantic.Field(
        default=False, exclude=True, init=False, init_var=False, repr=False
    )

    def __init__(
        self,
        *,
        yaml_str: Optional[str] = None,
        **data,
    ):
        skip_validation = data.get("skip_validation", False)
        logger.debug(f"WorkflowDef::current skip_validation: {skip_validation}")

        if yaml_str:
            try:
                _data = yaml.safe_load(yaml_str)
                if not isinstance(_data, dict):
                    raise PydanticCustomError(
                        "invalid_workflow",
                        "Workflow definition should be a dictionary",
                        dict(),
                    )
                data.update(_data)
            except yaml.YAMLError as e:
                raise PydanticCustomError(
                    "yaml_error",
                    "Error parsing yaml: {error}",
                    dict(error=str(e)),
                )
        # if extra fields are present, raise an error
        if not skip_validation:
            for k in data.keys():
                if k not in self.model_fields.keys():
                    raise PydanticCustomError(
                        "extra_field",
                        "Extra Workflow field `{extra_field}` found",
                        dict(extra_field=k),
                    )
        if skip_validation:
            # add the skip_validation flag to the steps
            for _step in data.get("steps", []):
                logger.debug(
                    f"Setting skip_validation flag for step {_step.get('name')}"
                )
                _step["skip_validation"] = skip_validation
                logger.debug(f"Step data: {_step}")
        super().__init__(**data)

    def validate_inputs(self, inputs: Dict[str, Any]) -> List[ValidationError]:
        errors = []
        for _param in self.inputs:
            _param.value = inputs.get(_param.name, _param.default)
            if (
                _param.user_permission != "READ_WRITE"
                and _param.value != _param.default
            ):
                errors.append(
                    ValidationError(
                        loc=_param.name,
                        msg="Parameter is immutable",
                        type="immutable_workflow_input",
                    )
                )
            # raise error if the input value is None
            # and the parameter is not optional
            elif _param.value is None and not _param.optional:
                errors.append(
                    ValidationError(
                        loc=_param.name,
                        msg="Parameter is required",
                        type="missing_workflow_input",
                    )
                )
            else:
                # validate the input value
                _errors = _param.value_validation()
                if _errors:
                    errors.append(
                        ValidationError(
                            loc=_param.name,
                            msg=str(_errors),
                            type="invalid_workflow_input",
                        )
                    )
        return errors

    def get_required_integrations(self) -> List[str]:
        integrations = []
        for step in self.steps:
            step_class = registered_steps.get(step.type)
            if step_class is not None:
                integrations.extend(step_class.required_integrations)
        return list(set(integrations))

    # @pydantic.model_validator(mode="after")
    # def validate_dry_run(self):
    #     try:
    #         self.run(dry_run=True, user=User())
    #     except ValueReferenceError as e:
    #         logger.warning(f"Variable reference warning in step {e.step_name}: {e.incorrect_variable}")
    #         return self
    #     except Exception as e:
    #         raise PydanticCustomError(
    #             "workflow_error",
    #             "Error running workflow in dry run mode: {error}",
    #             dict(error=str(e)),
    #         )

    # temporarily ignore workflow validation errors for backward compatibility
    @pydantic.model_validator(mode="after")
    def validate_dry_run(self):
        if self.skip_validation:
            return
        try:
            self.run(dry_run=True)
        except ValueReferenceError as e:
            raise PydanticCustomError(
                "value_reference_error",
                "Step {step_name} has incorrect variable reference `{incorrect_variable}`. Available variables: {available_variables}",
                dict(
                    step_name=e.step_name,
                    incorrect_variable=e.incorrect_variable,
                    available_variables=e.available_variables,
                ),
            )
        except Exception as e:
            raise PydanticCustomError(
                "workflow_error",
                "Error running workflow in dry run mode: {error}",
                dict(error=str(e)),
            )

    def run(
        self,
        run_inputs: Optional[Dict] = None,
        *,
        dry_run=False,
    ) -> WorkflowRunResult:
        _start_at = datetime.now(tz=timezone.utc)
        # initialize the inputs
        if run_inputs is None:
            run_inputs = {}

        if dry_run:
            # if dry run, initialize the inputs with dummy values
            for _param in self.inputs:
                run_inputs[_param.name] = _param.get_dry_run_value()

        # validate the inputs
        _input_errors = []
        for _param in self.inputs:
            _param.value = run_inputs.get(_param.name, _param.default)
            # raise error if the input value is None
            # and the parameter is not optional
            if _param.value is None and not _param.optional:
                _input_errors.append(f"Parameter {_param.name} is required")

            # validate the input value
            errors = _param.value_validation()
            if errors:
                _input_errors.append(f"Invalid input value for {_param.name}: {errors}")
        if _input_errors:
            return WorkflowRunResult(
                status=WorkflowRunStatus.FAILURE,
                result=[
                    WorkflowStepResult(
                        step_name="input",
                        step_type="input",
                        status=WorkflowStepStatus.FAILURE,
                        status_reason="; ".join(_input_errors),
                        started_at=str(_start_at),
                        finished_at=str(datetime.now(tz=timezone.utc)),
                        inputs=[],
                        outputs=[],
                    )
                ],
            )

        # initialize the context, and prefilled with the inputs
        context: Dict = {f"input.{_param.name}": _param.value for _param in self.inputs}

        result = []
        status = WorkflowRunStatus.SUCCESS
        for step in self.steps:
            # This `init_input` method is called to reinitialize the step's input, because:
            # - The step input is initialized during dry run validation, and filled with dummy values.
            step.init_input()
            step_result: WorkflowStepResult = step.run(context, dry_run=dry_run)
            result.append(step_result)

            if step_result.status == WorkflowStepStatus.FAILURE:
                status = WorkflowRunStatus.FAILURE

        return WorkflowRunResult(status=status, result=result)


class ValidationResponse(pydantic.BaseModel):
    errors: Optional[List[ValidationError]] = None
    ok: bool


def workflow_yaml_validation(yaml_str: str) -> List[ValidationError]:
    result = []
    try:
        WorkflowDef(yaml_str=yaml_str)
    except pydantic.ValidationError as e:
        logger.exception(e)
        logger.error("e.errors(): %s", e.errors())
        for error in e.errors():
            result.append(
                ValidationError(
                    loc=".".join([str(x) for x in error["loc"]]),
                    msg=error["msg"],
                    type=error["type"],
                )
            )
    except PydanticCustomError as e:
        logger.exception(e)
        result.append(
            ValidationError(
                loc="",
                msg=str(e),
                type="yaml_error",
            )
        )
    except Exception as e:
        logger.exception(e)
        result.append(
            ValidationError(
                loc="",
                msg=str(e),
                type="workflow_error",
            )
        )
    return result
