// static/js/image-viewer.js
/**
 * 图片查看器模块 - 处理图片预览、放大、下载
 */

// 当前打开的模态框实例
let currentModal = null;

/**
 * 在模态框中显示图片
 */
function showImageInModal(imageUrl, imageTitle = '图片预览') {
  const modalImage = document.getElementById('modalImage');
  const modalTitle = document.getElementById('modalTitle');
  const modalElement = document.getElementById('imageModal');
  
  if (!modalImage || !modalTitle || !modalElement) {
    console.error('图片预览模态框元素未找到');
    return;
  }
  
  // 设置图片和标题
  modalImage.src = imageUrl;
  modalTitle.textContent = imageTitle;
  
  // 确保之前的模态框已关闭
  if (currentModal) {
    try {
      currentModal.hide();
    } catch (e) {
      console.warn('关闭之前的模态框时出错:', e);
    }
  }
  
  // 显示模态框
  if (typeof bootstrap !== 'undefined') {
    try {
      currentModal = new bootstrap.Modal(modalElement, {
        backdrop: true,
        keyboard: true,
        focus: true
      });
      currentModal.show();
      
      // 监听关闭事件，清理资源
      modalElement.addEventListener('hidden.bs.modal', function() {
        cleanupModal();
      });
    } catch (e) {
      console.error('显示模态框失败:', e);
      // 回退方案：直接显示模态框
      modalElement.classList.add('show');
      modalElement.style.display = 'block';
      document.body.classList.add('modal-open');
      document.body.style.overflow = 'hidden';
    }
  } else {
    console.error('Bootstrap未加载');
    // 回退方案
    modalElement.classList.add('show');
    modalElement.style.display = 'block';
    document.body.classList.add('modal-open');
    document.body.style.overflow = 'hidden';
  }
}

/**
 * 清理模态框资源
 */
function cleanupModal() {
  // 清理图片资源
  const modalImage = document.getElementById('modalImage');
  if (modalImage) {
    modalImage.src = '';
  }
  
  // 清理模态框实例
  currentModal = null;
  
  // 确保遮罩层被移除
  setTimeout(function() {
    const backdrops = document.querySelectorAll('.modal-backdrop');
    backdrops.forEach(function(backdrop) {
      if (backdrop.parentNode) {
        backdrop.parentNode.removeChild(backdrop);
      }
    });
    
    // 确保body样式恢复
    document.body.classList.remove('modal-open');
    document.body.style.overflow = '';
    document.body.style.paddingRight = '';
  }, 100);
}

/**
 * 关闭所有模态框
 */
function closeAllModals() {
  // 关闭图片模态框
  const imageModal = document.getElementById('imageModal');
  if (imageModal && imageModal.classList.contains('show')) {
    if (currentModal) {
      currentModal.hide();
    } else if (typeof bootstrap !== 'undefined') {
      const modal = bootstrap.Modal.getInstance(imageModal);
      if (modal) {
        modal.hide();
      }
    }
  }
  
  // 关闭上传进度模态框
  const uploadModal = document.getElementById('uploadProgressModal');
  if (uploadModal && uploadModal.classList.contains('show')) {
    if (typeof bootstrap !== 'undefined') {
      const modal = bootstrap.Modal.getInstance(uploadModal);
      if (modal) {
        modal.hide();
      }
    }
  }
  
  // 强制清理
  cleanupModal();
}

/**
 * 下载模态框中的图片
 */
function downloadModalImage() {
  const modalImage = document.getElementById('modalImage');
  if (!modalImage || !modalImage.src) {
    console.warn('没有图片可下载');
    return;
  }
  
  const imageUrl = modalImage.src.split('?')[0]; // 去掉查询参数
  const fileName = imageUrl.split('/').pop().split('?')[0] || 'image.png';
  
  const link = document.createElement('a');
  link.href = imageUrl;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

/**
 * 设置图片点击事件
 */
function setupImageClickEvents() {
  console.log('设置图片点击事件');
  
  // 主图点击放大
  const plotImg = document.getElementById('plot');
  if (plotImg) {
    plotImg.style.cursor = 'zoom-in';
    plotImg.addEventListener('click', function() {
      if (plotImg.src && plotImg.src !== '') {
        const fileName = plotImg.src.split('/').pop().split('?')[0];
        showImageInModal(plotImg.src, fileName);
      }
    });
  }
  
  // 参数总结表点击放大
  const summaryImg = document.getElementById('summaryTable');
  if (summaryImg) {
    summaryImg.style.cursor = 'zoom-in';
    summaryImg.addEventListener('click', function() {
      if (summaryImg.src && summaryImg.src !== '') {
        const fileName = summaryImg.src.split('/').pop().split('?')[0];
        showImageInModal(summaryImg.src, fileName);
      }
    });
  }
  
  // 缩略图点击放大（事件委托）
  document.addEventListener('click', function(e) {
    if (e.target.classList.contains('thumb')) {
      e.preventDefault();
      e.stopPropagation();
      
      // 获取对应的原图URL（去掉缩略图的查询参数，使用原始图片）
      const thumbSrc = e.target.src;
      const originalSrc = thumbSrc.split('?')[0]; // 去掉防缓存参数
      const fileName = e.target.alt || 'image.png';
      
      showImageInModal(originalSrc, fileName);
    }
  });
  
  // 添加ESC键关闭模态框功能
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' || e.key === 'Esc') {
      closeAllModals();
    }
  });
  
  // 点击遮罩层关闭模态框
  document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal-backdrop')) {
      closeAllModals();
    }
  });
}

/**
 * 动态添加的图片设置点击事件
 */
function setupDynamicImageClick(imgElement) {
  if (!imgElement) return;
  
  if (imgElement.id === 'plot' || imgElement.id === 'summaryTable') {
    imgElement.style.cursor = 'zoom-in';
    imgElement.addEventListener('click', function() {
      if (imgElement.src && imgElement.src !== '') {
        const fileName = imgElement.src.split('/').pop().split('?')[0];
        showImageInModal(imgElement.src, fileName);
      }
    });
  }
}

// 暴露给全局使用
window.showImageInModal = showImageInModal;
window.downloadModalImage = downloadModalImage;
window.setupImageClickEvents = setupImageClickEvents;
window.setupDynamicImageClick = setupDynamicImageClick;
window.closeAllModals = closeAllModals;
window.cleanupModal = cleanupModal;

// 在页面加载完成后设置图片点击事件
document.addEventListener('DOMContentLoaded', function() {
  setTimeout(() => {
    setupImageClickEvents();
  }, 1000);
});