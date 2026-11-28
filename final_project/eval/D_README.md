# 模組 D：評估與語言模型

| 檔案 | 功能 |
|---|---|
| `LMSearch.py` | Query likelihood + Dirichlet 平滑（`search_lm(query, k, mu)`，預設 mu=1000） |
| `Evaluate.py` | `evaluate(run, qrels)` → P@10、MAP、nDCG@10、Unjudged@10；執行本檔會跑公式自我檢查 |
| `Methods.py` | 所有方案統一成 `fn(query, k) -> [(doc, score)]`；A、C 以 `METHODS = {...}` 掛上來 |
| `Pooling.py` | pooling、互動標註、CSV 匯出/合併、標註進度 |
| `RunExperiments.py` | 比較表、依查詢類型拆分、逐查詢結果、顯著性檢定、mu 掃描、長條圖、TREC run 檔 |

## 流程
```bash
python SourceCode/Pooling.py annotate --methods tfidf bm25 --depth 20        # 或 export / merge 用試算表分工
python SourceCode/Pooling.py status
python SourceCode/RunExperiments.py                                           # baseline
python SourceCode/RunExperiments.py --sweep-mu 100 500 1000 2000 5000
python SourceCode/RunExperiments.py --plugins SemanticSearch Feedback         # A、C 完成後
```
新方法加入後先用 `Pooling.py annotate --methods ... --plugins ...` 補標（只會問沒標過的），再重跑實驗。

## 標註準則
2 = 頁面主要內容就是該主題；1 = 部分相關；0 = 不相關。多義詞（ambiguous）任何一種意思只要頁面主要談它就算相關。
qrels 為 TREC 格式 `qid 0 docID rel`；標錯時在檔尾補同 qid／docID 的新行即可（後面的覆蓋前面的）。

## 方法定義重點
- 未標註文件視為不相關；R=0 的查詢不納入平均；MAP 看前 100 名；nDCG gain = 2^rel − 1
- LM 計分用與原式排名等價的形式，分數是相對值，不能和其他方案的分數直接比
- 調參與報告用同一份 qrels 會偏樂觀，報告中請說明
