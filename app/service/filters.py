import cv2
import numpy as np
from app.service.data_processor import BaseFilter
from app.core.exceptions import AppException


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
        raise AppException.image_blur_error(
            f"Image is too blurry (score: {self._measure_blur(image):.2f}, threshold: {self.BLUR_THRESHOLD}) and could not be recovered."
        )


class BrightnessFilter(BaseFilter):
    """
    Detects if an image is too dark or too bright.
    Uses the mean pixel value of the grayscale image.
    Attempts gamma correction as a fix.
    """

    MIN_BRIGHTNESS = 70   # below this = too dark
    MAX_BRIGHTNESS = 220  # above this = too bright

    def _measure_brightness(self, image: np.ndarray) -> float:
        """Returns mean brightness (0-255). 0 = black, 255 = white."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return float(np.mean(gray))

    def _gamma_correction(self, image: np.ndarray, gamma: float) -> np.ndarray:
        """
        Gamma < 1 = darken, Gamma > 1 = brighten.
        Builds a lookup table for fast per-pixel correction.
        """
        inv_gamma = 1.0 / gamma
        table = np.array([
            ((i / 255.0) ** inv_gamma) * 255
            for i in range(256)
        ], dtype=np.uint8)
        return cv2.LUT(image, table)

    def verify_image(self, image: np.ndarray) -> bool:
        brightness = self._measure_brightness(image)
        print(
            f"[BrightnessFilter] Brightness: {brightness:.2f} (range: {self.MIN_BRIGHTNESS}-{self.MAX_BRIGHTNESS})")
        return self.MIN_BRIGHTNESS <= brightness <= self.MAX_BRIGHTNESS

    def process_image(self, image: np.ndarray) -> np.ndarray:
        # Step 1 — test
        if self.verify_image(image):
            return image

        brightness = self._measure_brightness(image)

        # Step 2 — fix
        gamma = 2.0 if brightness < self.MIN_BRIGHTNESS else 0.5
        fixed = self._gamma_correction(image, gamma)

        # Step 3 — retest
        if self.verify_image(fixed):
            return fixed

        # Step 4 — reject
        raise AppException.bad_request(
            f"Image brightness {brightness:.2f} is out of acceptable range "
            f"({self.MIN_BRIGHTNESS}–{self.MAX_BRIGHTNESS}) and could not be corrected."
        )
