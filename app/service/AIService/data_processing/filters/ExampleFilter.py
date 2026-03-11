from app.service.AIService.data_processing.data_processor import BaseFilter

class ExampleFilter(BaseFilter):
    def verify_image(self, image)->bool:
        print("ExampleFilter verify_image")
        return True
    
    def process_image(self, image):
        print("ExampleFilter process_image")
        return image