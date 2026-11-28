# hw3/SourceCode/RagLLM.py
import os
import ollama
import Search as S
from WebApp import DocStore
from config import WARC_FILE_PATH, BASE_DIR, DEFAULT_MODEL

# 載入 HW2 倒排索引
print("正在載入倒排索引...")
S.load_index()

# 初始化 WARC 文件讀取器 (抓取全文)
doc_store = DocStore(WARC_FILE_PATH)
if doc_store.available:
    print(f"正在掃描 WARC 檔 ({WARC_FILE_PATH})...")
    doc_store.scan()
    print(f"WARC 檔掃描完成，共有 {len(doc_store.offsets)} 篇文件可用。")
else:
    print(f"[警告] 找不到 WARC 檔：{WARC_FILE_PATH}，RAG 只能使用 Doc ID 做測試。")

def get_context_from_hw2(query: str, top_k: int = 3) -> str:
    """呼叫 HW2 的 Search 抓取前 k 篇相關文件與內文"""
    try:
        results, _, _ = S.search(query, interactive=False, top_k=top_k)
    except Exception as e:
        print(f"檢索發生錯誤: {e}")
        return ""

    if not results:
        return "No relevant documents found."

    context_text = ""
    for rank, (doc_id, score) in enumerate(results[:top_k], 1):
        context_text += f"\n--- Document {rank} (ID: {doc_id}, Score: {score:.4f}) ---\n"
        
        # 從 DocStore 取出標題與內文
        doc = doc_store.get(doc_id) if doc_store.ready else None
        if doc:
            title, body = doc
            if title:
                context_text += f"Title: {title}\n"
            # 擷取內文前 800 個字，防止 Context 過長
            clean_body = body.strip().replace("\n", " ")
            context_text += f"Content: {clean_body[:800]}...\n"
        else:
            context_text += "Content: [Content not available in WARC]\n"
        
    return context_text

def generate_rag_response(user_prompt: str, use_rag: bool = True, model_name: str = DEFAULT_MODEL) -> str:
    """呼叫 Ollama 產生回應 (可切換有/無 RAG)"""
    
    if use_rag:
        # 檢索相關文獻
        context = get_context_from_hw2(user_prompt, top_k=3)
        
        # 組合 Final Prompt
        system_instruction = (
            "You are a helpful assistant. Answer the user's prompt based strictly on the provided Context. "
            "If the info contains document IDs, titles, or special tokens (such as student IDs), cite them explicitly in your answer. "
            "If the answer cannot be found in the Context, state that you do not know."
        )
        full_prompt = f"Context Documents:\n{context}\n\nUser Prompt:\n{user_prompt}"
    else:
        system_instruction = "You are a helpful assistant."
        full_prompt = user_prompt

    # 呼叫 Ollama API
    try:
        response = ollama.chat(
            model=model_name,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": full_prompt},
            ]
        )
        return response['message']['content']
    except Exception as e:
        return f"[Ollama 呼叫失敗] 請確認 Ollama 服務已啟動且模型已下載 ({model_name})。錯誤資訊: {e}"

if __name__ == "__main__":
    print("==================================================")
    print(" IR HW3: RAG with Local Open LLM (Ollama)")
    print("==================================================")

    while True:
        prompt = input("\n請輸入 Prompt (輸入 exit 離開): ").strip()
        if prompt.lower() == 'exit':
            break
        if not prompt:
            continue

        print("\n------------------ [無 RAG 對照組] ------------------")
        no_rag_ans = generate_rag_response(prompt, use_rag=False)
        print(no_rag_ans)

        print("\n------------------ [有 RAG 實驗組] ------------------")
        rag_ans = generate_rag_response(prompt, use_rag=True)
        print(rag_ans)