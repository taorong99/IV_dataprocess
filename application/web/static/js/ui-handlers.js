// static/js/ui-handlers.js
/**
 * UI 控制模块 - 负责 PNG/ECharts 双模式开关与全局设置
 */

// 默认图表模式
window.CHART_MODE = localStorage.getItem('preferredChartMode') || 'png';

document.addEventListener('DOMContentLoaded', () => {
  // 初始化开关状态
  const modePng = document.getElementById('modePng');
  const modeEcharts = document.getElementById('modeEcharts');
  
  if (modePng && modeEcharts) {
    if (window.CHART_MODE === 'echarts') {
      modeEcharts.checked = true;
    } else {
      modePng.checked = true;
    }
  }

  // 监听单选按钮的变化
  const modeRadios = document.querySelectorAll('input[name="chartMode"]');
  modeRadios.forEach(radio => {
    radio.addEventListener('change', (e) => {
      if (e.target.checked) {
        window.CHART_MODE = e.target.value;
        localStorage.setItem('preferredChartMode', window.CHART_MODE);
        console.log('图表模式已切换为:', window.CHART_MODE);
        
        // 模式切换时切换显示容器 (Commit-3 详细挂载逻辑会在后面增加)
        const plotImg = document.getElementById('plot');
        const ivChart = document.getElementById('ivChart');
        if (plotImg && ivChart) {
          if (window.CHART_MODE === 'echarts') {
            plotImg.style.display = 'none';
            ivChart.style.display = 'block';
          } else {
            plotImg.style.display = 'block';
            ivChart.style.display = 'none';
          }
        }
      }
    });
  });

  // 初次加载容器状态调整
  const plotImg = document.getElementById('plot');
  const ivChart = document.getElementById('ivChart');
  if (plotImg && ivChart) {
    if (window.CHART_MODE === 'echarts') {
      plotImg.style.display = 'none';
      ivChart.style.display = 'block';
    } else {
      plotImg.style.display = 'block';
      ivChart.style.display = 'none';
    }
  }
});
