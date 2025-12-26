#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
smiles_canon_compare.py
用法：
  1) 直接在命令行传入： 
     python smiles_canon_compare.py -s "CN1C(N)=NC(C)(c2cc(NC(=O)c3ccc(F)cn3)ccc2F)CS1(=O)=O" \
                                    -s "CC1(CS(=O)(=O)N(C(=N1)N)C)C2=C(C=CC(=C2)NC(=O)C3=NC=C(C=C3)F)F"
  2) 从文件读入（每行一个 SMILES）：
     python smiles_canon_compare.py --file smiles.txt
"""
import argparse
from typing import List, Tuple, Optional

def try_import_rdkit():
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
        from rdkit.Chem import rdMolDescriptors as Descriptors
        from rdkit.Chem import inchi as rdInchi
        return Chem, AllChem, Descriptors, rdInchi
    except Exception as e:
        return None, None, None, None

def canon_with_rdkit(smiles: str, Chem, AllChem, Descriptors, rdInchi) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """返回 (canonical_smiles, inchi, inchikey)，解析失败则全 None"""
    try:
        mol = Chem.MolFromSmiles(smiles, sanitize=True)
        if mol is None:
            return None, None, None
        # 生成 canonical SMILES（RDKit 默认 canonical=True）
        cano = Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)
        # InChI / InChIKey（若 RDKit 编译时未带 InChI，会抛异常）
        try:
            inchi = rdInchi.MolToInchi(mol)
            inchikey = rdInchi.MolToInchiKey(mol)
        except Exception:
            inchi, inchikey = None, None
        return cano, inchi, inchikey
    except Exception:
        return None, None, None

def compare_strings(a: Optional[str], b: Optional[str]) -> str:
    if a is None or b is None:
        return "N/A"
    return "==" if a == b else "!="

def make_pairwise_matrix(rows: List[str]) -> List[List[str]]:
    n = len(rows)
    mat = [["" for _ in range(n+1)] for _ in range(n+1)]
    mat[0][0] = "#"
    for i in range(n):
        mat[0][i+1] = f"S{i+1}"
        mat[i+1][0] = f"S{i+1}"
    for i in range(n):
        for j in range(n):
            mat[i+1][j+1] = compare_strings(rows[i], rows[j])
    return mat

def print_table(table: List[List[str]]):
    colw = [max(len(str(x)) for x in col) for col in zip(*table)]
    for r in table:
        line = "  ".join(str(x).ljust(w) for x, w in zip(r, colw))
        print(line)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--smiles", action="append", help="输入的 SMILES，可重复使用 -s 多次", default=[])
    parser.add_argument("--file", help="包含 SMILES 的文本文件（每行一个）")
    args = parser.parse_args()

    inputs: List[str] = []
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    inputs.append(line)
    inputs.extend(args.smiles)

    if not inputs:
        print("未提供 SMILES。请用 -s 或 --file 提供输入。")
        return

    Chem, AllChem, Descriptors, rdInchi = try_import_rdkit()
    if Chem is None:
        print("未检测到 RDKit。请先安装：pip install rdkit-pypi")
        return

    records = []
    for idx, s in enumerate(inputs, 1):
        cano, inchi, inchikey = canon_with_rdkit(s, Chem, AllChem, Descriptors, rdInchi)
        records.append({
            "id": f"S{idx}",
            "input": s,
            "canonical_smiles": cano,
            "inchi": inchi,
            "inchikey": inchikey
        })

    # 展示结果
    print("\n=== 规范化结果 ===")
    for r in records:
        print(f"[{r['id']}]")
        print(f"Input:            {r['input']}")
        print(f"Canonical SMILES: {r['canonical_smiles']}")
        print(f"InChIKey:         {r['inchikey']}")
        if r["inchi"]:
            print(f"InChI:            {r['inchi']}")
        print("-" * 60)

    # 基于 InChIKey 对比（若不可用，回退到 canonical SMILES）
    keys = [r["inchikey"] or r["canonical_smiles"] for r in records]
    print("\n=== 两两对比矩阵（相等为 '==', 不等为 '!='） ===")
    print("（优先用 InChIKey；若无则使用 Canonical SMILES）")
    mat = make_pairwise_matrix(keys)
    print_table(mat)

    # 去重
    seen = {}
    for r in records:
        k = r["inchikey"] or r["canonical_smiles"]
        seen.setdefault(k, []).append(r["id"])
    print("\n=== 去重分组（同组表示为同一分子） ===")
    for i, (k, ids) in enumerate(seen.items(), 1):
        print(f"Group {i}: {', '.join(ids)}")

if __name__ == "__main__":
    main()
