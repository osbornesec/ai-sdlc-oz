# pyright: reportMissingImports=false
"""Integration tests for the context command."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ai_sdlc.commands.context import run_context


class TestContextCommand:
    """Test context command functionality."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # Create config file
            config = {
                "version": "0.1.0",
                "active_dir": "doing",
                "done_dir": "done",
                "prompt_dir": "prompts",
                "steps": ["00-idea", "01-prd", "02-prd-plus"],
            }
            (project_dir / ".aisdlc").write_text(
                f"""
                version = "{config["version"]}"
                active_dir = "{config["active_dir"]}"
                done_dir = "{config["done_dir"]}"
                prompt_dir = "{config["prompt_dir"]}"
                steps = {json.dumps(config["steps"])}
                """
            )

            # Create lock file
            lock = {"slug": "test-project", "current": "00-idea"}
            (project_dir / ".aisdlc.lock").write_text(json.dumps(lock))

            # Create project directories
            (project_dir / "doing" / "test-project").mkdir(parents=True)

            # Create idea file with library mentions
            idea_file = (
                project_dir / "doing" / "test-project" / "00-idea-test-project.md"
            )
            idea_file.write_text("""
# Test Project

Building a web app using React and FastAPI.
Database will be PostgreSQL.
""")

            yield project_dir

    def test_context_no_args(self, temp_project, monkeypatch):
        """Test context command with no arguments."""
        monkeypatch.chdir(temp_project)

        with (
            patch("ai_sdlc.commands.context.ROOT", temp_project),
            patch("ai_sdlc.utils.ROOT", temp_project),
        ):
            with patch("builtins.print") as mock_print:
                run_context([])

        # Should detect libraries and show output
        output = " ".join(str(call[0][0]) for call in mock_print.call_args_list)
        assert "Context7 Library Detection" in output
        assert "react" in output
        assert "fastapi" in output
        assert "postgresql" in output

    def test_context_with_libraries_arg(self, temp_project, monkeypatch):
        """Test context command with --libraries argument."""
        monkeypatch.chdir(temp_project)

        with (
            patch("ai_sdlc.commands.context.ROOT", temp_project),
            patch("ai_sdlc.utils.ROOT", temp_project),
        ):
            with patch("builtins.print") as mock_print:
                run_context(["--libraries", "django,redis"])

        output = " ".join(str(call[0][0]) for call in mock_print.call_args_list)
        assert "django" in output
        assert "redis" in output

    def test_context_invalid_library_name(self, temp_project, monkeypatch):
        """Test context command with invalid library name."""
        monkeypatch.chdir(temp_project)

        with (
            patch("ai_sdlc.commands.context.ROOT", temp_project),
            patch("ai_sdlc.utils.ROOT", temp_project),
        ):
            with pytest.raises(SystemExit):
                with patch("builtins.print") as mock_print:
                    run_context(["--libraries", "inv@lid!"])

        output = " ".join(str(call[0][0]) for call in mock_print.call_args_list)
        assert "Invalid library name" in output

    def test_context_show_cache(self, temp_project, monkeypatch):
        """Test context command with --show-cache."""
        monkeypatch.chdir(temp_project)

        # Create cache directory with a file
        cache_dir = temp_project / ".context7_cache"
        cache_dir.mkdir()
        (cache_dir / "react_00-idea.md").write_text("Cached content")

        with (
            patch("ai_sdlc.commands.context.ROOT", temp_project),
            patch("ai_sdlc.utils.ROOT", temp_project),
        ):
            with patch("builtins.print") as mock_print:
                run_context(["--show-cache"])

        output = " ".join(str(call[0][0]) for call in mock_print.call_args_list)
        assert "Context7 Cache Contents" in output
        assert "react_00-idea" in output

    def test_context_clear_cache(self, temp_project, monkeypatch):
        """Test context command with --clear-cache."""
        monkeypatch.chdir(temp_project)

        # Create cache directory
        cache_dir = temp_project / ".context7_cache"
        cache_dir.mkdir()
        (cache_dir / "test.md").write_text("test")

        with (
            patch("ai_sdlc.commands.context.ROOT", temp_project),
            patch("ai_sdlc.utils.ROOT", temp_project),
        ):
            with patch("builtins.print") as mock_print:
                run_context(["--clear-cache"])

        output = " ".join(str(call[0][0]) for call in mock_print.call_args_list)
        assert "Context7 cache cleared" in output
        assert cache_dir.exists()
        assert not any(cache_dir.iterdir())

    def test_context_no_active_workstream(self, temp_project, monkeypatch):
        """Test context command without active workstream."""
        monkeypatch.chdir(temp_project)

        # Remove lock file
        (temp_project / ".aisdlc.lock").write_text("{}")

        with (
            patch("ai_sdlc.commands.context.ROOT", temp_project),
            patch("ai_sdlc.utils.ROOT", temp_project),
        ):
            with pytest.raises(SystemExit):
                with patch("builtins.print") as mock_print:
                    run_context([])

        output = " ".join(str(call[0][0]) for call in mock_print.call_args_list)
        assert "No active workstream" in output

    def test_context_unknown_argument(self, temp_project, monkeypatch):
        """Test context command with unknown argument."""
        monkeypatch.chdir(temp_project)

        with (
            patch("ai_sdlc.commands.context.ROOT", temp_project),
            patch("ai_sdlc.utils.ROOT", temp_project),
        ):
            with pytest.raises(SystemExit):
                with patch("builtins.print") as mock_print:
                    run_context(["--unknown"])

        output = " ".join(str(call[0][0]) for call in mock_print.call_args_list)
        assert "Unknown argument" in output

    @patch("ai_sdlc.commands.context.Context7Service")
    def test_context_with_step_recommendations(
        self, mock_service_class, temp_project, monkeypatch
    ):
        """Test context command shows step-specific recommendations."""
        monkeypatch.chdir(temp_project)

        # Mock the service
        mock_service = Mock()
        mock_service.extract_libraries_from_text.return_value = ["react"]
        mock_service.get_step_specific_libraries.return_value = ["jest", "vitest"]
        mock_service.create_context_command_output.return_value = "Test output"
        mock_service_class.return_value = mock_service

        # Update lock to be on a test step
        lock = {"slug": "test-project", "current": "01-prd"}
        (temp_project / ".aisdlc.lock").write_text(json.dumps(lock))

        with (
            patch("ai_sdlc.commands.context.ROOT", temp_project),
            patch("ai_sdlc.utils.ROOT", temp_project),
        ):
            with patch("builtins.print") as mock_print:
                run_context([])

        # Should call get_step_specific_libraries for next step
        mock_service.get_step_specific_libraries.assert_called()

        output = " ".join(str(call[0][0]) for call in mock_print.call_args_list)
        assert "Recommended for next step" in output
