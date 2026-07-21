/**
 * 运动分析 - Dashboard 监控脚本
 *
 * 职责:
 * - ECharts 实时传感器波形图
 * - Leaflet GPS 轨迹地图
 * - WebSocket 实时数据接收
 * - 步态参数计算与展示
 * - 历史会话管理
 */
(function () {
  'use strict';

  // ============================================================
  //  状态管理
  // ============================================================
  const state = {
    socket: null,
    currentSessionId: null,
    connected: false,
    demoMode: false,
    demoInterval: null,

    // 传感器波形缓冲 (保留最近10秒)
    displayWindow: 500,     // 显示500个点 (~10秒@50Hz)
    timestamps: [],
    accX: [], accY: [], accZ: [],
    gyroX: [], gyroY: [], gyroZ: [],

    // GPS 轨迹
    gpsTrack: [],
    mapInitialized: false,
    mapMarkers: [],

    // 推理历史
    inferences: [],
    currentLabel: '--',
    currentConfidence: 0,
    currentProbas: {},

    // 步态参数
    steps: 0,
    distance: 0,
    startTime: 0,
    duration: 0,
    cadence: 0,
    speed: 0,

    // 图表实例
    waveChart: null,
    showChannel: 'composite',
  };

  const $ = (sel) => document.querySelector(sel);

  // ============================================================
  //  WebSocket 连接
  // ============================================================
  function connect() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${location.host}`;

    state.socket = io(wsUrl, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: Infinity,
    });

    state.socket.on('connect', () => {
      state.connected = true;
      updateConnectionStatus(true);
      loadHistory();
    });

    state.socket.on('disconnect', () => {
      state.connected = false;
      updateConnectionStatus(false);
    });

    state.socket.on('dashboard:new_session', handleNewSession);
    state.socket.on('dashboard:session_ended', handleSessionEnd);
    state.socket.on('dashboard:sensor_stream', handleSensorStream);
    state.socket.on('dashboard:inference_result', handleInference);
    state.socket.on('dashboard:gait_params', handleGaitParams);
    state.socket.on('dashboard:history', handleHistory);
  }

  function updateConnectionStatus(connected) {
    const dot = $('#connDot');
    const text = $('#connText');
    if (connected) {
      dot.className = 'conn-dot connected';
      text.textContent = '已连接';
    } else {
      dot.className = 'conn-dot disconnected';
      text.textContent = '未连接';
    }
  }

  // ============================================================
  //  事件处理
  // ============================================================
  function handleNewSession(data) {
    state.currentSessionId = data.session_id;
    state.startTime = data.start_time || Date.now() / 1000;
    state.currentLabel = data.label || 'unknown';
    state.timestamps = [];
    state.accX = []; state.accY = []; state.accZ = [];
    state.gyroX = []; state.gyroY = []; state.gyroZ = [];
    state.gpsTrack = [];
    state.inferences = [];
    state.steps = 0;
    state.distance = 0;

    // 显示焦点区
    setFocusView(true);
    updateFocusCard(data.label, 0, {});
    $('#correctionPanel').classList.remove('hidden');
    updateCorrectionButtons();

    // 重置地图
    resetMap();
  }

  function handleSessionEnd(data) {
    if (data.session_id === state.currentSessionId) {
      setFocusView(false);
      loadHistory();
    }
  }

  function handleSensorStream(data) {
    if (data.session_id !== state.currentSessionId) return;

    const t = data.timestamp || Date.now() / 1000;
    state.timestamps.push(t);
    state.accX.push(data.acc_x || 0);
    state.accY.push(data.acc_y || 0);
    state.accZ.push(data.acc_z || 0);
    state.gyroX.push(data.gyro_x || 0);
    state.gyroY.push(data.gyro_y || 0);
    state.gyroZ.push(data.gyro_z || 0);

    // 限制缓冲区大小
    while (state.timestamps.length > state.displayWindow) {
      state.timestamps.shift();
      state.accX.shift(); state.accY.shift(); state.accZ.shift();
      state.gyroX.shift(); state.gyroY.shift(); state.gyroZ.shift();
    }

    // 更新 GPS (如果有的话)
    if (data.lat && data.lng) {
      updateGpsTrack(data.lat, data.lng);
    }

    // 更新图表 (节流)
    throttleUpdateChart();
  }

  function handleInference(data) {
    if (data.session_id !== state.currentSessionId) return;

    state.currentLabel = data.label;
    state.currentConfidence = data.confidence || 0;
    state.currentProbas = data.probas || {};
    state.inferences.push({
      timestamp: data.timestamp,
      label: data.label,
      confidence: data.confidence,
    });

    updateFocusCard(data.label, data.confidence, data.probas);
  }

  // ============================================================
  //  ECharts 波形图
  // ============================================================
  function initChart() {
    const container = $('#waveChart');
    if (!container) return;

    state.waveChart = echarts.init(container, 'dark');

    const option = {
      backgroundColor: 'transparent',
      grid: { left: 50, right: 15, top: 10, bottom: 30 },
      xAxis: {
        type: 'value',
        show: true,
        axisLine: { lineStyle: { color: '#30363d' } },
        axisLabel: { color: '#6e7681', fontSize: 10 },
        name: '时间 (s)',
        nameTextStyle: { color: '#6e7681', fontSize: 10 },
        min: 0, max: 10,
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: '#21262d' } },
        axisLabel: { color: '#6e7681', fontSize: 10 },
      },
      legend: {
        bottom: 0, textStyle: { color: '#8b949e', fontSize: 10 },
        data: ['加速度合成', '角速度合成'],
      },
      tooltip: { trigger: 'axis' },
      animation: false,
      series: [
        {
          name: '加速度合成',
          type: 'line',
          symbol: 'none',
          lineStyle: { color: '#58a6ff', width: 1.5 },
          data: [],
        },
        {
          name: '角速度合成',
          type: 'line',
          symbol: 'none',
          lineStyle: { color: '#a371f7', width: 1.5 },
          data: [],
        },
      ],
    };

    state.waveChart.setOption(option);
    window.addEventListener('resize', () => state.waveChart?.resize());
  }

  function updateChart() {
    if (!state.waveChart || state.timestamps.length < 2) return;

    const t0 = state.timestamps[0];
    const xData = state.timestamps.map((t) => parseFloat((t - t0).toFixed(2)));

    let seriesData;

    if (state.showChannel === 'composite') {
      // 合成量
      const accMag = state.accX.map((x, i) =>
        Math.sqrt(x*x + state.accY[i]*state.accY[i] + state.accZ[i]*state.accZ[i])
      );
      const gyroMag = state.gyroX.map((x, i) =>
        Math.sqrt(x*x + state.gyroY[i]*state.gyroY[i] + state.gyroZ[i]*state.gyroZ[i])
      );
      seriesData = [accMag, gyroMag];
      const names = ['加速度合成', '角速度合成'];
      state.waveChart.setOption({
        legend: { data: names },
        series: [
          { name: names[0], data: xData.map((t, i) => [t, seriesData[0][i]]) },
          { name: names[1], data: xData.map((t, i) => [t, seriesData[1][i]]) },
        ],
        xAxis: { min: 0, max: Math.max(xData[xData.length - 1], 10) },
      });
    } else if (state.showChannel === 'acc') {
      const names = ['Acc X', 'Acc Y', 'Acc Z'];
      state.waveChart.setOption({
        legend: { data: names },
        series: [
          { name: names[0], lineStyle: { color: '#f85149' }, data: xData.map((t, i) => [t, state.accX[i]]) },
          { name: names[1], lineStyle: { color: '#3fb950' }, data: xData.map((t, i) => [t, state.accY[i]]) },
          { name: names[2], lineStyle: { color: '#58a6ff' }, data: xData.map((t, i) => [t, state.accZ[i]]) },
        ],
        xAxis: { min: 0, max: Math.max(xData[xData.length - 1], 10) },
      });
    } else {
      const names = ['Gyro X', 'Gyro Y', 'Gyro Z'];
      state.waveChart.setOption({
        legend: { data: names },
        series: [
          { name: names[0], lineStyle: { color: '#d2991d' }, data: xData.map((t, i) => [t, state.gyroX[i]]) },
          { name: names[1], lineStyle: { color: '#a371f7' }, data: xData.map((t, i) => [t, state.gyroY[i]]) },
          { name: names[2], lineStyle: { color: '#58a6ff' }, data: xData.map((t, i) => [t, state.gyroZ[i]]) },
        ],
        xAxis: { min: 0, max: Math.max(xData[xData.length - 1], 10) },
      });
    }
  }

  let _chartThrottle = 0;
  function throttleUpdateChart() {
    const now = Date.now();
    if (now - _chartThrottle > 200) {
      _chartThrottle = now;
      updateChart();
    }
  }

  window.toggleChannel = function (channel, btn) {
    state.showChannel = channel;
    document.querySelectorAll('.toggle-btn').forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    updateChart();
  };

  // ============================================================
  //  Leaflet 地图
  // ============================================================
  function initMap() {
    if (state.mapInitialized) return;

    if (typeof L === 'undefined') {
      console.warn('Leaflet 尚未加载，跳过地图初始化');
      return;
    }

    const container = $('#trackMap');
    if (!container) return;

    state.mapInstance = L.map(container, {
      attributionControl: false,
      zoomControl: true,
    }).setView([31.23, 121.47], 16);

    // 使用高德瓦片（国内访问稳定，OpenStreetMap 瓦片常被墙）
    L.tileLayer('https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}', {
      subdomains: ['1', '2', '3', '4'],
      maxZoom: 18,
    }).addTo(state.mapInstance);

    state.mapTrackLine = L.polyline([], {
      color: '#58a6ff', weight: 3, opacity: 0.7,
    }).addTo(state.mapInstance);

    state.mapInitialized = true;

    // 延迟刷新尺寸
    setTimeout(() => state.mapInstance?.invalidateSize(), 300);
    window.addEventListener('resize', () => {
      setTimeout(() => state.mapInstance?.invalidateSize(), 100);
    });
  }

  function resetMap() {
    state.gpsTrack = [];
    if (state.mapTrackLine) {
      state.mapTrackLine.setLatLngs([]);
    }
  }

  function updateGpsTrack(lat, lng) {
    if (!state.mapInitialized) initMap();

    state.gpsTrack.push([lat, lng]);
    if (state.mapTrackLine) {
      state.mapTrackLine.setLatLngs(state.gpsTrack);
    }

    // 居中到最新位置
    if (state.mapInstance && state.gpsTrack.length > 0) {
      state.mapInstance.setView(
        state.gpsTrack[state.gpsTrack.length - 1],
        state.mapInstance.getZoom(),
        { animate: true }
      );
    }
  }

  // ============================================================
  //  焦点区更新
  // ============================================================
  function setFocusView(active) {
    const placeholder = $('#focusPlaceholder');
    const content = $('#focusContent');
    if (active) {
      placeholder?.classList.add('hidden');
      content?.classList.remove('hidden');
      $('#focusCard')?.classList.add('ready');
    } else {
      placeholder?.classList.remove('hidden');
      content?.classList.add('hidden');
      $('#focusCard')?.classList.remove('ready');
    }
  }

  function updateFocusCard(label, confidence, probas) {
    const icons = { static: '🧍', walking: '🚶', running: '🏃' };
    const names = { static: '静止', walking: '走路', running: '跑步' };

    const iconEl = $('#focusIcon');
    const labelEl = $('#focusLabel');
    const confEl = $('#focusConfidence');

    if (iconEl) iconEl.textContent = icons[label] || '❓';
    if (labelEl) labelEl.textContent = names[label] || label;
    if (confEl) confEl.textContent = confidence > 0
      ? `置信度 ${(confidence * 100).toFixed(1)}%`
      : '分析中...';

    // 渲染全部类别概率条
    renderProbBars(probas || {}, label);
  }

  /**
   * 渲染所有类别的概率条，高亮置信度最高的运动
   */
  function renderProbBars(probas, activeLabel) {
    const container = $('#probBars');
    if (!container) return;

    const allLabels = ['static', 'walking', 'running'];
    const icons = { static: '🧍', walking: '🚶', running: '🏃' };
    const names = { static: '静止', walking: '走路', running: '跑步' };

    let html = '';
    for (let i = 0; i < allLabels.length; i++) {
      const lb = allLabels[i];
      const p = probas[lb] || 0;
      const pct = (p * 100).toFixed(1);
      const barW = (p * 100).toFixed(0);
      const isTop = lb === activeLabel;
      html += `<div class="prob-row${isTop ? ' prob-top' : ''}">` +
        `<span class="prob-icon">${icons[lb] || '❓'}</span>` +
        `<span class="prob-name">${names[lb] || lb}</span>` +
        `<span class="prob-pct">${pct}%</span>` +
        `<div class="prob-bar-track">` +
          `<div class="prob-bar-fill" style="width:${barW}%"></div>` +
        `</div>` +
      `</div>`;
    }
    container.innerHTML = html;
  }

  function updateCorrectionButtons() {
    const container = $('#correctionBtns');
    if (!container) return;

    const labels = [
      { key: 'static', name: '🧍 静止' },
      { key: 'walking', name: '🚶 走路' },
      { key: 'running', name: '🏃 跑步' },
    ];

    container.innerHTML = labels.map((l) =>
      `<button class="correction-btn" onclick="correctLabel('${l.key}')">${l.name}</button>`
    ).join('');
  }

  window.correctLabel = function (label) {
    if (state.socket && state.socket.connected && state.currentSessionId) {
      state.socket.emit('dashboard:manual_correction', {
        session_id: state.currentSessionId,
        label: label,
      });
      updateFocusCard(label, 1.0, correctedProbas(label));

      // 短暂高亮反馈
      const card = $('#focusCard');
      if (card) {
        card.style.borderColor = '#58a6ff';
        setTimeout(() => { card.style.borderColor = ''; }, 500);
      }
    }
  };

  // ============================================================
  //  步态参数 — 由手机端通过 WebSocket 同步，保证两端数据一致
  // ============================================================
  function handleGaitParams(data) {
    if (data.session_id !== state.currentSessionId) return;

    // 静止时显示 --（与手机端行为一致）
    if (data.is_static) {
      $('#gaitCadence') && ($('#gaitCadence').textContent = '--');
      $('#gaitSpeed') && ($('#gaitSpeed').textContent = '--');
    } else {
      const cadence = data.cadence || 0;
      const speed = cadence > 0
        ? (cadence * 0.8 / 1000 * 60).toFixed(1)  // 与手机端相同公式，仅格式化
        : '--';
      $('#gaitCadence') && ($('#gaitCadence').textContent = cadence || '--');
      $('#gaitSpeed') && ($('#gaitSpeed').textContent = speed);
    }

    // 距离：手机端 GPS Haversine 累计 (米 → km)
    const distKm = (data.distance || 0) / 1000;
    $('#gaitDistance') && ($('#gaitDistance').textContent = distKm.toFixed(2));
    $('#gaitDuration') && ($('#gaitDuration').textContent = data.duration_s || 0);

    // 同步到 state 供其他模块参考
    state.steps = data.steps || 0;
    state.distance = data.distance || 0;
  }

  /**
   * 演示模式步态模拟（仅 demo 调用，真实数据由 handleGaitParams 处理）
   * 根据演示标签生成接近真实的步频/速度
   */
  function updateDemoGait(elapsedSec) {
    // 演示标签切换周期: 每 5 秒换一次
    const demoLabels = ['static','static','walking','walking','running','running',
                        'walking','walking','running','running','walking','walking'];
    const idx = Math.floor(elapsedSec / 5) % demoLabels.length;
    const label = demoLabels[idx];
    const phaseProgress = (elapsedSec % 5) / 5;  // 当前标签段内的进度 0~1

    // 各运动类型对应的典型步频范围
    const gaitProfiles = {
      static:     { cadenceBase: 0,   speed: 0,    stepLen: 0 },
      walking:    { cadenceBase: 110, speed: 4.2,  stepLen: 0.64 },
      running:    { cadenceBase: 170, speed: 9.8,  stepLen: 0.96 },
    };
    const profile = gaitProfiles[label] || gaitProfiles.walking;

    // 带缓动过渡的步频/速度/距离
    const ease = Math.sin(phaseProgress * Math.PI / 2);
    const cadence = profile.cadenceBase > 0
      ? Math.round(profile.cadenceBase * ease)
      : 0;
    const speed = profile.speed * ease;
    const distance = (speed * elapsedSec / 3600);  // km

    // 静止：显示 '--'
    if (label === 'static') {
      $('#gaitCadence') && ($('#gaitCadence').textContent = '--');
      $('#gaitSpeed') && ($('#gaitSpeed').textContent = '--');
    } else {
      $('#gaitCadence') && ($('#gaitCadence').textContent = cadence || '--');
      $('#gaitSpeed') && ($('#gaitSpeed').textContent = speed.toFixed(1));
    }
    $('#gaitDistance') && ($('#gaitDistance').textContent = distance.toFixed(2));
    $('#gaitDuration') && ($('#gaitDuration').textContent = elapsedSec);

    state.steps = Math.round(distance * 1000 / profile.stepLen);
    state.distance = distance * 1000;
  }

  // ============================================================
  //  演示模式
  // ============================================================
  window.toggleDemo = function () {
    state.demoMode = !state.demoMode;
    const btn = $('#demoBtn');
    const icon = $('#demoIcon');

    if (state.demoMode) {
      btn?.classList.add('active');
      if (icon) icon.textContent = '▶️';
      startDemo();
    } else {
      btn?.classList.remove('active');
      if (icon) icon.textContent = '🎬';
      stopDemo();
    }
  };

  /**
   * 手动纠正后的概率分布（纠正类别 100%）
   */
  function correctedProbas(label) {
    const allLabels = ['static', 'walking', 'running'];
    const result = {};
    for (let i = 0; i < allLabels.length; i++) {
      result[allLabels[i]] = allLabels[i] === label ? 1.0 : 0.0;
    }
    return result;
  }

  /**
   * 生成演示用假概率分布（主导类别 ~90%，其余随机分配）
   */
  function demoProbas(primary) {
    const allLabels = ['static', 'walking', 'running'];
    const result = {};
    let remaining = 1.0;
    // 主导类别占 85%~95%
    const primaryP = 0.85 + Math.random() * 0.10;
    result[primary] = primaryP;
    remaining -= primaryP;
    // 剩余概率随机分配给其他类别
    const others = allLabels.filter(l => l !== primary);
    for (let i = 0; i < others.length; i++) {
      if (i === others.length - 1) {
        result[others[i]] = Math.max(0, remaining);
      } else {
        const share = remaining * (0.3 + Math.random() * 0.4);
        result[others[i]] = Math.max(0, share);
        remaining -= share;
      }
    }
    return result;
  }

  function startDemo() {
    // 模拟数据
    const demoLabels = ['static', 'static', 'walking', 'walking', 'running', 'running',
                       'walking', 'walking', 'running', 'running', 'walking', 'walking'];

    setFocusView(true);
    updateFocusCard('running', 0.95, demoProbas('running'));
    $('#correctionPanel')?.classList.remove('hidden');
    updateCorrectionButtons();

    state.timestamps = [];
    state.accX = []; state.accY = []; state.accZ = [];
    state.gyroX = []; state.gyroY = []; state.gyroZ = [];

    let i = 0;
    const t0 = Date.now() / 1000;

    // 模拟 GPS 轨迹
    if (!state.mapInitialized) initMap();
    state.gpsTrack = [];
    let baseLat = 31.230;
    let baseLng = 121.470;

    state.demoInterval = setInterval(() => {
      const t = Date.now() / 1000 - t0;
      state.timestamps.push(t + t0);

      // 根据当前运动类型生成不同的加速度模式
      const label = demoLabels[Math.floor(t / 5) % demoLabels.length];
      let accAmp, gyroAmp, freq;
      if (label === 'static') { accAmp = 0.2; gyroAmp = 3; freq = 0.3; }
      else if (label === 'walking') { accAmp = 1.5; gyroAmp = 30; freq = 1.8; }
      else if (label === 'running') { accAmp = 4; gyroAmp = 80; freq = 2.8; }
      else { accAmp = 1.5; gyroAmp = 30; freq = 1.8; }

      const phase = t * freq * 2 * Math.PI;
      state.accX.push(accAmp * Math.sin(phase) + (Math.random() - 0.5) * 0.3);
      state.accY.push(accAmp * 0.5 * Math.cos(phase) + (Math.random() - 0.5) * 0.3);
      state.accZ.push(9.8 + accAmp * 0.8 * Math.abs(Math.sin(phase)));
      state.gyroX.push(gyroAmp * Math.cos(phase * 0.7) + (Math.random() - 0.5) * 5);
      state.gyroY.push(gyroAmp * 0.6 * Math.sin(phase) + (Math.random() - 0.5) * 5);
      state.gyroZ.push(gyroAmp * 0.3 * Math.sin(phase * 0.5) + (Math.random() - 0.5) * 3);

      // GPS (模拟移动)
      baseLat += 0.00002;
      baseLng += 0.00003;
      state.gpsTrack.push([baseLat, baseLng]);
      if (state.mapTrackLine) {
        state.mapTrackLine.setLatLngs(state.gpsTrack);
        if (state.mapInstance && state.gpsTrack.length % 20 === 0) {
          state.mapInstance.setView(state.gpsTrack[state.gpsTrack.length - 1],
                                     state.mapInstance.getZoom(), { animate: false });
        }
      }

      // 推理模拟
      if (Math.floor(t) % 2 === 0 && state.inferences.length * 2 < t) {
        state.inferences.push({ timestamp: t, label: label, confidence: 0.90 + Math.random() * 0.09 });
        updateFocusCard(label, 0.92 + Math.random() * 0.07, demoProbas(label));
      }

      // 缓冲区大小限制
      while (state.timestamps.length > 300) {
        state.timestamps.shift(); state.accX.shift(); state.accY.shift(); state.accZ.shift();
        state.gyroX.shift(); state.gyroY.shift(); state.gyroZ.shift();
      }

      updateDemoGait(Math.floor(t));
      throttleUpdateChart();
    }, 33); // ~30Hz
  }

  function stopDemo() {
    if (state.demoInterval) {
      clearInterval(state.demoInterval);
      state.demoInterval = null;
    }
    setFocusView(false);
    $('#correctionPanel')?.classList.add('hidden');
  }

  // ============================================================
  //  历史会话
  // ============================================================
  function loadHistory() {
    if (state.socket && state.socket.connected) {
      state.socket.emit('dashboard:request_history');
    }
  }

  window.refreshHistory = loadHistory;

  function handleHistory(data) {
    // 底部栏
    var barContainer = $('#historyList');
    if (barContainer) {
      if (!data.sessions || data.sessions.length === 0) {
        barContainer.innerHTML = '<span class="history-hint">没有历史会话</span>';
      } else {
        barContainer.innerHTML = data.sessions.map(function (s) {
          var labelMap = { static: '静止', walking: '走路', running: '跑步' };
          var lbl = labelMap[s.label] || s.label;
          var dur = s.duration_s ? Math.floor(s.duration_s / 60) + '分' + Math.floor(s.duration_s % 60) + '秒' : '进行中';
          var active = s.id === state.currentSessionId ? ' active' : '';
          var status = s.status === 'active' ? ' ●' : '';
          return '<div class="history-item' + active + '" onclick="viewSession(' + s.id + ')" title="会话 #' + s.id + '">' +
            '📅 ' + lbl + ' · ' + dur + ' · ' + (s.total_samples || 0) + '样本' + status +
          '</div>';
        }).join('');
      }
    }

    // 历史视图表格
    var tbody = $('#historyTableBody');
    if (!tbody) return;
    if (!data.sessions || data.sessions.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4" class="empty-hint">暂无历史会话</td></tr>';
      return;
    }
    var labelMap = { static: '静止', walking: '走路', running: '跑步' };
    tbody.innerHTML = data.sessions.map(function (s) {
      var lbl = labelMap[s.label] || s.label || '--';
      var time = s.started_at ? new Date(s.started_at).toLocaleString('zh-CN') : '--';
      var dur = s.duration_s ? Math.floor(s.duration_s / 60) + '分' + Math.floor(s.duration_s % 60) + '秒' : '进行中';
      return '<tr>' +
        '<td>' + lbl + '</td>' +
        '<td>' + time + '</td>' +
        '<td>' + dur + '</td>' +
        '<td><button class="toggle-btn" onclick="viewSession(' + s.id + ')">查看详情</button></td>' +
      '</tr>';
    }).join('');
  }

  window.viewSession = function (sessionId) {
    fetch(`/api/sessions/${sessionId}`)
      .then((r) => r.json())
      .then((data) => {
        alert(
          `会话 #${sessionId}\n` +
          `分类: ${data.classification?.primary || '未知'}\n` +
          `样本: ${data.n_samples}\n` +
          `推理: ${data.n_inferences}次\n` +
          `分布: ${JSON.stringify(data.classification || {})}`
        );
      })
      .catch((err) => console.error('获取会话失败:', err));
  };

  // ============================================================
  //  面板拖拽缩放
  // ============================================================
  function initResizeHandles() {
    const layout = $('#dashboardLayout');
    if (!layout) return;

    const handles = document.querySelectorAll('.resize-handle');
    let activeHandle = null;
    let startX = 0;
    let startLeft = 0;
    let startRight = 0;

    handles.forEach(function (handle) {
      handle.addEventListener('mousedown', function (e) {
        e.preventDefault();
        activeHandle = handle;
        activeHandle.classList.add('active');
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';

        const style = getComputedStyle(layout);
        startX = e.clientX;
        startLeft = parseInt(style.getPropertyValue('--col-left') || '260');
        startRight = parseInt(style.getPropertyValue('--col-right') || '300');
      });
    });

    document.addEventListener('mousemove', function (e) {
      if (!activeHandle) return;
      const dx = e.clientX - startX;
      const target = activeHandle.getAttribute('data-target');

      if (target === 'left') {
        // 左分隔条: 调整左栏宽度
        const newLeft = Math.max(200, Math.min(500, startLeft + dx));
        layout.style.setProperty('--col-left', newLeft + 'px');
        // 重绘图表和地图
        if (state.waveChart) state.waveChart.resize();
        if (state.mapInstance) setTimeout(function () { state.mapInstance.invalidateSize(); }, 50);
      } else if (target === 'right') {
        // 右分隔条: 调整右栏(地图)宽度
        const newRight = Math.max(200, Math.min(600, startRight - dx));
        layout.style.setProperty('--col-right', newRight + 'px');
        if (state.mapInstance) setTimeout(function () { state.mapInstance.invalidateSize(); }, 50);
      }
    });

    document.addEventListener('mouseup', function () {
      if (!activeHandle) return;
      activeHandle.classList.remove('active');
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      activeHandle = null;
      // 最终重绘
      if (state.waveChart) state.waveChart.resize();
      if (state.mapInstance) setTimeout(function () { state.mapInstance.invalidateSize(); }, 100);
    });
  }

  // ============================================================
  //  页面导航
  // ============================================================
  window.navigateTo = function (page) {
    // 更新侧边栏激活状态
    document.querySelectorAll('.nav-item').forEach(function (el) {
      el.classList.toggle('active', el.getAttribute('data-page') === page);
    });

    // 跨页跳转
    if (page === 'mobile') {
      window.location.href = '/mobile';
      return;
    }

    // 本页视图切换
    var isMonitor = page === 'monitor';
    // 监控视图: dashboard-layout + bottombar
    $('#dashboardLayout').classList.toggle('hidden', !isMonitor);
    $('#monitorBottombar').classList.toggle('hidden', !isMonitor);
    // 历史视图
    $('#historyView').classList.toggle('hidden', isMonitor);

    if (!isMonitor) loadHistory();
    if (isMonitor) {
      // 使用双重 RAF 确保 DOM 布局完成后再重绘
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          if (state.waveChart) state.waveChart.resize();
          if (state.mapInstance) state.mapInstance.invalidateSize();
        });
      });
    }
  };

  // ============================================================
  //  初始化
  // ============================================================
  function init() {
    initChart();
    initMap();
    initResizeHandles();
    connect();
  }

  // 等待依赖加载
  if (typeof io !== 'undefined' && typeof echarts !== 'undefined' && typeof L !== 'undefined') {
    init();
  } else {
    window.addEventListener('load', init);
  }
})();
