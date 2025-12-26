"""
比较 inchikeys_with_smiles.csv 和 bace.csv 中的 SMILES 重合情况
支持考虑立体化学差异的比较
"""
import pandas as pd
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def remove_stereochemistry(smiles):
    """
    去除SMILES中的立体化学标记
    """
    # 去除常见的立体化学标记
    stereo_markers = ['@', '/', '\\']
    cleaned = smiles
    for marker in stereo_markers:
        cleaned = cleaned.replace(marker, '')
    return cleaned

def canonicalize_simple(smiles):
    """
    简单的SMILES规范化（不使用RDKit）
    """
    # 去除空格
    cleaned = smiles.strip()
    # 去除立体化学
    cleaned = remove_stereochemistry(cleaned)
    return cleaned

def try_rdkit_canonicalize(smiles):
    """
    尝试使用RDKit进行更严格的规范化
    """
    try:
        from rdkit import Chem
        mol = Chem.MolFromSmiles(smiles)
        if mol is not None:
            # 去除立体化学信息
            Chem.RemoveStereochemistry(mol)
            return Chem.MolToSmiles(mol)
        return None
    except ImportError:
        logging.warning("未安装RDKit，使用简单字符串比较")
        return None
    except:
        return None

def main():
    # 检查文件是否存在
    file1 = Path("inchikeys_with_smiles.csv")
    file2 = Path("bace.csv")
    
    if not file1.exists():
        logging.error(f"错误: 找不到文件 {file1}")
        return
    
    if not file2.exists():
        logging.error(f"错误: 找不到文件 {file2}")
        return
    
    # 读取两个文件
    logging.info(f"正在读取 {file1}...")
    df1 = pd.read_csv(file1)
    
    logging.info(f"正在读取 {file2}...")
    df2 = pd.read_csv(file2)
    
    # 提取SMILES
    smiles1 = set(df1['SMILES'].dropna().unique())
    logging.info(f"inchikeys_with_smiles.csv 中有 {len(smiles1)} 个唯一的SMILES")
    
    # 提取 bace.csv 中 Class=1 的 SMILES
    df2_class1 = df2[df2['Class'] == 1]
    smiles2 = set(df2_class1['mol'].dropna().unique())
    logging.info(f"bace.csv 中 Class=1 的有 {len(smiles2)} 个唯一的SMILES")
    
    # 方法1: 直接字符串匹配
    logging.info("\n" + "="*60)
    logging.info("方法1: 直接SMILES字符串匹配")
    logging.info("="*60)
    
    direct_matches = smiles1.intersection(smiles2)
    logging.info(f"直接匹配数量: {len(direct_matches)}")
    
    # 方法2: 去除立体化学后匹配
    logging.info("\n" + "="*60)
    logging.info("方法2: 去除立体化学标记后匹配")
    logging.info("="*60)
    
    # 创建映射：规范化SMILES -> 原始SMILES列表
    map1 = {}
    for s in smiles1:
        canonical = canonicalize_simple(s)
        if canonical not in map1:
            map1[canonical] = []
        map1[canonical].append(s)
    
    map2 = {}
    for s in smiles2:
        canonical = canonicalize_simple(s)
        if canonical not in map2:
            map2[canonical] = []
        map2[canonical].append(s)
    
    # 找到匹配的规范化SMILES
    canonical_matches = set(map1.keys()).intersection(set(map2.keys()))
    
    # 统计总匹配数（考虑一对多的情况）
    total_matches = 0
    match_details = []
    
    for canonical in canonical_matches:
        smiles1_list = map1[canonical]
        smiles2_list = map2[canonical]
        
        for s1 in smiles1_list:
            for s2 in smiles2_list:
                total_matches += 1
                match_details.append({
                    'SMILES_from_inchikeys': s1,
                    'SMILES_from_bace': s2,
                    'Canonical': canonical,
                    'Exact_Match': s1 == s2
                })
    
    logging.info(f"规范化后匹配的唯一结构数: {len(canonical_matches)}")
    logging.info(f"总匹配对数: {total_matches}")
    
    # 方法3: 尝试使用RDKit进行更严格的匹配
    try:
        from rdkit import Chem
        
        logging.info("\n" + "="*60)
        logging.info("方法3: 使用RDKit规范化SMILES（去除立体化学）")
        logging.info("="*60)
        
        # 创建RDKit规范化映射
        rdkit_map1 = {}
        rdkit_map2 = {}
        
        for s in smiles1:
            canonical = try_rdkit_canonicalize(s)
            if canonical:
                if canonical not in rdkit_map1:
                    rdkit_map1[canonical] = []
                rdkit_map1[canonical].append(s)
        
        for s in smiles2:
            canonical = try_rdkit_canonicalize(s)
            if canonical:
                if canonical not in rdkit_map2:
                    rdkit_map2[canonical] = []
                rdkit_map2[canonical].append(s)
        
        rdkit_matches = set(rdkit_map1.keys()).intersection(set(rdkit_map2.keys()))
        
        logging.info(f"RDKit规范化后匹配的唯一结构数: {len(rdkit_matches)}")
        
        # 保存RDKit匹配详情
        rdkit_details = []
        for canonical in rdkit_matches:
            for s1 in rdkit_map1[canonical]:
                for s2 in rdkit_map2[canonical]:
                    rdkit_details.append({
                        'SMILES_from_inchikeys': s1,
                        'SMILES_from_bace': s2,
                        'Canonical_SMILES': canonical,
                        'Exact_Match': s1 == s2
                    })
        
        # 保存RDKit结果
        if rdkit_details:
            df_rdkit_matches = pd.DataFrame(rdkit_details)
            output_rdkit = Path("smiles_matches_rdkit.csv")
            df_rdkit_matches.to_csv(output_rdkit, index=False)
            logging.info(f"RDKit匹配详情已保存到: {output_rdkit}")
    
    except ImportError:
        logging.warning("未安装RDKit，跳过方法3")
    
    # 保存匹配详情
    if match_details:
        df_matches = pd.DataFrame(match_details)
        output_file = Path("smiles_matches.csv")
        df_matches.to_csv(output_file, index=False)
        logging.info(f"\n匹配详情已保存到: {output_file}")
        
        # 统计完全相同的匹配
        exact_matches = df_matches[df_matches['Exact_Match'] == True]
        logging.info(f"其中完全相同的SMILES: {len(exact_matches)}")
        logging.info(f"仅结构相同但有立体化学差异的: {len(df_matches) - len(exact_matches)}")
    
    # 显示一些示例
    logging.info("\n" + "="*60)
    logging.info("匹配示例（前5个）:")
    logging.info("="*60)
    
    if match_details:
        for i, detail in enumerate(match_details[:5], 1):
            logging.info(f"\n示例 {i}:")
            logging.info(f"  inchikeys文件: {detail['SMILES_from_inchikeys']}")
            logging.info(f"  bace文件:      {detail['SMILES_from_bace']}")
            logging.info(f"  完全相同:      {detail['Exact_Match']}")
    
    # 总结
    logging.info("\n" + "="*60)
    logging.info("总结")
    logging.info("="*60)
    logging.info(f"inchikeys_with_smiles.csv: {len(smiles1)} 个SMILES")
    logging.info(f"bace.csv (Class=1):        {len(smiles2)} 个SMILES")
    logging.info(f"直接字符串匹配:           {len(direct_matches)} 个")
    logging.info(f"去除立体化学后匹配:       {len(canonical_matches)} 个结构")
    
    # 计算重合率
    overlap_rate = len(canonical_matches) / len(smiles1) * 100 if smiles1 else 0
    logging.info(f"重合率（基于inchikeys）:   {overlap_rate:.2f}%")

if __name__ == "__main__":
    main()


