# Placeholder — TV2 sẽ implement
# Index corpus vào ChromaDB
import os
from rag.indexer import index_documents 

def run_indexing():
    """
    Quét thư mục data/corpus để đưa toàn bộ tài liệu chuyên ngành vào ChromaDB.
    """
    corpus_path = "./data/corpus"
    if not os.path.exists(corpus_path):
        print(f"Error: Path {corpus_path} not found.")
        return

    print(f"Starting to index documents from {corpus_path}...")
    count = index_documents(corpus_path)
    print(f"Successfully indexed {count} document chunks into Vector Store.")

if __name__ == "__main__":
    run_indexing()