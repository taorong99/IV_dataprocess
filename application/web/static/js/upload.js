// static/js/upload.js
/**
 * 文件上传模块 - 处理拖拽上传和进度显示
 */

// 上传状态
let uploadController = null;
let uploadStartTime = null;
let uploadedBytes = 0;
let totalBytes = 0;
let isUploading = false;
let uploadCheckInterval = null;
let currentUploadFiles = [];
let draggedFiles = [];

// DOM元素
let fileInput, dragDropArea, selectedFilesList, selectedFilesContent;

/**
 * 初始化上传模块
 */
function initUploadModule(options = {}) {
  fileInput = options.fileInput || document.getElementById('datafiles');
  dragDropArea = options.dragDropArea || document.getElementById('dragDropArea');
  selectedFilesList = options.selectedFilesList || document.getElementById('selectedFilesList');
  selectedFilesContent = options.selectedFilesContent || document.getElementById('selectedFilesContent');
  
  console.log('初始化上传模块:', {
    fileInput: !!fileInput,
    dragDropArea: !!dragDropArea,
    selectedFilesList: !!selectedFilesList,
    selectedFilesContent: !!selectedFilesContent
  });
  
  setupDragDrop();
}

/**
 * 设置拖拽上传事件
 */
function setupDragDrop() {
  if (!dragDropArea || !fileInput) {
    console.error('上传模块初始化失败: 缺少必要的DOM元素');
    return;
  }
  
  console.log('设置拖拽上传事件');
  
  // 点击拖拽区域触发文件选择
  dragDropArea.addEventListener('click', handleDragAreaClick);
  
  // 监听文件输入变化
  fileInput.addEventListener('change', handleFileInputChange);
  
  // 拖拽事件处理
  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dragDropArea.addEventListener(eventName, preventDefaults, false);
  });
  
  ['dragenter', 'dragover'].forEach(eventName => {
    dragDropArea.addEventListener(eventName, highlight, false);
  });
  
  ['dragleave', 'drop'].forEach(eventName => {
    dragDropArea.addEventListener(eventName, unhighlight, false);
  });
  
  dragDropArea.addEventListener('drop', handleDrop, false);
}

/**
 * 处理拖拽区域点击
 */
function handleDragAreaClick() {
  console.log('点击拖拽区域');
  if (fileInput) {
    fileInput.click();
  }
}

/**
 * 更新已选择文件显示
 */
function updateSelectedFilesDisplay() {
  if (!selectedFilesList || !selectedFilesContent) return;
  
  if (draggedFiles.length === 0) {
    selectedFilesList.style.display = 'none';
    return;
  }
  
  selectedFilesList.style.display = 'block';
  let html = '';
  
  draggedFiles.forEach((file, index) => {
    const sizeKB = (file.size / 1024).toFixed(1);
    html += `
      <div class="selected-file-item">
        <div class="selected-file-name" title="${file.name}">
          ${index + 1}. ${file.name} (${sizeKB} KB)
        </div>
        <button class="remove-file-btn" onclick="window.uploadManager.removeDraggedFile(${index})" title="移除文件">
          ×
        </button>
      </div>
    `;
  });
  
  selectedFilesContent.innerHTML = html;
}

/**
 * 移除拖拽文件
 */
function removeDraggedFile(index) {
  draggedFiles.splice(index, 1);
  updateSelectedFilesDisplay();
  
  if (draggedFiles.length > 0) {
    updateFileInputFromDraggedFiles();
  } else if (fileInput) {
    fileInput.value = '';
  }
}

/**
 * 更新文件输入元素
 */
function updateFileInputFromDraggedFiles() {
  if (!fileInput) return;
  
  const dataTransfer = new DataTransfer();
  draggedFiles.forEach(file => {
    dataTransfer.items.add(file);
  });
  
  fileInput.files = dataTransfer.files;
}

/**
 * 处理文件输入变化
 */
function handleFileInputChange(e) {
  console.log('文件输入变化:', e.target.files.length, '个文件');
  
  if (e.target.files && e.target.files.length > 0) {
    draggedFiles = Array.from(e.target.files);
    updateSelectedFilesDisplay();
    updateFileInputFromDraggedFiles();
    
    // 自动上传
    autoUploadFiles();
  }
}

/**
 * 自动上传文件
 */
function autoUploadFiles() {
  console.log('自动上传检查:', {
    hasDatasetManager: !!window.datasetManager,
    hasGetCurrentUser: window.datasetManager && !!window.datasetManager.getCurrentUser,
    hasGetCurrentDataset: window.datasetManager && !!window.datasetManager.getCurrentDataset
  });
  
  if (!window.datasetManager || !window.datasetManager.getCurrentUser || !window.datasetManager.getCurrentDataset) {
    console.warn('无法自动上传: datasetManager未正确初始化');
    showBackendMessage('系统初始化中，请稍后重试', 'warning');
    return;
  }
  
  const username = window.datasetManager.getCurrentUser();
  const dataset = window.datasetManager.getCurrentDataset();
  
  console.log('获取当前用户和数据集:', { username, dataset });
  
  if (username && dataset) {
    console.log('开始自动上传到:', username, dataset);
    startUpload(username, dataset);
  } else {
    console.warn('用户或数据集未选择:', { username, dataset });
    showBackendMessage('请先选择用户和数据集', 'warning');
  }
}

/**
 * 处理拖放事件
 */
function handleDrop(e) {
  console.log('文件拖放事件');
  const dt = e.dataTransfer;
  const files = dt.files;
  
  if (files.length > 0) {
    const acceptedFiles = Array.from(files).filter(file => {
      const fileName = file.name.toLowerCase();
      const isAccepted = fileName.endsWith('.txt') || fileName.endsWith('.csv');
      console.log('文件检查:', file.name, isAccepted);
      return isAccepted;
    });
    
    if (acceptedFiles.length > 0) {
      console.log('接受文件数量:', acceptedFiles.length);
      draggedFiles = draggedFiles.concat(acceptedFiles);
      updateSelectedFilesDisplay();
      updateFileInputFromDraggedFiles();
      
      // 自动上传
      autoUploadFiles();
    } else {
      console.warn('无接受的文件格式');
      showBackendMessage('只支持 .txt 和 .csv 文件格式！', 'warning');
    }
  }
}

/**
 * 开始上传文件
 */
async function startUpload(username, dataset) {
  console.log('开始上传:', username, dataset, '文件数:', draggedFiles.length);
  
  clearProcessResult();
  
  if (!username) {
    showBackendMessage('请先选择用户', 'warning');
    return;
  }
  
  if (!dataset) {
    showBackendMessage('请先选择或新建数据集', 'warning');
    return;
  }
  
  let filesToUpload = [];
  if (draggedFiles.length > 0) {
    filesToUpload = draggedFiles;
  } else if (fileInput && fileInput.files && fileInput.files.length > 0) {
    filesToUpload = Array.from(fileInput.files);
  } else {
    showBackendMessage('请选择要上传的文件', 'warning');
    return;
  }
  
  // 计算总大小
  totalBytes = filesToUpload.reduce((sum, file) => sum + file.size, 0);
  
  try {
    // 检查重复文件
    let hasDuplicate = false;
    for (const file of filesToUpload) {
      const exists = await checkFileExists(username, dataset, file.name);
      if (exists) {
        showBackendMessage(`文件 "${file.name}" 已存在，请先删除！`, 'warning');
        hasDuplicate = true;
        break;
      }
    }
    
    if (hasDuplicate) return;
    
    // 显示进度模态框
    showUploadProgress(filesToUpload.length, totalBytes);
    updateOverallProgress(0, filesToUpload.length);
    
    // 创建AbortController用于取消上传
    uploadController = new AbortController();
    currentUploadFiles = filesToUpload;
    
    // 使用XMLHttpRequest来获取上传进度
    const xhr = new XMLHttpRequest();
    
    // 进度事件
    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable) {
        // 计算总体进度
        const overallProgress = Math.round((event.loaded / event.total) * 100);
        
        // 计算当前文件进度（假设均匀分布）
        const filesCount = filesToUpload.length;
        const bytesPerFile = event.total / filesCount;
        const currentFileIndex = Math.min(
          Math.floor(event.loaded / bytesPerFile),
          filesCount - 1
        );
        
        const fileProgress = Math.round(
          ((event.loaded % bytesPerFile) / bytesPerFile) * 100
        );
        
        // 更新显示
        updateOverallProgress(currentFileIndex + 1, filesCount);
        if (currentFileIndex < filesToUpload.length) {
          updateCurrentFileProgress(filesToUpload[currentFileIndex].name, fileProgress);
        }
        
        // 更新上传字节数
        uploadedBytes = event.loaded;
      }
    });
    
    // 完成事件
    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const result = JSON.parse(xhr.responseText);
          
          let successCount = 0;
          let errorCount = 0;
          let errorMessages = [];
          
          result.forEach(res => {
            if (res.success) {
              successCount++;
            } else {
              errorCount++;
              errorMessages.push(`${res.filename}: ${res.error || '上传失败'}`);
            }
          });
          
          if (successCount > 0) {
            showProcessResult(`成功上传 ${successCount} 个文件`, true);
            // 通知datasetManager重新加载数据
            if (window.datasetManager && window.datasetManager.loadDatasetsForUser) {
              window.datasetManager.loadDatasetsForUser(username, true);
            }
            draggedFiles = [];
            updateSelectedFilesDisplay();
          }
          
          if (errorCount > 0) {
            showProcessResult(`上传失败 ${errorCount} 个文件:\n${errorMessages.join('\n')}`, false);
          }
          
          // 完成时显示100%进度
          updateOverallProgress(filesToUpload.length, filesToUpload.length);
          updateCurrentFileProgress('', 100);
          
          // 清理上传状态
          cleanupUploadProgress();
          
        } catch (e) {
          showProcessResult(`解析响应失败: ${e.message}`, false);
          cleanupUploadProgress();
        }
      } else {
        showProcessResult(`上传失败: HTTP ${xhr.status}`, false);
        cleanupUploadProgress();
      }
    });
    
    // 错误事件
    xhr.addEventListener('error', () => {
      showProcessResult('网络错误，上传失败', false);
      cleanupUploadProgress();
    });
    
    // 中止事件
    xhr.addEventListener('abort', () => {
      showBackendMessage('上传已取消', 'warning');
      cleanupUploadProgress();
    });
    
    // 设置超时
    xhr.timeout = 300000; // 5分钟超时
    xhr.addEventListener('timeout', () => {
      showProcessResult('上传超时，请检查网络连接', false);
      cleanupUploadProgress();
    });
    
    // 准备FormData
    const fd = new FormData();
    fd.append('username', username);
    fd.append('batchname', dataset);
    for (const file of filesToUpload) {
      fd.append('datafiles', file);
    }
    
    // 发送请求
    xhr.open('POST', '/upload');
    
    // 绑定取消事件
    uploadController.signal.addEventListener('abort', () => {
      xhr.abort();
    });
    
    xhr.send(fd);
    
  } catch (err) {
    showProcessResult(`上传失败：${err.message}`, false);
    cleanupUploadProgress();
  } finally {
    if (fileInput) fileInput.value = '';
  }
}

/**
 * 显示上传进度模态框
 */
function showUploadProgress(totalFiles, totalSize) {
  const overallProgressBar = document.getElementById('overallProgressBar');
  const overallProgressText = document.getElementById('overallProgressText');
  const currentFileProgressBar = document.getElementById('currentFileProgressBar');
  const currentFileProgressText = document.getElementById('currentFileProgressText');
  const uploadedCount = document.getElementById('uploadedCount');
  const totalFilesCount = document.getElementById('totalFilesCount');
  
  if (!overallProgressBar || !overallProgressText) {
    console.error('上传进度模态框元素未找到');
    return;
  }
  
  // 重置进度
  overallProgressBar.style.width = '0%';
  overallProgressText.textContent = '0%';
  if (currentFileProgressBar) currentFileProgressBar.style.width = '0%';
  if (currentFileProgressText) currentFileProgressText.textContent = '0%';
  if (uploadedCount) uploadedCount.textContent = '0';
  if (totalFilesCount) totalFilesCount.textContent = totalFiles;
  
  // 隐藏当前文件进度（初始时）
  const currentFileSection = document.getElementById('currentFileSection');
  const speedInfo = document.getElementById('speedInfo');
  if (currentFileSection) currentFileSection.style.display = 'none';
  if (speedInfo) speedInfo.style.display = 'none';
  
  // 确保之前的模态框已正确关闭
  closeModal('uploadProgressModal');
  
  // 显示模态框
  const modalElement = document.getElementById('uploadProgressModal');
  if (modalElement && typeof bootstrap !== 'undefined') {
    try {
      const modal = new bootstrap.Modal(modalElement, {
        backdrop: 'static', // 设置为static，防止点击外部关闭
        keyboard: false     // 禁用ESC键关闭
      });
      modal.show();
    } catch (e) {
      console.error('显示上传进度模态框失败:', e);
    }
  }
  
  // 开始计时
  uploadStartTime = Date.now();
  uploadedBytes = 0;
  totalBytes = totalSize;
  isUploading = true;
  
  // 开始更新速度显示
  uploadCheckInterval = setInterval(updateUploadSpeed, 1000);
}

/**
 * 更新总体进度
 */
function updateOverallProgress(uploaded, total) {
  const progress = total > 0 ? Math.round((uploaded / total) * 100) : 0;
  
  const progressBar = document.getElementById('overallProgressBar');
  const progressText = document.getElementById('overallProgressText');
  const uploadedCount = document.getElementById('uploadedCount');
  
  if (progressBar) progressBar.style.width = `${progress}%`;
  if (progressText) progressText.textContent = `${progress}%`;
  if (uploadedCount) uploadedCount.textContent = uploaded;
}

/**
 * 更新当前文件进度
 */
function updateCurrentFileProgress(filename, progress) {
  const section = document.getElementById('currentFileSection');
  const currentFileName = document.getElementById('currentFileName');
  const progressBar = document.getElementById('currentFileProgressBar');
  const progressText = document.getElementById('currentFileProgressText');
  
  if (section) section.style.display = 'block';
  if (currentFileName) currentFileName.textContent = filename;
  if (progressBar) progressBar.style.width = `${progress}%`;
  if (progressText) progressText.textContent = `${progress}%`;
}

/**
 * 更新上传速度和剩余时间
 */
function updateUploadSpeed() {
  if (!uploadStartTime || !isUploading) return;
  
  const elapsedSeconds = (Date.now() - uploadStartTime) / 1000;
  if (elapsedSeconds < 1) return;
  
  const speed = uploadedBytes / elapsedSeconds; // 字节/秒
  const remainingBytes = totalBytes - uploadedBytes;
  const remainingSeconds = speed > 0 ? remainingBytes / speed : 0;
  
  const speedElement = document.getElementById('uploadSpeed');
  const timeElement = document.getElementById('timeRemaining');
  const speedInfo = document.getElementById('speedInfo');
  
  if (speedInfo) speedInfo.style.display = 'block';
  if (speedElement) speedElement.textContent = formatBytes(speed) + '/s';
  if (timeElement) timeElement.textContent = formatTime(remainingSeconds);
}

/**
 * 取消上传
 */
function cancelUpload() {
  console.log('取消上传');
  
  if (uploadController) {
    uploadController.abort();
    showBackendMessage('上传已取消', 'warning');
  }
  
  if (uploadCheckInterval) {
    clearInterval(uploadCheckInterval);
    uploadCheckInterval = null;
  }
  
  isUploading = false;
  
  // 关闭模态框
  closeModal('uploadProgressModal');
}

/**
 * 上传完成后清理
 */
function cleanupUploadProgress() {
  if (uploadCheckInterval) {
    clearInterval(uploadCheckInterval);
    uploadCheckInterval = null;
  }
  
  isUploading = false;
  uploadController = null;
  
  // 延迟关闭模态框，让用户看到100%完成
  setTimeout(() => {
    closeModal('uploadProgressModal');
  }, 1500);
}

/**
 * 关闭指定模态框
 */
function closeModal(modalId) {
  const modalElement = document.getElementById(modalId);
  if (modalElement) {
    // 使用Bootstrap方式关闭
    if (typeof bootstrap !== 'undefined') {
      try {
        const modal = bootstrap.Modal.getInstance(modalElement);
        if (modal) {
          modal.hide();
        } else {
          // 如果没有实例，手动隐藏
          manualCloseModal(modalElement);
        }
      } catch (e) {
        console.warn('关闭模态框时出错:', e);
        manualCloseModal(modalElement);
      }
    } else {
      // 手动关闭
      manualCloseModal(modalElement);
    }
  }
  
  // 确保修复模态框背景
  fixModalBackdrop();
}

/**
 * 手动关闭模态框
 */
function manualCloseModal(modalElement) {
  if (!modalElement) return;
  
  modalElement.classList.remove('show');
  modalElement.style.display = 'none';
  
  // 调用全局修复函数
  if (typeof fixModalBackdrop === 'function') {
    fixModalBackdrop();
  }
}

/**
 * 拖拽辅助函数
 */
function preventDefaults(e) {
  e.preventDefault();
  e.stopPropagation();
}

function highlight() {
  if (dragDropArea) dragDropArea.classList.add('drag-over');
}

function unhighlight() {
  if (dragDropArea) dragDropArea.classList.remove('drag-over');
}

// 暴露给全局使用
window.uploadManager = {
  initUploadModule,
  updateSelectedFilesDisplay,
  removeDraggedFile,
  startUpload,
  cancelUpload,
  closeModal
};

// 暴露取消上传函数给全局
window.cancelUpload = cancelUpload;

// 在页面加载完成后初始化上传模块
document.addEventListener('DOMContentLoaded', function() {
  console.log('DOM加载完成，初始化上传模块');
  
  // 等待所有资源加载完成
  setTimeout(() => {
    const fileInput = document.getElementById('datafiles');
    const dragDropArea = document.getElementById('dragDropArea');
    
    if (fileInput && dragDropArea) {
      console.log('找到上传相关DOM元素，初始化上传模块');
      initUploadModule({
        fileInput,
        dragDropArea,
        selectedFilesList: document.getElementById('selectedFilesList'),
        selectedFilesContent: document.getElementById('selectedFilesContent')
      });
    } else {
      console.error('上传模块初始化失败: 未找到必要的DOM元素');
    }
  }, 500);
});