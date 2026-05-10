from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPlan:
    profile: str
    status: str
    chat_model: str
    autocomplete_model: str
    chat_label: str = "Pro AI Chat"
    autocomplete_label: str = "Pro AI Autocomplete"

    @property
    def ollama_pull_commands(self) -> tuple[str, ...]:
        seen: set[str] = set()
        commands: list[str] = []
        for model in (self.chat_model, self.autocomplete_model):
            if model not in seen:
                seen.add(model)
                commands.append(f"ollama pull {model}")
        return tuple(commands)


MODEL_PLANS: dict[str, ModelPlan] = {
    "lightweight": ModelPlan(
        profile="lightweight",
        status="experimental",
        chat_model="qwen2.5-coder:1.5b",
        autocomplete_model="qwen2.5-coder:0.5b",
    ),
    "professional": ModelPlan(
        profile="professional",
        status="recommended",
        chat_model="qwen2.5-coder:3b",
        autocomplete_model="qwen2.5-coder:1.5b-base",
    ),
    "max": ModelPlan(
        profile="max",
        status="high-memory",
        chat_model="qwen2.5-coder:7b",
        autocomplete_model="qwen2.5-coder:1.5b-base",
    ),
}


def model_plan_for_profile(profile: str) -> ModelPlan:
    normalized = profile.strip().lower()
    try:
        return MODEL_PLANS[normalized]
    except KeyError as exc:
        valid_profiles = ", ".join(MODEL_PLANS)
        raise ValueError(f"Unknown model profile '{profile}'. Expected one of: {valid_profiles}.") from exc


def model_plan_for_ram(ram_gb: float) -> ModelPlan:
    if ram_gb < 5:
        return MODEL_PLANS["lightweight"]
    if ram_gb < 9:
        return MODEL_PLANS["professional"]
    return MODEL_PLANS["max"]
