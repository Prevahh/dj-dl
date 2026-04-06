from click.testing import CliRunner
from dj_dl.cli import main

def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "dj-dl" in result.output

def test_cli_get_help():
    runner = CliRunner()
    result = runner.invoke(main, ["get", "--help"])
    assert result.exit_code == 0
    assert "QUERY" in result.output

def test_cli_sync_help():
    runner = CliRunner()
    result = runner.invoke(main, ["sync", "--help"])
    assert result.exit_code == 0

def test_cli_migrate_help():
    runner = CliRunner()
    result = runner.invoke(main, ["migrate", "--help"])
    assert result.exit_code == 0

def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output
