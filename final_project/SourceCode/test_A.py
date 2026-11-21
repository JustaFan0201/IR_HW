import Search as S
import feedback

S.load_index()

output_lines = []

# 1. 先找出真的含有 "busi" (business 的詞幹) 的文件
busi_doc_ids = []
if "busi" in S.inverted_index:
    busi_doc_ids = list(S.inverted_index["busi"]["postings"].keys())
    output_lines.append(f"含有 'busi' 的文件數: {len(busi_doc_ids)}")
    output_lines.append(f"前 5 個文件 ID: {busi_doc_ids[:5]}")
else:
    output_lines.append("警告: 索引裡找不到 'busi' 這個詞幹！")

output_lines.append("")

# 2. 測 get_doc_vector：用一個真的含 busi 的文件
if busi_doc_ids:
    test_doc = busi_doc_ids[0]
    doc_vec = S.get_doc_vector(test_doc)
    output_lines.append(f"=== get_doc_vector('{test_doc}') ===")
    output_lines.append(f"向量維度數: {len(doc_vec)}")
    output_lines.append(f"'busi' 在此文件的權重: {doc_vec.get('busi', '不存在')}")
    # 列出權重最高的前10個詞，方便檢查
    top_terms = sorted(doc_vec.items(), key=lambda x: x[1], reverse=True)[:10]
    output_lines.append(f"權重最高前10詞: {top_terms}")
    output_lines.append("")

# 3. 測 expand_terms：用兩篇真的含 busi 的文件
if len(busi_doc_ids) >= 2:
    top_ids = busi_doc_ids[:2]
    expanded = feedback.expand_terms("business", top_ids, m=5)
    output_lines.append(f"=== expand_terms('business', {top_ids}, m=5) ===")
    output_lines.append(f"結果: {expanded}")
    output_lines.append("")

# 4. 測 rocchio：用真實數據
if busi_doc_ids:
    rel_ids = busi_doc_ids[:1]
    nonrel_ids = busi_doc_ids[1:2] if len(busi_doc_ids) > 1 else []
    query_vec = {"busi": 2.0}

    new_vec = feedback.rocchio(query_vec, rel_ids, nonrel_ids)
    output_lines.append(f"=== rocchio ===")
    output_lines.append(f"原始 query_vec: {query_vec}")
    output_lines.append(f"rel_ids: {rel_ids}")
    output_lines.append(f"nonrel_ids: {nonrel_ids}")
    output_lines.append(f"新向量 'busi' 的權重: {new_vec.get('busi', '不存在')}")
    output_lines.append(f"新向量詞數: {len(new_vec)}")
    # 檢查是否有負值或0 (理論上不該有)
    non_positive = [(t, w) for t, w in new_vec.items() if w <= 0]
    output_lines.append(f"是否有 <=0 的權重殘留 (應該是空的 []): {non_positive}")
    output_lines.append(f"新向量前10項: {list(new_vec.items())[:10]}")

# 寫入檔案
with open("test_A_output.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))

print("測試結果已寫入 test_A_output.txt")