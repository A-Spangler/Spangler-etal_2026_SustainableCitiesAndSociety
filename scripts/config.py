# By: Ava Spangler
# Date: 7/16/25
# Description: This code provides paths for Baltimore_SWMM_analysis.py to reference

scenarios = {
    'Base': r"/inputdata/Inner_Harbor_Model_V23.inp",
    'V': r"/inputdata//Inner_Harbor_Model_V23_vacants.inp",
    'I': r"/inputdata/Inner_Harbor_Model_V23_inlets.inp",
    'V&I': r"/inputdata/Inner_Harbor_Model_V23_inlets+vacants.inp"
}

storms = {
    '2x_fullstorm_6_27_23': '6/27/23_fullstorm_x2depth',
    '6_27_23': '6/27/2023',
    '0.5x_fullstorm_6_27_23': '6/27/23_fullstorm_x0.5depth'
}

rpts = {
    'Base': r"/inputdata/Inner_Harbor_Model_V23.rpt",
    'I': r"/inputdata/Inner_Harbor_Model_V23_inlets.rpt",
    'V&I': r"/inputdata/Inner_Harbor_Model_V23_inlets+vacants.rpt",
    'V': r"/inputdata/Inner_Harbor_Model_V23_vacants.inp",
}

model_path = 'inputdata/Inner_Harbor_Model_V23.inp'