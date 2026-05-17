# Placeholder — TV2 sẽ implement
# Tách câu, tokenize, làm sạch văn bản
import re

class Preprocessor:
    def __init__(self):
        self.vi_pattern = (
            r"[àáạảãâầấậẩẫăằắặẳẵ"
            r"èéẹẻẽêềếệểễ"
            r"ìíịỉĩ"
            r"òóọỏõôồốộổỗơờớợởỡ"
            r"ùúụủũưừứựửữ"
            r"ỳýỵỷỹđ]"
        )

    def detect_language(self, text: str) -> str:
        """Nhận diện ngôn ngữ: trả về 'vi' hoặc 'en'"""
        if re.search(self.vi_pattern, text.lower()):
            return "vi"
        return "en"

    def get_direction(self, text: str) -> str:
        """Xác định chiều dịch thuật"""
        lang = self.detect_language(text)
        if lang == "vi":
            return "Vietnamese to English"
        return "English to Vietnamese"

preprocessor = Preprocessor()