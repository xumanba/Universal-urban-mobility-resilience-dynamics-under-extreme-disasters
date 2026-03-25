"""
San Jose 数据流整合 Pipeline
从 SafeGraph 原始 CSV 出发，计算 Aij → pk → px。
"""
import json
import os
import sys
import numpy as np
import pandas as pd
from collections import Counter

# 禁用 stdout 缓冲，方便查看进度
sys.stdout.reconfigure(line_buffering=True)

# ============================================================
# 输入文件路径
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

INPUT_FILES = {
    '08-14': os.path.join(SCRIPT_DIR, 'CA_SanJose_08-14.csv'),
    '08-21': os.path.join(SCRIPT_DIR, 'CA_SanJose_08-21.csv'),
    '08-28': os.path.join(SCRIPT_DIR, 'CA_SanJose_08-28.csv'),
}

# ============================================================
# Step 1: 从原始 CSV 计算 Aij 矩阵
# 逻辑来源: 48.CA_data.py (Santa Cruz) + 6.get_Aij_dict.py (Dallas)
# ============================================================
def compute_aij(file_path, city='San Jose'):
    """从 SafeGraph CSV 计算 CBG-CBG 交互矩阵 Aij"""
    print(f"  读取 CSV: {os.path.basename(file_path)} ...")
    df = pd.read_csv(file_path, usecols=[
        'city', 'poi_cbg', 'placekey',
        'visitor_home_cbgs', 'normalized_visits_by_state_scaling'
    ])
    city_df = df[df['city'] == city].copy()
    print(f"  {city} 行数: {len(city_df)}")

    # 获取唯一的 CBG 列表 (基于 city 过滤)
    cbg_float_list = list(set(city_df['poi_cbg'].tolist()))
    print(f"  CBG 数量: {len(cbg_float_list)}")

    # 建立 CBG → POI 映射 (key 为 11 位字符串)
    # 关键：使用全量 df 按 poi_cbg 查找 POI，而非 city_df 按 city 查找
    # 因为同一 CBG 中的 POI 可能有不同的 city 名称
    cbg_poi_dict = {}
    for cbg in cbg_float_list:
        pois = df[df['poi_cbg'] == cbg]['placekey'].unique().tolist()
        if len(pois) > 0:
            cbg_poi_dict[str(int(cbg))] = pois
    print(f"  CBG→POI 映射完成: {len(cbg_poi_dict)} 个 CBG")

    # 零填充 CBG key 列表 (12 位, 用于匹配 visitor_home_cbgs)
    cbg_list_12 = ['0' + str(int(x)) for x in cbg_float_list]
    # 构建快速查找字典 (替代 list.index 的 O(n) 查找)
    cbg_12_to_idx = {k: i for i, k in enumerate(cbg_list_12)}
    print(f"  零填充 CBG 列表: {len(cbg_list_12)} 个 key (12 位)")

    # 预建 placekey 查找表 (使用全量 df)
    all_pois = set()
    for pois in cbg_poi_dict.values():
        all_pois.update(pois)

    # 对每个 placekey 预计算 visitor_home_cbgs 和 scaling (使用全量 df)
    poi_vhcbgs = {}
    poi_scaling = {}
    for poi in all_pois:
        rows = df[df['placekey'] == poi]
        if len(rows) == 0:
            continue
        vhcbgs_val = rows['visitor_home_cbgs'].iloc[0]
        nvs_val = rows['normalized_visits_by_state_scaling'].iloc[0]
        if pd.isna(vhcbgs_val):
            poi_vhcbgs[poi] = None
            continue
        temp_dict = eval(vhcbgs_val)
        total_visits = sum(temp_dict.values())
        if total_visits == 0:
            poi_vhcbgs[poi] = None
            continue
        scaling = round(nvs_val / total_visits, 2)
        poi_vhcbgs[poi] = temp_dict
        poi_scaling[poi] = scaling
    print(f"  POI 预处理完成: {len(poi_vhcbgs)} 个 POI")

    # 对每个 CBG 计算交互矩阵行
    dict0 = {}
    cbg_order = list(cbg_poi_dict.keys())
    for idx, key in enumerate(cbg_order):
        pois = cbg_poi_dict[key]
        cbg_total = [0] * len(cbg_list_12)
        for poi in pois:
            if poi_vhcbgs.get(poi) is None:
                continue
            temp_dict = poi_vhcbgs[poi]
            scaling = poi_scaling[poi]
            for k, v in temp_dict.items():
                if k in cbg_12_to_idx:
                    cbg_idx = cbg_12_to_idx[k]
                    cbg_total[cbg_idx] += round(v * scaling)
        dict0[key] = cbg_total
        if (idx + 1) % 100 == 0:
            print(f"    已处理 {idx + 1}/{len(cbg_order)} 个 CBG")

    print(f"  Aij 计算完成: {len(dict0)} 行")
    return dict0


def save_aij(aij_dict, output_path):
    """保存 Aij 矩阵为 JSON"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(aij_dict, f, indent=4, ensure_ascii=False)
    print(f"  已保存: {output_path}")


# ============================================================
# Step 2: 从 Aij 计算 pk (度分布)
# 逻辑来源: 44.pk2csv.py
# ============================================================
def compute_pk(aij_dict):
    """从 Aij 计算 pk (度分布)"""
    Aij_matrix = np.array(list(aij_dict.values()))
    Aij_matrix[Aij_matrix != 0] = 1  # 二值化
    column_sums = np.sum(Aij_matrix, axis=1)  # 行求和 = 出度

    counts = Counter(column_sums)
    counts = {key: counts[key] for key in sorted(counts)}
    counts = {key: value for key, value in counts.items() if key <= 300}

    keys_list = list(counts.keys())
    values_list = list(counts.values())

    bins = np.arange(0, 302, 2)
    binned = pd.cut(keys_list, bins=bins, right=False)
    count_values = pd.Series(values_list).groupby(binned).mean()

    # 确保 150 个 bin 都有值 (空 bin 填 NaN)
    all_bins = pd.IntervalIndex.from_breaks(bins, closed='left')
    count_values = count_values.reindex(all_bins)
    count_list = count_values.tolist()

    numbers_list = [1 + i * 2 for i in range(150)]
    return numbers_list, count_list


# ============================================================
# Step 3: 从 Aij 计算 px (净流入分布)
# 逻辑来源: 45.px2csv.py
# ============================================================
def compute_px(aij_dict):
    """从 Aij 计算 px (净流入分布)"""
    Aij_matrix = np.array(list(aij_dict.values()))
    row_sums = Aij_matrix.sum(axis=1)
    column_sums = Aij_matrix.sum(axis=0)
    jingliuchu = column_sums - row_sums  # 净流入 = 入度 - 出度

    counts = Counter(jingliuchu)
    counts = {key: counts[key] for key in sorted(counts)}
    counts = {key: value for key, value in counts.items() if -500000 <= key <= 500000}

    keys_list = list(counts.keys())
    values_list = list(counts.values())

    bins = np.arange(-500000, 520000, 20000)
    binned = pd.cut(keys_list, bins=bins, right=False)
    count_values = pd.Series(values_list).groupby(binned).sum()

    # 确保 50 个 bin 都有值
    all_bins = pd.IntervalIndex.from_breaks(bins, closed='left')
    count_values = count_values.reindex(all_bins)
    count_list = count_values.tolist()

    numbers_list = [-490000 + i * 20000 for i in range(50)]
    return numbers_list, count_list


# ============================================================
# pk 缩放输出
# ============================================================
def scale_pk_to_fig25(pk_x, pk_values, scale_factor):
    """pk 缩放: pk / scale_factor"""
    y_values = [v / scale_factor if not pd.isna(v) else v for v in pk_values]
    return pk_x, y_values


# ============================================================
# px 处理输出
# ============================================================
def process_px_to_fig32(px_x, px_values, date_label):
    """px 转换为 fig3.2 格式"""
    # 确定参数
    if date_label in ('08-14', '08-28'):
        divisor = 400000
        norm_factor = 18
    else:  # 0821
        divisor = 500000
        norm_factor = 20

    x_values = [x / divisor for x in px_x]
    total = sum(v for v in px_values if not pd.isna(v))
    y_values = [v / total * norm_factor if not pd.isna(v) else v for v in px_values]

    return x_values, y_values


def save_fig_csv(x_values, y_values, output_path):
    """保存 3 列 CSV (index, x, y)"""
    df = pd.DataFrame({'x': x_values, 'y': y_values})
    df.to_csv(output_path, index=True)
    print(f"  已保存: {output_path}")


# ============================================================
# 主流程
# ============================================================
def main():
    print("=" * 60)
    print("San Jose 数据流整合 Pipeline")
    print("=" * 60)

    # ----------------------------------------------------------
    # Phase 1: 计算 Aij
    # ----------------------------------------------------------
    print("\n[Phase 1] 计算 Aij 矩阵")
    aij_dict = {}
    for date_label, file_path in INPUT_FILES.items():
        print(f"\n--- 日期: {date_label} ---")
        aij = compute_aij(file_path)
        aij_dict[date_label] = aij
        # 保存中间结果
        save_aij(aij, os.path.join(OUTPUT_DIR, f'Aij_CA_San Jose_{date_label}.json'))

    # ----------------------------------------------------------
    # Phase 2: 计算 pk 和 px
    # ----------------------------------------------------------
    print("\n[Phase 2] 计算 pk 和 px")
    pk_data = {}
    px_data = {}
    for date_label in INPUT_FILES:
        print(f"\n--- 日期: {date_label} ---")
        pk_x, pk_values = compute_pk(aij_dict[date_label])
        pk_data[date_label] = (pk_x, pk_values)
        print(f"  pk: {len(pk_values)} 个 bin, 非空: {sum(1 for v in pk_values if not pd.isna(v))}")

        px_x, px_values = compute_px(aij_dict[date_label])
        px_data[date_label] = (px_x, px_values)
        print(f"  px: {len(px_values)} 个 bin, 非空: {sum(1 for v in px_values if not pd.isna(v))}")

    # ----------------------------------------------------------
    # Phase 3: pk/px 输出
    # ----------------------------------------------------------
    print("\n[Phase 3] 输出 pk 和 px")

    scale_config = {
        '08-14': ('before', 0.8),
        '08-21': ('during', 0.6),
        '08-28': ('after', 0.8),
    }

    for date_label, (period, factor) in scale_config.items():
        pk_x, pk_values = pk_data[date_label]
        _, scaled_y = scale_pk_to_fig25(pk_x, pk_values, factor)
        save_fig_csv(pk_x, scaled_y, os.path.join(OUTPUT_DIR, f'pk_data_{period}.csv'))

        px_x, px_values = px_data[date_label]
        proc_x, proc_y = process_px_to_fig32(px_x, px_values, date_label)
        save_fig_csv(proc_x, proc_y, os.path.join(OUTPUT_DIR, f'px_data_{period}.csv'))

    # ----------------------------------------------------------
    # 总结
    # ----------------------------------------------------------
    print("\n" + "=" * 60)
    print("Pipeline 完成!")
    print(f"所有输出文件保存在: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == '__main__':
    main()
