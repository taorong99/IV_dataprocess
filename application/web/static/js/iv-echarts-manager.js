// static/js/iv-echarts-manager.js
/**
 * IV ECharts 图表渲染管理器
 * 负责解析后端的压缩数据并交由ECharts绘制交互图。
 */

let currentChartInstance = null;

/**
 * 转换量化单位到浮点数 (返回 mV/nA 等实际坐标显示需要的数值，建议显示为 mV 和 uA 等)
 * 实际上，ECharts渲染建议直接使用科学计数法或适合的缩放。
 * 为了配合后续使用和显示，这里统一缩放到更易读的数值如：X轴 mV, Y轴 μA，或统一还原为 V / A。
 * 为了减少精度丢失并结合实际超导数据规模，我们将其还原为 SI 基础单位 (V, A) 用于内部存储，
 * 在 formatter 中使用合适的单位。
 */
function createSeriesData(xIntArray, yIntArray) {
    if (!xIntArray || !yIntArray || xIntArray.length !== yIntArray.length) return [];
    
    const data = [];
    for (let i = 0; i < xIntArray.length; i++) {
        data.push([
            xIntArray[i], // 原样保留，单位见 axis_unit
            yIntArray[i]
        ]);
    }
    return data;
}

/**
 * 恢复图表容器到正常非全屏形态
 */
function resetContainerFullScreen(dom) {
    if (!dom) return;
    if (dom.getAttribute('data-is-full') === '1') {
        dom.setAttribute('data-is-full', '0');
        const placeholder = document.getElementById('echarts-placeholder');
        if (placeholder && placeholder.parentNode) {
            placeholder.parentNode.insertBefore(dom, placeholder);
            placeholder.remove();
        }
        dom.style.cssText = dom.getAttribute('data-orig-style') || '';
    }
}

/**
 * 销毁当前图表实例
 */
function disposeCurrentChart() {
    if (currentChartInstance) {
        currentChartInstance.dispose();
        currentChartInstance = null;
    }
}

/**
 * 获取数值显示的合理精度
 */
function getDecimalPrecisionFloat(unit) {
    if (unit === 'V' || unit === 'A') return 8;
    if (unit === 'mV' || unit === 'mA') return 5;
    if (unit === 'uV' || unit === 'uA') return 2;
    if (unit === 'nV' || unit === 'nA') return 0;
    return 3;
}

/**
 * 通用状态栏更新逻辑
 */
function updateStatusBar(params, chartDom, unitConf) {
    const statusDiv = document.getElementById('echarts-status-bar');
    if (!statusDiv) return;
    
    if (params && params.data) {
        const vPrec = getDecimalPrecisionFloat(unitConf.x_v_unit);
        const iPrec = getDecimalPrecisionFloat(unitConf.y_i_unit);
        statusDiv.innerHTML = `V = ${params.data[0].toFixed(vPrec)} ${unitConf.x_v_unit} &nbsp;&nbsp;|&nbsp;&nbsp; I = ${params.data[1].toFixed(iPrec)} ${unitConf.y_i_unit}`;
    } else {
        statusDiv.innerHTML = '移动鼠标查看数据点坐标';
    }
}

/**
 * 渲染 IV 曲线图
 * @param {HTMLElement} container 容器DOM元素
 * @param {Object} jsonData 包含 schema_version 和 chart.iv 的数据包
 */
function renderIVChart(container, jsonData) {
    resetContainerFullScreen(container);
    disposeCurrentChart();
    
    const ivData = jsonData.chart?.iv;
    const unitConf = jsonData.axis_unit || { x_v_unit: 'nV', y_i_unit: 'nA' };
    
    if (!ivData || !ivData.x_v || !ivData.y_i) {
        container.innerHTML = '<div class="empty-message">无法解析IV图表数据, 请重新拟合</div>';
        return;
    }

    // 提取并转换实测数据
    const rawSeries = createSeriesData(ivData.x_v, ivData.y_i);
    const aux = ivData.aux || {};
    
    // 计算原始数据的范围，用作坐标轴的固定极值边界（裁切拟合线的越界部分，外扩20%）
    let xMin = Number.POSITIVE_INFINITY;
    let xMax = Number.NEGATIVE_INFINITY;
    let yMin = Number.POSITIVE_INFINITY;
    let yMax = Number.NEGATIVE_INFINITY;
    for (let i = 0; i < rawSeries.length; i++) {
        const x = rawSeries[i][0];
        const y = rawSeries[i][1];
        if (x < xMin) xMin = x;
        if (x > xMax) xMax = x;
        if (y < yMin) yMin = y;
        if (y > yMax) yMax = y;
    }
    
    // V和I独立取自身绝对值的20%进行冗余，且向下/上取整为10的整数倍以包裹数据
    const vMinNew = xMin - Math.abs(xMin) * 0.2;
    const vMaxNew = xMax + Math.abs(xMax) * 0.2;
    const iMinNew = yMin - Math.abs(yMin) * 0.2;
    const iMaxNew = yMax + Math.abs(yMax) * 0.2;

    const xAxisMinLimit = Math.floor(vMinNew / 10) * 10;
    const xAxisMaxLimit = Math.ceil(vMaxNew / 10) * 10;
    const yAxisMinLimit = Math.floor(iMinNew / 10) * 10;
    const yAxisMaxLimit = Math.ceil(iMaxNew / 10) * 10;
    
    // 初始化 ECharts
    currentChartInstance = echarts.init(container);
    
    // 配置坐标系与系列
    const option = {
        title: {
            text: jsonData.file || 'IV Curve',
            left: 'center',
            textStyle: { fontSize: 14 }
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'line',
                axis: 'y',
                lineStyle: { type: 'dashed' }
            },
            formatter: function (params) {
                const iPrec = getDecimalPrecisionFloat(unitConf.y_i_unit);
                const vPrec = getDecimalPrecisionFloat(unitConf.x_v_unit);
                let html = `I = ${Number(params[0].axisValue).toFixed(iPrec)} ${unitConf.y_i_unit}<br/>`;
                params.forEach(p => {
                    if (p.seriesName === 'Raw Data') {
                        html += `${p.marker} V = ${Number(p.data[0]).toFixed(vPrec)} ${unitConf.x_v_unit}<br/>`;
                    }
                });
                return html;
            }
        },
        toolbox: {
            feature: {
                myFullScreen: {
                    show: true,
                    title: '下置放大图 (全屏/还原)',
                    icon: 'path://M15 3h6v6h-2V5.4l-6.2 6.2-1.4-1.4L17.6 4H15V3zM9 3v2H5.4l6.2 6.2-1.4 1.4L4 6.4V9H2V3h7zm3.8 13.4l6.2-6.2 1.4 1.4-6.2 6.2H19v2h-7v-7h2v3.6zm-10.4-1.4L8.6 8.8l1.4 1.4-6.2 6.2H6v2H-1v-7h2v3.6z',
                    onclick: function () {
                        const dom = container;
                        if (dom.getAttribute('data-is-full') === '1') {
                            dom.setAttribute('data-is-full', '0');
                            const placeholder = document.getElementById('echarts-placeholder');
                            if (placeholder) {
                                placeholder.parentNode.insertBefore(dom, placeholder);
                                placeholder.remove();
                            }
                            dom.style.cssText = dom.getAttribute('data-orig-style') || '';
                        } else {
                            dom.setAttribute('data-is-full', '1');
                            dom.setAttribute('data-orig-style', dom.style.cssText);
                            const placeholder = document.createElement('div');
                            placeholder.id = 'echarts-placeholder';
                            placeholder.style.width = dom.offsetWidth + 'px';
                            placeholder.style.height = dom.offsetHeight + 'px';
                            dom.parentNode.insertBefore(placeholder, dom);
                            dom.style.cssText = 'position:fixed;top:5vh;left:5vw;width:90vw;height:90vh;z-index:99999;background:#fff;border:1px solid #ccc;box-shadow:0 0 20px rgba(0,0,0,0.5);border-radius:8px;padding:20px;box-sizing:border-box;';
                            document.body.appendChild(dom);
                        }
                        if (currentChartInstance) setTimeout(() => currentChartInstance.resize(), 100);
                    }
                },
                dataZoom: {
                    filterMode: 'none',
                    yAxisIndex: 'all',
                    xAxisIndex: 'all'
                },
                restore: {},
                saveAsImage: {}
            }
        },
        dataZoom: [
            { type: 'inside', xAxisIndex: 0, filterMode: 'none' },
            { type: 'inside', yAxisIndex: 0, filterMode: 'none' }
        ],
        grid: {
            left: 80,
            right: 80,
            bottom: 70,
            top: 60,
            containLabel: false
        },
        xAxis: {
            name: `Voltage (${unitConf.x_v_unit})`,
            nameLocation: 'middle',
            nameGap: 30,
            type: 'value',
            scale: true,
            min: xAxisMinLimit,
            max: xAxisMaxLimit,
            splitLine: { show: false }
        },
        yAxis: {
            name: `Current (${unitConf.y_i_unit})`,
            nameLocation: 'middle',
            nameGap: 50,
            nameTextStyle: { padding: [0, 0, 10, 0] },
            type: 'value',
            scale: true,
            min: yAxisMinLimit,
            max: yAxisMaxLimit,
            splitLine: { show: true, lineStyle: { type: 'dashed' } }
        },
        series: [
            {
                name: 'Raw Data',
                type: 'scatter',
                symbolSize: 4,
                data: rawSeries,
                itemStyle: { color: '#0d6efd' },
                large: true, // 开启大数据量优化
                emphasis: {
                    focus: 'series',
                    itemStyle: { color: '#ff7f50', borderColor: '#fff', borderWidth: 1 },
                    symbolSize: 10
                }
            }
        ]
    };

    // 提取并转换拟合数据线
    // 提取并转换拟合数据线
    if (ivData.fit_pos && ivData.fit_pos.x_v) {
        let fitPosSeries = createSeriesData(ivData.fit_pos.x_v, ivData.fit_pos.y_i);
        fitPosSeries.sort((a, b) => a[0] - b[0]);
        // 找到在初始可视区域内的点，用于锚定标签
        let validPosPoints = fitPosSeries.filter(p => p[0] >= xAxisMinLimit && p[0] <= xAxisMaxLimit && p[1] >= yAxisMinLimit && p[1] <= yAxisMaxLimit);
        let posLabelPoint = validPosPoints.length > 0 ? validPosPoints[validPosPoints.length - 1] : fitPosSeries[fitPosSeries.length - 1];

        const rPosLabel = aux.r_pos ? `R=${Number(aux.r_pos).toPrecision(5)}Ω` : '';
        option.series.push({
            name: 'Fit Pos',
            type: 'line',
            showSymbol: false,
            data: fitPosSeries,
            lineStyle: { color: '#dc3545', width: 2, type: 'dashed' },
            clip: true,
            markPoint: rPosLabel ? {
                symbol: 'circle',
                symbolSize: 0, // 隐藏标记点本身，只显示标签
                data: [
                    {
                        coord: posLabelPoint,
                        label: {
                            show: true,
                            formatter: rPosLabel,
                            color: '#dc3545',
                            position: 'left',
                            offset: [0, -10]
                        }
                    }
                ]
            } : null
        });
    }

    if (ivData.fit_neg && ivData.fit_neg.x_v) {
        let fitNegSeries = createSeriesData(ivData.fit_neg.x_v, ivData.fit_neg.y_i);
        fitNegSeries.sort((a, b) => a[0] - b[0]);
        // 找到在初始可视区域内的点，用于锚定负向标签（通常是左下角的起点区域）
        let validNegPoints = fitNegSeries.filter(p => p[0] >= xAxisMinLimit && p[0] <= xAxisMaxLimit && p[1] >= yAxisMinLimit && p[1] <= yAxisMaxLimit);
        let negLabelPoint = validNegPoints.length > 0 ? validNegPoints[0] : fitNegSeries[0];
        
        const rNegLabel = aux.r_neg ? `R=${Number(aux.r_neg).toPrecision(5)}Ω` : '';
        option.series.push({
            name: 'Fit Neg',
            type: 'line',
            showSymbol: false,
            data: fitNegSeries,
            lineStyle: { color: '#198754', width: 2, type: 'dashed' },
            clip: true,
            markPoint: rNegLabel ? {
                symbol: 'circle',
                symbolSize: 0,
                data: [
                    {
                        coord: negLabelPoint,
                        label: {
                            show: true,
                            formatter: rNegLabel,
                            color: '#198754',
                            position: 'right',
                            offset: [0, 10]
                        }
                    }
                ]
            } : null
        });
    }

    // 辅助线 (Ic)
    // 纵轴单位由于直接使用了 json 原始数据，辅助线的截距也即原来的整型值就是对应的原始数据。
    // json 中的 aux.ic_pos 被存在 json 时是被转为 int 的（通常与目标坐标系同单位）。
    const formatUa = (val, unit) => {
        let num = Number(val);
        if (unit === 'A') num *= 1e6;
        else if (unit === 'mA') num *= 1000;
        else if (unit === 'nA') num /= 1000;
        else if (unit === 'pA') num /= 1e6;
        return num.toFixed(1) + ' μA';
    };

    const markLines = [];
    if (aux.ic_pos != null) {
        markLines.push({ yAxis: aux.ic_pos, label: { position: 'insideEndBottom', formatter: `Ic+: ${formatUa(aux.ic_pos, unitConf.y_i_unit)}` }, lineStyle: { color: '#ffb703', type: 'dashed' } });
    }
    if (aux.ic_neg != null) {
        markLines.push({ yAxis: aux.ic_neg, label: { position: 'insideEndTop', formatter: `Ic-: ${formatUa(aux.ic_neg, unitConf.y_i_unit)}` }, lineStyle: { color: '#ffb703', type: 'dashed' } });
    }
    
    if (markLines.length > 0) {
        option.series[0].markLine = {
            symbol: ['none', 'none'],
            data: markLines
        };
    }

    currentChartInstance.setOption(option);

    // 绑定鼠标事件更新状态栏
    appendStatusBar(container);
    currentChartInstance.on('highlight', function(params) {
       // 空实现，可以在此处提取高亮点的坐标更新底部栏，使用 mousemove 更全
    });

    currentChartInstance.getZr().on('mousemove', function (params) {
        const pointInPixel = [params.offsetX, params.offsetY];
        if (currentChartInstance.containPixel('grid', pointInPixel)) {
            const pointInGrid = currentChartInstance.convertFromPixel('grid', pointInPixel);
            const statusDiv = document.getElementById('echarts-status-bar');
            if (statusDiv) {
                const vPrec = getDecimalPrecisionFloat(unitConf.x_v_unit);
                const iPrec = getDecimalPrecisionFloat(unitConf.y_i_unit);
                statusDiv.innerHTML = `V = ${pointInGrid[0].toFixed(vPrec)} ${unitConf.x_v_unit} &nbsp;&nbsp;|&nbsp;&nbsp; I = ${pointInGrid[1].toFixed(iPrec)} ${unitConf.y_i_unit}`;
            }
        }
    });

    window.addEventListener('resize', () => currentChartInstance.resize());
}

/**
 * 渲染 Ic Spread 柱状图
 */
function renderIcSpreadChart(container, jsonData) {
    resetContainerFullScreen(container);
    disposeCurrentChart();
    
    const spreadData = jsonData.chart?.ic_spread;
    const unitConf = jsonData.axis_unit || { x_v_unit: 'nV', y_i_unit: 'nA' };
    
    if (!spreadData || !spreadData.x_ic || !spreadData.y_count) {
        container.innerHTML = '<div class="empty-message">无法解析 Ic Spread 数据</div>';
        return;
    }
    
    // 构建柱状图数据，原样保留
    const xData = spreadData.x_ic;
    const yData = spreadData.y_count;
    
    currentChartInstance = echarts.init(container);

    const option = {
        title: {
            text: jsonData.file ? `${jsonData.file} - Ic Spread` : 'Ic Spread',
            left: 'center',
            textStyle: { fontSize: 14 }
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: `{b} ${unitConf.y_i_unit} : {c} 个`
        },
        toolbox: {
            feature: {
                myFullScreen: {
                    show: true,
                    title: '下置放大图 (全屏/还原)',
                    icon: 'path://M15 3h6v6h-2V5.4l-6.2 6.2-1.4-1.4L17.6 4H15V3zM9 3v2H5.4l6.2 6.2-1.4 1.4L4 6.4V9H2V3h7zm3.8 13.4l6.2-6.2 1.4 1.4-6.2 6.2H19v2h-7v-7h2v3.6zm-10.4-1.4L8.6 8.8l1.4 1.4-6.2 6.2H6v2H-1v-7h2v3.6z',
                    onclick: function () {
                        const dom = container;
                        if (dom.getAttribute('data-is-full') === '1') {
                            dom.setAttribute('data-is-full', '0');
                            const placeholder = document.getElementById('echarts-placeholder');
                            if (placeholder) {
                                placeholder.parentNode.insertBefore(dom, placeholder);
                                placeholder.remove();
                            }
                            dom.style.cssText = dom.getAttribute('data-orig-style') || '';
                        } else {
                            dom.setAttribute('data-is-full', '1');
                            dom.setAttribute('data-orig-style', dom.style.cssText);
                            const placeholder = document.createElement('div');
                            placeholder.id = 'echarts-placeholder';
                            placeholder.style.width = dom.offsetWidth + 'px';
                            placeholder.style.height = dom.offsetHeight + 'px';
                            dom.parentNode.insertBefore(placeholder, dom);
                            dom.style.cssText = 'position:fixed;top:5vh;left:5vw;width:90vw;height:90vh;z-index:99999;background:#fff;border:1px solid #ccc;box-shadow:0 0 20px rgba(0,0,0,0.5);border-radius:8px;padding:20px;box-sizing:border-box;';
                            document.body.appendChild(dom);
                        }
                        if (currentChartInstance) setTimeout(() => currentChartInstance.resize(), 100);
                    }
                },
                dataZoom: {},
                restore: {},
                saveAsImage: {}
            }
        },
        grid: {
            left: 80, right: 80, bottom: 70, top: 60, containLabel: false
        },
        dataZoom: [
            { type: 'inside' }
        ],
        xAxis: {
            type: 'category',
            name: `Ic (${unitConf.y_i_unit})`,
            nameLocation: 'middle',
            nameGap: 30,
            data: xData
        },
        yAxis: {
            type: 'value',
            name: 'Count'
        },
        series: [
            {
                name: 'Count',
                type: 'bar',
                data: yData,
                itemStyle: { color: '#20c997' }
            }
        ]
    };
    
    currentChartInstance.setOption(option);
    appendStatusBar(container);
    window.addEventListener('resize', () => currentChartInstance.resize());
}

/**
 * 为容器附加底部状态栏
 */
function appendStatusBar(container) {
    let statusDiv = document.getElementById('echarts-status-bar');
    if (!statusDiv) {
        statusDiv = document.createElement('div');
        statusDiv.id = 'echarts-status-bar';
        statusDiv.style.position = 'absolute';
        statusDiv.style.bottom = '5px';
        statusDiv.style.left = '10px';
        statusDiv.style.fontSize = '12px';
        statusDiv.style.color = '#666';
        statusDiv.style.background = 'rgba(255,255,255,0.8)';
        statusDiv.style.padding = '2px 5px';
        statusDiv.style.borderRadius = '3px';
        container.style.position = 'relative'; // 确保父容器是 relative
        container.appendChild(statusDiv);
    }
    statusDiv.innerHTML = '加载完成，移动鼠标查看数据坐标...';
}
