"""
Created on 2024-12-26 23:29:07.

@author: Tao Rong.
"""

import json
import tkinter as tk
from dataclasses import dataclass, field
from tkinter import filedialog, ttk

import matplotlib.pyplot as plt
import numpy as np


@dataclass
class InputTab:
    """
    用于创建一个窗口布局, 包含输入数据所需的所有控件. 是notebook的一个tab页.
    例如, data_type, I_unit, V_unit的选择, 多个文件的添加删除, 以及开始处理按钮.
    开始拟合后, 会生成一个config字典, data_type, I_unit, V_unit的选择.
    """

    notebook: ttk.Notebook
    func_fileread: callable = None  # 用于读取文件的函数. 点击confirm后, 会调用此函数.
    tab_name: str = "Input"
    filepaths: list = field(
        default_factory=list
    )  # iv数据文件路径列表. 可以为空, 待add file后添加文件路径.

    def __post_init__(self):
        self.tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_frame, text=self.tab_name)

        self.data_type = tk.StringVar()
        self.I_unit = tk.StringVar()
        self.V_unit = tk.StringVar()

        config = self.read_config()
        self.data_type.set(config["data_type"])
        self.I_unit.set(config["I_unit"])
        self.V_unit.set(config["V_unit"])

        self.layout()

    def layout(self):
        datatype_frame = tk.Frame(self.tab_frame)
        Iunit_frame = tk.Frame(self.tab_frame)
        Vunit_frame = tk.Frame(self.tab_frame)
        file_frame = tk.Frame(self.tab_frame)
        filepaths_frame = tk.Frame(self.tab_frame)  # 用于显示文件路径列表
        datatype_frame.pack()
        Iunit_frame.pack()
        Vunit_frame.pack()
        file_frame.pack()
        filepaths_frame.pack()

        # 放置一个label和下拉选择框, 用于选择数据类型
        tk.Label(datatype_frame, text="Data Type:").pack(side="left")
        self.datatype_box = ttk.Combobox(
            datatype_frame, textvariable=self.data_type, values=["IV", "VI"]
        ).pack(side="left")

        # 放置一个label和下拉选择框, 用于选择电流单位, 提示可自行输入
        tk.Label(Iunit_frame, text="I Unit:").pack(side="left")
        self.Iunit_box = ttk.Combobox(
            Iunit_frame,
            textvariable=self.I_unit,
            values=["A", "mA", "uA", "enter else"],
        ).pack(side="left")

        # 放置一个label和下拉选择框, 用于选择电压单位, 提示可自行输入
        tk.Label(Vunit_frame, text="V Unit:").pack(side="left")
        self.Vunit_box = ttk.Combobox(
            Vunit_frame,
            textvariable=self.V_unit,
            values=["V", "mV", "uV", "enter else"],
        ).pack(side="left")

        # 放置三个按钮, 分别是add file和clear_all, confirm
        self.add_file_button = tk.Button(
            file_frame, text="Add File", command=self.add_file
        ).pack(side="left")
        self.clear_all_button = tk.Button(
            file_frame, text="Clear All", command=self.clear_all
        ).pack(side="left")
        self.confirm_button = tk.Button(
            file_frame,
            text="Confirm",
            command=self.confirm,
            bg="#0078D7",
            fg="white",
            cursor="hand2",
        ).pack()

        # 放置一个label, label的内容根据self.filepaths的内容动态变化
        self.filepaths_label = tk.Label(filepaths_frame, text="File Paths:")
        self.filepaths_label.pack(side="left")
        self.update_filepaths_label()

    def read_config(self) -> dict:
        """
        读取用户的配置, 并返回一个config字典.
        如果config文件不存在, 则程序中自行设置一个默认的config字典.

        Returns:
            dict: config字典, 包含data_type, I_unit, V_unit的选择.
        """
        try:
            with open("./config_input_tab.json", "r") as f:
                config = json.load(f)
        except FileNotFoundError:
            config = {
                "data_type": "IV",
                "I_unit": "A",
                "V_unit": "V",
            }

        return config

    def create_config(self):
        """
        创建一个config字典, 包含data_type, I_unit, V_unit的选择.
        config文件保存路径为"./config_input_tab.json".
        """
        config = {
            "data_type": self.data_type.get(),
            "I_unit": self.I_unit.get(),
            "V_unit": self.V_unit.get(),
        }

        with open("./config_input_tab.json", "w") as f:
            json.dump(config, f)

    def confirm(self):
        self.create_config()
        self.func_fileread()

    def add_file(self):
        """
        用于添加文件. 弹出一个文件选择框, 选择文件后, 将文件路径添加到文件列表中.

        Returns:
            list: 此次添加的文件路径的列表.
        """
        # 创建一个隐藏的主窗口
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口

        # 打开文件选择对话框
        filepaths = filedialog.askopenfilenames(
            title="Select a file",
            filetypes=[
                ("Data files", ("*.txt", "*.csv")),
                ("Text files", "*.txt"),
                ("Csv files", "*.csv"),
                ("All files", "*.*"),
            ],
        )

        root.destroy()

        filepaths = list(filepaths)
        self.filepaths.extend(filepaths)
        self.update_filepaths_label()

        return filepaths

    def clear_all(self):
        """
        用于清空文件路径列表.
        """
        self.filepaths.clear()
        self.update_filepaths_label()

    def update_filepaths_label(self):
        """
        更新文件路径列表的label. 首先显示共有多少个文件, 然后分行显示文件路径列表.
        """
        str_to_show = f"Now you have selected {len(self.filepaths)} files:\n"
        for filepath in self.filepaths:
            str_to_show += f"{filepath}\n"
        self.filepaths_label.config(text=str_to_show)


if __name__ == "__main__":
    root = tk.Tk()
    root.title("IV Data Process")
    root.geometry("800x600")

    notebook = ttk.Notebook(root)
    notebook.pack(expand=True, fill="both")

    input_tab1 = InputTab(notebook, tab_name="Input1")
    input_tab2 = InputTab(notebook, tab_name="Input2")

    notebook.pack(expand=True, fill="both")
    root.mainloop()
