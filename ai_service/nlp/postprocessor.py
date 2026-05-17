# Placeholder — TV2 sẽ implement
# Ghép câu, format output, handle PDF layout
import re

class Postprocessor:
    def __init__(self):
        self.garbage_patterns = [
            r"^translation\s*:\s*",
            r"^english\s*:\s*",
            r"^vietnamese\s*:\s*",
            r"^output\s*:\s*"
        ]
        self.invalid_keywords = [
            "translation",
            "english:",
            "vietnamese:",
            "i will"
        ]

    def clean_output(self, text: str) -> str:
        """Loại bỏ các prefix rác và lấy dòng đầu tiên"""
        cleaned_text = text.strip()
        for pattern in self.garbage_patterns:
            cleaned_text = re.sub(
                pattern,
                "",
                cleaned_text,
                flags=re.IGNORECASE
            )
        return cleaned_text.split("\n")[0].strip()

    def is_valid_output(self, text: str) -> bool:
        """Kiểm tra xem kết quả AI trả về có hợp lệ không"""
        if not text.strip():
            return False
        
        lowered = text.lower()
        return not any(
            keyword in lowered 
            for keyword in self.invalid_keywords
        )

postprocessor = Postprocessor()