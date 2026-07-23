from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import Settings


class AvatarImageError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class AvatarImageResult:
    image_bytes: bytes
    mime_type: str
    provider: str
    model: str
    prompt: str


class AvatarImageService:
    def __init__(
        self,
        *,
        provider: str,
        model: str,
        hf_token: str,
        timeout: float,
    ) -> None:
        self._provider = provider.strip()
        self._model = model.strip()
        self._hf_token = hf_token
        self._timeout = timeout

    @classmethod
    def from_settings(cls, settings: Settings) -> "AvatarImageService":
        return cls(
            provider=settings.avatar_image_provider,
            model=settings.avatar_image_model,
            hf_token=settings.hf_token,
            timeout=settings.ai_timeout_seconds,
        )

    def generate(
        self,
        *,
        style: str,
        customization: dict[str, Any],
        prompt: str | None,
    ) -> AvatarImageResult:
        if not self._provider:
            raise AvatarImageError(
                "provider_disabled",
                "La génération d'avatar IA n'est pas configurée.",
            )
        if not self._hf_token:
            raise AvatarImageError(
                "missing_token",
                "HF_TOKEN n'est pas configuré pour les avatars IA.",
            )
        if not self._model:
            raise AvatarImageError(
                "missing_model",
                "AVATAR_IMAGE_MODEL n'est pas configuré.",
            )

        final_prompt = _build_avatar_prompt(style, customization, prompt)
        model = quote(self._model, safe="")
        provider = quote(self._provider, safe="")
        response = httpx.post(
            f"https://router.huggingface.co/{provider}/models/{model}",
            headers={
                "Authorization": f"Bearer {self._hf_token}",
                "Accept": "image/png",
            },
            json={
                "inputs": final_prompt,
                "parameters": {
                    "width": 512,
                    "height": 512,
                    "num_inference_steps": 8,
                    "negative_prompt": (
                        "photo background, text, watermark, logo, scary, violent, "
                        "adult, realistic injury, low quality, blurry"
                    ),
                },
            },
            timeout=self._timeout,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise AvatarImageError(
                "provider_error",
                "La génération d'avatar IA est indisponible pour le moment.",
            ) from exc

        content_type = response.headers.get("content-type", "image/png").split(";")[0]
        if content_type not in {"image/png", "image/jpeg", "image/webp"}:
            raise AvatarImageError(
                "invalid_provider_response",
                "Le fournisseur IA n'a pas renvoyé une image valide.",
            )
        if not response.content:
            raise AvatarImageError(
                "empty_provider_response",
                "Le fournisseur IA a renvoyé une image vide.",
            )
        return AvatarImageResult(
            image_bytes=response.content,
            mime_type=content_type,
            provider=self._provider,
            model=self._model,
            prompt=final_prompt,
        )


def _build_avatar_prompt(
    style: str,
    customization: dict[str, Any],
    prompt: str | None,
) -> str:
    style_labels = {
        "friendly_school": "friendly school icon avatar",
        "realistic": "soft realistic student portrait avatar",
        "cartoon": "colorful cartoon student avatar",
    }
    safe_style = style_labels.get(style, "friendly school icon avatar")
    option_text = ", ".join(
        f"{key}: {value}"
        for key, value in customization.items()
        if value is not None and str(value).strip()
    )
    extra = f", {prompt.strip()}" if prompt and prompt.strip() else ""
    if option_text:
        extra = f", {option_text}{extra}"
    return (
        f"{safe_style}, child-safe education app profile picture, centered face, "
        f"clean vector-inspired composition, rounded friendly features, bright "
        f"balanced colors, simple background, no text, no watermark{extra}"
    )
