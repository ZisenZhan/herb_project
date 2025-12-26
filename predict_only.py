import argparse
import logging
from pathlib import Path

# 导入项目模块
import config
from modeling import predictor
from scoring import ranker

def predict_main():
    """仅执行预测和排名流程的脚本"""
    
    # --- 1. 设置和解析参数 ---
    parser = argparse.ArgumentParser(description="使用已训练好的模型进行预测并排名中药。")
    parser.add_argument(
        "--run_id", 
        type=str, 
        required=True, 
        help="指定一个已存在的run_id (例如: 'entrez_run_2025-07-06_11-14-12')"
    )
    args = parser.parse_args()
    
    run_name = args.run_id
    
    # --- 2. 设置路径和日志 ---
    run_output_dir = config.OUTPUTS_DIR / run_name
    run_models_dir = config.MODELS_DIR / run_name
    
    if not run_models_dir.exists() or not any(run_models_dir.glob('*.ckpt')):
        print(f"错误：在 {run_models_dir} 中找不到模型文件。请确保run_id正确，且模型已训练。")
        return

    # 配置日志系统，追加到现有日志
    log_file_path = run_output_dir / "run.log"
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    if logger.hasHandlers():
        logger.handlers.clear()
        
    # 使用追加模式'a'，这样不会覆盖之前的训练日志
    file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logging.info(f"===== 使用run_id '{run_name}' 继续执行预测和排名 =====")

    try:
        # --- 3. 执行预测和排名流程 ---
        
        # 步骤 4: 对化合物库进行预测
        logging.info("===== 步骤 4: 使用模型进行预测 =====")
        compound_predictions_path = predictor.generate_compound_predictions(run_models_dir, config, run_output_dir)
        
        # 步骤 5: 聚合分数并排名中药
        logging.info("===== 步骤 5: 排名中药 =====")
        final_ranking_path = ranker.rank_herbs(compound_predictions_path, config, run_output_dir)

        logging.info(f"===== 预测流程成功结束！ =====")
        logging.info(f"最终的中药排名报告已生成: {final_ranking_path}")

    except Exception as e:
        logging.error(f"在执行预测过程中发生严重错误: {e}", exc_info=True)
        logging.info("===== 流程因错误而终止 =====")

if __name__ == "__main__":
    predict_main() 