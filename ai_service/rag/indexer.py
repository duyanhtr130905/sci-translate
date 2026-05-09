import json
import os
from rag.vector_store import build_vectorstore

VI_PATH = r"C:\Users\ACER NITRO 5\Desktop\KPDL_Final_Edition\sci-translate\data_pipeline\raw\arxiv_sentences_vi.json"
EN_PATH = r"C:\Users\ACER NITRO 5\Desktop\KPDL_Final_Edition\sci-translate\data_pipeline\raw\arxiv_sentences_en.json"

OUTPUT_JSON = "vi_en_dict.json"
DB_DIR = "vectorstore"

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def merge_json(vi_data, en_data):
    print("Merging VI + EN...")

    vi_dict = {str(item["id"]): item["sentence"] for item in vi_data}
    en_dict = {str(item["id"]): item["sentence"] for item in en_data}

    result = []

    for sent_id in vi_dict:
        if sent_id in en_dict:
            vi = vi_dict[sent_id]
            en = en_dict[sent_id]

            result.append({
                "id": sent_id,
                "text": f"{vi} || {en}",
                "vi": vi,
                "en": en
            })

    print("Total pairs:", len(result))
    return result


def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("Saved JSON:", path)



def main():
    if not os.path.exists(VI_PATH) or not os.path.exists(EN_PATH):
        print("Không tìm thấy file input")
        return

    vi_data = load_json(VI_PATH)
    en_data = load_json(EN_PATH)

    merged = merge_json(vi_data, en_data)

    save_json(merged, OUTPUT_JSON)

    build_vectorstore(merged, DB_DIR)

    print("=== DONE ===")


if __name__ == "__main__":
    main()