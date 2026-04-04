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


def _encode_image(image_path: Path) -> str:
    """Return base64-encoded JPEG data URL."""
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/jpeg;base64,{data}"


def analyze_frame(
    image_path: Path,
    api_key: str,
    prompt_type: str,
) -> str:
    """Send a frame to GPT-4o Vision and return a prompt string.

    Args:
        image_path: Path to the JPEG frame.
        api_key: OpenAI API key (sk-…).
        prompt_type: "image" or "video".

    Returns:
        Non-empty prompt string.

    Raises:
        VisionError: On API failure after retries.
    """
    try:
        from openai import OpenAI, APIStatusError  # type: ignore
    except ImportError as exc:
        raise VisionError("openai package is not installed. Run: pip install openai") from exc

    if prompt_type == "video":
        system_prompt = _VIDEO_SYSTEM_PROMPT
    else:
        system_prompt = _IMAGE_SYSTEM_PROMPT

    image_data_url = _encode_image(image_path)
    client = OpenAI(api_key=api_key)

    last_error: Exception | None = None
    for attempt, delay in enumerate([0, 1, 2, 4]):
        if delay:
            time.sleep(delay)
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
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
