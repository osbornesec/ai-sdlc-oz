# tests/unit/test_ai_service.py

import os
from unittest.mock import MagicMock, patch

import pytest

# Attempt to import actual openai errors for isinstance checks if available
try:
    import openai
    # Specific exceptions to use in isinstance checks if needed, not for raising directly in mocks
    ActualAPIAuthError = openai.AuthenticationError
    ActualAPITimeoutError = openai.APITimeoutError
    ActualRateLimitError = openai.RateLimitError
    ActualAPIConnectionError = openai.APIConnectionError
    ActualAPIStatusError = openai.APIStatusError
except ImportError:
    openai = None # type: ignore
    ActualAPIAuthError = Exception
    ActualAPITimeoutError = Exception
    ActualRateLimitError = Exception
    ActualAPIConnectionError = Exception
    ActualAPIStatusError = Exception


from ai_sdlc.services.ai_service import (
    generate_text,
    get_api_key,
    generate_text_openai,
    AiServiceError,
    UnsupportedProviderError,
    ApiKeyMissingError,
    OpenAIError,
    AnthropicError, # Import new error
    generate_text_anthropic, # Import new function
)
from ai_sdlc.types import AiProviderConfig

# Attempt to import actual anthropic errors for isinstance checks if available
try:
    import anthropic as actual_anthropic_lib
    # Specific exceptions to use in isinstance checks if needed
    ActualAnthropicAPIAuthError = actual_anthropic_lib.AuthenticationError
    ActualAnthropicAPITimeoutError = actual_anthropic_lib.APITimeoutError
    ActualAnthropicRateLimitError = actual_anthropic_lib.RateLimitError
    ActualAnthropicAPIConnectionError = actual_anthropic_lib.APIConnectionError
    ActualAnthropicAPIStatusError = actual_anthropic_lib.APIStatusError
    # Note: Anthropic doesn't have a general APIError exception
except ImportError:
    actual_anthropic_lib = None # type: ignore
    ActualAnthropicAPIAuthError = Exception
    ActualAnthropicAPITimeoutError = Exception
    ActualAnthropicRateLimitError = Exception
    ActualAnthropicAPIConnectionError = Exception
    ActualAnthropicAPIStatusError = Exception

# Define a mock for the openai module's parts that are used,
# This helps in environments where openai might not be installed
# or when we want to precisely control its behavior.
class MockOpenAIModule:
    """Mocks the `openai` module and its `OpenAI` client class."""

    # Mocked Exception classes that mirror real OpenAI exceptions
    # These are raised by the *mocked* client below
    class AuthenticationError(Exception): pass
    class APITimeoutError(Exception): pass
    class RateLimitError(Exception): pass
    class APIConnectionError(Exception): pass
    class APIStatusError(Exception):
        def __init__(self, message, *, response, body=None): # Match real signature
            super().__init__(message)
            self.response = response
            # Ensure status_code is available on the mock response for the error handler
            self.status_code = getattr(response, 'status_code', 500)
            self.body = body

    class OpenAI:
        """Mocks the `openai.OpenAI` client class."""
        def __init__(self, api_key: str):
            self.api_key = api_key
            # This instance will be replaced by a MagicMock in tests that need to mock methods like chat.completions.create
            self.chat = MagicMock()
            self.chat.completions = MagicMock()

class MockAnthropicModule:
    """Mocks the `anthropic` module and its `Anthropic` client class."""
    class AuthenticationError(Exception): pass
    class APITimeoutError(Exception): pass
    class RateLimitError(Exception): pass
    class APIConnectionError(Exception): pass
    class APIStatusError(Exception):
        def __init__(self, message, *, response, body=None):
            super().__init__(message)
            self.response = response
            self.status_code = getattr(response, 'status_code', 500)
            self.body = body
    # Note: Anthropic doesn't have a general APIError exception

    class Anthropic:
        """Mocks the `anthropic.Anthropic` client class."""
        def __init__(self, api_key: str, timeout: float):
            self.api_key = api_key
            self.timeout = timeout
            self.messages = MagicMock()


# Fixtures for AiProviderConfig
@pytest.fixture
def anthropic_provider_config() -> AiProviderConfig:
    return {
        "name": "anthropic",
        "model": "claude-3-opus-20240229",
        "api_key_env_var": "ANTHROPIC_API_KEY",
        "direct_api_calls": True,
        "timeout_seconds": 70, # Different from openai for distinction
    }

@pytest.fixture
def openai_provider_config() -> AiProviderConfig:
    return {
        "name": "openai",
        "model": "gpt-3.5-turbo",
        "api_key_env_var": "OPENAI_API_KEY",
        "direct_api_calls": True, # This field is for ai_sdlc.commands.next, not ai_service directly
        "timeout_seconds": 60,
    }

@pytest.fixture
def manual_provider_config() -> AiProviderConfig:
    return {
        "name": "manual",
        "model": "", # Typically empty for manual
        "api_key_env_var": "", # Typically empty for manual
        "direct_api_calls": False,
        "timeout_seconds": 60, # Can still have a timeout
    }

@pytest.fixture
def custom_provider_config() -> AiProviderConfig: # For testing unsupported provider
    return {
        "name": "custom_provider",
        "model": "custom_model",
        "api_key_env_var": "CUSTOM_API_KEY",
        "direct_api_calls": True,
        "timeout_seconds": 30,
    }

# Tests for get_api_key()
def test_get_api_key_success(openai_provider_config: AiProviderConfig):
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key_123"}):
        assert get_api_key(openai_provider_config) == "test_key_123"

def test_get_api_key_missing_config_var_key(openai_provider_config: AiProviderConfig):
    config_no_env_var_key = openai_provider_config.copy()
    del config_no_env_var_key["api_key_env_var"]

    with pytest.raises(ApiKeyMissingError, match="Configuration error: 'api_key_env_var' is not set"):
        get_api_key(config_no_env_var_key)

def test_get_api_key_empty_config_var_value(openai_provider_config: AiProviderConfig):
    config_empty_env_var_value = openai_provider_config.copy()
    config_empty_env_var_value["api_key_env_var"] = ""
    with pytest.raises(ApiKeyMissingError, match="Configuration error: 'api_key_env_var' is not set"):
        get_api_key(config_empty_env_var_value)

def test_get_api_key_env_var_not_set(openai_provider_config: AiProviderConfig):
    env_var_name = openai_provider_config["api_key_env_var"]
    # Ensure the env var is not set by temporarily removing it if it exists
    original_value = os.environ.pop(env_var_name, None)

    with pytest.raises(ApiKeyMissingError, match=f"API key not found: Environment variable {env_var_name} is not set"):
        get_api_key(openai_provider_config)

    if original_value is not None: # Restore it if it was originally set
        os.environ[env_var_name] = original_value


# Tests for generate_text_openai()
# Since openai is imported inside the function, we mock sys.modules
def test_generate_text_openai_success(openai_provider_config: AiProviderConfig):
    mock_openai_module = MockOpenAIModule()
    
    with patch.dict('sys.modules', {'openai': mock_openai_module}):
        mock_openai_client_instance = MagicMock() # Mock the client instance
        mock_chat_completion = MagicMock()
        mock_chat_completion.message = MagicMock()
        mock_chat_completion.message.content = "Successfully generated text"
        
        # Configure the 'create' method on the client instance's chat.completions attribute
        mock_openai_client_instance.chat.completions.create.return_value = MagicMock(choices=[mock_chat_completion])
        
        # Now, we need `MockOpenAIModule.OpenAI` (the class) to return this `mock_openai_client_instance` when called.
        mock_openai_module.OpenAI = MagicMock(return_value=mock_openai_client_instance)
        
        response = generate_text_openai(
            prompt="A test prompt",
            model=openai_provider_config["model"],
            api_key="a_test_key",
            timeout_seconds=openai_provider_config["timeout_seconds"]
        )
        assert response == "Successfully generated text"
        mock_openai_module.OpenAI.assert_called_once_with(api_key="a_test_key")
        mock_openai_client_instance.chat.completions.create.assert_called_once_with(
            model=openai_provider_config["model"],
            messages=[{"role": "user", "content": "A test prompt"}],
            timeout=openai_provider_config["timeout_seconds"]
        )

def test_generate_text_openai_empty_content(openai_provider_config: AiProviderConfig):
    mock_openai_module = MockOpenAIModule()
    
    with patch.dict('sys.modules', {'openai': mock_openai_module}):
        mock_openai_client_instance = MagicMock()
        mock_chat_completion = MagicMock()
        mock_chat_completion.message = MagicMock()
        mock_chat_completion.message.content = None # Simulate empty content from API
        mock_openai_client_instance.chat.completions.create.return_value = MagicMock(choices=[mock_chat_completion])
        mock_openai_module.OpenAI = MagicMock(return_value=mock_openai_client_instance)
        
        with pytest.raises(OpenAIError, match="OpenAI API returned an empty message content."):
            generate_text_openai(
                "Prompt for empty",
                openai_provider_config["model"],
                "another_key",
                openai_provider_config["timeout_seconds"]
            )

# Parametrize for different OpenAI exceptions defined in our MockOpenAIModule
@pytest.mark.parametrize(
    "openai_exception_class_name, expected_message_snippet",
    [
        ("AuthenticationError", "OpenAI API Authentication Error"),
        ("APITimeoutError", "OpenAI API Timeout Error"),
        ("RateLimitError", "OpenAI API Rate Limit Error"),
        ("APIConnectionError", "OpenAI API Connection Error"),
    ]
)
def test_generate_text_openai_standard_exceptions(
    openai_provider_config: AiProviderConfig,
    openai_exception_class_name: str, expected_message_snippet: str
):
    mock_openai_module = MockOpenAIModule()
    
    with patch.dict('sys.modules', {'openai': mock_openai_module}):
        ExceptionToRaise = getattr(mock_openai_module, openai_exception_class_name)
        
        mock_openai_client_instance = MagicMock()
        mock_openai_client_instance.chat.completions.create.side_effect = ExceptionToRaise("Mocked API error details")
        mock_openai_module.OpenAI = MagicMock(return_value=mock_openai_client_instance)
        
        with pytest.raises(OpenAIError, match=expected_message_snippet):
            generate_text_openai(
                "A prompt",
                openai_provider_config["model"],
                "a_key",
                openai_provider_config["timeout_seconds"]
            )

def test_generate_text_openai_apistatuserror(openai_provider_config: AiProviderConfig):
    mock_openai_module = MockOpenAIModule()
    
    with patch.dict('sys.modules', {'openai': mock_openai_module}):
        mock_api_response = MagicMock()
        mock_api_response.status_code = 403 # Example: Forbidden
        
        # Use the APIStatusError from our MockOpenAIModule for raising
        status_error_instance = mock_openai_module.APIStatusError(
            "Mocked API Status Error content", response=mock_api_response
        )
        
        mock_openai_client_instance = MagicMock()
        mock_openai_client_instance.chat.completions.create.side_effect = status_error_instance
        mock_openai_module.OpenAI = MagicMock(return_value=mock_openai_client_instance)
        
        with pytest.raises(OpenAIError, match=r"OpenAI API Error \(Status 403\):"):
            generate_text_openai(
                "A prompt",
                openai_provider_config["model"],
                "a_key",
                openai_provider_config["timeout_seconds"]
            )

def test_generate_text_openai_unexpected_exception(openai_provider_config: AiProviderConfig):
    mock_openai_module = MockOpenAIModule()
    
    with patch.dict('sys.modules', {'openai': mock_openai_module}):
        mock_openai_client_instance = MagicMock()
        mock_openai_client_instance.chat.completions.create.side_effect = ValueError("Completely unexpected error") # e.g. a ValueError
        mock_openai_module.OpenAI = MagicMock(return_value=mock_openai_client_instance)
        
        with pytest.raises(OpenAIError, match="An unexpected error occurred with OpenAI: Completely unexpected error"):
            generate_text_openai(
                "A prompt",
                openai_provider_config["model"],
                "a_key",
                openai_provider_config["timeout_seconds"]
            )

# Tests for generate_text_anthropic()
def test_generate_text_anthropic_success(anthropic_provider_config: AiProviderConfig):
    mock_anthropic_module = MockAnthropicModule()
    
    with patch.dict('sys.modules', {'anthropic': mock_anthropic_module}):
        mock_anthropic_client_instance = MagicMock()
        mock_message_response = MagicMock()
        # Anthropic response structure: response.content is a list of ContentBlock objects.
        # For text, it's typically a TextBlock.
        mock_text_block = MagicMock()
        mock_text_block.text = "Successfully generated text from Anthropic"
        mock_message_response.content = [mock_text_block]
        
        mock_anthropic_client_instance.messages.create.return_value = mock_message_response
        mock_anthropic_module.Anthropic = MagicMock(return_value=mock_anthropic_client_instance)
        
        response = generate_text_anthropic(
            prompt="A test prompt for Anthropic",
            model=anthropic_provider_config["model"],
            api_key="an_anthropic_key",
            timeout_seconds=anthropic_provider_config["timeout_seconds"]
        )
        assert response == "Successfully generated text from Anthropic"
        mock_anthropic_module.Anthropic.assert_called_once_with(api_key="an_anthropic_key", timeout=float(anthropic_provider_config["timeout_seconds"]))
        mock_anthropic_client_instance.messages.create.assert_called_once_with(
            model=anthropic_provider_config["model"],
            max_tokens=4096,
            messages=[{"role": "user", "content": "A test prompt for Anthropic"}],
        )

def test_generate_text_anthropic_empty_content(anthropic_provider_config: AiProviderConfig):
    mock_anthropic_module = MockAnthropicModule()
    
    with patch.dict('sys.modules', {'anthropic': mock_anthropic_module}):
        mock_anthropic_client_instance = MagicMock()
        mock_message_response = MagicMock()
        mock_text_block = MagicMock()
        mock_text_block.text = None # Simulate empty text content
        mock_message_response.content = [mock_text_block]
        mock_anthropic_client_instance.messages.create.return_value = mock_message_response
        mock_anthropic_module.Anthropic = MagicMock(return_value=mock_anthropic_client_instance)
        
        with pytest.raises(AnthropicError, match="Anthropic API returned empty message content."):
            generate_text_anthropic("Prompt", anthropic_provider_config["model"], "key", 60)

def test_generate_text_anthropic_unexpected_content_structure(anthropic_provider_config: AiProviderConfig):
    mock_anthropic_module = MockAnthropicModule()
    
    with patch.dict('sys.modules', {'anthropic': mock_anthropic_module}):
        mock_anthropic_client_instance = MagicMock()
        mock_message_response_empty_content_list = MagicMock()
        mock_message_response_empty_content_list.content = [] # Empty list
        mock_anthropic_client_instance.messages.create.return_value = mock_message_response_empty_content_list
        mock_anthropic_module.Anthropic = MagicMock(return_value=mock_anthropic_client_instance)
        
        with pytest.raises(AnthropicError, match="Anthropic API returned unexpected or empty content structure."):
            generate_text_anthropic("Prompt", anthropic_provider_config["model"], "key", 60)
        
        mock_message_response_no_text_attr = MagicMock()
        mock_non_text_block = MagicMock(spec=[]) # A block that doesn't have 'text'
        mock_message_response_no_text_attr.content = [mock_non_text_block]
        mock_anthropic_client_instance.messages.create.return_value = mock_message_response_no_text_attr
        with pytest.raises(AnthropicError, match="Anthropic API returned unexpected or empty content structure."):
            generate_text_anthropic("Prompt", anthropic_provider_config["model"], "key", 60)


@pytest.mark.parametrize(
    "anthropic_exception_class_name, expected_message_snippet",
    [
        ("AuthenticationError", "Anthropic API Authentication Error"),
        ("APITimeoutError", "Anthropic API Timeout Error"),
        ("RateLimitError", "Anthropic API Rate Limit Error"),
        ("APIConnectionError", "Anthropic API Connection Error"),
    ]
)
def test_generate_text_anthropic_standard_exceptions(
    anthropic_provider_config: AiProviderConfig,
    anthropic_exception_class_name: str, expected_message_snippet: str
):
    mock_anthropic_module = MockAnthropicModule()
    
    with patch.dict('sys.modules', {'anthropic': mock_anthropic_module}):
        ExceptionToRaise = getattr(mock_anthropic_module, anthropic_exception_class_name)
        
        mock_anthropic_client_instance = MagicMock()
        mock_anthropic_client_instance.messages.create.side_effect = ExceptionToRaise("Mocked Anthropic API error")
        mock_anthropic_module.Anthropic = MagicMock(return_value=mock_anthropic_client_instance)
        
        with pytest.raises(AnthropicError, match=expected_message_snippet):
            generate_text_anthropic("Prompt", anthropic_provider_config["model"], "key", 60)

def test_generate_text_anthropic_apistatuserror(anthropic_provider_config: AiProviderConfig):
    mock_anthropic_module = MockAnthropicModule()
    
    with patch.dict('sys.modules', {'anthropic': mock_anthropic_module}):
        mock_api_response = MagicMock()
        mock_api_response.status_code = 401
        status_error_instance = mock_anthropic_module.APIStatusError(
            "Mocked Anthropic API Status Error", response=mock_api_response
        )
        mock_anthropic_client_instance = MagicMock()
        mock_anthropic_client_instance.messages.create.side_effect = status_error_instance
        mock_anthropic_module.Anthropic = MagicMock(return_value=mock_anthropic_client_instance)
        
        with pytest.raises(AnthropicError, match=r"Anthropic API Error \(Status 401\):"):
            generate_text_anthropic("Prompt", anthropic_provider_config["model"], "key", 60)

def test_generate_text_anthropic_unexpected_exception(anthropic_provider_config: AiProviderConfig):
    mock_anthropic_module = MockAnthropicModule()
    
    with patch.dict('sys.modules', {'anthropic': mock_anthropic_module}):
        mock_anthropic_client_instance = MagicMock()
        mock_anthropic_client_instance.messages.create.side_effect = TypeError("Unexpected TypeError from Anthropic client")
        mock_anthropic_module.Anthropic = MagicMock(return_value=mock_anthropic_client_instance)
        
        with pytest.raises(AnthropicError, match="An unexpected error occurred with Anthropic: Unexpected TypeError"):
            generate_text_anthropic("Prompt", anthropic_provider_config["model"], "key", 60)

# Test with custom max_tokens
def test_generate_text_anthropic_custom_max_tokens(anthropic_provider_config: AiProviderConfig):
    mock_anthropic_module = MockAnthropicModule()
    
    with patch.dict('sys.modules', {'anthropic': mock_anthropic_module}):
        mock_anthropic_client_instance = MagicMock()
        mock_message_response = MagicMock()
        mock_text_block = MagicMock()
        mock_text_block.text = "Generated with custom max_tokens"
        mock_message_response.content = [mock_text_block]
        
        mock_anthropic_client_instance.messages.create.return_value = mock_message_response
        mock_anthropic_module.Anthropic = MagicMock(return_value=mock_anthropic_client_instance)
        
        response = generate_text_anthropic(
            prompt="Test prompt",
            model=anthropic_provider_config["model"],
            api_key="test_key",
            timeout_seconds=60,
            max_tokens=2048
        )
        
        assert response == "Generated with custom max_tokens"
        mock_anthropic_client_instance.messages.create.assert_called_once_with(
            model=anthropic_provider_config["model"],
            max_tokens=2048,  # Should use the provided value
            messages=[{"role": "user", "content": "Test prompt"}],
        )

# Test timeout validation
def test_generate_text_openai_negative_timeout():
    with pytest.raises(AiServiceError, match="timeout_seconds must be a positive integer"):
        generate_text_openai("prompt", "gpt-3.5-turbo", "key", -5)

def test_generate_text_openai_zero_timeout():
    with pytest.raises(AiServiceError, match="timeout_seconds must be a positive integer"):
        generate_text_openai("prompt", "gpt-3.5-turbo", "key", 0)

def test_generate_text_anthropic_negative_timeout():
    with pytest.raises(AiServiceError, match="timeout_seconds must be a positive integer"):
        generate_text_anthropic("prompt", "claude-3-opus", "key", -1)

# Test missing library imports
def test_generate_text_openai_missing_library():
    with patch('builtins.__import__', side_effect=ImportError("No module named 'openai'")):
        with pytest.raises(AiServiceError, match="OpenAI library is not installed"):
            generate_text_openai("prompt", "gpt-3.5-turbo", "key", 30)

def test_generate_text_anthropic_missing_library():
    with patch('builtins.__import__', side_effect=ImportError("No module named 'anthropic'")):
        with pytest.raises(AiServiceError, match="Anthropic library is not installed"):
            generate_text_anthropic("prompt", "claude-3-opus", "key", 30)


# Tests for generate_text() (main dispatcher)

@patch("ai_sdlc.services.ai_service.generate_text_openai")
@patch("ai_sdlc.services.ai_service.get_api_key")
def test_generate_text_openai_provider_success_calls(
    mock_get_api_key: MagicMock,
    mock_generate_text_openai_func: MagicMock,
    openai_provider_config: AiProviderConfig
):
    mock_get_api_key.return_value = "retrieved_api_key"
    mock_generate_text_openai_func.return_value = "Expected AI output"

    result = generate_text("Input prompt", openai_provider_config)

    assert result == "Expected AI output"
    mock_get_api_key.assert_called_once_with(openai_provider_config)
    mock_generate_text_openai_func.assert_called_once_with(
        "Input prompt",
        openai_provider_config["model"],
        "retrieved_api_key",
        openai_provider_config["timeout_seconds"]
    )

def test_generate_text_manual_provider_behavior(manual_provider_config: AiProviderConfig):
    result = generate_text("Any prompt", manual_provider_config)
    assert result == "AI provider is set to 'manual'. No API call will be made."

@patch("ai_sdlc.services.ai_service.get_api_key")
def test_generate_text_unsupported_provider_error(mock_get_api_key: MagicMock, custom_provider_config: AiProviderConfig):
    mock_get_api_key.return_value = "custom_key_value"

    with pytest.raises(UnsupportedProviderError, match="Unsupported AI provider: custom_provider. Supported providers are: 'openai', 'anthropic', 'manual'."):
        generate_text("A prompt", custom_provider_config)
    mock_get_api_key.assert_called_once_with(custom_provider_config)


@patch("ai_sdlc.services.ai_service.generate_text_anthropic")
@patch("ai_sdlc.services.ai_service.get_api_key")
def test_generate_text_anthropic_provider_success_calls(
    mock_get_api_key: MagicMock,
    mock_generate_text_anthropic_func: MagicMock,
    anthropic_provider_config: AiProviderConfig
):
    mock_get_api_key.return_value = "retrieved_anthropic_key"
    mock_generate_text_anthropic_func.return_value = "Expected Anthropic AI output"

    result = generate_text("Input prompt for Anthropic", anthropic_provider_config)

    assert result == "Expected Anthropic AI output"
    mock_get_api_key.assert_called_once_with(anthropic_provider_config)
    mock_generate_text_anthropic_func.assert_called_once_with(
        "Input prompt for Anthropic",
        anthropic_provider_config["model"],
        "retrieved_anthropic_key",
        anthropic_provider_config["timeout_seconds"],
        None  # max_tokens not set in config
    )

# Test with max_tokens in config
@patch("ai_sdlc.services.ai_service.generate_text_anthropic")
@patch("ai_sdlc.services.ai_service.get_api_key")
def test_generate_text_anthropic_with_max_tokens_config(
    mock_get_api_key: MagicMock,
    mock_generate_text_anthropic_func: MagicMock,
    anthropic_provider_config: AiProviderConfig
):
    anthropic_config_with_max_tokens = anthropic_provider_config.copy()
    anthropic_config_with_max_tokens["max_tokens"] = 2048
    
    mock_get_api_key.return_value = "api_key"
    mock_generate_text_anthropic_func.return_value = "Result"
    
    result = generate_text("Prompt", anthropic_config_with_max_tokens)
    
    assert result == "Result"
    mock_generate_text_anthropic_func.assert_called_once_with(
        "Prompt",
        anthropic_config_with_max_tokens["model"],
        "api_key",
        anthropic_config_with_max_tokens["timeout_seconds"],
        2048  # max_tokens from config
    )


def test_generate_text_missing_model_for_api_provider(openai_provider_config: AiProviderConfig, anthropic_provider_config: AiProviderConfig):
    # Test for OpenAI
    config_missing_model_openai = openai_provider_config.copy()
    del config_missing_model_openai["model"]
    with pytest.raises(AiServiceError, match="Configuration error: 'model' is not set for provider 'openai'"):
        generate_text("A prompt", config_missing_model_openai)

    config_empty_model_openai = openai_provider_config.copy()
    config_empty_model_openai["model"] = ""
    with pytest.raises(AiServiceError, match="Configuration error: 'model' is not set for provider 'openai'"):
        generate_text("A prompt", config_empty_model_openai)

    # Test for Anthropic
    config_missing_model_anthropic = anthropic_provider_config.copy()
    del config_missing_model_anthropic["model"]
    with pytest.raises(AiServiceError, match="Configuration error: 'model' is not set for provider 'anthropic'"):
        generate_text("A prompt", config_missing_model_anthropic)

    config_empty_model_anthropic = anthropic_provider_config.copy()
    config_empty_model_anthropic["model"] = ""
    with pytest.raises(AiServiceError, match="Configuration error: 'model' is not set for provider 'anthropic'"):
        generate_text("A prompt", config_empty_model_anthropic)


def test_generate_text_api_key_error_propagates(openai_provider_config: AiProviderConfig):
    # This test relies on get_api_key raising an error, so no need to mock get_api_key itself.
    # We just need to ensure the environment variable is not set.
    env_var_name = openai_provider_config["api_key_env_var"]
    original_value = os.environ.pop(env_var_name, None)

    with pytest.raises(ApiKeyMissingError): # The specific message is tested in get_api_key tests
        generate_text("A prompt", openai_provider_config)

    if original_value is not None:
        os.environ[env_var_name] = original_value


@patch("ai_sdlc.services.ai_service.generate_text_openai")
@patch("ai_sdlc.services.ai_service.get_api_key")
def test_generate_text_default_timeout_used(
    mock_get_api_key: MagicMock,
    mock_generate_text_openai_func: MagicMock,
    openai_provider_config: AiProviderConfig
):
    mock_get_api_key.return_value = "retrieved_api_key"
    config_no_timeout = openai_provider_config.copy()
    del config_no_timeout["timeout_seconds"] # Remove to test default fallback

    generate_text("A prompt", config_no_timeout)

    mock_generate_text_openai_func.assert_called_once_with(
        "A prompt",
        openai_provider_config["model"],
        "retrieved_api_key",
        60  # Expected default timeout from generate_text's signature for `timeout`
    )

# Test that 'name' defaulting to 'manual' works as expected
@patch("ai_sdlc.services.ai_service.get_api_key")
@patch("ai_sdlc.services.ai_service.generate_text_openai")
@patch("ai_sdlc.services.ai_service.generate_text_anthropic")
def test_generate_text_missing_name_defaults_to_manual(
    mock_generate_text_anthropic_func: MagicMock,
    mock_generate_text_openai_func: MagicMock,
    mock_get_api_key: MagicMock
    ):
    config_no_name: AiProviderConfig = { # type: ignore
        # "name": missing
        "model": "gpt-3.5-turbo", # Model is present
        "api_key_env_var": "SOME_KEY_ENV_VAR", # API key var is present
        "timeout_seconds": 30
    }
    # Set direct_api_calls to True to ensure it's not defaulting to manual due to that
    config_no_name["direct_api_calls"] = True


    result = generate_text("A prompt", config_no_name)
    assert result == "AI provider is set to 'manual'. No API call will be made."
    mock_get_api_key.assert_not_called()
    mock_generate_text_openai_func.assert_not_called()
    mock_generate_text_anthropic_func.assert_not_called()

# Test that get_api_key is NOT called for "manual" provider
@patch("ai_sdlc.services.ai_service.get_api_key")
def test_generate_text_manual_provider_no_api_key_call(mock_get_api_key: MagicMock, manual_provider_config: AiProviderConfig):
    generate_text("Test prompt", manual_provider_config)
    mock_get_api_key.assert_not_called()

# Test that provider-specific generation functions are NOT called for "manual" provider
@patch("ai_sdlc.services.ai_service.generate_text_openai")
@patch("ai_sdlc.services.ai_service.generate_text_anthropic")
def test_generate_text_manual_provider_no_specific_provider_call(
    mock_generate_text_anthropic_func: MagicMock,
    mock_generate_text_openai_func: MagicMock,
    manual_provider_config: AiProviderConfig
):
    generate_text("Test prompt", manual_provider_config)
    mock_generate_text_openai_func.assert_not_called()
    mock_generate_text_anthropic_func.assert_not_called()

# Test that direct_api_calls being part of AiProviderConfig for typing.
# This field is used in `next.py` but good to have a type check here.
def test_provider_config_includes_direct_api_calls(openai_provider_config: AiProviderConfig):
    assert "direct_api_calls" in openai_provider_config
    assert isinstance(openai_provider_config["direct_api_calls"], bool)

# Test APIStatusError with a response that doesn't have status_code (should default)
def test_generate_text_openai_apistatuserror_response_missing_status_code(
    openai_provider_config: AiProviderConfig
):
    mock_openai_module = MockOpenAIModule()
    
    with patch.dict('sys.modules', {'openai': mock_openai_module}):
        mock_response_no_status = MagicMock(spec=[]) # No attributes, so getattr(response, 'status_code', default) will use default.
        
        status_error_instance = mock_openai_module.APIStatusError(
            "Error with response lacking status_code", response=mock_response_no_status
        )
        
        mock_openai_client_instance = MagicMock()
        mock_openai_client_instance.chat.completions.create.side_effect = status_error_instance
        mock_openai_module.OpenAI = MagicMock(return_value=mock_openai_client_instance)
        
        # MockOpenAI.APIStatusError defaults status_code to 500 if not found on response
        with pytest.raises(OpenAIError, match=r"OpenAI API Error \(Status 500\):"):
            generate_text_openai(
                "A prompt",
                openai_provider_config["model"],
                "a_key",
                openai_provider_config["timeout_seconds"]
            )