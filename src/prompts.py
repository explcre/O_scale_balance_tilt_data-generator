"""Scale Balance Tilt Task Prompts - Precise version."""

def get_prompt(task_data: dict) -> str:
    """Generate a precise prompt that uniquely determines the video output.
    
    The prompt specifies:
    - The weights on each side
    - That the heavier side tips DOWN
    - The stopping condition (lower pan reaches base level - red dashed line)
    - The highlighting of the heavier side
    """
    left_weights = task_data["left_weights"]
    right_weights = task_data["right_weights"]
    total_left = task_data["total_left"]
    total_right = task_data["total_right"]
    heavier_side = task_data["heavier_side"]
    
    left_str = " + ".join(str(w) for w in left_weights)
    right_str = " + ".join(str(w) for w in right_weights)
    
    prompt = f"""A balance scale has weights on both sides:
- LEFT pan: {left_str} = {total_left}
- RIGHT pan: {right_str} = {total_right}

The scale starts balanced (beam horizontal). Calculate which side is heavier.
The heavier side will tip DOWN. The animation shows:
1. The beam tilts so the heavier side's pan moves downward
2. The tilting stops when the lower pan reaches the base level (shown as a red dashed line)
3. The heavier side's pan is highlighted in red

Which side tips down? Show the tilting animation until the stopping condition is met."""

    return prompt


def get_all_prompts() -> list[str]:
    """Return example prompts."""
    return [
        "Balance scale with labeled weights. Heavier side tips DOWN until lower pan reaches base level (red dashed line)."
    ]
