import json
import sys
import pandas as pd
import pickle
import tqdm
from geopy.distance import geodesic

pd.set_option('display.max_columns', None)  # 设置最大显示列数为 None，即不限制列数

state = 'CA'
city = 'San Diego'
year = '2023'
date = ['07-24', '07-31', '08-07', '08-14', '08-21', '08-28', '09-04', '09-11', '09-18', '09-25']


# ['06-21', '06-28', '07-05', '07-12', '07-19', '07-26', '08-02', '08-09', '08-16', '08-23', '08-30']
# ['01-02', '01-09', '01-16', '01-23', '01-30', '02-06', '02-13', '02-20', '02-27', '03-06', '03-13', '03-20',
#         '03-27']
# ['07-24', '07-31', '08-07', '08-14', '08-21', '08-28', '09-04', '09-11', '09-18', '09-25']
# ['01-02', '01-09', '01-16', '01-23', '01-30', '02-06', '02-13']
# ['12-05', '12-12', '12-19', '12-26']
# ['11-15', '12-06', '12-13', '12-20', '12-27']
# ['01-03', '01-10', '01-17', '01-24', '01-31', '02-07', '02-14', '02-21', '02-28', '03-07']
def get_cbg_set(file_name):
    safegraph_df = pd.read_csv(file_name)
    condition = safegraph_df['city'] == city
    poi_cbg = safegraph_df[condition]['poi_cbg'].tolist()
    cbgs_list = list(set(poi_cbg))
    return cbgs_list


for x in tqdm.tqdm(date):

    file_name = f'{state}_{year}-{x}.csv'
    cbg_list = get_cbg_set(file_name)
    cbg_list = [str(int(x)) for x in cbg_list]
    cbg_list_keys = set(cbg_list)

    with open('cbg_center_dict.pkl', 'rb') as f:
        cbg_center_dict = pickle.load(f)
    cbg_center_dict = {str(key): value for key, value in cbg_center_dict.items()}

    cbg_center_keys = set(cbg_center_dict.keys())
    cbg_list_dict = {}

    for a in cbg_list_keys:
        if a in cbg_center_keys:
            cbg_list_dict[a] = cbg_center_dict[a]
        else:
            sum_first = 0
            sum_second = 0

            for value in cbg_list_dict.values():
                sum_first += value[0]
                sum_second += value[1]

            avg_first = sum_first / len(cbg_list_dict)
            avg_second = sum_second / len(cbg_list_dict)
            cbg_list_dict[a] = (avg_first, avg_second)

    cbg_lonlat_dict = cbg_list_dict

    dict0 = {}
    for a in tqdm.tqdm(cbg_lonlat_dict):
        point1_lon = cbg_lonlat_dict[a][0]
        point1_lat = cbg_lonlat_dict[a][1]
        coord1 = (point1_lat, point1_lon)
        list1 = []
        for b in cbg_list:
            point2_lon = cbg_lonlat_dict[b][0]
            point2_lat = cbg_lonlat_dict[b][1]
            coord2 = (point2_lat, point2_lon)
            distance = geodesic(coord1, coord2).kilometers
            list1.append(distance)
        dict0[a] = list1

    with open(f'{state}_{city}_{x}_Rij.json', 'w', encoding='utf-8') as f:
        json.dump(dict0, f, indent=4, ensure_ascii=False)
