/**
 * NEXUS TRADER // Frontend Core Application
 * High-performance WebSocket telemetry, TradingView Lightweight Charts v5,
 * Real-time indicators, Risk controls & Sound Engine.
 */

// Application State
const state = {
  isRunning: false,
  status: 'PAUSED',
  mode: 'PAPER',
  symbol: 'BTC/USDT',
  timeframe: '1m',
  activeStrategy: 'ema_rsi',
  currentPrice: 0.0,
  lastPrice: 0.0,
  soundEnabled: true,
  logFilter: 'ALL',
  allLogs: [],
  chartMarkers: []
};

// Global Chart References
let chart = null;
let candleSeries = null;
let emaFastSeries = null;
let emaSlowSeries = null;
let ws = null;
let pingInterval = null;

// Audio Context for synthesized sound cues
let audioCtx = null;

function initAudio() {
  if (!audioCtx) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (AudioContextClass) {
      audioCtx = new AudioContextClass();
    }
  }
}

function playTradeSound(side) {
  if (!state.soundEnabled) return;
  try {
    initAudio();
    if (!audioCtx) return;
    if (audioCtx.state === 'suspended') {
      audioCtx.resume();
    }

    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain);
    gain.connect(audioCtx.destination);

    const now = audioCtx.currentTime;
    if (side === 'BUY') {
      // Ascending crystal chime
      osc.type = 'sine';
      osc.frequency.setValueAtTime(587.33, now); // D5
      osc.frequency.exponentialRampToValueAtTime(880.0, now + 0.18); // A5
      gain.gain.setValueAtTime(0.2, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
      osc.start(now);
      osc.stop(now + 0.36);
    } else {
      // Descending resolve chime
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(783.99, now); // G5
      osc.frequency.exponentialRampToValueAtTime(523.25, now + 0.22); // C5
      gain.gain.setValueAtTime(0.2, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.4);
      osc.start(now);
      osc.stop(now + 0.41);
    }
  } catch (e) {
    console.debug('Audio cue skipped:', e);
  }
}

// ==========================================================================
// CHART INITIALIZATION (TradingView Lightweight Charts v5)
// ==========================================================================
function initChart() {
  const container = document.getElementById('tv-chart-container');
  if (!container) return;

  container.innerHTML = ''; // Clear container

  chart = LightweightCharts.createChart(container, {
    width: container.clientWidth,
    height: container.clientHeight || 520,
    layout: {
      background: { type: 'solid', color: '#0a0e16' },
      textColor: '#8e9cb2',
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: 11
    },
    grid: {
      vertLines: { color: 'rgba(255, 255, 255, 0.03)' },
      horzLines: { color: 'rgba(255, 255, 255, 0.03)' }
    },
    crosshair: {
      mode: LightweightCharts.CrosshairMode.Normal,
      vertLine: {
        color: 'rgba(0, 229, 255, 0.4)',
        width: 1,
        style: LightweightCharts.LineStyle.Dashed
      },
      horzLine: {
        color: 'rgba(0, 229, 255, 0.4)',
        width: 1,
        style: LightweightCharts.LineStyle.Dashed
      }
    },
    rightPriceScale: {
      borderColor: 'rgba(255, 255, 255, 0.08)',
      scaleMargins: { top: 0.1, bottom: 0.15 }
    },
    timeScale: {
      borderColor: 'rgba(255, 255, 255, 0.08)',
      timeVisible: true,
      secondsVisible: false
    }
  });

  // Candlestick Series
  candleSeries = chart.addSeries(LightweightCharts.CandlestickSeries, {
    upColor: '#00f59b',
    downColor: '#ff3366',
    borderVisible: false,
    wickUpColor: '#00f59b',
    wickDownColor: '#ff3366'
  });

  // Fast EMA (9) - Cyan
  emaFastSeries = chart.addSeries(LightweightCharts.LineSeries, {
    color: '#00e5ff',
    lineWidth: 2,
    title: 'EMA 9',
    crosshairMarkerVisible: false
  });

  // Slow EMA (21) - Purple
  emaSlowSeries = chart.addSeries(LightweightCharts.LineSeries, {
    color: '#9d4edd',
    lineWidth: 2,
    title: 'EMA 21',
    crosshairMarkerVisible: false
  });

  // Responsive Resize Observer
  const resizeObserver = new ResizeObserver(entries => {
    if (!entries || entries.length === 0) return;
    const { width, height } = entries[0].contentRect;
    if (chart && width > 0 && height > 0) {
      chart.applyOptions({ width, height });
    }
  });
  resizeObserver.observe(container);
}

// ==========================================================================
// WEBSOCKET TELEMETRY CLIENT
// ==========================================================================
function connectWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws`;

  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log('[WS] Connected to Nexus Trading Engine.');
    updateLivePulse(true);

    // Keepalive ping
    if (pingInterval) clearInterval(pingInterval);
    pingInterval = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: 'PING', time: Date.now() }));
      }
    }, 15000);
  };

  ws.onmessage = event => {
    try {
      const msg = JSON.parse(event.data);
      handleWsMessage(msg);
    } catch (e) {
      console.error('[WS] Parse error:', e);
    }
  };

  ws.onerror = err => {
    console.warn('[WS] Error:', err);
  };

  ws.onclose = () => {
    console.warn('[WS] Disconnected. Reconnecting in 3 seconds...');
    updateLivePulse(false);
    if (pingInterval) clearInterval(pingInterval);
    setTimeout(connectWebSocket, 3000);
  };
}

function handleWsMessage(msg) {
  switch (msg.type) {
    case 'INITIAL_STATE':
      loadInitialState(msg.data);
      break;

    case 'TICKER_UPDATE':
      handleTickerUpdate(msg.data);
      break;

    case 'INDICATORS_UPDATE':
      handleIndicatorsUpdate(msg.data);
      break;

    case 'TRADE_EXECUTED':
      handleTradeExecuted(msg.data);
      break;

    case 'LOG_ENTRY':
      appendLog(msg.data);
      break;
  }
}

// ==========================================================================
// STATE & TELEMETRY HANDLERS
// ==========================================================================
function loadInitialState(data) {
  state.isRunning = data.is_running;
  state.status = data.status;
  state.mode = data.mode;
  state.symbol = data.symbol;
  state.timeframe = data.timeframe;
  state.activeStrategy = data.active_strategy;
  state.currentPrice = data.current_price;

  // Sync Top Controls
  document.getElementById('pair-select').value = data.symbol;
  document.querySelectorAll('.tf-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.tf === data.timeframe);
  });
  updateModeBadge(data.mode);
  updateBotButton(data.status);

  // Sync Strategy & Risk Inputs
  document.getElementById('strategy-select').value = data.active_strategy;
  const cfg = data.config || {};
  if (cfg.trade_amount_usdt) {
    document.getElementById('input-trade-amount').value = cfg.trade_amount_usdt;
    document.getElementById('val-trade-amount-disp').textContent = `$${cfg.trade_amount_usdt}`;
  }
  if (cfg.stop_loss_pct) {
    document.getElementById('input-stop-loss').value = cfg.stop_loss_pct;
    document.getElementById('val-stop-loss-disp').textContent = `-${cfg.stop_loss_pct}%`;
  }
  if (cfg.take_profit_pct) {
    document.getElementById('input-take-profit').value = cfg.take_profit_pct;
    document.getElementById('val-take-profit-disp').textContent = `+${cfg.take_profit_pct}%`;
  }
  if (cfg.trailing_stop_enabled !== undefined) {
    document.getElementById('check-trailing-stop').checked = cfg.trailing_stop_enabled;
  }

  // Populate Candles on Chart
  if (data.candles && data.candles.length > 0 && candleSeries) {
    candleSeries.setData(data.candles);

    // Compute basic initial EMA series for chart lines
    const emaFastData = [];
    const emaSlowData = [];
    data.candles.forEach(c => {
      emaFastData.push({ time: c.time, value: c.close });
      emaSlowData.push({ time: c.time, value: c.close });
    });
    emaFastSeries.setData(emaFastData);
    emaSlowSeries.setData(emaSlowData);
    chart.timeScale().fitContent();
  }

  // Populate Markers
  if (data.markers && data.markers.length > 0) {
    state.chartMarkers = data.markers;
    if (typeof candleSeries.setMarkers === 'function') {
      candleSeries.setMarkers(state.chartMarkers);
    }
  }

  // Portfolio & Indicators
  if (data.portfolio) {
    updatePortfolioUI(data.portfolio);
  }
  if (data.indicators) {
    updateIndicatorsHUD(data.indicators);
  }
  if (data.signal) {
    updateSignalCard(data.signal);
  }

  // Logs
  if (data.logs && Array.isArray(data.logs)) {
    state.allLogs = data.logs;
    renderLogs();
  }
}

function handleTickerUpdate(data) {
  const price = data.price;
  state.currentPrice = price;

  // Flash ticker price in HUD
  const priceEl = document.getElementById('hud-price');
  if (priceEl) {
    priceEl.textContent = formatCurrency(price);
    priceEl.classList.remove('tick-up', 'tick-down');
    if (state.lastPrice > 0) {
      if (price > state.lastPrice) priceEl.classList.add('tick-up');
      else if (price < state.lastPrice) priceEl.classList.add('tick-down');
    }
  }
  state.lastPrice = price;

  // Update live candle on chart
  if (data.candle && candleSeries) {
    candleSeries.update(data.candle);
  }

  // Update Portfolio Equity & Position in real time
  if (data.portfolio) {
    updatePortfolioUI(data.portfolio);
  }
}

function handleIndicatorsUpdate(data) {
  updateIndicatorsHUD(data);

  if (data.signal) {
    updateSignalCard(data.signal);
  }

  // Update EMA lines at current candle time
  if (candleSeries && emaFastSeries && emaSlowSeries && data.price) {
    const lastBar = candleSeries.data ? candleSeries.data()[candleSeries.data().length - 1] : null;
    const nowSec = lastBar ? lastBar.time : Math.floor(Date.now() / 1000);

    if (data.ema_fast) emaFastSeries.update({ time: nowSec, value: data.ema_fast });
    if (data.ema_slow) emaSlowSeries.update({ time: nowSec, value: data.ema_slow });
  }
}

function handleTradeExecuted(data) {
  const trade = data.trade;
  const marker = data.marker;

  // Play audio chime
  playTradeSound(trade.side);

  // Add marker to chart
  if (marker && candleSeries) {
    state.chartMarkers.push(marker);
    if (state.chartMarkers.length > 50) state.chartMarkers.shift();
    if (typeof candleSeries.setMarkers === 'function') {
      candleSeries.setMarkers(state.chartMarkers);
    }
  }

  // Prepend trade to recent executions table
  prependTradeRow(trade);
}

// ==========================================================================
// UI RENDERERS
// ==========================================================================
function updatePortfolioUI(p) {
  document.getElementById('metric-total-equity').textContent = formatNumber(p.total_equity);
  document.getElementById('metric-usdt-balance').textContent = formatNumber(p.usdt_balance);
  document.getElementById('metric-win-rate').textContent = `${p.win_rate_pct}%`;
  document.getElementById('metric-profit-factor').textContent = p.profit_factor.toFixed(2);
  document.getElementById('metric-max-dd').textContent = `${p.max_drawdown_pct.toFixed(1)}%`;
  document.getElementById('trades-count-badge').textContent = `${p.total_trades} TRADES`;

  // Net PnL Pill
  const pnlPill = document.getElementById('metric-total-pnl-pill');
  const pnlSign = p.total_realized_pnl >= 0 ? '+' : '';
  pnlPill.textContent = `${pnlSign}$${p.total_realized_pnl.toFixed(2)} (${p.total_pnl_pct >= 0 ? '+' : ''}${p.total_pnl_pct.toFixed(2)}%)`;
  pnlPill.className = 'pnl-pill ' + (p.total_realized_pnl > 0 ? 'profit' : (p.total_realized_pnl < 0 ? 'loss' : 'neutral'));

  // Allocation Bar
  const totalVal = p.total_equity > 0 ? p.total_equity : 10000;
  const assetVal = p.active_position ? p.active_position.market_value : 0;
  const allocPct = Math.min(100, Math.max(0, (assetVal / totalVal) * 100));
  document.getElementById('allocation-bar-fill').style.width = `${allocPct.toFixed(1)}%`;
  document.getElementById('allocation-pct-label').textContent = `${allocPct.toFixed(1)}% in Asset`;

  const assetBase = state.symbol.split('/')[0];
  document.getElementById('asset-holding-label').textContent = `${p.asset_balance.toFixed(4)} ${assetBase}`;

  // Active Position Card
  const posBadge = document.getElementById('pos-status-badge');
  const posPnlDisp = document.getElementById('pos-pnl-display');
  const posPnlPct = document.getElementById('pos-pnl-pct');
  const posDetails = document.getElementById('pos-details-text');

  if (p.active_position) {
    const pos = p.active_position;
    posBadge.textContent = `LONG ${pos.quantity.toFixed(4)} ${assetBase}`;
    posBadge.className = 'pos-badge long';

    const pnlSign = pos.unrealized_pnl >= 0 ? '+' : '';
    posPnlDisp.textContent = `${pnlSign}$${pos.unrealized_pnl.toFixed(2)}`;
    posPnlPct.textContent = `(${pnlSign}${pos.unrealized_pnl_pct.toFixed(2)}%)`;

    const posClass = pos.unrealized_pnl >= 0 ? 'profit' : 'loss';
    posPnlDisp.className = `metric-value mono ${posClass}`;
    posPnlPct.className = `pos-pnl-pct mono ${posClass}`;

    posDetails.innerHTML = `Entry: <strong>$${formatCurrency(pos.entry_price)}</strong> | Val: <strong>$${formatNumber(pos.market_value)}</strong>`;
  } else {
    posBadge.textContent = 'NO OPEN POSITION';
    posBadge.className = 'pos-badge none';
    posPnlDisp.textContent = '$0.00';
    posPnlPct.textContent = '(0.00%)';
    posPnlDisp.className = 'metric-value mono neutral';
    posPnlPct.className = 'pos-pnl-pct mono neutral';
    posDetails.textContent = 'Bot awaiting entry triggers';
  }

  // Populate recent trades table if available
  if (p.recent_trades && Array.isArray(p.recent_trades)) {
    renderTradesTable(p.recent_trades);
  }
}

function updateIndicatorsHUD(ind) {
  if (ind.ema_fast) document.getElementById('val-ema-fast').textContent = formatCurrency(ind.ema_fast);
  if (ind.ema_slow) document.getElementById('val-ema-slow').textContent = formatCurrency(ind.ema_slow);

  if (ind.rsi !== undefined) {
    const rsi = ind.rsi;
    const rsiEl = document.getElementById('val-rsi');
    rsiEl.textContent = rsi.toFixed(1);

    // Color code RSI
    if (rsi <= 30) rsiEl.className = 'chip-val mono success';
    else if (rsi >= 70) rsiEl.className = 'chip-val mono danger';
    else rsiEl.className = 'chip-val mono';

    // Update RSI Gauge in Sidebar
    document.getElementById('gauge-rsi-val').textContent = rsi.toFixed(1);
    const needle = document.getElementById('rsi-pointer');
    if (needle) {
      needle.style.left = `${Math.min(100, Math.max(0, rsi))}%`;
    }
  }
}

function updateSignalCard(sig) {
  const actionBadge = document.getElementById('val-signal-action');
  const action = sig.action || 'HOLD';
  actionBadge.textContent = action;
  actionBadge.className = `signal-badge ${action.toLowerCase()}`;

  document.getElementById('signal-reason-text').textContent = sig.reason || 'Analyzing market trend...';
  const confPct = Math.round((sig.confidence || 0) * 100);
  document.getElementById('signal-confidence').textContent = `${confPct}% CONFIDENCE`;
}

function prependTradeRow(t) {
  const tbody = document.getElementById('trades-table-body');
  if (!tbody) return;

  const emptyRow = tbody.querySelector('.empty-row');
  if (emptyRow) emptyRow.remove();

  const tr = document.createElement('tr');
  const d = new Date(t.timestamp || Date.now());
  const timeStr = d.toTimeString().split(' ')[0];

  const sideClass = t.side === 'BUY' ? 'buy' : 'sell';
  let pnlCell = '---';
  if (t.realized_pnl !== undefined) {
    const sign = t.realized_pnl >= 0 ? '+' : '';
    const pnlClass = t.realized_pnl >= 0 ? 'success' : 'danger';
    pnlCell = `<span class="${pnlClass}">${sign}$${t.realized_pnl.toFixed(2)} (${sign}${t.realized_pnl_pct}%)</span>`;
  }

  tr.innerHTML = `
    <td>${timeStr}</td>
    <td><span class="trade-side-badge ${sideClass}">${t.side}</span></td>
    <td>$${formatCurrency(t.price)}</td>
    <td>${pnlCell}</td>
  `;

  tbody.insertBefore(tr, tbody.firstChild);
  while (tbody.children.length > 20) {
    tbody.removeChild(tbody.lastChild);
  }
}

function renderTradesTable(trades) {
  const tbody = document.getElementById('trades-table-body');
  if (!tbody) return;

  if (trades.length === 0) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="4">No trades executed yet.</td></tr>';
    return;
  }

  tbody.innerHTML = '';
  trades.forEach(t => prependTradeRow(t));
}

function appendLog(log) {
  state.allLogs.unshift(log);
  if (state.allLogs.length > 150) state.allLogs.pop();
  renderLogs();
}

function renderLogs() {
  const container = document.getElementById('terminal-log-stream');
  if (!container) return;

  const filter = state.logFilter;
  const filtered = state.allLogs.filter(l => {
    if (filter === 'ALL') return true;
    return l.level === filter;
  });

  document.getElementById('terminal-count').textContent = `${filtered.length} logs`;

  container.innerHTML = filtered.map(l => `
    <div class="log-line">
      <span class="log-time">${l.time}</span>
      <span class="log-badge ${l.level}">${l.level}</span>
      <span class="log-msg">${escapeHtml(l.message)}</span>
    </div>
  `).join('');
}

// ==========================================================================
// CONTROLS & EVENT LISTENERS
// ==========================================================================
function setupEventListeners() {
  // Test Buy Button (Instant Execution Test)
  const btnTestBuy = document.getElementById('btn-test-buy');
  if (btnTestBuy) {
    btnTestBuy.addEventListener('click', async () => {
      initAudio();
      btnTestBuy.disabled = true;
      btnTestBuy.style.opacity = '0.6';
      try {
        await fetch('/api/bot/manual-buy', { method: 'POST' });
      } catch (err) {
        console.error('Test buy failed:', err);
      } finally {
        setTimeout(() => {
          btnTestBuy.disabled = false;
          btnTestBuy.style.opacity = '1';
        }, 1200);
      }
    });
  }

  // Bot Start/Pause Button
  const btnToggle = document.getElementById('btn-bot-toggle');
  btnToggle.addEventListener('click', async () => {
    initAudio();
    if (state.status === 'RUNNING') {
      await fetch('/api/bot/stop', { method: 'POST' });
      state.status = 'PAUSED';
      state.isRunning = false;
    } else {
      await fetch('/api/bot/start', { method: 'POST' });
      state.status = 'RUNNING';
      state.isRunning = true;
    }
    updateBotButton(state.status);
  });

  // Panic Button
  const btnPanic = document.getElementById('btn-panic');
  btnPanic.addEventListener('click', async () => {
    initAudio();
    if (confirm('🚨 EMERGENCY PANIC:\n\nLiquidate all open positions at market price and halt trading?')) {
      await fetch('/api/bot/panic', { method: 'POST' });
      state.status = 'PAUSED';
      state.isRunning = false;
      updateBotButton(state.status);
    }
  });

  // Pair Dropdown Change
  const pairSelect = document.getElementById('pair-select');
  pairSelect.addEventListener('change', async e => {
    const symbol = e.target.value;
    state.symbol = symbol;
    document.getElementById('hud-symbol').textContent = symbol;
    await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol })
    });
  });

  // Timeframe Pills
  document.querySelectorAll('.tf-btn').forEach(btn => {
    btn.addEventListener('click', async e => {
      document.querySelectorAll('.tf-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const tf = btn.dataset.tf;
      state.timeframe = tf;
      await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ timeframe: tf })
      });
    });
  });

  // Sliders Live Value Updates
  const inputAmount = document.getElementById('input-trade-amount');
  inputAmount.addEventListener('input', e => {
    document.getElementById('val-trade-amount-disp').textContent = `$${e.target.value}`;
  });

  const inputSL = document.getElementById('input-stop-loss');
  inputSL.addEventListener('input', e => {
    document.getElementById('val-stop-loss-disp').textContent = `-${parseFloat(e.target.value).toFixed(1)}%`;
  });

  const inputTP = document.getElementById('input-take-profit');
  inputTP.addEventListener('input', e => {
    document.getElementById('val-take-profit-disp').textContent = `+${parseFloat(e.target.value).toFixed(1)}%`;
  });

  // Apply Settings Button
  const btnApply = document.getElementById('btn-apply-settings');
  btnApply.addEventListener('click', async () => {
    const payload = {
      active_strategy: document.getElementById('strategy-select').value,
      trade_amount_usdt: parseFloat(inputAmount.value) || 500,
      stop_loss_pct: parseFloat(inputSL.value) || 1.5,
      take_profit_pct: parseFloat(inputTP.value) || 3.0,
      trailing_stop_enabled: document.getElementById('check-trailing-stop').checked
    };

    btnApply.textContent = 'Applying...';
    try {
      await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      btnApply.textContent = '✓ Parameters Applied!';
      setTimeout(() => { btnApply.textContent = 'Apply Strategy Parameters'; }, 1600);
    } catch (e) {
      btnApply.textContent = 'Error Applying';
    }
  });

  // Reset Paper Wallet Button
  const btnReset = document.getElementById('btn-reset-wallet');
  btnReset.addEventListener('click', async () => {
    if (confirm('Reset simulated wallet back to $10,000.00 USDT and clear trade history?')) {
      await fetch('/api/bot/reset-paper', { method: 'POST' });
    }
  });

  // Sound Toggle Button
  const btnSound = document.getElementById('btn-sound-toggle');
  btnSound.addEventListener('click', () => {
    state.soundEnabled = !state.soundEnabled;
    btnSound.classList.toggle('active', state.soundEnabled);
    if (state.soundEnabled) {
      initAudio();
      playTradeSound('BUY');
    }
  });

  // Terminal Log Filters
  document.querySelectorAll('.log-filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.log-filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.logFilter = btn.dataset.filter;
      renderLogs();
    });
  });

  // Terminal Collapse Toggle
  const btnToggleTerminal = document.getElementById('btn-toggle-terminal');
  btnToggleTerminal.addEventListener('click', () => {
    const body = document.getElementById('terminal-log-stream');
    body.classList.toggle('collapsed');
  });

  // Settings Modal Controls
  const modal = document.getElementById('settings-modal');
  const btnOpenModal = document.getElementById('btn-open-settings');
  const btnCloseModal = document.getElementById('btn-close-modal');
  const btnCancelModal = document.getElementById('btn-cancel-modal');
  const btnSaveModal = document.getElementById('btn-save-modal');

  btnOpenModal.addEventListener('click', () => modal.classList.remove('hidden'));
  btnCloseModal.addEventListener('click', () => modal.classList.add('hidden'));
  btnCancelModal.addEventListener('click', () => modal.classList.add('hidden'));

  // Environment Mode Switcher inside modal
  const btnEnvPaper = document.getElementById('tab-env-paper');
  const btnEnvTestnet = document.getElementById('tab-env-testnet');
  const testnetBox = document.getElementById('testnet-credentials-box');

  btnEnvPaper.addEventListener('click', () => {
    btnEnvPaper.classList.add('active');
    btnEnvTestnet.classList.remove('active');
    testnetBox.classList.add('hidden');
    state.mode = 'PAPER';
  });

  btnEnvTestnet.addEventListener('click', () => {
    btnEnvTestnet.classList.add('active');
    btnEnvPaper.classList.remove('active');
    testnetBox.classList.remove('hidden');
    state.mode = 'BINANCE_TESTNET';
  });

  btnSaveModal.addEventListener('click', async () => {
    const payload = {
      mode: state.mode,
      binance_testnet: {
        api_key: document.getElementById('testnet-api-key').value.trim(),
        api_secret: document.getElementById('testnet-api-secret').value.trim()
      }
    };
    await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    updateModeBadge(state.mode);
    modal.classList.add('hidden');
  });
}

function updateBotButton(status) {
  const btn = document.getElementById('btn-bot-toggle');
  const text = document.getElementById('bot-toggle-text');
  if (status === 'RUNNING') {
    btn.className = 'btn btn-pause';
    text.textContent = 'PAUSE BOT';
  } else {
    btn.className = 'btn btn-start';
    text.textContent = 'START BOT';
  }
}

function updateModeBadge(mode) {
  const badge = document.getElementById('mode-badge');
  const text = document.getElementById('mode-text');
  if (mode === 'BINANCE_TESTNET') {
    badge.className = 'mode-badge testnet';
    text.textContent = 'BINANCE TESTNET';
  } else {
    badge.className = 'mode-badge paper';
    text.textContent = 'PAPER SIMULATOR';
  }
}

function updateLivePulse(connected) {
  const dot = document.querySelector('.radar-dot');
  if (dot) {
    dot.style.background = connected ? 'var(--accent-cyan)' : 'var(--accent-crimson)';
    dot.style.boxShadow = connected ? '0 0 10px var(--accent-cyan)' : '0 0 10px var(--accent-crimson)';
  }
}

// Helpers
function formatNumber(num) {
  return Number(num || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatCurrency(num) {
  const n = Number(num || 0);
  if (n < 1.0) return n.toFixed(4);
  return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function escapeHtml(str) {
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// Initialize on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  initChart();
  setupEventListeners();
  connectWebSocket();
});
