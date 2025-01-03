# Release Notes
## [1.2] - 2025-01-03
### Added
- 添加了`get_Rsg()`方法, 用于计算JJu的subgap电阻. 可自行设置`V_sg`属性, 默认为2e-3V.
- 添加了`get_Ic_spread()`和`plot_Ic_spread()`方法, 用于计算和绘制`JJa`的Ic的分布.
- 添加了`GUI_IV`脚本, 用于GUI界面的IV数据处理. 虽然还在调试中, 但已经能满足基本的需求. 所以此次将其同步更新.

### Fixed
- 修复了画图时部分参数的显示问题, 目前大多数参数显示的是4位有效数字, 而不是2位小数点. 这样避免了数据过大和过小发生的显示冗余和不全的问题.

### Changed
- 优化了`fit_R()`的方法, 以适配`JJa`的数据. 主要是将拟合的数据范围根据结的个数进行了调整.



## [1.1] - 2024-11-18
### Added
-  增加了`n_convolve`参数, 用于`get_Ic()`时的平滑处理. 默认为1, 即不进行平滑处理. 当`n_convolve`大于1时, 会用数据点附近的`n_convolve`个点进行平均处理.

### Fixed
- 修复了`remove_V_offset()`方法中容易出现`V_offset_calarray`数组为`np.array([nan])`的问题, 这会导致`V_data`的元素都变成`nan`. 改动有两点: 1. 当`I_data`没有小于10uA的元素时, 默认取绝对值最小的5个点. 2. 在移除离群点前, 先判断移除后`V_offset_calarray`是否还有元素.
- 修复了`IV_unit_convert()`单位大于1时函数失效的问题.
- 修复了`IVdata_split_4_segments()`函数中`incres_seg`的切片错误问题, 当初未仔细检查copilot自动给出的切片区间.
  
### Changed
- 将`JJu`曲线判断的阈值从`Vg/2`改为`Vg/4`, 以适应更多的情况, 例如济南测试C6样品只有准粒子隧穿曲线的情况.


## [1.0] - 2024-11-17
### Added
- 添加了`IVDataProcess`类，用于处理IV数据. 主要根据自己以前写的脚本进行了重写.

### Fixed
- 将最开始的IV_data_process脚本进行了重写.

### Changed
- 将`select_files`和`create_table`移到了辅助函数中.