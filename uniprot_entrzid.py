import requests
import csv
import io
import time
from typing import List, Dict, Optional

UNIPROT_SEARCH_URL = "https://rest.uniprot.org/uniprotkb/search"

def chunked(lst, n):
    """将列表分割成大小为n的块"""
    for i in range(0, len(lst), n):
        yield lst[i:i+n]

def build_query(ids: List[str]) -> str:
    """构建UniProt查询字符串"""
    parts = [f"accession:{i}" for i in ids]
    return " OR ".join(parts)

def fetch_mapping_batch(ids: List[str], retries: int = 3, backoff: float = 1.5) -> Dict[str, Optional[str]]:
    """
    批量获取UniProt ID到Entrez Gene ID的映射
    返回 {uniprot_id: entrez_gene_id or None}
    若一个条目对应多个GeneID，则以分号连接
    """
    params = {
        "query": build_query(ids),
        "fields": "accession,xref_geneid",
        "format": "tsv",
        "size": 500  # 单次最多返回行数
    }
    
    for attempt in range(retries):
        try:
            r = requests.get(UNIPROT_SEARCH_URL, params=params, timeout=30)
            r.raise_for_status()
            text = r.text
            
            # 解析TSV
            reader = csv.DictReader(io.StringIO(text), delimiter='\t')
            out = {i: None for i in ids}
            
            for row in reader:
                acc = row.get("Entry") or row.get("accession")
                geneids = row.get("GeneID", "") or row.get("xref_geneid", "")
                geneids = geneids.strip()
                
                if acc in out:
                    out[acc] = geneids if geneids else None
            
            return out
        except Exception as e:
            if attempt == retries - 1:
                # 最后一次仍失败：整批置为None
                return {i: None for i in ids}
            time.sleep(backoff ** attempt)

def map_uniprot_to_entrez(uniprot_ids: List[str], batch_size: int = 200, sleep_between: float = 0.2) -> Dict[str, Optional[str]]:
    """
    批量映射UniProt ID到Entrez Gene ID
    返回字典：{ 'Q9H3K2': '1017', 'P04637': '1956;1957', 'BADID': None, ... }
    """
    ids = [i.strip() for i in uniprot_ids if i and i.strip()]
    result: Dict[str, Optional[str]] = {i: None for i in ids}
    
    for batch in chunked(ids, batch_size):
        batch_res = fetch_mapping_batch(batch)
        for k, v in batch_res.items():
            result[k] = v
        time.sleep(sleep_between)  # 礼貌性限速，避免429错误
    
    return result

if __name__ == "__main__":
    # 示例：单个或多个UniProt ID
    example_ids = [
        # "P00533",   # EGFR
        # "P04637",   # TP53
        # "Q9H3K2",   # 示例
        "Q12888",
        "P04637"
    ]
    
    mapping = map_uniprot_to_entrez(example_ids)
    
    print("UniProt ID\tEntrez Gene ID")
    print("-" * 40)
    for uid, gid in mapping.items():
        print(f"{uid}\t{gid or 'Not found'}")
