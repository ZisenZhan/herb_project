import pandas as pd
import numpy as np
import torch
import logging
from pathlib import Path

from chemprop.data import MoleculeDatapoint, MoleculeDataset, build_dataloader
from chemprop.models.model import MPNN
from chemprop import featurizers
from lightning import pytorch as pl

from data_pipeline.data_preparer import get_smiles_for_inchikeys # 复用SMILES转换逻辑

def predict_with_ensemble(models_dir: Path, data_to_predict: pd.DataFrame, config) -> pd.DataFrame:
    """
    使用训练好的模型集成对新数据进行预测。
    """
    logging.info(f"开始使用模型集成进行预测，目标数据量: {len(data_to_predict)}...")
    
    # 准备数据加载器
    smis = data_to_predict[config.SMILES_COL].values
    points = [MoleculeDatapoint.from_smi(smi, y=None) for smi in smis]
    featurizer = featurizers.SimpleMoleculeMolGraphFeaturizer()
    dset = MoleculeDataset(points, featurizer)
    loader = build_dataloader(dset, num_workers=config.NUM_WORKERS, shuffle=False)
    
    all_preds = []
    model_files = sorted(models_dir.glob("*.ckpt"))
    
    if not model_files:
        logging.error(f"在 {models_dir} 中未找到任何模型文件(.ckpt)。")
        raise FileNotFoundError(f"No model checkpoints found in {models_dir}")

    for model_path in model_files:
        logging.info(f"正在使用模型 {model_path.name} 进行预测...")
        model = MPNN.load_from_checkpoint(
            model_path,
            map_location=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        )
        trainer = pl.Trainer(accelerator="auto", devices=1, logger=False)
        
        with torch.inference_mode():
            preds = trainer.predict(model, loader)
        
        # 展平并收集预测结果
        # preds 是一个列表的列表，需要将它们连接成一个一维数组
        preds_flat = np.concatenate([p.flatten() for p in preds])
        all_preds.append(preds_flat)

    # 计算集成预测的平均值
    ensemble_preds = np.mean(all_preds, axis=0)
    
    # 将预测结果添加到DataFrame中
    data_to_predict['predicted_probability'] = ensemble_preds
    logging.info("所有模型的预测已完成，并计算了集成平均分。")
    
    return data_to_predict

def generate_compound_predictions(models_dir: Path, config, run_output_dir: Path) -> Path:
    """
    对整个中药化合物库进行预测。
    """
    # 1. 加载中药化合物库 (InChIKeys)
    herb_compounds_path = config.TCM_DATA_ROOT / config.HERB_COMPOUNDS_FILE
    logging.info(f"正在加载中药化合物库: {herb_compounds_path}")
    df_compounds = pd.read_csv(herb_compounds_path, sep='\t', usecols=[config.INCHIKEY_COL, config.CHP_ID_COL])
    df_compounds.drop_duplicates(subset=[config.INCHIKEY_COL], inplace=True)
    
    # 2. 为化合物获取SMILES
    df_compounds_with_smiles = get_smiles_for_inchikeys(df_compounds, config)
    
    if df_compounds_with_smiles.empty:
        logging.error("无法为任何库中化合物找到SMILES，无法进行预测。")
        raise ValueError("Cannot find SMILES for any compound in the library.")
        
    # 3. 使用模型集成进行预测
    df_predictions = predict_with_ensemble(models_dir, df_compounds_with_smiles, config)
    
    # 4. 保存预测结果
    output_path = run_output_dir / "compound_predictions.csv"
    df_predictions.to_csv(output_path, index=False)
    logging.info(f"化合物预测分数已保存至: {output_path}")
    
    return output_path 