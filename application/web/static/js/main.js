// static/js/main.js
/**
 * 主入口文件 - 初始化所有模块并协调工作
 */

// 页面加载完成后初始化应用
document.addEventListener('DOMContentLoaded', function() {
  console.log('IV数据简易处理平台初始化...');
  
  // 延迟初始化，确保所有DOM元素和模块都已加载
  setTimeout(() => {
    // 检查关键模块是否已加载
    console.log('模块检查:', {
      datasetManager: !!window.datasetManager,
      uploadManager: !!window.uploadManager,
      downloadManager: !!window.downloadManager,
      setupImageClickEvents: !!window.setupImageClickEvents
    });
    
    // 设置图片点击事件
    if (window.setupImageClickEvents) {
      window.setupImageClickEvents();
    }
    
    // 初始化下载模块（如果尚未初始化）
    if (window.downloadManager && window.downloadManager.initDownloadModule) {
      const btnDownloadAll = document.getElementById('btnDownloadAll');
      if (btnDownloadAll) {
        window.downloadManager.initDownloadModule({ btnDownloadAll });
      }
    }
    
    console.log('应用初始化完成');
    
    // 显示加载完成消息
    if (window.showBackendMessage) {
      window.showBackendMessage('应用已加载完成', 'success');
      
      // 延迟隐藏欢迎消息
      setTimeout(() => {
        if (window.hideBackendMessage) {
          window.hideBackendMessage();
        }
      }, 3000);
    }
  }, 1000);
});