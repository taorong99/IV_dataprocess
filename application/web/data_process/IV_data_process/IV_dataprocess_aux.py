"""
Created on 2024-11-18 00:16:22.

@author: Tao Rong.
"""
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import os

def create_table(filepaths: list, fit_results: list[np.ndarray], curve_types: list, Rsg_results, array_params, save_table=False):
    """
    使用matplotlib来创建一个表格, 将拟合结果显示在表格中.

    Parameters:
        filepaths(list): 文件名列表. 要输入文件名, 可以包含文件夹路径.
        fit_results(list): 拟合结果列表. 每个元素是一个np.ndarray, 包含拟合结果. 拟合结果列表. 每个元素是一个tuple, 包含拟合结果, 该tuple来源于IVDataProcess类. 每个np.ndarray的元素依次是Ic_1, Ic_2, R_fitp, R_fitm, intercept_p, intercept_m. 
        curve_types(list): 曲线类型列表. 每个元素是一个字符串, 表示对应文件的曲线类型. 该字符串来源于IVDataProcess类.
        Rsg_results(list): Rsg结果列表. 每个元素是一个list, 每个list里面包含6个元素, 分别是Rsg_p, V1_p, V2_p, Rsg_m, V1_m, V2_m. 即正负向的subgap电阻和选取电压点的值.
        array_params(list): 结阵的各个参数. 包含两个元素的列表, 第一个元素是结阵的数量, 第二个元素是优化后的Vg值.
        save_table(bool): 是否保存表格图片. 默认为False.
    Returns:
        None.
    """    
    has_JJa = False # 是否有JJa曲线, 没有的话, 表中不显示num_JJ和Vg_optimal
    for curve_type in curve_types:
        if curve_type == 'JJa':
            has_JJa = True
            break
    data = []
    for filepath, fit_result, curve_type,Rsg_result, array_param in zip(filepaths, fit_results, curve_types, Rsg_results, array_params):

        if fit_result.any() is None:
            continue
        Ic_1, Ic_2, R_fitp, R_fitm, intercept_p, intercept_m = fit_result
        IcR_p, IcR_m = '/', '/'
        num_JJ, Vg_optimal = '/', '/'
        Rsg_p, Rsg_m = '/', '/'
        if curve_type == 'JJu':
            IcR_p, IcR_m = f'{Ic_1*R_fitp*1e3:.2f}', f'{Ic_2*R_fitp*1e3:.2f}'
            Rsg_p, Rsg_m = f'{Rsg_result[0]:.1f}', f'{Rsg_result[3]:.1f}'
        if curve_type == 'JJa':
            num_JJ, Vg_optimal = array_param
            IcR_p, IcR_m = f'{Ic_1*R_fitm*1e3/num_JJ:.2f}', f'{Ic_2*R_fitm*1e3/num_JJ:.2f}'
            num_JJ = f'{num_JJ:.0f}'
            Vg_optimal = f'{Vg_optimal*1e3:.4f}'
        

        if has_JJa:
            data.append([os.path.basename(filepath), f'{Ic_1*1e6:.1f}, {Ic_2*1e6:.1f}', f'{R_fitp:.2f}, {R_fitm:.2f}', IcR_p+', '+IcR_m, f'{intercept_p*1e3:.2f}, {intercept_m*1e3:.2f}', (Rsg_p+', '+Rsg_m), num_JJ, Vg_optimal, curve_type])
        else:
            data.append([os.path.basename(filepath), f'{Ic_1*1e6:.1f}, {Ic_2*1e6:.1f}', f'{R_fitp:.2f}, {R_fitm:.2f}', IcR_p+', '+IcR_m, f'{intercept_p*1e3:.2f}, {intercept_m*1e3:.2f}', (Rsg_p+', '+Rsg_m), curve_type])


    # 设置列名
    if has_JJa:
        columns = ['filepath', 'Ic(uA)', 'R_fit(Ohm)', 'IcR(mV)', 'V_intercept(mV)', 'R_sg(Ohm)', 'num_JJ', 'Vg_opt(mV)', 'curve_type']
    else:
        columns = ['filepath', 'Ic(uA)', 'R_fit(Ohm)', 'IcR(mV)', 'V_intercept(mV)', 'R_sg(Ohm)', 'curve_type']
    # 创建图形和轴
    fig, ax = plt.subplots(figsize=(1.5*len(data[0]), 0.28*len(data)))
    ax.axis('off')
    # 创建表格
    table = ax.table(cellText=data, colLabels=columns, loc='center', cellLoc='center')
    # 设置表格样式
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1.2, 1.2)
    table.auto_set_column_width([n for n in range(len(columns))]) # 设置列宽度,自动调整
    # 获取当前时间
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ax.title.set_text(f'Table created at {current_time}')
    if save_table:
        table_name = os.path.join(os.path.dirname(filepaths[0]), 'summary_table.png')
        plt.savefig(table_name, bbox_inches='tight', dpi=500)
    plt.show()

try:
    import tkinter as tk
    from tkinter import filedialog
    def select_files():
        """
        使用tkinter来选择文件，并确保文件选择对话框显示在最前面
        """
        root = tk.Tk()
        root.withdraw()
        
        # 临时创建一个可见的顶级窗口来承载对话框
        top = tk.Toplevel(root)
        top.withdraw()
        top.attributes('-topmost', True)
        
        # 使用这个顶级窗口来创建文件对话框
        filepaths = filedialog.askopenfilenames(
            parent=top,
            title="Select a file",
            filetypes=[("Data files", ("*.txt", "*.csv")), 
                    ("Text files", "*.txt"), 
                    ("Csv files", "*.csv"), 
                    ("All files", "*.*")]
        )
        
        top.destroy()
        root.destroy()
        return filepaths
except:
    pass