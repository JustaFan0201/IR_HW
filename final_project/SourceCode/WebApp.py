"""HW2 加分：網頁搜尋介面 (只用 Python 標準函式庫，不需額外套件)。

    python SourceCode/WebApp.py [--port 8000] [--top 10] [--weighting tfidf] [--champion R]

啟動後開啟 http://127.0.0.1:8000 。功能：
  - 搜尋框 (支援布林、片語、鄰近、萬用字元) 與權重方案、顯示筆數選單
  - 拼字/發音建議，點一下就套用
  - 結果摘要並標示查詢詞 (highlighting)，點標題可看全文 (同樣標示)
摘要與全文來自 HW1 的 WARC 檔 (config.py 的 WARC_FILE_PATH)；找不到該檔時仍可搜尋，只是不顯示摘要。
"""
import argparse
import html
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import Search
import feedback
from docs import DocStore
from analyzer import analyze, token_spans
from config import (BASE_DIR, DEFAULT_WEIGHTING, ROCCHIO_ALPHA, ROCCHIO_BETA, ROCCHIO_GAMMA, TOP_K,
                    WARC_FILE_PATH)

SNIPPET_CHARS = 300
FULL_TEXT_CHARS = 100_000
TOP_CHOICES = (10, 20, 50, 100)
EXAMPLES = ['airplanes', 'United States government', 'hong AND NOT kong', '"hong kong"~5',
            'govern*', 'goverment', 'mikrosoft']


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


# ---------------------------------------------------------------- 相關回饋 (模組 A 的 rocchio)

FEEDBACK_SHOWN_TERMS = 10  # 結果頁顯示 Rocchio 加入的前幾個詞


def scoring_terms(q, suggestions, apply_suggestions):
    """與 Search.search 相同的計分詞與布林運算式 (含拼字建議替換)，回傳 (terms, expression)。"""
    expression = Search.parse_boolean_query(q)
    if expression is not None:
        if apply_suggestions and suggestions:
            expression = Search.replace_boolean_terms(expression, suggestions)
        return Search.get_boolean_terms(expression), expression
    terms = analyze(q)
    if apply_suggestions:
        terms = [suggestions[t][0] if t in suggestions else t for t in terms]
    return terms, None


def rocchio_rerank(q, suggestions, apply_suggestions, rel_ids, nonrel_ids):
    """以 Rocchio 修正查詢向量後用 tfidf cosine 重查；布林查詢仍限制在符合運算式的文件內。
    回傳 (results, 新加入的詞 [(詞, 權重)])。"""
    terms, expression = scoring_terms(q, suggestions, apply_suggestions)
    new_vec = feedback.rocchio(Search.query_vector(terms), rel_ids, nonrel_ids)
    allowed = Search.evaluate_boolean_query(expression) if expression is not None else None
    added = sorted(((t, w) for t, w in new_vec.items() if t not in set(terms)), key=lambda x: x[1], reverse=True)
    return Search.rank_by_vector(new_vec, allowed), added[:FEEDBACK_SHOWN_TERMS]


# ---------------------------------------------------------------- 頁面

CSS = """
:root{--bg:#f6f7f9;--fg:#1c2330;--muted:#667085;--card:#fff;--line:#e3e6eb;--accent:#2455d8;--mark:#ffe58a;--warn:#fff4d6;--warnfg:#6b4e00}
@media (prefers-color-scheme:dark){:root{--bg:#14171c;--fg:#e6e9ee;--muted:#9aa3b2;--card:#1d2128;--line:#2c323b;--accent:#7ea2ff;--mark:#6b5600;--warn:#3a3014;--warnfg:#f2d98a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 system-ui,"Noto Sans TC","Microsoft JhengHei",sans-serif}
main{max-width:820px;margin:0 auto;padding:24px 16px 60px}
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
.votes{margin-left:12px}.votes label{margin-right:8px;cursor:pointer;font-family:system-ui,sans-serif;font-size:14px}
.votes input{vertical-align:middle;margin:0 3px 0 0}.fbbar{margin:10px 0}
"""

# 同一篇的 👍 和 👎 互斥：勾一個就取消另一個
VOTE_SCRIPT = """<script>document.querySelectorAll('.votes input').forEach(function(box){
box.addEventListener('change',function(){if(!box.checked)return;
box.closest('.votes').querySelectorAll('input').forEach(function(o){if(o!==box)o.checked=false;});});});</script>"""


def page(title, body):
    return (f"<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(title)}</title><style>{CSS}</style></head><body><main>{body}</main></body></html>")


class App:
    def __init__(self, top, weighting, champion, store):
        self.top, self.weighting, self.champion, self.store = top, weighting, champion, store

    def search_form(self, q, weighting, top):
        weight_options = "".join(
            f"<option value='{w}'{' selected' if w == weighting else ''}>{w}</option>"
            for w in Search.WEIGHTING_SCHEMES)
        top_options = "".join(
            f"<option value='{n}'{' selected' if n == top else ''}>前 {n} 名</option>"
            for n in sorted(set(TOP_CHOICES) | {top}))
        examples = " ".join(
            f"<a href='/?q={html.escape(requests_quote(e))}&weighting={weighting}&top={top}'>{html.escape(e)}</a>"
            for e in EXAMPLES)
        return (f"<h1>IR HW2 搜尋</h1><p class='sub'>向量空間模型 (TF-IDF + cosine)，索引來自 HW1，共 {Search.TOTAL_DOCS:,} 篇</p>"
                f"<form class='search' action='/' method='get'>"
                f"<input type='text' name='q' value='{html.escape(q, quote=True)}' placeholder='例如：hong AND NOT kong' autofocus>"
                f"<select name='weighting'>{weight_options}</select><select name='top'>{top_options}</select>"
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
        apply_suggestions = params.get("apply", ["0"])[0] == "1"
        rel_ids, nonrel_ids = params.get("rel", []), params.get("nonrel", [])
        both = set(rel_ids) & set(nonrel_ids)  # 同時勾 👍 和 👎 視為沒標
        rel_ids = list(dict.fromkeys(d for d in rel_ids if d not in both))
        nonrel_ids = list(dict.fromkeys(d for d in nonrel_ids if d not in both))

        body = [self.search_form(q, weighting, top)]
        if q:
            body.append(self.results(q, weighting, top, apply_suggestions, rel_ids, nonrel_ids))
        return page("IR HW2 搜尋" if not q else f"{q} - IR HW2 搜尋", "".join(body))

    def results(self, q, weighting, top, apply_suggestions, rel_ids=(), nonrel_ids=()):
        started = time.perf_counter()
        try:
            results, suggestions, notes = Search.search(
                q, interactive=False, weighting=weighting, use_champion=self.champion is not None,
                top_k=top, apply_suggestions=apply_suggestions)
            use_feedback = bool(rel_ids or nonrel_ids)
            if use_feedback:
                results, added = rocchio_rerank(q, suggestions, apply_suggestions, rel_ids, nonrel_ids)
        except ValueError as error:
            return f"<div class='notice'>查詢錯誤：{html.escape(str(error))}</div>"
        elapsed = (time.perf_counter() - started) * 1000

        parts = []
        if use_feedback:
            added_text = "、".join(html.escape(t) for t, _ in added) or "(無)"
            clear = f"/?q={requests_quote(q)}&weighting={weighting}&top={top}" + ("&apply=1" if apply_suggestions else "")
            parts.append(f"<div class='notice'>相關回饋 (Rocchio α={ROCCHIO_ALPHA}, β={ROCCHIO_BETA}, γ={ROCCHIO_GAMMA})："
                         f"👍 {len(rel_ids)} 篇、👎 {len(nonrel_ids)} 篇，以 tfidf cosine 重新排序。"
                         f"加入權重最高的詞：{added_text} — <a href='{html.escape(clear)}'>清除回饋</a></div>")
        for note in notes:
            parts.append(f"<div class='notice'>萬用字元：{html.escape(note)}</div>")
        if suggestions:
            lines = "；".join(html.escape(Search.format_suggestions(t, m)) for t, m in suggestions.items())
            if apply_suggestions:
                parts.append(f"<div class='notice'>已套用拼字建議：{lines}</div>")
            else:
                link = f"/?q={requests_quote(q)}&weighting={weighting}&top={top}&apply=1"
                parts.append(f"<div class='notice'>拼字建議：{lines} — <a href='{html.escape(link)}'>改用第一個建議搜尋</a></div>")

        if use_feedback:
            mode = "tfidf cosine + Rocchio 回饋"
        else:
            mode = weighting + ("，champion list 近似計分" if self.champion is not None else "")
        parts.append(f"<div class='meta'>命中 {len(results):,} 篇，顯示前 {min(top, len(results))} 名 · "
                     f"{mode} · {elapsed:.0f} ms</div>")
        if not results:
            parts.append("<div class='empty'>找不到符合的搜尋結果。</div>")
            return "".join(parts)

        # 結果列表包在回饋表單裡：勾 👍／👎 後按按鈕，標記以 rel / nonrel 參數帶到網址，可多輪累積
        hidden = "".join(f"<input type='hidden' name='{k}' value='{html.escape(str(v), quote=True)}'>"
                         for k, v in (("q", q), ("weighting", weighting), ("top", top)))
        hidden += "<input type='hidden' name='apply' value='1'>" if apply_suggestions else ""
        submit = "<div class='fbbar'><button type='submit'>依回饋重新搜尋</button> <span class='meta'>勾選 👍 相關／👎 不相關的結果</span></div>"
        parts.append(f"<form class='feedback' action='/' method='get'>{hidden}{submit}")
        rel_set, nonrel_set = set(rel_ids), set(nonrel_ids)
        terms = query_terms_for_highlight(q, suggestions)
        for rank, (doc_id, score) in enumerate(results[:top], 1):
            doc = self.store.get(doc_id) if self.store.ready else None
            title = (doc[0] if doc and doc[0] else doc_id)
            snippet = make_snippet(doc[1], terms) if doc else ""
            link = f"/doc?id={requests_quote(doc_id)}&q={requests_quote(q)}" + ("&apply=1" if apply_suggestions else "")
            value = html.escape(doc_id, quote=True)
            votes = (f"<span class='votes'>"
                     f"<label title='相關'><input type='checkbox' name='rel' value='{value}'{' checked' if doc_id in rel_set else ''}>👍</label>"
                     f"<label title='不相關'><input type='checkbox' name='nonrel' value='{value}'{' checked' if doc_id in nonrel_set else ''}>👎</label></span>")
            parts.append(
                f"<div class='result'><span class='score'>{score:.6f}</span>"
                f"<div class='title'>{rank}. <a href='{html.escape(link)}'>{highlight(title[:120], terms)}</a></div>"
                f"<div class='id'>{html.escape(doc_id)}{votes}</div>"
                + (f"<div class='snippet'>{snippet}</div>" if snippet else "") + "</div>")
        parts.append(f"{submit}</form>{VOTE_SCRIPT}")
        if not self.store.ready:
            parts.append("<div class='meta'>(" + ("摘要尚未準備好：正在掃描 WARC 檔，稍後重新整理即可。" if self.store.available
                                                    else "找不到 WARC 檔，因此不顯示摘要。") + ")</div>")
        return "".join(parts)

    def document(self, params):
        doc_id = params.get("id", [""])[0]
        q = params.get("q", [""])[0]
        doc = self.store.get(doc_id) if self.store.ready else None
        back = f"/?q={requests_quote(q)}"
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
