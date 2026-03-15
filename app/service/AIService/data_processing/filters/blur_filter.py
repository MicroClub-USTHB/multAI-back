import cv2
import numpy as np
from app.service.AIService.data_processing.data_processor import BaseFilter


class BlurFilter(BaseFilter):
    """
    Detects if an image is too blurry.
    Uses Laplacian variance — sharp images have high variance,
    blurry images have low variance.
    Blur cannot be fully fixed, but we attempt a sharpening pass once.
    """

    BLUR_THRESHOLD = 15.0

    def _measure_blur(self, image: np.ndarray) -> float:
        """Returns the Laplacian variance score. Higher = sharper."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return cv2.Laplacian(gray, cv2.CV_64F).var()

    def _sharpen(self, image: np.ndarray) -> np.ndarray:
        """Applies an unsharp mask to try to recover some sharpness."""
        kernel = np.array([
            [0, -1,  0],
            [-1,  5, -1],
            [0, -1,  0]
        ])
        return cv2.filter2D(image, -1, kernel)

    def verify_image(self, image: np.ndarray) -> bool:
        score = self._measure_blur(image)
        print(
            f"[BlurFilter] Blur score: {score:.2f} (threshold: {self.BLUR_THRESHOLD})")
        return score >= self.BLUR_THRESHOLD

    def process_image(self, image: np.ndarray) -> np.ndarray:
        # Step 1 — test
        if self.verify_image(image):
            print("[BlurFilter] PASS — image is sharp enough.")
            return image

        print("[BlurFilter] FAIL — image is blurry. Attempting sharpening fix...")

        # Step 2 — fix
        fixed = self._sharpen(image)

        # Step 3 — retest
        if self.verify_image(fixed):
            print("[BlurFilter] PASS after fix — sharpening worked.")
            return fixed

        # Step 4 — reject
        print("[BlurFilter] REJECT — image still too blurry after fix.")
        raise ValueError(
            "Image rejected: too blurry and could not be recovered.")
