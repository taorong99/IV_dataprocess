// static/js/utils.js
/**
 * 通用工具函数模块
 */

// 防缓存URL函数
function addCacheBustingParam(url) {
  if (!url) return url;
  const baseUrl = url.split('?')[0];
  const timestamp = Date.now();
  return `${baseUrl}?_=${timestamp}`;
}

// URL安全编码函数
function encodeDatasetName(dataset) {
  return encodeURIComponent(dataset);
}

// URL安全解码函数
function decodeDatasetName(encodedDataset) {
  return decodeURIComponent(encodedDataset);
}

// 显示后端消息提示
function showBackendMessage(message, type = 'info', containerId = 'backendMessageContainer') {
  const container = document.getElementById(containerId);
  const textElement = document.getElementById('backendMessageText');
  
  if (!message || !container || !textElement) return;
  
  textElement.textContent = message;
  
  const backendMessage = container.querySelector('.backend-message');
  backendMessage.className = 'backend-message alert';
  
  // 设置样式
  const icon = backendMessage.querySelector('.me-2');
  if (type === 'warning') {
    backendMessage.classList.add('alert-warning');
    backendMessage.style.borderLeftColor = '#ffc107';
    if (icon) icon.textContent = '⚠️';
  } else if (type === 'error' || type === 'danger') {
    backendMessage.classList.add('alert-danger');
    backendMessage.style.borderLeftColor = '#dc3545';
    if (icon) icon.textContent = '❌';
  } else if (type === 'success') {
    backendMessage.classList.add('alert-success');
    backendMessage.style.borderLeftColor = '#198754';
    if (icon) icon.textContent = '✅';
  } else {
    backendMessage.classList.add('alert-info');
    backendMessage.style.borderLeftColor = '#0dcaf0';
    if (icon) icon.textContent = 'ℹ️';
  }
  
  container.style.display = 'block';
  
  // 自动隐藏
  const hideTime = (type === 'error' || type === 'danger') ? 10000 : 5000;
  setTimeout(() => {
    if (container.style.display === 'block') {
      hideBackendMessage(containerId);
    }
  }, hideTime);
}

// 隐藏后端消息
function hideBackendMessage(containerId = 'backendMessageContainer') {
  const container = document.getElementById(containerId);
  if (container) {
    container.style.display = 'none';
    const textElement = document.getElementById('backendMessageText');
    if (textElement) textElement.textContent = '';
  }
}

// 显示处理结果消息
function showProcessResult(msg, isSuccess = true, resultElementId = 'processResult') {
  const resultElement = document.getElementById(resultElementId);
  if (!resultElement) return;
  
  resultElement.innerHTML = msg || '';
  resultElement.className = isSuccess ? 'success' : 'error';
  
  // 同时在后端信息栏显示
  if (msg && msg.trim() !== '') {
    const type = isSuccess ? 'success' : 'error';
    showBackendMessage(msg, type);
  }
}

// 清除处理结果
function clearProcessResult(resultElementId = 'processResult') {
  const resultElement = document.getElementById(resultElementId);
  if (resultElement) {
    resultElement.innerHTML = '';
    resultElement.className = '';
  }
  hideBackendMessage();
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

// 简单的警告框
function showAlert(message) {
  alert(message);
}