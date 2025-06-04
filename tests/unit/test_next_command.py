# tests/unit/test_next_command.py

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_sdlc.commands.next import run_next
from ai_sdlc.services.ai_service import (
    AiServiceError,
    ApiKeyMissingError,
    OpenAIError,
    UnsupportedProviderError,
)
from ai_sdlc.types import AiProviderConfig, ConfigDict, LockDict

# Default values for fixtures
DEFAULT_SLUG = "test-project"
DEFAULT_STEPS = ["00-setup", "01-design", "02-impl"]
DEFAULT_CURRENT_STEP = "00-setup"
DEFAULT_NEXT_STEP = "01-design"

PROMPT_TEMPLATE_CONTENT = (
    "Prompt for <prev_step></prev_step> to generate " + DEFAULT_NEXT_STEP
)
PREV_STEP_CONTENT = "Content from previous step: " + DEFAULT_CURRENT_STEP
PLACEHOLDER = "<prev_step></prev_step>"


@pytest.fixture
def mock_config_base() -> ConfigDict:
    return {
        "version": "0.7.0",
        "steps": DEFAULT_STEPS,
        "active_dir": "active",
        "done_dir": "done",
        "prompt_dir": "prompts",
        "context7": {"enabled": False},  # Disable context7 by default for these tests
        # ai_provider will be added by other fixtures
    }  # type: ignore


@pytest.fixture
def mock_ai_provider_openai_direct(
    openai_provider_config: AiProviderConfig,
) -> AiProviderConfig:
    # openai_provider_config is from conftest.py or test_ai_service.py if run together
    # For isolation, define it here or ensure conftest provides it.
    # Assuming it's available from test_ai_service.py's fixtures for now.
    # If not, we need to define a similar fixture here.
    # Let's define a minimal one here for test_next_command's direct use.
    return {
        "name": "openai",
        "model": "gpt-3.5-turbo",
        "api_key_env_var": "OPENAI_API_KEY_TEST_NEXT",  # Use a distinct env var for clarity
        "direct_api_calls": True,
        "timeout_seconds": 60,
    }


@pytest.fixture
def mock_ai_provider_openai_direct_no_key(
    mock_ai_provider_openai_direct: AiProviderConfig,
) -> AiProviderConfig:
    config = mock_ai_provider_openai_direct.copy()
    # To simulate ApiKeyMissingError due to env var not set, we rely on os.environ manipulation
    # or ensure the specific env var for this config is not set.
    # For ApiKeyMissingError due to config, we'd change "api_key_env_var".
    return config


@pytest.fixture
def mock_ai_provider_manual() -> AiProviderConfig:
    return {
        "name": "manual",
        "model": "",
        "api_key_env_var": "",
        "direct_api_calls": False,  # Can be True or False, 'manual' name takes precedence
        "timeout_seconds": 60,
    }


@pytest.fixture
def mock_ai_provider_direct_disabled(
    mock_ai_provider_openai_direct: AiProviderConfig,
) -> AiProviderConfig:
    config = mock_ai_provider_openai_direct.copy()
    config["direct_api_calls"] = False
    return config


# Fixture to combine base config with different AI provider configs
@pytest.fixture
def mock_config(mock_config_base: ConfigDict, request) -> ConfigDict:
    # request.param will be the AiProviderConfig
    # Default to manual if no param is passed, or handle explicitly
    ai_provider_conf = getattr(request, "param", mock_ai_provider_manual())
    full_config = mock_config_base.copy()
    full_config["ai_provider"] = ai_provider_conf
    return full_config


@pytest.fixture
def mock_lock() -> LockDict:
    return {
        "slug": DEFAULT_SLUG,
        "current": DEFAULT_CURRENT_STEP,
        "created": "2023-01-01T12:00:00Z",
    }


# This fixture will create actual files in tmp_path for more robust testing
@pytest.fixture
def setup_working_directory(
    tmp_path: Path, mock_config: ConfigDict, mock_lock: LockDict
):
    # Create directories
    (tmp_path / mock_config["active_dir"] / mock_lock["slug"]).mkdir(
        parents=True, exist_ok=True
    )
    (tmp_path / mock_config["prompt_dir"]).mkdir(parents=True, exist_ok=True)

    # Create previous step file
    prev_file_path = (
        tmp_path
        / mock_config["active_dir"]
        / mock_lock["slug"]
        / f"{DEFAULT_CURRENT_STEP}-{mock_lock['slug']}.md"
    )
    prev_file_path.write_text(PREV_STEP_CONTENT)

    # Create prompt template file
    prompt_template_path = (
        tmp_path / mock_config["prompt_dir"] / f"{DEFAULT_NEXT_STEP}.prompt.yml"
    )
    prompt_template_path.write_text(PROMPT_TEMPLATE_CONTENT)

    return tmp_path  # Return root tmp_path, specific paths can be derived in tests


# Mocks for external dependencies of run_next
@pytest.fixture(autouse=True)  # Applied to all tests in this file
def auto_mock_dependencies(request):  # `request` allows conditional mocking if needed
    # Basic mocks, can be overridden per test using @patch if specific behavior is needed

    # Mock file system interactions that are not covered by tmp_path setup
    # For example, if Path.exists() is called on a non-tmp_path file, or if we want to simulate non-existence easily.
    # However, for files managed by setup_working_directory, their existence is real.

    mock_load_conf = patch("ai_sdlc.commands.next.load_config").start()
    # We'll set mock_load_conf.return_value in tests that use mock_config fixture

    mock_rlock = patch("ai_sdlc.commands.next.read_lock").start()
    # We'll set mock_rlock.return_value in tests that use mock_lock fixture

    mock_wlock = patch("ai_sdlc.commands.next.write_lock").start()

    # Mock context7 enrichment to return prompt as is, simplifying tests
    mock_context7 = patch(
        "ai_sdlc.commands.next._apply_context7_enrichment",
        side_effect=lambda conf, prompt, *args: prompt,
    ).start()

    # Mock the AI service's generate_text function within the next.py module
    mock_gen_text = patch("ai_sdlc.commands.next.generate_text").start()

    # Mock ROOT to point to tmp_path for consistency if any code uses utils.ROOT directly
    # This assumes setup_working_directory is used, which provides tmp_path
    # Note: This might be tricky if utils.ROOT is used at module import time elsewhere.
    # For next.py, it seems ROOT is used to construct paths relative to the project root.
    # If tests use tmp_path correctly, direct mocking of ROOT might not be strictly needed
    # for `next` command's own operations if all paths are derived from config + slug.
    # Let's assume for now that path constructions in `next.py` are relative to `tmp_path`
    # when `active_dir` and `prompt_dir` are used from config.
    # If `ai_sdlc.utils.ROOT` is used by `next.py` to prefix these, then it needs mocking.
    # `_prepare_file_paths` uses `ROOT / conf["active_dir"]` and `ROOT / conf["prompt_dir"]`.
    # So, utils.ROOT needs to be tmp_path.

    mock_root_util = patch("ai_sdlc.utils.ROOT").start()
    # We will set mock_root_util in tests via the setup_working_directory fixture, effectively.
    # No, `auto_mock_dependencies` runs before `setup_working_directory` can set it.
    # This needs careful handling. It's better if `run_next` gets `ROOT` via dependency injection or
    # if tests ensure `utils.ROOT` is patched *before* `run_next` is called.
    # The `start()` method returns the MagicMock instance.

    yield {  # Provide mocks to tests if they need to inspect/modify them
        "load_config": mock_load_conf,
        "read_lock": mock_rlock,
        "write_lock": mock_wlock,
        "apply_context7": mock_context7,
        "generate_text": mock_gen_text,
        "utils_ROOT": mock_root_util,
    }

    patch.stopall()  # Stop all patches started with start()


# Test Scenarios for run_next()


@pytest.mark.parametrize(
    "mock_config",
    [pytest.lazy_fixture("mock_ai_provider_openai_direct")],
    indirect=True,
)
def test_run_next_direct_api_call_success(
    mock_config: ConfigDict,
    mock_lock: LockDict,
    setup_working_directory: Path,
    auto_mock_dependencies: dict,
    capsys: pytest.CaptureFixture,
):
    root_path = setup_working_directory
    auto_mock_dependencies[
        "utils_ROOT"
    ].return_value = root_path  # Critical for path resolution
    auto_mock_dependencies["load_config"].return_value = mock_config
    auto_mock_dependencies["read_lock"].return_value = mock_lock

    mock_generate_text_func = auto_mock_dependencies["generate_text"]
    mock_generate_text_func.return_value = "AI generated content successfully."

    # Set OPENAI_API_KEY_TEST_NEXT for this test environment
    with patch.dict(
        os.environ, {mock_config["ai_provider"]["api_key_env_var"]: "fake_key_for_test"}
    ):
        run_next()

    captured = capsys.readouterr()
    assert "🤖 Attempting to generate text using AI provider: openai..." in captured.out
    assert "✅ AI successfully generated content and saved to:" in captured.out

    next_step_file = (
        root_path
        / mock_config["active_dir"]
        / mock_lock["slug"]
        / f"{DEFAULT_NEXT_STEP}-{mock_lock['slug']}.md"
    )
    assert next_step_file.exists()
    assert next_step_file.read_text() == "AI generated content successfully."

    prompt_output_file = (
        root_path
        / mock_config["active_dir"]
        / mock_lock["slug"]
        / f"_prompt-{DEFAULT_NEXT_STEP}.md"
    )
    assert not prompt_output_file.exists()  # Should be cleaned up or not created

    auto_mock_dependencies["write_lock"].assert_called_once_with(
        {
            "slug": mock_lock["slug"],
            "current": DEFAULT_NEXT_STEP,
            "created": mock_lock["created"],
        }
    )
    # Ensure context7 was called (even if it does nothing)
    auto_mock_dependencies["apply_context7"].assert_called_once()


@pytest.mark.parametrize(
    "mock_config",
    [pytest.lazy_fixture("mock_ai_provider_openai_direct")],
    indirect=True,
)
@pytest.mark.parametrize(
    "error_to_raise, error_name_in_output",
    [
        (ApiKeyMissingError("Test API Key Missing"), "API Key Missing Error"),
        (
            UnsupportedProviderError("Test Unsupported Provider"),
            "Unsupported Provider Error",
        ),
        (OpenAIError("Test OpenAI Error"), "OpenAI API Error"),
        (AiServiceError("Test Generic AI Service Error"), "AI Service Error"),
        (
            Exception("Test Unexpected Error during API call"),
            "An unexpected error occurred",
        ),
    ],
)
def test_run_next_direct_api_call_errors_fallback_to_manual(
    mock_config: ConfigDict,
    mock_lock: LockDict,
    setup_working_directory: Path,
    auto_mock_dependencies: dict,
    capsys: pytest.CaptureFixture,
    error_to_raise: Exception,
    error_name_in_output: str,
):
    root_path = setup_working_directory
    auto_mock_dependencies["utils_ROOT"].return_value = root_path
    auto_mock_dependencies["load_config"].return_value = mock_config
    auto_mock_dependencies["read_lock"].return_value = mock_lock

    mock_generate_text_func = auto_mock_dependencies["generate_text"]
    mock_generate_text_func.side_effect = error_to_raise

    # For ApiKeyMissingError, ensure the env var is set if the error is NOT about the env var itself
    # If error_to_raise is ApiKeyMissingError and is about config, key should be set.
    # If it's about env var, key should NOT be set.
    # The test for ApiKeyMissingError here is generic; specific get_api_key tests are in test_ai_service.
    # Here, we assume generate_text raises it, implying get_api_key might have, or other logic.
    # Let's ensure the key is present for non-ApiKeyMissingError cases to avoid that being the cause.
    env_var_name = mock_config["ai_provider"]["api_key_env_var"]
    with patch.dict(
        os.environ,
        {env_var_name: "fake_key_for_test"}
        if not isinstance(error_to_raise, ApiKeyMissingError)
        else {},
    ):
        # If it IS ApiKeyMissingError, we want it to be due to the mocked side_effect, not actual missing key.
        # So, if the side_effect is ApiKeyMissingError, the key *could* be present or not,
        # as the mock overrides the actual get_api_key call path within generate_text.
        # For this test, we're testing generate_text's behavior *when it raises*, so env var state is secondary
        # to the mock's side_effect.
        run_next()

    captured = capsys.readouterr()
    assert "🤖 Attempting to generate text using AI provider: openai..." in captured.out
    assert f"❌ {error_name_in_output}: {error_to_raise}" in captured.out
    assert "Falling back to manual prompt generation." in captured.out
    assert "📝  Generated AI prompt file:" in captured.out  # Manual instructions shown

    next_step_file = (
        root_path
        / mock_config["active_dir"]
        / mock_lock["slug"]
        / f"{DEFAULT_NEXT_STEP}-{mock_lock['slug']}.md"
    )
    assert not next_step_file.exists()  # AI content not written

    prompt_output_file = (
        root_path
        / mock_config["active_dir"]
        / mock_lock["slug"]
        / f"_prompt-{DEFAULT_NEXT_STEP}.md"
    )
    assert prompt_output_file.exists()  # Manual prompt file IS created
    expected_prompt_content = PROMPT_TEMPLATE_CONTENT.replace(
        PLACEHOLDER, PREV_STEP_CONTENT
    )
    assert prompt_output_file.read_text() == expected_prompt_content

    # Lock state should NOT advance because next_file is not created
    auto_mock_dependencies["write_lock"].assert_not_called()


@pytest.mark.parametrize(
    "mock_config",
    [pytest.lazy_fixture("mock_ai_provider_direct_disabled")],
    indirect=True,
)
def test_run_next_direct_api_calls_disabled(
    mock_config: ConfigDict,
    mock_lock: LockDict,
    setup_working_directory: Path,
    auto_mock_dependencies: dict,
    capsys: pytest.CaptureFixture,
):
    root_path = setup_working_directory
    auto_mock_dependencies["utils_ROOT"].return_value = root_path
    auto_mock_dependencies["load_config"].return_value = mock_config
    auto_mock_dependencies["read_lock"].return_value = mock_lock

    mock_generate_text_func = auto_mock_dependencies["generate_text"]

    run_next()

    captured = capsys.readouterr()
    assert (
        "ℹ️  Direct API calls are disabled or provider is not configured for direct calls."
        in captured.out
    )
    assert "📝  Generated AI prompt file:" in captured.out

    mock_generate_text_func.assert_not_called()  # Crucial check

    prompt_output_file = (
        root_path
        / mock_config["active_dir"]
        / mock_lock["slug"]
        / f"_prompt-{DEFAULT_NEXT_STEP}.md"
    )
    assert prompt_output_file.exists()
    expected_prompt_content = PROMPT_TEMPLATE_CONTENT.replace(
        PLACEHOLDER, PREV_STEP_CONTENT
    )
    assert prompt_output_file.read_text() == expected_prompt_content

    auto_mock_dependencies["write_lock"].assert_not_called()  # No advance


@pytest.mark.parametrize(
    "mock_config", [pytest.lazy_fixture("mock_ai_provider_manual")], indirect=True
)
def test_run_next_manual_provider(
    mock_config: ConfigDict,
    mock_lock: LockDict,
    setup_working_directory: Path,
    auto_mock_dependencies: dict,
    capsys: pytest.CaptureFixture,
):
    root_path = setup_working_directory
    auto_mock_dependencies["utils_ROOT"].return_value = root_path
    auto_mock_dependencies["load_config"].return_value = mock_config
    auto_mock_dependencies["read_lock"].return_value = mock_lock

    mock_generate_text_func = auto_mock_dependencies["generate_text"]

    run_next()

    captured = capsys.readouterr()
    # No specific message for "manual mode selected", just straight to prompt generation
    assert "📝  Generated AI prompt file:" in captured.out

    mock_generate_text_func.assert_not_called()

    prompt_output_file = (
        root_path
        / mock_config["active_dir"]
        / mock_lock["slug"]
        / f"_prompt-{DEFAULT_NEXT_STEP}.md"
    )
    assert prompt_output_file.exists()
    expected_prompt_content = PROMPT_TEMPLATE_CONTENT.replace(
        PLACEHOLDER, PREV_STEP_CONTENT
    )
    assert prompt_output_file.read_text() == expected_prompt_content

    auto_mock_dependencies["write_lock"].assert_not_called()


@pytest.mark.parametrize(
    "mock_config", [pytest.lazy_fixture("mock_ai_provider_manual")], indirect=True
)  # Config doesn't matter much here
def test_run_next_step_file_already_exists(
    mock_config: ConfigDict,
    mock_lock: LockDict,
    setup_working_directory: Path,
    auto_mock_dependencies: dict,
    capsys: pytest.CaptureFixture,
):
    root_path = setup_working_directory
    auto_mock_dependencies["utils_ROOT"].return_value = root_path
    auto_mock_dependencies["load_config"].return_value = mock_config
    auto_mock_dependencies["read_lock"].return_value = mock_lock

    mock_generate_text_func = auto_mock_dependencies["generate_text"]

    # Pre-create the next_step_file
    next_step_file_path = (
        root_path
        / mock_config["active_dir"]
        / mock_lock["slug"]
        / f"{DEFAULT_NEXT_STEP}-{mock_lock['slug']}.md"
    )
    next_step_file_path.write_text("Already existing content.")

    # Also create the _prompt file, to check if it gets cleaned up
    prompt_output_file = (
        root_path
        / mock_config["active_dir"]
        / mock_lock["slug"]
        / f"_prompt-{DEFAULT_NEXT_STEP}.md"
    )
    prompt_output_file.write_text("Temporary prompt content.")

    run_next()

    captured = capsys.readouterr()
    # Should not attempt API call or write prompt if file exists
    assert "Attempting to generate text" not in captured.out
    assert (
        "Generated AI prompt file" not in captured.out
    )  # The _write_prompt_and_show_instructions is skipped

    assert "✅  Found existing file:" in captured.out
    assert "✅  Advanced to step: " + DEFAULT_NEXT_STEP in captured.out
    assert (
        "🧹  Cleaned up prompt file:" in captured.out
    )  # _prompt file should be cleaned

    mock_generate_text_func.assert_not_called()

    auto_mock_dependencies["write_lock"].assert_called_once_with(
        {
            "slug": mock_lock["slug"],
            "current": DEFAULT_NEXT_STEP,
            "created": mock_lock["created"],
        }
    )
    assert not prompt_output_file.exists()  # Check it was actually deleted


# Test for workflow completion
@pytest.mark.parametrize(
    "mock_config", [pytest.lazy_fixture("mock_ai_provider_manual")], indirect=True
)
def test_run_next_all_steps_complete(
    mock_config: ConfigDict,
    mock_lock: LockDict,
    setup_working_directory: Path,
    auto_mock_dependencies: dict,
    capsys: pytest.CaptureFixture,
):
    root_path = setup_working_directory
    auto_mock_dependencies["utils_ROOT"].return_value = root_path
    auto_mock_dependencies["load_config"].return_value = mock_config

    # Modify lock to be the last step
    completed_lock = mock_lock.copy()
    completed_lock["current"] = DEFAULT_STEPS[-1]  # e.g. "02-impl"
    auto_mock_dependencies["read_lock"].return_value = completed_lock

    mock_exit = patch.object(sys, "exit").start()

    run_next()

    captured = capsys.readouterr()
    assert "🎉  All steps complete. Run `aisdlc done` to archive." in captured.out
    mock_exit.assert_called_once_with(0)
    auto_mock_dependencies["generate_text"].assert_not_called()
    auto_mock_dependencies["write_lock"].assert_not_called()
    patch.stopall()  # Stop sys.exit mock


# Test for missing previous step file
@pytest.mark.parametrize(
    "mock_config", [pytest.lazy_fixture("mock_ai_provider_manual")], indirect=True
)
def test_run_next_missing_prev_file(
    mock_config: ConfigDict,
    mock_lock: LockDict,
    setup_working_directory: Path,
    auto_mock_dependencies: dict,
    capsys: pytest.CaptureFixture,
):
    root_path = setup_working_directory
    auto_mock_dependencies["utils_ROOT"].return_value = root_path
    auto_mock_dependencies["load_config"].return_value = mock_config
    auto_mock_dependencies["read_lock"].return_value = mock_lock

    # Delete the previous step file that setup_working_directory created
    prev_file_path = (
        root_path
        / mock_config["active_dir"]
        / mock_lock["slug"]
        / f"{DEFAULT_CURRENT_STEP}-{mock_lock['slug']}.md"
    )
    if prev_file_path.exists():
        prev_file_path.unlink()

    mock_exit = patch.object(sys, "exit").start()
    run_next()

    captured = capsys.readouterr()
    assert (
        f"❌ Error: The previous step's output file '{prev_file_path}' is missing."
        in captured.out
    )
    mock_exit.assert_called_once_with(1)
    patch.stopall()  # Stop sys.exit mock


# Test for missing prompt template file
@pytest.mark.parametrize(
    "mock_config", [pytest.lazy_fixture("mock_ai_provider_manual")], indirect=True
)
def test_run_next_missing_prompt_template_file(
    mock_config: ConfigDict,
    mock_lock: LockDict,
    setup_working_directory: Path,
    auto_mock_dependencies: dict,
    capsys: pytest.CaptureFixture,
):
    root_path = setup_working_directory
    auto_mock_dependencies["utils_ROOT"].return_value = root_path
    auto_mock_dependencies["load_config"].return_value = mock_config
    auto_mock_dependencies["read_lock"].return_value = mock_lock

    # Delete the prompt template file that setup_working_directory created
    prompt_template_path = (
        root_path / mock_config["prompt_dir"] / f"{DEFAULT_NEXT_STEP}.prompt.yml"
    )
    if prompt_template_path.exists():
        prompt_template_path.unlink()

    mock_exit = patch.object(sys, "exit").start()
    run_next()

    captured = capsys.readouterr()
    assert (
        f"❌ Critical Error: Prompt template file '{prompt_template_path}' is missing."
        in captured.out
    )
    mock_exit.assert_called_once_with(1)
    patch.stopall()  # Stop sys.exit mock


# Test that if ai_provider_config is missing entirely from config, it defaults to manual-like behavior
@pytest.mark.parametrize(
    "mock_config", [pytest.lazy_fixture("mock_ai_provider_manual")], indirect=True
)  # Start with a base
def test_run_next_missing_ai_provider_section_in_config(
    mock_config: ConfigDict,  # This will have ai_provider due to fixture setup
    mock_lock: LockDict,
    setup_working_directory: Path,
    auto_mock_dependencies: dict,
    capsys: pytest.CaptureFixture,
):
    root_path = setup_working_directory
    auto_mock_dependencies["utils_ROOT"].return_value = root_path

    # Modify the config to remove ai_provider section
    config_no_ai_section = mock_config.copy()
    if "ai_provider" in config_no_ai_section:
        del config_no_ai_section["ai_provider"]

    auto_mock_dependencies["load_config"].return_value = config_no_ai_section
    auto_mock_dependencies["read_lock"].return_value = mock_lock

    mock_generate_text_func = auto_mock_dependencies["generate_text"]

    run_next()

    captured = capsys.readouterr()
    # Should behave like manual mode: no API call attempt, just prompt generation.
    # No specific error message about missing section, just proceeds to manual.
    assert "Attempting to generate text" not in captured.out
    assert (
        "📝  Generated AI prompt file:" in captured.out
    )  # Falls back to manual prompt generation

    mock_generate_text_func.assert_not_called()

    prompt_output_file = (
        root_path
        / config_no_ai_section["active_dir"]
        / mock_lock["slug"]
        / f"_prompt-{DEFAULT_NEXT_STEP}.md"
    )
    assert prompt_output_file.exists()
    expected_prompt_content = PROMPT_TEMPLATE_CONTENT.replace(
        PLACEHOLDER, PREV_STEP_CONTENT
    )
    assert prompt_output_file.read_text() == expected_prompt_content

    auto_mock_dependencies["write_lock"].assert_not_called()


# Test for `ai_provider_config.get("name")` being None or missing, expecting default to "manual"
@pytest.mark.parametrize(
    "mock_config",
    [pytest.lazy_fixture("mock_ai_provider_openai_direct")],
    indirect=True,
)
def test_run_next_ai_provider_name_missing(
    mock_config: ConfigDict,
    mock_lock: LockDict,
    setup_working_directory: Path,
    auto_mock_dependencies: dict,
    capsys: pytest.CaptureFixture,
):
    root_path = setup_working_directory
    auto_mock_dependencies["utils_ROOT"].return_value = root_path

    config_provider_name_missing = mock_config.copy()
    # Ensure ai_provider dict exists but 'name' is missing
    # Casting to AiProviderConfig for type safety, but then deleting a required key for test
    provider_details = config_provider_name_missing["ai_provider"].copy()  # type: ignore
    if "name" in provider_details:
        del provider_details["name"]
    config_provider_name_missing["ai_provider"] = provider_details

    auto_mock_dependencies["load_config"].return_value = config_provider_name_missing
    auto_mock_dependencies["read_lock"].return_value = mock_lock

    mock_generate_text_func = auto_mock_dependencies["generate_text"]

    run_next()  # Should default to manual behavior due to name missing

    captured = capsys.readouterr()
    assert "📝  Generated AI prompt file:" in captured.out
    mock_generate_text_func.assert_not_called()  # Because name defaults to 'manual'


# Test for `ai_provider_config.get("direct_api_calls")` being missing, expecting default to False
@pytest.mark.parametrize(
    "mock_config",
    [pytest.lazy_fixture("mock_ai_provider_openai_direct")],
    indirect=True,
)
def test_run_next_ai_provider_direct_api_calls_missing(
    mock_config: ConfigDict,
    mock_lock: LockDict,
    setup_working_directory: Path,
    auto_mock_dependencies: dict,
    capsys: pytest.CaptureFixture,
):
    root_path = setup_working_directory
    auto_mock_dependencies["utils_ROOT"].return_value = root_path

    config_direct_calls_missing = mock_config.copy()
    provider_details = config_direct_calls_missing["ai_provider"].copy()  # type: ignore
    if "direct_api_calls" in provider_details:
        del provider_details["direct_api_calls"]  # Remove the key
    # 'name' is still 'openai', but direct_api_calls defaults to False
    config_direct_calls_missing["ai_provider"] = provider_details

    auto_mock_dependencies["load_config"].return_value = config_direct_calls_missing
    auto_mock_dependencies["read_lock"].return_value = mock_lock

    mock_generate_text_func = auto_mock_dependencies["generate_text"]

    run_next()

    captured = capsys.readouterr()
    # Should fall back to manual because direct_api_calls defaults to False
    assert (
        "ℹ️  Direct API calls are disabled or provider is not configured for direct calls."
        in captured.out
    )
    assert "📝  Generated AI prompt file:" in captured.out
    mock_generate_text_func.assert_not_called()


# Ensure conftest.py or relevant fixtures are available if this file is run standalone
# For AiProviderConfig fixtures like openai_provider_config:
# If they are defined in test_ai_service.py, pytest might pick them up if tests are run together.
# For robustness, important shared fixtures could be in a conftest.py at the 'tests' or 'tests/unit' level.
# The current mock_ai_provider_openai_direct is defined locally, which is fine.
# The parametrize for mock_config indirectly uses these AiProviderConfig fixtures.
# Make sure `openai_provider_config` fixture (if used by name from another file) is accessible.
# Here, `mock_ai_provider_openai_direct` is defined locally, so it's fine.
