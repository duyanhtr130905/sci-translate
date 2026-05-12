"""
Ollama Configuration
"""

import os
import json

# =========================
# MODEL CONFIG
# =========================
MODEL_AI = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

# =========================
# GPU / RUNTIME SAFETY CONFIG
# =========================
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "2048"))
OLLAMA_NUM_GPU = int(os.getenv("OLLAMA_NUM_GPU", "1"))
OLLAMA_BATCH_SIZE = int(os.getenv("OLLAMA_BATCH_SIZE", "1"))
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "10m")
OLLAMA_NUM_THREAD = int(os.getenv("OLLAMA_NUM_THREAD", "4"))


def get_ollama_params():
    return {
        "num_ctx": OLLAMA_NUM_CTX,
        "num_gpu": OLLAMA_NUM_GPU,
        "num_batch": OLLAMA_BATCH_SIZE,
        "num_thread": OLLAMA_NUM_THREAD,
        "keep_alive": OLLAMA_KEEP_ALIVE,
    }


# =========================
# GLOSSARY
# =========================
GLOSSARY = {
    # Nhóm ML Core
    "Tuesday": "thứ ba",
    "overfitting": "quá khớp",
    "underfitting": "chưa khớp",
    "model": "mô hình",
    "gradient descent": "hạ gradient",
    "learning rate": "tốc độ học",
    "parameter": "tham số",
    "epoch": "vòng lặp huấn luyện",
    "batch size": "kích thước lô",
    "loss function": "hàm mất mát",
    "activation function": "hàm kích hoạt",
    "dropout": "bỏ ngẫu nhiên",
    "fine-tuning": "tinh chỉnh",
    "embedding": "nhúng vector",
    "tokenization": "phân tách token",
    "classification": "phân loại",
    "regression": "hồi quy",
    "clustering": "phân cụm",
    "attention mechanism": "cơ chế chú ý",
    "transformer": "mô hình transformer",
    "backpropagation": "lan truyền ngược",

    # Nhóm Hạ tầng & Hệ thống
    "distributed system": "hệ thống phân tán",
    "cloud computing": "điện toán đám mây",
    "high availability": "độ sẵn sàng cao",
    "latency": "độ trễ",
    "throughput": "thông lượng",
    "load balancing": "cân bằng tải",

    # Nhóm Dữ liệu & Giải thuật
    "data structure": "cấu trúc dữ liệu",
    "complexity": "độ phức tạp",
    "optimization": "tối ưu hóa",
    "preprocessing": "tiền xử lý",
    "feature extraction": "trích xuất đặc trưng",
    "dimensionality reduction": "giảm chiều dữ liệu",

    # Nhóm AI/ML/NLP
    "supervised learning": "học có giám sát",
    "unsupervised learning": "học không giám sát",
    "reinforcement learning": "học tăng cường",
    "neural network": "mạng thần kinh",
    "inference": "suy luận",
    "ground truth": "dữ liệu thực tế",

    # Nhóm Đánh giá
    "accuracy": "độ chính xác",
    "precision": "độ chính xác dự báo",
    "recall": "độ nhạy",
    "benchmark": "kiểm chuẩn",
}

# Extend từ env
env_glossary = os.getenv("AI_GLOSSARY")
if env_glossary:
    try:
        extra = json.loads(env_glossary)
        if isinstance(extra, dict):
            GLOSSARY.update(extra)
    except Exception:
        pass


def build_glossary():
    return "\n".join(f"- {k}: {v}" for k, v in GLOSSARY.items())


class OllamaConfig:
    def __init__(
        self,
        base_url="http://localhost:11434",
        model="qwen2.5:3b",
        temperature=0.3,
        num_ctx=4096,
        timeout=30,
    ):
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.num_ctx = num_ctx
        self.timeout = timeout

    @classmethod
    def from_env(cls):
        return cls(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model=os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
            temperature=float(os.getenv("OLLAMA_TEMPERATURE", "0.3")),
        )

    @staticmethod
    def get_ollama_params():
        return get_ollama_params()

    @staticmethod
    def build_glossary():
        return build_glossary()
