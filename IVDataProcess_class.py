"""
Created on 2024-09-19 19:41:39.

@author: Tao Rong.
Modified on 2024-11-17 21:12:19, by Tao Rong. Version 1.0. Procedure-oriented -> Object-oriented.
Modified on 2024-11-18 18:00:00, by Tao Rong. Version 1.1. Optimize remove_V_offset method, IV_unit_convert method.
"""
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from scipy.stats import linregress #线性回归用于拟合R
from scipy.stats import zscore #计算V_offset时去除离群点用


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
        curve_type(str): IV曲线的类型, 可选R, JJu, JJo.
        Ic_fitp(float): 正向临界电流.
        Ic_fitm(float): 负向临界电流.
        R_fitp(float): 正向拟合电阻.
        R_fitm(float): 负向拟合电阻.
        Vintcp_p(float): 正向R拟合后在V轴的截距.
        Vintcp_m(float): 负向R拟合后在V轴的截距.
        segms(list[dict, dict, dict, dict]): 四段IV曲线的字典. 字典的key是'I'和'V', value是对应的电流和电压数据.
        n_convolve(int): 对R_diff进行平滑处理时的卷积核大小, 默认为1.

    Methods:
        file_read(): 根据file_path读取数据文件, 得到self.I, self.V两个数组(量纲为A, V), 同时还会保存原始数据在self.I_raw, self.V_raw的两个数组中.
        IV_unit_convert(): 将原始数据转换为指定单位的数据.
        get_separator(): 从文件中读取中间一行数据, 并根据这行数据自动判断分隔符.
        remove_V_offset(): 获取V_offset值, 并将V_data减去offset.
        curve_classifier(): 判断IV曲线的类型, 并返回.
        get_Ic(): 获取Ic_fitp和Ic_fitm, 即正向和负向的临界电流.
        fit_R(): 对IV曲线进行R拟合, 得到Rp和Rm.
        IVdata_split_4_segments(): 将数组 I_data和V_data 分成四段: 上升段、下降到零段、下降段、上升到零段.
        Vdata_correct(): 矫正V_data的正负号.
        plot_IV(): 画IV曲线图, 根据I_data和V_data而不是I_raw和V_raw. 画图时会根据IV曲线的类型, 临界电流, R拟合结果, V_g等信息进行标注. 画图时会自动调整电流和电压的单位, 使得数值不会太大或太小.
    """

    ALLOWED_DATA_TYPE = ["IV", "VI"]
    
    def __init__(self, file_path: str, data_type: str, I_unit: str="A", V_unit: str="V", data_sep: str=None, V_g: float=2.8e-3):
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

        self.filename = file_path.split('/')[-1]
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
              
        if abs(V_offset) < V_offset_threshold:
            V_offset = 0.0

        self.V_offset = V_offset
        self.V_data = self.V_data - self.V_offset
        return V_offset 
    
    def curve_classifier(self) -> str:
        """
        判断IV曲线的类型, 并返回. IV曲线的类型有R, JJu, JJo三种, 将来支持JJa, JJs等. 首先根据I_data和V_data在首尾的20个点线性拟合结果, 25%以内认为是R. 如果不是R, 则根据V_data的回滞绝对值是否大于V_g/2判断是JJu还是JJo.

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
            #将I按从小到大排序, V对应I的排序. 如果V相邻差值可以大于Vg一半, 则认为是JJu, 否则是JJo.
            V_sort = self.V_data[np.argsort(self.I_data)]
            V_diff = np.diff(V_sort)
            if np.max(abs(V_diff) > self.V_g/4):
                curve_type = 'JJu'
            else:
                curve_type = 'JJo'

        self.curve_type = curve_type
        return curve_type
    
    def get_Ic(self) -> tuple[float, float]:
        """
        获取Ic_fitp和Ic_fitm, 即正向和负向的临界电流. 对于'R'类型的IV曲线, Ic_fitp和Ic_fitm都是0.0. 对于'JJu'和'JJo'类型的IV曲线, Ic_fitph和Ic_fitm由直流电阻和差分电阻的转角决定.

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
            
            Ic_seg = np.zeros(4) #len(IV_segments)=4
            for n, seg in enumerate(IV_segments):
                if self.curve_type == 'JJu' and (n==1 or n==3): #回滞结的回滞段没法判断Ic
                    Ic_seg[n] = Ic_seg[n-1]
                    continue
                I, V = seg['I'], seg['V']
                V_diff = abs(np.diff(V)) #电压差分
                I_diff = abs(np.diff(I)) #电流差分 
                R_diff = V_diff/(I_diff+1e-9) + 1e-9 # 1e-9是为了避免分母为0
                R_0 = abs(V/(I+1e-9)) + 1e-9 # 1e-9是为了避免分母为0
                #对R_diff进行平滑处理, 取3个点已经开始对underdump的结果产生了轻微影响.
                R_diff = np.convolve(R_diff, np.ones(n_convolve)/n_convolve, mode='same')
                #取IV曲线上转角接近90度的点, 即直流电阻和差分电阻曲线夹角最小的点
                phi = np.pi + np.arctan(1/R_diff) - np.arctan(1/R_0[0:-1])
                index_end = -n_convolve+1 if n_convolve > 1 else len(phi)+1
                Ic_seg[n] = I[np.argmin(phi[n_convolve-1:index_end]) + n_convolve-1]

            Ic_fitp = min(Ic_seg[Ic_seg > 0])
            Ic_fitm = max(Ic_seg[Ic_seg < 0])
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
            else:
                R_fitp, R_fitm = 0.0, 0.0
                Vintcp_p, Vintcp_m = 0.0, 0.0 
                raise Warning('R fitting error, .Curve_type should be R, JJu or JJo')
            #\-------------筛选用于拟合的数据\-------------#

            #-------------Rp和Rm拟合-------------#
            try:
                R_fitp, Vintcp_p, r_value, p_value, std_err = linregress(I_data_fitp, V_data_fitp) #斜率、截距、相关系数r、p值和标准误差。
                R_fitm, Vintcp_m, r_value, p_value, std_err = linregress(I_data_fitm, V_data_fitm) #斜率、截距、相关系数r、p值和标准误差。
            except Exception as e:
                print(e)
                print('R fitting error')
            
                R_fitp, R_fitm = 0.0, 0.0
                Vintcp_p, Vintcp_m = 0.0, 0.0
            #\-------------Rp和Rm拟合\-------------#
        self.fit_result[2], self.fit_result[3], self.fit_result[4], self.fit_result[5] = R_fitp, R_fitm, Vintcp_p, Vintcp_m
        self.R_fitp, self.R_fitm, self.Vintcp_p, self.Vintcp_m = R_fitp, R_fitm, Vintcp_p, Vintcp_m
        return (R_fitp, R_fitm, Vintcp_p, Vintcp_m)

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

    
    def plot_IV(self, save_fig: bool=False):
        """
        画IV曲线图, 根据I_data和V_data而不是I_raw和V_raw. 画图时会根据IV曲线的类型, 临界电流, R拟合结果, V_g等信息进行标注. 画图时会自动调整电流和电压的单位, 使得数值不会太大或太小.

        Parameters:
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
            plt.plot(V_hlinep_plot*0.9, hlinep_plot, label=f'Ic={Ic1_plot:.1f} '+ I_plot_suffix + f'A, -Ic={Ic2_plot:.1f} '+ I_plot_suffix + 'A', linestyle='--', color='gray')
            plt.plot(V_hlinem_plot*0.9, hlinem_plot, linestyle='--', color='gray')
        
        # RN拟合线
        if curve_type == 'R':
            plt.plot(V_pfit_plot*1.1, I_plot*1.1, label=f'R={R_fitp:.2f} Ohm, V_intercept={intercp_plot:.2f} '+ intercp_suffix + 'V', linestyle=':', color='gray')
        else: 
            plt.plot(V_pfit_plot, I_plot, label=f'R_+={R_fitp:.2f} Ohm, V_intercept={intercp_plot:.2f} '+ intercp_suffix + 'V', linestyle=':', color='gray')
            plt.plot(V_mfit_plot, I_plot, label=f'R_-={R_fitm:.2f} Ohm, V_intercept={intercm_plot:.2f} '+ intercp_suffix + 'V', linestyle=':', color='gray')

        # V_g示意线
        if curve_type == 'JJu':
            plt.vlines((V_g/V_plot_multiplier, -V_g/V_plot_multiplier), I_plot.min(), I_plot.max(), linestyles='dashed', color='gray')

        # 数据点,最后画以覆盖前面的辅助线
        if curve_type == 'R' or curve_type == 'JJo':
            plt.plot(V_plot, I_plot, 'o', label='data', markersize=2)
        else:
            plt.plot(V_plot, I_plot, label='data')
            plt.vlines(V_g, I.min(), I.max(), linestyles='dashed', color='gray')

        plt.xlabel('V(' + V_plot_suffix + 'V)')
        plt.ylabel('I(' + I_plot_suffix + 'A)')
        plt.title(self.filename)
        plt.legend()
        plt.grid()
        if save_fig:
            figname = self.filename.split('.')[0] + '_fit.png'
            plt.savefig(self.file_path.replace(self.filename, figname))
        plt.show()
        #\----------------\画图\----------------\#
        return None
        
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
        