"""查詢端文字分析：與 HW1 的 Solr 索引分析鏈保持一致。

HW1 的 custom_text_type (見 hw1/SourceCode/SetupSchema.py)：
    StandardTokenizer -> LowerCase -> StopFilter(lang/stopwords_en.txt) -> PorterStem
這裡用純 Python 重現同一條鏈，查詢詞才能對上索引裡的詞。
"""
import re

from nltk.stem.porter import PorterStemmer

# Solr lang/stopwords_en.txt 的實際內容 (35 個詞，含檔案裡的 stopworda / stopwordb)
STOPWORDS = frozenset(
    "stopworda stopwordb a an and are as at be but by for if in into is it no not "
    "of on or such that the their then there these they this to was will with".split()
)

# 近似 Unicode UAX#29 (StandardTokenizer)：
#   - 英數字連續段為一個 token；字母間可夾 ' . : ，數字間可夾 , .
#   - 連字號、斜線等其他標點視為分隔 ("non-profit" -> non, profit)
_ALNUM = r"[^\W_]+"
_TOKEN_RE = re.compile(rf"{_ALNUM}(?:['’.:,]{_ALNUM})*|\w+")

# Lucene 的 PorterStemFilter 採用原始 Porter 演算法
_stemmer = PorterStemmer(mode=PorterStemmer.ORIGINAL_ALGORITHM)
_stem_cache = {}


def _stem(token):
    stemmed = _stem_cache.get(token)
    if stemmed is None:
        stemmed = _stem_cache[token] = _stemmer.stem(token)
    return stemmed


def analyze_positions(text):
    """回傳 [(詞, 位置)]。位置照切詞順序編號，停用詞佔位但不輸出，
    與 HW1 索引一致 (移除停用詞後位置不重新編號)，phrase 查詢才對得上。"""
    items = []
    for position, token in enumerate(_TOKEN_RE.findall(text)):
        token = token.lower()
        if token in STOPWORDS:
            continue
        items.append((_stem(token), position))
    return items


def analyze(text):
    """回傳經過 切詞 -> 轉小寫 -> 去停用詞 -> 詞幹還原 的詞串列。"""
    return [term for term, _ in analyze_positions(text)]
