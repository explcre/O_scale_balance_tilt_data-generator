# O-75: Scale Balance Tilt Prediction Data Generator

## Task Description
Given a balance scale with labeled weights on both sides, predict which side will tip down based on total weight.

**Reasoning Type:** Physics/Weight - Weight comparison

## Visual Elements
- **Scale**: Balance beam on triangular fulcrum with base platform
- **Pans**: Left and right pans hanging from beam ends
- **Weights**: Labeled boxes (number = weight) on each pan
- **Sum Labels**: "Sum: N" below each pan
- **Stop Line**: Red dashed line at base level
- **Winner Highlight**: Red color on heavier pan

## Task Logic
- Sum weights on each side
- Heavier side tips DOWN
- Animation stops when lower pan reaches base level
- Correct physics: heavier side moves downward

## Output Format
```
data/questions/scale_balance_task/{task_id}/
├── first_frame.png      # Balanced scale with weights, "Which side tips DOWN?"
├── final_frame.png      # Tilted scale, winner highlighted red
├── prompt.txt           # Precise weights and calculation
└── ground_truth.mp4     # Tilting animation
```

## Animation Sequence
1. Scale starts balanced (beam horizontal)
2. Beam tilts so heavier side goes DOWN
3. Red dashed stop line appears at base level
4. Tilting stops when lower pan reaches base level
5. Heavier pan highlighted in red
6. Result message shows which side won

## Usage
```bash
python examples/generate.py --num-samples 100 --seed 42
```

## Configuration
Edit `src/config.py` to customize:
- `min_objects` / `max_objects`: Weights per side (default: 1-4)
- `min_weight` / `max_weight`: Weight values (default: 1-10)
- `beam_length`: Length of balance beam (default: 300px)
- `fulcrum_height`: Height of support triangle (default: 100px)

## Sample Prompt
```
A balance scale has weights on both sides:
- LEFT pan: 5 + 3 + 7 = 15
- RIGHT pan: 4 + 2 = 6

The scale starts balanced (beam horizontal). Calculate which side is heavier.
The heavier side will tip DOWN. The animation shows:
1. The beam tilts so the heavier side's pan moves downward
2. The tilting stops when the lower pan reaches the base level (shown as a red dashed line)
...
```
