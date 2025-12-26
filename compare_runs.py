import pandas as pd

runs = ['entrez_run_2025-12-23_21-20-38', 'entrez_run_2025-12-24_12-04-54']

for run in runs:
    print(f'\n===== {run} =====')
    herbs = pd.read_csv(f'outputs/{run}/herb_ranking_comprehensive.csv')
    compounds = pd.read_csv(f'outputs/{run}/compound_predictions_with_names.csv')
    
    for _, row in herbs.head(10).iterrows():
        chp_id, name = row['CHP_ID'], row['Chinese_herbal_pieces']
        print(f"\n[{int(row['rank'])}] {name} ({chp_id})")
        top = compounds[compounds['CHP_ID']==chp_id].nlargest(10, 'predicted_probability')
        for i, (_, c) in enumerate(top.iterrows(), 1):
            # print(f"  {i}. {c['InChIKey']} | prob={c['predicted_probability']:.4f}")
            print(f"  {i}. {c['InChIKey']}")

