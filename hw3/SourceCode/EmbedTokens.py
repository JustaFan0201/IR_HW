"""HW3：把特殊 token (組員學號) 嵌入文件集，產生 HW3 用的 WARC 與倒排索引。

    python SourceCode/EmbedTokens.py            # 產生檔案並印出 sha256
    python SourceCode/EmbedTokens.py --check    # 只檢查設定能不能用，不寫檔

輸入 (不會被修改)：hw1/02.warc、hw1/HW1.txt
輸出：hw3/02_hw3.warc、hw3/HW1.txt (兩者都被 .gitignore，各自執行產生)
嵌入內容寫在 hw3/embed_tokens.json (進 git)，同一份設定 + 同一支程式 → 每個人產生的檔案完全相同，
可用最後印出的 sha256 與 README 記錄的值比對。

作法：
  1. WARC：在指定文件的 HTTP 標頭之後、HTML 之前插入一句含學號的文字，並更新該筆 WARC 的 Content-Length。
     放在最前面，抽出的純文字一定從這句開始 (RAG 只取每篇前 800 字，放後面會被截掉)。
  2. 索引：不重跑 Solr，直接修補 HW1.txt。
     插入的句子在文件中佔位置 0..k-1 (k = 句子的 token 數，停用詞也佔位，與 HW1 一致)，
     所以這幾篇文件原本所有詞的位置都 +k，再為句子裡的每個詞加上 posting (df、tf 一併更新)。
     句子的切詞用 analyzer.py (與 HW1 Solr 分析鏈一致)。
"""
import argparse
import hashlib
import json
import os
import sys

from bs4 import BeautifulSoup

from analyzer import _TOKEN_RE, analyze_positions
from config import BASE_DIR, INDEX_FILE_PATH, WARC_FILE_PATH
from WebApp import html_to_text as docstore_text

REPO_DIR = os.path.dirname(BASE_DIR)
SOURCE_WARC = os.path.join(REPO_DIR, "hw1", "02.warc")
SOURCE_INDEX = os.path.join(REPO_DIR, "hw1", "HW1.txt")
CONFIG_PATH = os.path.join(BASE_DIR, "embed_tokens.json")


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = json.load(f)
    embeds = {}
    for item in config["docs"]:
        sentence = config["template"].format(student_id=item["student_id"])
        if item["doc_id"] in embeds:
            sys.exit(f"[錯誤] {item['doc_id']} 重複出現在 embed_tokens.json")
        embeds[item["doc_id"]] = sentence
    return embeds


def split_http(block):
    """與 HW1 IndexWarc.html_to_text 相同的切法：回傳 (HTTP 標頭含分隔, HTML)。"""
    head, sep, html = block.partition(b"\r\n\r\n")
    if not sep:
        head, sep, html = block.partition(b"\n\n")
        if not sep:
            return b"", block
    return head + sep, html


def hw1_text(block):
    """HW1 建索引時抽出的純文字 (hw1/SourceCode/IndexWarc.py 的 html_to_text)。"""
    _, html = split_http(block)
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "meta", "noscript"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)


def embed_block(block, sentence):
    head, html = split_http(block)
    return head + sentence.encode("utf-8") + b"\n" + html


def iter_records(f):
    """逐筆回傳 (WARC 標頭原始行 list, 標頭 dict, 內容 bytes, 內容後到下一筆前的位元組)。"""
    pending = b""
    while True:
        line = f.readline()
        if not line:
            if pending:
                yield None, None, None, pending
            return
        if not line.startswith(b"WARC/"):
            pending += line
            continue
        if pending:
            yield None, None, None, pending
            pending = b""
        lines = [line]
        header = {}
        while True:
            h = f.readline()
            lines.append(h)
            if h in (b"\r\n", b"\n", b""):
                break
            key, _, value = h.partition(b":")
            header[key.strip().decode("ascii", "ignore")] = value.strip().decode("utf-8", "ignore")
        yield lines, header, f.read(int(header.get("Content-Length", 0))), b""


def set_content_length(lines, length):
    out = []
    for h in lines:
        key, sep, value = h.partition(b":")
        if sep and key.strip().lower() == b"content-length":
            ending = b"\r\n" if h.endswith(b"\r\n") else b"\n"
            h = key + b": " + str(length).encode() + ending
        out.append(h)
    return out


def process_warc(embeds, write):
    """寫出新 WARC (write=False 時只檢查)；回傳每篇的 token 數 k 與詞位置。"""
    found = {}
    dst = open(WARC_FILE_PATH, "wb") if write else None
    try:
        with open(SOURCE_WARC, "rb") as src:
            for lines, header, block, extra in iter_records(src):
                if lines is None:
                    if dst:
                        dst.write(extra)
                    continue
                doc_id = header.get("WARC-TREC-ID") or header.get("WARC-Record-ID")
                if header.get("WARC-Type") == "response" and doc_id in embeds:
                    sentence = embeds[doc_id]
                    new_block = embed_block(block, sentence)
                    # 兩種抽文字方式 (HW1 索引、HW3 DocStore) 都必須以這句開頭，位置才算得準
                    if not hw1_text(new_block).startswith(sentence):
                        sys.exit(f"[錯誤] {doc_id}：HW1 抽出的文字不是以嵌入句開頭，請換一篇文件")
                    if not docstore_text(new_block)[1].startswith(sentence):
                        sys.exit(f"[錯誤] {doc_id}：DocStore 抽出的文字不是以嵌入句開頭，請換一篇文件")
                    found[doc_id] = (len(_TOKEN_RE.findall(sentence)), analyze_positions(sentence))
                    lines = set_content_length(lines, len(new_block))
                    block = new_block
                if dst:
                    dst.writelines(lines)
                    dst.write(block)
    finally:
        if dst:
            dst.close()
    missing = set(embeds) - set(found)
    if missing:
        sys.exit(f"[錯誤] WARC 裡找不到這些文件：{sorted(missing)}")
    return found


def parse_line(line):
    head, _, rest = line.partition(": <")
    term = head.rpartition(", ")[0]
    postings = {}
    for p in rest[:-1].split("; "):
        doc_part, _, pos = p.partition(": <")
        doc_id = doc_part.split(", ")[0]
        postings[doc_id] = [int(x) for x in pos[:-1].split(", ")]
    return term, postings


def format_line(term, postings):
    parts = "; ".join(
        f"{doc_id}, {len(pos)}: <{', '.join(map(str, pos))}>"
        for doc_id, pos in sorted(postings.items())
    )
    return f"{term}, {len(postings)}: <{parts}>"


def patch_index(found, write):
    """修補倒排索引：目標文件的舊位置 +k，再加入嵌入句的詞。"""
    additions = {}  # term -> {doc_id: [位置]}
    for doc_id, (_, items) in found.items():
        for term, position in items:
            additions.setdefault(term, {}).setdefault(doc_id, []).append(position)
    targets = {doc_id.encode() for doc_id in found}

    def merged(term, postings):
        for doc_id, (k, _) in found.items():
            if doc_id in postings:
                postings[doc_id] = [p + k for p in postings[doc_id]]
        for doc_id, pos in additions.get(term, {}).items():
            postings[doc_id] = sorted(pos + postings.get(doc_id, []))
        return format_line(term, postings)

    seen_docs = set()
    new_terms = sorted(additions, key=lambda t: t.encode("utf-8"))
    dst = open(INDEX_FILE_PATH, "w", encoding="utf-8", newline="\r\n") if write else None
    try:
        with open(SOURCE_INDEX, "rb") as src:
            for raw in src:
                term_bytes = raw[:raw.index(b": <")].rpartition(b", ")[0]
                # 依位元組順序插入原本沒有的詞
                while new_terms and new_terms[0].encode("utf-8") < term_bytes:
                    t = new_terms.pop(0)
                    if dst:
                        dst.write(merged(t, {}) + "\n")
                if new_terms and new_terms[0].encode("utf-8") == term_bytes:
                    new_terms.pop(0)
                if term_bytes.decode("utf-8") in additions or any(d in raw for d in targets):
                    term, postings = parse_line(raw.decode("utf-8").rstrip("\r\n"))
                    hit = {d for d in found if d in postings}
                    seen_docs |= hit
                    if term in additions or hit:
                        line = merged(term, postings)
                    else:
                        line = raw.decode("utf-8").rstrip("\r\n")
                    if dst:
                        dst.write(line + "\n")
                elif dst:
                    dst.write(raw.decode("utf-8").rstrip("\r\n") + "\n")
            for t in new_terms:
                if dst:
                    dst.write(merged(t, {}) + "\n")
    finally:
        if dst:
            dst.close()
    not_indexed = set(found) - seen_docs
    if not_indexed:
        sys.exit(f"[錯誤] 這些文件不在 HW1 索引裡 (HW1 當作空文件略過)，請換一篇：{sorted(not_indexed)}")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="嵌入組員學號，產生 HW3 用的 WARC 與索引")
    parser.add_argument("--check", action="store_true", help="只檢查 embed_tokens.json 能不能用，不寫檔")
    args = parser.parse_args()
    write = not args.check

    embeds = load_config()
    print(f"讀取 {SOURCE_WARC}，嵌入 {len(embeds)} 篇 ...")
    found = process_warc(embeds, write)
    print(f"讀取 {SOURCE_INDEX}，修補索引 ...")
    patch_index(found, write)
    for doc_id, sentence in embeds.items():
        print(f"  {doc_id}: {sentence}")
    if write:
        print(f"完成！\n  {WARC_FILE_PATH}\n    sha256 {sha256(WARC_FILE_PATH)}")
        print(f"  {INDEX_FILE_PATH}\n    sha256 {sha256(INDEX_FILE_PATH)}")
    else:
        print("檢查通過 (未寫檔)。")


if __name__ == "__main__":
    main()
