"""Scale Balance Tilt Task Prompts."""

import random

PROMPTS = {
    "default": [
        "Compare the total weights on each side of the scale. Which side will tip down?",
        "Add up the weights on each pan. Show which side is heavier by tilting the scale.",
        "Calculate which side has more total weight and animate the scale tipping accordingly.",
    ],
}

def get_prompt(task_type: str = "default") -> str:
    prompts = PROMPTS.get(task_type, PROMPTS["default"])
    return random.choice(prompts)

def get_all_prompts(task_type: str = "default") -> list[str]:
    return PROMPTS.get(task_type, PROMPTS["default"])
