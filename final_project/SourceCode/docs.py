"""文件內容 (WARC)：讀 WARC、HTML 轉文字。WebApp (摘要／全文) 與 semantic (編碼) 共用這一份。"""
import os
import threading
from html.parser import HTMLParser


# ---------------------------------------------------------------- 讀 WARC

def iter_responses(f, read=True):
    """依 WARC 標頭的 Content-Length 逐筆讀取 response 紀錄。
    f 是以 "rb" 開啟的 WARC 檔；回傳 (doc_id, 內容起點, 長度, 內容 bytes)，read=False 時內容為 None (只 seek 不讀)。"""
    while True:
        line = f.readline()
        if not line:
            return
        if not line.startswith(b"WARC/"):
            continue
        header = {}
        while True:
            h = f.readline()
            if h in (b"\r\n", b"\n", b""):
                break
            key, _, value = h.partition(b":")
            header[key.strip().decode("ascii", "ignore")] = value.strip().decode("utf-8", "ignore")
        length = int(header.get("Content-Length", 0))
        start = f.tell()
        block = f.read(length) if read and header.get("WARC-Type") == "response" else None
        f.seek(start + length)
        if header.get("WARC-Type") == "response":
            yield header.get("WARC-TREC-ID") or header.get("WARC-Record-ID"), start, length, block


# ---------------------------------------------------------------- HTML 轉文字

class _TextExtractor(HTMLParser):
    """把 HTML 轉成純文字；script / style / noscript 內的文字不算內文，<title> 的文字另外存為標題。
    meta 沒有結束標籤也沒有文字，不放進 SKIP 計數，否則 <meta> 之後的內文全被跳過。"""
    SKIP = {"script", "style", "noscript"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.title_parts, self._skip, self._in_title = [], [], 0, False
        self._title_done = False  # 只有第一個有文字的 <title> 當標題；之後的 (例如內文 SVG 的 <title>) 算內文

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag == "title" and not self._title_done:
            self._in_title = True

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        elif tag == "title" and self._in_title:
            self._in_title = False
            self._title_done = bool(self.title_parts)

    def handle_data(self, data):
        if self._skip:
            return
        data = data.strip()
        if data:
            (self.title_parts if self._in_title else self.parts).append(data)


def http_body(block):
    """去掉 HTTP 標頭。標頭以第一個空行結束 (\\r\\n\\r\\n 或 \\n\\n，取先出現者)；找不到空行就整段當內容。"""
    ends = [(i, len(sep)) for sep in (b"\r\n\r\n", b"\n\n") if (i := block.find(sep)) >= 0]
    if not ends:
        return block
    i, n = min(ends)
    return block[i + n:]


def html_to_text(block):
    """WARC response 內容 (含 HTTP 標頭) 轉成 (標題, 內文)；內文不含標題。"""
    parser = _TextExtractor()
    try:
        parser.feed(http_body(block).decode("utf-8", "replace"))
    except Exception:
        pass
    return " ".join(parser.title_parts), " ".join(parser.parts)


# ---------------------------------------------------------------- 依 doc ID 取文件

class DocStore:
    """掃一次 WARC 記下每篇文件的位置 (只 seek 不讀內容)，之後依 docID 取出 (標題, 內文)。"""

    def __init__(self, path):
        self.path = path
        self.offsets = {}  # docID -> (內容起點, 長度)
        self.ready = False
        self.available = os.path.exists(path)
        self._cache = {}
        self._lock = threading.Lock()

    def scan(self):
        if not self.available:
            return
        with open(self.path, "rb") as f:
            for doc_id, start, length, _ in iter_responses(f, read=False):
                self.offsets[doc_id] = (start, length)
        self.ready = True

    def get(self, doc_id):
        """回傳 (標題, 內文)；取不到回傳 None。"""
        with self._lock:
            if doc_id in self._cache:
                return self._cache[doc_id]
        location = self.offsets.get(doc_id)
        if location is None:
            return None
        with open(self.path, "rb") as f:
            f.seek(location[0])
            block = f.read(location[1])
        result = html_to_text(block)
        with self._lock:
            if len(self._cache) > 200:
                self._cache.clear()
            self._cache[doc_id] = result
        return result
