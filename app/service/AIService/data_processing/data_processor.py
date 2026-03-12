from abc import ABC, abstractmethod
from app.service.AIService.data_processing.filters.blur_filter import BlurFilter
from app.service.AIService.data_processing.filters.brightness_filter import BrightnessFilter


class BaseFilter(ABC):

    @abstractmethod
    def verify_image(self, image) -> bool:
        pass

    @abstractmethod
    def process_image(self, image):
        pass


class FilterFactory:
    def __init__(self):
        self.filters = {
            "blur_filter": BlurFilter,
            "brightness_filter": BrightnessFilter,
        }

    def get_filter(self, filter_type: str) -> BaseFilter:
        if filter_type in self.filters:
            return self.filters[filter_type]
        else:
            raise ValueError("Invalid filter type")
