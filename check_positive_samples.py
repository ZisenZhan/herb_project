import argparse
import logging
import sys
from pathlib import Path

# 将项目根目录添加到系统路径中，以便能正确导入其他模块
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

import config
from data_pipeline import data_loader

def check_codes(icd_codes_to_check: list):
    """
    检查一个ICD-11代码列表，并识别出哪些代码拥有正样本。

    Args:
        icd_codes_to_check (list): 一个包含ICD-11代码字符串的列表。
    """
    logging.info(f"开始检查 {len(icd_codes_to_check)} 个ICD代码...")
    
    codes_with_positives = []

    for code in icd_codes_to_check:
        # 为了更清晰的日志，每次检查前打印分隔符
        logging.info(f"\n{'='*20} 正在检查代码: {code} {'='*20}")
        try:
            # 复用主流程中的函数来查找正样本
            df_positive = data_loader.find_positive_samples(code, config)
            
            if not df_positive.empty:
                logging.info(f"成功: 为代码 '{code}' 找到 {len(df_positive)} 个正样本。")
                codes_with_positives.append(code)
            else:
                logging.warning(f"失败: 未为代码 '{code}' 找到任何正样本。")

        except Exception as e:
            logging.error(f"检查代码 '{code}' 时发生严重错误: {e}")

    # --- 在所有检查结束后，打印最终的总结报告 ---
    print("\n" + "#"*60)
    print(" 所有代码检查完成 ".center(60, '#'))
    print("#"*60)
    
    if codes_with_positives:
        print("\n[+] 以下ICD代码成功找到了至少一个正样本:")
        for code in codes_with_positives:
            print(f"  - {code}")
    else:
        print("\n[-] 所有提供的ICD代码均未能找到任何正样本。")
    
    print("\n" + "#"*60)


def main():
    """脚本主入口"""
    # --- 为此脚本配置一个简单的日志记录器，只输出到控制台 ---
    # 这样可以避免与main.py中复杂的文件日志记录器冲突
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s', stream=sys.stdout)

    # --- 设置和解析命令行参数 ---
    parser = argparse.ArgumentParser(
        description="快速检查一个或多个ICD11代码，筛选出能找到对应正样本的疾病代码。",
        formatter_class=argparse.RawTextHelpFormatter # 保持帮助信息格式
    )
    parser.add_argument(
        "icd_codes", 
        nargs='+', # '+'号表示可以接受一个或多个参数
        type=str, 
        help="一个或多个要检查的ICD11代码，用空格分隔。\n示例: python check_positive_samples.py DA09.7 2B66.0 AB12.3"
    )
    args = parser.parse_args()
    
    check_codes(args.icd_codes)


if __name__ == "__main__":
    main() 