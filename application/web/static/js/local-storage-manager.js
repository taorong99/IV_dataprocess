// static/js/local-storage-manager.js
/**
 * localStorage管理模块 - 处理用户偏好的存储和读取
 */

const STORAGE_KEY = 'last_valid_username';
var DEFAULT_USER = '默认用户';

/**
 * 保存当前用户到localStorage
 * @param {string} username - 要保存的用户名
 */
function saveCurrentUser(username) {
  if (!username || typeof username !== 'string' || username.trim() === '') {
    console.warn('saveCurrentUser: 无效的用户名', username);
    return false;
  }
  
  const cleanUsername = username.trim();
  
  try {
    // 只存储纯字符串，不存储JSON对象
    localStorage.setItem(STORAGE_KEY, cleanUsername);
    console.log(`✅ 用户偏好已保存: "${cleanUsername}"`);
    return true;
  } catch (error) {
    console.error('❌ 保存用户偏好失败:', error);
    
    // 可能是存储空间不足，尝试清理旧数据
    if (error.name === 'QuotaExceededError') {
      console.warn('存储空间不足，尝试清理...');
      try {
        localStorage.removeItem(STORAGE_KEY);
        localStorage.setItem(STORAGE_KEY, cleanUsername);
        console.log('✅ 清理后保存成功');
        return true;
      } catch (e2) {
        console.error('❌ 清理后仍然保存失败');
        return false;
      }
    }
    return false;
  }
}

/**
 * 从localStorage读取存储的用户名
 * @returns {string|null} 存储的用户名，如果没有则返回null
 */
function getStoredUser() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? stored.trim() : null;
  } catch (error) {
    console.error('读取localStorage失败:', error);
    return null;
  }
}

/**
 * 验证并获取有效的用户名
 * @param {Array} availableUsers - 可用的用户列表
 * @returns {string} 应该加载的用户名
 */
function getValidUserToLoad(availableUsers) {
  if (!Array.isArray(availableUsers)) {
    console.warn('getValidUserToLoad: 无效的用户列表');
    return DEFAULT_USER;
  }
  
  // 确保默认用户存在
  const defaultUserExists = availableUsers.includes(DEFAULT_USER);
  if (!defaultUserExists && availableUsers.length > 0) {
    // 如果没有默认用户，使用第一个用户
    console.log('默认用户不存在，使用第一个用户');
    return availableUsers[0];
  }
  
  // 尝试从存储中读取
  const storedUser = getStoredUser();
  
  if (!storedUser) {
    // 没有存储记录
    console.log('无本地存储记录，使用默认用户');
    return DEFAULT_USER;
  }
  
  // 验证存储的用户是否存在
  const userExists = availableUsers.includes(storedUser);
  
  if (userExists) {
    // 用户有效
    console.log(`✅ 从本地存储加载用户: "${storedUser}"`);
    return storedUser;
  } else {
    // 用户无效（可能被删除）
    console.warn(`❌ 存储的用户"${storedUser}"已不存在，清理存储`);
    clearStoredUser();
    return DEFAULT_USER;
  }
}

/**
 * 清除存储的用户名
 */
function clearStoredUser() {
  try {
    localStorage.removeItem(STORAGE_KEY);
    console.log('✅ 已清除本地存储的用户偏好');
  } catch (error) {
    console.error('清除存储失败:', error);
  }
}

/**
 * 检查localStorage是否可用
 * @returns {boolean} 是否可用
 */
function isLocalStorageAvailable() {
  try {
    const testKey = '__test__';
    localStorage.setItem(testKey, testKey);
    localStorage.removeItem(testKey);
    return true;
  } catch (error) {
    return false;
  }
}

// 暴露给全局使用
window.storageManager = {
  saveCurrentUser,
  getStoredUser,
  getValidUserToLoad,
  clearStoredUser,
  isLocalStorageAvailable,
  STORAGE_KEY,
  DEFAULT_USER
};

// 初始化检查
if (!isLocalStorageAvailable()) {
  console.warn('⚠️ localStorage不可用，用户偏好记忆功能将不可用');
}

// 在页面加载时输出存储状态（调试用）
document.addEventListener('DOMContentLoaded', function() {
  setTimeout(() => {
    const stored = getStoredUser();
    console.log('当前存储状态:', { 
      localStorage可用: isLocalStorageAvailable(),
      存储的用户: stored,
      存储键: STORAGE_KEY 
    });
  }, 500);
});