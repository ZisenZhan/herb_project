import argparse
import pandas as pd
from pathlib import Path
import config
import logging

# --- 日志配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_data(file_path, usecols=None, sep='\t'):
    """安全地加载TSV数据"""
    try:
        df = pd.read_csv(file_path, sep=sep, usecols=usecols, low_memory=False)
        logging.info(f"成功加载文件: {file_path}")
        return df
    except FileNotFoundError:
        logging.error(f"错误: 文件未找到 {file_path}")
        return None
    except Exception as e:
        logging.error(f"加载文件 {file_path} 时出错: {e}")
        return None

def trace_targets(inchikey: str, icd_codes: list[str]):
    """
    根据InChIKey和ICD编码追溯共同的靶点。
    """
    report = []
    report.append(f"===== 靶点追溯报告 =====")
    report.append(f"输入 InChIKey: {inchikey}")
    report.append(f"输入 ICD 编码: {', '.join(icd_codes)}")
    report.append("=" * 50)

    # --- 1. 查找化合物的靶点 ---
    report.append("\n--- 步骤 1: 查找化合物靶点 ---")
    df_inchi_entrez = load_data(config.TCM_DATA_ROOT / config.INCHIKEY_ENTREZ_FILE, usecols=[config.INCHIKEY_COL, config.ENTREZ_ID_COL])
    if df_inchi_entrez is None:
        report.append("错误: 无法加载化合物-靶点数据，流程终止。")
        return "\\n".join(report)
        
    compound_targets_df = df_inchi_entrez[df_inchi_entrez[config.INCHIKEY_COL] == inchikey]
    compound_targets = set(compound_targets_df[config.ENTREZ_ID_COL].unique())
    
    report.append(f"从 {config.INCHIKEY_ENTREZ_FILE} 中找到 {len(compound_targets)} 个与 {inchikey} 相关的靶点:")
    report.append(f"  -> 靶点 (EntrezIDs): {compound_targets if compound_targets else '无'}")

    # --- 2. 查找疾病的靶点 ---
    report.append("\n--- 步骤 2: 查找疾病相关靶点 ---")
    
    # a. ICD -> CUI/MeSH/DOID
    df_icd_cui = load_data(config.TCM_DATA_ROOT / config.DISEASE_ICD11_FILE, usecols=[config.ICD11_CODE_COL, config.CUI_COL])
    df_icd_mesh = load_data(config.TCM_DATA_ROOT / config.ICD11_MESH_FILE, usecols=[config.ICD11_CODE_COL, config.MESH_COL])
    df_icd_doid = load_data(config.TCM_DATA_ROOT / config.ICD11_DOID_FILE, usecols=[config.ICD11_CODE_COL, config.DOID_COL])

    disease_cuis = set(df_icd_cui[df_icd_cui[config.ICD11_CODE_COL].isin(icd_codes)][config.CUI_COL].unique()) if df_icd_cui is not None else set()
    disease_meshes = set(df_icd_mesh[df_icd_mesh[config.ICD11_CODE_COL].isin(icd_codes)][config.MESH_COL].unique()) if df_icd_mesh is not None else set()
    disease_doids = set(df_icd_doid[df_icd_doid[config.ICD11_CODE_COL].isin(icd_codes)][config.DOID_COL].unique()) if df_icd_doid is not None else set()
    
    report.append("ICD 编码到医学概念的映射:")
    report.append(f"  - CUI: {disease_cuis if disease_cuis else '无'}")
    report.append(f"  - MeSH: {disease_meshes if disease_meshes else '无'}")
    report.append(f"  - DOID: {disease_doids if disease_doids else '无'}")

    # b. CUI/MeSH/DOID -> EntrezID
    df_cui_target = load_data(config.TCM_DATA_ROOT / config.CUI_TARGETS_FILE, usecols=[config.CUI_COL, config.ENTREZ_ID_COL])
    df_mesh_target = load_data(config.TCM_DATA_ROOT / config.MESH_TARGETS_FILE, usecols=[config.MESH_COL, config.ENTREZ_ID_COL])
    df_doid_target = load_data(config.TCM_DATA_ROOT / config.DOID_TARGETS_FILE, usecols=[config.DOID_COL, config.ENTREZ_ID_COL])

    disease_targets = set()
    if df_cui_target is not None and disease_cuis:
        targets = set(df_cui_target[df_cui_target[config.CUI_COL].isin(disease_cuis)][config.ENTREZ_ID_COL].unique())
        disease_targets.update(targets)
    if df_mesh_target is not None and disease_meshes:
        targets = set(df_mesh_target[df_mesh_target[config.MESH_COL].isin(disease_meshes)][config.ENTREZ_ID_COL].unique())
        disease_targets.update(targets)
    if df_doid_target is not None and disease_doids:
        targets = set(df_doid_target[df_doid_target[config.DOID_COL].isin(disease_doids)][config.ENTREZ_ID_COL].unique())
        disease_targets.update(targets)

    report.append(f"\n从疾病相关概念中找到 {len(disease_targets)} 个总靶点:")
    report.append(f"  -> 靶点 (EntrezIDs): {disease_targets if disease_targets else '无'}")

    # --- 3. 取交集 ---
    report.append("\n--- 步骤 3: 查找共同靶点 ---")
    common_targets = compound_targets.intersection(disease_targets)
    
    if common_targets:
        report.append(f"成功找到 {len(common_targets)} 个共同靶点！")
        report.append(f"  -> 共同靶点 (EntrezID): {common_targets}")
        report.append("\n详细追溯路径:")
        for target in common_targets:
            report.append(f"  - 靶点 {target}:")
            report.append(f"    - 来源于化合物 {inchikey}")
            # 追溯疾病来源
            source_info = []
            if df_cui_target is not None and target in df_cui_target[config.ENTREZ_ID_COL].values:
                cuis = df_cui_target[df_cui_target[config.ENTREZ_ID_COL] == target][config.CUI_COL]
                source_info.append(f"通过CUI {list(cuis)}")
            if df_mesh_target is not None and target in df_mesh_target[config.ENTREZ_ID_COL].values:
                meshes = df_mesh_target[df_mesh_target[config.ENTREZ_ID_COL] == target][config.MESH_COL]
                source_info.append(f"通过MeSH {list(meshes)}")
            if df_doid_target is not None and target in df_doid_target[config.ENTREZ_ID_COL].values:
                doids = df_doid_target[df_doid_target[config.ENTREZ_ID_COL] == target][config.DOID_COL]
                source_info.append(f"通过DOID {list(doids)}")
            report.append(f"    - 来源于疾病（ICD: {', '.join(icd_codes)}），关联路径: {' | '.join(source_info)}")
    else:
        report.append("未找到任何共同靶点。")
        
    report.append("\n" + "=" * 50)
    report.append("报告结束。")
    return "\\n".join(report)

def main():
    parser = argparse.ArgumentParser(description="根据给定的InChIKey和ICD编码，追溯其共同的基因靶点。")
    parser.add_argument("--inchikey", type=str, required=True, help="要查询的化合物的InChIKey。")
    parser.add_argument("--icd", type=str, required=True, help="一个或多个ICD-11编码，用逗号分隔。")
    parser.add_argument("--output", type=str, help="将报告保存到的可选输出文件名。")
    
    args = parser.parse_args()
    
    icd_codes = [code.strip() for code in args.icd.split(',')]
    
    report_content = trace_targets(args.inchikey, icd_codes)
    
    print(report_content)
    
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        logging.info(f"报告已保存至: {output_path}")

if __name__ == "__main__":
    main()
