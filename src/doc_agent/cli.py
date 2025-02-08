from typing import List
import click
import yaml
from doc_agent import __version__
from doc_agent.types import ValidationError, WorkflowRunResult
from doc_agent.workflowyaml import WorkflowDef, workflow_yaml_validation


@click.group()
def main() -> None:
    """
    The main entry point of the CLI.
    """
    click.echo(f"Welcome to doc_agent {__version__}!")


# sub command: generate
# generate example workflow file
@main.command()
@click.option(
    # output file path
    "--output",
    "-o",
    type=click.Path(),
    default="workflow.yml",
    help="The output file path.",
)
def generate(output: str) -> None:
    """
    Generate an example workflow file.
    """
    click.echo(f"Generating an example workflow file at {output}.")

    with open(output, "w") as f:
        f.write(
            """
name: example workflow
steps:
  - name: example step
    type: dummy
    inputs:
        input: Hello, World!
"""
        )


# sub command: test
# test the workflow file
@main.command()
@click.argument(
    # workflow file path
    "workflow",
    type=click.Path(exists=True),
)
def test(workflow: str) -> None:
    """
    Test the workflow file.
    """
    click.echo(f"Testing the workflow file at {workflow}.")
    # read the workflow file
    with open(workflow, "r") as f:
        content = f.read()
    # validate the workflow file
    errors: List[ValidationError] = workflow_yaml_validation(content)
    if errors:
        click.echo("Validation failed:")
        for error in errors:
            click.echo(f"  - {error}")
    else:
        click.echo("✅Validation passed.")


# sub command: run
# run the workflow file
@main.command()
@click.argument(
    # workflow file path
    "workflow_path",
    type=click.Path(exists=True),
)
def run(workflow_path: str) -> None:
    """
    Run the workflow file.
    """
    click.echo(f"Running the workflow file at {workflow_path}.")
    # read the workflow file
    with open(workflow_path, "r") as f:
        content = f.read()
    # validate the workflow file
    workflow = WorkflowDef(**yaml.safe_load(content))
    result: WorkflowRunResult = workflow.run(dry_run=False)
    click.echo(f"Workflow run result:{result.status}")
    for step in result.result:
        click.echo(f"  - {step.step_name}: {step.status}")
        if step.status_reason:
            click.echo(f"    {step.status_reason}")
        if step.inputs:
            click.echo("    Inputs:")
            for input in step.inputs:
                click.echo(f"      - {input.name}: {input.value}")
        if step.outputs:
            click.echo("    Outputs:")
            for output in step.outputs:
                click.echo(f"      - {output.name}: {output.value}")
        click.echo(f"    Started at: {step.started_at}")
        click.echo(f"    Finished at: {step.finished_at}")


if __name__ == "__main__":
    main()
