"""
Scale Balance Tilt Task Configuration.
"""

from pydantic import Field
from core import GenerationConfig


class TaskConfig(GenerationConfig):
    """
    Scale Balance Tilt task configuration.
    
    Task: Given a balance scale with weighted objects on both sides,
    predict which side will tip down.
    """
    
    domain: str = Field(default="scale_balance")
    image_size: tuple[int, int] = Field(default=(512, 512))
    
    generate_videos: bool = Field(default=True)
    video_fps: int = Field(default=10)
    
    # Weight settings
    min_objects: int = Field(default=1, description="Minimum objects per side")
    max_objects: int = Field(default=4, description="Maximum objects per side")
    min_weight: int = Field(default=1, description="Minimum weight per object")
    max_weight: int = Field(default=10, description="Maximum weight per object")
    
    # Scale settings
    beam_length: int = Field(default=300, description="Length of balance beam")
    beam_height: int = Field(default=8, description="Height of balance beam")
    fulcrum_height: int = Field(default=100, description="Height of fulcrum triangle")
    pan_width: int = Field(default=100, description="Width of each pan")
    
    # Colors
    bg_color: tuple[int, int, int] = Field(default=(255, 255, 255))
    beam_color: tuple[int, int, int] = Field(default=(139, 90, 43))  # Brown
    fulcrum_color: tuple[int, int, int] = Field(default=(100, 100, 100))
    pan_color: tuple[int, int, int] = Field(default=(180, 180, 180))
    weight_color: tuple[int, int, int] = Field(default=(80, 80, 200))
    heavy_side_color: tuple[int, int, int] = Field(default=(200, 50, 50))
