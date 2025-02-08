from enum import Enum
from typing import Any, List, Optional, Union

import pydantic

from pydantic_core import PydanticUndefined


class WorkflowStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class WorkflowRunStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    CANCELLED = "CANCELLED"


class ParameterDataType(str, Enum):
    STRING = "STRING"
    MARKDOWN = "MARKDOWN"
    NUMBER = "NUMBER"
    BOOLEAN = "BOOLEAN"
    OBJECT = "OBJECT"
    DATETIME = "DATETIME"
    FILE = "FILE"
    OPTION = "OPTION"
    OUTPUT = "OUTPUT"


class WorkflowStepStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class FileTypes(str, Enum):
    PDF = "application/pdf"
    MP3 = "audio/mpeg"
    PNG = "image/png"
    ICS = "text/calendar"


class Parameter(pydantic.BaseModel, validate_assignment=True):
    name: str
    data_type: ParameterDataType
    value: Optional[Any] = None
    optional: Optional[bool] = False
    default: Optional[Any] = None
    description: Optional[str] = None
    content_type: Optional[FileTypes] = None
    choices: Optional[List[str]] = None
    invisible: Optional[bool] = False
    mention_data_only: Optional[bool] = False

    @property
    def v(self) -> Optional[Union[str, int, float, bool]]:
        """
        Return parsed value of the parameter. If the value is not set, return the default value.
        """
        v = self.value
        if v is None:
            v = self.default
        if v is PydanticUndefined:
            v = None
        if self.data_type == ParameterDataType.STRING:
            return str(v)
        elif self.data_type == ParameterDataType.NUMBER:
            return float(v) if v is not None else None
        elif self.data_type == ParameterDataType.BOOLEAN:
            return bool(v)

        return v

    @pydantic.model_validator(mode="after")
    def check_content_type_for_file(obj: "Parameter") -> "Parameter":
        if obj.data_type == ParameterDataType.FILE and not obj.content_type:
            raise ValueError("Content type is required for file parameter")
        return obj

    @pydantic.model_validator(mode="after")
    def check_choices_for_option(obj: "Parameter") -> "Parameter":
        if obj.data_type == ParameterDataType.OPTION:
            if not obj.choices:
                raise ValueError("Choices are required for option parameter")
            if obj.default is not None and obj.default not in obj.choices:
                raise ValueError(
                    f"Default value {obj.default} is not in the list of choices {obj.choices}"
                )
        return obj

    @pydantic.model_validator(mode="after")
    def check_value_for_option(obj: "Parameter") -> "Parameter":
        if (
            obj.data_type == ParameterDataType.OPTION
            and obj.value is not None
            and obj.choices is not None
        ):
            if obj.value not in obj.choices:
                raise ValueError(
                    f"Value {obj.value} is not in the list of choices {obj.choices}"
                )
        return obj

    def get_dry_run_value(self) -> Union[str, int, float, bool]:
        assert self.data_type in [
            ParameterDataType.STRING,
            ParameterDataType.NUMBER,
            ParameterDataType.BOOLEAN,
        ]
        if self.data_type == ParameterDataType.STRING:
            return "dummy"
        elif self.data_type == ParameterDataType.NUMBER:
            return 0
        else:
            return False

    def value_validation(self) -> List[str]:
        errors = []
        if self.value is None and not self.optional:
            errors.append(f"Parameter {self.name} is required")
        if self.value is not None:
            if self.data_type == ParameterDataType.STRING:
                if not isinstance(self.value, str):
                    errors.append(
                        f"Invalid data type for {self.name}: {self.value}, expected string, got {type(self.value).__name__}"
                    )
            elif self.data_type == ParameterDataType.NUMBER:
                if not isinstance(self.value, (int, float)):
                    try:
                        _ = float(self.value)
                    except ValueError:
                        errors.append(
                            f"Invalid data type for {self.name}: {self.value}, expected number"
                        )
            elif self.data_type == ParameterDataType.BOOLEAN:
                if not isinstance(self.value, bool):
                    try:
                        _ = bool(self.value)
                    except ValueError:
                        errors.append(
                            f"Invalid data type for {self.name}: {self.value}, expected boolean"
                        )
        return errors


class InputPermissionLevel(str, Enum):
    READ_ONLY = "READ_ONLY"
    READ_WRITE = "READ_WRITE"
    NO_ACCESS = "NO_ACCESS"


class InputParameter(Parameter):
    user_permission: Optional[InputPermissionLevel] = InputPermissionLevel.READ_WRITE

    # object level validation
    @pydantic.model_validator(mode="before")
    def check_default_value_for_read_only(cls, values):
        if values.get(
            "user_permission", InputPermissionLevel.READ_WRITE
        ) != InputPermissionLevel.READ_WRITE and not values.get("default"):
            raise ValueError("Default value is required for non-writable input")

        return values


class StepConfig(pydantic.BaseModel):
    type_name: str
    description: Optional[str]
    input_parameters: List[Parameter]
    output_parameters: List[Parameter]
    model_config = pydantic.ConfigDict(extra="allow")


class StepConfigList(pydantic.BaseModel):
    available_steps: List[StepConfig]


class WorkflowStepResult(pydantic.BaseModel):
    step_name: str
    step_type: str
    status: WorkflowStepStatus
    status_reason: Optional[str] = None
    inputs: List[Parameter]
    outputs: List[Parameter]
    started_at: str
    finished_at: str


class WorkflowRunResult(pydantic.BaseModel):
    status: WorkflowRunStatus
    result: List[WorkflowStepResult]


class ValidationError(pydantic.BaseModel):
    # line: Optional[int]
    loc: Optional[str]
    msg: str
    type: str
