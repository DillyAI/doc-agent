from pathlib import Path

import click
from click.testing import CliRunner

from doc_agent import __version__
from doc_agent.cli import main


def test_version():
    click.echo(f"Welcome to doc_agent {__version__}!")
    assert True


def test_main():
    """
    Test the main CLI entry point.

    This test uses the CliRunner to invoke the main function of the CLI application
    and checks the following:
    - The exit code of the command is 0, indicating successful execution.
    - The output contains a welcome message with the current version of the application.
    """
    runner = CliRunner()
    result = runner.invoke(main)
    assert result.exit_code == 0
    assert f"Usage: main [OPTIONS] COMMAND [ARGS]" in result.output


def test_generate():
    """
    Test the generate subcommand of the CLI.

    This test uses the CliRunner to invoke the generate subcommand of the CLI application
    and checks the following:
    - The exit code of the command is 0, indicating successful
    - The output contains a message indicating that an example workflow file has been generated.
    """
    runner = CliRunner()
    result = runner.invoke(main, ["generate"])
    assert result.exit_code == 0
    assert "Generating an example workflow file" in result.output
    # confirm the `workflow.yml` file is created
    assert Path("workflow.yml").exists()


def test_test():
    """
    Test the test subcommand of the CLI.

    This test uses the CliRunner to invoke the test subcommand of the CLI application
    and checks the following:
    - The exit code of the command is 0, indicating successful
    - The output contains a message indicating that the workflow file is being tested.
    """

    runner = CliRunner()
    result = runner.invoke(main, ["test", "workflow.yml"])
    assert result.exit_code == 0
    assert "Testing the workflow file at workflow.yml" in result.output
