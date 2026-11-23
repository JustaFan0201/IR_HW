"""HW2 加分：網頁搜尋介面 (只用 Python 標準函式庫，不需額外套件)。

    python SourceCode/WebApp.py [--port 8000] [--top 10] [--weighting tfidf] [--champion R]

啟動後開啟 http://127.0.0.1:8000 。功能：
  - 搜尋框 (支援布林、片語、鄰近、萬用字元) 與權重方案、顯示筆數選單
  - 拼字/發音建議，點一下就套用
  - 結果摘要並標示查詢詞 (highlighting)，點標題可看全文 (同樣標示)
  - 結果分群 (模組 B)：對前 N 篇結果做 k-means / 階層式分群，左側欄顯示各群標籤與篇數，點一群只看該群；
    上方的 2D 散佈圖 (PCA) 每個點是一篇文件、顏色是所屬群，點一個點就打開該篇文件
摘要與全文來自 HW1 的 WARC 檔 (config.py 的 WARC_FILE_PATH)；找不到該檔時仍可搜尋，只是不顯示摘要。
"""
import argparse
import html
import os
import re
import threading
import time
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import Search
import clustering
from analyzer import analyze, token_spans
from config import (BASE_DIR, CLUSTER_METHOD, CLUSTER_TOP_N, DEFAULT_WEIGHTING, TOP_K,
                    WARC_FILE_PATH)

SNIPPET_CHARS = 300
FULL_TEXT_CHARS = 100_000
TOP_CHOICES = (10, 20, 50, 100)
EXAMPLES = ['airplanes', 'United States government', 'hong AND NOT kong', '"hong kong"~5',
            'govern*', 'goverment', 'mikrosoft', 'java', 'apple', 'jaguar']
CLUSTER_OFF = "off"
CLUSTER_CHOICES = (CLUSTER_OFF,) + clustering.METHODS
K_CHOICES = (2, 3, 4, 5, 6, 7, 8)
# 分群依據：整頁，或查詢詞前後文 (網頁的導覽列、側欄很多，整頁容易分出「哪個網站」而不是詞義)
CONTEXT_PAGE, CONTEXT_QUERY = "page", "ctx"
CONTEXT_NAMES = {CONTEXT_PAGE: "分群依據：整頁", CONTEXT_QUERY: "分群依據：查詢詞前後文"}


# ---------------------------------------------------------------- 文件內容 (WARC)

class _TextExtractor(HTMLParser):
    """把 HTML 轉成純文字；script / style / noscript 的內容不算內文，與 HW1 的處理一致。"""
    # meta 是沒有結束標籤的元素 (<meta ...> 不會有 </meta>)，放在 SKIP 裡計數器永遠減不回來，
    # 導致 <meta> 之後的內文全部被略過；meta 本來就沒有文字內容，不需要略過。
    SKIP = {"script", "style", "noscript"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.title, self._skip, self._in_title = [], "", 0, False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._skip:
            return
        data = data.strip()
        if not data:
            return
        if self._in_title and not self.title:
            self.title = data
        self.parts.append(data)


def html_to_text(block):
    """去掉 HTTP 標頭後轉文字，回傳 (標題, 內文)。"""
    _, sep, body = block.partition(b"\r\n\r\n")
    if not sep:
        _, sep, body = block.partition(b"\n\n")
        if not sep:
            body = block
    parser = _TextExtractor()
    try:
        parser.feed(body.decode("utf-8", "replace"))
    except Exception:
        pass
    return parser.title, " ".join(parser.parts)


class DocStore:
    """掃一次 WARC 記下每篇文件的位置 (只 seek 不讀內容)，之後依 docID 取出文字。"""

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
            while True:
                line = f.readline()
                if not line:
                    break
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
                if header.get("WARC-Type") == "response":
                    doc_id = header.get("WARC-TREC-ID") or header.get("WARC-Record-ID")
                    self.offsets[doc_id] = (f.tell(), length)
                f.seek(length, os.SEEK_CUR)
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


# ---------------------------------------------------------------- 標示查詢詞

def query_terms_for_highlight(query, suggestions):
    """查詢裡要標示的詞幹 (含萬用字元展開的詞與拼字建議)。"""
    expression = Search.parse_boolean_query(query)
    terms = set(Search.get_boolean_terms(expression)) if expression is not None else set(analyze(query))
    for matches in suggestions.values():
        terms.update(matches[:1])
    return terms


def highlight(text, terms):
    """把 text 中詞幹屬於 terms 的 token 包上 <mark>，其餘跳脫成安全的 HTML。"""
    out, last = [], 0
    for start, end, stem in token_spans(text):
        if stem in terms:
            out.append(html.escape(text[last:start]))
            out.append(f"<mark>{html.escape(text[start:end])}</mark>")
            last = end
    out.append(html.escape(text[last:]))
    return "".join(out)


def make_snippet(text, terms):
    """挑查詢詞最密集的一段 (約 SNIPPET_CHARS 字) 當摘要，並標示查詢詞。"""
    hits = [(s, e) for s, e, stem in token_spans(text) if stem in terms]
    start = 0
    if hits:
        best, best_count = hits[0][0], 0
        for i, (s, _) in enumerate(hits):  # 以每個命中為視窗起點，數視窗內有幾個命中
            count = sum(1 for h in hits[i:i + 12] if h[0] < s + SNIPPET_CHARS)
            if count > best_count:
                best, best_count = s, count
        start = max(0, best - 40)
        start = text.rfind(" ", 0, start) + 1 if start else 0
    piece = text[start:start + SNIPPET_CHARS]
    if start + SNIPPET_CHARS < len(text):
        piece = piece[:piece.rfind(" ")] if " " in piece else piece
    return ("… " if start else "") + highlight(piece, terms) + (" …" if start + len(piece) < len(text) else "")


# ---------------------------------------------------------------- 頁面

CSS = """
:root{--bg:#f6f7f9;--fg:#1c2330;--muted:#667085;--card:#fff;--line:#e3e6eb;--accent:#2455d8;--mark:#ffe58a;--warn:#fff4d6;--warnfg:#6b4e00}
@media (prefers-color-scheme:dark){:root{--bg:#14171c;--fg:#e6e9ee;--muted:#9aa3b2;--card:#1d2128;--line:#2c323b;--accent:#7ea2ff;--mark:#6b5600;--warn:#3a3014;--warnfg:#f2d98a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 system-ui,"Noto Sans TC","Microsoft JhengHei",sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 60px}
h1{font-size:22px;margin:0 0 4px}.sub{color:var(--muted);margin:0 0 18px}
form.search{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px}
input[type=text]{flex:1 1 320px;padding:10px 12px;font-size:16px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--fg)}
select,button{padding:10px 12px;font-size:14px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--fg)}
button{background:var(--accent);color:#fff;border-color:var(--accent);cursor:pointer;font-weight:600}
.examples{font-size:13px;color:var(--muted);margin-bottom:18px}.examples a{margin-right:10px}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.meta{color:var(--muted);font-size:13px;margin:12px 0}
.notice{background:var(--warn);color:var(--warnfg);padding:8px 12px;border-radius:8px;margin:8px 0;font-size:14px}
.result{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:10px 0}
.result .title{font-size:17px;font-weight:600}.result .id{color:var(--muted);font-size:12px;font-family:ui-monospace,Consolas,monospace}
.result .score{float:right;color:var(--muted);font-size:13px;font-variant-numeric:tabular-nums}
.snippet{margin-top:4px;word-break:break-word}mark{background:var(--mark);color:inherit;padding:0 2px;border-radius:3px}
.fulltext{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;white-space:pre-wrap;word-break:break-word}
.empty{color:var(--muted);padding:20px 0}
"""


def page(title, body):
    return (f"<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(title)}</title><style>{CSS}{clustering.CLUSTER_CSS}</style></head><body><main>{body}</main></body></html>")


class App:
    def __init__(self, top, weighting, champion, store):
        self.top, self.weighting, self.champion, self.store = top, weighting, champion, store

    # ------------------------------------------------ 網址
    def view_url(self, q, weighting, top, cm, k, cl=None, apply=False, cx=CONTEXT_PAGE):
        """同一個搜尋畫面的網址 (保留權重、筆數、分群方法與群數；cl 是只看某一群)。"""
        parts = [f"q={requests_quote(q)}", f"weighting={weighting}", f"top={top}", f"cm={cm}", f"cx={cx}"]
        if k:
            parts.append(f"k={k}")
        if cl is not None:
            parts.append(f"cl={cl}")
        if apply:
            parts.append("apply=1")
        return "/?" + "&".join(parts)

    def search_form(self, q, weighting, top, cm, k, cx=CONTEXT_PAGE):
        weight_options = "".join(
            f"<option value='{w}'{' selected' if w == weighting else ''}>{w}</option>"
            for w in Search.WEIGHTING_SCHEMES)
        top_options = "".join(
            f"<option value='{n}'{' selected' if n == top else ''}>前 {n} 名</option>"
            for n in sorted(set(TOP_CHOICES) | {top}))
        cluster_options = "".join(
            f"<option value='{c}'{' selected' if c == cm else ''}>"
            f"{'不分群' if c == CLUSTER_OFF else '分群：' + clustering.METHOD_NAMES[c]}</option>"
            for c in CLUSTER_CHOICES)
        context_options = "".join(
            f"<option value='{c}'{' selected' if c == cx else ''}>{name}</option>" for c, name in CONTEXT_NAMES.items())
        k_options = "<option value=''>群數：自動</option>" + "".join(
            f"<option value='{n}'{' selected' if n == k else ''}>{n} 群</option>" for n in K_CHOICES)
        examples = " ".join(
            f"<a href='/?q={html.escape(requests_quote(e))}&weighting={weighting}&top={top}&cm={cm}&cx={cx}'>{html.escape(e)}</a>"
            for e in EXAMPLES)
        return (f"<h1>IR HW2 搜尋</h1><p class='sub'>向量空間模型 (TF-IDF + cosine)，索引來自 HW1，共 {Search.TOTAL_DOCS:,} 篇</p>"
                f"<form class='search' action='/' method='get'>"
                f"<input type='text' name='q' value='{html.escape(q, quote=True)}' placeholder='例如：hong AND NOT kong' autofocus>"
                f"<select name='weighting'>{weight_options}</select><select name='top'>{top_options}</select>"
                f"<select name='cm'>{cluster_options}</select><select name='cx'>{context_options}</select>"
                f"<select name='k'>{k_options}</select>"
                f"<button type='submit'>搜尋</button></form><div class='examples'>範例：{examples}</div>")

    def home(self, params):
        q = params.get("q", [""])[0].strip()
        weighting = params.get("weighting", [self.weighting])[0]
        if weighting not in Search.WEIGHTING_SCHEMES:
            weighting = self.weighting
        try:
            top = max(1, min(500, int(params.get("top", [self.top])[0])))
        except ValueError:
            top = self.top
        cm = params.get("cm", [CLUSTER_METHOD])[0]
        if cm not in CLUSTER_CHOICES:
            cm = CLUSTER_METHOD
        try:
            k = int(params.get("k", [""])[0] or 0)
        except ValueError:
            k = 0
        k = k if k in K_CHOICES else None
        cx = params.get("cx", [CONTEXT_PAGE])[0]
        if cx not in CONTEXT_NAMES:
            cx = CONTEXT_PAGE
        try:
            cl = int(params["cl"][0]) if "cl" in params else None
        except ValueError:
            cl = None
        apply_suggestions = params.get("apply", ["0"])[0] == "1"

        body = [self.search_form(q, weighting, top, cm, k, cx)]
        if q:
            body.append(self.results(q, weighting, top, apply_suggestions, cm, k, cl, cx))
        return page("IR HW2 搜尋" if not q else f"{q} - IR HW2 搜尋", "".join(body))

    # ------------------------------------------------ 結果頁
    def results(self, q, weighting, top, apply_suggestions, cm=CLUSTER_OFF, k=None, cl=None, cx=CONTEXT_PAGE):
        started = time.perf_counter()
        try:
            results, suggestions, notes = Search.search(
                q, interactive=False, weighting=weighting, use_champion=self.champion is not None,
                top_k=top, apply_suggestions=apply_suggestions)
        except ValueError as error:
            return f"<div class='notice'>查詢錯誤：{html.escape(str(error))}</div>"
        elapsed = (time.perf_counter() - started) * 1000

        parts = []
        for note in notes:
            parts.append(f"<div class='notice'>萬用字元：{html.escape(note)}</div>")
        if suggestions:
            lines = "；".join(html.escape(Search.format_suggestions(t, m)) for t, m in suggestions.items())
            if apply_suggestions:
                parts.append(f"<div class='notice'>已套用拼字建議：{lines}</div>")
            else:
                link = self.view_url(q, weighting, top, cm, k, apply=True, cx=cx)
                parts.append(f"<div class='notice'>拼字建議：{lines} — <a href='{html.escape(link)}'>改用第一個建議搜尋</a></div>")

        terms = query_terms_for_highlight(q, suggestions)
        # 分群：只對排名前 CLUSTER_TOP_N 篇做 (顯示筆數不影響分群範圍)
        analysis, surface, selected, no_structure_notice = None, {}, None, ""
        if cm != CLUSTER_OFF and results:
            if clustering.is_ready():
                context_kwargs = {}
                if cx == CONTEXT_QUERY:             # 只取查詢詞前後文分群：需要文件內文 (WARC 摘要資料)
                    if self.store.ready:
                        context_kwargs = dict(query_terms=frozenset(terms),
                                              get_text=lambda d: (self.store.get(d) or (None, None))[1])
                    else:
                        parts.append("<div class='notice'>前後文分群需要文件內文 (WARC 還在掃描)，這次先用整頁分群。</div>")
                analysis = clustering.analyze([doc_id for doc_id, _ in results[:CLUSTER_TOP_N]], cm, k, **context_kwargs)
                if analysis["no_structure"]:        # 分不出明顯的群：不畫側欄與散佈圖，只在結果上方提示
                    no_structure_notice = clustering.render_no_structure(analysis)
                    analysis = None
                else:
                    surface = clustering.surface_forms(
                        analysis, lambda d: (self.store.get(d) or (None, None))[1] if self.store.ready else None)
                    if cl is not None and 0 <= cl < len(analysis["clusters"]):
                        selected = cl
            else:
                parts.append("<div class='notice'>分群功能準備中 (正在建立文件向量)，稍後重新整理即可。</div>")

        mode = "，champion list 近似計分" if self.champion is not None else ""
        if selected is not None:
            shown = analysis["clusters"][selected]["doc_ids"]
            shown_text = f"群 {selected} 的 {len(shown)} 篇"
        else:
            shown = [doc_id for doc_id, _ in results[:top]]
            shown_text = f"顯示前 {min(top, len(results))} 名"
        parts.append(f"<div class='meta'>命中 {len(results):,} 篇，{shown_text} · "
                     f"{weighting}{mode} · {elapsed:.0f} ms</div>")
        parts.append(no_structure_notice)
        if not results:
            parts.append("<div class='empty'>找不到符合的搜尋結果。</div>")
            return "".join(parts)

        scores = dict(results[:max(top, CLUSTER_TOP_N)])
        rank_of = {doc_id: rank for rank, (doc_id, _) in enumerate(results[:max(top, CLUSTER_TOP_N)], 1)}
        assignment = analysis["assignment"] if analysis else {}

        def doc_link(doc_id):
            link = f"/doc?id={requests_quote(doc_id)}&q={requests_quote(q)}" + ("&apply=1" if apply_suggestions else "")
            back = self.view_url(q, weighting, top, cm, k, selected, apply_suggestions, cx)
            return f"{link}&ret={requests_quote(back)}"

        cards = []
        for doc_id in shown:
            rank, score = rank_of[doc_id], scores[doc_id]
            doc = self.store.get(doc_id) if self.store.ready else None
            title = (doc[0] if doc and doc[0] else doc_id)
            snippet = make_snippet(doc[1], terms) if doc else ""
            style, chip, css = "", "", ""
            info = clustering.doc_cluster_info(analysis, doc_id, surface) if analysis else None
            if info:
                cluster_id, color, label = info
                style, css = f" style='border-left-color:{color}'", " clustered"
                chip = f"<span class='chip'>群 {cluster_id}：{html.escape(label)}</span>"
            cards.append(
                f"<div class='result{css}'{style}><span class='score'>{score:.6f}</span>"
                f"<div class='title'>{rank}. <a href='{html.escape(doc_link(doc_id))}'>{highlight(title[:120], terms)}</a></div>"
                f"<div class='id'>{html.escape(doc_id)}{chip}</div>"
                + (f"<div class='snippet'>{snippet}</div>" if snippet else "") + "</div>")
        if not self.store.ready:
            cards.append("<div class='meta'>(" + ("摘要尚未準備好：正在掃描 WARC 檔，稍後重新整理即可。" if self.store.available
                                                else "找不到 WARC 檔，因此不顯示摘要。") + ")</div>")

        if analysis is None or not analysis["clusters"]:
            return "".join(parts) + "".join(cards)
        sidebar = clustering.render_sidebar(
            analysis,
            lambda cluster_id: self.view_url(q, weighting, top, cm, k, cluster_id, apply_suggestions, cx),
            selected, surface)
        titles = {d: (self.store.get(d) or ("", ""))[0] for d in analysis["assignment"]} if self.store.ready else {}
        plot = clustering.render_scatter(analysis, doc_link, selected, titles, rank_of, surface)
        return "".join(parts) + f"<div class='layout'>{sidebar}<section>{plot}{''.join(cards)}</section></div>"

    def document(self, params):
        doc_id = params.get("id", [""])[0]
        q = params.get("q", [""])[0]
        doc = self.store.get(doc_id) if self.store.ready else None
        ret = params.get("ret", [""])[0]
        # 回到原本的搜尋畫面 (含分群與篩選)；只接受站內的 /?... 網址
        back = ret if ret.startswith("/?") else f"/?q={requests_quote(q)}"
        if doc is None:
            return page("找不到文件", f"<p><a href='{html.escape(back)}'>← 回搜尋結果</a></p><div class='empty'>找不到文件 {html.escape(doc_id)} 的內容。</div>")
        suggestions = {}
        if params.get("apply", ["0"])[0] == "1" and q:
            try:
                _, suggestions, _ = Search.search(q, interactive=False, apply_suggestions=False)
            except ValueError:
                pass
        terms = query_terms_for_highlight(q, suggestions) if q else set()
        text = doc[1][:FULL_TEXT_CHARS]
        cut = "<div class='meta'>(內容過長，只顯示前 100,000 字)</div>" if len(doc[1]) > FULL_TEXT_CHARS else ""
        return page(doc[0] or doc_id,
                    f"<p><a href='{html.escape(back)}'>← 回搜尋結果</a></p><h1>{html.escape(doc[0] or doc_id)}</h1>"
                    f"<div class='id sub'>{html.escape(doc_id)}</div>{cut}<div class='fulltext'>{highlight(text, terms)}</div>")


def requests_quote(value):
    from urllib.parse import quote
    return quote(value, safe="")


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            url = urlparse(self.path)
            params = parse_qs(url.query)
            try:
                if url.path == "/":
                    content = app.home(params)
                elif url.path == "/doc":
                    content = app.document(params)
                else:
                    self.send_error(404)
                    return
                status = 200
            except Exception as error:  # 不讓單一請求的錯誤把伺服器弄掛
                content, status = page("錯誤", f"<div class='notice'>內部錯誤：{html.escape(repr(error))}</div>"), 500
            data = content.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, fmt, *args):
            pass

    return Handler


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IR HW2: 網頁搜尋介面")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--top", type=Search.positive_int, default=TOP_K, help="預設顯示前 N 名")
    parser.add_argument("--weighting", choices=Search.WEIGHTING_SCHEMES, default=DEFAULT_WEIGHTING)
    parser.add_argument("--champion", type=Search.positive_int, metavar="R",
                        help="啟用 champion list 近似檢索 (只對與 --weighting 相同的方案生效)")
    args = parser.parse_args()

    Search.load_index()
    if args.champion is not None:
        count = Search.build_champion_lists(args.champion, args.weighting)
        print(f"champion list 建立完成：{count} 個詞 (每個保留貢獻最大的 {args.champion} 篇)")

    if not hasattr(Search, "get_doc_vector"):   # 還沒有 get_doc_vector 時，先在背景建好分群用的文件矩陣
        def build_cluster_matrix():
            started = time.perf_counter()
            clustering.build_doc_matrix()
            print(f"分群用的文件向量建立完成 ({time.perf_counter() - started:.1f} 秒)")
        threading.Thread(target=build_cluster_matrix, daemon=True).start()

    store = DocStore(WARC_FILE_PATH)
    if store.available:
        threading.Thread(target=lambda: (store.scan(), print(f"WARC 掃描完成：{len(store.offsets)} 篇文件可顯示摘要")),
                         daemon=True).start()
    else:
        print(f"[提醒] 找不到 WARC 檔 {WARC_FILE_PATH}，網頁仍可搜尋，但不會顯示摘要與全文。")

    server = ThreadingHTTPServer((args.host, args.port), make_handler(App(args.top, args.weighting, args.champion, store)))
    print(f"網頁介面已啟動：http://{args.host}:{args.port}  (Ctrl+C 結束)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass