import pandas as pd
import logging
from pathlib import Path
from tqdm import tqdm

# 全局变量，用于缓存从本地文件加载的SMILES查询字典
_smiles_lookup = None

def _load_smiles_lookup(config):
    """
    从本地TSV文件加载InChIKey到SMILES的映射，并将其缓存在全局变量中。
    如果已经加载，则直接返回。
    """
    global _smiles_lookup
    if _smiles_lookup is not None:
        return

    smiles_tsv_path = config.LOCAL_INCHIKEY_SMILES_TSV
    inchikey_col = config.INCHIKEY_COL
    smiles_col = config.SMILES_COL

    logging.info(f"正在从本地文件加载SMILES数据: {smiles_tsv_path}")
    if not smiles_tsv_path.exists():
        logging.error(f"SMILES数据文件未找到: {smiles_tsv_path}!")
        raise FileNotFoundError(f"SMILES数据文件未找到: {smiles_tsv_path}!")

    # 使用制表符作为分隔符读取TSV文件
    df = pd.read_csv(smiles_tsv_path, sep='\\t', header=0, usecols=[inchikey_col, smiles_col], engine='python')
    df.dropna(subset=[inchikey_col], inplace=True)
    df.drop_duplicates(subset=[inchikey_col], keep='first', inplace=True)

    # 创建查询字典并存入全局缓存
    _smiles_lookup = pd.Series(df[smiles_col].values, index=df[inchikey_col]).to_dict()
    logging.info(f"成功加载并缓存 {len(_smiles_lookup)} 条InChIKey-SMILES映射。")

def get_smiles_for_inchikeys(inchikeys_df: pd.DataFrame, config) -> pd.DataFrame:
    """
    从本地预编译的TSV文件中为给定的InChIKey获取SMILES。
    """
    inchikey_col = config.INCHIKEY_COL
    smiles_col = config.SMILES_COL
    
    # 1. 加载SMILES查询字典（如果尚未加载）
    _load_smiles_lookup(config)

    # 2. 从输入的DataFrame中获取所有唯一的InChIKey
    unique_inchikeys = inchikeys_df[inchikey_col].unique()
    
    # 3. 在内存字典中执行查找
    results = []
    for inchikey in tqdm(unique_inchikeys, desc="从本地文件获取SMILES"):
        smiles = _smiles_lookup.get(inchikey)
        if smiles is None:
            logging.warning(f"在本地文件中未找到InChIKey {inchikey} 对应的SMILES。")
        results.append({inchikey_col: inchikey, smiles_col: smiles})

    # 4. 将查询结果转换为DataFrame，并与原始DataFrame合并
    df_smiles = pd.DataFrame(results)
    df_with_smiles = pd.merge(inchikeys_df, df_smiles, on=inchikey_col, how='left')

    # 5. 报告查找结果并清理
    original_count = len(unique_inchikeys)
    found_count = df_with_smiles[smiles_col].notna().sum()
    logging.info(f"从本地文件中，成功为 {found_count} / {original_count} 个独立的InChIKey找到SMILES。")
    
    # 根据原始逻辑，删除那些未能找到SMILES的行
    df_with_smiles.dropna(subset=[smiles_col], inplace=True)
    
    return df_with_smiles


def prepare_training_data(positive_inchikeys_df: pd.DataFrame, config, run_output_dir: Path) -> Path:
    """
    准备用于模型训练的最终数据集。
    此版本会根据正样本数量，按1:10的比例对未标记样本进行下采样。

    Args:
        positive_inchikeys_df (pd.DataFrame): 包含正样本InChIKey的DataFrame。
        config: 配置模块。
        run_output_dir (Path): 当前运行的输出目录路径。

    Returns:
        Path: 生成的训练数据CSV文件的路径。
    """
    # 1. 为正样本获取SMILES，并确定正样本数量
    df_positive = get_smiles_for_inchikeys(positive_inchikeys_df, config)
    if df_positive.empty:
        logging.error("无法为任何正样本找到SMILES，无法继续。")
        raise ValueError("无法为任何正样本找到SMILES，无法继续。")
    df_positive[config.TARGET_COL] = 1
    n_positive = len(df_positive)
    logging.info(f"步骤完成：确定正样本数量为 {n_positive}。")

    # 2. 加载未标记样本
    unlabeled_path = config.UNLABELED_SAMPLES_FILE
    logging.info(f"正在加载完整的未标记样本库: {unlabeled_path}")
    # 兼容不同的列名格式 (smiles 或 SMILES)
    df_unlabeled = pd.read_csv(unlabeled_path)
    # 统一列名为大写 SMILES
    if 'smiles' in df_unlabeled.columns and config.SMILES_COL not in df_unlabeled.columns:
        df_unlabeled.rename(columns={'smiles': config.SMILES_COL}, inplace=True)
    df_unlabeled = df_unlabeled[[config.SMILES_COL]]  # 只保留SMILES列
    df_unlabeled.dropna(subset=[config.SMILES_COL], inplace=True)
    df_unlabeled.drop_duplicates(subset=[config.SMILES_COL], inplace=True)

    # 3. 确保未标记样本与正样本不重复
    positive_smiles_set = set(df_positive[config.SMILES_COL])
    df_unlabeled_clean = df_unlabeled[~df_unlabeled[config.SMILES_COL].isin(positive_smiles_set)]
    logging.info(f"去除与正样本重复的项后，可用的未标记样本数: {len(df_unlabeled_clean)}")

    # 4. 按10倍比例随机下采样未标记样本
    n_unlabeled_needed = n_positive * 10
    logging.info(f"下一步：根据1:10的比例，需要从未标记样本中随机抽取 {n_unlabeled_needed} 个。")

    if len(df_unlabeled_clean) < n_unlabeled_needed:
        error_msg = (
            f"错误：未标记样本不足！需要 {n_unlabeled_needed} 个, "
            f"但可用的 (不与正样本重复的) 样本仅有 {len(df_unlabeled_clean)} 个。"
        )
        logging.error(error_msg)
        raise ValueError(error_msg)
        
    df_unlabeled_sampled = df_unlabeled_clean.sample(n=n_unlabeled_needed, random_state=config.RANDOM_SEED)
    df_unlabeled_sampled[config.TARGET_COL] = 0
    logging.info(f"已成功随机抽取 {len(df_unlabeled_sampled)} 个未标记样本。")
    
    # 5. 合并正样本和抽样后的未标记样本
    logging.info("正在合并正样本和抽样后的未标记样本...")
    df_combined = pd.concat([df_positive[[config.SMILES_COL, config.TARGET_COL]], df_unlabeled_sampled], ignore_index=True)

    logging.info(f"最终训练集总样本数: {len(df_combined)}")
    logging.info(f"样本比例 (Positive:Unlabeled) 约为 1:{len(df_unlabeled_sampled)/n_positive:.0f}")

    # 6. 保存到文件
    output_path = run_output_dir / "prepared_training_data.csv"
    df_combined.to_csv(output_path, index=False)
    logging.info(f"已将按比例准备好的训练数据保存到: {output_path}")
    
    return output_path 