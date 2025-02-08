"""
Unit tests for dry run results of workflow
"""

from unittest import TestCase
from doc_agent.types import (
    InputParameter,
    InputPermissionLevel,
    Parameter,
    ParameterDataType,
)


class TestInputParameter(TestCase):

    def test_input_parameter(self):
        input_parameter = InputParameter(
            name="input",
            data_type=ParameterDataType.STRING,
            user_permission=InputPermissionLevel.READ_WRITE,
            default="default",
        )
        self.assertEqual(input_parameter.name, "input")

    def test_read_only_input_parameter_without_default_value(self):
        # exception is expected when default value is not provided for read only input
        with self.assertRaises(ValueError) as context:
            _ = InputParameter(
                name="input",
                data_type=ParameterDataType.STRING,
                user_permission=InputPermissionLevel.READ_ONLY,
            )
            self.assertTrue(
                "Default value is required for read only input"
                in str(context.exception)
            )


class TestParameter(TestCase):
    def test_file_type_without_content_type(self):
        # exception is expected when content type is not provided for file parameter
        with self.assertRaises(ValueError) as _:
            _ = Parameter(
                name="file",
                data_type=ParameterDataType.FILE,
            )

    def test_option_type_without_choices(self):
        # exception is expected when choices are not provided for option parameter
        with self.assertRaises(ValueError) as _:
            _ = Parameter(
                name="option",
                data_type=ParameterDataType.OPTION,
            )

    def test_option_type_with_non_existing_default_value(self):
        # exception is expected when non existing choice is provided for option parameter
        with self.assertRaises(ValueError) as context:
            _ = Parameter(
                name="option",
                data_type=ParameterDataType.OPTION,
                choices=["choice1", "choice2"],
                default="choice3",
            )
            self.assertTrue("Default value is not in choices" in str(context.exception))

    def test_option_type_with_non_existing_choice(self):
        # exception is expected when non existing choice is provided for option parameter
        with self.assertRaises(ValueError) as _:
            p = Parameter(
                name="option",
                data_type=ParameterDataType.OPTION,
                choices=["choice1", "choice2"],
            )

            p.value = "choice3"
