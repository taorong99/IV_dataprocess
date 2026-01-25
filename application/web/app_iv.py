import os
import shutil
import time
import re
import logging
from logging.handlers import RotatingFileHandler
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from flask import Flask, request, jsonify, render_template, send_file
from werkzeug.utils import secure_filename
import sys
from pathlib import Path
from datetime import datetime
import urllib.parse

# 导入IV拟合函数
current_dir = Path(__file__).parent
data_process_dir = current_dir / "data_process"
if str(data_process_dir) not in sys.path:
    sys.path.insert(0, str(data_process_dir))

try:
    from iv_fit import iv_fit
    IV_FIT_AVAILABLE = True
except ImportError as e:
    print(f"警告: 无法导入iv_fit模块: {e}")
    print("将使用原有的process_data函数作为备用")
    IV_FIT_AVAILABLE = False

def custom_secure_filename(filename):
    """
    Custom filename sanitization that preserves non-ASCII characters (e.g. Chinese).
    Replaces secure_filename which strips all non-ASCII.
    """
    if not filename:
        return ""
    
    # Decode if bytes
    if isinstance(filename, bytes):
        filename = filename.decode("utf-8")
        
    # Strip path: take only the basename (stripping both / and \)
    if '/' in filename:
        filename = filename.rsplit('/', 1)[-1]
    if '\\' in filename:
        filename = filename.rsplit('\\', 1)[-1]
        
    # Replace dangerous characters for Windows/Linux filesystems
    # Forbidden: < > : " / \ | ? *
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove control characters
    filename = "".join(ch for ch in filename if ch.isprintable())
    
    # Trim spaces and dots
    filename = filename.strip().strip('.')
    
    if not filename:
        filename = f"unnamed_file_{int(time.time())}"
        
    return filename

app = Flask(__name__)

# 配置路径
BASE_FOLDER = "static"
INPUTS_FOLDER = os.path.join(BASE_FOLDER, "inputs")
RESULTS_FOLDER = os.path.join(BASE_FOLDER, "results")
LOGS_FOLDER = "logs"
DEFAULT_USER = "默认用户"
upload_progress = {}

# 创建必要的文件夹
os.makedirs(INPUTS_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)
os.makedirs(LOGS_FOLDER, exist_ok=True)

# 配置日志
def setup_logger():
    """配置日志记录器"""
    # 创建日志格式
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)
    
    # 文件处理器 - 按日期分割日志
    log_date = datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(LOGS_FOLDER, f'flask_app_{log_date}.log')
    
    # 使用 RotatingFileHandler，每个文件最大10MB，保留5个备份
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # 获取Flask应用日志记录器
    app_logger = logging.getLogger('flask_app')
    app_logger.setLevel(logging.INFO)
    
    # 移除所有现有的处理器
    app_logger.handlers.clear()
    
    # 添加处理器
    app_logger.addHandler(file_handler)
    app_logger.addHandler(console_handler)
    
    # 配置Flask内部日志
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(logging.INFO)
    
    # 为werkzeug添加文件处理器
    werkzeug_file_handler = RotatingFileHandler(
        os.path.join(LOGS_FOLDER, f'werkzeug_{log_date}.log'),
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    werkzeug_file_handler.setLevel(logging.INFO)
    werkzeug_file_handler.setFormatter(formatter)
    
    # 移除werkzeug默认的处理器，添加文件处理器
    werkzeug_logger.handlers.clear()
    werkzeug_logger.addHandler(werkzeug_file_handler)
    
    return app_logger

# 初始化日志
logger = setup_logger()

# 保证默认用户存在
def ensure_default_user():
    default_input_path = os.path.join(INPUTS_FOLDER, DEFAULT_USER)
    default_result_path = os.path.join(RESULTS_FOLDER, DEFAULT_USER)
    os.makedirs(default_input_path, exist_ok=True)
    os.makedirs(default_result_path, exist_ok=True)
    logger.info(f"确保默认用户文件夹存在: {default_input_path}, {default_result_path}")

ensure_default_user()

def smart_read(file_path, filename):
    ext = os.path.splitext(filename)[1].lower().strip()
    try:
        if ext == ".csv":
            return pd.read_csv(file_path)
        elif ext == ".txt" or ext == "":
            try:
                return pd.read_csv(file_path, sep="\t", comment="#", header=None)
            except Exception:
                return pd.read_csv(file_path, header=None)
        elif ext in [".xls", ".xlsx"]:
            return pd.read_excel(file_path)
        else:
            try:
                return pd.read_csv(file_path, sep="\t", comment="#", header=None)
            except Exception:
                return pd.read_csv(file_path, header=None)
    except Exception as e:
        error_msg = f"无法解析文件 {filename}: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg)

def process_data(input_folder, output_folder, filename):
    """原有的process_data函数作为备用"""
    input_path = os.path.join(input_folder, filename)
    logger.info(f"处理文件: {filename}")
    
    try:
        df = smart_read(input_path, filename)
        
        if df.shape[1] < 2:
            error_msg = f"文件 {filename} 列数不足，至少需要两列数据"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        plt.figure()
        try:
            plt.plot(df.iloc[:, 0], df.iloc[:, 1], 'o-')
            plt.xlabel("X")
            plt.ylabel("Y")
            plt.title(f"{filename}")
            
            # 生成对应的图片文件名（保持原名，只改扩展名）
            img_filename = os.path.splitext(filename)[0] + ".png"
            img_path = os.path.join(output_folder, img_filename)
            plt.savefig(img_path, bbox_inches='tight')
            logger.info(f"生成图片: {img_filename}")
        finally:
            plt.close('all')
        
        return img_filename  # 只返回文件名，不返回完整路径
    except Exception as e:
        logger.error(f"处理文件 {filename} 失败: {e}")
        raise

def _fallback_process_one_by_one(input_folder, output_folder):
    """Auxiliary function: Process files one by one using the legacy process_data"""
    results = {}
    input_files = [f for f in os.listdir(input_folder) 
                  if f.lower().endswith(('.txt', '.csv')) and os.path.isfile(os.path.join(input_folder, f))]
    
    for filename in input_files:
        try:
            img_filename = process_data(input_folder, output_folder, filename)
            results[filename] = [img_filename]
        except Exception as e:
            logger.error(f"处理文件 {filename} 失败: {e}")
            results[filename] = []
    return results

def process_iv_data(input_folder, output_folder):
    """
    使用新的iv_fit函数批量处理IV数据
    参数:
        input_folder: 输入文件夹路径
        output_folder: 输出文件夹路径（用于存储移动后的图片）
    返回:
        dict: 文件名到生成的图片列表的映射 {filename: [img1, img2, ...]}
    """
    try:
        if not IV_FIT_AVAILABLE:
            logger.warning("iv_fit模块不可用，使用原有的process_data函数逐个处理")
            return _fallback_process_one_by_one(input_folder, output_folder)
        
        # 记录处理前input_folder中的文件
        original_files = set(os.listdir(input_folder))
        logger.info(f"开始批量处理IV数据，文件夹: {input_folder}，文件数量: {len(original_files)}")
        
        # 调用新的iv_fit函数（批量处理整个文件夹）
        iv_fit(input_folder)
        logger.info("iv_fit函数执行完成")
        
        # 获取处理后新生成的文件
        after_files = set(os.listdir(input_folder))
        new_files = after_files - original_files
        logger.info(f"新生成文件数量: {len(new_files)}")
        
        # 筛选出图片文件（.png）并移动到output_folder
        generated_images = []
        for file in new_files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                src_path = os.path.join(input_folder, file)
                dst_path = os.path.join(output_folder, file)
                
                # 移动文件到output_folder
                try:
                    shutil.move(src_path, dst_path)
                    generated_images.append(file)
                    logger.info(f"已移动图片: {file} 从 {src_path} 到 {dst_path}")
                except Exception as e:
                    logger.error(f"移动文件失败 {file}: {e}")
                    # 如果移动失败，尝试复制
                    try:
                        shutil.copy2(src_path, dst_path)
                        generated_images.append(file)
                        logger.info(f"已复制图片: {file} 到 {dst_path}")
                    except Exception as e2:
                        logger.error(f"复制文件失败 {file}: {e2}")
        
        # 如果没有生成图片，尝试使用原有的process_data函数逐个处理
        if not generated_images:
            logger.warning(f"iv_fit未生成图片，尝试使用process_data逐个处理")
            return _fallback_process_one_by_one(input_folder, output_folder)
        
        # 将生成的图片映射回原始文件
        # 根据文件名前缀匹配：例如 "3-4_fit.png" 对应原始文件 "3-4.txt" 或 "3-4.csv"
        results = {}
        input_files = [f for f in os.listdir(input_folder) 
                      if f.lower().endswith(('.txt', '.csv')) and os.path.isfile(os.path.join(input_folder, f))]
        
        for input_file in input_files:
            # 提取基础文件名（不含扩展名）
            base_name = os.path.splitext(input_file)[0]
            
            # 查找所有以base_name开头的图片文件
            related_images = []
            for img_file in generated_images:
                img_base = os.path.splitext(img_file)[0]
                # 匹配规则：
                # 1. 完全匹配：base_name.png
                # 2. 带后缀：base_name_fit.png, base_name_Ic_spread.png, base_name_summary_table.png
                # 3. 以base_name开头的任何图片
                if (img_base == base_name or 
                    img_base.startswith(base_name + '_') or
                    (img_base.startswith(base_name) and len(img_base) > len(base_name))):
                    related_images.append(img_file)
            
            if related_images:
                results[input_file] = related_images
                logger.info(f"文件 {input_file} 匹配到 {len(related_images)} 张图片")
            else:
                results[input_file] = []
                logger.warning(f"文件 {input_file} 未匹配到任何图片")
        
        logger.info(f"批量处理完成，共处理 {len(results)} 个文件")
        return results
        
    except Exception as e:
        error_msg = f"批量处理IV数据失败: {e}"
        logger.error(error_msg)
        # 如果批量处理失败，回退到原有的process_data函数逐个处理
        return _fallback_process_one_by_one(input_folder, output_folder)

@app.route('/')
def index():
    logger.info("访问首页")
    return render_template("index.html")

# 列出所有用户
@app.route('/users', methods=['GET'])
def list_users():
    ensure_default_user()
    # 同时检查inputs和results文件夹
    input_users = [name for name in os.listdir(INPUTS_FOLDER) 
                   if os.path.isdir(os.path.join(INPUTS_FOLDER, name))]
    result_users = [name for name in os.listdir(RESULTS_FOLDER) 
                    if os.path.isdir(os.path.join(RESULTS_FOLDER, name))]
    
    # 合并用户列表，去重
    all_users = list(set(input_users + result_users))
    all_users = sorted(all_users)
    
    if DEFAULT_USER in all_users:
        all_users.remove(DEFAULT_USER)
        all_users.insert(0, DEFAULT_USER)
    
    logger.info(f"列出用户，共 {len(all_users)} 个用户")
    return jsonify(all_users)

# 创建用户
@app.route('/users/create', methods=['POST'])
def create_user():
    username = request.form.get("username", "").strip()
    logger.info(f"创建用户请求，用户名: {username}")
    
    if not username:
        logger.warning("创建用户失败: 用户名为空")
        return jsonify({"success": False, "message": "用户名不能为空"})
    
    # 在inputs和results中都创建用户文件夹
    user_input_folder = os.path.join(INPUTS_FOLDER, username)
    user_result_folder = os.path.join(RESULTS_FOLDER, username)
    os.makedirs(user_input_folder, exist_ok=True)
    os.makedirs(user_result_folder, exist_ok=True)
    
    logger.info(f"用户创建成功: {username}, 路径: {user_input_folder}")
    return jsonify({"success": True, "username": username})

# 列出某用户的所有数据集
@app.route('/datasets', methods=['GET'])
def list_datasets():
    username = request.args.get("username", "").strip()
    logger.info(f"列出数据集请求，用户: {username}")
    
    if not username:
        logger.warning("列出数据集失败: 用户名为空")
        return jsonify([])
    
    user_input_folder = os.path.join(INPUTS_FOLDER, username)
    user_result_folder = os.path.join(RESULTS_FOLDER, username)
    
    # 获取inputs和results中的数据集，合并去重
    input_datasets = []
    result_datasets = []
    
    if os.path.exists(user_input_folder):
        input_datasets = [name for name in os.listdir(user_input_folder)
                         if os.path.isdir(os.path.join(user_input_folder, name))
                         and not name.startswith("_deleted_")]  # 跳过标记删除的文件夹
    
    if os.path.exists(user_result_folder):
        result_datasets = [name for name in os.listdir(user_result_folder)
                          if os.path.isdir(os.path.join(user_result_folder, name)) 
                          and not name.startswith("_deleted_")]  # 跳过标记删除的文件夹
    
    # 合并数据集列表，去重
    all_datasets = list(set(input_datasets + result_datasets))
    
    # 按创建时间排序 - 升序（老的在前，新的在后）
    all_datasets.sort(key=lambda d: os.path.getctime(
        os.path.join(user_input_folder, d) if os.path.exists(os.path.join(user_input_folder, d)) 
        else os.path.join(user_result_folder, d)
    ))
    
    # 返回原始数据集名称，不要编码！
    # 之前错误的代码：encoded_datasets = [urllib.parse.quote(dataset, safe='') for dataset in all_datasets]
    # 应该直接返回原始名称
    logger.info(f"用户 {username} 共有 {len(all_datasets)} 个数据集")
    return jsonify(all_datasets)  # 直接返回原始名称

# 创建数据集
@app.route('/datasets/create', methods=['POST'])
def create_dataset():
    username = request.form.get("username", "").strip()
    dataset = request.form.get("dataset", "").strip()
    logger.info(f"创建数据集请求，用户: {username}, 数据集: {dataset}")
    
    if not username or not dataset:
        logger.warning("创建数据集失败: 用户名或数据集名为空")
        return jsonify({"success": False, "message": "用户名或数据集不能为空"})
    
    user_input_folder = os.path.join(INPUTS_FOLDER, username)
    user_result_folder = os.path.join(RESULTS_FOLDER, username)
    
    if not os.path.exists(user_input_folder):
        os.makedirs(user_input_folder, exist_ok=True)
    if not os.path.exists(user_result_folder):
        os.makedirs(user_result_folder, exist_ok=True)
    
    # 在inputs和results中都创建数据集文件夹
    ds_input_folder = os.path.join(user_input_folder, dataset)
    ds_result_folder = os.path.join(user_result_folder, dataset)
    os.makedirs(ds_input_folder, exist_ok=True)
    os.makedirs(ds_result_folder, exist_ok=True)
    
    logger.info(f"数据集创建成功: {dataset}, 路径: {ds_input_folder}")
    return jsonify({"success": True, "dataset": dataset})

# 删除数据集
@app.route('/datasets/delete', methods=['POST'])
def delete_dataset():
    username = request.form.get("username", "").strip()
    dataset = request.form.get("dataset", "").strip()
    logger.info(f"删除数据集请求，用户: {username}, 数据集: {dataset}")
    
    if not username or not dataset:
        logger.warning("删除数据集失败: 用户名或数据集名为空")
        return jsonify({"success": False, "message": "用户名或数据集不能为空"})
    
    user_input_folder = os.path.join(INPUTS_FOLDER, username)
    user_result_folder = os.path.join(RESULTS_FOLDER, username)
    ds_input_folder = os.path.join(user_input_folder, dataset)
    ds_result_folder = os.path.join(user_result_folder, dataset)
    
    if not os.path.exists(user_input_folder):
        logger.warning(f"删除数据集失败: 用户 {username} 不存在")
        return jsonify({"success": False, "message": "用户不存在"})
    
    try:
        # 标记删除inputs文件夹
        if os.path.exists(ds_input_folder):
            timestamp = int(time.time())
            deleted_input_folder = os.path.join(user_input_folder, f"_deleted_{dataset}_{timestamp}")
            
            # 如果已存在同名的删除标记文件夹，先删除它
            if os.path.exists(deleted_input_folder):
                shutil.rmtree(deleted_input_folder, ignore_errors=True)
                logger.info(f"已清理旧的inputs删除标记文件夹: {deleted_input_folder}")
            
            os.rename(ds_input_folder, deleted_input_folder)
            logger.info(f"已标记删除inputs文件夹: {ds_input_folder} -> {deleted_input_folder}")
        else:
            logger.info(f"inputs文件夹不存在: {ds_input_folder}")
        
        # 标记删除results文件夹
        if os.path.exists(ds_result_folder):
            timestamp = int(time.time())
            deleted_result_folder = os.path.join(user_result_folder, f"_deleted_{dataset}_{timestamp}")
            
            # 如果已存在同名的删除标记文件夹，先删除它
            if os.path.exists(deleted_result_folder):
                shutil.rmtree(deleted_result_folder, ignore_errors=True)
                logger.info(f"已清理旧的results删除标记文件夹: {deleted_result_folder}")
            
            os.rename(ds_result_folder, deleted_result_folder)
            logger.info(f"已标记删除results文件夹: {ds_result_folder} -> {deleted_result_folder}")
        else:
            logger.info(f"results文件夹不存在: {ds_result_folder}")
        
        logger.info(f"数据集 '{dataset}' 标记删除成功")
        return jsonify({"success": True, "message": f"数据集 '{dataset}' 已标记删除"})
    
    except Exception as e:
        error_msg = f"删除数据集失败: {str(e)}"
        logger.error(error_msg)
        return jsonify({"success": False, "message": error_msg})

@app.route('/upload', methods=['POST'])
def upload_files():
    username = request.form.get("username", DEFAULT_USER).strip()
    batchname = request.form.get("batchname", "dataset1").strip()
    user_input_folder = os.path.join(INPUTS_FOLDER, username)
    batch_input_folder = os.path.join(user_input_folder, batchname)
    
    logger.info(f"上传文件请求，用户: {username}, 数据集: {batchname}")
    
    # 创建必要的文件夹
    os.makedirs(batch_input_folder, exist_ok=True)
    
    files = request.files.getlist("datafiles")
    results = []
    
    logger.info(f"共收到 {len(files)} 个文件")
    
    for i, f in enumerate(files):
        try:
            # 清理是否有不安全的文件名
            if not f.filename:
                continue
            # safe_name = secure_filename(f.filename) # secure_filename strips Chinese characters
            safe_name = custom_secure_filename(f.filename)
            
            # 保存原始文件到inputs文件夹
            input_path = os.path.join(batch_input_folder, safe_name)
            f.save(input_path)
            
            logger.info(f"文件上传成功: {safe_name} -> {input_path}")
            results.append({
                "success": True, 
                "filename": safe_name,
                "message": f"{safe_name} 上传成功"
            })
        except Exception as e:
            error_msg = f"文件上传失败 {f.filename}: {e}"
            logger.error(error_msg)
            results.append({
                "success": False, 
                "filename": f.filename if f else "unknown",
                "error": str(e)
            })
    
    return jsonify(results)

# 如果需要更精确的进度跟踪，可以添加以下路由（可选）
@app.route('/upload-progress', methods=['GET'])
def get_upload_progress():
    """获取上传进度（可选功能）"""
    upload_id = request.args.get('upload_id')
    if upload_id in upload_progress:
        return jsonify(upload_progress[upload_id])
    return jsonify({"progress": 0, "status": "unknown"})
# 执行拟合操作
@app.route('/process', methods=['POST'])
def process_files():
    username = request.form.get("username", DEFAULT_USER).strip()
    batchname = request.form.get("batchname", "dataset1").strip()
    
    logger.info(f"开始处理文件，用户: {username}, 数据集: {batchname}")
    
    user_input_folder = os.path.join(INPUTS_FOLDER, username)
    user_result_folder = os.path.join(RESULTS_FOLDER, username)
    batch_input_folder = os.path.join(user_input_folder, batchname)
    batch_result_folder = os.path.join(user_result_folder, batchname)
    
    # 创建结果文件夹
    os.makedirs(batch_result_folder, exist_ok=True)
    
    if not os.path.exists(batch_input_folder):
        error_msg = "数据集不存在或没有上传文件"
        logger.error(error_msg)
        return jsonify({"success": False, "message": error_msg})
    
    results = []
    processed_count = 0
    error_count = 0
    
    # 获取当前时间戳
    timestamp = int(time.time())
    
    try:
        # 使用新的批量IV拟合函数处理整个文件夹
        processing_results = process_iv_data(batch_input_folder, batch_result_folder)
        
        # 处理结果映射：{filename: [img1, img2, ...]}
        for filename, generated_images in processing_results.items():
            if generated_images:
                # 为每个生成的图片构建URL
                img_urls = []
                for img_filename in generated_images:
                    # 对数据集名称和文件名进行URL编码
                    encoded_batchname = urllib.parse.quote(batchname, safe='')
                    encoded_img_filename = urllib.parse.quote(img_filename, safe='')
                    rel_path = os.path.join("static", "results", username, encoded_batchname, encoded_img_filename).replace("\\", "/")
                    # 添加时间戳参数防止缓存
                    img_url = f"/{rel_path}?_={timestamp}"
                    img_urls.append(img_url)
                
                # 如果有多个图片，使用第一个作为主要图片
                main_img_url = img_urls[0] if img_urls else ""
                
                results.append({
                    "success": True,
                    "filename": filename,
                    "img_url": main_img_url,
                    "img_urls": img_urls,
                    "message": f"{filename} 拟合成功，生成 {len(generated_images)} 张图片"
                })
                processed_count += 1
                logger.info(f"文件处理成功: {filename}, 生成图片: {len(generated_images)}张")
            else:
                results.append({
                    "success": False,
                    "filename": filename,
                    "error": f"{filename} 处理失败，未生成图片"
                })
                error_count += 1
                logger.warning(f"文件处理失败: {filename}, 未生成图片")
    except Exception as e:
        error_msg = f"批量处理失败: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            "success": False,
            "message": error_msg,
            "processed": 0,
            "errors": 1,
            "results": []
        })
    
    logger.info(f"处理完成，成功: {processed_count}, 失败: {error_count}")
    return jsonify({
        "success": True if processed_count > 0 else False,
        "processed": processed_count,
        "errors": error_count,
        "results": results,
        "timestamp": timestamp
    })

# 检查inputs文件夹中的文件数量
@app.route('/check-inputs', methods=['GET'])
def check_inputs():
    username = request.args.get("username", DEFAULT_USER).strip()
    dataset = request.args.get("dataset", "").strip()
    
    logger.debug(f"检查输入文件数量，用户: {username}, 数据集: {dataset}")
    
    if not username or not dataset:
        logger.warning("检查输入文件失败: 用户名或数据集名为空")
        return jsonify({"file_count": 0})
    
    # 解码数据集名称
    decoded_dataset = urllib.parse.unquote(dataset)
    input_folder = os.path.join(INPUTS_FOLDER, username, decoded_dataset)
    
    if not os.path.exists(input_folder):
        logger.info(f"输入文件夹不存在: {input_folder}")
        return jsonify({"file_count": 0})
    
    try:
        # 统计文件夹中的文件数量（排除子文件夹）
        file_count = 0
        for item in os.listdir(input_folder):
            item_path = os.path.join(input_folder, item)
            if os.path.isfile(item_path):
                file_count += 1
        
        logger.info(f"文件夹 {input_folder} 中共有 {file_count} 个文件")
        return jsonify({"file_count": file_count})
    except Exception as e:
        error_msg = f"检查inputs文件夹失败: {e}"
        logger.error(error_msg)
        return jsonify({"file_count": 0})

# 检查文件是否已存在
@app.route('/check-file', methods=['GET'])
def check_file():
    username = request.args.get("username", DEFAULT_USER).strip()
    dataset = request.args.get("dataset", "").strip()
    filename = request.args.get("filename", "").strip()
    
    logger.debug(f"检查文件是否存在，用户: {username}, 数据集: {dataset}, 文件名: {filename}")
    
    if not username or not dataset or not filename:
        logger.warning("检查文件失败: 参数不完整")
        return jsonify({"exists": False})
    
    # 解码数据集名称和文件名
    decoded_dataset = urllib.parse.unquote(dataset)
    decoded_filename = urllib.parse.unquote(filename)
    
    input_folder = os.path.join(INPUTS_FOLDER, username, decoded_dataset)
    input_file_path = os.path.join(input_folder, decoded_filename)
    
    # 检查文件是否已存在
    exists = os.path.exists(input_file_path) and os.path.isfile(input_file_path)
    
    logger.info(f"文件 {decoded_filename} 是否存在: {exists}")
    return jsonify({"exists": exists})

# 返回用户下所有数据集及其信息
@app.route('/history', methods=['GET'])
def history():
    username = request.args.get("username", DEFAULT_USER).strip()
    logger.info(f"获取历史数据，用户: {username}")
    
    user_result_folder = os.path.join(RESULTS_FOLDER, username)
    history_data = {}
    
    # 获取当前时间戳
    timestamp = int(time.time())
    
    if os.path.exists(user_result_folder):
        for batch in os.listdir(user_result_folder):
            # 跳过已删除的数据集（以_deleted_开头）
            if batch.startswith("_deleted_"):
                continue
                
            batch_folder = os.path.join(user_result_folder, batch)
            if not os.path.isdir(batch_folder):
                continue
            
            files = []
            summary_table = None
            
            for f in os.listdir(batch_folder):
                if f.lower().endswith(".png"):
                    # 对数据集名称进行URL编码（用于URL路径）
                    encoded_batch = urllib.parse.quote(batch, safe='')
                    
                    # 对文件名进行URL编码
                    encoded_filename = urllib.parse.quote(f, safe='')
                    
                    # 构建URL - 确保路径正确
                    file_url = f"/static/results/{username}/{encoded_batch}/{encoded_filename}?_={timestamp}"
                    
                    if f.lower() == "summary_table.png":
                        summary_table = file_url
                    else:
                        files.append(file_url)
            
            # 按修改时间排序
            try:
                files.sort(key=lambda p: os.path.getmtime(
                    os.path.join(batch_folder, os.path.basename(f))
                ))
            except Exception as e:
                logger.warning(f"排序文件时出错: {e}")
                files.sort(key=lambda p: p.split('/')[-1].split('?')[0])
            
            # 关键修改：使用原始dataset名称作为键，而不是编码后的名称
            # 这样前端可以用原始名称直接查找
            history_data[batch] = {  # 修改这里：使用原始batch名称作为键
                "files": files,
                "summary_table": summary_table
            }
        
        logger.info(f"用户 {username} 共有 {len(history_data)} 个历史数据集")
    else:
        logger.info(f"用户 {username} 没有历史数据")
    
    return jsonify(history_data)

# 删除单个文件（同时删除inputs和results中的文件）
@app.route('/delete', methods=['POST'])
def delete_file():
    username = request.form.get("username", "").strip()
    batchname = request.form.get("batchname", "").strip()
    filename = request.form.get("filename", "").strip()
    
    logger.info(f"删除文件请求，用户: {username}, 数据集: {batchname}, 文件名: {filename}")
    
    if not username or not batchname or not filename:
        logger.warning("删除文件失败: 缺少必要参数")
        return jsonify({"success": False, "message": "缺少必要参数"})
    
    # 删除inputs中的原始文件
    input_file_path = os.path.join(INPUTS_FOLDER, username, batchname, filename)
    input_deleted = False
    if os.path.exists(input_file_path) and os.path.isfile(input_file_path):
        try:
            os.remove(input_file_path)
            input_deleted = True
            logger.info(f"已删除输入文件: {input_file_path}")
        except Exception as e:
            logger.error(f"删除输入文件失败: {e}")
    else:
        logger.warning(f"输入文件不存在: {input_file_path}")
    
    # 删除results中对应的图片文件
    # 查找所有可能的图片文件（可能有多个图片）
    result_files = []
    base_name = os.path.splitext(filename)[0]
    
    # 可能的图片文件名模式（根据iv_fit生成的图片）
    possible_patterns = [
        base_name + ".png",                    # 例如：3-4.png
        base_name + "_fit.png",                # 例如：3-4_fit.png
        base_name + "_Ic_spread.png",          # 例如：3-4_Ic_spread.png
        base_name + "_summary_table.png",      # 总结表
    ]
    
    result_folder = os.path.join(RESULTS_FOLDER, username, batchname)
    if os.path.exists(result_folder):
        for f in os.listdir(result_folder):
            # 提取基础文件名（不含查询参数）
            clean_f = f.split('?')[0]  # 去除查询参数
            
            # 检查是否匹配任何可能的模式
            if clean_f in possible_patterns:
                result_files.append(clean_f)
            # 额外检查：如果文件名以base_name开头，并且是图片文件
            elif clean_f.startswith(base_name) and clean_f.lower().endswith(('.png', '.jpg', '.jpeg')):
                result_files.append(clean_f)
    
    # 删除所有相关的图片文件
    result_deleted_count = 0
    for result_file in result_files:
        result_file_path = os.path.join(result_folder, result_file)
        if os.path.exists(result_file_path) and os.path.isfile(result_file_path):
            try:
                os.remove(result_file_path)
                result_deleted_count += 1
                logger.info(f"已删除结果文件: {result_file_path}")
            except Exception as e:
                logger.error(f"删除结果文件失败 {result_file}: {e}")
    
    # 返回删除结果
    message = []
    if input_deleted:
        message.append(f"原始文件 {filename} 已删除")
    if result_deleted_count > 0:
        message.append(f"{result_deleted_count} 个结果文件已删除")
    
    if not input_deleted and result_deleted_count == 0:
        logger.warning(f"文件 {filename} 不存在")
        return jsonify({"success": False, "message": f"文件 {filename} 不存在"})
    
    logger.info(f"文件删除成功: {', '.join(message)}")
    return jsonify({"success": True, "message": "，".join(message)})

# 恢复简单且正确的图片服务路由
@app.route('/static/results/<path:username>/<path:dataset>/<path:filename>')
def serve_result_image(username, dataset, filename):
    """处理结果图片请求，支持编码的路径"""
    try:
        # 解码路径参数
        decoded_username = urllib.parse.unquote(username)
        decoded_dataset = urllib.parse.unquote(dataset)
        decoded_filename = urllib.parse.unquote(filename)
        
        # 安全性检查：防止目录遍历
        if '..' in decoded_username or '..' in decoded_dataset or '..' in decoded_filename:
             logger.warning(f"检测到非法路径请求: {username}/{dataset}/{filename}")
             return jsonify({"error": "Invalid path"}), 400

        logger.info(f"图片请求 - 用户: {decoded_username}, 数据集: {decoded_dataset}, 文件名: {decoded_filename}")
        
        # 构建并规范化文件路径
        base_results_dir = os.path.abspath(RESULTS_FOLDER)
        file_path = os.path.abspath(os.path.join(RESULTS_FOLDER, decoded_username, decoded_dataset, decoded_filename))
        
        # 确保文件路径在RESULTS_FOLDER内
        if not file_path.startswith(base_results_dir):
            logger.warning(f"访问权限拒绝: {file_path}")
            return jsonify({"error": "Access denied"}), 403

        if os.path.exists(file_path):
            # logger.info(f"返回图片: {file_path}") # 减少日志噪音
            # 设置缓存控制头
            response = send_file(file_path)
            response.headers['Cache-Control'] = 'public, max-age=3600'
            return response
        else:
            logger.warning(f"图片不存在: {file_path}")
            return jsonify({"error": "File not found"}), 404
    except Exception as e:
        logger.error(f"处理图片请求失败: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.before_request
def log_request_info():
    """记录每个请求的信息"""
    logger.info(f"请求: {request.method} {request.path} - IP: {request.remote_addr}")

@app.errorhandler(404)
def not_found_error(error):
    logger.warning(f"404错误: {request.path}")
    return jsonify({"success": False, "message": "请求的资源不存在"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500错误: {str(error)}")
    return jsonify({"success": False, "message": "服务器内部错误"}), 500

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("Flask IV拟合应用启动")
    logger.info(f"INPUTS_FOLDER: {os.path.abspath(INPUTS_FOLDER)}")
    logger.info(f"RESULTS_FOLDER: {os.path.abspath(RESULTS_FOLDER)}")
    logger.info(f"LOGS_FOLDER: {os.path.abspath(LOGS_FOLDER)}")
    
    if IV_FIT_AVAILABLE:
        logger.info("IV拟合模块已加载")
    else:
        logger.warning("IV拟合模块未加载，将使用备用处理函数")
    
    # 修改端口号为 5176
    port = 5176
    logger.info(f"应用将在端口 {port} 启动")
    logger.info("=" * 60)
    
    # 注意：在生产环境中应设置 debug=False
    app.run(host='0.0.0.0', port=port, debug=False)