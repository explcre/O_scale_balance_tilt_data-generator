"""Scale Balance Tilt Task Prompts - Ultra-detailed version."""

def get_prompt(task_data: dict) -> str:
    """Generate extremely detailed prompt describing every visual element and animation."""
    left_weights = task_data["left_weights"]
    right_weights = task_data["right_weights"]
    total_left = task_data["total_left"]
    total_right = task_data["total_right"]
    heavier_side = task_data["heavier_side"]
    
    left_str = " + ".join(str(w) for w in left_weights)
    right_str = " + ".join(str(w) for w in right_weights)
    
    # Determine which side goes up/down
    if heavier_side == "left":
        down_side = "left"
        up_side = "right"
        down_sum = total_left
        up_sum = total_right
    else:
        down_side = "right"
        up_side = "left"
        down_sum = total_right
        up_sum = total_left
    
    prompt = f"""INITIAL STATE:
A balance scale with a brown horizontal beam balanced on a gray triangular fulcrum.
Two gray pans hang from chains at the beam's ends.

WEIGHTS ON PANS:
- Left pan: boxes labeled {left_str}
- Right pan: boxes labeled {right_str}

TEXT LABELS (present throughout entire video):
- Below left pan: "Sum: {total_left}" in gray text
- Below right pan: "Sum: {total_right}" in gray text
These "Sum: N" labels are attached to their respective pans and MOVE WITH THE PANS during tilting.

ANIMATION SEQUENCE:
1. Initial frame: beam is perfectly horizontal, both pans at equal height
2. Beam begins to tilt because left pan has total weight {total_left} and right pan has total weight {total_right}
3. The {down_side} pan (heavier, weight={down_sum}) moves DOWNWARD
4. The {up_side} pan (lighter, weight={up_sum}) moves UPWARD
5. As pans move, the "Sum: {total_left}" text moves down/up with left pan, "Sum: {total_right}" text moves down/up with right pan
6. When tilting reaches approximately 70% progress, a RED DASHED horizontal line appears at the base platform level
7. Tilting continues until the lower ({down_side}) pan reaches the red dashed line level
8. At approximately 80% tilting progress, the {down_side} pan changes color from gray to RED
9. Final state: beam is tilted, {down_side} pan is at base level (touching red line), {down_side} pan is colored red, red dashed line is visible

PHYSICAL REASONING:
The {down_side} side tips DOWN because {down_sum} > {up_sum}.
The heavier side goes down, lighter side goes up.

ANSWER: The {down_side} pan tips down and is highlighted in red at the end."""

    return prompt


def get_all_prompts() -> list[str]:
    return ["Scale tilts with heavier pan moving down. Sum labels move with pans. Red dashed line appears. Heavier pan turns red."]
