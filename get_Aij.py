import json
import sys
import tqdm
import pandas as pd

pd.set_option('display.max_columns', None)  # 设置最大显示列数为 None，即不限制列数


def get_cbg_set(file_name):
    safegraph_df = pd.read_csv(file_name)
    # poi_cbg = safegraph_df['poi_cbg'].tolist()
    condition = safegraph_df['city'] == 'Santa Cruz'
    poi_cbg = safegraph_df[condition]['poi_cbg'].tolist()
    cbgs_list = list(set(poi_cbg))
    return cbgs_list


def gen_empty_dict(key_list):
    empty_dict = {}
    for a in key_list:
        empty_dict[a] = 0
    return empty_dict


if __name__ == '__main__':

    date = '02-27'
    city = 'Santa Cruz'
    file_name = f'CA_2023-{date}.csv'
    cbg_list = get_cbg_set(file_name)
    safegraph_df = pd.read_csv(file_name)
    cbg_poi_list_dict = {}

    for cbg in tqdm.tqdm(cbg_list):
        condition = safegraph_df['poi_cbg'] == cbg
        placekey = safegraph_df[condition]['placekey']
        placekey_ls = list(set(list(placekey)))
        if len(placekey_ls) > 0:
            cbg_poi_list_dict[str(int(cbg))] = placekey_ls

    dict0 = {}
    cbg_list = [str(int(x)) for x in cbg_list]
    cbg_list = ['0' + item for item in cbg_list]

    for key, v in tqdm.tqdm(cbg_poi_list_dict.items()):
        cbg_total_list = [0] * len(cbg_list)
        for poi in v:
            empty_dict = gen_empty_dict(cbg_list)
            condition = safegraph_df['placekey'] == poi
            visitor_home_cbgs = safegraph_df[condition]['visitor_home_cbgs']
            total_visits = 0
            if not pd.isna(visitor_home_cbgs.array[0]):
                temp_dict = eval(visitor_home_cbgs.array[0])
                for k, v in temp_dict.items():
                    total_visits += v

                normalized_visits_by_state_scaling = safegraph_df[condition]['normalized_visits_by_state_scaling']
                scaling = round(normalized_visits_by_state_scaling.array[0] / total_visits, 2)

                for k, v in temp_dict.items():
                    if k in empty_dict:
                        empty_dict[k] = round(v * scaling)

                values = list(empty_dict.values())
                cbg_total_list = [x + y for x, y in zip(cbg_total_list, values)]

        dict0[key] = cbg_total_list

    with open(f'Aij_CA_{city}_{date}.json', 'w', encoding='utf-8') as f:
        json.dump(dict0, f, indent=4, ensure_ascii=False)
