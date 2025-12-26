"""
将 filtered_inchikeys.csv 中的 InChIKey 转换为 SMILES
"""
import pandas as pd
import logging
from pathlib import Path
import config
from data_pipeline.data_preparer import get_smiles_for_inchikeys

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    # 输入文件路径
    input_file = Path("filtered_inchikeys.csv")
    
    if not input_file.exists():
        logging.error(f"错误: 找不到文件 {input_file}")
        logging.info("请先运行 get_inchikeys_by_entrez.py 生成 filtered_inchikeys.csv")
        return
    
    # 读取 InChIKey 列表
    logging.info(f"正在读取 {input_file}...")
    df_inchikeys = pd.read_csv(input_file)
    
    logging.info(f"共有 {len(df_inchikeys)} 个 InChIKey 需要转换")
    
    # 转换为 SMILES
    logging.info("开始转换 InChIKey 到 SMILES...")
    df_with_smiles = get_smiles_for_inchikeys(df_inchikeys, config)
    
    # 保存结果
    output_file = Path("inchikeys_with_smiles.csv")
    df_with_smiles.to_csv(output_file, index=False)
    
    # 统计结果
    total = len(df_inchikeys)
    converted = len(df_with_smiles)
    failed = total - converted
    
    logging.info(f"\n{'='*50}")
    logging.info(f"转换完成！")
    logging.info(f"总数: {total}")
    logging.info(f"成功转换: {converted} ({converted/total*100:.1f}%)")
    logging.info(f"未找到SMILES: {failed}")
    logging.info(f"结果已保存到: {output_file}")
    logging.info(f"{'='*50}\n")
    
    # 显示前几行预览
    if not df_with_smiles.empty:
        logging.info("前5行预览:")
        print(df_with_smiles.head().to_string(index=False))

if __name__ == "__main__":
    main()

