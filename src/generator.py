"""
Scale Balance Tilt Task Generator - Clean version.

Rotation: Left heavy = counter-clockwise (left down), Right heavy = clockwise (right down)
Stop: When lower pan reaches base level (red dashed line)
"""

import random
import tempfile
import math
from pathlib import Path
from typing import Tuple
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
        task_data = self._generate_task_data()
        
        first_image = self._render_initial_state(task_data)
        final_image = self._render_final_state(task_data)
        
        video_path = None
        if self.config.generate_videos and self.video_generator:
            video_path = self._generate_video(first_image, final_image, task_id, task_data)
        
        prompt = get_prompt(task_data)
        
        return TaskPair(
            task_id=task_id,
            domain=self.config.domain,
            prompt=prompt,
            first_image=first_image,
            final_image=final_image,
            ground_truth_video=video_path
        )
    
    def _generate_task_data(self) -> dict:
        num_left = random.randint(self.config.min_objects, self.config.max_objects)
        left_weights = [random.randint(self.config.min_weight, self.config.max_weight) 
                       for _ in range(num_left)]
        
        num_right = random.randint(self.config.min_objects, self.config.max_objects)
        right_weights = [random.randint(self.config.min_weight, self.config.max_weight) 
                        for _ in range(num_right)]
        
        while sum(left_weights) == sum(right_weights):
            if random.random() < 0.5 and left_weights:
                left_weights[random.randint(0, len(left_weights) - 1)] = random.randint(
                    self.config.min_weight, self.config.max_weight)
            elif right_weights:
                right_weights[random.randint(0, len(right_weights) - 1)] = random.randint(
                    self.config.min_weight, self.config.max_weight)
        
        total_left = sum(left_weights)
        total_right = sum(right_weights)
        heavier_side = "left" if total_left > total_right else "right"
        
        return {
            "left_weights": left_weights,
            "right_weights": right_weights,
            "total_left": total_left,
            "total_right": total_right,
            "heavier_side": heavier_side,
        }
    
    def _calculate_final_angle(self, heavier_side: str) -> float:
        """Calculate angle so lower pan reaches base level."""
        width, height = self.config.image_size
        base_bottom_y = height - 80
        pivot_y = base_bottom_y - self.config.fulcrum_height
        half_beam = self.config.beam_length // 2
        pan_drop = 40
        
        vertical_displacement = base_bottom_y - pivot_y - pan_drop
        sin_angle = min(0.9, vertical_displacement / half_beam)
        angle_deg = math.degrees(math.asin(sin_angle))
        
        # Left heavy = negative (counter-clockwise), Right heavy = positive (clockwise)
        return -angle_deg if heavier_side == "left" else angle_deg
    
    def _draw_weight_box(self, draw: ImageDraw.Draw, x: int, y: int, weight: int, color: tuple):
        base_size = 25
        size = base_size + weight * 2
        
        draw.rectangle([x - size // 2, y - size, x + size // 2, y],
                      fill=color, outline=(0, 0, 0), width=2)
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        except:
            font = ImageFont.load_default()
        
        text = str(weight)
        bbox = draw.textbbox((0, 0), text, font=font)
        draw.text((x - (bbox[2] - bbox[0]) // 2, y - size // 2 - (bbox[3] - bbox[1]) // 2),
                 text, fill=(255, 255, 255), font=font)
    
    def _rotate_point(self, x: float, y: float, cx: float, cy: float, angle: float) -> Tuple[float, float]:
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        return (cos_a * (x - cx) - sin_a * (y - cy) + cx,
                sin_a * (x - cx) + cos_a * (y - cy) + cy)
    
    def _draw_scale(self, draw: ImageDraw.Draw, task_data: dict, tilt_angle: float = 0,
                    highlight_heavy: bool = False, show_stop_line: bool = False):
        width, height = self.config.image_size
        center_x = width // 2
        base_bottom_y = height - 80
        pivot_y = base_bottom_y - self.config.fulcrum_height
        
        # Draw base
        fulcrum_width = 60
        draw.polygon([(center_x, pivot_y), 
                     (center_x - fulcrum_width // 2, base_bottom_y),
                     (center_x + fulcrum_width // 2, base_bottom_y)], 
                    fill=self.config.fulcrum_color)
        draw.rectangle([center_x - 80, base_bottom_y, center_x + 80, base_bottom_y + 10],
                      fill=self.config.fulcrum_color)
        
        # Stop line
        if show_stop_line:
            for i in range(0, 240, 20):
                draw.line([(center_x - 120 + i, base_bottom_y), 
                          (center_x - 110 + i, base_bottom_y)],
                         fill=(255, 100, 100), width=3)
        
        # Beam
        angle_rad = math.radians(tilt_angle)
        half_beam = self.config.beam_length // 2
        beam_height = self.config.beam_height
        
        left_x = center_x - half_beam * math.cos(angle_rad)
        left_y = pivot_y - half_beam * math.sin(angle_rad)
        right_x = center_x + half_beam * math.cos(angle_rad)
        right_y = pivot_y + half_beam * math.sin(angle_rad)
        
        beam_points = [
            self._rotate_point(center_x - half_beam, pivot_y - beam_height // 2, center_x, pivot_y, angle_rad),
            self._rotate_point(center_x + half_beam, pivot_y - beam_height // 2, center_x, pivot_y, angle_rad),
            self._rotate_point(center_x + half_beam, pivot_y + beam_height // 2, center_x, pivot_y, angle_rad),
            self._rotate_point(center_x - half_beam, pivot_y + beam_height // 2, center_x, pivot_y, angle_rad),
        ]
        draw.polygon(beam_points, fill=self.config.beam_color)
        
        # Pans
        pan_drop = 40
        pan_width = self.config.pan_width
        pan_height = 10
        
        left_pan_x, left_pan_y = int(left_x), int(left_y) + pan_drop
        right_pan_x, right_pan_y = int(right_x), int(right_y) + pan_drop
        
        # Chains
        for px, py, bx, by in [(left_pan_x, left_pan_y, left_x, left_y),
                               (right_pan_x, right_pan_y, right_x, right_y)]:
            draw.line([(px - pan_width // 3, py), (int(bx), int(by))], fill=(100, 100, 100), width=2)
            draw.line([(px + pan_width // 3, py), (int(bx), int(by))], fill=(100, 100, 100), width=2)
        
        # Pan colors
        left_color = self.config.heavy_side_color if highlight_heavy and task_data["heavier_side"] == "left" else self.config.pan_color
        right_color = self.config.heavy_side_color if highlight_heavy and task_data["heavier_side"] == "right" else self.config.pan_color
        
        draw.rectangle([left_pan_x - pan_width // 2, left_pan_y, 
                       left_pan_x + pan_width // 2, left_pan_y + pan_height],
                      fill=left_color, outline=(0, 0, 0), width=2)
        draw.rectangle([right_pan_x - pan_width // 2, right_pan_y,
                       right_pan_x + pan_width // 2, right_pan_y + pan_height],
                      fill=right_color, outline=(0, 0, 0), width=2)
        
        # Weights
        for weights, pan_x, pan_y in [(task_data["left_weights"], left_pan_x, left_pan_y),
                                       (task_data["right_weights"], right_pan_x, right_pan_y)]:
            if weights:
                spacing = pan_width // (len(weights) + 1)
                for i, w in enumerate(weights):
                    wx = pan_x - pan_width // 2 + spacing * (i + 1)
                    self._draw_weight_box(draw, wx, pan_y, w, self.config.weight_color)
        
        # Labels
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except:
            font = ImageFont.load_default()
        
        draw.text((left_pan_x - 20, pivot_y - 50), "LEFT", fill=(80, 80, 80), font=font)
        draw.text((right_pan_x - 25, pivot_y - 50), "RIGHT", fill=(80, 80, 80), font=font)
        draw.text((left_pan_x - 25, left_pan_y + pan_height + 15), 
                 f"Sum: {task_data['total_left']}", fill=(100, 100, 100), font=font)
        draw.text((right_pan_x - 25, right_pan_y + pan_height + 15),
                 f"Sum: {task_data['total_right']}", fill=(100, 100, 100), font=font)
    
    def _render_initial_state(self, task_data: dict) -> Image.Image:
        width, height = self.config.image_size
        img = Image.new('RGB', (width, height), self.config.bg_color)
        draw = ImageDraw.Draw(img)
        self._draw_scale(draw, task_data, tilt_angle=0)
        return img
    
    def _render_final_state(self, task_data: dict) -> Image.Image:
        width, height = self.config.image_size
        img = Image.new('RGB', (width, height), self.config.bg_color)
        draw = ImageDraw.Draw(img)
        final_angle = self._calculate_final_angle(task_data["heavier_side"])
        self._draw_scale(draw, task_data, tilt_angle=final_angle, 
                        highlight_heavy=True, show_stop_line=True)
        return img
    
    def _generate_video(self, first_image: Image.Image, final_image: Image.Image,
                        task_id: str, task_data: dict) -> str:
        temp_dir = Path(tempfile.gettempdir()) / f"{self.config.domain}_videos"
        temp_dir.mkdir(parents=True, exist_ok=True)
        video_path = temp_dir / f"{task_id}_ground_truth.mp4"
        
        frames = []
        hold_frames = 8
        animation_frames = 25
        
        width, height = self.config.image_size
        final_angle = self._calculate_final_angle(task_data["heavier_side"])
        
        for _ in range(hold_frames):
            frames.append(first_image.copy())
        
        for i in range(animation_frames):
            progress = i / (animation_frames - 1)
            progress = 1 - (1 - progress) ** 3  # Ease out
            
            current_angle = final_angle * progress
            show_line = progress > 0.7
            highlight = progress > 0.8
            
            img = Image.new('RGB', (width, height), self.config.bg_color)
            draw = ImageDraw.Draw(img)
            self._draw_scale(draw, task_data, tilt_angle=current_angle,
                           highlight_heavy=highlight, show_stop_line=show_line)
            frames.append(img)
        
        for _ in range(hold_frames * 2):
            frames.append(final_image.copy())
        
        result = self.video_generator.create_video_from_frames(frames, video_path)
        return str(result) if result else None
