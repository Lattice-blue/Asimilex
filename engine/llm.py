"""
LLM abstraction layer.
Keeps AI model providers (Gemini, Claude, local models) swappable.
"""

def call_llm(prompt: str, system: str = "") -> str:
    """Sends a context snapshot to the AI and returns proposals."""
    raise NotImplementedError("LLM provider not configured yet.")