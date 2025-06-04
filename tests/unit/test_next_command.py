"""Unit tests for the next command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_sdlc.commands import next as next_cmd


class TestNextCommand:
    """Test cases for next command functionality."""

    def test_validate_required_files_missing_prev_file(
        self, temp_project_dir: Path, capsys
    ):
        """Test validation when previous step file is missing."""
        prev_file = temp_project_dir / "missing.md"
        prompt_file = temp_project_dir / "prompt.yml"
        prompt_file.write_text("content")

        with pytest.raises(SystemExit) as exc_info:
            next_cmd._validate_required_files(
                prev_file, prompt_file, "00-idea", "01-prd", {}
            )
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "previous step's output file" in captured.out
        assert "missing.md" in captured.out

    def test_validate_required_files_missing_prompt_file(
        self, temp_project_dir: Path, capsys
    ):
        """Test validation when prompt file is missing."""
        prev_file = temp_project_dir / "prev.md"
        prev_file.write_text("content")
        prompt_file = temp_project_dir / "missing-prompt.yml"

        with pytest.raises(SystemExit) as exc_info:
            next_cmd._validate_required_files(
                prev_file, prompt_file, "00-idea", "01-prd", {"prompt_dir": "prompts"}
            )
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Prompt template file" in captured.out
        assert "missing-prompt.yml" in captured.out

    def test_read_and_merge_content(self, temp_project_dir: Path, capsys):
        """Test reading and merging content."""
        prev_file = temp_project_dir / "prev.md"
        prev_file.write_text("Previous content")

        prompt_file = temp_project_dir / "prompt.yml"
        prompt_file.write_text("Before <prev_step></prev_step> After")

        result = next_cmd._read_and_merge_content(prev_file, prompt_file)
        assert result == "Before Previous content After"

        captured = capsys.readouterr()
        assert "Reading previous step from" in captured.out
        assert "Reading prompt template from" in captured.out

    def test_apply_context7_enrichment_disabled(self):
        """Test Context7 enrichment when disabled."""
        conf = {"context7": {"enabled": False}}
        prompt = "Test prompt"

        result = next_cmd._apply_context7_enrichment(
            conf, prompt, Path("."), ["00-idea"], 0, "test", "01-prd"
        )
        assert result == prompt

    def test_apply_context7_enrichment_enabled(self, temp_project_dir: Path, capsys):
        """Test Context7 enrichment when enabled."""
        conf = {"context7": {"enabled": True}}
        prompt = "Test prompt"

        mock_service = MagicMock()
        mock_service.enrich_prompt.return_value = "Enriched prompt"

        with patch("ai_sdlc.commands.next.Context7Service", return_value=mock_service):
            result = next_cmd._apply_context7_enrichment(
                conf, prompt, temp_project_dir, ["00-idea"], 0, "test", "01-prd"
            )

        assert result == "Enriched prompt"
        mock_service.enrich_prompt.assert_called_once()

        captured = capsys.readouterr()
        assert "Enriching prompt with Context7 documentation" in captured.out

    def test_handle_next_step_file_exists(self, temp_project_dir: Path, capsys):
        """Test handling when next step file already exists."""
        next_file = temp_project_dir / "next.md"
        next_file.write_text("content")
        prompt_file = temp_project_dir / "prompt.md"
        prompt_file.write_text("prompt")

        lock = {"current": "00-idea"}

        with patch("ai_sdlc.commands.next.write_lock") as mock_write_lock:
            next_cmd._handle_next_step_file(next_file, "01-prd", lock, prompt_file)

            # Verify lock was updated
            assert lock["current"] == "01-prd"
            mock_write_lock.assert_called_once_with(lock)

        # Verify prompt file was cleaned up
        assert not prompt_file.exists()

        captured = capsys.readouterr()
        assert "Found existing file" in captured.out
        assert "Advanced to step: 01-prd" in captured.out
        assert "Cleaned up prompt file" in captured.out

    def test_handle_next_step_file_not_exists(self, temp_project_dir: Path, capsys):
        """Test handling when next step file doesn't exist."""
        next_file = temp_project_dir / "next.md"
        prompt_file = temp_project_dir / "prompt.md"
        lock = {"current": "00-idea"}

        next_cmd._handle_next_step_file(next_file, "01-prd", lock, prompt_file)

        captured = capsys.readouterr()
        assert "Waiting for you to create" in captured.out
        assert str(next_file) in captured.out

    def test_validate_workflow_state_no_lock(self, capsys):
        """Test workflow validation with no lock."""
        with pytest.raises(SystemExit) as exc_info:
            next_cmd._validate_workflow_state({}, {})
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "No active workstream" in captured.out

    def test_validate_workflow_state_all_complete(self, capsys):
        """Test workflow validation when all steps are complete."""
        conf = {"steps": ["00-idea", "01-prd"]}
        lock = {"slug": "test", "current": "01-prd"}

        with pytest.raises(SystemExit) as exc_info:
            next_cmd._validate_workflow_state(conf, lock)
        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "All steps complete" in captured.out

    def test_validate_workflow_state_success(self):
        """Test successful workflow validation."""
        conf = {"steps": ["00-idea", "01-prd", "02-prd-plus"]}
        lock = {"slug": "test", "current": "00-idea"}

        slug, idx, steps = next_cmd._validate_workflow_state(conf, lock)
        assert slug == "test"
        assert idx == 0
        assert steps == ["00-idea", "01-prd", "02-prd-plus"]

    def test_prepare_file_paths(self, temp_project_dir: Path):
        """Test file path preparation."""
        conf = {"active_dir": "doing", "prompt_dir": "prompts"}

        with patch("ai_sdlc.commands.next.ROOT", temp_project_dir):
            workdir, prev_file, prompt_file, next_file, prompt_output = (
                next_cmd._prepare_file_paths(conf, "test-feature", "00-idea", "01-prd")
            )

        assert workdir == temp_project_dir / "doing" / "test-feature"
        assert prev_file == workdir / "00-idea-test-feature.md"
        assert prompt_file == temp_project_dir / "prompts" / "01-prd.prompt.yml"
        assert next_file == workdir / "01-prd-test-feature.md"
        assert prompt_output == workdir / "_prompt-01-prd.md"

    def test_run_next_full_flow(self, temp_project_dir: Path, capsys):
        """Test complete next command flow."""
        # Setup configuration
        conf = {
            "steps": ["00-idea", "01-prd", "02-prd-plus"],
            "active_dir": "doing",
            "prompt_dir": "prompts",
            "context7": {"enabled": False},
        }
        lock = {"slug": "test-feature", "current": "00-idea"}

        # Create necessary directories and files
        workdir = temp_project_dir / "doing" / "test-feature"
        workdir.mkdir(parents=True)

        prev_file = workdir / "00-idea-test-feature.md"
        prev_file.write_text("# Test Feature\n\nThis is the idea.")

        prompt_dir = temp_project_dir / "prompts"
        prompt_dir.mkdir()
        prompt_file = prompt_dir / "01-prd.prompt.yml"
        prompt_file.write_text("Generate PRD for:\n<prev_step></prev_step>")

        with patch("ai_sdlc.commands.next.ROOT", temp_project_dir):
            with patch("ai_sdlc.commands.next.load_config", return_value=conf):
                with patch("ai_sdlc.commands.next.read_lock", return_value=lock):
                    next_cmd.run_next()

        # Verify prompt output file was created
        prompt_output = workdir / "_prompt-01-prd.md"
        assert prompt_output.exists()
        assert "Generate PRD for:" in prompt_output.read_text()
        assert "This is the idea" in prompt_output.read_text()

        captured = capsys.readouterr()
        assert "Reading previous step" in captured.out
        assert "Generated AI prompt file" in captured.out
        assert "run 'aisdlc next' again" in captured.out
