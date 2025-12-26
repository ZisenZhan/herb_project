"""
输出排名前N的中药，每个中药的前M个高分化合物

用法:
    python top_herbs_compounds.py [中药数量] [化合物数量]
    
示例:
    python top_herbs_compounds.py 5 4      # 前5名中药，每个前4个化合物
    python top_herbs_compounds.py 10 3     # 前10名中药，每个前3个化合物
"""
import pandas as pd
import argparse

# 解析命令行参数
parser = argparse.ArgumentParser(description='输出排名前N的中药及其Top M化合物')
parser.add_argument('top_herbs', type=int, nargs='?', default=5, 
                    help='输出前几名中药 (默认: 5)')
parser.add_argument('top_compounds', type=int, nargs='?', default=10, 
                    help='每个中药输出前几个化合物 (默认: 4)')
args = parser.parse_args()

TOP_HERBS = args.top_herbs
TOP_COMPOUNDS = args.top_compounds

# 读取数据
herb_ranking = pd.read_csv('outputs/entrez_run_2025-12-24_11-34-54/herb_ranking_comprehensive.csv')
compound_predictions = pd.read_csv('outputs/entrez_run_2025-12-24_11-34-54/compound_predictions_with_names.csv')

# 获取前N名中药
top_n_herbs = herb_ranking.head(TOP_HERBS)

print("=" * 80)
print(f"排名前{TOP_HERBS}的中药及其Top {TOP_COMPOUNDS}化合物")
print("=" * 80)

results = []

for idx, row in top_n_herbs.iterrows():
    chp_id = row['CHP_ID']
    herb_name = row['Chinese_herbal_pieces']
    rank = row['rank']
    score = row['comprehensive_score']
    
    print(f"\n【第{int(rank)}名】{herb_name} ({chp_id})")
    print(f"    综合评分: {score:.4f}")
    print("-" * 60)
    
    # 筛选该中药的化合物，按预测分数排序
    herb_compounds = compound_predictions[compound_predictions['CHP_ID'] == chp_id]
    top_m_compounds = herb_compounds.nlargest(TOP_COMPOUNDS, 'predicted_probability')
    
    for i, (_, comp) in enumerate(top_m_compounds.iterrows(), 1):
        inchikey = comp['InChIKey']
        smiles = comp['SMILES']
        prob = comp['predicted_probability']
        
        print(f"    化合物 {i}:")
        print(f"      InChIKey: {inchikey}")
        print(f"      SMILES: {smiles}")
        print(f"      预测概率: {prob:.6f}")
        
        results.append({
            'herb_rank': int(rank),
            'herb_name': herb_name,
            'CHP_ID': chp_id,
            'compound_rank': i,
            'InChIKey': inchikey,
            'SMILES': smiles,
            'predicted_probability': prob
        })

print("\n" + "=" * 80)

# 保存为CSV
output_df = pd.DataFrame(results)
output_file = f'outputs/entrez_run_2025-12-23_21-20-38/top{TOP_HERBS}_herbs_top{TOP_COMPOUNDS}_compounds.csv'
output_df.to_csv(output_file, index=False, encoding='utf-8-sig')
print(f"\n结果已保存到: {output_file}")

