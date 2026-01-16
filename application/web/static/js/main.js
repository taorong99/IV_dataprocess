// 常量定义
const DEFAULT_USER = '默认用户';

// DOM元素引用
const userSel = document.getElementById('username');
const dsSel = document.getElementById('dataset');
const fileList = document.getElementById('fileList');
const plotImg = document.getElementById('plot');
const summaryImg = document.getElementById('summaryTable');
const summaryContainer = document.getElementById('summaryContainer');
const processResult = document.getElementById('processResult');
const fileInput = document.getElementById('datafiles');
const btnNewUser = document.getElementById('btnNewUser');
const btnNewDataset = document.getElementById('btnNewDataset');
const btnDeleteDataset = document.getElementById('btnDeleteDataset');
const btnProcess = document.getElementById('btnProcess');
const btnDownloadAll = document.getElementById('btnDownloadAll');
const uploadedFileCountSpan = document.getElementById('uploadedFileCount');
const processedFileCountSpan = document.getElementById('processedFileCount');
const dragDropArea = document.getElementById('dragDropArea');
const selectedFilesList = document.getElementById('selectedFilesList');
const selectedFilesContent = document.getElementById('selectedFilesContent');
const backendMessageContainer = document.getElementById('backendMessageContainer');
const backendMessageText = document.getElementById('backendMessageText');

// 上传进度相关变量
let uploadController = null;  // 用于取消上传的AbortController
let uploadStartTime = null;
let uploadedBytes = 0;
let totalBytes = 0;
let isUploading = false;
let uploadCheckInterval = null;
let currentUploadFiles = [];

// 状态变量
let currentSelectedDataset = '';
let datasetSummaryTables = {};
let currentInputFileCount = 0;
let currentResultFileCount = 0;
let draggedFiles = [];

// ==================== 工具函数 ====================

function showProcessResult(msg, isSuccess = true) {
  processResult.innerHTML = msg || '';
  processResult.className = isSuccess ? 'success' : 'error';
  
  // 同时在后端信息栏显示（如果是重要信息）
  if (msg && msg.trim() !== '') {
    const type = isSuccess ? 'success' : 'error';
    showBackendMessage(msg, type);
  }
}

function clearProcessResult() {
  processResult.innerHTML = '';
  processResult.className = '';
  hideBackendMessage();
}

function showAlert(message) {
  alert(message);
}

// 防缓存函数
function addCacheBustingParam(url) {
  if (!url) return url;
  
  // 移除所有现有查询参数
  const baseUrl = url.split('?')[0];
  
  // 使用时间戳参数
  const timestamp = Date.now();
  
  return `${baseUrl}?_=${timestamp}`;
}

// URL安全编码函数，单层编码（与后端保持一致）
function encodeDatasetName(dataset) {
  return encodeURIComponent(dataset);
}

// URL安全解码函数
function decodeDatasetName(encodedDataset) {
  return decodeURIComponent(encodedDataset);
}

// 显示后端信息提示
function showBackendMessage(message, type = 'info') {
  if (!message || message.trim() === '') {
    hideBackendMessage();
    return;
  }
  
  backendMessageText.textContent = message;
  
  // 设置alert类型样式
  const backendMessage = backendMessageContainer.querySelector('.backend-message');
  backendMessage.className = 'backend-message alert'; // 重置类
  
  if (type === 'warning') {
    backendMessage.classList.add('alert-warning');
    backendMessage.style.borderLeftColor = '#ffc107';
    backendMessage.querySelector('.me-2').textContent = '⚠️';
  } else if (type === 'error' || type === 'danger') {
    backendMessage.classList.add('alert-danger');
    backendMessage.style.borderLeftColor = '#dc3545';
    backendMessage.querySelector('.me-2').textContent = '❌';
  } else if (type === 'success') {
    backendMessage.classList.add('alert-success');
    backendMessage.style.borderLeftColor = '#198754';
    backendMessage.querySelector('.me-2').textContent = '✅';
  } else {
    backendMessage.classList.add('alert-info');
    backendMessage.style.borderLeftColor = '#0dcaf0';
    backendMessage.querySelector('.me-2').textContent = 'ℹ️';
  }
  
  backendMessageContainer.style.display = 'block';
  
  // 如果是错误类型，10秒后自动隐藏；其他类型5秒后隐藏
  const hideTime = (type === 'error' || type === 'danger') ? 10000 : 5000;
  setTimeout(() => {
    if (backendMessageContainer.style.display === 'block') {
      hideBackendMessage();
    }
  }, hideTime);
}

// 隐藏后端信息提示
function hideBackendMessage() {
  backendMessageContainer.style.display = 'none';
  backendMessageText.textContent = '';
}

// 暴露给全局使用
window.hideBackendMessage = hideBackendMessage;

// 更新文件计数显示
function updateFileCounts(inputCount, resultCount) {
  currentInputFileCount = inputCount;
  currentResultFileCount = resultCount;
  uploadedFileCountSpan.textContent = inputCount;
  processedFileCountSpan.textContent = resultCount;
  
  // 只要数据集中有文件（inputCount > 0）就可以点击执行拟合
  btnProcess.disabled = inputCount === 0;
  
  // 同时更新下载按钮状态
  updateDownloadButtonState();
}

// 更新下载按钮状态
function updateDownloadButtonState() {
  if (!btnDownloadAll) return;
  
  const username = userSel.value;
  const dataset = dsSel.value;
  
  if (!username || !dataset) {
    btnDownloadAll.disabled = true;
    return;
  }
  
  // 从datasetSummaryTables中获取实际的图片数量
  const datasetData = datasetSummaryTables[dataset];
  const hasImages = datasetData && datasetData.files && datasetData.files.length > 0;
  
  btnDownloadAll.disabled = !hasImages;
}

function updateSelectedFilesDisplay() {
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
        <button class="remove-file-btn" onclick="removeDraggedFile(${index})" title="移除文件">
          ×
        </button>
      </div>
    `;
  });
  
  selectedFilesContent.innerHTML = html;
}

function removeDraggedFile(index) {
  draggedFiles.splice(index, 1);
  updateSelectedFilesDisplay();
  
  if (draggedFiles.length > 0) {
    updateFileInputFromDraggedFiles();
  } else {
    fileInput.value = '';
  }
}

function updateFileInputFromDraggedFiles() {
  const dataTransfer = new DataTransfer();
  
  draggedFiles.forEach(file => {
    dataTransfer.items.add(file);
  });
  
  fileInput.files = dataTransfer.files;
}

// ==================== 上传进度相关函数 ====================

// 显示上传进度模态框
function showUploadProgress(totalFiles, totalSize) {
  // 重置进度
  document.getElementById('overallProgressBar').style.width = '0%';
  document.getElementById('overallProgressText').textContent = '0%';
  document.getElementById('currentFileProgressBar').style.width = '0%';
  document.getElementById('currentFileProgressText').textContent = '0%';
  document.getElementById('uploadedCount').textContent = '0';
  document.getElementById('totalFilesCount').textContent = totalFiles;
  
  // 隐藏当前文件进度（初始时）
  document.getElementById('currentFileSection').style.display = 'none';
  document.getElementById('speedInfo').style.display = 'none';
  
  // 显示模态框
  const modal = new bootstrap.Modal(document.getElementById('uploadProgressModal'));
  modal.show();
  
  // 开始计时
  uploadStartTime = Date.now();
  uploadedBytes = 0;
  totalBytes = totalSize;
  isUploading = true;
  
  // 开始更新速度显示
  uploadCheckInterval = setInterval(updateUploadSpeed, 1000);
}

// 更新总体进度
function updateOverallProgress(uploaded, total) {
  const progress = total > 0 ? Math.round((uploaded / total) * 100) : 0;
  
  const progressBar = document.getElementById('overallProgressBar');
  const progressText = document.getElementById('overallProgressText');
  
  progressBar.style.width = `${progress}%`;
  progressText.textContent = `${progress}%`;
  
  // 更新已上传文件数
  document.getElementById('uploadedCount').textContent = uploaded;
}

// 更新当前文件进度
function updateCurrentFileProgress(filename, progress) {
  const section = document.getElementById('currentFileSection');
  section.style.display = 'block';
  
  document.getElementById('currentFileName').textContent = filename;
  
  const progressBar = document.getElementById('currentFileProgressBar');
  const progressText = document.getElementById('currentFileProgressText');
  
  progressBar.style.width = `${progress}%`;
  progressText.textContent = `${progress}%`;
}

// 更新上传速度和剩余时间
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
  
  speedInfo.style.display = 'block';
  speedElement.textContent = formatBytes(speed) + '/s';
  timeElement.textContent = formatTime(remainingSeconds);
}

// 格式化字节大小
function formatBytes(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 格式化时间
function formatTime(seconds) {
  if (seconds === 0) return '0秒';
  if (seconds < 60) return Math.ceil(seconds) + '秒';
  
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.ceil(seconds % 60);
  
  if (minutes < 60) return `${minutes}分${remainingSeconds}秒`;
  
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}小时${remainingMinutes}分`;
}

// 取消上传
function cancelUpload() {
  if (uploadController) {
    uploadController.abort();
    showBackendMessage('上传已取消', 'warning');
  }
  
  if (uploadCheckInterval) {
    clearInterval(uploadCheckInterval);
    uploadCheckInterval = null;
  }
  
  isUploading = false;
  
  // 隐藏模态框
  const modal = bootstrap.Modal.getInstance(document.getElementById('uploadProgressModal'));
  if (modal) modal.hide();
}

// 上传完成后清理
function cleanupUploadProgress() {
  if (uploadCheckInterval) {
    clearInterval(uploadCheckInterval);
    uploadCheckInterval = null;
  }
  
  isUploading = false;
  uploadController = null;
  
  // 延迟隐藏模态框，让用户看到100%完成
  setTimeout(() => {
    const modal = bootstrap.Modal.getInstance(document.getElementById('uploadProgressModal'));
    if (modal) modal.hide();
  }, 1500);
}

// 使用XMLHttpRequest上传单个文件（支持进度）
function uploadFileWithProgress(formData, file, currentIndex, totalFiles, uploadedSoFar, totalSize) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    
    // 进度事件
    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable) {
        // 当前文件进度
        const fileProgress = Math.round((event.loaded / event.total) * 100);
        updateCurrentFileProgress(file.name, fileProgress);
        
        // 更新总上传字节数
        uploadedBytes = uploadedSoFar + event.loaded;
        updateUploadSpeed();
      }
    });
    
    // 完成事件
    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const response = JSON.parse(xhr.responseText);
          resolve(response);
        } catch (e) {
          resolve({ success: true });
        }
      } else {
        reject(new Error(`上传失败: HTTP ${xhr.status}`));
      }
    });
    
    // 错误事件
    xhr.addEventListener('error', () => {
      reject(new Error('网络错误'));
    });
    
    // 中止事件
    xhr.addEventListener('abort', () => {
      reject(new DOMException('上传被取消', 'AbortError'));
    });
    
    // 设置超时
    xhr.timeout = 300000; // 5分钟超时
    xhr.addEventListener('timeout', () => {
      reject(new Error('上传超时'));
    });
    
    // 发送请求
    xhr.open('POST', '/upload');
    xhr.send(formData);
    
    // 保存xhr引用以便取消
    if (uploadController) {
      uploadController.signal.addEventListener('abort', () => {
        xhr.abort();
      });
    }
  });
}

// ==================== API函数 ====================

async function checkFileExists(username, dataset, filename) {
  try {
    const encodedDataset = encodeDatasetName(dataset);
    const response = await fetch(`/check-file?username=${encodeURIComponent(username)}&dataset=${encodedDataset}&filename=${encodeURIComponent(filename)}&_=${Date.now()}`);
    if (response.ok) {
      const data = await response.json();
      return data.exists || false;
    }
    return false;
  } catch (err) {
    console.error('检查文件是否存在失败:', err);
    return false;
  }
}

async function fetchJSON(url, options = {}) {
  try {
    // 为GET请求添加时间戳防止缓存
    let finalUrl = url;
    if (!options.method || options.method === 'GET') {
      const separator = url.includes('?') ? '&' : '?';
      finalUrl = `${url}${separator}_=${Date.now()}`;
    }
    
    const resp = await fetch(finalUrl, options);
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status} fetching ${finalUrl}`);
    }
    return await resp.json();
  } catch (err) {
    console.error(`请求失败 ${url}:`, err);
    throw err;
  }
}

async function getInputFileCount(username, dataset) {
  try {
    const encodedDataset = encodeDatasetName(dataset);
    const data = await fetchJSON(`/check-inputs?username=${encodeURIComponent(username)}&dataset=${encodedDataset}`);
    return data.file_count || 0;
  } catch (err) {
    console.error('获取输入文件数量失败:', err);
    return 0;
  }
}

function updateSummaryTable(dataset) {
  const summaryUrl = datasetSummaryTables[dataset]?.summary_table;
  // 这里使用原始dataset名称查找
  if (summaryUrl) {
    // 为summary图片添加防缓存参数
    summaryImg.src = addCacheBustingParam(summaryUrl);
    summaryContainer.style.display = 'block';
    document.querySelector('#plot-container > div:first-child').style.flex = '2';
  } else {
    summaryImg.src = '';
    summaryContainer.style.display = 'none';
    document.querySelector('#plot-container > div:first-child').style.flex = '1';
  }
}

// ==================== 下载相关函数 ====================

// 下载所有图片函数
async function downloadAllImages() {
  const username = userSel.value;
  const dataset = dsSel.value;
  
  if (!username || !dataset) {
    showBackendMessage('请先选择用户和数据集', 'warning');
    return;
  }
  
  try {
    // 获取当前数据集的所有图片
    const datasetData = datasetSummaryTables[dataset];
    if (!datasetData || !datasetData.files || datasetData.files.length === 0) {
      showBackendMessage('该数据集中没有图片可下载', 'warning');
      return;
    }
    
    const imageUrls = datasetData.files;
    
    // 显示下载进度
    showBackendMessage(`正在准备下载 ${imageUrls.length} 个图片...`, 'info');
    
    // 使用JSZip库来打包下载（如果没有JSZip，可以用逐个下载的方式）
    if (typeof JSZip === 'undefined') {
      // 如果JSZip未加载，使用逐个下载的方式
      showBackendMessage('正在逐个下载图片，请稍候...', 'info');
      downloadImagesOneByOne(imageUrls, dataset);
      return;
    }
    
    // 使用JSZip打包下载
    await downloadImagesAsZip(imageUrls, dataset);
    
  } catch (err) {
    console.error('下载图片失败:', err);
    showBackendMessage(`下载失败：${err.message}`, 'error');
  }
}

// 逐个下载图片（兼容方案）
function downloadImagesOneByOne(imageUrls, datasetName) {
  let downloadedCount = 0;
  const totalCount = imageUrls.length;
  
  // 更新按钮状态
  if (btnDownloadAll) {
    btnDownloadAll.disabled = true;
    btnDownloadAll.textContent = `下载中...`;
  }
  
  // 逐个创建下载链接
  imageUrls.forEach((url, index) => {
    setTimeout(() => {
      const link = document.createElement('a');
      link.href = url.split('?')[0]; // 去掉缓存参数
      const filename = url.split('/').pop().split('?')[0];
      link.download = filename;
      link.style.display = 'none';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      downloadedCount++;
      
      // 更新进度
      if (downloadedCount === totalCount) {
        showBackendMessage(`成功下载 ${totalCount} 个图片`, 'success');
        if (btnDownloadAll) {
          btnDownloadAll.disabled = false;
          btnDownloadAll.textContent = '下载所有图片';
        }
      }
    }, index * 100); // 间隔100ms避免浏览器阻塞
  });
}

// 使用JSZip打包下载（推荐方式）
async function downloadImagesAsZip(imageUrls, datasetName) {
  try {
    if (btnDownloadAll) {
      btnDownloadAll.disabled = true;
      btnDownloadAll.textContent = '打包中...';
    }
    
    showBackendMessage('正在打包图片，请稍候...', 'info');
    
    const zip = new JSZip();
    const folder = zip.folder(datasetName);
    
    // 添加summary table图片（如果有）
    const summaryUrl = datasetSummaryTables[datasetName]?.summary_table;
    if (summaryUrl) {
      const summaryBlob = await fetchBlob(summaryUrl);
      const summaryFilename = summaryUrl.split('/').pop().split('?')[0] || 'summary_table.png';
      folder.file(summaryFilename, summaryBlob);
    }
    
    // 添加所有拟合图片
    for (let i = 0; i < imageUrls.length; i++) {
      const url = imageUrls[i];
      const filename = url.split('/').pop().split('?')[0];
      
      try {
        const blob = await fetchBlob(url);
        folder.file(filename, blob);
        
        // 更新进度
        if (i % 5 === 0 || i === imageUrls.length - 1) {
          const progress = Math.round(((i + 1) / imageUrls.length) * 100);
          showBackendMessage(`正在打包图片... ${progress}% (${i + 1}/${imageUrls.length})`, 'info');
        }
      } catch (err) {
        console.warn(`下载图片失败 ${filename}:`, err);
      }
    }
    
    // 生成ZIP文件
    showBackendMessage('正在生成ZIP文件...', 'info');
    const content = await zip.generateAsync({ type: 'blob' });
    
    // 下载ZIP文件
    const zipLink = document.createElement('a');
    zipLink.href = URL.createObjectURL(content);
    zipLink.download = `${datasetName}_图片包_${new Date().toISOString().split('T')[0]}.zip`;
    zipLink.style.display = 'none';
    document.body.appendChild(zipLink);
    zipLink.click();
    document.body.removeChild(zipLink);
    
    // 清理URL对象
    setTimeout(() => URL.revokeObjectURL(zipLink.href), 100);
    
    showBackendMessage(`成功打包下载 ${imageUrls.length} 个图片`, 'success');
    
  } catch (err) {
    console.error('打包下载失败:', err);
    showBackendMessage(`打包下载失败：${err.message}`, 'error');
  } finally {
    if (btnDownloadAll) {
      btnDownloadAll.disabled = false;
      btnDownloadAll.textContent = '下载所有图片';
    }
  }
}

// 获取图片Blob
async function fetchBlob(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return await response.blob();
}

// ==================== 核心功能函数 ====================

async function initUsers() {
  try {
    clearProcessResult();
    const users = await fetchJSON('/users');
    userSel.innerHTML = '';
    
    users.forEach(u => {
      const opt = document.createElement('option');
      opt.value = u;
      opt.textContent = u;
      userSel.appendChild(opt);
    });
    
    const defaultInList = users.includes(DEFAULT_USER);
    userSel.value = defaultInList ? DEFAULT_USER : (users[0] || '');
    
    if (!userSel.value) {
      showProcessResult('没有可用用户，请先创建用户', false);
      dsSel.disabled = true;
      return;
    }
    
    await loadDatasetsForUser(userSel.value);
  } catch (err) {
    showProcessResult(`加载用户失败：${err.message}`, false);
  }
}

async function loadDatasetsForUser(username, keepCurrentSelection = false) {
  try {
    clearProcessResult();
    const encodedUsername = encodeURIComponent(username);
    const datasets = await fetchJSON(`/datasets?username=${encodedUsername}`);
    
    // 解码数据集名称显示（从服务器获取的应该是编码后的，需要解码显示）
    const decodedDatasets = datasets.map(ds => decodeDatasetName(ds));
    const reversedDatasets = [...decodedDatasets].reverse();
    const previousSelection = keepCurrentSelection ? dsSel.value : '';
    
    dsSel.innerHTML = '';
    reversedDatasets.forEach(ds => {
      const opt = document.createElement('option');
      opt.value = ds; // 存储解码后的名称
      opt.textContent = ds; // 显示解码后的名称
      dsSel.appendChild(opt);
    });

    dsSel.disabled = false;
    
    if (reversedDatasets.length > 0) {
      let datasetToSelect;
      if (keepCurrentSelection && previousSelection && reversedDatasets.includes(previousSelection)) {
        datasetToSelect = previousSelection;
      } else {
        datasetToSelect = reversedDatasets[0];
      }
      
      dsSel.value = datasetToSelect;
      currentSelectedDataset = datasetToSelect;
      btnDeleteDataset.style.display = 'block';
      await displayDataset(username, datasetToSelect);
    } else {
      dsSel.value = '';
      currentSelectedDataset = '';
      btnDeleteDataset.style.display = 'none';
      updateFileCounts(0, 0);
      fileList.innerHTML = '<div class="empty-message">该用户暂无数据集，请新建并上传。</div>';
      plotImg.src = '';
      summaryImg.src = '';
      summaryContainer.style.display = 'none';
      document.querySelector('#plot-container > div:first-child').style.flex = '1';
    }
  } catch (err) {
    showProcessResult(`加载数据集失败：${err.message}`, false);
  }
}

// 修改displayDataset函数中的这部分代码
async function displayDataset(username, dataset) {
  try {
    clearProcessResult();
    if (!dataset) return;
    
    const encodedDataset = encodeDatasetName(dataset); // 单层编码用于API请求
    const [historyData, inputFileCount] = await Promise.all([
      fetchJSON(`/history?username=${encodeURIComponent(username)}`),
      getInputFileCount(username, dataset)
    ]);
    
    datasetSummaryTables = {};
    // 修复：直接使用原始键，不进行解码
    for (const dsKey in historyData) {
      datasetSummaryTables[dsKey] = {
        files: historyData[dsKey].files || [],
        summary_table: historyData[dsKey].summary_table || null
      };
    }
    
    // 现在 datasetSummaryTables 的键是原始名称
    const datasetData = datasetSummaryTables[dataset] || { files: [], summary_table: null };
    const resultFiles = datasetData.files || [];
    
    fileList.innerHTML = '';
    plotImg.src = '';
    
    // 更新summary_table显示
    updateSummaryTable(dataset);
    
    // 更新文件计数
    updateFileCounts(inputFileCount, resultFiles.length);
    
    if (resultFiles.length === 0 && inputFileCount === 0) {
      fileList.innerHTML = '<div class="empty-message">该数据集中暂无文件，请上传。</div>';
      return;
    }
    
    // 显示results中的文件
    resultFiles.forEach(fileUrl => {
      const item = document.createElement('div');
      item.className = 'file-item';
      
      const thumb = document.createElement('img');
      thumb.className = 'thumb';
      // 缩略图使用防缓存URL
      thumb.src = addCacheBustingParam(fileUrl);
      // 从URL中提取干净的文件名作为alt文本
      const fullFileName = fileUrl.split('/').pop();
      const cleanFileName = fullFileName.split('?')[0];
      thumb.alt = cleanFileName;
      
      const btnShow = document.createElement('button');
      btnShow.className = 'btn btn-outline-secondary btn-sm';
      // 显示干净的文件名（只需要单层解码）
      btnShow.textContent = decodeURIComponent(cleanFileName);
      btnShow.onclick = () => { 
        // 点击时使用防缓存URL
        plotImg.src = addCacheBustingParam(fileUrl);
      };
      
      const btnDelete = document.createElement('button');
      btnDelete.className = 'btn btn-danger btn-sm';
      btnDelete.textContent = '删除';
      btnDelete.onclick = async () => {
        // 提取原始文件名：去掉图片后缀，恢复为.txt文件
        let originalFilename = decodeURIComponent(cleanFileName);
        
        // 移除常见的图片后缀
        if (originalFilename.endsWith('_fit.png')) {
          originalFilename = originalFilename.replace('_fit.png', '.txt');
        } else if (originalFilename.endsWith('_Ic_spread.png')) {
          originalFilename = originalFilename.replace('_Ic_spread.png', '.txt');
        } else if (originalFilename.endsWith('_summary_table.png')) {
          originalFilename = originalFilename.replace('_summary_table.png', '.txt');
        } else if (originalFilename.endsWith('.png')) {
          originalFilename = originalFilename.replace('.png', '.txt');
        } else if (originalFilename.endsWith('.jpg')) {
          originalFilename = originalFilename.replace('.jpg', '.txt');
        } else if (originalFilename.endsWith('.jpeg')) {
          originalFilename = originalFilename.replace('.jpeg', '.txt');
        }
        
        if (!confirm(`确定要删除文件 "${decodeURIComponent(cleanFileName)}" 吗？\n对应的原始文件 "${originalFilename}" 也将被删除。`)) return;
        
        try {
          const fd = new FormData();
          fd.append('username', username);
          fd.append('batchname', dataset); // 发送原始数据集名称
          fd.append('filename', originalFilename);
          const res = await fetchJSON('/delete', { method: 'POST', body: fd });
          if (res.success) {
            item.remove();
            // 如果当前显示的图片是被删除的，清空显示
            if (plotImg.src.includes(cleanFileName)) {
              plotImg.src = '';
            }
            await loadDatasetsForUser(username, true);
            showProcessResult(res.message, true);
          } else {
            showProcessResult(res.message || '删除失败', false);
          }
        } catch (err) {
          showProcessResult(`删除失败：${err.message}`, false);
        }
      };
      
      item.appendChild(thumb);
      item.appendChild(btnShow);
      item.appendChild(btnDelete);
      fileList.appendChild(item);
    });
    
    // 显示第一个文件的图像
    if (resultFiles.length > 0) {
      plotImg.src = addCacheBustingParam(resultFiles[0]);
    }
    
    // 更新下载按钮状态
    updateDownloadButtonState();
  } catch (err) {
    showProcessResult(`加载数据失败：${err.message}`, false);
  }
}

async function processDataset() {
  const username = userSel.value;
  const dataset = dsSel.value;
  
  if (!username || !dataset) {
    showProcessResult('请先选择用户和数据集', false);
    return;
  }
  
  if (currentInputFileCount === 0) {
    showProcessResult('该数据集没有需要处理的文件', false);
    return;
  }
  
  try {
    clearProcessResult();
    btnProcess.disabled = true;
    btnProcess.textContent = '处理中...';
    
    const fd = new FormData();
    fd.append('username', username);
    fd.append('batchname', dataset); // 使用原始数据集名称
    
    const result = await fetchJSON('/process', { method: 'POST', body: fd });
    
    if (result.success) {
      const successMsg = `成功处理 ${result.processed} 个文件`;
      const errorMsg = result.errors > 0 ? `，${result.errors} 个文件处理失败` : '';
      showProcessResult(successMsg + errorMsg, true);
      
      // 处理成功后重新加载数据集
      await loadDatasetsForUser(username, true);
      showProcessResult('拟合处理完成！', true);
      
    } else {
      showProcessResult('处理失败：没有找到可处理的文件', false);
    }
  } catch (err) {
    showProcessResult(`处理失败：${err.message}`, false);
    console.error('处理失败:', err);
  } finally {
    btnProcess.textContent = '执行拟合';
  }
}

// ==================== 上传文件功能 ====================

// 修改后的上传文件函数（支持进度显示）
async function uploadFiles() {
  clearProcessResult();
  const username = userSel.value;
  const dataset = dsSel.value;
  
  if (!username) return showProcessResult('请先选择用户', false);
  if (!dataset) return showProcessResult('请先选择或新建数据集', false);
  
  let filesToUpload = [];
  if (draggedFiles.length > 0) {
    filesToUpload = draggedFiles;
  } else if (fileInput.files && fileInput.files.length > 0) {
    filesToUpload = Array.from(fileInput.files);
  } else {
    return showProcessResult('请选择要上传的文件', false);
  }
  
  // 计算总大小
  const totalSize = filesToUpload.reduce((sum, file) => sum + file.size, 0);
  
  try {
    // 检查重复文件
    let hasDuplicate = false;
    for (const file of filesToUpload) {
      const exists = await checkFileExists(username, dataset, file.name);
      if (exists) {
        showAlert(`文件 "${file.name}" 已存在，请先删除！`);
        hasDuplicate = true;
        break;
      }
    }
    
    if (hasDuplicate) return;
    
    // 显示进度模态框
    showUploadProgress(filesToUpload.length, totalSize);
    updateOverallProgress(0, filesToUpload.length);
    
    // 创建AbortController用于取消上传
    uploadController = new AbortController();
    currentUploadFiles = filesToUpload;
    
    // 使用FormData上传所有文件（原接口保持兼容）
    const fd = new FormData();
    fd.append('username', username);
    fd.append('batchname', dataset); // 使用原始数据集名称
    for (const file of filesToUpload) {
      fd.append('datafiles', file);
    }
    
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
        updateCurrentFileProgress(filesToUpload[currentFileIndex].name, fileProgress);
        
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
            loadDatasetsForUser(username, true);
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
    fileInput.value = '';
  }
}

// 暴露取消上传函数给全局
window.cancelUpload = cancelUpload;

// ==================== 事件处理 ====================

// 新建用户
btnNewUser.addEventListener('click', async () => {
  const newUser = prompt('请输入新用户名：');
  if (!newUser) return;
  try {
    const fd = new FormData();
    fd.append('username', newUser);
    const res = await fetchJSON('/users/create', { method: 'POST', body: fd });
    if (res.success) {
      await initUsers();
      userSel.value = newUser;
      await loadDatasetsForUser(newUser);
      showProcessResult(`用户 "${newUser}" 创建成功`, true);
    } else {
      showProcessResult(res.message || '创建用户失败', false);
    }
  } catch (err) {
    showProcessResult(`创建用户失败：${err.message}`, false);
  }
});

// 新建数据集
btnNewDataset.addEventListener('click', async () => {
  const username = userSel.value;
  if (!username) return showProcessResult('请先选择用户', false);
  
  const newDs = prompt('请输入新数据集名称：\n注意：不能包含 % 号');
  if (!newDs) return;
  
  // 检查是否包含 % 号
  if (newDs.includes('%')) {
    showProcessResult('数据集名称不能包含 % 号', false);
    return;
  }
  
  try {
    const fd = new FormData();
    fd.append('username', username);
    fd.append('dataset', newDs);
    const res = await fetchJSON('/datasets/create', { method: 'POST', body: fd });
    if (res.success) {
      await loadDatasetsForUser(username);
      dsSel.value = newDs;
      await displayDataset(username, newDs);
      showProcessResult(`数据集 "${newDs}" 创建成功`, true);
    } else {
      showProcessResult(res.message || '创建数据集失败', false);
    }
  } catch (err) {
    showProcessResult(`创建数据集失败：${err.message}`, false);
  }
});

// 删除数据集
btnDeleteDataset.addEventListener('click', async () => {
  const username = userSel.value;
  const dataset = dsSel.value;
  
  if (!username || !dataset) {
    return showProcessResult('请先选择要删除的数据集', false);
  }
  
  if (!confirm(`确定要删除数据集 "${dataset}" 吗？此操作将删除该数据集中的所有文件，且不可恢复！`)) {
    return;
  }
  
  try {
    const fd = new FormData();
    fd.append('username', username);
    fd.append('dataset', dataset);
    const res = await fetchJSON('/datasets/delete', { method: 'POST', body: fd });
    
    if (res.success) {
      await loadDatasetsForUser(username);
      showProcessResult(`数据集 "${dataset}" 已删除`, false);
    } else {
      showProcessResult(res.message || '删除数据集失败', false);
    }
  } catch (err) {
    showProcessResult(`删除数据集失败：${err.message}`, false);
  }
});

// 用户选择变化
userSel.addEventListener('change', async () => {
  await loadDatasetsForUser(userSel.value);
});

// 数据集选择变化
dsSel.addEventListener('change', async () => {
  const username = userSel.value;
  const ds = dsSel.value;
  if (!ds) return;
  currentSelectedDataset = ds;
  await displayDataset(username, ds);
});

// ==================== 拖拽上传功能 ====================

function preventDefaults(e) {
  e.preventDefault();
  e.stopPropagation();
}

function highlight() {
  dragDropArea.classList.add('drag-over');
}

function unhighlight() {
  dragDropArea.classList.remove('drag-over');
}

function handleDrop(e) {
  const dt = e.dataTransfer;
  const files = dt.files;
  
  if (files.length > 0) {
    const acceptedFiles = Array.from(files).filter(file => {
      const fileName = file.name.toLowerCase();
      return fileName.endsWith('.txt') || fileName.endsWith('.csv');
    });
    
    if (acceptedFiles.length > 0) {
      draggedFiles = draggedFiles.concat(acceptedFiles);
      updateSelectedFilesDisplay();
      updateFileInputFromDraggedFiles();
      uploadFiles();
    } else {
      showAlert('只支持 .txt 和 .csv 文件格式！');
    }
  }
}

// 点击拖拽区域触发文件选择
dragDropArea.addEventListener('click', () => {
  fileInput.click();
});

// 监听文件输入变化
fileInput.addEventListener('change', (e) => {
  if (e.target.files && e.target.files.length > 0) {
    draggedFiles = Array.from(e.target.files);
    updateSelectedFilesDisplay();
    updateFileInputFromDraggedFiles();
    uploadFiles();
  }
});

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
btnProcess.addEventListener('click', processDataset);

// 下载按钮事件监听
if (btnDownloadAll) {
  btnDownloadAll.addEventListener('click', downloadAllImages);
}

// ==================== 初始化 ====================

initUsers();