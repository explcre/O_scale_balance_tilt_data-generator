"""
Scale Balance Tilt Task Generator.

Generates balance scale scenarios with labeled weights on both sides.
Task: Predict which side will tip down based on total weight.

ROTATION DIRECTION FIX:
- When LEFT side is heavier: beam rotates COUNTER-CLOCKWISE (left pan goes down)
- When RIGHT side is heavier: beam rotates CLOCKWISE (right pan goes down)

STOPPING CONDITION:
- The lower pan stops exactly at the same horizontal level as the bottom of the base
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
            if random.random() < 0.5 and left_weights:
                idx = random.randint(0, len(left_weights) - 1)
                left_weights[idx] = random.randint(self.config.min_weight, self.config.max_weight)
            elif right_weights:
                idx = random.randint(0, len(right_weights) - 1)
                right_weights[idx] = random.randint(self.config.min_weight, self.config.max_weight)
        
        total_left = sum(left_weights)
        total_right = sum(right_weights)
        
        # Determine heavier side - this side goes DOWN
        heavier_side = "left" if total_left > total_right else "right"
        
        return {
            "left_weights": left_weights,
            "right_weights": right_weights,
            "total_left": total_left,
            "total_right": total_right,
            "heavier_side": heavier_side,
        }
    
    def _draw_weight_box(self, draw: ImageDraw.Draw, x: int, y: int, 
                         weight: int, color: tuple):
        """Draw a weight box with label."""
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
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        draw.text((x - text_width // 2, y - size // 2 - text_height // 2),
                 text, fill=(255, 255, 255), font=font)
        
        return size
    
    def _calculate_final_angle(self, heavier_side: str) -> float:
        """Calculate the exact angle so lower pan reaches base level.
        
        Geometry:
        - Beam pivots at pivot_y
        - Pan hangs pan_drop below beam end
        - We want the lower pan to reach base_bottom_y
        
        For left heavy (counter-clockwise rotation, negative angle in standard math):
        - Left beam end goes DOWN, right goes UP
        - We need: pivot_y + half_beam * sin(angle) + pan_drop = base_bottom_y
        
        Solving: sin(angle) = (base_bottom_y - pivot_y - pan_drop) / half_beam
        """
        width, height = self.config.image_size
        
        base_bottom_y = height - 80
        fulcrum_height = self.config.fulcrum_height
        pivot_y = base_bottom_y - fulcrum_height
        
        beam_length = self.config.beam_length
        half_beam = beam_length // 2
        pan_drop = 40
        
        # Distance the lower pan needs to travel down from its balanced position
        # In balanced state, pan is at: pivot_y + pan_drop
        # Target: base_bottom_y
        # Vertical displacement needed = base_bottom_y - (pivot_y + pan_drop)
        vertical_displacement = base_bottom_y - pivot_y - pan_drop
        
        # sin(angle) = vertical_displacement / half_beam
        # But we need to cap it to avoid impossible angles
        sin_angle = min(0.95, vertical_displacement / half_beam)
        angle_rad = math.asin(sin_angle)
        angle_deg = math.degrees(angle_rad)
        
        # Return the angle - direction depends on which side is heavy
        # REVERSED: Left heavy = NEGATIVE angle (counter-clockwise)
        #           Right heavy = POSITIVE angle (clockwise)
        if heavier_side == "left":
            return -angle_deg  # Counter-clockwise (left goes down)
        else:
            return angle_deg   # Clockwise (right goes down)
    
    def _draw_scale(self, draw: ImageDraw.Draw, task_data: dict, 
                    tilt_angle: float = 0, highlight_heavy: bool = False,
                    show_stop_line: bool = False):
        """Draw the balance scale.
        
        ROTATION CONVENTION (REVERSED):
        - Negative angle = counter-clockwise = LEFT side goes DOWN
        - Positive angle = clockwise = RIGHT side goes DOWN
        """
        width, height = self.config.image_size
        center_x = width // 2
        
        # Base/fulcrum position
        base_bottom_y = height - 80  # Bottom of the triangular base
        fulcrum_height = self.config.fulcrum_height
        pivot_y = base_bottom_y - fulcrum_height  # Top of fulcrum where beam pivots
        
        # Draw base (triangle)
        fulcrum_width = 60
        draw.polygon([
            (center_x, pivot_y),  # Top (pivot point)
            (center_x - fulcrum_width // 2, base_bottom_y),  # Bottom left
            (center_x + fulcrum_width // 2, base_bottom_y),  # Bottom right
        ], fill=self.config.fulcrum_color)
        
        # Draw base platform
        draw.rectangle([center_x - 80, base_bottom_y, center_x + 80, base_bottom_y + 10],
                      fill=self.config.fulcrum_color)
        
        # Draw stop line indicator if requested (red dashed line at base level)
        if show_stop_line:
            for i in range(0, 240, 20):
                draw.line([(center_x - 120 + i, base_bottom_y), 
                          (center_x - 110 + i, base_bottom_y)],
                         fill=(255, 100, 100), width=3)
        
        # Beam calculations
        beam_length = self.config.beam_length
        beam_height = self.config.beam_height
        
        # Convert angle to radians
        # Negative = counter-clockwise, Positive = clockwise
        angle_rad = math.radians(tilt_angle)
        
        # Calculate beam endpoints
        # Standard rotation: 
        # - cos gives horizontal component
        # - sin gives vertical component (positive sin with positive angle = right side up)
        half_beam = beam_length // 2
        
        # Left end of beam
        left_x = center_x - half_beam * math.cos(angle_rad)
        left_y = pivot_y - half_beam * math.sin(angle_rad)  # Negative angle -> positive sin component -> left goes down
        
        # Right end of beam
        right_x = center_x + half_beam * math.cos(angle_rad)
        right_y = pivot_y + half_beam * math.sin(angle_rad)  # Negative angle -> negative sin component -> right goes up
        
        # Draw beam
        beam_points = [
            self._rotate_point(center_x - half_beam, pivot_y - beam_height // 2, center_x, pivot_y, angle_rad),
            self._rotate_point(center_x + half_beam, pivot_y - beam_height // 2, center_x, pivot_y, angle_rad),
            self._rotate_point(center_x + half_beam, pivot_y + beam_height // 2, center_x, pivot_y, angle_rad),
            self._rotate_point(center_x - half_beam, pivot_y + beam_height // 2, center_x, pivot_y, angle_rad),
        ]
        draw.polygon(beam_points, fill=self.config.beam_color)
        
        # Pan positions (hanging below beam ends)
        pan_drop = 40  # How far pans hang below beam
        pan_width = self.config.pan_width
        pan_height = 10
        
        # Left pan position
        left_pan_x = int(left_x)
        left_pan_y = int(left_y) + pan_drop
        
        # Right pan position  
        right_pan_x = int(right_x)
        right_pan_y = int(right_y) + pan_drop
        
        # Draw strings/chains
        draw.line([(left_pan_x - pan_width // 3, left_pan_y), (int(left_x), int(left_y))], 
                 fill=(100, 100, 100), width=2)
        draw.line([(left_pan_x + pan_width // 3, left_pan_y), (int(left_x), int(left_y))], 
                 fill=(100, 100, 100), width=2)
        draw.line([(right_pan_x - pan_width // 3, right_pan_y), (int(right_x), int(right_y))], 
                 fill=(100, 100, 100), width=2)
        draw.line([(right_pan_x + pan_width // 3, right_pan_y), (int(right_x), int(right_y))], 
                 fill=(100, 100, 100), width=2)
        
        # Draw pans
        left_pan_color = self.config.heavy_side_color if (highlight_heavy and task_data["heavier_side"] == "left") else self.config.pan_color
        right_pan_color = self.config.heavy_side_color if (highlight_heavy and task_data["heavier_side"] == "right") else self.config.pan_color
        
        draw.rectangle([left_pan_x - pan_width // 2, left_pan_y, 
                       left_pan_x + pan_width // 2, left_pan_y + pan_height],
                      fill=left_pan_color, outline=(0, 0, 0), width=2)
        draw.rectangle([right_pan_x - pan_width // 2, right_pan_y, 
                       right_pan_x + pan_width // 2, right_pan_y + pan_height],
                      fill=right_pan_color, outline=(0, 0, 0), width=2)
        
        # Draw weights on pans
        left_weights = task_data["left_weights"]
        right_weights = task_data["right_weights"]
        
        # Left weights
        if left_weights:
            weight_spacing = pan_width // (len(left_weights) + 1)
            for i, w in enumerate(left_weights):
                wx = left_pan_x - pan_width // 2 + weight_spacing * (i + 1)
                wy = left_pan_y
                self._draw_weight_box(draw, wx, wy, w, self.config.weight_color)
        
        # Right weights
        if right_weights:
            weight_spacing = pan_width // (len(right_weights) + 1)
            for i, w in enumerate(right_weights):
                wx = right_pan_x - pan_width // 2 + weight_spacing * (i + 1)
                wy = right_pan_y
                self._draw_weight_box(draw, wx, wy, w, self.config.weight_color)
        
        # Draw totals below pans
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except:
            font = ImageFont.load_default()
        
        left_total = f"Sum: {task_data['total_left']}"
        right_total = f"Sum: {task_data['total_right']}"
        
        # Position totals relative to pan positions
        draw.text((left_pan_x - 25, left_pan_y + pan_height + 20), left_total, 
                 fill=(100, 100, 100), font=font)
        draw.text((right_pan_x - 25, right_pan_y + pan_height + 20), right_total, 
                 fill=(100, 100, 100), font=font)
        
        # Labels above beam
        draw.text((left_pan_x - 20, pivot_y - 50), "LEFT", fill=(80, 80, 80), font=font)
        draw.text((right_pan_x - 25, pivot_y - 50), "RIGHT", fill=(80, 80, 80), font=font)
        
        return base_bottom_y, left_pan_y, right_pan_y
    
    def _rotate_point(self, x: float, y: float, cx: float, cy: float, 
                      angle: float) -> Tuple[float, float]:
        """Rotate point around center. Standard math convention."""
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        # Standard rotation matrix
        nx = cos_a * (x - cx) - sin_a * (y - cy) + cx
        ny = sin_a * (x - cx) + cos_a * (y - cy) + cy
        return (nx, ny)
    
    def _render_initial_state(self, task_data: dict) -> Image.Image:
        """Render balanced scale (horizontal beam)."""
        width, height = self.config.image_size
        img = Image.new('RGB', (width, height), self.config.bg_color)
        draw = ImageDraw.Draw(img)
        
        self._draw_scale(draw, task_data, tilt_angle=0, highlight_heavy=False)
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        except:
            font = ImageFont.load_default()
        
        # Title
        draw.text((width // 2 - 80, 20), "Which side tips DOWN?", fill=(80, 80, 80), font=font)
        
        return img
    
    def _render_final_state(self, task_data: dict) -> Image.Image:
        """Render tilted scale with heavier side DOWN, stopped at base level."""
        width, height = self.config.image_size
        img = Image.new('RGB', (width, height), self.config.bg_color)
        draw = ImageDraw.Draw(img)
        
        # Calculate the exact angle so lower pan reaches base level
        final_angle = self._calculate_final_angle(task_data["heavier_side"])
        
        self._draw_scale(draw, task_data, tilt_angle=final_angle, 
                        highlight_heavy=True, show_stop_line=True)
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        except:
            font = ImageFont.load_default()
        
        side = task_data["heavier_side"].upper()
        draw.text((width // 2 - 100, 20), f"{side} side tips DOWN!", 
                 fill=self.config.heavy_side_color, font=font)
        
        # Explanation
        try:
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except:
            small_font = font
        draw.text((width // 2 - 140, height - 40), 
                 "(Stopped: lower pan reached base level - red dashed line)", 
                 fill=(150, 150, 150), font=small_font)
        
        return img
    
    def _generate_video(self, first_image: Image.Image, final_image: Image.Image,
                        task_id: str, task_data: dict) -> str:
        """Generate video showing scale tilting until lower pan reaches base level."""
        temp_dir = Path(tempfile.gettempdir()) / f"{self.config.domain}_videos"
        temp_dir.mkdir(parents=True, exist_ok=True)
        video_path = temp_dir / f"{task_id}_ground_truth.mp4"
        
        frames = []
        hold_frames = 8
        animation_frames = 25
        
        width, height = self.config.image_size
        
        # Calculate the exact final angle
        final_angle = self._calculate_final_angle(task_data["heavier_side"])
        
        # Hold initial (balanced)
        for _ in range(hold_frames):
            frames.append(first_image.copy())
        
        # Animate tilt with easing
        for i in range(animation_frames):
            progress = i / (animation_frames - 1)
            # Ease out cubic for realistic physics feel
            progress = 1 - (1 - progress) ** 3
            
            current_angle = final_angle * progress
            
            img = Image.new('RGB', (width, height), self.config.bg_color)
            draw = ImageDraw.Draw(img)
            
            # Show stop line during animation
            show_line = progress > 0.7
            self._draw_scale(draw, task_data, tilt_angle=current_angle, 
                           highlight_heavy=(progress > 0.8), show_stop_line=show_line)
            
            frames.append(img)
        
        # Hold final
        for _ in range(hold_frames * 2):
            frames.append(final_image.copy())
        
        result = self.video_generator.create_video_from_frames(frames, video_path)
        return str(result) if result else None
