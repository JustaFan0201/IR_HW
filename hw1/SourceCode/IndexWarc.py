import sys
import json
import requests
from bs4 import BeautifulSoup
from config import WARC_FILE_PATH, SOLR_BASE_URL, BATCH_SIZE

headers = {"Content-type": "application/json"}
update_url = f"{SOLR_BASE_URL}/update"

# 測試用：python IndexWarc.py 200 只匯入前 200 篇
limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0


def read_records(path):
    """依 WARC 標頭的 Content-Length 逐筆讀取，回傳 (標頭 dict, 內容 bytes)。"""
    with open(path, "rb") as f:
        while True:
            line = f.readline()
            if not line:
                return
            if not line.startswith(b"WARC/"):
                continue  # 記錄之間的空行
            header = {}
            while True:
                h = f.readline()
                if h in (b"\r\n", b"\n", b""):
                    break
                key, _, value = h.partition(b":")
                header[key.strip().decode("ascii", "ignore")] = value.strip().decode("utf-8", "ignore")
            yield header, f.read(int(header.get("Content-Length", 0)))


def html_to_text(block):
    """去掉 HTTP 標頭，把 HTML 轉成純文字 (script / style 不算內文)。"""
    _, sep, html = block.partition(b"\r\n\r\n")
    if not sep:  # 有些標頭是用 \n\n 結尾
        _, sep, html = block.partition(b"\n\n")
        if not sep:
            html = block
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)


def post_batch(batch):
    r = requests.post(f"{update_url}/json/docs", params={"commit": "false"}, data=json.dumps(batch), headers=headers)
    if r.status_code != 200:
        print(f"[錯誤] 這批 {len(batch)} 筆匯入失敗：{r.status_code} {r.text[:200]}")
    return r.status_code == 200


print("正在清空 Solr 舊有資料，確保索引乾淨...")
requests.post(update_url, params={"commit": "true"}, json={"delete": {"query": "*:*"}}, headers=headers)
print(f"開始解析並匯入資料: {WARC_FILE_PATH} ...")

batch = []
imported = empty = failed = 0
for header, block in read_records(WARC_FILE_PATH):
    if header.get("WARC-Type") != "response":
        continue
    doc_id = header.get("WARC-TREC-ID") or header.get("WARC-Record-ID")

    try:
        text = html_to_text(block)
    except Exception as e:
        print(f"[警告] {doc_id} 解析失敗：{e}")
        failed += 1
        continue
    if not text:
        empty += 1
        continue

    batch.append({"id": doc_id, "content": text})
    if len(batch) >= BATCH_SIZE:
        if post_batch(batch):
            imported += len(batch)
            print(f"已匯入 {imported} 筆文件...")
        else:
            failed += len(batch)
        batch = []

    if limit and imported + len(batch) >= limit:
        break

if batch:  # 最後不滿一批的尾數
    if post_batch(batch):
        imported += len(batch)
    else:
        failed += len(batch)

requests.post(update_url, params={"commit": "true"})
print(f"完成！匯入 {imported} 篇，內容為空略過 {empty} 篇，失敗 {failed} 篇。")
if failed:
    sys.exit(1)
