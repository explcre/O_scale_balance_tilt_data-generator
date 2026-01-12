"""
Scale Balance Tilt Task Generator.

Generates balance scale scenarios with labeled weights on both sides.
Task: Predict which side will tip down based on total weight.
"""

import random
import tempfile
import math
from pathlib import Path
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageFont

from core import BaseGenerator, TaskPair, ImageRenderer
from core.video_utils import VideoGenerator
from .config import TaskConfig
from .prompts import get_prompt


class TaskGenerator(BaseGenerator):
    """Scale balance tilt prediction task generator."""
    
    def __init__(self, config: TaskConfig):
        super().__init__(config)
        self.renderer = ImageRenderer(image_size=config.image_size)
        
        self.video_generator = None
        if config.generate_videos and VideoGenerator.is_available():
            self.video_generator = VideoGenerator(fps=config.video_fps, output_format="mp4")
    
    def generate_task_pair(self, task_id: str) -> TaskPair:
        """Generate one task pair."""
        task_data = self._generate_task_data()
        
        first_image = self._render_initial_state(task_data)
        final_image = self._render_final_state(task_data)
        
        video_path = None
        if self.config.generate_videos and self.video_generator:
            video_path = self._generate_video(first_image, final_image, task_id, task_data)
        
        prompt = get_prompt(task_data.get("type", "default"))
        
        return TaskPair(
            task_id=task_id,
            domain=self.config.domain,
            prompt=prompt,
            first_image=first_image,
            final_image=final_image,
            ground_truth_video=video_path
        )
    
    def _generate_task_data(self) -> dict:
        """Generate weights for both sides."""
        # Generate left side weights
        num_left = random.randint(self.config.min_objects, self.config.max_objects)
        left_weights = [random.randint(self.config.min_weight, self.config.max_weight) 
                       for _ in range(num_left)]
        
        # Generate right side weights
        num_right = random.randint(self.config.min_objects, self.config.max_objects)
        right_weights = [random.randint(self.config.min_weight, self.config.max_weight) 
                        for _ in range(num_right)]
        
        # Ensure they're not equal
        while sum(left_weights) == sum(right_weights):
            # Adjust one weight randomly
            if random.random() < 0.5 and left_weights:
                idx = random.randint(0, len(left_weights) - 1)
                left_weights[idx] = random.randint(self.config.min_weight, self.config.max_weight)
            elif right_weights:
                idx = random.randint(0, len(right_weights) - 1)
                right_weights[idx] = random.randint(self.config.min_weight, self.config.max_weight)
        
        total_left = sum(left_weights)
        total_right = sum(right_weights)
        
        # Determine heavier side
        heavier_side = "left" if total_left > total_right else "right"
        
        return {
            "left_weights": left_weights,
            "right_weights": right_weights,
            "total_left": total_left,
            "total_right": total_right,
            "heavier_side": heavier_side,
            "type": "default",
        }
    
    def _draw_weight_box(self, draw: ImageDraw.Draw, x: int, y: int, 
                         weight: int, color: tuple):
        """Draw a weight box with label."""
        # Box size proportional to weight
        base_size = 25
        size = base_size + weight * 2
        
        # Draw box
        draw.rectangle([x - size // 2, y - size, x + size // 2, y],
                      fill=color, outline=(0, 0, 0), width=2)
        
        # Draw weight label
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        except:
            font = ImageFont.load_default()
        
        text = str(weight)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        draw.text((x - text_width // 2, y - size // 2 - text_height // 2),
                 text, fill=(255, 255, 255), font=font)
        
        return size
    
    def _draw_scale(self, draw: ImageDraw.Draw, task_data: dict, 
                    tilt_angle: float = 0, highlight_heavy: bool = False):
        """Draw the balance scale."""
        width, height = self.config.image_size
        center_x = width // 2
        
        # Fulcrum position
        fulcrum_y = height - 100
        fulcrum_height = self.config.fulcrum_height
        
        # Draw fulcrum (triangle)
        fulcrum_width = 60
        draw.polygon([
            (center_x, fulcrum_y - fulcrum_height),  # Top
            (center_x - fulcrum_width // 2, fulcrum_y),  # Bottom left
            (center_x + fulcrum_width // 2, fulcrum_y),  # Bottom right
        ], fill=self.config.fulcrum_color)
        
        # Beam
        beam_length = self.config.beam_length
        beam_height = self.config.beam_height
        
        # Calculate beam endpoints with tilt
        pivot_y = fulcrum_y - fulcrum_height
        left_x = center_x - beam_length // 2
        right_x = center_x + beam_length // 2
        
        # Apply tilt
        tilt_offset = math.sin(math.radians(tilt_angle)) * beam_length // 2
        left_y = pivot_y + tilt_offset
        right_y = pivot_y - tilt_offset
        
        # Draw beam as rotated rectangle
        angle_rad = math.radians(tilt_angle)
        beam_points = [
            self._rotate_point(left_x, pivot_y - beam_height // 2, center_x, pivot_y, angle_rad),
            self._rotate_point(right_x, pivot_y - beam_height // 2, center_x, pivot_y, angle_rad),
            self._rotate_point(right_x, pivot_y + beam_height // 2, center_x, pivot_y, angle_rad),
            self._rotate_point(left_x, pivot_y + beam_height // 2, center_x, pivot_y, angle_rad),
        ]
        draw.polygon(beam_points, fill=self.config.beam_color)
        
        # Calculate pan positions
        pan_y_left = left_y + 30
        pan_y_right = right_y + 30
        
        # Draw pans
        pan_width = self.config.pan_width
        pan_height = 10
        
        # Left pan
        left_pan_color = self.config.heavy_side_color if (highlight_heavy and task_data["heavier_side"] == "left") else self.config.pan_color
        draw.rectangle([left_x - pan_width // 2, pan_y_left, 
                       left_x + pan_width // 2, pan_y_left + pan_height],
                      fill=left_pan_color, outline=(0, 0, 0), width=2)
        
        # Draw chains/strings
        draw.line([(left_x - pan_width // 3, pan_y_left), (left_x, left_y)], fill=(100, 100, 100), width=2)
        draw.line([(left_x + pan_width // 3, pan_y_left), (left_x, left_y)], fill=(100, 100, 100), width=2)
        
        # Right pan
        right_pan_color = self.config.heavy_side_color if (highlight_heavy and task_data["heavier_side"] == "right") else self.config.pan_color
        draw.rectangle([right_x - pan_width // 2, pan_y_right, 
                       right_x + pan_width // 2, pan_y_right + pan_height],
                      fill=right_pan_color, outline=(0, 0, 0), width=2)
        
        draw.line([(right_x - pan_width // 3, pan_y_right), (right_x, right_y)], fill=(100, 100, 100), width=2)
        draw.line([(right_x + pan_width // 3, pan_y_right), (right_x, right_y)], fill=(100, 100, 100), width=2)
        
        # Draw weights on pans
        left_weights = task_data["left_weights"]
        right_weights = task_data["right_weights"]
        
        # Left weights
        weight_spacing = pan_width // (len(left_weights) + 1) if left_weights else 0
        for i, w in enumerate(left_weights):
            wx = left_x - pan_width // 2 + weight_spacing * (i + 1)
            wy = pan_y_left
            self._draw_weight_box(draw, wx, wy, w, self.config.weight_color)
        
        # Right weights
        weight_spacing = pan_width // (len(right_weights) + 1) if right_weights else 0
        for i, w in enumerate(right_weights):
            wx = right_x - pan_width // 2 + weight_spacing * (i + 1)
            wy = pan_y_right
            self._draw_weight_box(draw, wx, wy, w, self.config.weight_color)
        
        # Draw totals
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        except:
            font = ImageFont.load_default()
        
        left_total = f"Total: {task_data['total_left']}"
        right_total = f"Total: {task_data['total_right']}"
        
        draw.text((left_x - 30, pan_y_left + 50), left_total, fill=(100, 100, 100), font=font)
        draw.text((right_x - 30, pan_y_right + 50), right_total, fill=(100, 100, 100), font=font)
    
    def _rotate_point(self, x: float, y: float, cx: float, cy: float, 
                      angle: float) -> Tuple[float, float]:
        """Rotate point around center."""
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        nx = cos_a * (x - cx) - sin_a * (y - cy) + cx
        ny = sin_a * (x - cx) + cos_a * (y - cy) + cy
        return (nx, ny)
    
    def _render_initial_state(self, task_data: dict) -> Image.Image:
        """Render balanced scale."""
        width, height = self.config.image_size
        img = Image.new('RGB', (width, height), self.config.bg_color)
        draw = ImageDraw.Draw(img)
        
        self._draw_scale(draw, task_data, tilt_angle=0, highlight_heavy=False)
        
        # Draw question
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        draw.text((width // 2 - 100, 30), "Which side tips down?", fill=(100, 100, 100), font=font)
        
        return img
    
    def _render_final_state(self, task_data: dict) -> Image.Image:
        """Render tilted scale with heavier side highlighted."""
        width, height = self.config.image_size
        img = Image.new('RGB', (width, height), self.config.bg_color)
        draw = ImageDraw.Draw(img)
        
        # Tilt towards heavier side
        tilt_angle = 15 if task_data["heavier_side"] == "left" else -15
        
        self._draw_scale(draw, task_data, tilt_angle=tilt_angle, highlight_heavy=True)
        
        # Draw answer
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        side = task_data["heavier_side"].upper()
        draw.text((width // 2 - 80, 30), f"{side} side tips down!", 
                 fill=self.config.heavy_side_color, font=font)
        
        return img
    
    def _generate_video(self, first_image: Image.Image, final_image: Image.Image,
                        task_id: str, task_data: dict) -> str:
        """Generate video showing scale tilting."""
        temp_dir = Path(tempfile.gettempdir()) / f"{self.config.domain}_videos"
        temp_dir.mkdir(parents=True, exist_ok=True)
        video_path = temp_dir / f"{task_id}_ground_truth.mp4"
        
        frames = []
        hold_frames = 5
        animation_frames = 20
        
        width, height = self.config.image_size
        final_angle = 15 if task_data["heavier_side"] == "left" else -15
        
        # Hold initial
        for _ in range(hold_frames):
            frames.append(first_image.copy())
        
        # Animate tilt
        for i in range(animation_frames):
            progress = i / (animation_frames - 1)
            # Ease out
            progress = 1 - (1 - progress) ** 2
            
            current_angle = final_angle * progress
            
            img = Image.new('RGB', (width, height), self.config.bg_color)
            draw = ImageDraw.Draw(img)
            
            self._draw_scale(draw, task_data, tilt_angle=current_angle, 
                           highlight_heavy=(progress > 0.8))
            
            frames.append(img)
        
        # Hold final
        for _ in range(hold_frames * 2):
            frames.append(final_image.copy())
        
        result = self.video_generator.create_video_from_frames(frames, video_path)
        return str(result) if result else None
