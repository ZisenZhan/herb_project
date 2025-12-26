# 中药预测系统使用指南

## 项目简介

本项目是一个基于机器学习的中药预测系统，可以根据基因靶点（EntrezID）自动预测和排名相关的中药。系统采用PU-Learning（正样本-未标记学习）方法和图神经网络（ChemProp）进行训练。

## 主要功能

1. **基于EntrezID预测中药**：输入一个或多个基因靶点ID，系统会：
   - 查找与这些靶点相关的化合物（正样本）
   - 训练机器学习模型
   - 预测化合物库中所有化合物的相关性
   - 聚合生成中药排名列表

2. **仅预测模式**：使用已训练好的模型直接进行预测，跳过训练步骤

## 环境配置

### 1. 安装依赖

```bash
# 安装基础依赖
pip install -r requirements.txt

# 如果需要化学信息学相关功能
pip install -r requriements_chem.txt
```

主要依赖包括：
- pandas, numpy: 数据处理
- torch, lightning: 深度学习框架
- chemprop: 分子图神经网络
- scikit-learn: 机器学习工具
- pubchempy: 化学数据库接口

### 2. 配置数据路径

编辑 `config.py` 文件，确保以下路径正确：

```python
# 指向存放D1-D24等原始TSV文件的地方
TCM_DATA_ROOT = Path("D:/TCM")  # 修改为你的数据目录

# 其他路径会自动在项目目录下创建
OUTPUTS_DIR = PROJECT_ROOT / "outputs"  # 输出目录
MODELS_DIR = PROJECT_ROOT / "models"    # 模型目录
```

## 使用方法

### 方法一：完整流程（训练 + 预测）

适用于首次运行或需要重新训练模型的情况。

```bash
python main.py --entrez_ids "2,19,23"
```

**参数说明**：
- `--entrez_ids`: 一个或多个EntrezID，用逗号分隔（必需）

**示例**：
```bash
# 单个EntrezID
python main.py --entrez_ids "1234"

# 多个EntrezID
python main.py --entrez_ids "1234,5678,9012"
```

**执行流程**：
1. 根据EntrezID查找正样本化合物
2. 准备训练数据（正样本 + 背景样本）
3. 训练PU-Bagging集成模型（默认10折）
4. 对化合物库进行预测
5. 聚合化合物分数，生成中药排名

### 方法二：仅预测模式

如果已经有训练好的模型，可以直接使用模型进行预测：

```bash
python predict_only.py --run_id "entrez_run_2025-07-06_11-12-05"
```

**参数说明**：
- `--run_id`: 之前运行生成的运行ID（必需）

**示例**：
```bash
python predict_only.py --run_id "entrez_run_2025-07-06_11-12-05"
```

## 输出结果

### 目录结构

每次运行会创建两个目录：

1. **outputs/[run_id]/**：存放输出文件
   - `run.log`: 运行日志
   - `prepared_training_data.csv`: 准备好的训练数据
   - `final_herb_ranking.csv`: **最终中药排名**（主要结果）
   - `herb_ranking_*.csv`: 各种排名策略的结果
   - `ranking_summary.txt`: 排名统计摘要

2. **models/[run_id]/**：存放训练的模型
   - `fold_0.ckpt` ~ `fold_9.ckpt`: 10个折叠的模型文件
   - `compound_predictions.csv`: 化合物预测结果

### 主要结果文件

#### 1. final_herb_ranking.csv
最终的中药排名列表，包含以下字段：
- `CHP_ID`: 中药ID
- `Chinese_herbal_pieces`: 中药名称
- `final_score`: 综合评分
- `rank`: 排名

#### 2. herb_ranking_comprehensive.csv
详细的中药评分信息，包含：
- 多种评分策略（最大分、平均分、总分等）
- 化合物数量统计
- 质量指标（高质量化合物比例等）

## 配置说明

在 `config.py` 中可以调整以下参数：

```python
# 模型参数
N_ESTIMATORS = 10      # PU-Bagging基学习器数量（建议10-20）
MAX_EPOCHS = 20        # 神经网络训练轮次（建议10-30）
NUM_WORKERS = 0        # 数据加载线程数（0=主线程）
RANDOM_SEED = 42       # 随机种子（保证可重复性）
```

## 辅助工具

### 查看EntrezID对应的化合物数量

```bash
python get_inchikeys_by_entrez.py
```

这会生成 `entrez_id_counts.csv` 文件，显示每个EntrezID关联的化合物数量。

### 检查正样本

```bash
python check_positive_samples.py
```

用于验证特定EntrezID的正样本数据。

### 将InChIKey转换为SMILES

如果你获得了 `filtered_inchikeys.csv`，可以转换为SMILES格式：

```bash
python convert_inchikey_to_smiles.py
```

这个脚本会：
1. 读取 `filtered_inchikeys.csv`
2. 从本地数据库（`D12_InChIKey.tsv`）查找对应的SMILES
3. 生成 `inchikeys_with_smiles.csv`，包含InChIKey和SMILES两列

## 运行示例

```bash
# 1. 完整运行示例
python main.py --entrez_ids "2,19,23"

# 输出示例：
# 2025-07-06 11:12:05 - INFO - ===== 开始为EntrezID集合 '2,19,23' 生成中药排名 =====
# 2025-07-06 11:12:05 - INFO - 本次运行的输出将保存在: outputs\entrez_run_2025-07-06_11-12-05
# 2025-07-06 11:12:05 - INFO - 步骤 1: 查找正样本
# ...
# 2025-07-06 11:15:30 - INFO - ===== 流程成功结束！ =====
# 2025-07-06 11:15:30 - INFO - 最终的中药排名报告已生成: outputs\entrez_run_2025-07-06_11-12-05\final_herb_ranking.csv

# 2. 仅预测示例（使用已有模型）
python predict_only.py --run_id "entrez_run_2025-07-06_11-12-05"
```

## 注意事项

1. **数据依赖**：确保 `TCM_DATA_ROOT` 目录下包含所有必需的数据文件（D6, D9, D12, D13, D19-D24等）

2. **计算资源**：
   - 训练需要较多时间（取决于正样本数量和化合物库大小）
   - 建议使用GPU加速（自动检测）
   - 预测阶段也需要一定时间处理整个化合物库

3. **正样本数量**：如果EntrezID对应的正样本太少（<10），模型效果可能不佳

4. **日志文件**：所有运行信息都会记录在 `outputs/[run_id]/run.log` 中

## 项目结构

```
herb_project/
├── main.py                  # 主入口（完整流程）
├── predict_only.py          # 仅预测模式
├── config.py                # 配置文件
├── requirements.txt         # 依赖列表
├── data_pipeline/           # 数据处理模块
│   ├── data_loader.py      # 数据加载
│   └── data_preparer.py    # 数据准备
├── modeling/                # 建模模块
│   ├── trainer.py          # 模型训练
│   └── predictor.py        # 模型预测
├── scoring/                 # 评分模块
│   └── ranker.py           # 中药排名
├── outputs/                 # 输出目录
└── models/                  # 模型目录
```

## 常见问题

**Q: 如何选择合适的EntrezID？**
A: 可以先运行 `get_inchikeys_by_entrez.py` 查看各EntrezID的化合物数量，选择有足够正样本的EntrezID。

**Q: 训练时间太长怎么办？**
A: 可以在 `config.py` 中减少 `N_ESTIMATORS` 或 `MAX_EPOCHS`，或使用 `predict_only.py` 直接使用已有模型。

**Q: 如何解读排名结果？**
A: `final_score` 越高表示该中药与目标靶点的相关性越强，建议重点关注排名靠前的中药。

## 更新日志

- 2025-07-06: 添加多折交叉验证支持
- 2025-07-05: 实现基于EntrezID的预测流程
- 2025-07-01: 初始版本，支持基于疾病代码的预测

## 联系方式

如有问题，请查看日志文件或联系项目维护者。

