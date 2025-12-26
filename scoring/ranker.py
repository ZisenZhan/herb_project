import pandas as pd
import logging
from pathlib import Path
import argparse
import sys

# 确保可以从项目根目录导入模块
sys.path.append(str(Path(__file__).resolve().parents[1]))
import config

def rank_herbs(compound_predictions_path: Path, config, run_output_dir: Path) -> Path:
    """
    根据化合物的预测分数，对中药进行聚合评分和排名。

    Args:
        compound_predictions_path (Path): 化合物预测分数的CSV文件路径。
        config: 配置模块。
        run_output_dir (Path): 当前运行的输出目录路径。

    Returns:
        Path: 最终生成的中药排名报告CSV文件的路径。
    """
    logging.info("开始对中药进行评分和排名...")

    # 1. 加载化合物预测结果
    logging.info(f"正在加载化合物预测分数: {compound_predictions_path}")
    df_preds = pd.read_csv(compound_predictions_path)
    
    # 检查预测文件是否已经包含 CHP_ID 列
    if config.CHP_ID_COL not in df_preds.columns:
        # 如果预测文件中没有 CHP_ID，则需要从映射文件中获取
        logging.info("预测文件中缺少 CHP_ID 列，正在从映射文件中获取...")
        herb_compounds_path = config.TCM_DATA_ROOT / config.HERB_COMPOUNDS_FILE
        logging.info(f"正在加载中药-化合物映射: {herb_compounds_path}")
        df_herb_map = pd.read_csv(
            herb_compounds_path, 
            usecols=[config.INCHIKEY_COL, config.CHP_ID_COL],
            sep='\t' # 使用正则表达式匹配一个或多个空白字符作为分隔符
        )
        # 将预测分数与CHP_ID合并
        df_merged = pd.merge(df_preds, df_herb_map, on=config.INCHIKEY_COL, how='left')
        df_merged.dropna(subset=[config.CHP_ID_COL], inplace=True)
    else:
        # 如果预测文件中已经包含 CHP_ID，直接使用
        logging.info("预测文件中已包含 CHP_ID 列，直接使用...")
        df_merged = df_preds.copy()
        df_merged.dropna(subset=[config.CHP_ID_COL], inplace=True)

    # 3. 按CHP_ID聚合分数，计算多种排名指标
    logging.info("正在按中药ID (CHP_ID) 聚合分数...")
    
    def calculate_herb_metrics(group):
        """计算单个中药的多种评分指标"""
        scores = group['predicted_probability']
        
        # 基础统计
        total_compounds = len(scores)
        total_score = scores.sum()
        avg_score = scores.mean() if total_compounds > 0 else 0
        
        # 有效成分（不为0）的统计
        effective_scores = scores[scores > 0]
        effective_count = len(effective_scores)
        effective_avg = effective_scores.mean() if effective_count > 0 else 0
        
        # 高质量成分（大于0.8）的统计
        high_quality_scores = scores[scores > 0.8]
        high_quality_count = len(high_quality_scores)
        high_quality_avg = high_quality_scores.mean() if high_quality_count > 0 else 0
        
        # 超高质量成分（大于0.9）的统计
        ultra_high_scores = scores[scores > 0.9]
        ultra_high_count = len(ultra_high_scores)
        ultra_high_avg = ultra_high_scores.mean() if ultra_high_count > 0 else 0
        
        # 其他有用的指标
        max_score = scores.max()
        median_score = scores.median()
        std_score = scores.std()
        
        # 质量分布比例
        effective_ratio = effective_count / total_compounds if total_compounds > 0 else 0
        high_quality_ratio = high_quality_count / total_compounds if total_compounds > 0 else 0
        ultra_high_ratio = ultra_high_count / total_compounds if total_compounds > 0 else 0
        
        return pd.Series({
            'total_compounds': total_compounds,
            'total_score': total_score,
            'avg_score': avg_score,
            'effective_count': effective_count,
            'effective_avg': effective_avg,
            'effective_ratio': effective_ratio,
            'high_quality_count': high_quality_count,
            'high_quality_avg': high_quality_avg,
            'high_quality_ratio': high_quality_ratio,
            'ultra_high_count': ultra_high_count,
            'ultra_high_avg': ultra_high_avg,
            'ultra_high_ratio': ultra_high_ratio,
            'max_score': max_score,
            'median_score': median_score,
            'std_score': std_score
        })
    
    df_herb_scores = df_merged.groupby(config.CHP_ID_COL).apply(calculate_herb_metrics).reset_index()

    # 计算贝叶斯平滑平均分（抗小样本波动）
    global_mean = df_merged['predicted_probability'].mean()
    alpha = getattr(config, 'BAYESIAN_ALPHA', 10)
    df_herb_scores['adj_avg_score'] = (
        (df_herb_scores['total_score'] + alpha * global_mean) /
        (df_herb_scores['total_compounds'] + alpha)
    )

    # 4. 关联中药名称
    herb_names_path = config.TCM_DATA_ROOT / config.HERB_NAMES_FILE
    logging.info(f"正在加载中药名称: {herb_names_path}")
    df_herb_names = pd.read_csv(herb_names_path, usecols=[config.CHP_ID_COL, config.CHINESE_HERB_COL],sep='\t')
    
    # 在输出目录中保存一个带中药名称列的化合物预测文件，便于查看
    try:
        df_preds_with_names = pd.merge(df_merged, df_herb_names, on=config.CHP_ID_COL, how='left')
        preds_with_names_path = run_output_dir / "compound_predictions_with_names.csv"
        df_preds_with_names.to_csv(preds_with_names_path, index=False)
        logging.info(f"已生成带中药名称的化合物预测文件: {preds_with_names_path}")
    except Exception as e:
        logging.warning(f"生成带中药名称的化合物预测文件失败: {e}")

    df_final_ranking = pd.merge(df_herb_scores, df_herb_names, on=config.CHP_ID_COL, how='left')
    
    # 5. 生成多种排名
    logging.info("正在生成多种排名方式...")
    
    # 创建多个排名版本
    ranking_methods = {
        'avg_score': ('平均分排名', 'avg_score', False),
        'adj_avg_score': ('贝叶斯平均分排名', 'adj_avg_score', False),
        'effective_avg': ('有效成分平均分排名', 'effective_avg', False),
        'high_quality_avg': ('高质量成分平均分排名', 'high_quality_avg', False),
        'ultra_high_count': ('超高质量成分数量排名', 'ultra_high_count', False),
        'ultra_high_avg': ('超高质量成分平均分排名', 'ultra_high_avg', False),
        'comprehensive': ('综合排名', 'comprehensive_score', False),
        'quality_ratio': ('质量比例排名', 'high_quality_ratio', False),
        'max_score': ('最高成分分数排名', 'max_score', False)
    }
    
    # 计算综合评分（多指标加权）
    df_final_ranking['comprehensive_score'] = (
        0.3 * df_final_ranking['adj_avg_score'] +
        0.2 * df_final_ranking['effective_avg'] +
        0.2 * df_final_ranking['high_quality_avg'] +
        0.15 * df_final_ranking['ultra_high_count'] / df_final_ranking['ultra_high_count'].max() +
        0.15 * df_final_ranking['high_quality_ratio']
    )
    
    # 生成各种排名文件
    output_files = []
    
    for method_key, (method_name, sort_col, ascending) in ranking_methods.items():
        df_ranked = df_final_ranking.copy()
        df_ranked = df_ranked.sort_values(by=sort_col, ascending=ascending)
        
        # 添加排名列
        df_ranked['rank'] = range(1, len(df_ranked) + 1)
        
        # 选择输出列
        if method_key == 'comprehensive':
            output_cols = [
                'rank', config.CHP_ID_COL, config.CHINESE_HERB_COL, 
                'comprehensive_score', 'avg_score', 'adj_avg_score', 'total_score', 'effective_avg', 
                'high_quality_avg', 'ultra_high_count', 'high_quality_ratio'
            ]
        else:
            output_cols = [
                'rank', config.CHP_ID_COL, config.CHINESE_HERB_COL, sort_col,
                'total_compounds', 'effective_count', 'high_quality_count', 'ultra_high_count'
            ]
        
        df_output = df_ranked[output_cols]
        
        # 保存文件
        output_path = run_output_dir / f"herb_ranking_{method_key}.csv"
        df_output.to_csv(output_path, index=False)
        output_files.append((method_name, output_path))
        
        logging.info(f"{method_name}已生成: {output_path}")
    
    # 生成汇总报告
    summary_path = run_output_dir / "ranking_summary.txt"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("中药排名汇总报告\n")
        f.write("=" * 50 + "\n\n")
        f.write("排名方法说明:\n")
        f.write("1. 综合排名: 多指标加权综合评分\n")
        f.write("   计算方法: 0.3×贝叶斯平均分 + 0.2×有效成分平均分 + 0.2×高质量成分平均分 + 0.15×超高质量成分数量(标准化) + 0.15×高质量成分比例\n")
        f.write("   说明: 平衡考虑了中药的整体效果、有效成分质量、高质量成分含量和比例，且通过贝叶斯平均抑制小样本波动\n\n")
        f.write("2. 平均分排名: 所有化合物预测分数的平均值\n")
        f.write("   说明: 反映中药成分的整体平均质量\n\n")
        f.write("3. 贝叶斯平均分排名: 使用贝叶斯平滑的平均分 (alpha=配置项)\n")
        f.write("   说明: 在平均分基础上加入全局先验，降低成分数过少导致的虚高\n\n")
        f.write("4. 有效成分平均分排名: 预测分数>0的化合物的平均分\n")
        f.write("   说明: 反映中药有效成分的平均质量\n\n")
        f.write("5. 高质量成分平均分排名: 预测分数>0.8的化合物的平均分\n")
        f.write("   说明: 反映中药高质量成分的平均效果\n\n")
        f.write("6. 超高质量成分数量排名: 预测分数>0.9的化合物数量\n")
        f.write("   说明: 反映中药含有的超高质量活性成分数量\n\n")
        f.write("7. 超高质量成分平均分排名: 预测分数>0.9的化合物的平均分\n")
        f.write("   说明: 反映中药超高质量成分的平均效果\n\n")
        f.write("8. 质量比例排名: 高质量成分占总成分的比例\n")
        f.write("   说明: 反映中药成分的整体质量分布\n\n")
        f.write("9. 最高成分分数排名: 单个化合物的最高预测分数\n")
        f.write("   说明: 反映中药中最具潜力的单一成分效果\n\n")
        
        f.write("各排名方法的前10名中药:\n")
        f.write("-" * 50 + "\n")
        
        # 重新排序，将综合排名放在最前面
        ordered_methods = [
            ('综合排名', run_output_dir / "herb_ranking_comprehensive.csv"),
            ('平均分排名', run_output_dir / "herb_ranking_avg_score.csv"),
            ('贝叶斯平均分排名', run_output_dir / "herb_ranking_adj_avg_score.csv"),
            ('有效成分平均分排名', run_output_dir / "herb_ranking_effective_avg.csv"),
            ('高质量成分平均分排名', run_output_dir / "herb_ranking_high_quality_avg.csv"),
            ('超高质量成分数量排名', run_output_dir / "herb_ranking_ultra_high_count.csv"),
            ('超高质量成分平均分排名', run_output_dir / "herb_ranking_ultra_high_avg.csv"),
            ('质量比例排名', run_output_dir / "herb_ranking_quality_ratio.csv"),
            ('最高成分分数排名', run_output_dir / "herb_ranking_max_score.csv")
        ]
        
        for method_name, file_path in ordered_methods:
            f.write(f"\n{method_name}:\n")
            df_top = pd.read_csv(file_path).head(10)
            for idx, row in df_top.iterrows():
                f.write(f"  {row['rank']}. {row[config.CHINESE_HERB_COL]} ({row[config.CHP_ID_COL]})\n")
    
    logging.info(f"汇总报告已生成: {summary_path}")
    
    # 返回综合排名文件路径作为主要结果
    main_output_path = run_output_dir / "herb_ranking_comprehensive.csv"
    logging.info(f"最终中药排名已生成并保存至: {main_output_path}")
    
    return main_output_path

def main():
    """主函数，用于独立运行排名脚本。"""
    parser = argparse.ArgumentParser(description="根据化合物预测分数对中药进行排名。")
    parser.add_argument(
        "compound_predictions_csv",
        type=str,
        help="包含化合物预测分数的CSV文件路径。"
    )
    args = parser.parse_args()

    compound_predictions_path = Path(args.compound_predictions_csv)
    
    if not compound_predictions_path.is_file():
        print(f"错误: 文件不存在或不是一个有效的文件: {compound_predictions_path}")
        return

    # 从输入路径推断 run_id 和输出目录
    run_id = compound_predictions_path.parent.name
    run_output_dir = config.OUTPUTS_DIR / run_id
    run_output_dir.mkdir(parents=True, exist_ok=True)
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(run_output_dir / "ranking.log", mode='w', encoding='utf-8')
        ]
    )

    logging.info(f"===== 单独执行中药排名流程 =====")
    logging.info(f"Run ID: {run_id}")
    logging.info(f"输入文件: {compound_predictions_path}")
    logging.info(f"输出目录: {run_output_dir}")

    try:
        final_ranking_path = rank_herbs(compound_predictions_path, config, run_output_dir)
        logging.info(f"===== 排名流程成功结束！ =====")
        logging.info(f"最终的中药排名报告已生成: {final_ranking_path}")
    except Exception as e:
        logging.error(f"在执行排名过程中发生严重错误: {e}", exc_info=True)
        logging.info("===== 流程因错误而终止 =====")

if __name__ == "__main__":
    main() 