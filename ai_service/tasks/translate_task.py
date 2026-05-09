# Placeholder — TV2 sẽ implement
# @celery_app.task: async translation job (gọi Ollama)
from .celery_app import celery_app
from models.ollama_engine import get_chain
import time

@celery_app.task(bind=True, name="tasks.translate_task.async_translate")
def async_translate_task(self, text_list, direction, glossary_str):
    """
    Xử lý dịch danh sách câu hoặc đoạn văn dài bất đồng bộ.
    """
    chain = get_chain()
    results = []
    total = len(text_list)

    for i, text in enumerate(text_list):
        self.update_state(
            state='PROGRESS',
            meta={'current': i + 1, 'total': total, 'status': 'Processing...'}
        )
        
        try:
            res = chain.invoke({
                "input": text,
                "direction": direction,
                "glossary": glossary_str,
                "examples": ""
            })
            results.append(res)
        except Exception as e:
            results.append(f"[Error]: {str(e)}")
            
    return {
        "status": "Completed",
        "results": results,
        "total_processed": total
    }