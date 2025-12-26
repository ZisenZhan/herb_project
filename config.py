import os
from pathlib import Path

# --- 项目根目录 ---
# 使用Path(__file__).resolve().parent来获取当前文件所在目录的父目录，即项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent

# --- 核心数据目录 ---
# 指向存放D1-D24等原始TSV文件的地方
# 请确保这里的路径是正确的
TCM_DATA_ROOT = Path("D:/TCM") 

# --- 项目内部数据路径 ---
# 用于存放每次运行时生成的中间文件和最终结果
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
MODELS_DIR = PROJECT_ROOT / "models"
# 为当前运行创建一个唯一的子目录，以时间戳命名，避免覆盖
RUN_ID = None # 将在主程序中设置

# --- 原始数据文件名 ---
# 这里我们列出需要用到的关键数据文件
# 数据管道将使用这些文件名在TCM_DATA_ROOT中查找文件
DISEASE_ICD11_FILE = "D19_ICD11_CUI.tsv" # 包含 ICD11 -> CUI 的映射
ICD11_MESH_FILE = "D20_ICD11_MeSH.tsv"
ICD11_DOID_FILE = "D21_ICD11_DOID.tsv"

CUI_TARGETS_FILE = "D22_CUI_targets.tsv" # CUI -> EntrezID
MESH_TARGETS_FILE = "D23_MeSH_targets.tsv"
DOID_TARGETS_FILE = "D24_DOID_targets.tsv"

INCHIKEY_ENTREZ_FILE = "D13_InChIKey_EntrezID.tsv" # EntrezID -> InChIKey
HERB_COMPOUNDS_FILE = "D9_CHP_InChIKey.tsv" # 中药 -> InChIKey
HERB_NAMES_FILE = "D6_Chinese_herbal_pieces.tsv" # 中药ID -> 中药名

# --- SMILES 数据 ---
# 用于将InChIKey转换为SMILES的文件，或作为背景/阴性样本
INCHIKEY_SMILES_FILE = PROJECT_ROOT.parent / "牙周炎.csv" # 预计算的SMILES缓存
LOCAL_INCHIKEY_SMILES_TSV = TCM_DATA_ROOT / "D12_InChIKey.tsv" # 从本地TSV文件获取SMILES
UNLABELED_SAMPLES_FILE = PROJECT_ROOT / "chembl29.csv" # 背景化合物库 (ChEMBL29)
SMILES_CACHE_FILE = PROJECT_ROOT / "smiles_cache.csv" # 用于缓存InChIKey-SMILES对

# --- 机器学习模型参数 ---
N_ESTIMATORS = 10  # PU-Bagging中的基学习器数量
MAX_EPOCHS = 20  # 神经网络训练的最大轮次
NUM_WORKERS = 0  # 数据加载器的工作线程数 (0表示在主线程中加载)
RANDOM_SEED = 42 # 随机种子，确保结果可复现

# --- 评分参数 ---
BAYESIAN_ALPHA = 10  # 贝叶斯平均分先验强度 (可调)

# --- 列名配置 ---
# 统一管理数据文件中用到的列名，方便维护
SMILES_COL = 'SMILES'
TARGET_COL = 'label'
INCHIKEY_COL = 'InChIKey'
CHP_ID_COL = 'CHP_ID'
ICD11_CODE_COL = 'ICD11_code'
CUI_COL = 'CUI'
MESH_COL = 'MeSH'
DOID_COL = 'DOID'
ENTREZ_ID_COL = 'EntrezID'
CHINESE_HERB_COL = 'Chinese_herbal_pieces' 