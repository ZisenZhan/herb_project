import argparse
import logging
from datetime import datetime
from pathlib import Path

# 导入项目模块
import config
from data_pipeline import data_loader, data_preparer
from modeling import trainer, predictor
from scoring import ranker

def main():
    """项目主入口函数"""
    
    # --- 1. 设置和解析参数 ---
    parser = argparse.ArgumentParser(description="根据EntrezID，预测并排名相关中药。")
    parser.add_argument(
        "--entrez_ids", 
        type=str, 
        required=True, 
        help="一个或多个用逗号分隔的EntrezID (例如: '2,19,23')"
    )
    args = parser.parse_args()
    entrez_ids_str = args.entrez_ids
    entrez_id_set = set(entrez_ids_str.split(','))
    
    logging.info(f"===== 开始为EntrezID集合 '{entrez_ids_str}' 生成中药排名 =====")

    # --- 2. 创建本次运行的专属目录 ---
    run_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_name = f"entrez_run_{run_timestamp}"
    run_output_dir = config.OUTPUTS_DIR / run_name
    run_models_dir = config.MODELS_DIR / run_name
    run_output_dir.mkdir(parents=True, exist_ok=True)
    run_models_dir.mkdir(parents=True, exist_ok=True)
    
    # --- 2b. 配置日志系统 ---
    log_file_path = run_output_dir / "run.log"
    
    # 获取根日志记录器
    logger = logging.getLogger()
    logger.setLevel(logging.INFO) # 设置总级别
    
    # 如果已有处理器，先清除，防止重复记录
    if logger.hasHandlers():
        logger.handlers.clear()
        
    # 创建文件处理器，写入日志文件
    file_handler = logging.FileHandler(log_file_path, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # 创建控制台处理器，打印到屏幕
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 定义日志格式
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 将处理器添加到根日志记录器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logging.info(f"日志将同时输出到控制台和文件: {log_file_path}")
    logging.info(f"本次运行的输出将保存在: {run_output_dir}")
    logging.info(f"本次运行的模型将保存在: {run_models_dir}")

    try:
        # --- 3. 执行数据和模型流程 ---
        
        # 步骤 1: 查找正样本
        positive_samples_df = data_loader.find_positive_samples_by_entrez(entrez_id_set, config)
        if positive_samples_df.empty:
            logging.error("未能找到任何正样本，流程终止。")
            return

        # 步骤 2: 准备训练数据
        training_data_path = data_preparer.prepare_training_data(positive_samples_df, config, run_output_dir)

        # 步骤 3: 训练模型
        trained_models_dir = trainer.train_pu_model_ensemble(training_data_path, config, run_models_dir)

        # 步骤 4: 对化合物库进行预测
        compound_predictions_path = predictor.generate_compound_predictions(trained_models_dir, config, run_output_dir)
        
        # 步骤 5: 聚合分数并排名中药
        final_ranking_path = ranker.rank_herbs(compound_predictions_path, config, run_output_dir)

        logging.info(f"===== 流程成功结束！ =====")
        logging.info(f"最终的中药排名报告已生成: {final_ranking_path}")

    except Exception as e:
        logging.error(f"在执行过程中发生严重错误: {e}", exc_info=True)
        logging.info("===== 流程因错误而终止 =====")

if __name__ == "__main__":
    main() 