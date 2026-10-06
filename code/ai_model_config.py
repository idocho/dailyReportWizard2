"""Engine model settings shared by UI, probes and generation."""
from copy import deepcopy
import re
from constants import GEMINI_MODEL, OPENAI_MODEL

DEFAULTS = {
    "gemini": {"model": GEMINI_MODEL, "thinking_level": "low"},
    "claude": {"model": "claude-sonnet-5", "thinking_level": "disabled"},
    "openai": {"model": OPENAI_MODEL, "thinking_level": "none"},
}
OPTIONS = {
    "gemini": ("omit", "minimal", "low", "medium", "high"),
    "claude": ("omit", "disabled", "adaptive"),
    "openai": ("omit", "none", "minimal", "low", "medium", "high", "xhigh"),
}

def resolve(engine, settings=None):
    if engine not in DEFAULTS:
        raise ValueError("지원하지 않는 엔진")
    result = dict(DEFAULTS[engine])
    if settings is not None:
        if not isinstance(settings, dict):
            raise ValueError("모델 설정은 객체여야 합니다")
        result.update({k: settings[k] for k in result if k in settings})
    model = result["model"]
    if not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,159}", model):
        raise ValueError("정확한 모델 ID를 입력하세요 (URL·공백 사용 불가)")
    if result["thinking_level"] not in OPTIONS[engine]:
        raise ValueError("지원하지 않는 사고 옵션")
    return result

def from_config(cfg, engine):
    models = cfg.get("ai_models", {})
    if not isinstance(models, dict):
        raise ValueError("ai_models 설정은 객체여야 합니다")
    return resolve(engine, deepcopy(models.get(engine)))
