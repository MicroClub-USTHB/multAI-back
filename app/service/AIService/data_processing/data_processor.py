from abc import ABC, abstractmethod

class BaseFilter(ABC):

    @abstractmethod
    def verify_image(self, image)->bool:
        pass

    @abstractmethod
    def process_image(self, image):
        pass

class FilterFactory:
    def __init__(self):
        self.filters = {
            # blur_filter: BlurFilter
        }
    
    def get_filter(self, filter_type:str)->BaseFilter:
        if filter_type in self.filters:
            return self.filters[filter_type]
        else:
            raise ValueError("Invalid filter type")