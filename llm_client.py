"""
Unified LLM Client for COHA.

Provides a single interface for both Anthropic (claude-*) and HuggingFace
(e.g. LGAI-EXAONE/EXAONE-4.0-1.2B-Instruct) models.

Backend selection is automatic:
  - model name starts with "claude" → Anthropic backend
  - anything else                  → HuggingFace / transformers backend

All imports of heavy dependencies (anthropic, transformers, torch) are
deferred inside methods so that this module is importable without either
library installed.
"""

import os
import time
import logging

logger = logging.getLogger(__name__)


class UnifiedLLMClient:
    """
    Unified LLM client supporting Anthropic and HuggingFace backends.

    Usage:
        client = UnifiedLLMClient()                  # uses config.MODEL_NAME
        client = UnifiedLLMClient("claude-sonnet-4-6")
        client = UnifiedLLMClient("LGAI-EXAONE/EXAONE-4.0-1.2B-Instruct")

        text = client.generate(system="You are helpful.", user="Hello!")
    """

    def __init__(self, model_name: str = None):
        """
        Initialize the unified LLM client.

        Args:
            model_name: Model identifier.  If None, reads from config.MODEL_NAME.
                        Models starting with "claude" use the Anthropic backend;
                        all others use the HuggingFace transformers backend.
        """
        if model_name is None:
            try:
                import config as _cfg
                model_name = _cfg.MODEL_NAME
            except Exception:
                model_name = "LGAI-EXAONE/EXAONE-4.0-1.2B-Instruct"

        self.model_name = model_name

        if model_name.startswith("claude"):
            self.backend = "anthropic"
        else:
            self.backend = "huggingface"

        # Lazy-initialised backend objects
        self._anthropic_client = None
        self._hf_pipe = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def generate(
        self,
        system: str,
        user: str,
        max_tokens: int = 1024,
    ) -> str:
        """
        Generate a response from the LLM.

        Args:
            system: System prompt (may be empty string or None).
            user:   User message.
            max_tokens: Maximum tokens to generate.

        Returns:
            Generated text as a plain string.
        """
        if self.backend == "anthropic":
            return self._generate_anthropic(system, user, max_tokens)
        else:
            return self._generate_huggingface(system, user, max_tokens)

    # ------------------------------------------------------------------
    # Anthropic backend
    # ------------------------------------------------------------------

    def _init_anthropic(self):
        """Lazily initialise the Anthropic client."""
        if self._anthropic_client is None:
            import anthropic as _anthropic
            self._anthropic_client = _anthropic.Anthropic(
                api_key=os.environ.get("ANTHROPIC_API_KEY")
            )

    def _generate_anthropic(
        self,
        system: str,
        user: str,
        max_tokens: int,
    ) -> str:
        """Call the Anthropic messages API with retry logic."""
        self._init_anthropic()
        import anthropic as _anthropic

        max_retries = 3
        for attempt in range(max_retries):
            try:
                kwargs = dict(
                    model=self.model_name,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": user}],
                )
                if system:
                    kwargs["system"] = system

                resp = self._anthropic_client.messages.create(**kwargs)
                return resp.content[0].text.strip()

            except _anthropic.APIError as exc:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError(
                    f"Anthropic LLM call failed after {max_retries} attempts: {exc}"
                ) from exc

    # ------------------------------------------------------------------
    # HuggingFace backend
    # ------------------------------------------------------------------

    def _init_huggingface(self):
        """Lazily initialise the transformers pipeline."""
        if self._hf_pipe is None:
            from transformers import pipeline
            import torch  # noqa: F401 — validates torch is present

            logger.info(
                f"UnifiedLLMClient: Loading HuggingFace model '{self.model_name}'…"
            )
            self._hf_pipe = pipeline(
                "text-generation",
                model=self.model_name,
                device_map="auto",
                torch_dtype="auto",
                trust_remote_code=True,
            )
            logger.info("UnifiedLLMClient: HuggingFace pipeline ready.")

    def _generate_huggingface(
        self,
        system: str,
        user: str,
        max_tokens: int,
    ) -> str:
        """Call the HuggingFace pipeline with retry logic."""
        self._init_huggingface()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})

        max_retries = 3
        for attempt in range(max_retries):
            try:
                outputs = self._hf_pipe(
                    messages,
                    max_new_tokens=max_tokens,
                    do_sample=False,
                    return_full_text=False,
                )
                result = outputs[0]["generated_text"]
                # transformers >= 4.43 returns a list of message dicts when
                # the input was also a list of dicts (chat format).
                # Extract the last assistant message content in that case.
                if isinstance(result, list):
                    for msg in reversed(result):
                        if isinstance(msg, dict) and msg.get("role") == "assistant":
                            return msg.get("content", "").strip()
                    return ""
                return str(result).strip()

            except Exception as exc:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError(
                    f"HuggingFace LLM call failed after {max_retries} attempts: {exc}"
                ) from exc


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------

def get_client(model_name: str = None) -> UnifiedLLMClient:
    """
    Return a UnifiedLLMClient instance.

    Args:
        model_name: Optional model override.  Defaults to config.MODEL_NAME.

    Returns:
        UnifiedLLMClient instance.
    """
    return UnifiedLLMClient(model_name=model_name)
