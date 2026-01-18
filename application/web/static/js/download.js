// static/js/download.js
/**
 * 下载功能模块 - 处理图片打包下载
 */

// DOM元素
let btnDownloadAll;

/**
 * 初始化下载模块
 */
function initDownloadModule(options = {}) {
  btnDownloadAll = options.btnDownloadAll || document.getElementById('btnDownloadAll');
  
  if (btnDownloadAll) {
    console.log('初始化下载模块，绑定下载按钮事件');
    btnDownloadAll.addEventListener('click', handleDownloadAllImages);
  }
}

/**
 * 更新下载按钮状态
 */
function updateDownloadButtonState() {
  if (!btnDownloadAll) {
    console.warn('下载按钮元素未找到');
    return;
  }
  
  // 从全局datasetManager获取数据
  if (!window.datasetManager || !window.datasetManager.getDatasetSummaryTables) {
    btnDownloadAll.disabled = true;
    return;
  }
  
  const datasetSummaryTables = window.datasetManager.getDatasetSummaryTables();
  const currentDataset = window.datasetManager.getCurrentDataset ? window.datasetManager.getCurrentDataset() : '';
  
  if (!currentDataset) {
    btnDownloadAll.disabled = true;
    return;
  }
  
  const datasetData = datasetSummaryTables[currentDataset];
  const hasImages = datasetData && datasetData.files && datasetData.files.length > 0;
  
  btnDownloadAll.disabled = !hasImages;
}

/**
 * 处理下载所有图片
 */
async function handleDownloadAllImages() {
  console.log('开始下载所有图片');
  
  if (!window.datasetManager || !window.datasetManager.getDatasetSummaryTables || !window.datasetManager.getCurrentDataset) {
    showBackendMessage('下载功能初始化失败', 'error');
    return;
  }
  
  const datasetSummaryTables = window.datasetManager.getDatasetSummaryTables();
  const currentDataset = window.datasetManager.getCurrentDataset();
  
  if (!currentDataset) {
    showBackendMessage('请先选择数据集', 'warning');
    return;
  }
  
  try {
    const datasetData = datasetSummaryTables[currentDataset];
    if (!datasetData || !datasetData.files || datasetData.files.length === 0) {
      showBackendMessage('该数据集中没有图片可下载', 'warning');
      return;
    }
    
    const imageUrls = datasetData.files;
    
    // 显示下载进度
    showBackendMessage(`正在准备下载 ${imageUrls.length} 个图片...`, 'info');
    
    // 检查JSZip是否可用
    if (typeof JSZip === 'undefined') {
      // 如果JSZip未加载，使用逐个下载的方式
      console.warn('JSZip未加载，使用逐个下载方式');
      downloadImagesOneByOne(imageUrls, currentDataset);
      return;
    }
    
    // 使用JSZip打包下载
    await downloadImagesAsZip(imageUrls, currentDataset);
    
  } catch (err) {
    console.error('下载图片失败:', err);
    showBackendMessage(`下载失败：${err.message}`, 'error');
  }
}

/**
 * 逐个下载图片（兼容方案）
 */
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

/**
 * 使用JSZip打包下载（推荐方式）
 */
async function downloadImagesAsZip(imageUrls, datasetName) {
  try {
    if (btnDownloadAll) {
      btnDownloadAll.disabled = true;
      btnDownloadAll.textContent = '打包中...';
    }
    
    showBackendMessage('正在打包图片，请稍候...', 'info');
    
    const zip = new JSZip();
    const folder = zip.folder(datasetName);
    
    // 获取summary table图片（如果有）
    const datasetSummaryTables = window.datasetManager.getDatasetSummaryTables();
    const datasetData = datasetSummaryTables[datasetName];
    const summaryUrl = datasetData?.summary_table;
    
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

/**
 * 获取图片Blob
 */
async function fetchBlob(url) {
  const cleanUrl = url.split('?')[0]; // 去掉缓存参数
  const response = await fetch(cleanUrl);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return await response.blob();
}

// 暴露给全局使用
window.downloadManager = {
  initDownloadModule,
  updateDownloadButtonState
};

// 在页面加载完成后初始化下载模块
document.addEventListener('DOMContentLoaded', function() {
  setTimeout(() => {
    const btnDownloadAll = document.getElementById('btnDownloadAll');
    if (btnDownloadAll) {
      initDownloadModule({ btnDownloadAll });
    }
  }, 1500);
});