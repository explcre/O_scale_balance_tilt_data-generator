#!/usr/bin/env python3
"""Task generation script."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from core import OutputWriter
from src import TaskGenerator, TaskConfig


def main():
    parser = argparse.ArgumentParser(description="Generate scale balance tilt tasks")
    parser.add_argument("--num-samples", type=int, required=True)
    parser.add_argument("--output", type=str, default="data/questions")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--no-videos", action="store_true")
    
    args = parser.parse_args()
    
    print(f"🎲 Generating {args.num_samples} scale balance tasks...")
    
    config = TaskConfig(
        num_samples=args.num_samples,
        random_seed=args.seed,
        output_dir=Path(args.output),
        generate_videos=not args.no_videos,
    )
    
    generator = TaskGenerator(config)
    tasks = generator.generate_dataset()
    
    writer = OutputWriter(Path(args.output))
    writer.write_dataset(tasks)
    
    print(f"✅ Done! Generated {len(tasks)} tasks in {args.output}/{config.domain}_task/")


if __name__ == "__main__":
    main()
