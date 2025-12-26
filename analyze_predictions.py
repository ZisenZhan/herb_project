"""
分析预测结果中概率分布
"""
import pandas as pd

# 读取预测结果
predictions = pd.read_csv('outputs/entrez_run_2025-12-23_21-20-38/compound_predictions.csv')

# 统计概率分布
print('=== 预测概率分布统计 ===')
print(f'总预测数: {len(predictions)}')
print(f'概率 = 1.0 的数量: {(predictions["predicted_probability"] == 1.0).sum()}')
print(f'概率 >= 0.99 的数量: {(predictions["predicted_probability"] >= 0.99).sum()}')
print(f'概率 >= 0.9 的数量: {(predictions["predicted_probability"] >= 0.9).sum()}')
print(f'概率 >= 0.5 的数量: {(predictions["predicted_probability"] >= 0.5).sum()}')
print(f'概率 < 0.5 的数量: {(predictions["predicted_probability"] < 0.5).sum()}')
print()

# 读取训练数据
training = pd.read_csv('outputs/entrez_run_2025-12-23_21-20-38/prepared_training_data.csv')
positive_samples = training[training['label'] == 1]
print(f'=== 训练数据统计 ===')
print(f'正样本数: {len(positive_samples)}')
print(f'未标记样本数: {len(training) - len(positive_samples)}')
print()

# 检查重叠情况
positive_smiles = set(positive_samples['SMILES'].values)
pred_smiles = set(predictions['SMILES'].values)
overlap = positive_smiles.intersection(pred_smiles)
print(f'=== 关键发现：正样本与预测目标的重叠 ===')
print(f'正样本SMILES数: {len(positive_smiles)}')
print(f'预测目标SMILES数: {len(pred_smiles)}')
print(f'重叠的SMILES数: {len(overlap)}')
print()

# 检查重叠的化合物预测概率
if len(overlap) > 0:
    overlap_predictions = predictions[predictions['SMILES'].isin(overlap)]
    print(f'重叠化合物的预测概率统计:')
    print(f'  平均概率: {overlap_predictions["predicted_probability"].mean():.4f}')
    print(f'  概率 = 1.0 的数量: {(overlap_predictions["predicted_probability"] == 1.0).sum()}')
    print(f'  概率 >= 0.99 的数量: {(overlap_predictions["predicted_probability"] >= 0.99).sum()}')
    print()
    
    # 非重叠化合物的概率分布
    non_overlap_predictions = predictions[~predictions['SMILES'].isin(overlap)]
    print(f'非重叠化合物的预测概率统计:')
    print(f'  数量: {len(non_overlap_predictions)}')
    print(f'  平均概率: {non_overlap_predictions["predicted_probability"].mean():.4f}')
    print(f'  概率 = 1.0 的数量: {(non_overlap_predictions["predicted_probability"] == 1.0).sum()}')
    print(f'  概率 >= 0.99 的数量: {(non_overlap_predictions["predicted_probability"] >= 0.99).sum()}')
    print(f'  概率 >= 0.9 的数量: {(non_overlap_predictions["predicted_probability"] >= 0.9).sum()}')

