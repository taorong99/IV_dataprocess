"""
Created on 2024-09-19 19:41:39.

@author: Tao Rong.
Modified on 2024-11-17 21:12, by Tao Rong. Version 1.0. Procedure-oriented -> Object-oriented.
Modified on 2024-11-18 18:00, by Tao Rong. Version 1.1. Optimize remove_V_offset method, IV_unit_convert method.
Modified on 2024-12-27 22:00, by Tao Rong. Version 1.2. Add get_Rsg method. Add V_sg, Rsg_p, Rsg_m, Rsg_result attributes. Add linestyle parameter in plot_IV method.
Modified on 2025-01-02 12:00, by Tao Rong. Didn't change version number. Add 'JJa' curve type. Add get_Ic_spread and plot_Ic_spread methods.  change {:.2f} to {:.4g} in plot_IV method.
"""
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from scipy.stats import linregress #线性回归用于拟合R
from scipy.stats import zscore #计算V_offset时去除离群点用
from scipy.optimize import minimize
import os

#plt 显示中文
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False


class IVDataProcess:
    """
    IV数据处理类, 用于处理IV曲线数据, 包括读取数据, 去除V_offset, 判断IV曲线类型, 获取Ic, 拟合R等功能.

    Attributes:
        file_path(str): data文件路径. 路径的斜杠必须使用"/".
        data_type(str): 数据类型, 可选IV或VI. 分别代表两列数据是电流电压还是电压电流.
        I_unit(str): 电流单位, 默认为A.
        V_unit(str): 电压单位, 默认为V.
        data_sep(str): IV数据分隔符, 
        V_g(float): 结的gap电压, 默认为2.8e-3V.
        filename(str): 文件名.
        V_offset(float): V_offset值, 默认为0.0. V_offset值是指电压数据中的偏移值.
        fit_result(np.ndarray): 拟合结果数组, 长度为6. 依次是Ic_1, Ic_2, R_fitp, R_fitm, Vintcp_p, Vintcp_m.
        I_data(np.ndarray): 处理后的电流数据.
        V_data(np.ndarray): 处理后的电压数据.
        I_raw(np.ndarray): 原始电流数据.
        V_raw(np.ndarray): 原始电压数据.
        curve_type(str): IV曲线的类型, 可选R, JJu, JJo, JJa.
        Ic_fitp(float): 正向临界电流.
        Ic_fitm(float): 负向临界电流.
        R_fitp(float): 正向拟合电阻.
        R_fitm(float): 负向拟合电阻.
        Vintcp_p(float): 正向R拟合后在V轴的截距.
        Vintcp_m(float): 负向R拟合后在V轴的截距.
        segms(list[dict, dict, dict, dict]): 四段IV曲线的字典. 字典的key是'I'和'V', value是对应的电流和电压数据.
        V_sg(float): subgap电压, 默认为2.0e-3V.
        Rsg_p(float): 正向subgap电阻.
        Rsg_m(float): 负向subgap电阻.
        Rsg_result(tuple): Rsg_p, V1_p, V2_p, Rsg_m, V1_m, V2_m.
        num_JJ(int): IV曲线中的结的个数.
        Vg_optimal(float): JJa数据优化后的gap电压.
        Ic_array(np.ndarray): Ic_spread计算时的Ic数组, 即Ic的可能取值.
        JJ_counts(np.ndarray): Ic_spread计算时的JJ_counts数组, 即每个Ic对应的JJ数.
        n_convolve(int): 对R_diff进行平滑处理时的卷积核大小, 默认为1.

    Methods:
        file_read(): 根据file_path读取数据文件, 得到self.I, self.V两个数组(量纲为A, V), 同时还会保存原始数据在self.I_raw, self.V_raw的两个数组中.
        IV_unit_convert(): 将原始数据转换为指定单位的数据.
        get_separator(): 从文件中读取中间一行数据, 并根据这行数据自动判断分隔符.
        remove_V_offset(): 获取V_offset值, 并将V_data减去offset.
        curve_classifier(): 判断IV曲线的类型, 并返回.
        get_Ic(): 获取Ic_fitp和Ic_fitm, 即正向和负向的临界电流.
        fit_R(): 对IV曲线进行R拟合, 得到Rp和Rm.
        get_Rsg(): 根据JJu类型曲线的回滞段, 得到subgap电阻的Rsg_p和Rsg_m, 以及插值的V1, V2.
        get_Ic_spread(): 计算Ic_spread, 只会对JJa曲线进行计算. 
        IVdata_split_4_segments(): 将数组 I_data和V_data 分成四段: 上升段、下降到零段、下降段、上升到零段.
        Vdata_correct(): 矫正V_data的正负号.
        plot_IV(): 画IV曲线图, 根据I_data和V_data而不是I_raw和V_raw. 画图时会根据IV曲线的类型, 临界电流, R拟合结果, V_g等信息进行标注. 画图时会自动调整电流和电压的单位, 使得数值不会太大或太小.
        plot_Ic_spread(): 画Ic_spread图, 只对JJa曲线有效.
    """

    ALLOWED_DATA_TYPE = ["IV", "VI"]
    
    def __init__(self, file_path: str, data_type: str, I_unit: str="A", V_unit: str="V", data_sep: str=None, V_g: float=2.8e-3, V_sg: float=2.0e-3):
        """
        类初始化函数

        Parameters:
            file_path(str): data文件路径. 路径的斜杠必须使用"/".
            data_type(float): 数据类型, 可选IV或VI. 分别代表两列数据是电流电压还是电压电流.
            I_unit(float): 电流单位, 默认为A.
            V_unit(float): 电压单位, 默认为V.
            data_sep(float): IV数据分隔符, 默认为None, 会自动判断. 手动指定后, 会直接使用该分隔符读取数据文件.
            V_g(float): 结的gap电压, 默认为2.8e-3V. 这个gap电压将用于判断IV曲线的类型, 以及画图时给出V_g的位置, 目前没有自动判断gap电压的功能.
        """
        self.file_path = file_path
        self.data_type = data_type
        self.I_unit = I_unit
        self.V_unit = V_unit
        self.data_sep = data_sep
        self.V_g = V_g
        self.V_sg = V_sg

        self.filename = os.path.basename(file_path)
        self.V_offset = 0.0
        self.fit_result = np.array([None, None, None, None, None, None])
        self.input_check()


    def file_read(self):
        """
        根据file_path读取数据文件, 得到self.I, self.V两个数组(量纲为A, V), 同时还会保存原始数据在self.I_raw, self.V_raw的两个数组中.
        """
        if self.data_sep is None:
            self.data_sep = self.get_separator()
        dataset = pd.read_csv(self.file_path, sep=self.data_sep, header=None, engine='python')
        if self.data_type == 'IV':
            V = dataset.iloc[:, 1].values
            I = dataset.iloc[:, 0].values
        elif self.data_type == 'VI':
            I = dataset.iloc[:, 1].values
            V = dataset.iloc[:, 0].values

        #将前面几行不是数字的数据去掉
        start_row = 0
        for i in range(len(I)):
            try:
                float(I[i])
                float(V[i])
                start_row = i
                break
            except:
                continue

        #将I和V由string转为float
        I_raw = np.array([float(i) for i in I[start_row:]])
        V_raw = np.array([float(v) for v in V[start_row:]])
        I_data, V_data = self.IV_unit_convert(I_raw, V_raw, self.I_unit, self.V_unit)        

        self.I_data, self.V_data = I_data, V_data
        self.I_raw, self.V_raw = I_raw, V_raw
        return I_data, V_data, I_raw, V_raw

    def IV_unit_convert(self, I_raw: np.ndarray, V_raw: np.ndarray, I_unit: str, V_unit: str) -> tuple[np.ndarray, np.ndarray]:
        """
        将原始数据转换为指定单位的数据.

        Parameters:
            I_raw(np.array): 原始电流数据.
            V_raw(np.array): 原始电压数据.
            I_unit(str): 电流单位.
            V_unit(str): 电压单位.
        
        Returns:
            I_data(np.ndarray): 转换后的电流数据.
            V_data(np.ndarray): 转换后的电压数据.
        """
        I_data, V_data = I_raw.copy(), V_raw.copy()
        #I_unit, V_unit = I_unit.replace('A', ''), V_unit.replace('V', '')
        for multiplier,suffix in zip([1e-15, 1e-12, 1e-9, 1e-6, 1e-3, 1e3, 1e6, 1e9, 1e12], ['f', 'p', 'n', 'u', 'm', 'k', 'M', 'G', 'T']):
            if suffix in I_unit[0]:
                I_data =I_raw * multiplier
                break
        for multiplier,suffix in zip([1e-15, 1e-12, 1e-9, 1e-6, 1e-3, 1e3, 1e6, 1e9, 1e12], ['f', 'p', 'n', 'u', 'm', 'k', 'M', 'G', 'T']):
            if suffix in V_unit[0]:
                V_data = V_raw * multiplier
                break
        return (I_data, V_data)

    def get_separator(self):
        """
        从文件中读取中间一行数据, 并根据这行数据自动判断分隔符.

        Returns:
            sep(str): IV数据分隔符.
        """
        f = open(self.file_path, "r")
        lines = f.readlines()
        f.close()
        middle_line = lines[len(lines) // 2].replace("\n", "").lstrip() #自动删除行尾换行以及行首空格
        #从左到右尝试, 记录第一个不是数字的索引left_index. 从右到左尝试, 记录第一个不是数字的索引right_index
        for i in range(len(middle_line)):
            if not middle_line[i].isdigit() and middle_line[i] not in [".", "e", "E", "-", "+"]:
                left_index = i
                break
        for i in range(len(middle_line) - 1, -1, -1):
            if not middle_line[i].isdigit() and middle_line[i] not in [".", "e", "E", "-", "+"]:
                right_index = i
                break
        try:
            sep = middle_line[left_index:right_index+1]
        except Exception as e:
            print(e)
            print('Get separator error. filename:', self.filename)
            return '\t'
        sep = '  ' if list(filter(None, sep.split(' '))) == [] else sep #如果分隔符是多个空格，则全部替换为两个空格
        self.data_sep = sep
        return sep
    
    def remove_V_offset(self, V_offset_threshold = 0.2e-4) -> float:
        """
        获取V_offset值, 并将V_data减去offset. V_offset值是指电压数据中的偏移值, 用于修正电压数据. 该方法根据I_data数组中绝对值小于10uA的数据进行计算V_offset. 计算过程中两次使用zscore去除离群点.

        Parameters:
            V_offset_threshold(float): V_offset阈值, 默认为0.2e-4. 计算得到的V_offset值大于该阈值才有效. 否则V_offset=0.
        Returns:
            V_offset(float): V_offset值.
        """
        I_abs = np.abs(self.I_data)

        V_offset_calarray = self.V_data[I_abs<10e-6] #用于计算V_offset的array
        if V_offset_calarray.size == 0:
            print('No data for V_offset calculation.')
            V_offset_calarray = self.V_data[np.argsort(abs(self.I_data))[:5]]
        #去掉离群点, 使得V_offset更准确. zscore表示数据点与平均值相距zscore个标准差.
        if V_offset_calarray[np.abs(zscore(V_offset_calarray)) < 1].size >= 1:
            V_offset_calarray = V_offset_calarray[np.abs(zscore(V_offset_calarray)) < 1]
        if len(V_offset_calarray) > 1 and V_offset_calarray[np.abs(zscore(V_offset_calarray)) < 2].size >= 1:
            V_offset_calarray = V_offset_calarray[np.abs(zscore(V_offset_calarray)) < 2]

        V_offset = np.mean(V_offset_calarray)
        # print('V_offset calculated from I<10uA data:', V_offset)
        if abs(V_offset) < V_offset_threshold:
            V_offset = 0.0

        self.V_noise = np.std(V_offset_calarray) * 3
        self.V_offset = V_offset
        self.V_data = self.V_data - self.V_offset
        return V_offset
    
    def remove_offset(self, I_offset_threshold=1e-6, V_offset_threshold=0.01e-3):
        """
        取出I_data和V_data中的offset. JJa和JJu曲线使用I下降段的数据, 其他曲线使用所有数据.
        如果是半边扫描的数据, 即I>0或I<0的数据点不足2个, 则根据I最接近0的两个点来计算V_offset.
        阈值和最大值的0.01倍中较小的作为有效阈值.
        如果是正负扫描的数据, 则将正负段分为对照组与数据处理组, 用对照组中的每个I, 在数据处理组中进行插值, 然后记录结果差, V_offset就是结果差的均值. 处理完V_offset后, 再用同样的方法计算I_offset. 
        对于实际测试数据的特点, 必须要先去除V_offset, 才能有效计算I_offset.
        
        Parameters:
            I_offset_threshold(float): I_offset阈值, 默认为1e-6A. 该阈值和0.01倍最大数据中的较小者作为有效阈值, 计算得到的I_offset值大于有效阈值才有效. 否则I_offset=0.
            V_offset_threshold(float): V_offset阈值, 默认为0.01e-3V. 该阈值和0.01倍最大数据中的较小者作为有效阈值, 计算得到的V_offset值大于有效阈值才有效. 否则V_offset=0.
        Returns:
            I_offset(float): I_offset值.
            V_offset(float): V_offset值.
        """
        if not hasattr(self, 'curve_type'):
            self.curve_classifier()
        if not hasattr(self, 'segms'):
                self.IVdata_split_4_segments(self.I_data, self.V_data)
        if self.curve_type == 'JJa' or self.curve_type == 'JJu':
            I_calarray = np.concatenate([self.segms[1]['I'], self.segms[3]['I']])
            V_calarray = np.concatenate([self.segms[1]['V'], self.segms[3]['V']])
            print(len(I_calarray[I_calarray>0]), len(I_calarray[I_calarray<0]))
        else:            
            I_calarray = self.I_data
            V_calarray = self.V_data
        # 按照I递增来排序, 因为后面插值要求递增
        # I_calarray, V_calarray = zip(*sorted(zip(I_calarray, V_calarray), key=lambda x: x[0]))
        # I_calarray, V_calarray = np.array(I_calarray), np.array(V_calarray)
        # plt.figure()
        # plt.plot(V_calarray, I_calarray, 'o-', markersize=3)
        # plt.show()
        
        if len(I_calarray[I_calarray>0]) < 2 or len(I_calarray[I_calarray<0]) < 2:
            # 如果是半边扫描的数据, 即I>0或I<0的数据点不足2个, 则只根据I最接近0的两个点来计算V_offset.
            I_calarray = I_calarray[np.argsort(abs(I_calarray))[:2]]
            V_calarray = V_calarray[np.argsort(abs(I_calarray))[:2]]
            V_offset = np.mean(V_calarray)
            if abs(V_offset) < V_offset_threshold and abs(V_offset) < 0.01*abs(V_calarray).max():
                V_offset = 0.0
            self.V_data = self.V_data - V_offset
            self.V_offset = V_offset
            self.I_offset = 0.0
            print('V_offset calculated from two branches:', V_offset)
            self.IVdata_split_4_segments(self.I_data, self.V_data)
            return V_offset, 0.0
        
        # 去除I_calarray和V_calarray中符号相异的点
        mask = (I_calarray >= 0) & (V_calarray >= 0) | (I_calarray <= 0) & (V_calarray <= 0)
        I_calarray = I_calarray[mask]
        V_calarray = V_calarray[mask]

        # 长度小的作为对照组, 长度大的作为数据处理组
        if len(I_calarray[I_calarray>0]) <= len(I_calarray[I_calarray<0]):
            I_control = I_calarray[I_calarray>0]
            V_control = V_calarray[I_calarray>0]
            I_process = I_calarray[I_calarray<0]
            V_process = V_calarray[I_calarray<0]
        else:
            I_control = I_calarray[I_calarray<0]
            V_control = V_calarray[I_calarray<0]
            I_process = I_calarray[I_calarray>0]
            V_process = V_calarray[I_calarray>0]

        # 先粗矫一轮offset, 根据对照组的最远点, 找到数据处理组中最接近的点, 计算两者的平均值作为粗矫offset
        V_offset_rough = 0.0
        pass
        
        # 对于对照组中的每个I, 在数据处理组中进行插值, 然后记录结果差, 插值用的I必须在±90%范围内
        V_offs = []
        sort_indeices = np.argsort(I_process)
        I_process, V_process = I_process[sort_indeices], V_process[sort_indeices]
        for i, v in zip(I_control, V_control):
            mask = (abs(I_process)>abs(i*0.9)) & (abs(I_process)<abs(i*1.1))
            # print(i,I_process)
            if len(I_process[mask]) >= 2:
                V_interp = np.interp(-i, I_process[mask], V_process[mask])
                # print(i,v,V_interp)
                V_offs.append(0.5*(v + V_interp))
        #去除离群点
        V_offs = np.array(V_offs)
        V_offs = V_offs[abs(V_offs - np.mean(V_offs)) < 2*np.std(V_offs)]
        V_offset = np.mean(V_offs) if len(V_offs) > 0 else 0.0
        # if abs(V_offset) < V_offset_threshold and abs(V_offset) < 0.01*abs(self.V_data).max():
        #     V_offset = 0.0
        # self.V_offset = V_offset
        self.V_data = self.V_data - V_offset
        print('V_offset calculated from two branches:', V_offset)

        # 处理完V_offset后, 再用同样的方法计算I_offset. 这里必须要先去除V_offset, 才能有效计算I_offset.
        V_control = V_control - V_offset
        V_process = V_process - V_offset
        I_offs = []
        sort_indeices = np.argsort(V_process)
        I_process, V_process = I_process[sort_indeices], V_process[sort_indeices]
        for i, v in zip(I_control, V_control):
            mask = (abs(V_process)>abs(v*0.9)) & (abs(V_process)<abs(v*1.1))
            if len(V_process[mask]) >= 2:
                I_interp = np.interp(-v, V_process[mask], I_process[mask])
                I_offs.append(0.5*(i + I_interp))
        I_offset = np.mean(I_offs) if len(I_offs) > 0 else 0.0
        # if abs(I_offset) < I_offset_threshold and abs(I_offset) < 0.01*abs(self.I_data).max():
        #     I_offset = 0.0
        self.I_data = self.I_data - I_offset
        print('I_offset calculated from two branches:', I_offset)
        print(f'V_offset/I_offset: {V_offset/I_offset}')
        self.IVdata_split_4_segments(self.I_data, self.V_data)

    def curve_classifier(self) -> str:
        """
        判断IV曲线的类型, 并返回. IV曲线的类型有R, JJu, JJo, JJa四种, 将来支持JJs等. 首先根据I_data和V_data在首尾的20个点线性拟合结果, 25%以内认为是R. 如果不是R, 则根据V_data的回滞绝对值是否大于V_g/4和1.5Vg判断是JJu还是JJo.

        Returns:
            curve_type(str): IV曲线的类型, 可选R, JJu, JJo.
        """
        # 取I的最小二十个点和最大二十个点的线性拟合比较, 如果两者拟合的R25%以内, 则认为是R.
        I_min20, V_min20 = self.I_data[np.argsort(abs(self.I_data))[:20]], self.V_data[np.argsort(abs(self.I_data))[:20]]
        I_max20, V_max20 = self.I_data[np.argsort(abs(self.I_data))[-20:]], self.V_data[np.argsort(abs(self.I_data))[-20:]]
        slope_min20, Vintcp_min20, r_value_min20, p_value_min20, std_err_min20 = linregress(I_min20, V_min20) #斜率、截距、相关系数r、p值和标准误差。
        if r_value_min20 < 0.9:
            slope_min20 = 0.0
        slope_max20, Vintcp_max20, r_value_max20, p_value_max20, std_err_max20 = linregress(I_max20, V_max20) #斜率、截距、相关系数r、p值和标准误差。

        if abs(slope_min20-slope_max20) < 0.25*max(abs(slope_min20), abs(slope_max20)):
            curve_type = 'R'
        else:
            #将I按从小到大排序, V对应I的排序. 如果V相邻差值可以大于Vg/4, 则认为是JJu, 否则是JJo.
            V_sort = self.V_data[np.argsort(self.I_data)]
            V_diff = np.diff(V_sort)
            V_hyster = np.max(abs(V_diff)) # 回滞电压
            if V_hyster > 1.5*self.V_g:
                curve_type = 'JJa'
            elif V_hyster > self.V_g/4:
                curve_type = 'JJu'
            else:
                curve_type = 'JJo'

        self.curve_type = curve_type
        return curve_type

    def get_Vg(self) -> float:
        """
        根据正向扫描的回滞段得到Vg值.
        """
        if self.curve_type != 'JJu' and self.curve_type != 'JJa':
            return 0.0
        if not hasattr(self, 'segms'):
            self.IVdata_split_4_segments(self.I_data, self.V_data)
        IV_segments = self.segms

        I_hyst = IV_segments[1]['I'] #回滞段的电流
        V_hyst = IV_segments[1]['V'] #回滞段的电压
        if len(I_hyst) < 2 or len(V_hyst) < 2:
            print('No hysteresis data for Vg calculation.')
            return 0.0
        I_diff = np.diff(I_hyst)
        V_diff = np.diff(V_hyst)
        R_diff = V_diff/(I_diff+1e-9) + 1e-9 # 1e-9是为了避免分母为0
        # 移除电阻离群点
        R_diff[np.abs(R_diff - np.median(R_diff)) > 3*np.std(R_diff)] = np.nan
        # R_diff最大点对应的电压取为Vg, 后1/4点赋nan, 以免影响判断
        R_diff[-len(R_diff)//4:] = np.nan
        Vg_fit = V_hyst[np.nanargmax(R_diff)]

        # plt.figure()
        # plt.plot(I_hyst[1:], R_diff, 'o-', markersize=3, label='R_diff')
        # plt.show()

        return Vg_fit

    
    def get_phi_halfpi(self, I: np.ndarray, V: np.ndarray) -> list:
        """
        计算IV曲线中转角接近90度的点的电流值. 这里的IV曲线只能是一段, 或者说是单向的.

        Parameters:
            I(np.ndarray): 电流数据.
            V(np.ndarray): 电压数据.

        Returns:
            index_and_phi(list): 一个列表, 第一个元素是转角接近90度的点的索引, 第二个元素是该点的转角值(单位:弧度).
        """        
        V_diff = abs(np.diff(V)) #电压差分
        if self.curve_type == 'JJa':
            I_diff = abs(np.diff(I))*1e3 # JJa的V一般很大, 因此需要同步提升I的单位, 以便计算转角
        else:
            I_diff = abs(np.diff(I)) #电流差分 
        R_diff = V_diff/(I_diff+1e-9) + 1e-9 # 1e-9是为了避免分母为0
        R_0 = abs(V/(I+1e-9)) + 1e-9 # 1e-9是为了避免分母为0

        #取IV曲线上转角接近90度的点, 即直流电阻和差分电阻曲线夹角最小的点
        phi = np.pi + np.arctan(1/R_diff) - np.arctan(1/R_0[0:-1])
        phi = (phi + np.pi) % (2 * np.pi) - np.pi #将phi限制在[-pi,pi]范围内
        phi_diff90 = abs(abs(phi - np.pi/2))#/(I[1:]+1e-10)) # 1e-10是为了避免分母为0

        index_halfpi = np.argmin(phi_diff90)
        return [index_halfpi, phi[index_halfpi]]

    def get_Ic(self, Ic_ests: list = [None, None]) -> tuple[float, float]:
        """
        获取Ic_fitp和Ic_fitm, 即正向和负向的临界电流. 对于'R'类型的IV曲线, Ic_fitp和Ic_fitm都是0.0. 对于'JJu'和'JJo'类型的IV曲线, Ic_fitph和Ic_fitm由直流电阻和差分电阻的转角决定.

        Parameters:
            Ic_ests(list): 初始估计的Ic值, 用于拟合Ic_fitp和Ic_fitm. 单位为A. 如果不指定, 则默认使用[None, None], 即不使用初始估计值. 拟合时会在Ic_ests的±15%范围内搜索最优解, 如果±15%内不足3个数据点, 则.

        Returns:
            Ic_fitp(float): 正向临界电流.
            Ic_fitm(float): 负向临界电流.
        """
        if not hasattr(self, 'n_convolve'):           
            self.n_convolve = 1
        if self.n_convolve < 1:
            self.n_convolve = 1
        n_convolve = self.n_convolve
        
        if self.curve_type == 'R':
            Ic_fitp, Ic_fitm = 0.0, 0.0
        
        else:
            if not hasattr(self, 'segms'):
                self.IVdata_split_4_segments(self.I_data, self.V_data)
            IV_segments = self.segms
            
            Ic_seg = np.array([0.0,0.0,-0.0,-0.0]) #len(IV_segments)=4
            phi_seg = Ic_seg.copy() #存储Ic对应的转角值, 弧度
            for n, seg in enumerate(IV_segments):
                if (self.curve_type == 'JJu' or self.curve_type == 'JJa') and (n==1 or n==3): #回滞结的回滞段没法判断Ic
                    Ic_seg[n] = Ic_seg[n-1]
                    continue

                I, V = seg['I'], seg['V']
                if len(I) <= 2:
                    continue

                # I,V按照I绝对值从小到达排列, 并且归一化
                I, V = zip(*sorted(zip(I, V), key=lambda x: abs(x[0])))
                I, V = np.array(I), np.array(V)
                I_norm, V_norm = abs(I).max(), abs(V).max()
                I = I/I_norm
                V = V/V_norm

                if n_convolve > 1:
                    V = np.convolve(V, np.ones(n_convolve)/n_convolve, mode='same')
                    index_convo = np.ceil(n_convolve/2).astype(int)
                    I = I[index_convo-1: -(index_convo-1)].copy()
                    V = V[index_convo-1: -(index_convo-1)].copy()

                if (n==0 or n==1) and Ic_ests[0] is not None:
                    mask = (I>Ic_ests[0]*0.85) & (I<Ic_ests[0]*1.15)
                    if len(I[mask]) < 3: #不足3个点则补齐
                        mask = np.argsort(abs(I-Ic_ests[0]))[:3]
                        mask = np.sort(mask)
                    V = V[mask]
                    I = I[mask]
                elif (n==2 or n==3) and Ic_ests[1] is not None:
                    mask = (I<Ic_ests[1]*0.85) & (I>Ic_ests[1]*1.15)
                    if len(I[mask]) < 3: #不足3个点则补齐
                        mask = np.argsort(abs(I-Ic_ests[1]))[:3]
                        mask = np.sort(mask)
                    V = V[mask]
                    I = I[mask]
                
                index_halfpi, phi_seg[n] = self.get_phi_halfpi(I, V)

                # 对于JJo, 如果大于Ic的点, 存在连续两个点的V小于Ic点的V, 则在Ic,Imax之间再找一轮Ic
                if self.curve_type == 'JJo':
                    for m in range(10):
                        I_above_Ic = I[index_halfpi+1:]
                        V_above_Ic = V[index_halfpi+1:]
                        for i in range(len(I_above_Ic)-1):
                            index_halfpi1 = 0
                            if abs(V_above_Ic[i]) < abs(V[index_halfpi+1]) and abs(V_above_Ic[i+1]) < abs(V[index_halfpi+1]):
                                index_halfpi1, phi_seg[n] = self.get_phi_halfpi(I_above_Ic, V_above_Ic)
                                index_halfpi = index_halfpi + 1 + index_halfpi1
                                break
                        if index_halfpi1 == 0:
                            print(f'Recalculate Ic for JJo. Seg number: {n}, iteration times: {m}') if m>0 else None
                            break
    
                Ic_seg[n] = I[index_halfpi]* I_norm
                # print(phi_seg[n], Ic_seg[n])

            Ic_fitp = Ic_seg[np.argmin([abs(phi_seg[0]-np.pi/2), abs(phi_seg[1]-np.pi/2)])]
            Ic_fitm = Ic_seg[2+np.argmin([abs(phi_seg[2]-np.pi/2), abs(phi_seg[3]-np.pi/2)])]
        self.Ic_fitp, self.Ic_fitm = Ic_fitp, Ic_fitm
        self.fit_result[0], self.fit_result[1] = Ic_fitp, Ic_fitm
        return (Ic_fitp, Ic_fitm)
            
    def fit_R(self) -> tuple[float, float, float, float]:
        """
        对IV曲线进行R拟合, 得到Rp和Rm. 对于'R'类型的IV曲线, Rp和Rm相等, 都是根据全局数据拟合的, 并不是正方向分段. 对于'JJu', 筛选V>1.1*Vg的后半段数据进行拟合. 对于'JJo', 筛选I>0.5*Ic的后半段数据进行拟合.

        Returns:
            (R_fitp, R_fitm, Vintcp_p, Vintcp_m): Rp, Rm, Vp, Vm.
        """

        V_g = self.V_g
        I, V = self.I_data, self.V_data
        if self.curve_type == 'R':
            try:
                slope, intercept, r_value, p_value, std_err = linregress(I, V) #斜率、截距、相关系数r、p值和标准误差。
                R_fitp, R_fitm = slope, slope
                Vintcp_p, Vintcp_m = intercept, intercept
            except Exception as e:
                print(e)
                print('R fitting error')
                R_fitp, R_fitm = 0.0, 0.0
                Vintcp_p, Vintcp_m = 0.0, 0.0
        else:
            #-------------筛选用于拟合的数据-------------#
            if self.curve_type == 'JJu':
                V_plimit = (1.1*V_g + V.max()) * 0.5
                V_mlimit = (-1.1*V_g + V.min()) * 0.5
                V_data_fitp, I_data_fitp = V[V>V_plimit], I[V>V_plimit] #正方向的R拟合所用数据
                V_data_fitm, I_data_fitm = V[V<V_mlimit], I[V<V_mlimit] #负方向的R拟合所用数据
            elif self.curve_type == 'JJo':
                I_plimit = (self.Ic_fitp + I[V<0.9*V_g].max()) * 0.5
                I_mlimit = (self.Ic_fitm + I[V>-0.9*V_g].min()) * 0.5
                V_data_fitp, I_data_fitp = V[I>I_plimit], I[I>I_plimit] #正方向的R拟合所用数据
                V_data_fitm, I_data_fitm = V[I<I_mlimit], I[I<I_mlimit] #负方向的R拟合所用数据
            elif self.curve_type == 'JJa':
                if not hasattr(self, 'num_JJ'):
                    self.get_Ic_spread()
                V_plimit = (1.1*self.num_JJ*V_g + V.max()) * 0.5
                V_mlimit = (-1.1*self.num_JJ*V_g + V.min()) * 0.5
                V_data_fitp, I_data_fitp = V[V>V_plimit], I[V>V_plimit] #正方向的R拟合所用数据
                V_data_fitm, I_data_fitm = V[V<V_mlimit], I[V<V_mlimit] #负方向的R拟合所用数据
            else:
                R_fitp, R_fitm = 0.0, 0.0
                Vintcp_p, Vintcp_m = 0.0, 0.0 
                print('Warning: R fitting error, .Curve_type should be R, JJu, JJo or JJa.')
            #\-------------筛选用于拟合的数据\-------------#

            #-------------Rp和Rm拟合-------------#
            try:
                if len(I_data_fitp) > 3:
                    R_fitp, Vintcp_p, r_value, p_value, std_err = linregress(I_data_fitp, V_data_fitp) #斜率、截距、相关系数r、p值和标准误差。
                else:
                    R_fitp, Vintcp_p = 0.0, 0.0
                if len(I_data_fitm) > 3:
                    R_fitm, Vintcp_m, r_value, p_value, std_err = linregress(I_data_fitm, V_data_fitm) #斜率、截距、相关系数r、p值和标准误差。
                else:
                    R_fitm, Vintcp_m = 0.0, 0.0
            except Exception as e:
                print(e)
                print('R fitting error')
            
                R_fitp, R_fitm = 0.0, 0.0
                Vintcp_p, Vintcp_m = 0.0, 0.0
            #\-------------Rp和Rm拟合\-------------#
        self.fit_result[2], self.fit_result[3], self.fit_result[4], self.fit_result[5] = R_fitp, R_fitm, Vintcp_p, Vintcp_m
        self.R_fitp, self.R_fitm, self.Vintcp_p, self.Vintcp_m = R_fitp, R_fitm, Vintcp_p, Vintcp_m
        return (R_fitp, R_fitm, Vintcp_p, Vintcp_m)
    
    def get_Rsg(self) -> tuple[float, float, float, float, float, float]:
        """
        根据JJu类型曲线的回滞段, 得到subgap电阻的Rsg_p和Rsg_m.
        Rsg_p和Rsg_m是在V=±V_sg处的电阻值.
        如果V_sg正好在数据中, 则直接取该点的I值计算Rsg = V_sg/I.
        如果V_sg不在数据中, 则取V_sg左右两个点, 并作线性插值得到I_sg. 计算Rsg = V_sg/I_sg.

        Returns:
            tuple (float, float, float, float, float, float):
            Rsg_p, V1_p, V2_p, Rsg_m, V1_m, V2_m.
            分别是正负向的subgap电阻和选取电压点的值.
        """
        if self.curve_type != 'JJu':
            self.Rsg_result = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
            return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        IV_segments = self.segms
        Ip, Vp = IV_segments[1]['I'], IV_segments[1]['V']
        Im, Vm = IV_segments[3]['I'], IV_segments[3]['V']
        Ip, Vp = Ip[np.argsort(Vp)], Vp[np.argsort(Vp)]
        Im, Vm = Im[np.argsort(Vm)], Vm[np.argsort(Vm)]

        Rsg_result = [0.0] * 6

        for n, I, V, V_sg in zip([0, 1], [Ip, Im], [Vp, Vm], [self.V_sg, -self.V_sg]):
            if len(I) < 2:
                continue
            if V_sg in V:
                I_sg = I[V == V_sg][0]
                V1, V2 = V_sg, V_sg
            else:
                # 上下边界寻找
                l_index, u_index = np.where(V < V_sg)[0][-1], np.where(V > V_sg)[0][0]
                I1, I2 = I[l_index], I[u_index]
                V1, V2 = V[l_index], V[u_index]
                I_sg = I1 + (I2 - I1) / (V2 - V1) * (V_sg - V1)
            Rsg = V_sg / I_sg
            Rsg_result[n * 3] = Rsg
            Rsg_result[n * 3 + 1] = V1
            Rsg_result[n * 3 + 2] = V2

        self.Rsg_p, self.Rsg_m = Rsg_result[0], Rsg_result[3]
        self.Rsg_result = tuple(Rsg_result)

        return tuple(Rsg_result)
    

    def get_Ic_spread(self, sigma:float=0.02, print_info:bool=False) -> tuple[np.ndarray, list, float]:
        """
        根据JJa的数据, 计算Ic的分布.
        会选取V的差分大于self.V_g/3的区间, 并根据这个区间的V_diff进行优化, 得到最优的Vg_optimal.
        优化的原理是改变Vg, 计算V_diff中每个数与Vg的整数倍的误差, 使得误差最小. 
        误差最小的Vg即为优化后的Vg_optimal. 
        再根据Vg_optimal, 计算每个Ic对应的结数量.
        如果curve_type不是JJa, 则返回([], [], self.V_g).

        Args:
            sigma(float): 优化Vg时的搜索范围, 默认为0.1. 即Vg的取值范围为self.V_g*(1-sigma)到self.V_g*(1+sigma).
            print_info(bool): 是否打印程序运行信息, 默认为False.

        Returns:
            tuple(np.ndarray, list, float): 分别对应Ic_array, counts, Vg_optimal. 即Ic的可能取值, 每个Ic对应的结数量, 优化后的Vg取值.
        """   
        if self.curve_type != 'JJa':
            self.Vg_optimal = self.V_g
            if self.curve_type == 'R':
                self.num_JJ = 0
            else:
                self.num_JJ = 1
            return ([], [], self.V_g)
        
        def error_function(Vg:float, V_diff:list) -> float:
            """
            误差函数: 计算V_diff中每个数与Vg的整数倍的误差. 
            该函数用于scipy.optimize.minimize函数, 求解误差最小的Vg, 即优化后的Vg_opt.
            还需要讨论residuals是直接取mod, 还是mod/count. 
            目前看mod/count在结数量多时会特别小.

            Args:
                Vg(float): 预设的gap电压.
                V_diff(list): 电压差值列表. 每个元素是实验上测到的一个电压差值.

            Returns:
                tuple(float): 误差值. 即V_diff中每个数与Vg的整数倍的误差的绝对值之和.

            """
            # V1 = np.array((V_diff[0], V_diff[-1]))
            # counts = np.round(V_diff / Vg)
            mod = abs(np.round(V_diff / Vg)- V_diff/Vg)
            residuals = np.sum(mod)
            
            return residuals
        
        # 从IV数据中获取V_diff
        V = self.segms[0]['V']
        I = self.segms[0]['I']
        V_diff = np.diff(V)
        minarg = np.argwhere(V_diff > self.V_g/3)[0][0]
        # maxarg = np.argwhere(V_diff[minarg:] < self.V_g/3)[0][0] + minarg
        # 连续3个点小于V_g/3才有效, 是否要考虑绝对值防止负阻?
        for n in range(minarg, len(V_diff)-3):
            if V_diff[n] < self.V_g/3 and V_diff[n+1] < self.V_g/3 and V_diff[n+2] < self.V_g/3 and abs(V[n]-self.get_Vg()) < self.get_Vg()/4:
                maxarg = n
                break
            maxarg = len(V_diff) - 1 # 如果没有找到, 则取到最后一个点

        if self.get_Vg() != 0.0:
            Vg_index = np.argmin(abs(V - self.get_Vg()))
            if maxarg > Vg_index:
                maxarg = Vg_index
                
        V_diff = np.diff(V[minarg:maxarg+1]).flatten()
        
        # 使用优化方法最小化误差
        result = minimize(error_function, x0=self.V_g, args=(V_diff), bounds=[(self.V_g*(1-sigma), self.V_g*(1+sigma))])


        Vg_optimal = result.x[0] # 优化后的Vg取值
        counts = np.array([round(V/Vg_optimal) for V in V_diff]) # 每个Ic对应的结数量
        Ic_array = I[minarg:maxarg].flatten() # Ic可能取值的列表
        self.Vg_optimal = Vg_optimal
        self.JJ_counts = counts
        self.num_JJ = sum(counts)
        self.Ic_array = Ic_array

        # 打印信息
        if print_info:
            print(f"优化后的V_g为: {Vg_optimal*1e3:.3f}mV, 搜索范围为：{self.V_g*(1-sigma)*1e3:.4f}-{self.V_g*(1+sigma)*1e3:.4f}mV")
            print(f'Ic 为{np.array(I[minarg:maxarg])*1e3}mA的结的数目分别为{counts}, 共{sum(counts)}个结。')
            print(f'电压差{np.diff(V[minarg:maxarg+1])*1e3}mV')

        return Ic_array, counts, Vg_optimal


    def IVdata_split_4_segments(self, I_data: np.ndarray, V_data: np.ndarray) -> list[dict, dict, dict, dict]:
        """
        将数组 I_data和V_data 分成四段: 上升段、下降到零段、下降段、上升到零段. 对应IV曲线的四个区间. 四段区间的首尾取值是有重复的, 例如上升段最后一个点和下降到零段的第一个点是重复的.
        该函数可以识别I从0扫到最大再到最小, 也可以I从0先扫到最小再最大. 即正反的IV曲线. 但最小到最大间必须是连续的.

        Parameters:
            I_data(np.ndarray): 电流数据.
            V_data(np.ndarray): 电压数据.
        
        Returns:
            segms(list[dict, dict, dict, dict]): 四段IV曲线的字典. 字典的key是'I'和'V', value是对应的电流和电压数据.
        """
        I, V = I_data, V_data
        incres_seg, decres_to_zero_seg, decres_seg, incres_to_zero_seg = {}, {}, {}, {} #四段IV曲线的字典
        # 找到最大值和最小值的位置
        max_index = np.argmax(I)  # 最大值的位置
        min_index = np.argmin(I)  # 最小值的位置

        #找到最大值和最小值中间的零点, 即绝对值最小的点
        down, up = (max_index, min_index) if max_index < min_index else (min_index, max_index) #down和up是按小-大顺序排好的max_index和min_index.
        zero_index = np.argmin(np.abs(I[down:up])) + down #电流最小值和最大值之间的零点index.

        if max_index < min_index:
            incres_seg['I'], incres_seg['V'] = [I[:down+1], V[:down+1]] # increasing segment上升段
            decres_to_zero_seg['I'], decres_to_zero_seg['V'] = [I[down:zero_index+1], V[down:zero_index+1]] # decreasing to zero segment下降到零段
            decres_seg['I'], decres_seg['V'] = [I[zero_index:up+1], V[zero_index:up+1]] # decreasing segment下降段
            incres_to_zero_seg['I'], incres_to_zero_seg['V'] = [I[up:], V[up:]] # increasing to zero segment上升到零段
        else: 
            incres_seg['I'], incres_seg['V'] = [I[zero_index:up+1], V[zero_index:up+1]] # increasing segment上升段
            decres_to_zero_seg['I'], decres_to_zero_seg['V'] = [I[up:], V[up:]]
            decres_seg['I'], decres_seg['V'] = [I[:down+1], V[:down+1]]
            incres_to_zero_seg['I'], incres_to_zero_seg['V'] = [I[down:zero_index+1], V[down:zero_index+1]]

        segms = [incres_seg, decres_to_zero_seg, decres_seg, incres_to_zero_seg]
        self.segms = [incres_seg, decres_to_zero_seg, decres_seg, incres_to_zero_seg]
        return segms


    def Vdata_correct(self):
        """
        矫正V_data的正负号. 确保I和V的符号一致, 即电阻是正数. 矫正的条件是I在正值或者负值时, V的值不是正值或者负值. 如果之前IV已经分成了四段, 还需要重新分段.
        """
        I = self.I_data
        V = self.V_data
        if np.mean(V[I>0]) < 0 or np.mean(V[I<0]) > 0:
            self.V_data = -self.V_data
            if hasattr(self, 'I_segms'):
                self.IVdata_split_4_segments(self.I_data, self.V_data)
            print("The sign of V_data is corrected.")

    
    def plot_IV(self, linestyle=None, save_fig: bool=False):
        """
        画IV曲线图, 根据I_data和V_data而不是I_raw和V_raw. 画图时会根据IV曲线的类型, 临界电流, R拟合结果, V_g等信息进行标注. 画图时会自动调整电流和电压的单位, 使得数值不会太大或太小.

        Parameters:
            linestyle(str): 画图的线型, 默认为None, 即JJo和R是数据点, JJu是实线.
            save_fig(bool): 是否保存图片, 默认为False.
        """

        Ic_1, Ic_2, R_fitp, R_fitm, Vintcp_p, Vintcp_m = self.fit_result
        I, V = self.I_data, self.V_data
        curve_type = self.curve_type
        V_g = self.V_g
        number_suffix = self.number_suffix

        #hline用来在图上画临界电流的水平线, 只画两段线, 而不是4段, 以免来回切换时虚线重合显示成了实线
        hline_p, hline_m = np.array((Ic_1, Ic_1)), np.array((Ic_2, Ic_2))
        V_hline_p, V_hline_m = np.array((V.max(), V[V>=0.0].min())), np.array((V.min(), V[V<=0.0].max()))

        #-----------------画图用数组-----------------#
        #data unit convert for plot
        I_plot_suffix, I_plot_multiplier = number_suffix(I.max())
        V_plot_suffix, V_plot_multiplier = number_suffix(V.max()*10)# *10是为了避免intercept数值太大, 出现几百uV, 不方便x显示
        intercp_suffix, intercp_multiplier = number_suffix(Vintcp_p*10) # *10是为了避免intercept数值太大, 出现几百, 不方便画图
        I_plot = I / I_plot_multiplier
        V_plot = V / V_plot_multiplier
        V_hlinep_plot = V_hline_p / V_plot_multiplier
        hlinep_plot = hline_p / I_plot_multiplier
        V_hlinem_plot = V_hline_m / V_plot_multiplier
        hlinem_plot = hline_m / I_plot_multiplier
        Ic1_plot = Ic_1 / I_plot_multiplier
        Ic2_plot = Ic_2 / I_plot_multiplier
        V_pfit = R_fitp * I + Vintcp_p
        V_mfit = R_fitm * I + Vintcp_m
        V_pfit_plot = V_pfit / V_plot_multiplier
        V_mfit_plot = V_mfit / V_plot_multiplier
        intercp_plot = Vintcp_p / intercp_multiplier
        intercm_plot = Vintcp_m / intercp_multiplier
        #\----------------\画图用数组\----------------\#

        #-----------------画图-----------------#
        plt.figure()
        #Ic拟合结果示意线
        if curve_type != 'R':
            plt.plot(V_hlinep_plot*0.9, hlinep_plot, label=f'Ic={Ic1_plot:.4g} '+ I_plot_suffix + f'A, -Ic={Ic2_plot:.4g} '+ I_plot_suffix + 'A', linestyle='--', color='gray')
            plt.plot(V_hlinem_plot*0.9, hlinem_plot, linestyle='--', color='gray')
        
        # RN拟合线
        if curve_type == 'R':
            plt.plot(V_pfit_plot*1.1, I_plot*1.1, label=f'R={R_fitp:.5g} Ohm, V_intercept={intercp_plot:.2f} '+ intercp_suffix + 'V', linestyle=':', color='gray')
        else: 
            plt.plot(V_pfit_plot, I_plot, label=f'R_+={R_fitp:.4g} Ohm, V_intercept={intercp_plot:.2f} '+ intercp_suffix + 'V', linestyle=':', color='gray')
            plt.plot(V_mfit_plot, I_plot, label=f'R_-={R_fitm:.4g} Ohm, V_intercept={intercm_plot:.2f} '+ intercp_suffix + 'V', linestyle=':', color='gray')

        # V_g和Rsg示意线
        if curve_type == 'JJu':
            Vg_plot = [V_g/V_plot_multiplier, -V_g/V_plot_multiplier]
            if self.V_data.max() < V_g*0.75:
                Vg_plot.pop(0)
            if self.V_data.min() > -V_g*0.75:
                Vg_plot.pop(-1)
            plt.vlines((Vg_plot), I_plot.min(), I_plot.max(), linestyles='dashed', color='gray')
            try:
                plt.plot(V[I>0]/V_plot_multiplier, V[I>0]/self.Rsg_p/I_plot_multiplier, label=f'Rsg_p={self.Rsg_p:.1f} Ohm, Rsg_m={self.Rsg_m:.1f} Ohm', linestyle=':', color='black')
                plt.plot(V[I<0]/V_plot_multiplier, V[I<0]/self.Rsg_m/I_plot_multiplier, linestyle=':', color='black')
            except:
                print('Rsg plot error')
        elif curve_type == 'JJa':
            plt.vlines((self.Vg_optimal*self.num_JJ/V_plot_multiplier, -self.Vg_optimal*self.num_JJ/V_plot_multiplier), I_plot.min(), I_plot.max(), linestyles='dashed', color='gray')


        # 数据点,最后画以覆盖前面的辅助线
        if curve_type == 'R' or curve_type == 'JJo':
            if linestyle is None:
                linestyle = 'o'
            plt.plot(V_plot, I_plot, linestyle, label='data', markersize=2)
        else:
            if linestyle is None:
                linestyle = '-'
            plt.plot(V_plot, I_plot, linestyle, label='data', markersize=2)
            plt.vlines(V_g, I.min(), I.max(), linestyles='dashed', color='gray')

        plt.xlabel('V(' + V_plot_suffix + 'V)')
        plt.ylabel('I(' + I_plot_suffix + 'A)')
        plt.title(self.filename)
        plt.legend()
        plt.grid()
        if save_fig:
            figname = os.path.splitext(self.filename)[0] + '_fit.png'
            plt.savefig(self.file_path.replace(self.filename, figname))
        plt.show()
        #\----------------\画图\----------------\#
        return None
    
    def plot_Ic_spread(self, save_fig: bool=False):
        if self.curve_type != 'JJa':
            return None
        
        if not hasattr(self, 'Vg_optimal'):
            self.get_Ic_spread()
        Ic_array, counts, Vg_optimal = self.Ic_array, self.JJ_counts, self.Vg_optimal

        bin_width = np.diff(Ic_array).mean()  # 平均宽度
        bins = np.append(Ic_array - bin_width / 2, Ic_array[-1] + bin_width / 2)  # 左右扩展

        plt.figure(figsize=(8, 5))
        plt.hist(Ic_array, bins=bins, weights=counts, edgecolor='black', alpha=0.7)

        # 改变x轴的刻度
        Ic_suffix, Ic_multiplier = self.number_suffix(Ic_array.max())
        #Ic_array = Ic_array / Ic_multiplier
        plt.xticks(Ic_array, [f'{Ic/Ic_multiplier:.5g}' for Ic in Ic_array])
        plt.xlim(Ic_array[0] - bin_width, Ic_array[-1] + bin_width)

        # 添加标题和轴标签
        plt.title(self.filename+f' 预估V_g={Vg_optimal*1e3:.3f}mV', fontsize=14)
        plt.xlabel("Ic(" + Ic_suffix + "A)", fontsize=12)
        plt.ylabel(f"结的数目(共{self.num_JJ}个)", fontsize=12)
        if len(Ic_array) > 15:
            plt.xticks(rotation=45)

        # 显示网格
        plt.grid(axis='y', linestyle='--', alpha=0.7)

        if save_fig:
            figname = os.path.splitext(self.filename)[0] + '_Ic_spread.png'
            plt.savefig(self.file_path.replace(self.filename, figname))

        plt.show()

    def number_suffix(self, num: float) -> tuple[str, float]:
        """
        计算一个数的量级. 
        返回一个数值的单位后缀和乘数. 例如: 1.23e-6 -> ('u', 1e-6)

        Parameters:
            num(float): 待计算量级的数.

        Returns:
            suffix(str): 数值的单位后缀.
            multiplier(float): 数值的乘数.
        """
        num_abs = abs(num)
        if num_abs > 1 or num_abs==0:
            for (multiplier,suffix) in zip([1, 1e3, 1e6, 1e9, 1e12], ['', 'k', 'M', 'G', 'T']):
                if num_abs < 1000:
                    return (suffix, multiplier)
                num_abs /= 1000
        else:
            for (multiplier,suffix) in zip([1, 1e-3, 1e-6, 1e-9, 1e-12, 1e-15], ['', 'm', 'u', 'n', 'p', 'f']):
                if num_abs >= 1:
                    return (suffix, multiplier)
                num_abs *= 1000

    def input_check(self):
        """
        检查输入参数是否合法.
        """
        if not isinstance(self.file_path, str):
            raise ValueError("file_path must be a string.")
        if not isinstance(self.data_type, str):
            raise ValueError("data_type must be a string.")
        if self.data_type not in self.ALLOWED_DATA_TYPE:
            raise ValueError("data_type must be 'IV' or 'VI'.")
        if not isinstance(self.I_unit, str):
            raise ValueError("I_unit must be a string.")
        if not isinstance(self.V_unit, str):
            raise ValueError("V_unit must be a string.")
        if self.data_sep is not None and not isinstance(self.data_sep, str):
            raise ValueError("data_sep must be a string or None.")
        