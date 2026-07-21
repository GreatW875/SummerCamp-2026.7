/**
 * 运动分析 - 手机端传感器采集脚本
 *
 * 职责:
 * - DeviceMotion / Geolocation 传感器数据采集
 * - WebSocket 实时通信
 * - 前端数据缓冲与降采样
 * - 会话生命周期管理
 * - 防误触与触觉反馈
 */
(function () {
  'use strict';

  // ============================================================
  //  状态管理
  // ============================================================
  const state = {
    socket: null,
    sessionId: null,
    active: false,
    selectedType: 'running',
    currentInferredLabel: 'running',  // 当前模型推理标签（静止时抑制步频）
    currentProbas: {},                // 当前各类别概率分布
    startTime: 0,
    timerInterval: null,
    sampleCount: 0,
    lastAcc: null,
    lastGyro: null,
    lastGps: null,
    buffer: [],
    bufferSize: 100,        // 累积100条后批量发送
    sendInterval: 200,       // 每200ms发送一次
    lastSendTime: 0,
    imuAvailable: false,
    gyroAvailable: false,
    gpsAvailable: false,
    wakeLock: null,
    stepDetector: {
      lastPeak: 0,
      steps: 0,
      cooldown: 0,
    },
    totalDistance: 0,
    lastGpsCoord: null,
    mapInitialized: false,
    mapInstance: null,
    mapTrackLine: null,
    gpsTrack: [],
    showMap: false,
  };

  // ============================================================
  //  DOM 引用
  // ============================================================
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const configView = $('#configView');
  const sportView = $('#sportView');
  const statusIndicator = $('#statusIndicator');
  const statusText = $('#statusText');
  const startBtn = $('#startBtn');
  const timerDisplay = $('#timerDisplay');
  const recordingDot = $('#recordingDot');
  const activityCard = $('#activityCard');
  const activityIcon = $('#activityIcon');
  const activityLabel = $('#activityLabel');
  const activityConfidence = $('#activityConfidence');
  const confirmModal = $('#confirmModal');
  const confirmDuration = $('#confirmDuration');
  const summaryModal = $('#summaryModal');
  const summaryContent = $('#summaryContent');

  // ============================================================
  //  传感器检测
  // ============================================================
  function detectSensors() {
    // 检测 DeviceMotion (加速度+陀螺仪)
    if (window.DeviceMotionEvent) {
      // iOS 13+ 需要用户手势授权
      if (typeof DeviceMotionEvent.requestPermission === 'function') {
        updateSensorStatus('imuStatus', '需要授权', '');
        updateSensorStatus('gyroStatus', '需要授权', '');
      } else {
        // Android / 旧版 iOS: 直接可用
        window.addEventListener('devicemotion', handleDeviceMotionTest, { once: true });
        setTimeout(() => {
          if (!state.imuAvailable) {
            updateSensorStatus('imuStatus', '不可用', 'error');
            updateSensorStatus('gyroStatus', '不可用', 'error');
          }
        }, 1000);
      }
    } else {
      updateSensorStatus('imuStatus', '不支持', 'error');
      updateSensorStatus('gyroStatus', '不支持', 'error');
    }

    // 检测 Geolocation
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        () => {
          state.gpsAvailable = true;
          updateSensorStatus('gpsStatus', '可用', 'ok');
        },
        () => {
          state.gpsAvailable = false;
          updateSensorStatus('gpsStatus', '未授权', 'error');
        },
        { timeout: 5000 }
      );
    } else {
      updateSensorStatus('gpsStatus', '不支持', 'error');
    }
  }

  function handleDeviceMotionTest(event) {
    const acc = event.accelerationIncludingGravity;
    const rot = event.rotationRate;
    if (acc) {
      state.imuAvailable = true;
      updateSensorStatus('imuStatus', '可用', 'ok');
    } else {
      updateSensorStatus('imuStatus', '不可用', 'error');
    }
    if (rot) {
      state.gyroAvailable = true;
      updateSensorStatus('gyroStatus', '可用', 'ok');
    } else {
      updateSensorStatus('gyroStatus', '不可用', 'error');
    }
  }

  function updateSensorStatus(id, text, cls) {
    const el = document.getElementById(id);
    if (el) {
      el.textContent = text;
      el.className = 'sensor-badge ' + cls;
    }
  }

  // ============================================================
  //  iOS 13+ 传感器权限请求
  // ============================================================
  async function requestIOSPermission() {
    if (typeof DeviceMotionEvent !== 'undefined' &&
        typeof DeviceMotionEvent.requestPermission === 'function') {
      try {
        const resp = await DeviceMotionEvent.requestPermission();
        if (resp === 'granted') {
          state.imuAvailable = true;
          state.gyroAvailable = true;
          updateSensorStatus('imuStatus', '已授权', 'ok');
          updateSensorStatus('gyroStatus', '已授权', 'ok');
        }
      } catch (e) {
        console.warn('传感器权限被拒绝:', e);
      }
    }
  }

  // ============================================================
  //  WebSocket 连接
  // ============================================================
  function connectWebSocket() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${location.host}`;

    // Bug 修复: 手机端自签名证书下 WSS 握手经常被浏览器静默拒绝，
    // 因此将 polling (XHR long-polling) 放在首位作为更可靠的传输方式。
    // Socket.IO 会先尝试 polling，成功后自动协商升级到 WebSocket。
    state.socket = io(wsUrl, {
      transports: ['polling', 'websocket'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: Infinity,
      timeout: 20000,          // 单次连接超时 20s
    });

    state.socket.on('connect', () => {
      updateSensorStatus('wsStatus', '已连接', 'ok');
      statusText.textContent = '已连接';
      statusIndicator.querySelector('.dot').className = 'dot dot-connected';
      startBtn.disabled = false;
      console.log('[Socket.IO] 已连接到服务器');
    });

    state.socket.on('disconnect', (reason) => {
      updateSensorStatus('wsStatus', '断开', 'error');
      statusText.textContent = '已断开';
      statusIndicator.querySelector('.dot').className = 'dot dot-disconnected';
      console.warn('[Socket.IO] 断开连接:', reason);
    });

    state.socket.on('connect_error', (err) => {
      updateSensorStatus('wsStatus', '连接失败', 'error');
      statusText.textContent = '连接失败';
      console.error('[Socket.IO] 连接错误:', err.message);
    });

    state.socket.on('mobile:session_started', (data) => {
      state.sessionId = data.session_id;
      console.log('会话已创建:', state.sessionId);
    });

    state.socket.on('mobile:session_ended', () => {
      showSummary();
    });

    // 接收推理结果
    state.socket.on('dashboard:inference_result', (data) => {
      if (data.session_id === state.sessionId) {
        state.currentProbas = data.probas || {};
        updateActivityDisplay(data.label, data.confidence);
      }
    });
  }

  // ============================================================
  //  运动类型选择
  // ============================================================
  window.selectType = function (label, btn) {
    state.selectedType = label;
    $$('.type-btn').forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');

    // 触觉反馈
    if (navigator.vibrate) {
      navigator.vibrate(10);
    }
  };

  // ============================================================
  //  开始运动
  // ============================================================
  window.startSession = async function () {
    if (!state.socket || !state.socket.connected) {
      alert('请等待服务器连接');
      return;
    }

    // iOS 权限请求
    await requestIOSPermission();

    // 禁用按钮，显示加载
    startBtn.disabled = true;
    startBtn.classList.add('loading');

    // 请求 WakeLock
    try {
      if (navigator.wakeLock) {
        state.wakeLock = await navigator.wakeLock.request('screen');
      }
    } catch (e) {
      console.warn('WakeLock 不可用:', e);
    }

    // 锁定竖屏
    try {
      if (screen.orientation && screen.orientation.lock) {
        await screen.orientation.lock('portrait').catch(() => {});
      }
    } catch (e) {}

    // 发送开始会话
    state.socket.emit('mobile:start_session', { label: state.selectedType });

    // 等待 session_id 返回
    let attempts = 0;
    while (!state.sessionId && attempts < 50) {
      await sleep(100);
      attempts++;
    }

    // 注册传感器监听
    registerSensors();

    // 启动计时器
    state.active = true;
    state.startTime = Date.now();
    state.sampleCount = 0;
    state.totalDistance = 0;
    state.lastGpsCoord = null;
    state.gpsTrack = [];
    state.stepDetector = { lastPeak: 0, steps: 0, cooldown: 0 };
    state.buffer = [];
    state.currentInferredLabel = state.selectedType;  // 初始同步用户选择的类型

    startTimer();
    startGpsTracking();

    // 切换到运动视图
    configView.classList.add('hidden');
    sportView.classList.remove('hidden');
    recordingDot.innerHTML = '● 采集中';
    statusIndicator.querySelector('.dot').className = 'dot dot-recording';

    // 初始化运动类型显示
    const icons = { static: '🧍', walking: '🚶', running: '🏃' };
    activityIcon.textContent = icons[state.selectedType] || '🏃';
    activityLabel.textContent = typeLabel(state.selectedType);
    activityConfidence.textContent = '准备分析...';
    activityCard.className = 'activity-card';

    // 触觉反馈
    if (navigator.vibrate) {
      navigator.vibrate(200);
    }

    startBtn.classList.remove('loading');
    startBtn.disabled = false;
  };

  // ============================================================
  //  传感器数据采集
  // ============================================================
  function registerSensors() {
    window.addEventListener('devicemotion', handleDeviceMotion, { passive: true });
  }

  function unregisterSensors() {
    window.removeEventListener('devicemotion', handleDeviceMotion);
    if (state.gpsWatchId) {
      navigator.geolocation.clearWatch(state.gpsWatchId);
      state.gpsWatchId = null;
    }
  }

  function handleDeviceMotion(event) {
    if (!state.active) return;

    const acc = event.accelerationIncludingGravity;
    const rot = event.rotationRate;

    const record = {
      timestamp: Date.now() / 1000,
      acc_x: acc?.x || 0,
      acc_y: acc?.y || 0,
      acc_z: acc?.z || 0,
      gyro_x: rot?.alpha || 0,
      gyro_y: rot?.beta || 0,
      gyro_z: rot?.gamma || 0,
      lat: state.lastGps?.lat || null,
      lng: state.lastGps?.lng || null,
    };

    state.buffer.push(record);
    state.sampleCount++;

    // 步频估算 (基于加速度幅值峰值检测)
    // 静止状态跳过步数累计，避免传感器噪声产生虚假步频
    const accMag = Math.sqrt(
      record.acc_x ** 2 + record.acc_y ** 2 + (record.acc_z - 9.8) ** 2
    );
    const now = Date.now();
    if (state.currentInferredLabel !== 'static' &&
        accMag > 12 &&
        now - state.stepDetector.lastPeak > 250) {
      state.stepDetector.steps++;
      state.stepDetector.lastPeak = now;
    }
    updateMetrics(accMag);

    // 批量发送
    const now2 = Date.now();
    if (state.buffer.length >= state.bufferSize ||
        (state.buffer.length > 0 && now2 - state.lastSendTime > state.sendInterval)) {
      flushBuffer();
    }
  }

  function flushBuffer() {
    if (!state.socket || !state.socket.connected) {
      // 离线缓冲在内存中（最多保留1000条）
      if (state.buffer.length > 1000) {
        state.buffer = state.buffer.slice(-1000);
      }
      return;
    }

    const batch = state.buffer.splice(0, state.buffer.length);
    const sessionId = state.sessionId;

    for (const record of batch) {
      state.socket.emit('mobile:sensor_data', {
        session_id: sessionId,
        ...record,
      });
    }
    state.lastSendTime = Date.now();

    // ── 同步步态参数到服务端，确保电脑端与手机端数据一致 ──
    emitGaitParams(sessionId);
  }

  function emitGaitParams(sessionId) {
    const isStatic = state.currentInferredLabel === 'static';
    const elapsedMin = state.startTime > 0
      ? (Date.now() - state.startTime) / 60000
      : 0;
    // 与 updateMetrics 完全相同的步频/速度公式
    const cadence = (!isStatic && elapsedMin > 0.1)
      ? Math.round(state.stepDetector.steps / elapsedMin)
      : 0;
    const speed = cadence > 0
      ? (cadence * 0.8 / 1000 * 60)  // km/h，保留原始精度不 toFixed
      : 0;
    const distance = state.totalDistance;  // GPS Haversine 累计距离 (米)

    state.socket.emit('mobile:gait_params', {
      session_id: sessionId,
      cadence: cadence,                     // 步/分
      speed: speed,                         // km/h
      distance: distance,                   // 米
      steps: state.stepDetector.steps,
      duration_s: state.startTime > 0
        ? Math.floor((Date.now() - state.startTime) / 1000)
        : 0,
      is_static: isStatic,
    });
  }

  // ============================================================
  //  GPS 追踪
  // ============================================================
  function startGpsTracking() {
    if (!navigator.geolocation) return;

    state.gpsWatchId = navigator.geolocation.watchPosition(
      (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        state.lastGps = { lat: lat, lng: lng };
        state.gpsAvailable = true;

        // 更新手机端地图轨迹
        updateMobileGps(lat, lng);

        // 计算距离
        if (state.lastGpsCoord) {
          const d = haversine(state.lastGpsCoord, state.lastGps);
          state.totalDistance += d;
          state.lastGpsCoord = state.lastGps;
        } else {
          state.lastGpsCoord = state.lastGps;
        }
        updateDistanceDisplay();
      },
      (err) => {
        console.warn('GPS error:', err);
        state.gpsAvailable = false;
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 1000,
      }
    );
  }

  function haversine(c1, c2) {
    const R = 6371000; // 地球半径 (m)
    const toRad = (deg) => (deg * Math.PI) / 180;
    const dLat = toRad(c2.lat - c1.lat);
    const dLng = toRad(c2.lng - c1.lng);
    const a =
      Math.sin(dLat / 2) ** 2 +
      Math.cos(toRad(c1.lat)) * Math.cos(toRad(c2.lat)) *
      Math.sin(dLng / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  // ============================================================
  //  手机端地图
  // ============================================================
  function initMobileMap() {
    if (state.mapInitialized) return;

    const container = document.getElementById('mobileMap');
    if (!container) return;

    state.mapInstance = L.map(container, {
      attributionControl: false,
      zoomControl: true,
    }).setView([31.23, 121.47], 16);

    // 高德瓦片
    L.tileLayer('https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}', {
      subdomains: ['1', '2', '3', '4'],
      maxZoom: 18,
    }).addTo(state.mapInstance);

    state.mapTrackLine = L.polyline([], {
      color: '#2563EB', weight: 4, opacity: 0.8,
    }).addTo(state.mapInstance);

    state.mapInitialized = true;
  }

  function updateMobileGps(lat, lng) {
    if (!state.mapInitialized) initMobileMap();

    state.gpsTrack.push([lat, lng]);
    if (state.mapTrackLine) {
      state.mapTrackLine.setLatLngs(state.gpsTrack);
    }

    // 地图跟随最新位置
    if (state.mapInstance && state.gpsTrack.length > 0) {
      state.mapInstance.setView(
        state.gpsTrack[state.gpsTrack.length - 1],
        state.mapInstance.getZoom(),
        { animate: true }
      );
    }
  }

  window.toggleMapView = function () {
    const sportMain = document.getElementById('sportMain');
    const secondary = document.getElementById('secondaryBar');
    const mapView = document.getElementById('mobileMapView');
    const toggleIcon = document.getElementById('mapToggleIcon');

    state.showMap = !state.showMap;

    if (state.showMap) {
      // 切换到地图视图
      if (sportMain) sportMain.classList.add('hidden');
      if (secondary) secondary.classList.add('hidden');
      if (mapView) mapView.classList.remove('hidden');
      if (toggleIcon) toggleIcon.textContent = '📊';
      initMobileMap();
      // 重绘地图
      setTimeout(function () {
        if (state.mapInstance) state.mapInstance.invalidateSize();
      }, 100);
    } else {
      // 切换回数据视图
      if (sportMain) sportMain.classList.remove('hidden');
      if (secondary) secondary.classList.remove('hidden');
      if (mapView) mapView.classList.add('hidden');
      if (toggleIcon) toggleIcon.textContent = '🗺️';
    }
  };

  // ============================================================
  //  显示更新
  // ============================================================
  function updateActivityDisplay(label, confidence) {
    const icons = { static: '🧍', walking: '🚶', running: '🏃' };
    const hasChanged = activityLabel.textContent !== typeLabel(label);

    // 更新当前推理标签，供步数检测/步频计算使用
    state.currentInferredLabel = label;

    activityIcon.textContent = icons[label] || '❓';
    activityLabel.textContent = typeLabel(label);
    activityConfidence.textContent = `置信度 ${(confidence * 100).toFixed(1)}%`;

    // 置信度视觉层级
    activityCard.classList.remove('high-confidence', 'medium-confidence', 'low-confidence');
    if (confidence >= 0.90) {
      activityCard.classList.add('high-confidence');
    } else if (confidence >= 0.70) {
      activityCard.classList.add('medium-confidence');
    } else {
      activityCard.classList.add('low-confidence');
    }

    // 渲染全部类别概率条
    renderProbBars(state.currentProbas || {}, label);

    // 运动类型切换提醒
    if (hasChanged && navigator.vibrate) {
      navigator.vibrate([50, 50, 50]);
    }
  }

  /**
   * 渲染所有类别的概率条（手机端）
   */
  function renderProbBars(probas, activeLabel) {
    const container = document.getElementById('probBars');
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
      html += '<div class="prob-row' + (isTop ? ' prob-top' : '') + '">' +
        '<span class="prob-icon">' + (icons[lb] || '❓') + '</span>' +
        '<span class="prob-name">' + (names[lb] || lb) + '</span>' +
        '<span class="prob-pct">' + pct + '%</span>' +
        '<div class="prob-bar-track">' +
          '<div class="prob-bar-fill" style="width:' + barW + '%"></div>' +
        '</div>' +
      '</div>';
    }
    container.innerHTML = html;
  }

  function updateMetrics(accMag) {
    // 静止状态下不显示步频和速度（传感器噪声会产生假数据）
    if (state.currentInferredLabel === 'static') {
      document.getElementById('metricCadence').textContent = '--';
      document.getElementById('metricSpeed').textContent = '--';
    } else {
      // 步频估算
      if (state.startTime > 0) {
        const elapsedMin = (Date.now() - state.startTime) / 60000;
        const cadence = elapsedMin > 0.1
          ? Math.round(state.stepDetector.steps / elapsedMin)
          : 0;
        document.getElementById('metricCadence').textContent = cadence || '--';

        // 速度估算 (基于步频)
        if (cadence > 0) {
          const speed = (cadence * 0.8 / 1000 * 60).toFixed(1);
          document.getElementById('metricSpeed').textContent = speed;
        } else {
          document.getElementById('metricSpeed').textContent = '--';
        }
      }
    }

    document.getElementById('metricSamples').textContent = state.sampleCount;
  }

  function updateDistanceDisplay() {
    document.getElementById('metricDistance').textContent =
      (state.totalDistance / 1000).toFixed(2) + ' km';
  }

  // ============================================================
  //  计时器
  // ============================================================
  function startTimer() {
    state.timerInterval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - state.startTime) / 1000);
      const h = Math.floor(elapsed / 3600);
      const m = Math.floor((elapsed % 3600) / 60);
      const s = elapsed % 60;
      timerDisplay.textContent =
        String(h).padStart(2, '0') + ':' +
        String(m).padStart(2, '0') + ':' +
        String(s).padStart(2, '0');
    }, 200);
  }

  function stopTimer() {
    if (state.timerInterval) {
      clearInterval(state.timerInterval);
      state.timerInterval = null;
    }
  }

  // ============================================================
  //  结束运动
  // ============================================================
  window.endSession = function () {
    const elapsed = Math.floor((Date.now() - state.startTime) / 1000);
    const m = Math.floor(elapsed / 60);
    const s = elapsed % 60;
    confirmDuration.textContent = `已运动 ${m}分${s}秒，确定要结束吗？`;
    confirmModal.classList.remove('hidden');
  };

  window.cancelEndSession = function () {
    confirmModal.classList.add('hidden');
  };

  window.confirmEndSession = function () {
    confirmModal.classList.add('hidden');
    state.active = false;
    stopTimer();
    unregisterSensors();
    flushBuffer();

    if (state.socket && state.socket.connected) {
      state.socket.emit('mobile:end_session', {
        session_id: state.sessionId,
      });
    }

    // 释放 WakeLock
    if (state.wakeLock) {
      state.wakeLock.release().catch(() => {});
      state.wakeLock = null;
    }

    // 解锁竖屏
    try {
      if (screen.orientation && screen.orientation.unlock) {
        screen.orientation.unlock();
      }
    } catch (e) {}

    recordingDot.innerHTML = '○ 已停止';
    statusIndicator.querySelector('.dot').className = 'dot dot-connected';
  };

  // ============================================================
  //  运动小结
  // ============================================================
  function showSummary() {
    const elapsed = Math.floor((Date.now() - state.startTime) / 1000);
    const h = Math.floor(elapsed / 3600);
    const m = Math.floor((elapsed % 3600) / 60);
    const s = elapsed % 60;

    const cadence = parseInt(document.getElementById('metricCadence').textContent) || 0;
    const speed = document.getElementById('metricSpeed').textContent || '--';

    summaryContent.innerHTML = `
      <div class="summary-row">
        <span class="summary-row-label">运动类型</span>
        <span class="summary-row-value">${typeLabel(state.selectedType)}</span>
      </div>
      <div class="summary-row">
        <span class="summary-row-label">持续时间</span>
        <span class="summary-row-value">${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}</span>
      </div>
      <div class="summary-row">
        <span class="summary-row-label">距离</span>
        <span class="summary-row-value">${(state.totalDistance / 1000).toFixed(2)} km</span>
      </div>
      <div class="summary-row">
        <span class="summary-row-label">平均步频</span>
        <span class="summary-row-value">${cadence} 步/分</span>
      </div>
      <div class="summary-row">
        <span class="summary-row-label">平均速度</span>
        <span class="summary-row-value">${speed} km/h</span>
      </div>
      <div class="summary-row">
        <span class="summary-row-label">采集样本</span>
        <span class="summary-row-value">${state.sampleCount} 条</span>
      </div>
    `;
    summaryModal.classList.remove('hidden');
  }

  window.closeSummary = function () {
    summaryModal.classList.add('hidden');
    // 返回配置视图
    sportView.classList.add('hidden');
    configView.classList.remove('hidden');
    state.sessionId = null;
    state.active = false;
    state.sampleCount = 0;
    state.totalDistance = 0;
  };

  // ============================================================
  //  工具函数
  // ============================================================
  function typeLabel(type) {
    const map = { static: '静止', walking: '走路', running: '跑步' };
    return map[type] || type;
  }

  function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  // ============================================================
  //  页面关闭前处理
  // ============================================================
  window.addEventListener('beforeunload', () => {
    if (state.active) {
      flushBuffer();
      if (state.socket && state.socket.connected) {
        state.socket.emit('mobile:end_session', { session_id: state.sessionId });
      }
    }
  });

  // ============================================================
  //  初始化
  // ============================================================
  function init() {
    startBtn.disabled = true;
    detectSensors();

    // 先请求iOS传感器权限
    requestIOSPermission().then(() => {
      connectWebSocket();
    });
  }

  // Socket.IO 加载后初始化
  if (typeof io !== 'undefined') {
    init();
  } else {
    window.addEventListener('load', () => {
      // 等待 Socket.IO CDN 加载（最多 15 秒）
      var _checkCount = 0;
      var _maxChecks = 75;  // 75 * 200ms = 15s
      var check = setInterval(function () {
        _checkCount++;
        if (typeof io !== 'undefined') {
          clearInterval(check);
          init();
        } else if (_checkCount >= _maxChecks) {
          clearInterval(check);
          // 超时：显示明确错误信息给用户
          updateSensorStatus('wsStatus', '库加载失败', 'error');
          statusText.textContent = '初始化失败';
          console.error(
            '[Socket.IO] CDN 加载超时。请检查：\n' +
            '  1. 手机能否访问外网 (cdn.socket.io)\n' +
            '  2. 是否已信任 SSL 证书\n' +
            '  3. 防火墙是否放行 5000 端口'
          );
        }
      }, 200);
    });
  }
})();
