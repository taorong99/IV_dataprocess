# import IVDataProcess类及辅助函数select_files和create_table.
from IVDataProcess_class import IVDataProcess
from IV_dataprocess_aux import select_files, create_table



# 数据文件格式为'IV', 即第一列为电流I, 第二列为电压V. 电流单位为A, 电压单位为V.
data_type, I_unit, V_unit = "IV", "A", "V"

# 文件路径列表, 手动输入
file_paths = ["data1.csv", "data2.csv", "data3.csv", "data4.csv"]

# 文件路径列表, 使用对话框选择文件, 需要安装tkinter模块
# file_paths = select_files()

ivs = []*len(file_paths) # 创建一个IVDataProcess对象列表
# 遍历文件路径列表, 依次处理数据, 并拟合, 画图
for file_path in file_paths:
    #创建一个IVDataProcess对象
    iv = IVDataProcess(file_path, data_type, I_unit, V_unit)
    ivs.append(iv)

    #读取数据文件
    iv.file_read()

     #计算偏置电压V_offset并去除
    iv.remove_V_offset()

    #矫正V_data的正负号, 防止电阻为负
    iv.Vdata_correct() 

    #判断IV曲线的类型
    iv.curve_classifier() 

    #得到正反向的临界电流
    iv.get_Ic() 

    #拟合电阻R
    iv.fit_R()

    #画图
    iv.plot_IV(save_fig=False)

# 创建一个总结表格
fit_results = [iv.fit_result for iv in ivs]
curve_types = [iv.curve_type for iv in ivs]
create_table(file_paths, fit_results, curve_types, save_table=False)
