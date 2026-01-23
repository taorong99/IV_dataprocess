// static/js/api.js
/**
 * API调用模块 - 封装所有后端请求
 */

// 全局配置
const API_BASE = ''; // 使用相对路径

// 通用的fetch包装函数
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

// 用户相关API
async function getUsers() {
  return await fetchJSON(`${API_BASE}/users`);
}

async function createUser(username) {
  const fd = new FormData();
  fd.append('username', username);
  return await fetchJSON(`${API_BASE}/users/create`, { 
    method: 'POST', 
    body: fd 
  });
}

// 数据集相关API
async function getDatasets(username) {
  const encodedUsername = encodeURIComponent(username);
  return await fetchJSON(`${API_BASE}/datasets?username=${encodedUsername}`);
}

async function createDataset(username, dataset) {
  const fd = new FormData();
  fd.append('username', username);
  fd.append('dataset', dataset);
  return await fetchJSON(`${API_BASE}/datasets/create`, { 
    method: 'POST', 
    body: fd 
  });
}

async function deleteDataset(username, dataset) {
  const fd = new FormData();
  fd.append('username', username);
  fd.append('dataset', dataset);
  return await fetchJSON(`${API_BASE}/datasets/delete`, { 
    method: 'POST', 
    body: fd 
  });
}

// 文件相关API
async function uploadFiles(username, dataset, files) {
  const fd = new FormData();
  fd.append('username', username);
  fd.append('batchname', dataset);
  
  // 添加所有文件
  if (Array.isArray(files)) {
    files.forEach(file => {
      fd.append('datafiles', file);
    });
  }
  
  return await fetchJSON(`${API_BASE}/upload`, { 
    method: 'POST', 
    body: fd 
  });
}

async function processDataset(username, dataset) {
  const fd = new FormData();
  fd.append('username', username);
  fd.append('batchname', dataset);
  return await fetchJSON(`${API_BASE}/process`, { 
    method: 'POST', 
    body: fd 
  });
}

async function checkFileExists(username, dataset, filename) {
  const encodedDataset = encodeDatasetName(dataset);
  const encodedUsername = encodeURIComponent(username);
  const encodedFilename = encodeURIComponent(filename);
  
  try {
    const response = await fetchJSON(
      `${API_BASE}/check-file?username=${encodedUsername}&dataset=${encodedDataset}&filename=${encodedFilename}`
    );
    return response.exists || false;
  } catch (err) {
    console.error('检查文件是否存在失败:', err);
    return false;
  }
}

async function getInputFileCount(username, dataset) {
  try {
    const encodedDataset = encodeDatasetName(dataset);
    const data = await fetchJSON(
      `${API_BASE}/check-inputs?username=${encodeURIComponent(username)}&dataset=${encodedDataset}`
    );
    return data.file_count || 0;
  } catch (err) {
    console.error('获取输入文件数量失败:', err);
    return 0;
  }
}

// 历史数据API
async function getHistory(username) {
  const encodedUsername = encodeURIComponent(username);
  return await fetchJSON(`${API_BASE}/history?username=${encodedUsername}`);
}

// 删除文件API
async function deleteFile(username, dataset, filename) {
  const fd = new FormData();
  fd.append('username', username);
  fd.append('batchname', dataset);
  fd.append('filename', filename);
  return await fetchJSON(`${API_BASE}/delete`, { 
    method: 'POST', 
    body: fd 
  });
}