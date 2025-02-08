from typing import Dict
from doc_agent.types import ParameterDataType, Parameter
from .base import BaseStep
from openai import OpenAI
import json


def llm_qa(system_message: str, prompt: str, model: str) -> str:
    client = OpenAI()

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": system_message,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    if completion.choices[0].message.content is None:
        raise ValueError("Completion is not provided")

    return completion.choices[0].message.content


class LLMStep(BaseStep):
    allow_dynamic_outputs = True  # Enable dynamic output parameters
    registered_names = ["llm"]
    input_parameters = [
        Parameter(
            name="prompt",
            data_type=ParameterDataType.STRING,
            description="Default (content above), should be hidden",
            invisible=True,
        ),
        Parameter(
            name="model",
            data_type=ParameterDataType.OPTION,
            default="gpt-4o",
            description="Placeholder Selection (GPT, Claude, LLaMA), Selection (gpt-4o, gpt-4o-mini)",
            choices=["gpt-4o", "gpt-4o-mini"],
        ),
        Parameter(
            name="chat_history",
            data_type=ParameterDataType.BOOLEAN,
            optional=True,
            default=False,
            description="Placeholder ON/OFF",
        ),
        Parameter(
            name="system_message",
            data_type=ParameterDataType.STRING,
            optional=True,
            default="",
            description="Placeholder",
        ),
        # Define a simple comma-separated string parameter for output names
        Parameter(
            name="output_names",
            data_type=ParameterDataType.OUTPUT,
            optional=True,
            default="",
            description='Output Parameters: Comma-separated output names, e.g. "summary, keywords, sentiment"',
        ),
    ]
    output_parameters = [
        Parameter(name="result", data_type=ParameterDataType.STRING),
    ]
    description = "Get the LLM"

    def __init__(self, name: str, **kwargs):
        output_names = None
        # Extract and remove output_names from kwargs to avoid duplicate parameters
        if "output_names" in kwargs:
            if kwargs["output_names"]:
                # Parse comma-separated string into list of output names
                output_names = [
                    name.strip() for name in kwargs["output_names"].split(",")
                ]
            del kwargs["output_names"]

        # Pass the parsed output_names separately to parent class
        super().__init__(name, output_names=output_names, **kwargs)

    def process(self, dry_run: bool = False) -> Dict[str, str]:
        prompt = self.inputs["prompt"].value
        model = self.inputs["model"].value

        if prompt is None:
            raise ValueError("Prompt is not provided")
        if model is None:
            raise ValueError("Model is not provided")

        if dry_run:
            # Return placeholder results for each output in dry run mode
            return {
                name: f"This is the {name} of the LLM Dry Run"
                for name in self.outputs.keys()
            }

        client = OpenAI()

        # For single output, use the original behavior
        if len(self.outputs) <= 1:
            completion = self._get_completion(client, prompt, model)
            return {"result": completion}

        # For multiple outputs:
        # 1. Modify the prompt to request a JSON response with specific keys
        # 2. Keep the original prompt but add formatting instructions
        modified_prompt = (
            f"{prompt}\n\n"
            f"Please provide your response in JSON format with the following keys: "
            f"{', '.join(self.outputs.keys())}"
            f"Important: Return only the JSON object, no markdown, no code blocks."
        )

        # Get completion using the modified prompt
        completion = self._get_completion(client, modified_prompt, model)

        try:
            # Try to parse the response as JSON
            return json.loads(completion)
        except json.JSONDecodeError:
            # Fallback: If JSON parsing fails, duplicate the entire response
            # for each requested output name to ensure we return something
            return {name: completion for name in self.outputs.keys()}

    def _get_completion(self, client: OpenAI, prompt: str, model: str) -> str:
        result = llm_qa(self.inputs["system_message"].value or "", prompt, model)
        return result
