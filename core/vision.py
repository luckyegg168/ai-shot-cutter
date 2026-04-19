"""OpenAI GPT-4o Vision wrapper — pure Python, no Qt imports."""
from __future__ import annotations

import base64
import time
from pathlib import Path

from .models import VisionError

_IMAGE_SYSTEM_PROMPT = (
    "You are an expert AI art director. Analyze this frame and generate a detailed, "
    "high-quality text-to-image prompt suitable for Midjourney, DALL-E 3, or Stable Diffusion. "
    "Include: subject, composition, lighting, color palette, mood, style, camera angle, "
    "and technical quality descriptors. Output only the prompt text, no explanations."
)

_VIDEO_SYSTEM_PROMPT = (
    "You are an expert AI video director. Analyze this frame and generate a detailed "
    "text-to-video prompt suitable for Sora, Runway, or Pika Labs. "
    "Include: scene description, camera movement, subject action, lighting, atmosphere, "
    "duration hint, and cinematic style. Output only the prompt text, no explanations."
)

_CHARACTER_SYSTEM_PROMPT = (
    "You are an expert character designer and AI art director. Analyze this frame and generate "
    "a detailed text-to-image prompt focused on character design. "
    "Include: character appearance, clothing style, facial features, pose, expression, "
    "art style (e.g. anime, realistic, painterly), lighting setup, and background context. "
    "Output only the prompt text, no explanations."
)

_LANDSCAPE_SYSTEM_PROMPT = (
    "You are an expert landscape and environment concept artist. Analyze this frame and generate "
    "a detailed text-to-image prompt focused on the environment and scenery. "
    "Include: terrain type, vegetation, weather conditions, time of day, atmospheric effects, "
    "color palette, perspective/composition, and emotional mood. "
    "Output only the prompt text, no explanations."
)

_PRODUCT_SYSTEM_PROMPT = (
    "You are an expert product photographer and AI art director. Analyze this frame and generate "
    "a detailed text-to-image prompt for product visualization. "
    "Include: product description, materials and textures, lighting setup (key/fill/rim), "
    "background style, shadows, reflections, and commercial photography aesthetic. "
    "Output only the prompt text, no explanations."
)

_ARCHITECTURE_SYSTEM_PROMPT = (
    "You are an expert architectural renderer and AI art director. Analyze this frame and generate "
    "a detailed text-to-image prompt focused on architectural visualization. "
    "Include: building style/era, materials and finishes, structural details, surrounding "
    "environment, lighting conditions, perspective type, and rendering quality descriptors. "
    "Output only the prompt text, no explanations."
)

_SYSTEM_PROMPTS: dict[str, str] = {
    "image":        _IMAGE_SYSTEM_PROMPT,
    "video":        _VIDEO_SYSTEM_PROMPT,
    "character":    _CHARACTER_SYSTEM_PROMPT,
    "landscape":    _LANDSCAPE_SYSTEM_PROMPT,
    "product":      _PRODUCT_SYSTEM_PROMPT,
    "architecture": _ARCHITECTURE_SYSTEM_PROMPT,
}


def _encode_image(image_path: Path) -> str:
    """Return base64-encoded JPEG data URL."""
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/jpeg;base64,{data}"


def analyze_frame(
    image_path: Path,
    api_key: str,
    prompt_type: str,
    *,
    use_local_model: bool = False,
    local_model_url: str = "",
    model_name: str = "",
    custom_system_prompt: str = "",
) -> str:
    """Send a frame to GPT-4o Vision (or local model) and return a prompt string.

    Args:
        image_path: Path to the JPEG frame.
        api_key: OpenAI API key (sk-…) or local model token.
        prompt_type: "image" or "video".
        use_local_model: If True, use local_model_url instead of OpenAI.
        local_model_url: Base URL for OpenAI-compatible local API.
        model_name: Model name override (e.g. "llava", "gpt-4o").
        custom_system_prompt: User-defined system prompt (overrides default).

    Returns:
        Non-empty prompt string.

    Raises:
        VisionError: On API failure after retries.
    """
    try:
        from openai import OpenAI, APIStatusError  # type: ignore
    except ImportError as exc:
        raise VisionError("openai package is not installed. Run: pip install openai") from exc

    # Determine system prompt
    if custom_system_prompt.strip():
        system_prompt = custom_system_prompt.strip()
    else:
        system_prompt = _SYSTEM_PROMPTS.get(prompt_type, _IMAGE_SYSTEM_PROMPT)

    image_data_url = _encode_image(image_path)

    # Build client: local model or OpenAI
    if use_local_model and local_model_url.strip():
        client = OpenAI(
            api_key=api_key if api_key.strip() else "local-no-key",
            base_url=local_model_url.strip(),
        )
    else:
        client = OpenAI(api_key=api_key)

    chosen_model = model_name.strip() if model_name.strip() else "gpt-4o"

    last_error: Exception | None = None
    for attempt, delay in enumerate([0, 1, 2, 4]):
        if delay:
            time.sleep(delay)
        try:
            response = client.chat.completions.create(
                model=chosen_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": image_data_url, "detail": "high"},
                            }
                        ],
                    },
                ],
                max_tokens=500,
            )
            text = response.choices[0].message.content or ""
            if not text.strip():
                raise VisionError("GPT-4o returned an empty response")
            return text.strip()

        except APIStatusError as exc:
            last_error = exc
            status = exc.status_code
            if status == 401:
                raise VisionError("Invalid OpenAI API key (401). Check your sk-… key.") from exc
            if status == 429:
                # Rate limited — always retry
                continue
            if 500 <= status < 600:
                # Server error — retry
                continue
            raise VisionError(f"OpenAI API error {status}: {exc.message}") from exc
        except Exception as exc:
            last_error = exc
            if attempt < 3:
                continue
            break

    raise VisionError(f"GPT-4o Vision failed after retries: {last_error}")
