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
python SourceCode/RunExperiments.py --plugins semantic                         # C 完成後 (模組檔名，不含 .py)；A 的 feedback.py 加上 METHODS 後再加 feedback
```
新方法加入後先用 `Pooling.py annotate --methods ... --plugins ...` 補標（只會問沒標過的），再重跑實驗。

## 標註準則
2 = 頁面主要內容就是該主題；1 = 部分相關；0 = 不相關。多義詞（ambiguous）任何一種意思只要頁面主要談它就算相關。
qrels 為 TREC 格式 `qid 0 docID rel`；標錯時在檔尾補同 qid／docID 的新行即可（後面的覆蓋前面的）。
手動補行時不必擔心結尾有沒有換行（程式寫入前會補）；格式不對的行載入時會印出警告與行號。

## 方法定義重點
- 未標註文件視為不相關；R=0 的查詢不納入平均；方法沒有回傳結果的查詢算 0 分（仍在分母內）；MAP 看前 100 名；nDCG gain = 2^rel − 1
- `--plugins` 載入失敗、模組沒有 `METHODS`、`--methods`／`--baseline` 打錯，都會直接報錯結束；`--baseline` 預設是 bm25（在比較名單中才做檢定）
- 顯著性 p 值為 (極端次數+1)/(次數+1)，最小約 0.0001；mu 必須大於 0
- `Pooling.py` 的 `--queries` 對 annotate／export／status 都有效；merge 會先檢查完所有 CSV 再一次寫入，支援 Excel 另存的 cp950 檔
- LM 計分用與原式排名等價的形式，分數是相對值，不能和其他方案的分數直接比
- 調參與報告用同一份 qrels 會偏樂觀，報告中請說明
- `RunExperiments.py --queries 別組.txt` 搭配完整 qrels 時，只評估該查詢檔裡的查詢（qrels 其他 qid 不算 0 分）
- `eval_queries.txt` 用 tab 分隔；編輯器轉成空格時，兩個以上連續空白也能切，否則會指出第幾行格式不對
- `Pooling.py merge` 不受 `--queries` 影響；標註時的文件內容讀取優先用 `docs.DocStore`，沒有才退回 `WebApp.DocStore`
- plugin 回傳 `(doc, score)` tuple 或 `[doc, score]` list 皆可（`Methods.register` 會統一格式）；mu 必須是大於 0 的有限數字
