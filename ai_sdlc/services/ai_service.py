from __future__ import annotations

import os
import openai
import anthropic # For Anthropic Claude
from ..types import AiProviderConfig

# Define custom exceptions for the AI service
class AiServiceError(Exception):
    """Base class for AI service errors."""
    pass

class UnsupportedProviderError(AiServiceError):
    """Raised when an unsupported AI provider is requested."""
    pass

class ApiKeyMissingError(AiServiceError):
    """Raised when the API key is not found in environment variables."""
    pass

class OpenAIError(AiServiceError):
    """Raised for errors specific to OpenAI API calls."""
    pass

class AnthropicError(AiServiceError):
    """Raised for errors specific to Anthropic API calls."""
    pass


def get_api_key(provider_config: AiProviderConfig) -> str:
    api_key_env_var = provider_config.get("api_key_env_var")
    if not api_key_env_var:
        raise ApiKeyMissingError(
            f"Configuration error: 'api_key_env_var' is not set for provider '{provider_config.get('name')}'. "
            "Please set it in your .aisdlc config file."
        )

    api_key = os.environ.get(api_key_env_var)
    if not api_key:
        raise ApiKeyMissingError(
            f"API key not found: Environment variable {api_key_env_var} is not set. "
            "Please set this environment variable to your API key."
        )
    return api_key

def generate_text_openai(
    prompt: str,
    model: str,
    api_key: str,
    timeout_seconds: int
) -> str:
    """Generates text using the OpenAI API."""
    try:
        # Ensure you have the 'openai' library installed and properly configured.
        # Replace with actual client initialization if needed, e.g., openai.OpenAI(api_key=api_key)
        # For newer versions of openai library, client initialization is required.
        # This is a simplified example.
        client = openai.OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            timeout=timeout_seconds,
        )
        # Ensure response format is as expected. Adjust access as per actual response structure.
        # For example, response.choices[0].message.content
        # This example assumes a simplified direct text response, which might not be the case.
        content = response.choices[0].message.content
        if content is None:
            raise OpenAIError("OpenAI API returned an empty message content.")
        return content
    except openai.APIAuthenticationError as e:
        raise OpenAIError(f"OpenAI API Authentication Error: {e}. Check your API key.")
    except openai.APITimeoutError as e:
        raise OpenAIError(f"OpenAI API Timeout Error: {e}. Try increasing timeout_seconds.")
    except openai.APIConnectionError as e:
        raise OpenAIError(f"OpenAI API Connection Error: {e}. Check your network connection.")
    except openai.RateLimitError as e:
        raise OpenAIError(f"OpenAI API Rate Limit Error: {e}. Please check your usage and limits.")
    except openai.APIStatusError as e: # General status error
        raise OpenAIError(f"OpenAI API Error (Status {e.status_code}): {e.response}")
    except Exception as e: # Catch any other OpenAI or unexpected errors
        raise OpenAIError(f"An unexpected error occurred with OpenAI: {e}")


def generate_text_anthropic(
    prompt: str,
    model: str,
    api_key: str,
    timeout_seconds: int
) -> str:
    """Generates text using the Anthropic API."""
    try:
        client = anthropic.Anthropic(api_key=api_key, timeout=float(timeout_seconds)) # timeout expects float

        response = client.messages.create(
            model=model,
            max_tokens=4096,  # Consider making this configurable later
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # According to Anthropic's Python SDK, response.content is a list of ContentBlock objects.
        # We expect a single TextBlock.
        if not response.content or not hasattr(response.content[0], 'text'):
             raise AnthropicError("Anthropic API returned unexpected or empty content structure.")

        content = response.content[0].text
        if content is None: # Should be caught by the above, but as a safeguard
            raise AnthropicError("Anthropic API returned empty message content.")
        return content
    except anthropic.APIAuthenticationError as e:
        raise AnthropicError(f"Anthropic API Authentication Error: {e}. Check your API key.")
    except anthropic.APITimeoutError as e:
        raise AnthropicError(f"Anthropic API Timeout Error: {e}. Try increasing timeout_seconds.")
    except anthropic.APIConnectionError as e:
        raise AnthropicError(f"Anthropic API Connection Error: {e}. Check your network connection.")
    except anthropic.RateLimitError as e:
        raise AnthropicError(f"Anthropic API Rate Limit Error: {e}. Please check your usage and limits.")
    except anthropic.APIStatusError as e: # General status error
        raise AnthropicError(f"Anthropic API Error (Status {e.status_code}): {e.response}")
    except anthropic.APIError as e: # Base error for other Anthropic issues
        raise AnthropicError(f"An Anthropic API error occurred: {e}")
    except Exception as e: # Catch any other unexpected errors
        raise AnthropicError(f"An unexpected error occurred with Anthropic: {e}")


def generate_text(
    prompt: str,
    provider_config: AiProviderConfig
) -> str:
    """
    Generates text using the configured AI provider.

    Args:
        prompt: The prompt to send to the AI.
        provider_config: The AI provider configuration from .aisdlc.

    Returns:
        The text generated by the AI.

    Raises:
        UnsupportedProviderError: If the configured provider is not supported.
        ApiKeyMissingError: If the API key is not found.
        AiServiceError: For other AI service related errors.
    """
    provider_name = provider_config.get("name", "manual")
    model = provider_config.get("model")
    timeout = provider_config.get("timeout_seconds", 60)

    if provider_name == "manual":
        # This case should ideally be handled by the caller,
        # but we can return a message or raise an error.
        return "AI provider is set to 'manual'. No API call will be made."

    if not model:
        raise AiServiceError(f"Configuration error: 'model' is not set for provider '{provider_name}'.")

    api_key = get_api_key(provider_config)

    if provider_name == "openai":
        return generate_text_openai(prompt, model, api_key, timeout)
    elif provider_name == "anthropic":
        return generate_text_anthropic(prompt, model, api_key, timeout)
    else:
        raise UnsupportedProviderError(
            f"Unsupported AI provider: {provider_name}. Supported providers are: 'openai', 'anthropic', 'manual'."
        )
