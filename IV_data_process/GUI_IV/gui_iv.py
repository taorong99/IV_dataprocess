"""
Created on 2024-12-15 11:04:12.

@author: Tao Rong.
"""

import os
import sys
import tkinter as tk
from dataclasses import dataclass, field
from datetime import datetime
from tkinter import messagebox, ttk

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import hsv_to_rgb  # 用于将HSV颜色转换为RGB颜色

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from IV_dataprocess_aux import select_files # type: ignore
from IVDataProcess_class import IVDataProcess # type: ignore

from .fitdata_tab import FitDataTab
from .input_tab import InputTab
from .overview_tab import OverviewTab
from .rawdata_tab import RawDataTab

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False


@dataclass
class GuiIV:
    # reST style docstring
    """
    用于创建一个GUI界面, 用于展示IV曲线的处理结果.

    Args:
        data_type(str): 数据文件格式, 可选'IV'或'VI'. 可以在GUI界面中选择.
        I_unit(str): 电流单位, 默认为'A'. 可以在GUI界面中选择.
        V_unit(str): 电压单位, 默认为'V'. 可以在GUI界面中选择.
    """
    def __post_init__(self):
        self.iv_list = self.read_data(list(select_files()))
        self.plot_colors = [hsv_to_rgb((i/len(self.iv_list), 1, 1)) for i in range(len(self.iv_list))] # 生成不同颜色的列表
        self.window = tk.Tk()
        self.layout_window() # 布局窗口
        self.read_data() # 再次读取数据, 确保用到的是input_tab中的设置
        self.window.bind("<Configure>", self.update_label_position) # 绑定窗口大小变化事件
        self.window.mainloop()

    def read_data(self, paths=None):
        """
        根据文件路径列表, 读取数据, 并进行数据处理. 所用的数据处理方法在IVDataProcess类中定义.

        Returns:
            list[IVDataProcess]: 一个IVDataProcess对象列表, 包含了处理数据后的结果.
        """
        if paths is None:
            self.file_paths = self.input_tab.filepaths
            self.data_type = self.input_tab.data_type.get()
            self.I_unit = self.input_tab.I_unit.get()
            self.V_unit = self.input_tab.V_unit.get()
        else:
            self.file_paths = paths
            self.data_type = 'IV'
            self.I_unit = 'A'
            self.V_unit = 'V'
        ivs: list[IVDataProcess] = []
        self.data_error_list: list[bool] = [] #用于标记数据处理出错的文件, 会以红色字体显示在文件列表中

        for file_path in self.file_paths:
            try:
                iv = IVDataProcess(file_path, self.data_type, self.I_unit, self.V_unit)
                ivs.append(iv)
                iv.file_read()
                iv.remove_V_offset()
                iv.Vdata_correct()
                iv.curve_classifier()
                iv.curve_classifier()
                iv.get_Ic()
                iv.fit_R()
                self.data_error_list.append(False)
            except Exception as e:
                print(f"Error when process {file_path}: {e}")
                self.data_error_list.append(True)
                continue
        self.fit_results = [iv.fit_result for iv in ivs]
        self.curve_types = [iv.curve_type for iv in ivs]
        
        self.file_names = [iv.filename for iv in ivs]
        self.iv_list = ivs
        self.plot_colors = [hsv_to_rgb((i/len(self.iv_list), 1, 1)) for i in range(len(self.iv_list))] # 生成不同颜色的列表
        
        self.update_3_tabs() # 更新三个tab页的数据

        # 如果其他tab页已经创建, 则更新这些tab页的数据
        return ivs

    def layout_window(self):
        self.window.title("IV Curves Ploter")
        self.window.geometry("1000x700") # 设置窗口大小
        self.selected_winsize = tk.StringVar()
        self.selected_winsize.set('[700, 525]')
        frame_window_size = tk.Frame(self.window)
        frame_window_size.pack()
        label_winsize = tk.Label(frame_window_size, text='Window Size:').pack(side=tk.LEFT)
        radiobutt1 = tk.Radiobutton(frame_window_size, text='700x525', value='[700, 525]', variable=self.selected_winsize, command=self.set_winsize).pack(side=tk.LEFT)
        radiobutt2 = tk.Radiobutton(frame_window_size, text='1000x700', value='[1000, 700]', variable=self.selected_winsize, command=self.set_winsize).pack(side=tk.LEFT)
        radiobutt3 = tk.Radiobutton(frame_window_size, text='else', value='else', variable=self.selected_winsize, command=self.set_winsize).pack(side=tk.LEFT)

        self.fig_name = tk.StringVar() # 用于存储保存图片的文件名
        # 保存图片frame, 
        save_fig_frame = tk.Frame(self.window)
        # 创建保存图片的entry和button
        fig_name_label = tk.Label(save_fig_frame, text="Picture Name:") 
        self.save_entry = tk.Entry(save_fig_frame, textvariable=self.fig_name)
        self.save_button = tk.Button(save_fig_frame, text="Save Picture", command=self.save_figure, bg="#0078D7", fg="white", cursor="hand2")
        save_fig_frame.pack()
        fig_name_label.pack(side=tk.LEFT)
        self.save_entry.pack(side=tk.LEFT)
        self.save_button.pack(side=tk.LEFT)

        #四个标签页的设置
        notebook = ttk.Notebook(self.window) # notebook是一个标签页的容器
        self.notebook = notebook
        self.input_tab = InputTab(
            notebook, 
            func_fileread=self.read_data,
            filepaths=self.file_paths)
        self.overview_tab = OverviewTab(
            notebook,
            iv_list=self.iv_list,
            data_error_list=self.data_error_list,
            plot_colors=self.plot_colors,
        )
        self.fitdata_tab = FitDataTab(
            notebook, iv_list=self.iv_list, data_error_list=self.data_error_list
        )
        self.rawdata_tab = RawDataTab(
            notebook,
            iv_list=self.iv_list,
            data_error_list=self.data_error_list,
            plot_colors=self.plot_colors,
        )

        notebook.pack(expand=True, fill="both")
        notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)
        

        self.copyright_label = tk.Label(self.window, text=f"© {datetime.now().year} Tao Rong. Licensed under the MIT License.", font=("Arial", 10), bg="lightgray", fg="black")

        self.copyright_label.pack(side=tk.RIGHT)

    def save_figure(self):
        try:
            dirname = os.path.dirname(self.file_paths[0])
        except Exception as e:
            messagebox.showerror(title='Error', message=f'Cannot get the file path: {e}')
            return
        # 根据当前选中的标签页, 选择对应的画布
        current_tab_index = self.notebook.index(self.notebook.select())
        current_tab = {0: self.input_tab, 1: self.overview_tab, 2: self.fitdata_tab, 3: self.rawdata_tab}[current_tab_index]
    
        try:
            fig = current_tab.fig
        except Exception as e:
            messagebox.showerror(title='Error', message=f'There is no figure to save in {self.notebook.tab(self.notebook.select(), "text")} tab. \n{e}')
            return
        # current_tab = self.notebook.index(self.notebook.select())
        # fig = self.fig_list[current_tab]
        #先判断文件是否存在, 如果存在, 则弹窗提示是否覆盖
        fig_name = self.fig_name.get()
        if fig_name == '':
            messagebox.showerror(title='File Name Empty', message='Please input the picture file name')
            return
        fig_name = fig_name + '.png'
        fig_path = dirname + '/' + fig_name
        if os.path.exists(fig_path):
            result = messagebox.askyesno(title='File Exists', message=f'Picture \'{fig_name}\' exists, do you want to overwrite it?')
            if result == False:
                return
            fig.savefig(fig_path, dpi=500)
            
        else:
            fig.savefig(fig_path, dpi=500)
        messagebox.showinfo(title='Save Picture', message=f'Picture \'{fig_name}\' saved successfully')

    def update_3_tabs(self):
        """
        当执行完read_data()方法后, 更新三个tab页的数据.
        """
        if hasattr(self, 'overview_tab'):
            self.overview_tab.iv_list = self.iv_list
            self.overview_tab.data_error_list = self.data_error_list
            self.overview_tab.plot_colors = self.plot_colors
            self.overview_tab.update_tab()
        if hasattr(self, 'fitdata_tab'):
            self.fitdata_tab.iv_list = self.iv_list
            self.fitdata_tab.data_error_list = self.data_error_list
            self.fitdata_tab.update_tab()
        if hasattr(self, 'rawdata_tab'):
            self.rawdata_tab.iv_list = self.iv_list
            self.rawdata_tab.data_error_list = self.data_error_list
            self.rawdata_tab.plot_colors = self.plot_colors
            self.rawdata_tab.update_tab()
        
    def update_label_position(self, event=None):
        """动态更新版权标签位置，保持在右下角"""
        self.window.update_idletasks()  # 更新窗口布局信息
        x = self.window.winfo_width() - self.copyright_label.winfo_reqwidth() - 10  # 距右边框 10px
        y = self.window.winfo_height() - self.copyright_label.winfo_reqheight() - 10  # 距底边框 10px
        self.copyright_label.place(x=x, y=y)

        # 窗口大小变化时更改winsize的radiobutt到'else'
        if self.selected_winsize.get() != 'else':
            select_list = eval(self.selected_winsize.get())
            if self.window.winfo_width()!= select_list[0] or self.window.winfo_height()!=select_list[1]:
                self.selected_winsize.set('else')

    def set_winsize(self):
        # 字符串转换为列表
        if self.selected_winsize.get() == 'else':
            return
        winsize = eval(self.selected_winsize.get())
        self.window.geometry(f"{winsize[0]}x{winsize[1]}")

    def on_tab_change(self, event=None): # 标签页切换事件 
        pass


        

if __name__ == "__main__":
    
    gui = GuiIV()
    