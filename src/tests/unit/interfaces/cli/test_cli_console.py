from unittest.mock import patch, MagicMock

import pytest

from interfaces.cli.console import ConsoleApp


class TestConsole:
    @patch("interfaces.cli.console.StockAgent")
    def test_init(self, mock_agent):
        app = ConsoleApp()
        assert app.raw_output is False
        assert mock_agent.called

    @patch("interfaces.cli.console.StockAgent")
    def test_toggle_raw(self, mock_agent):
        app = ConsoleApp()
        assert app.raw_output is False
        app.toggle_raw()
        assert app.raw_output is True
        app.toggle_raw()
        assert app.raw_output is False

    @patch("interfaces.cli.console.StockAgent")
    def test_print_json(self, mock_agent, capsys):
        app = ConsoleApp()
        app.print_json({"key": "value"})
        captured = capsys.readouterr()
        assert '"key": "value"' in captured.out

    @patch("interfaces.cli.console.StockAgent")
    def test_clear_screen_does_not_crash(self, mock_agent):
        app = ConsoleApp()
        app.clear_screen()

    @patch("interfaces.cli.console.StockAgent")
    def test_handle_command_exit(self, mock_agent):
        app = ConsoleApp()
        with pytest.raises(SystemExit):
            app.handle_command("/exit")

    @patch("interfaces.cli.console.StockAgent")
    def test_handle_command_clear(self, mock_agent):
        app = ConsoleApp()
        app.clear_screen = MagicMock()
        app.handle_command("/clear")
        app.clear_screen.assert_called_once()

    @patch("interfaces.cli.console.StockAgent")
    def test_handle_command_help(self, mock_agent, capsys):
        app = ConsoleApp()
        app.handle_command("/help")
        captured = capsys.readouterr()
        assert "/exit" in captured.out

    @patch("interfaces.cli.console.StockAgent")
    def test_handle_command_unknown(self, mock_agent, capsys):
        app = ConsoleApp()
        app.handle_command("/unknown")
        captured = capsys.readouterr()
        assert "Unknown command" in captured.out

    @patch("interfaces.cli.console.StockAgent")
    def test_handle_command_raw_toggle(self, mock_agent):
        app = ConsoleApp()
        app.handle_command("/raw")
        assert app.raw_output is True

    @patch("interfaces.cli.console.StockAgent")
    def test_agent_init_failure(self, mock_agent):
        mock_agent.side_effect = RuntimeError("no api key")
        with pytest.raises(SystemExit):
            ConsoleApp()

    @patch("interfaces.cli.console.StockAgent")
    @patch("interfaces.cli.console.GuardrailPipeline", side_effect=Exception("no guardrail"))
    def test_guardrail_init_failure(self, mock_gr, mock_agent):
        app = ConsoleApp()
        assert app.guardrail_pipeline is None


class TestConsoleGuardrailIntegration:
    @patch("interfaces.cli.console.StockAgent")
    @patch("interfaces.cli.console.GuardrailPipeline")
    def test_guardrail_blocks_query(self, mock_gr, mock_agent, capsys):
        mock_gr.return_value.check.return_value = MagicMock(passed=False)
        app = ConsoleApp()
        with patch("builtins.input", side_effect=["bad query", "/exit"]):
            with pytest.raises(SystemExit):
                app.run()
        captured = capsys.readouterr()
        assert "không thể xử lý" in captured.out


# -- run() scenarios -------------------------------------------------------


@patch("interfaces.cli.console.StockAgent")
@patch("interfaces.cli.console.GuardrailPipeline")
def test_run_empty_input_skips(mock_gr, mock_agent, capsys):
    mock_gr.return_value.check.return_value = MagicMock(passed=True)
    app = ConsoleApp()
    with patch("builtins.input", side_effect=["", "/exit"]):
        with pytest.raises(SystemExit):
            app.run()


@patch("interfaces.cli.console.StockAgent")
def test_run_keyboard_interrupt(mock_agent, capsys):
    app = ConsoleApp()
    with patch("builtins.input", side_effect=KeyboardInterrupt):
        app.run()
    captured = capsys.readouterr()
    assert "Bye" in captured.out


@patch("interfaces.cli.console.StockAgent")
def test_run_eof_error(mock_agent, capsys):
    app = ConsoleApp()
    with patch("builtins.input", side_effect=EOFError):
        app.run()
    captured = capsys.readouterr()
    assert "Bye" in captured.out


@patch("interfaces.cli.console.StockAgent")
@patch("interfaces.cli.console.GuardrailPipeline")
def test_run_agent_exception(mock_gr, mock_agent, capsys):
    mock_gr.return_value.check.return_value = MagicMock(passed=True)
    mock_agent.return_value.run.side_effect = RuntimeError("api error")
    app = ConsoleApp()
    with patch("builtins.input", side_effect=["test query", "/exit"]):
        with pytest.raises(SystemExit):
            app.run()
    captured = capsys.readouterr()
    assert "Error" in captured.out


@patch("interfaces.cli.console.StockAgent")
@patch("interfaces.cli.console.GuardrailPipeline")
def test_run_raw_output_mode(mock_gr, mock_agent, capsys):
    mock_gr.return_value.check.return_value = MagicMock(passed=True)
    mock_agent.return_value.run.return_value = {"result": "data"}
    app = ConsoleApp()
    app.raw_output = True
    with patch("builtins.input", side_effect=["test query", "/exit"]):
        with pytest.raises(SystemExit):
            app.run()
    captured = capsys.readouterr()
    assert '"result"' in captured.out


@patch("interfaces.cli.console.StockAgent")
@patch("interfaces.cli.console.GuardrailPipeline")
def test_run_guardrail_passed_processes_query(mock_gr, mock_agent, capsys):
    mock_gr.return_value.check.return_value = MagicMock(passed=True)
    mock_agent.return_value.run.return_value = "VCB price is 100"
    app = ConsoleApp()
    with patch("builtins.input", side_effect=["giá VCB", "/exit"]):
        with pytest.raises(SystemExit):
            app.run()
    captured = capsys.readouterr()
    assert "VCB" in captured.out
