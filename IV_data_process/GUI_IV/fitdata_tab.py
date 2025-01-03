"""
Created on 2024-12-27 13:57:37.

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
class FitDataTab:
    """
    用于创建一个窗口布局, 主要是单选画出拟合后的IV曲线.
    """

    notebook: ttk.Notebook
    tab_name: str = "Fitdata"
    iv_list: list[IVDataProcess] = field(
        default_factory=list
    )  # IVDataProcess对象的列表
    data_error_list: list[bool] = field(
        default_factory=list
    )  # 用于存储数据处理是否出错的列表. True表示出错, False表示正常

    def __post_init__(self):
        self.tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_frame, text=self.tab_name)

        self.fig, self.ax = plt.subplots()
        self.filepaths = [iv.file_path for iv in self.iv_list]
        self.file_names = [iv.filename for iv in self.iv_list]
        self.fit_results = [iv.fit_result for iv in self.iv_list]
        self.curve_types = [iv.curve_type for iv in self.iv_list]

        self.layout()

    def layout(self):
        """
        布局整个窗口, 即fitdata tab页.
        包括文件路径列表, 画布.
        文件路径列表中的每个文件名前面有一个RadioButton,
        还有一个label, 用于提示红色字体表示数据处理出错.
        如果 iv_list 为空, 则不会创建RadioButton.
        """
        self.plot_check = tk.IntVar()  # 用于存储当前RadioButton的选择
        self.radio_button_list = []  # 用于存储RadioButton对象

        # 文件路径列表frame, 画布frame
        frame_filepaths = tk.Frame(self.tab_frame)
        frame_canvas = tk.Frame(self.tab_frame, bg='white')
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
            radio_button = tk.Radiobutton(
                frame_filepaths,
                text=self.file_names[k],
                command=self.plot_figure,
                fg=fg,
                variable=self.plot_check,
                value=k,
                cursor="hand2",
            )
            self.radio_button_list.append(radio_button)

        # 添加一个summary table的RadioButton
        self.radio_button_list.append(
            tk.Radiobutton(
                frame_filepaths,
                text="Summary Table",
                command=self.plot_figure,
                fg="black",
                variable=self.plot_check,
                value=len(self.iv_list),
                cursor="hand2",
            )
        )

        [button.pack() for button in self.radio_button_list]

    def plot_figure(self):
        """
        画出拟合后的IV曲线.
        如果iv_list为空, 则不会画图.
        """
        if len(self.iv_list) == 0:
            return

        ax = self.ax
        ax.clear()

        index = self.plot_check.get()
        if index == len(self.iv_list):  # 生成summary table
            self.create_summary_table(
                self.file_names, self.fit_results, self.curve_types
            )
            return
        iv = self.iv_list[index]
        try:
            self.plot_fit(iv)
        except Exception as e:
            messagebox.showerror(
                title='Error',
                message=f'Error when plot {self.file_names[index]}: {e}. \n This may be caused by fitting error, please check the raw data and fitting result.',
            )

    def plot_fit(self, iv: IVDataProcess):
        """
        画出拟合后的IV曲线.
        画图时会根据IV曲线的类型, 临界电流, R拟合结果, V_g等信息进行标注.
        画图时会自动调整电流和电压的单位, 使得数值不会太大或太小.

        Parameters:
            iv(IVDataProcess): 一个IVDataProcess对象.
        """
        ax = self.ax

        Ic_1, Ic_2, R_fitp, R_fitm, Vintcp_p, Vintcp_m = iv.fit_result
        I, V = iv.I_data, iv.V_data
        curve_type = iv.curve_type
        V_g = iv.V_g
        number_suffix = iv.number_suffix

        # hline用来在图上画临界电流的水平线, 只画两段线, 而不是4段, 以免来回切换时虚线重合显示成了实线
        hline_p, hline_m = np.array((Ic_1, Ic_1)), np.array((Ic_2, Ic_2))
        V_hline_p, V_hline_m = np.array((V.max(), V[V >= 0.0].min())), np.array(
            (V.min(), V[V <= 0.0].max())
        )

        # -----------------画图用数组-----------------#
        # data unit convert for plot
        I_plot_suffix, I_plot_multiplier = number_suffix(I.max())
        V_plot_suffix, V_plot_multiplier = number_suffix(
            V.max() * 10
        )  # *10是为了避免intercept数值太大, 出现几百uV, 不方便x显示
        intercp_suffix, intercp_multiplier = number_suffix(
            Vintcp_p * 10
        )  # *10是为了避免intercept数值太大, 出现几百, 不方便画图
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
        # \----------------\画图用数组\----------------\#

        # -----------------画图-----------------#
        # Ic拟合结果示意线
        if curve_type != 'R':
            ax.plot(
                V_hlinep_plot * 0.9,
                hlinep_plot,
                label=f'Ic={Ic1_plot:.1f} '
                + I_plot_suffix
                + f'A, -Ic={Ic2_plot:.1f} '
                + I_plot_suffix
                + 'A',
                linestyle='--',
                color='gray',
            )
            ax.plot(V_hlinem_plot * 0.9, hlinem_plot, linestyle='--', color='gray')

        # RN拟合线
        if curve_type == 'R':
            ax.plot(
                V_pfit_plot * 1.1,
                I_plot * 1.1,
                label=f'R={R_fitp:.4f} Ohm, V_intercept={intercp_plot:.2f} '
                + intercp_suffix
                + 'V',
                linestyle=':',
                color='gray',
            )
        else:
            ax.plot(
                V_pfit_plot,
                I_plot,
                label=f'R_+={R_fitp:.2f} Ohm, V_intercept={intercp_plot:.2f} '
                + intercp_suffix
                + 'V',
                linestyle=':',
                color='gray',
            )
            ax.plot(
                V_mfit_plot,
                I_plot,
                label=f'R_-={R_fitm:.2f} Ohm, V_intercept={intercm_plot:.2f} '
                + intercp_suffix
                + 'V',
                linestyle=':',
                color='gray',
            )

        # V_g示意线
        if curve_type == 'JJu':
            ax.vlines(
                (V_g / V_plot_multiplier, -V_g / V_plot_multiplier),
                I_plot.min(),
                I_plot.max(),
                linestyles='dashed',
                color='gray',
            )

        # 数据点,最后画以覆盖前面的辅助线
        if curve_type == 'R' or curve_type == 'JJo':
            ax.plot(V_plot, I_plot, 'o', label='data', markersize=2)
        else:
            ax.plot(V_plot, I_plot, label='data')
            ax.vlines(V_g, I.min(), I.max(), linestyles='dashed', color='gray')

        ax.set_xlabel(f'V({V_plot_suffix}V)')
        ax.set_ylabel(f'I({I_plot_suffix}A)')
        ax.set_title(iv.filename)
        ax.legend()
        ax.grid()
        self.canvas.draw()
        # \----------------\画图\----------------\#

    def create_summary_table(
        self, filenames: list, fit_results: list[np.ndarray], curve_types: list
    ):
        """
        使用matplotlib来创建一个表格, 将拟合结果显示在表格中.

        Args:
            filepaths(list): 文件名列表. 要输入文件名, 可以包含文件夹路径.
            fit_results(list): 拟合结果列表. 每个元素是一个np.ndarray, 包含拟合结果. 拟合结果列表. 每个元素是一个tuple, 包含拟合结果, 该tuple来源于IVDataProcess类. 每个np.ndarray的元素依次是Ic_1, Ic_2, R_fitp, R_fitm, intercept_p, intercept_m.
            curve_types(list): 曲线类型列表. 每个元素是一个字符串, 表示对应文件的曲线类型. 该字符串来源于IVDataProcess类.
        Returns:
            None.
        """
        # 先清空画布再画表格
        fig = self.fig
        fig_size = fig.get_size_inches()
        fig.clear()
        self.canvas.draw()
        self.ax = fig.add_subplot(111)
        ax = self.ax

        data = []
        for filename, fit_result, curve_type in zip(
            filenames, fit_results, curve_types
        ):
            if fit_result.any() is None:
                continue
            Ic_1, Ic_2, R_fitp, R_fitm, intercept_p, intercept_m = fit_result
            IcR_p, IcR_m = '/', '/'
            if curve_type == 'JJu':
                IcR_p, IcR_m = f'{Ic_1*R_fitp*1e3:.2f}', f'{Ic_2*R_fitp*1e3:.2f}'

            data.append(
                [
                    filename,
                    f'{Ic_1*1e6:.1f}, {Ic_2*1e6:.1f}',
                    f'{R_fitp:.2f}, {R_fitm:.2f}',
                    IcR_p + ', ' + IcR_m,
                    f'{intercept_p*1e3:.2f}, {intercept_m*1e3:.2f}',
                    curve_type,
                ]
            )
        if data == []:
            return

        # 设置列名
        columns = [
            'filepath',
            'Ic(uA)',
            'R_fit(Ohm)',
            'IcR(mV)',
            'V_intercept(mV)',
            'curve_type',
        ]
        # 创建图形和轴
        fig.set_size_inches(1.5 * len(data[0]), 0.28 * len(data))
        ax.axis('off')
        # 创建表格
        table = ax.table(
            cellText=data, colLabels=columns, loc='center', cellLoc='center'
        )
        # 设置表格样式
        table.auto_set_font_size(False)
        table.set_fontsize(12)
        table.scale(1.2, 1.2)
        table.auto_set_column_width(
            [n for n in range(len(columns))]
        )  # 设置列宽度,自动调整
        ax.title.set_text(f'Summary Table')

        self.canvas.draw()
        fig.set_size_inches(fig_size)

    def update_tab(self):
        # 遍历并销毁 Frame 中的所有子组件
        for widget in self.tab_frame.winfo_children():
            widget.destroy()

        self.filepaths = [iv.file_path for iv in self.iv_list]
        self.file_names = [iv.filename for iv in self.iv_list]
        self.fit_results = [iv.fit_result for iv in self.iv_list]
        self.curve_types = [iv.curve_type for iv in self.iv_list]
        self.layout()
