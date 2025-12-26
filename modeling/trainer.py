import pandas as pd
import numpy as np
import torch
import os
import logging
from pathlib import Path
from joblib import Parallel, delayed

from chemprop.data import MoleculeDatapoint, MoleculeDataset, build_dataloader
from chemprop.models.model import MPNN
from chemprop.nn import BondMessagePassing, MeanAggregation, BinaryClassificationFFN
from chemprop import featurizers
from lightning import pytorch as pl

def train_single_model(fold_idx, train_pos, unlabeled_groups, config, run_models_dir):
    """
    训练单个基学习器模型。
    这是一个被并行调用的辅助函数。
    """
    fold_seed = config.RANDOM_SEED + fold_idx
    np.random.seed(fold_seed)
    torch.manual_seed(fold_seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(fold_seed)

    # 准备当前fold的数据
    current_unlabeled = unlabeled_groups[fold_idx]
    train_data = train_pos + current_unlabeled
    
    # chemprop数据集和加载器
    featurizer = featurizers.SimpleMoleculeMolGraphFeaturizer()
    train_dset = MoleculeDataset(train_data, featurizer)
    train_loader = build_dataloader(train_dset, num_workers=config.NUM_WORKERS, shuffle=True)
    
    # 定义模型
    model = MPNN(
        message_passing=BondMessagePassing(),
        agg=MeanAggregation(),
        predictor=BinaryClassificationFFN(n_tasks=1)
    )

    # 训练器
    trainer = pl.Trainer(
        logger=False,
        enable_checkpointing=False,
        enable_progress_bar=True,
        accelerator="auto",
        devices=1,
        max_epochs=config.MAX_EPOCHS,
        deterministic=True
    )

    # 训练
    logging.info(f"[Fold {fold_idx}] 开始训练，包含 {len(train_pos)} 个正样本和 {len(current_unlabeled)} 个未标记样本。")
    trainer.fit(model, train_loader)
    
    # 保存模型
    model_path = run_models_dir / f"fold_{fold_idx}.ckpt"
    trainer.save_checkpoint(model_path)
    logging.info(f"[Fold {fold_idx}] 训练完成，模型已保存至 {model_path}")
    
    return model_path

def train_pu_model_ensemble(training_data_path: Path, config, run_models_dir: Path):
    """
    训练一个PU-Bagging集成模型。
    """
    logging.info("开始PU-Bagging集成模型训练...")
    
    # 1. 加载和准备数据
    df_train = pd.read_csv(training_data_path)
    smis = df_train[config.SMILES_COL].values
    ys = df_train[config.TARGET_COL].values
    all_data = [MoleculeDatapoint.from_smi(smi, [y]) for smi, y in zip(smis, ys)]
    
    positive_data = [d for d in all_data if d.y[0] == 1]
    unlabeled_data = [d for d in all_data if d.y[0] == 0]
    
    if not positive_data:
        logging.error("训练数据中没有正样本，无法进行训练。")
        raise ValueError("No positive samples for training.")

    # 2. 将未标记样本分层分配到各基学习器
    n_unlabeled = len(unlabeled_data)
    group_size = n_unlabeled // config.N_ESTIMATORS
    unlabeled_groups = []
    indices = np.random.permutation(n_unlabeled)

    for i in range(config.N_ESTIMATORS):
        start_idx = i * group_size
        end_idx = (i + 1) * group_size if i != config.N_ESTIMATORS - 1 else n_unlabeled
        group_indices = indices[start_idx:end_idx]
        unlabeled_groups.append([unlabeled_data[j] for j in group_indices])

    # 3. 并行训练所有模型
    logging.info(f"将并行训练 {config.N_ESTIMATORS} 个模型...")
    
    # 注意：在Windows上，joblib的并行执行可能需要将辅助函数放在可导入的模块中
    # 我们这里的结构是符合这个要求的
    Parallel(n_jobs=-1)(
        delayed(train_single_model)(i, positive_data, unlabeled_groups, config, run_models_dir)
        for i in range(config.N_ESTIMATORS)
    )

    logging.info("所有基学习器训练完成。")
    return run_models_dir 