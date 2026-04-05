from IV_data_process.IVDataProcess_class import IVDataProcess
from IV_data_process.IV_dataprocess_aux import create_table
import os
import json
import numpy as np

def export_iv_data_to_json(iv, output_folder):
    """
    将拟合数据与数组导出为JSON格式，供前端ECharts渲染使用。
    """
    try:
        base_filename = os.path.splitext(iv.filename)[0]
        
        # Default empty fit data
        fit_pos = {"x_v": [], "y_i": []}
        fit_neg = {"x_v": [], "y_i": []}
        
        Ic_1, Ic_2, R_fitp, R_fitm, Vintcp_p, Vintcp_m = iv.fit_result
        i_min, i_max = np.min(iv.I_data), np.max(iv.I_data)
        
        if R_fitp is not None and Vintcp_p is not None:
            arr_i = np.array([i_min, i_max])
            arr_v = arr_i * R_fitp + Vintcp_p
            fit_pos["x_v"] = np.round(arr_v * 1e9).astype(int).tolist()
            fit_pos["y_i"] = np.round(arr_i * 1e9).astype(int).tolist()
        
        if R_fitm is not None and Vintcp_m is not None:
            arr_i = np.array([i_min, i_max])
            arr_v = arr_i * R_fitm + Vintcp_m
            fit_neg["x_v"] = np.round(arr_v * 1e9).astype(int).tolist()
            fit_neg["y_i"] = np.round(arr_i * 1e9).astype(int).tolist()

        aux_data = {
            "curve_type": str(iv.curve_type),
            "ic_pos": int(np.round(Ic_1 * 1e9)) if Ic_1 is not None else None,
            "ic_neg": int(np.round(Ic_2 * 1e9)) if Ic_2 is not None else None,
            "r_pos": float(R_fitp) if R_fitp is not None else None,
            "r_neg": float(R_fitm) if R_fitm is not None else None,
            "v_g": int(np.round(iv.V_g * 1e9)) if hasattr(iv, 'V_g') and iv.V_g is not None else None
        }

        if hasattr(iv, 'Rsg_result') and iv.Rsg_result:
            Rsg_p, R_p_r2, I_p_min, Rsg_m, R_m_r2, I_m_min = iv.Rsg_result
            aux_data["rsg_pos"] = float(Rsg_p) if Rsg_p is not None else None
            aux_data["rsg_neg"] = float(Rsg_m) if Rsg_m is not None else None
        
        # Main fit JSON (IV curve + aux limits + optional Ic spread inside)
        fit_json_data = {
            "schema_version": 1,
            "file": iv.filename,
            "axis_unit": {"x_v_unit": "nV", "y_i_unit": "nA"},
            "chart": {
                "iv": {
                    "x_v": np.round(iv.V_data * 1e9).astype(int).tolist(),
                    "y_i": np.round(iv.I_data * 1e9).astype(int).tolist(),
                    "fit_pos": fit_pos,
                    "fit_neg": fit_neg,
                    "aux": aux_data
                }
            }
        }
        
        ic_spread_data = None
        if iv.curve_type in ['JJa', 'JJs'] and hasattr(iv, 'Ic_array') and iv.Ic_array is not None and len(iv.Ic_array) > 0:
            ic_spread_data = {
                "x_ic": np.round(iv.Ic_array * 1e9).astype(int).tolist(),
                "y_count": iv.JJ_counts.tolist() if hasattr(iv, 'JJ_counts') else [],
                "meta": {
                    "num_jj": int(iv.num_JJ) if hasattr(iv, 'num_JJ') else None,
                    "vg_opt": int(np.round(iv.Vg_optimal * 1e9)) if hasattr(iv, 'Vg_optimal') and iv.Vg_optimal is not None else None
                }
            }
            fit_json_data["chart"]["ic_spread"] = ic_spread_data

        # Save main _fit.json
        json_v_path = os.path.join(output_folder, f"{base_filename}_fit.json")
        with open(json_v_path, 'w', encoding='utf-8') as f:
            json.dump(fit_json_data, f, ensure_ascii=False)
            
        # Save purely _Ic_spread.json if needed
        if ic_spread_data is not None:
            spread_json_data = {
                "schema_version": 1,
                "file": iv.filename,
                "axis_unit": {"x_v_unit": "nV", "y_i_unit": "nA"},
                "chart": {"ic_spread": ic_spread_data}
            }
            json_spread_path = os.path.join(output_folder, f"{base_filename}_Ic_spread.json")
            with open(json_spread_path, 'w', encoding='utf-8') as f:
                json.dump(spread_json_data, f, ensure_ascii=False)
    
    except Exception as j_err:
        print(f'JSON 导出错误: {j_err}')

def iv_fit(input_folder):
# 数据文件格式为'IV', 即第一列为电流I, 第二列为电压V. 电流单位为A, 电压单位为V.
    data_type, I_unit, V_unit = "VI", "mA", "V"
    # 加载所有文件
    file_paths = [os.path.join(input_folder, f) for f in os.listdir(input_folder)]
    ivs = []
    for file_path in file_paths:
        try:
        #创建一个IVDataProcess对象
            iv = IVDataProcess(file_path, data_type, I_unit, V_unit)

            #读取数据文件
            iv.file_read()

            #计算偏置电压V_offset并去除
            # iv.remove_V_offset()

            #矫正V_data的正负号, 防止电阻为负
            iv.Vdata_correct() 

            #判断IV曲线的类型
            iv.curve_classifier() 

            #得到正反向的临界电流
            iv.n_convolve = 1
            iv.get_Ic()

            #拟合电阻R
            iv.fit_R()

            # 计算Rsg, 只会对JJu曲线进行计算.
            try:
                iv.get_Rsg()
            except Exception as e:
                iv.Rsg_result= tuple([0.0] * 6)
                pass

            # 计算Ic_spread, 只会对JJa曲线进行计算.
            iv.get_Ic_spread(print_info=True)

            #画图
            if iv.curve_type == 'JJu':
                linestyle = '-'
            else:
                linestyle = 'o'
            iv.plot_IV(linestyle=linestyle, save_fig=True)
            iv.plot_Ic_spread(save_fig=True) # Ic_spread图, 只对JJa曲线有效
            
            # 导出与前端 ECharts 交互的 JSON 数据
            export_iv_data_to_json(iv, input_folder)
            
            ivs.append(iv)

        except Exception as e:
            print(f'发生错误: {e}')
            print(f'文件{file_path}处理失败')
            continue

    # 创建一个总结表格
    fit_results = [iv.fit_result for iv in ivs]
    curve_types = [iv.curve_type for iv in ivs]
    Rsg_results = [iv.Rsg_result for iv in ivs]
    array_params = [[iv.num_JJ, iv.Vg_optimal] for iv in ivs]
    file_paths_valid = [iv.file_path for iv in ivs]
    create_table(file_paths_valid, fit_results, curve_types, Rsg_results, array_params, save_table=True)