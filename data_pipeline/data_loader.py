import pandas as pd
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def _find_entrez_ids_via_path(icd11_code, config, id_map_file, target_map_file, id_col, id_name):
    """辅助函数：通过单一通路查找EntrezID"""
    entrez_ids = set()
    try:
        # 1. ICD11 -> 中间ID (CUI/MeSH/DOID)
        id_map_path = config.TCM_DATA_ROOT / id_map_file
        logging.info(f"[{id_name} Path] 正在读取ICD映射文件: {id_map_path}")
        df_id_map = pd.read_csv(id_map_path, sep='\t', usecols=[config.ICD11_CODE_COL, id_col], dtype=str)
        intermediate_ids = df_id_map[df_id_map[config.ICD11_CODE_COL] == icd11_code][id_col].unique()

        if len(intermediate_ids) == 0:
            logging.warning(f"[{id_name} Path] 未找到 ICD11 '{icd11_code}' 对应的 {id_name}。")
            return entrez_ids
        logging.info(f"[{id_name} Path] 找到 {len(intermediate_ids)} 个相关 {id_name}。")

        # 2. 中间ID -> EntrezID
        target_map_path = config.TCM_DATA_ROOT / target_map_file
        logging.info(f"[{id_name} Path] 正在读取靶点映射文件: {target_map_path}")
        df_target_map = pd.read_csv(target_map_path, sep='\t', usecols=[id_col, config.ENTREZ_ID_COL], dtype=str)
        found_entrez_ids = df_target_map[df_target_map[id_col].isin(intermediate_ids)][config.ENTREZ_ID_COL].unique()
        
        if len(found_entrez_ids) > 0:
            logging.info(f"[{id_name} Path] 找到 {len(found_entrez_ids)} 个相关 EntrezID。")
            entrez_ids.update(found_entrez_ids)

    except FileNotFoundError as e:
        logging.error(f"[{id_name} Path] 数据文件未找到: {e}")
    except Exception as e:
        logging.error(f"[{id_name} Path] 处理过程中发生错误: {e}")
        
    return entrez_ids


def find_positive_samples(icd11_code: str, config) -> pd.DataFrame:
    """
    根据给定的ICD11代码，通过CUI, MeSH, DOID三条通路查找关联的化合物InChIKeys（正样本）。
    """
    logging.info(f"开始为ICD11代码 '{icd11_code}' 通过三通路模型查找正样本...")

    # --- 兵分三路查找EntrezID ---
    entrez_ids_cui = _find_entrez_ids_via_path(
        icd11_code, config, config.DISEASE_ICD11_FILE, config.CUI_TARGETS_FILE, config.CUI_COL, "CUI"
    )
    entrez_ids_mesh = _find_entrez_ids_via_path(
        icd11_code, config, config.ICD11_MESH_FILE, config.MESH_TARGETS_FILE, config.MESH_COL, "MeSH"
    )
    entrez_ids_doid = _find_entrez_ids_via_path(
        icd11_code, config, config.ICD11_DOID_FILE, config.DOID_TARGETS_FILE, config.DOID_COL, "DOID"
    )
    
    # --- 合并EntrezID并集 ---
    all_entrez_ids = entrez_ids_cui.union(entrez_ids_mesh).union(entrez_ids_doid)
    if not all_entrez_ids:
        logging.error("所有通路均未找到任何相关的EntrezID，流程终止。")
        return pd.DataFrame({config.INCHIKEY_COL: []})
    logging.info(f"通过所有通路共找到 {len(all_entrez_ids)} 个独特的EntrezID。")

    # --- EntrezID -> InChIKey ---
    try:
        d13_path = config.TCM_DATA_ROOT / config.INCHIKEY_ENTREZ_FILE
        logging.info(f"正在从 {d13_path} 中查找与 {len(all_entrez_ids)} 个EntrezID相关的InChIKey...")
        
        chunk_size = 1_000_000 
        inchikey_list = []
        
        with pd.read_csv(d13_path, sep='\t', usecols=[config.INCHIKEY_COL, config.ENTREZ_ID_COL], chunksize=chunk_size, dtype=str) as reader:
            for chunk in reader:
                matches = chunk[chunk[config.ENTREZ_ID_COL].isin(all_entrez_ids)]
                if not matches.empty:
                    inchikey_list.extend(matches[config.INCHIKEY_COL].tolist())
        
        unique_inchikeys = list(set(inchikey_list))
        
        if not unique_inchikeys:
            logging.warning("未找到与EntrezID相关联的InChIKey。")
            return pd.DataFrame({config.INCHIKEY_COL: []})

        logging.info(f"成功找到 {len(unique_inchikeys)} 个独特的InChIKey作为正样本。")
        return pd.DataFrame(unique_inchikeys, columns=[config.INCHIKEY_COL])

    except FileNotFoundError as e:
        logging.error(f"数据文件未找到: {e}")
        return pd.DataFrame({config.INCHIKEY_COL: []})
    except Exception as e:
        logging.error(f"在查找InChIKey过程中发生未知错误: {e}")
        return pd.DataFrame({config.INCHIKEY_COL: []})

def find_positive_samples_by_entrez(all_entrez_ids: set, config) -> pd.DataFrame:
    """
    根据给定的EntrezID集合，查找关联的化合物InChIKeys（正样本）。
    """
    if not all_entrez_ids:
        logging.error("输入的EntrezID集合为空，流程终止。")
        return pd.DataFrame({config.INCHIKEY_COL: []})
    logging.info(f"接收到 {len(all_entrez_ids)} 个独特的EntrezID，开始查找正样本...")

    # --- EntrezID -> InChIKey ---
    try:
        d13_path = config.TCM_DATA_ROOT / config.INCHIKEY_ENTREZ_FILE
        logging.info(f"正在从 {d13_path} 中查找与 {len(all_entrez_ids)} 个EntrezID相关的InChIKey...")
        
        chunk_size = 1_000_000 
        inchikey_list = []
        
        with pd.read_csv(d13_path, sep='\t', usecols=[config.INCHIKEY_COL, config.ENTREZ_ID_COL], chunksize=chunk_size, dtype=str) as reader:
            for chunk in reader:
                matches = chunk[chunk[config.ENTREZ_ID_COL].isin(all_entrez_ids)]
                if not matches.empty:
                    inchikey_list.extend(matches[config.INCHIKEY_COL].tolist())
        
        unique_inchikeys = list(set(inchikey_list))
        
        if not unique_inchikeys:
            logging.warning("未找到与EntrezID相关联的InChIKey。")
            return pd.DataFrame({config.INCHIKEY_COL: []})

        logging.info(f"成功找到 {len(unique_inchikeys)} 个独特的InChIKey作为正样本。")
        return pd.DataFrame(unique_inchikeys, columns=[config.INCHIKEY_COL])

    except FileNotFoundError as e:
        logging.error(f"数据文件未找到: {e}")
        return pd.DataFrame({config.INCHIKEY_COL: []})
    except Exception as e:
        logging.error(f"在查找InChIKey过程中发生未知错误: {e}")
        return pd.DataFrame({config.INCHIKEY_COL: []}) 