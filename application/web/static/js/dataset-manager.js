// static/js/dataset-manager.js
/**
 * 数据集管理模块 - 处理用户和数据集的选择、创建、删除
 */

// 全局状态
let currentSelectedDataset = '';
let datasetSummaryTables = {};
let currentInputFileCount = 0;
let currentResultFileCount = 0;

// DOM元素引用
let userSel, dsSel, fileList, plotImg, summaryImg, summaryContainer;
let btnNewUser, btnNewDataset, btnDeleteDataset, btnProcess;
let uploadedFileCountSpan, processedFileCountSpan;

/**
 * 初始化数据集管理器
 */
function initDatasetManager(options = {}) {
  // 获取DOM元素
  userSel = options.userSel || document.getElementById('username');
  dsSel = options.dsSel || document.getElementById('dataset');
  fileList = options.fileList || document.getElementById('fileList');
  plotImg = options.plotImg || document.getElementById('plot');
  summaryImg = options.summaryImg || document.getElementById('summaryTable');
  summaryContainer = options.summaryContainer || document.getElementById('summaryContainer');
  btnNewUser = options.btnNewUser || document.getElementById('btnNewUser');
  btnNewDataset = options.btnNewDataset || document.getElementById('btnNewDataset');
  btnDeleteDataset = options.btnDeleteDataset || document.getElementById('btnDeleteDataset');
  btnProcess = options.btnProcess || document.getElementById('btnProcess');
  uploadedFileCountSpan = options.uploadedFileCountSpan || document.getElementById('uploadedFileCount');
  processedFileCountSpan = options.processedFileCountSpan || document.getElementById('processedFileCount');
  
  // 绑定事件
  if (userSel) userSel.addEventListener('change', handleUserChange);
  if (dsSel) dsSel.addEventListener('change', handleDatasetChange);
  if (btnNewUser) btnNewUser.addEventListener('click', handleNewUser);
  if (btnNewDataset) btnNewDataset.addEventListener('click', handleNewDataset);
  if (btnDeleteDataset) btnDeleteDataset.addEventListener('click', handleDeleteDataset);
  if (btnProcess) btnProcess.addEventListener('click', handleProcessDataset);
  
  // 初始化用户
  initUsers();
}

/**
 * 获取当前用户
 */
function getCurrentUser() {
  return userSel ? userSel.value : '';
}

/**
 * 获取当前数据集
 */
function getCurrentDataset() {
  return dsSel ? dsSel.value : '';
}

/**
 * 初始化用户列表
 */
async function initUsers() {
  try {
    clearProcessResult();
    const users = await getUsers();
    
    if (!userSel) return;
    
    userSel.innerHTML = '';
    
    users.forEach(u => {
      const opt = document.createElement('option');
      opt.value = u;
      opt.textContent = u;
      userSel.appendChild(opt);
    });
    
    // 使用storageManager获取要加载的用户
    let userToLoad;
    if (window.storageManager && window.storageManager.getValidUserToLoad) {
      userToLoad = window.storageManager.getValidUserToLoad(users);
    } else {
      // 降级：使用默认用户
      userToLoad = users.includes('默认用户') ? '默认用户' : (users[0] || '');
    }
    
    userSel.value = userToLoad;
    
    if (!userSel.value) {
      showProcessResult('没有可用用户，请先创建用户', false);
      if (dsSel) dsSel.disabled = true;
      return;
    }
    
    await loadDatasetsForUser(userSel.value);
  } catch (err) {
    showProcessResult(`加载用户失败：${err.message}`, false);
  }
}

/**
 * 为用户加载数据集
 */
async function loadDatasetsForUser(username, keepCurrentSelection = false) {
  try {
    clearProcessResult();
    const datasets = await getDatasets(username);
    
    const decodedDatasets = datasets.map(ds => decodeDatasetName(ds));
    const reversedDatasets = [...decodedDatasets].reverse();
    const previousSelection = keepCurrentSelection && dsSel ? dsSel.value : '';
    
    if (!dsSel) return;
    
    dsSel.innerHTML = '';
    reversedDatasets.forEach(ds => {
      const opt = document.createElement('option');
      opt.value = ds;
      opt.textContent = ds;
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
      if (btnDeleteDataset) btnDeleteDataset.style.display = 'block';
      await displayDataset(username, datasetToSelect);
    } else {
      dsSel.value = '';
      currentSelectedDataset = '';
      if (btnDeleteDataset) btnDeleteDataset.style.display = 'none';
      updateFileCounts(0, 0);
      if (fileList) fileList.innerHTML = '<div class="empty-message">该用户暂无数据集，请新建并上传。</div>';
      if (plotImg) plotImg.src = '';
      if (summaryImg) summaryImg.src = '';
      if (summaryContainer) summaryContainer.style.display = 'none';
      const plotContainerFirstDiv = document.querySelector('#plot-container > div:first-child');
      if (plotContainerFirstDiv) plotContainerFirstDiv.style.flex = '1';
    }
  } catch (err) {
    showProcessResult(`加载数据集失败：${err.message}`, false);
  }
}

/**
 * 显示数据集内容
 */
async function displayDataset(username, dataset) {
  try {
    clearProcessResult();
    if (!dataset) return;
    
    const [historyData, inputFileCount] = await Promise.all([
      getHistory(username),
      getInputFileCount(username, dataset)
    ]);
    
    datasetSummaryTables = {};
    for (const dsKey in historyData) {
      datasetSummaryTables[dsKey] = {
        files: historyData[dsKey].files || [],
        summary_table: historyData[dsKey].summary_table || null
      };
    }
    
    const datasetData = datasetSummaryTables[dataset] || { files: [], summary_table: null };
    const resultFiles = datasetData.files || [];
    
    if (fileList) fileList.innerHTML = '';
    if (plotImg) plotImg.src = '';
    
    // 更新summary_table显示
    updateSummaryTable(dataset);
    
    const fitFilesCount = resultFiles.filter(url => {
      const decodedUrl = decodeURIComponent(url);
      // Check if it ends with _fit.png (ignoring query parameters)
      return decodedUrl.split('?')[0].endsWith('_fit.png');
    }).length;

    // 更新文件计数
    updateFileCounts(inputFileCount, fitFilesCount);
    
    if (resultFiles.length === 0 && inputFileCount === 0) {
      if (fileList) fileList.innerHTML = '<div class="empty-message">该数据集中暂无文件，请上传。</div>';
      return;
    }
    
    // 显示results中的文件
    resultFiles.forEach(fileUrl => {
      if (!fileList) return;
      
      const item = document.createElement('div');
      item.className = 'file-item';
      
      const thumb = document.createElement('img');
      thumb.className = 'thumb';
      thumb.src = addCacheBustingParam(fileUrl);
      const fullFileName = fileUrl.split('/').pop();
      const cleanFileName = fullFileName.split('?')[0];
      thumb.alt = cleanFileName;
      
      const btnShow = document.createElement('button');
      btnShow.className = 'btn btn-outline-secondary btn-sm';
      btnShow.textContent = decodeURIComponent(cleanFileName);
      btnShow.onclick = () => { 
        if (plotImg) plotImg.src = addCacheBustingParam(fileUrl);
      };
      
      const btnDelete = document.createElement('button');
      btnDelete.className = 'btn btn-danger btn-sm';
      btnDelete.textContent = '删除';
      btnDelete.onclick = async () => {
        // 提取原始文件名
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
          const res = await deleteFile(username, dataset, originalFilename);
          if (res.success) {
            item.remove();
            // 如果当前显示的图片是被删除的，清空显示
            if (plotImg && plotImg.src.includes(cleanFileName)) {
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
    if (resultFiles.length > 0 && plotImg) {
      plotImg.src = addCacheBustingParam(resultFiles[0]);
    }
    
    // 更新下载按钮状态
    if (window.downloadManager && window.downloadManager.updateDownloadButtonState) {
      window.downloadManager.updateDownloadButtonState();
    }
    
  } catch (err) {
    showProcessResult(`加载数据失败：${err.message}`, false);
  }
}

/**
 * 更新参数总结表显示
 */
function updateSummaryTable(dataset) {
  const summaryUrl = datasetSummaryTables[dataset]?.summary_table;
  
  if (!summaryImg || !summaryContainer) return;
  
  if (summaryUrl) {
    summaryImg.src = addCacheBustingParam(summaryUrl);
    summaryContainer.style.display = 'block';
    const plotContainerFirstDiv = document.querySelector('#plot-container > div:first-child');
    if (plotContainerFirstDiv) plotContainerFirstDiv.style.flex = '2';
  } else {
    summaryImg.src = '';
    summaryContainer.style.display = 'none';
    const plotContainerFirstDiv = document.querySelector('#plot-container > div:first-child');
    if (plotContainerFirstDiv) plotContainerFirstDiv.style.flex = '1';
  }
}

/**
 * 更新文件计数
 */
function updateFileCounts(inputCount, resultCount) {
  currentInputFileCount = inputCount;
  currentResultFileCount = resultCount;
  
  if (uploadedFileCountSpan) uploadedFileCountSpan.textContent = inputCount;
  if (processedFileCountSpan) processedFileCountSpan.textContent = resultCount;
  
  // 更新处理按钮状态
  if (btnProcess) {
    btnProcess.disabled = inputCount === 0;
  }
  
  // 更新下载按钮状态
  if (window.downloadManager && window.downloadManager.updateDownloadButtonState) {
    window.downloadManager.updateDownloadButtonState();
  }
}

/**
 * 获取数据集摘要表
 */
function getDatasetSummaryTables() {
  return datasetSummaryTables;
}

/**
 * 获取文件计数
 */
function getFileCounts() {
  return {
    inputCount: currentInputFileCount,
    resultCount: currentResultFileCount
  };
}

/**
 * 事件处理函数
 */
async function handleUserChange() {
  if (userSel) {
    await loadDatasetsForUser(userSel.value);
  }
}

async function handleDatasetChange() {
  const username = userSel ? userSel.value : '';
  const ds = dsSel ? dsSel.value : '';
  if (!ds) return;
  currentSelectedDataset = ds;
  await displayDataset(username, ds);
}

async function handleNewUser() {
  const newUser = prompt('请输入新用户名：');
  if (!newUser) return;
  
  try {
    const res = await createUser(newUser);
    if (res.success) {
      await initUsers();
      if (userSel) userSel.value = newUser;
      await loadDatasetsForUser(newUser);
      showProcessResult(`用户 "${newUser}" 创建成功`, true);
    } else {
      showProcessResult(res.message || '创建用户失败', false);
    }
  } catch (err) {
    showProcessResult(`创建用户失败：${err.message}`, false);
  }
}

async function handleNewDataset() {
  const username = userSel ? userSel.value : '';
  if (!username) {
    showProcessResult('请先选择用户', false);
    return;
  }
  
  const newDs = prompt('请输入新数据集名称：\n注意：不能包含 % 号');
  if (!newDs) return;
  
  if (newDs.includes('%')) {
    showProcessResult('数据集名称不能包含 % 号', false);
    return;
  }
  
  try {
    const res = await createDataset(username, newDs);
    if (res.success) {
      await loadDatasetsForUser(username);
      if (dsSel) dsSel.value = newDs;
      await displayDataset(username, newDs);
      showProcessResult(`数据集 "${newDs}" 创建成功`, true);
    } else {
      showProcessResult(res.message || '创建数据集失败', false);
    }
  } catch (err) {
    showProcessResult(`创建数据集失败：${err.message}`, false);
  }
}

async function handleDeleteDataset() {
  const username = userSel ? userSel.value : '';
  const dataset = dsSel ? dsSel.value : '';
  
  if (!username || !dataset) {
    showProcessResult('请先选择要删除的数据集', false);
    return;
  }
  
  if (!confirm(`确定要删除数据集 "${dataset}" 吗？此操作将删除该数据集中的所有文件，且不可恢复！`)) {
    return;
  }
  
  try {
    const res = await deleteDataset(username, dataset);
    
    if (res.success) {
      await loadDatasetsForUser(username);
      showProcessResult(`数据集 "${dataset}" 已删除`, false);
    } else {
      showProcessResult(res.message || '删除数据集失败', false);
    }
  } catch (err) {
    showProcessResult(`删除数据集失败：${err.message}`, false);
  }
}

async function handleProcessDataset() {
  const username = userSel ? userSel.value : '';
  const dataset = dsSel ? dsSel.value : '';
  
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
    if (btnProcess) {
      btnProcess.disabled = true;
      btnProcess.textContent = '处理中...';
    }
    
    const result = await processDataset(username, dataset);
    
    if (result.success) {
      const successMsg = `成功处理 ${result.processed} 个文件`;
      const errorMsg = result.errors > 0 ? `，${result.errors} 个文件处理失败` : '';
      showProcessResult(successMsg + errorMsg, true);
      
      // 执行拟合成功后存储当前用户
      if (window.storageManager && window.storageManager.saveCurrentUser) {
        window.storageManager.saveCurrentUser(username);
      }
      
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
    if (btnProcess) {
      btnProcess.textContent = '执行拟合';
    }
  }
}

// 在页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
  // 延迟初始化，确保DOM完全加载
  setTimeout(() => {
    if (document.getElementById('username')) {
      initDatasetManager();
    }
  }, 100);
});

// 暴露给全局使用
window.datasetManager = {
  initUsers,
  loadDatasetsForUser,
  displayDataset,
  getCurrentUser: function() {
    return userSel ? userSel.value : '';
  },
  getCurrentDataset: function() {
    return dsSel ? dsSel.value : '';
  },
  getDatasetSummaryTables: function() {
    return datasetSummaryTables;
  },
  getFileCounts: function() {
    return {
      inputCount: currentInputFileCount,
      resultCount: currentResultFileCount
    };
  },
  updateFileCounts
};