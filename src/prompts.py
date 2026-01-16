"""Scale Balance Tilt Task Prompts - Clean version matching video exactly."""

def get_prompt(task_data: dict) -> str:
    """Generate prompt that exactly describes what happens in the video."""
    left_weights = task_data["left_weights"]
    right_weights = task_data["right_weights"]
    total_left = task_data["total_left"]
    total_right = task_data["total_right"]
    heavier_side = task_data["heavier_side"]
    
    left_str = " + ".join(str(w) for w in left_weights)
    right_str = " + ".join(str(w) for w in right_weights)
    
    prompt = f"""Balance scale with weights on both pans:
- LEFT: {left_str} = {total_left}
- RIGHT: {right_str} = {total_right}

The scale starts balanced. The heavier side tips DOWN.
The beam tilts until the lower pan reaches the base level (red dashed line appears).
The heavier pan is highlighted in red.

Answer: {heavier_side.upper()} side tips down ({total_left if heavier_side == "left" else total_right} > {total_right if heavier_side == "left" else total_left})."""

    return prompt


def get_all_prompts() -> list[str]:
    return ["Scale tilts until lower pan reaches base level, heavier pan highlighted red."]
