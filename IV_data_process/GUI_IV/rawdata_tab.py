"""
Created on 2024-12-27 14:41:12.

@author: Tao Rong.
"""

import tkinter as tk
from dataclasses import dataclass, field
from tkinter import ttk, messagebox

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ..IVDataProcess_class import IVDataProcess


@dataclass
class RawDataTab:
    """
    用于创建一个窗口布局, 主要是选择性画出各个数据文件的IV曲线.
    可以多选, 方便不同数据文件的对比.
    """

    notebook: ttk.Notebook
    tab_name: str = "Rawdata"
    iv_list: list[IVDataProcess] = field(
        default_factory=list
    )  # IVDataProcess对象的列表
    data_error_list: list[bool] = field(
        default_factory=list
    )  # 用于存储数据处理是否出错的列表. True表示出错, False表示正常
    plot_colors: list[str] = field(default_factory=list)  # 用于存储画图时的颜色列表

    def __post_init__(self):
        self.tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_frame, text=self.tab_name)

        self.fig, self.ax = plt.subplots()
        self.filepaths = [iv.file_path for iv in self.iv_list]
        self.file_names = [iv.filename for iv in self.iv_list]

        self.layout()

    def layout(self):
        """
        布局整个窗口, 即rawdata tab页.
        包括文件路径列表, 画布.
        文件路径列表中的每个文件名前面有一个checkbutton,
        还有一个label, 用于提示红色字体表示数据处理出错.
        如果 iv_list 为空, 则不会创建checkbutton.
        """

        self.plot_check_list = [
            tk.IntVar() for _ in range(len(self.iv_list))
        ]  # 用于存储checkbutton的状态
        self.check_button_list = []  # 用于存储Checkbutton对象

        # 文件路径列表frame, 画布frame
        frame_filepaths = tk.Frame(self.tab_frame)
        frame_canvas = tk.Frame(self.tab_frame, bg="white")
        frame_filepaths.pack(side=tk.LEFT)
        frame_canvas.pack(expand=True, fill=tk.BOTH)

        tk.Label(
            frame_filepaths,
            text="Red text indicates \n data processing error \n or fitting error",
        ).pack()  # checkbutton上的label, 用于提示红色字体表示数据处理出错
        self.canvas = FigureCanvasTkAgg(self.fig, master=frame_canvas)
        self.canvas.get_tk_widget().pack(expand=True, fill=tk.BOTH)

        if len(self.iv_list) == 0:
            return
        for k in range(len(self.iv_list)):
            fg = 'red' if self.data_error_list[k] else 'black'
            check_button = tk.Checkbutton(
                frame_filepaths,
                text=self.file_names[k],
                command=self.plot_figure,
                fg=fg,
                variable=self.plot_check_list[k],
                onvalue=1,
                offvalue=0,
                cursor="hand2",
            )
            self.check_button_list.append(check_button)
            self.check_button_list[k].pack()

    def plot_figure(self):
        """
        画出处理后的I_data和V_data组成的IV曲线.
        如果iv_list为空, 则不会画图.
        """
        if len(self.iv_list) == 0:
            return

        ax = self.ax
        ax.clear()

        for k in range(len(self.iv_list)):
            if self.plot_check_list[k].get() == 1:
                iv = self.iv_list[k]
                try:
                    ax.plot(
                        iv.V_raw,
                        iv.I_raw,
                        label=self.file_names[k],
                        color=self.plot_colors[k],
                    )
                except Exception as e:
                    messagebox.showerror(
                        title='Error',
                        message=f'Error when plot {self.file_names[k]}: {e}',
                    )

        ax.set_xlabel(f'V({self.iv_list[0].V_unit})')
        ax.set_ylabel(f'I({self.iv_list[0].I_unit})')
        ax.grid()
        if ax.lines:  # 有图才生成legend
            ax.set_title('IV Curve(Raw data)')
            ax.legend()
        else:
            ax.set_title('No data to plot')
        self.canvas.draw()

    def update_tab(self):
        """
        更新tab页的数据, 即重新构建tab页.
        主要是用于add_file后的更新.
        """
        # 遍历并销毁 Frame 中的所有子组件
        for widget in self.tab_frame.winfo_children():
            widget.destroy()
        
        self.filepaths = [iv.file_path for iv in self.iv_list]
        self.file_names = [iv.filename for iv in self.iv_list]
        self.layout()