import argparse
import logging
import pandas as pd
from pathlib import Path
import sys

# 将父目录（项目根目录）添加到系统路径，以便导入config
# 这使得脚本无论从哪里运行都能找到config模块
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

try:
    import config
except ImportError:
    print("错误：无法导入config.py。请确保此脚本位于'herb_project'文件夹内，"
          "并且'config.py'存在于同一文件夹中。")
    sys.exit(1)

# 配置日志系统
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def find_inchikeys_by_entrez(entrez_ids_set: set) -> pd.DataFrame:
    """
    根据给定的EntrezID集合，从主数据文件中查找对应的InChIKey。
    返回一个包含EntrezID和InChIKey配对的DataFrame。
    """
    source_file_path = config.TCM_DATA_ROOT / config.INCHIKEY_ENTREZ_FILE
    inchikey_col = config.INCHIKEY_COL
    entrez_id_col = config.ENTREZ_ID_COL

    if not source_file_path.exists():
        logging.error(f"错误：数据源文件未找到: {source_file_path}")
        return pd.DataFrame(columns=[inchikey_col, entrez_id_col])

    logging.info(f"正在从 {source_file_path} 为 {len(entrez_ids_set)} 个EntrezID查找InChIKey...")

    chunk_size = 1_000_000
    found_matches_dfs = []
    
    try:
        with pd.read_csv(source_file_path, sep='\t', usecols=[inchikey_col, entrez_id_col], chunksize=chunk_size, dtype=str) as reader:
            for i, chunk in enumerate(reader):
                logging.info(f"正在处理数据块 {i+1}...")
                matches = chunk[chunk[entrez_id_col].isin(entrez_ids_set)]
                if not matches.empty:
                    found_matches_dfs.append(matches)
    except Exception as e:
        logging.error(f"读取或处理文件时发生错误: {e}")
        return pd.DataFrame(columns=[inchikey_col, entrez_id_col])

    if not found_matches_dfs:
        logging.info("查找完毕，未找到任何匹配项。")
        return pd.DataFrame(columns=[inchikey_col, entrez_id_col])

    df_all_matches = pd.concat(found_matches_dfs, ignore_index=True)
    df_all_matches.drop_duplicates(inplace=True)
    
    logging.info(f"查找完毕。共找到 {len(df_all_matches)} 个独特的 EntrezID-InChIKey 对。")
    
    return df_all_matches

def main():
    """主函数：解析命令行参数并执行查找和保存操作。"""
    parser = argparse.ArgumentParser(
        description="根据一个或多个EntrezID，查找并导出一个只包含对应InChIKey的CSV文件，并报告每个ID的InChIKey数量。"
    )
    parser.add_argument(
        "--entrez_ids",
        type=str,
        required=True,
        help="一个或多个用逗号分隔的EntrezID字符串 (例如: '7157,3479,2353')"
    )
    args = parser.parse_args()
    
    entrez_id_set = {e.strip() for e in args.entrez_ids.split(',')}
    
    df_matches = find_inchikeys_by_entrez(entrez_id_set)
    
    if not df_matches.empty:
        inchikey_col = config.INCHIKEY_COL
        entrez_id_col = config.ENTREZ_ID_COL

        # 优化1: 统计每个ID的InChIKey数量并输出
        counts_per_id = df_matches.groupby(entrez_id_col)[inchikey_col].nunique().reset_index(name='unique_inchikey_count')
        
        logging.info("--- 每个EntrezID对应的独特InChIKey数量 ---")
        # 使用to_string来确保格式对齐，更美观
        print(counts_per_id.to_string(index=False))
        logging.info("------------------------------------------")
        
        # 保存计数摘要到新文件
        counts_output_path = Path(__file__).parent / "entrez_id_counts.csv"
        counts_per_id.to_csv(counts_output_path, index=False)
        logging.info(f"计数摘要已保存到: {counts_output_path}")

        # 保留原有功能: 保存所有找到的独特InChIKey列表
        unique_inchikeys = df_matches[inchikey_col].unique()
        output_path = Path(__file__).parent / "filtered_inchikeys.csv"
        df_output = pd.DataFrame(unique_inchikeys, columns=[inchikey_col])
        df_output.to_csv(output_path, index=False)
        logging.info(f"成功将 {len(df_output)} 个独特的InChIKey保存到: {output_path}")
    else:
        logging.warning("未能为给定的EntrezID找到任何InChIKey。")

if __name__ == "__main__":
    main() 