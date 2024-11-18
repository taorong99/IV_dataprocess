"""
Created on 2024-11-18 00:16:22.

@author: Tao Rong.
"""
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime


def create_table(filepaths: list, fit_results: list[np.ndarray], curve_types: list, save_table=False):
    """
    使用matplotlib来创建一个表格, 将拟合结果显示在表格中.

    Parameters:
        filepaths(list): 文件名列表. 要输入文件名, 可以包含文件夹路径.
        fit_results(list): 拟合结果列表. 每个元素是一个np.ndarray, 包含拟合结果. 拟合结果列表. 每个元素是一个tuple, 包含拟合结果, 该tuple来源于IVDataProcess类. 每个np.ndarray的元素依次是Ic_1, Ic_2, R_fitp, R_fitm, intercept_p, intercept_m. 
        curve_types(list): 曲线类型列表. 每个元素是一个字符串, 表示对应文件的曲线类型. 该字符串来源于IVDataProcess类.
        save_table(bool): 是否保存表格图片. 默认为False.
    Returns:
        None.
    """

    data = []
    for filepath, fit_result, curve_type in zip(filepaths, fit_results, curve_types):
        if fit_result.any() is None:
            continue
        Ic_1, Ic_2, R_fitp, R_fitm, intercept_p, intercept_m = fit_result
        IcR_p, IcR_m = '/', '/'
        if curve_type == 'JJu':
            IcR_p, IcR_m = f'{Ic_1*R_fitp*1e3:.2f}', f'{Ic_2*R_fitp*1e3:.2f}'

        data.append([filepath.split('/')[-1].split('.')[0], f'{Ic_1*1e6:.1f}, {Ic_2*1e6:.1f}', f'{R_fitp:.2f}, {R_fitm:.2f}', IcR_p+', '+IcR_m, f'{intercept_p*1e3:.2f}, {intercept_m*1e3:.2f}', curve_type])
    if data == []:
        print('aaaa')
        return

    # 设置列名
    columns = ['filepath', 'Ic(uA)', 'R_fit(Ohm)', 'IcR(mV)', 'V_intercept(mV)', 'curve_type']
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
        table_name = filepaths[0].replace(filepaths[0].split('/')[-1], '') + 'summary_table.png'
        plt.savefig(table_name, bbox_inches='tight', dpi=500)
    plt.show()

try:
    import tkinter as tk
    from tkinter import filedialog
    def select_files():
        """
        使用tkinter来选择文件.
        """
        # 创建一个隐藏的主窗口
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口

        # 打开文件选择对话框
        filepaths = filedialog.askopenfilenames(
            title="Select a file",
            filetypes=[("Data files", ("*.txt", "*.csv")), ("Text files", "*.txt"), ("Csv files", "*.csv"), ("All files", "*.*")]
        )

        return filepaths
except:
    pass