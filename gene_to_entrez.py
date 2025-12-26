"""
gene_to_entrez.py - 将基因名称(Gene Symbol)转换为EntrezID
"""
import requests
import pandas as pd

def gene_symbols_to_entrez(gene_symbols: list, species: str = "human") -> pd.DataFrame:
    """
    将基因符号列表转换为EntrezID
    
    参数:
        gene_symbols: 基因符号列表，如 ["TP53", "EGFR", "BRCA1"]
        species: 物种，默认 "human"，也可以是 "mouse", "rat" 等
    
    返回:
        DataFrame 包含 symbol, entrezgene, name 等信息
    """
    url = "https://mygene.info/v3/query"
    
    results = []
    
    # 批量查询（每次最多1000个）
    batch_size = 1000
    for i in range(0, len(gene_symbols), batch_size):
        batch = gene_symbols[i:i+batch_size]
        
        params = {
            "q": ",".join(batch),
            "scopes": "symbol,alias",  # 搜索symbol和别名
            "fields": "entrezgene,symbol,name,taxid",
            "species": species,
            "size": len(batch)
        }
        
        response = requests.post(url, data=params)
        data = response.json()
        
        for item in data:
            if isinstance(item, dict):
                results.append({
                    "query": item.get("query", ""),
                    "symbol": item.get("symbol", ""),
                    "entrezgene": item.get("entrezgene", None),
                    "name": item.get("name", ""),
                    "found": "notfound" not in item
                })
    
    return pd.DataFrame(results)


if __name__ == "__main__":
    # 示例：你的基因名称列表
    gene_list = ["TP53", "CDKN2A", "EGFR", "PIK3CA", "PTEN", "ING1", "CCND1", "STAT3", "IL2"]

    
    print("正在查询基因信息...")
    df = gene_symbols_to_entrez(gene_list)
    
    # 显示结果
    print("\n查询结果：")
    print(df.to_string(index=False))
    
    # 保存到CSV
    df.to_csv("gene_to_entrez_mapping.csv", index=False)
    print("\n结果已保存到 gene_to_entrez_mapping.csv")
    
    # 提取EntrezID用于main.py
    valid_ids = df[df['entrezgene'].notna()]['entrezgene'].astype(int).tolist()
    entrez_str = ",".join(map(str, valid_ids))
    print(f"\n可用于 main.py 的 EntrezID 字符串：")
    print(f'python main.py --entrez_ids "{entrez_str}"')