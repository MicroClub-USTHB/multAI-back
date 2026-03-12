import cv2
import numpy as np
from app.service.AIService.data_processing.data_processor import BaseFilter


class BrightnessFilter(BaseFilter):
    """
    Detects if an image is too dark or too bright.
    Uses the mean pixel value of the grayscale image.
    Attempts gamma correction as a fix.
    """

    MIN_BRIGHTNESS = 50   # below this = too dark
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
            print("[BrightnessFilter] PASS — brightness is acceptable.")
            return image

        brightness = self._measure_brightness(image)
        print(
            f"[BrightnessFilter] FAIL — brightness out of range. Applying gamma correction...")

        # Step 2 — fix
        if brightness < self.MIN_BRIGHTNESS:
            gamma = 2.0   # brighten
        else:
            gamma = 0.5   # darken

        fixed = self._gamma_correction(image, gamma)

        # Step 3 — retest
        if self.verify_image(fixed):
            print("[BrightnessFilter] PASS after fix — gamma correction worked.")
            return fixed

        # Step 4 — reject
        print("[BrightnessFilter] REJECT — brightness still unacceptable after fix.")
        raise ValueError(
            "Image rejected: brightness out of range and could not be corrected.")
