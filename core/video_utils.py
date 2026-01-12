"""Video generation utilities."""

from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image
import importlib.util

CV2_AVAILABLE = importlib.util.find_spec("cv2") is not None

if CV2_AVAILABLE:
    import cv2
    import numpy as np
else:
    cv2 = None
    np = None


class VideoGenerator:
    """Generate videos from image sequences."""
    
    def __init__(self, fps: int = 10, output_format: str = "mp4"):
        self.fps = fps
        self.output_format = output_format
        self.codec = 'mp4v' if output_format == "mp4" else 'XVID'
        self.extension = '.mp4' if output_format == "mp4" else '.avi'
        
        if not CV2_AVAILABLE:
            raise ImportError("opencv-python is required for video generation")
    
    @staticmethod
    def is_available() -> bool:
        return CV2_AVAILABLE
    
    def create_video_from_frames(
        self,
        frames: List[Image.Image],
        output_path: Path,
        size: Optional[Tuple[int, int]] = None
    ) -> Path:
        if not frames:
            raise ValueError("No frames provided")
        
        if size is None:
            size = frames[0].size
        
        width, height = size
        output_path = Path(output_path).with_suffix(self.extension)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        fourcc = cv2.VideoWriter_fourcc(*self.codec)
        writer = cv2.VideoWriter(str(output_path), fourcc, self.fps, (width, height))
        
        for frame in frames:
            if frame.size != size:
                frame = frame.resize(size, Image.Resampling.LANCZOS)
            frame_rgb = frame.convert('RGB')
            frame_array = np.array(frame_rgb)
            frame_bgr = cv2.cvtColor(frame_array, cv2.COLOR_RGB2BGR)
            writer.write(frame_bgr)
        
        writer.release()
        return output_path
