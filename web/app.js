/**
 * NEPTUNE TRADER // Autonomous Quantitative Trading Fleet Terminal
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
    console.log('[WS] Connected to Neptune Trading Engine.');
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

    case 'RADAR_SCAN_PULSE':
      updateDayTraderSuite(msg.data);
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
  state.watchlist = data.watchlist || [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT",
    "SUI/USDT", "DOGE/USDT", "XRP/USDT", "PEPE/USDT"
  ];
  state.prices = data.prices || {};
  state.timeframe = data.timeframe;
  state.activeStrategy = data.active_strategy;
  state.currentPrice = data.current_price;

  // Render Top Watchlist Ticker Tape
  renderWatchlistTape(state.watchlist, state.prices, state.symbol, data.portfolio?.active_positions || []);

  // Sync Top Controls & Custom Pair Option
  const pairSelect = document.getElementById('pair-select');
  if (pairSelect && data.symbol) {
    let exists = false;
    for (let i = 0; i < pairSelect.options.length; i++) {
      if (pairSelect.options[i].value === data.symbol) {
        exists = true;
        break;
      }
    }
    if (!exists) {
      const opt = document.createElement('option');
      opt.value = data.symbol;
      opt.textContent = `${data.symbol} — Custom`;
      pairSelect.appendChild(opt);
    }
    pairSelect.value = data.symbol;
  }

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
  if (cfg.binance_testnet) {
    if (cfg.binance_testnet.api_key) document.getElementById('testnet-api-key').value = cfg.binance_testnet.api_key;
    if (cfg.binance_testnet.api_secret) document.getElementById('testnet-api-secret').value = cfg.binance_testnet.api_secret;
  }
  if (cfg.binance_live) {
    if (cfg.binance_live.api_key) document.getElementById('live-api-key').value = cfg.binance_live.api_key;
    if (cfg.binance_live.api_secret) document.getElementById('live-api-secret').value = cfg.binance_live.api_secret;
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
  if (data.day_trader_suite) {
    updateDayTraderSuite(data.day_trader_suite);
  }

  // Logs
  if (data.logs && Array.isArray(data.logs)) {
    state.allLogs = data.logs;
    renderLogs();
  }
}

function handleTickerUpdate(data) {
  // Update multi-coin prices map
  if (data.prices) {
    state.prices = { ...state.prices, ...data.prices };
    for (const [sym, px] of Object.entries(data.prices)) {
      const base = sym.split('/')[0];
      const el = document.getElementById(`tape-px-${base}`);
      if (el) el.textContent = `$${formatCurrency(px)}`;
    }
  }

  // If this tick belongs to currently displayed chart symbol
  const isCurrent = data.symbol === state.symbol || (data.active_symbol && data.active_symbol === state.symbol);
  if (isCurrent && data.price > 0) {
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
  }

  // Update Portfolio Equity & Positions Basket in real time
  if (data.portfolio) {
    updatePortfolioUI(data.portfolio);
  }

  // Update Live Market Trends as price ticks
  if (data.market_trends && isCurrent) {
    updateMarketTrendsUI(data.market_trends);
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
  const positionsVal = p.total_positions_value || (p.active_position ? p.active_position.market_value : 0);
  const allocPct = Math.min(100, Math.max(0, (positionsVal / totalVal) * 100));
  document.getElementById('allocation-bar-fill').style.width = `${allocPct.toFixed(1)}%`;
  document.getElementById('allocation-pct-label').textContent = `${allocPct.toFixed(1)}% in Basket`;

  const activePositions = p.active_positions || (p.active_position ? [p.active_position] : []);
  const basketCount = activePositions.length;
  const maxSlots = 5;

  const assetBase = state.symbol.split('/')[0];
  document.getElementById('asset-holding-label').textContent = `${basketCount} Coins Held`;

  // Active Basket Card (Card 3)
  const posBadge = document.getElementById('pos-status-badge');
  const posPnlDisp = document.getElementById('pos-pnl-display');
  const posPnlPct = document.getElementById('pos-pnl-pct');
  const posDetails = document.getElementById('pos-details-text');
  const chipsContainer = document.getElementById('positions-chips-container');

  if (basketCount > 0) {
    posBadge.textContent = `${basketCount} / ${maxSlots} ACTIVE`;
    posBadge.className = 'pos-badge long';

    const totalUnrealizedPnl = activePositions.reduce((sum, x) => sum + (x.unrealized_pnl || 0), 0);
    const totalCost = activePositions.reduce((sum, x) => sum + (x.cost_usdt || 0), 0);
    const totalUnrealizedPct = totalCost > 0 ? (totalUnrealizedPnl / totalCost) * 100 : 0;

    const pSign = totalUnrealizedPnl >= 0 ? '+' : '';
    posPnlDisp.textContent = `${pSign}$${totalUnrealizedPnl.toFixed(2)}`;
    posPnlPct.textContent = `(${pSign}${totalUnrealizedPct.toFixed(2)}%)`;

    const posClass = totalUnrealizedPnl >= 0 ? 'profit' : 'loss';
    posPnlDisp.className = `metric-value mono ${posClass}`;
    posPnlPct.className = `pos-pnl-pct mono ${posClass}`;

    posDetails.innerHTML = `Basket Value: <strong>$${formatNumber(positionsVal)}</strong> in <strong>${basketCount}</strong> coins`;

    if (chipsContainer) {
      chipsContainer.innerHTML = activePositions.map(pos => {
        const s = pos.unrealized_pnl >= 0 ? '+' : '';
        return `<span class="pos-chip ${pos.unrealized_pnl >= 0 ? 'profit' : 'loss'}" onclick="switchMarket('${pos.symbol}')" title="Click to view chart">${pos.symbol.split('/')[0]}: ${s}$${pos.unrealized_pnl.toFixed(1)}</span>`;
      }).join('');
    }
  } else {
    posBadge.textContent = `0 / ${maxSlots} SLOTS`;
    posBadge.className = 'pos-badge none';
    posPnlDisp.textContent = '$0.00';
    posPnlPct.textContent = '(0.00%)';
    posPnlDisp.className = 'metric-value mono neutral';
    posPnlPct.className = 'pos-pnl-pct mono neutral';
    posDetails.textContent = 'Fleet scanning 8 high-volume coins';
    if (chipsContainer) chipsContainer.innerHTML = '';
  }

  // Update Basket Tray Section
  renderBasketTray(activePositions, positionsVal);

  // Update Top Watchlist Tape
  renderWatchlistTape(state.watchlist || [], state.prices || {}, state.symbol, activePositions);

  // Populate recent trades table if available
  if (p.recent_trades && Array.isArray(p.recent_trades)) {
    renderTradesTable(p.recent_trades);
  }
}

function renderBasketTray(activePositions, totalValue) {
  const badge = document.getElementById('basket-count-badge');
  if (badge) badge.textContent = activePositions.length;

  const eqTag = document.getElementById('basket-equity-tag');
  if (eqTag) eqTag.textContent = `ALLOCATED: $${formatNumber(totalValue)}`;

  const container = document.getElementById('basket-grid-container');
  if (!container) return;

  if (activePositions.length === 0) {
    container.innerHTML = `
      <div class="basket-empty-state">
        <span>No open coin positions. The fleet is actively watching top volume coins and will auto-enter on high-probability setups.</span>
      </div>
    `;
    return;
  }

  container.innerHTML = activePositions.map(pos => {
    const pnlSign = pos.unrealized_pnl >= 0 ? '+' : '';
    const pnlClass = pos.unrealized_pnl >= 0 ? 'profit' : 'loss';
    return `
      <div class="basket-coin-card">
        <div class="basket-coin-header">
          <span class="basket-coin-symbol" onclick="switchMarket('${pos.symbol}')" style="cursor:pointer;" title="Click to view chart">
            🪙 ${pos.symbol}
            <span class="basket-coin-tag">LONG</span>
          </span>
          <button class="basket-btn-close" onclick="closePosition('${pos.symbol}')" title="Close this position">Close</button>
        </div>
        <div class="basket-coin-body">
          <span class="basket-coin-pnl ${pnlClass}">
            ${pnlSign}$${pos.unrealized_pnl.toFixed(2)} (${pnlSign}${pos.unrealized_pnl_pct.toFixed(2)}%)
          </span>
          <span class="mono font-bold" style="font-size:12px; color:#fff;">$${formatCurrency(pos.current_price)}</span>
        </div>
        <div class="basket-coin-details">
          <span>Entry: $${formatCurrency(pos.entry_price)}</span>
          <span>Cost: $${pos.cost_usdt.toFixed(1)}</span>
        </div>
      </div>
    `;
  }).join('');
}

function renderWatchlistTape(watchlist, prices, activeSymbol, activePositions) {
  const container = document.getElementById('watchlist-tape-items');
  if (!container) return;

  const activeCoinsMap = {};
  if (Array.isArray(activePositions)) {
    activePositions.forEach(p => { activeCoinsMap[p.symbol] = p; });
  }

  container.innerHTML = watchlist.map(sym => {
    const px = prices[sym] || (sym === activeSymbol ? state.currentPrice : 0);
    const pxStr = px > 0 ? `$${formatCurrency(px)}` : '---';
    const isActive = sym === activeSymbol;
    const hasPos = Boolean(activeCoinsMap[sym]);
    const base = sym.split('/')[0];

    return `
      <div class="tape-coin-pill ${isActive ? 'active' : ''} ${hasPos ? 'has-position' : ''}" onclick="switchMarket('${sym}')" title="Click to view ${sym} chart and radar">
        <span class="tape-coin-symbol">${base}</span>
        <span class="tape-coin-price mono" id="tape-px-${base}">${pxStr}</span>
        ${hasPos ? '<span class="tape-coin-badge">HELD</span>' : ''}
      </div>
    `;
  }).join('');
}

async function switchMarket(symbol) {
  try {
    state.symbol = symbol;
    const pairSelect = document.getElementById('pair-select');
    if (pairSelect) pairSelect.value = symbol;

    const res = await fetch('/api/market/switch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol })
    });
    const data = await res.json();
    console.log('[Market] Switched to:', data.symbol);
  } catch (err) {
    console.error('Failed to switch market:', err);
  }
}

async function closePosition(symbol) {
  try {
    const res = await fetch('/api/bot/close-position', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol })
    });
    const data = await res.json();
    console.log('[Position] Closed:', data.symbol);
  } catch (err) {
    console.error('Failed to close position:', err);
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

function updateDayTraderSuite(suite) {
  if (!suite) return;

  // 1. Update Setups Radar List
  const container = document.getElementById('setups-container');
  if (container && suite.setups) {
    const defaultSetups = [
      { setup: "ORB_BREAKOUT", name: "Opening Range Breakout", badge: "ORB", idle: "Awaiting 15m Range" },
      { setup: "BULL_FLAG", name: "Bull Flag Momentum", badge: "FLAG", idle: "Scanning Channel" },
      { setup: "OVERSOLD_BOUNCE", name: "Oversold RSI Bounce", badge: "BOUNCE", idle: "RSI > 30 (Normal)" },
      { setup: "RECLAIM_MA20", name: "20-MA Support Reclaim", badge: "RECLAIM", idle: "Tracking 20 SMA" }
    ];

    container.innerHTML = defaultSetups.map(def => {
      const active = suite.setups.find(s => s.setup === def.setup && s.active);
      const isAct = Boolean(active);
      const statusText = active ? active.detail : def.idle;
      const statusClass = isAct ? 'active' : 'idle';
      const itemClass = isAct ? 'setup-item active-setup' : 'setup-item';

      return `
        <div class="${itemClass}">
          <div class="setup-meta">
            <span class="setup-badge ${def.badge.toLowerCase()}">${def.badge}</span>
            <span class="setup-name">${def.name}</span>
          </div>
          <span class="setup-status ${statusClass}">${statusText}</span>
        </div>
      `;
    }).join('');
  }

  // 2. Update Time Machine Monte Carlo Panel
  if (suite.timemachine) {
    const tm = suite.timemachine;
    document.getElementById('tm-target-pct').textContent = `${tm.target_first_pct}%`;
    document.getElementById('tm-stop-pct').textContent = `${tm.stop_first_pct}%`;
    document.getElementById('tm-target-fill').style.width = `${tm.target_first_pct}%`;
    document.getElementById('tm-stop-fill').style.width = `${tm.stop_first_pct}%`;

    const expR = tm.expected_r >= 0 ? `+${tm.expected_r.toFixed(2)}R` : `${tm.expected_r.toFixed(2)}R`;
    const expEl = document.getElementById('tm-expected-r');
    expEl.textContent = expR;
    expEl.className = 'tm-stat-val mono ' + (tm.expected_r >= 0 ? 'success' : 'danger');

    const vBadge = document.getElementById('tm-verdict-badge');
    vBadge.textContent = tm.verdict;
    if (tm.verdict.includes('FAVORABLE')) vBadge.className = 'verdict-badge favorable';
    else if (tm.verdict.includes('POOR')) vBadge.className = 'verdict-badge poor';
    else vBadge.className = 'verdict-badge coinflip';
  }

  // 3. Update Bracket Plan
  if (suite.plan) {
    const plan = suite.plan;
    document.getElementById('plan-entry-price').textContent = `$${formatCurrency(plan.entry_price)}`;
    document.getElementById('plan-stop-price').textContent = `$${formatCurrency(plan.stop_loss)}`;
    document.getElementById('plan-target-price').textContent = `$${formatCurrency(plan.take_profit)}`;
    document.getElementById('plan-rr-ratio').textContent = `${plan.reward_risk_ratio.toFixed(2)}R`;
  }

  // 4. Update Bot Fleet Status Matrix (Diagnostic Feedback)
  if (suite.fleet_status && Array.isArray(suite.fleet_status)) {
    updateFleetMatrix(suite.fleet_status);
  }

  // 5. Update Live Market Trends & Flow
  if (suite.market_trends) {
    updateMarketTrendsUI(suite.market_trends);
  }

  // 6. Update Time Machine Animated Canvas Data
  if (suite.timemachine) {
    updateTimeMachineData(suite.timemachine);
  }
}

function updateFleetMatrix(fleetStatus) {
  if (!fleetStatus || !Array.isArray(fleetStatus)) return;
  fleetStatus.forEach(bot => {
    const card = document.getElementById(`bot-card-${bot.id}`);
    const fb = document.getElementById(`fb-${bot.id}`);
    const st = document.getElementById(`st-${bot.id}`);
    const act = document.getElementById(`act-${bot.id}`);

    if (fb && bot.feedback) {
      fb.textContent = bot.feedback;
    }

    if (st && bot.status) {
      st.textContent = bot.status;
      const stLower = bot.status.toLowerCase();
      st.className = `bot-status-pill ${stLower}`;
    }

    if (act && bot.signal) {
      act.textContent = bot.signal;
      const actLower = bot.signal.toLowerCase();
      act.className = `bot-action-pill ${actLower}`;
    }

    if (card) {
      card.classList.remove('active-trade-buy', 'active-trade-sell');
      if (bot.signal === 'BUY') {
        card.classList.add('active-trade-buy');
      } else if (bot.signal === 'SELL') {
        card.classList.add('active-trade-sell');
      }
    }
  });
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

  // Re-run Time Machine Button
  const btnRunTM = document.getElementById('btn-run-timemachine');
  if (btnRunTM) {
    btnRunTM.addEventListener('click', async () => {
      btnRunTM.textContent = 'Simulating...';
      try {
        const res = await fetch('/api/bot/time-machine/run', { method: 'POST' });
        const d = await res.json();
        if (d.success) {
          updateDayTraderSuite(d);
        }
      } catch (e) {
        console.error('Time machine run failed:', e);
      } finally {
        setTimeout(() => { btnRunTM.textContent = 'Re-run'; }, 800);
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
  if (pairSelect) {
    pairSelect.addEventListener('change', async e => {
      const symbol = e.target.value;
      await switchMarket(symbol);
    });
  }

  // Custom Pair Modal
  const btnCustomPair = document.getElementById('btn-custom-pair');
  const customPairModal = document.getElementById('custom-pair-modal');
  const btnClosePairModal = document.getElementById('btn-close-pair-modal');
  const btnCancelPairModal = document.getElementById('btn-cancel-pair-modal');
  const btnLoadCustomPair = document.getElementById('btn-load-custom-pair');
  const inputCustomSymbol = document.getElementById('input-custom-symbol');

  if (btnCustomPair && customPairModal) {
    btnCustomPair.addEventListener('click', () => {
      customPairModal.classList.remove('hidden');
      if (inputCustomSymbol) inputCustomSymbol.focus();
    });

    const closePairModal = () => customPairModal.classList.add('hidden');
    if (btnClosePairModal) btnClosePairModal.addEventListener('click', closePairModal);
    if (btnCancelPairModal) btnCancelPairModal.addEventListener('click', closePairModal);

    if (btnLoadCustomPair && inputCustomSymbol) {
      btnLoadCustomPair.addEventListener('click', async () => {
        let rawSymbol = inputCustomSymbol.value.trim().toUpperCase();
        if (!rawSymbol) return;

        // Auto-format: if user inputs e.g. "SOLUSDT", convert to "SOL/USDT"
        if (!rawSymbol.includes('/') && rawSymbol.endsWith('USDT')) {
          rawSymbol = `${rawSymbol.slice(0, -4)}/USDT`;
        } else if (!rawSymbol.includes('/')) {
          rawSymbol = `${rawSymbol}/USDT`;
        }

        closePairModal();
        await switchMarket(rawSymbol);
      });

      inputCustomSymbol.addEventListener('keydown', e => {
        if (e.key === 'Enter') {
          btnLoadCustomPair.click();
        }
      });
    }
  }

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

  // Environment Mode Switcher inside modal (Paper, Testnet, Live)
  const btnEnvPaper = document.getElementById('tab-env-paper');
  const btnEnvTestnet = document.getElementById('tab-env-testnet');
  const btnEnvLive = document.getElementById('tab-env-live');
  const testnetBox = document.getElementById('testnet-credentials-box');
  const liveBox = document.getElementById('live-credentials-box');

  btnEnvPaper.addEventListener('click', () => {
    btnEnvPaper.classList.add('active');
    btnEnvTestnet.classList.remove('active');
    if (btnEnvLive) btnEnvLive.classList.remove('active');
    testnetBox.classList.add('hidden');
    if (liveBox) liveBox.classList.add('hidden');
    state.mode = 'PAPER';
  });

  btnEnvTestnet.addEventListener('click', () => {
    btnEnvTestnet.classList.add('active');
    btnEnvPaper.classList.remove('active');
    if (btnEnvLive) btnEnvLive.classList.remove('active');
    testnetBox.classList.remove('hidden');
    if (liveBox) liveBox.classList.add('hidden');
    state.mode = 'BINANCE_TESTNET';
  });

  if (btnEnvLive) {
    btnEnvLive.addEventListener('click', () => {
      btnEnvLive.classList.add('active');
      btnEnvPaper.classList.remove('active');
      btnEnvTestnet.classList.remove('active');
      testnetBox.classList.add('hidden');
      if (liveBox) liveBox.classList.remove('hidden');
      state.mode = 'BINANCE_LIVE';
    });
  }

  // Verify Binance Live API Keys Button
  const btnVerifyLive = document.getElementById('btn-verify-live-keys');
  const liveFeedback = document.getElementById('live-verify-feedback');
  if (btnVerifyLive) {
    btnVerifyLive.addEventListener('click', async () => {
      const apiKey = document.getElementById('live-api-key').value.trim();
      const apiSecret = document.getElementById('live-api-secret').value.trim();
      if (!apiKey || !apiSecret) {
        liveFeedback.className = 'verify-feedback error';
        liveFeedback.textContent = '⚠️ Please enter both API Key and Secret first.';
        return;
      }
      btnVerifyLive.disabled = true;
      liveFeedback.className = 'verify-feedback';
      liveFeedback.textContent = 'Connecting to Binance Spot API...';
      try {
        const resp = await fetch('/api/binance/validate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ api_key: apiKey, api_secret: apiSecret, is_testnet: false })
        });
        const res = await resp.json();
        if (res.valid) {
          liveFeedback.className = 'verify-feedback success';
          liveFeedback.textContent = `✓ Connected! Spot Balance: $${res.usdt_balance.toFixed(2)} USDT`;
        } else {
          liveFeedback.className = 'verify-feedback error';
          liveFeedback.textContent = `✕ Failed: ${res.error}`;
        }
      } catch (err) {
        liveFeedback.className = 'verify-feedback error';
        liveFeedback.textContent = '✕ Network error verifying keys.';
      } finally {
        btnVerifyLive.disabled = false;
      }
    });
  }

  btnSaveModal.addEventListener('click', async () => {
    const payload = {
      mode: state.mode,
      binance_testnet: {
        api_key: document.getElementById('testnet-api-key').value.trim(),
        api_secret: document.getElementById('testnet-api-secret').value.trim()
      },
      binance_live: {
        api_key: document.getElementById('live-api-key').value.trim(),
        api_secret: document.getElementById('live-api-secret').value.trim()
      }
    };
    await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    updateModeBadge(state.mode);
    modal.classList.add('hidden');
    appendLog({
      time: new Date().toLocaleTimeString(),
      level: 'INFO',
      message: `Trading environment updated to [${state.mode}]`
    });
  });

  // 24-Hour Performance Report Modal & CSV Controls
  const reportModal = document.getElementById('daily-report-modal');
  const btnOpenReport = document.getElementById('btn-open-report');
  const btnCloseReportModal = document.getElementById('btn-close-report-modal');
  const btnCloseReport = document.getElementById('btn-close-report');
  const btnDownloadCsv = document.getElementById('btn-download-csv');
  const btnDownloadReportCsv = document.getElementById('btn-download-report-csv');
  const btnStep2Transition = document.getElementById('btn-step2-transition');

  if (btnOpenReport && reportModal) {
    btnOpenReport.addEventListener('click', async () => {
      await refreshDailyReportModal();
      reportModal.classList.remove('hidden');
    });
  }

  const closeReportModal = () => {
    if (reportModal) reportModal.classList.add('hidden');
  };
  if (btnCloseReportModal) btnCloseReportModal.addEventListener('click', closeReportModal);
  if (btnCloseReport) btnCloseReport.addEventListener('click', closeReportModal);

  // CSV Audit Log Downloads
  const downloadTradesCsv = () => {
    window.location.href = '/api/reports/trades.csv';
  };
  if (btnDownloadCsv) btnDownloadCsv.addEventListener('click', downloadTradesCsv);
  if (btnDownloadReportCsv) btnDownloadReportCsv.addEventListener('click', downloadTradesCsv);

  // Transition to Real Money Step 2 Button
  if (btnStep2Transition) {
    btnStep2Transition.addEventListener('click', () => {
      closeReportModal();
      modal.classList.remove('hidden');
      if (btnEnvLive) btnEnvLive.click();
    });
  }

  // Periodic 25-second poll to keep session duration time updated
  setInterval(async () => {
    const data = await fetchDailyReport();
    if (data && data.session_duration_str) {
      const sessEl = document.getElementById('session-time-display');
      if (sessEl) sessEl.textContent = data.session_duration_str;
    }
  }, 25000);
  // Initial immediate fetch
  fetchDailyReport().then(d => {
    if (d && d.session_duration_str) {
      const sessEl = document.getElementById('session-time-display');
      if (sessEl) sessEl.textContent = d.session_duration_str;
    }
  });
}

async function fetchDailyReport() {
  try {
    const res = await fetch('/api/reports/daily-summary');
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    return null;
  }
}

async function refreshDailyReportModal() {
  const data = await fetchDailyReport();
  if (!data) return;

  const sessStr = data.session_duration_str || '0h 0m';
  const sessEl = document.getElementById('session-time-display');
  if (sessEl) sessEl.textContent = sessStr;
  const repDurEl = document.getElementById('rep-duration');
  if (repDurEl) repDurEl.textContent = sessStr;

  // Net realized PnL
  const pnlEl = document.getElementById('rep-pnl');
  const pnlPctEl = document.getElementById('rep-pnl-pct');
  const sign = data.total_realized_pnl >= 0 ? '+' : '';
  const pnlClass = data.total_realized_pnl >= 0 ? 'success' : 'danger';
  if (pnlEl) {
    pnlEl.textContent = `${sign}$${data.total_realized_pnl.toFixed(2)}`;
    pnlEl.className = `r-stat-val mono ${pnlClass}`;
  }
  if (pnlPctEl) {
    pnlPctEl.textContent = `${sign}${data.total_pnl_pct.toFixed(2)}%`;
    pnlPctEl.className = `r-stat-sub ${pnlClass}`;
  }

  // Win rate & trades
  const wrEl = document.getElementById('rep-winrate');
  if (wrEl) wrEl.textContent = `${data.win_rate_pct.toFixed(1)}%`;
  const tcEl = document.getElementById('rep-trades-count');
  if (tcEl) tcEl.textContent = `${data.closed_trades_count} Closed Trades (${data.winning_trades_count}W / ${data.losing_trades_count}L)`;

  // Profit Factor & Max DD
  const pfEl = document.getElementById('rep-pf');
  if (pfEl) pfEl.textContent = data.profit_factor.toFixed(2);
  const ddEl = document.getElementById('rep-maxdd');
  if (ddEl) ddEl.textContent = `Max DD: ${data.max_drawdown_pct.toFixed(1)}%`;

  // Best & Worst Trades
  const bestEl = document.getElementById('rep-best-trade');
  if (bestEl) {
    if (data.best_trade) {
      const bt = data.best_trade;
      bestEl.innerHTML = `<span class="success">+$${bt.realized_pnl.toFixed(2)} (+${bt.realized_pnl_pct}%)</span> &bull; ${bt.quantity} ${bt.symbol} @ $${formatCurrency(bt.price)}<br><small style="color:var(--text-muted)">${bt.reason || 'Take-profit target'}</small>`;
    } else {
      bestEl.textContent = 'No closed trades yet';
    }
  }

  const worstEl = document.getElementById('rep-worst-trade');
  if (worstEl) {
    if (data.worst_trade) {
      const wt = data.worst_trade;
      const wtSign = wt.realized_pnl < 0 ? '-' : '+';
      worstEl.innerHTML = `<span class="danger">${wtSign}$${Math.abs(wt.realized_pnl).toFixed(2)} (${wt.realized_pnl_pct}%)</span> &bull; ${wt.quantity} ${wt.symbol} @ $${formatCurrency(wt.price)}<br><small style="color:var(--text-muted)">${wt.reason || 'Stop-loss exit'}</small>`;
    } else {
      worstEl.textContent = 'No closed trades yet';
    }
  }

  // Readiness banner
  const banner = document.getElementById('report-readiness-banner');
  const rIcon = document.getElementById('readiness-icon');
  const rTitle = document.getElementById('readiness-title');
  const rDesc = document.getElementById('readiness-desc');

  if (banner && rIcon && rTitle && rDesc) {
    if (data.ready_for_real_money) {
      banner.className = 'readiness-banner ready';
      rIcon.textContent = '🎉';
      rTitle.textContent = 'READY FOR REAL MONEY TRADING';
      rDesc.textContent = 'Your Neptune Bot fleet has maintained positive net returns and disciplined risk controls. You can safely proceed to Step 2 to trade real money on Binance Spot.';
    } else {
      banner.className = 'readiness-banner in-progress';
      rIcon.textContent = '⏳';
      rTitle.textContent = '24-HOUR BENCHMARK IN PROGRESS';
      rDesc.textContent = 'Autonomous paper trading is actively running. Let the bot trade uninterrupted for 24 hours to gather statistical validity before deploying real capital.';
    }
  }

  // Sub-bot Breakdown Table
  const tbody = document.getElementById('rep-breakdown-tbody');
  if (tbody && data.bot_breakdown) {
    const roles = {
      orb: "Breakout Scalper &bull; 15m Range Trigger",
      bull_flag: "Trend Continuation &bull; High-Volume Flag",
      oversold_bounce: "Mean Reversion &bull; RSI &lt; 30 Capitulation",
      reclaim_ma20: "Support Scalper &bull; 20-SMA Reclaim",
      ema_rsi: "Trend Master &bull; EMA 9/21 Momentum"
    };

    tbody.innerHTML = Object.entries(data.bot_breakdown).map(([k, b]) => {
      const winRate = b.trades > 0 ? ((b.wins / b.trades) * 100).toFixed(1) : "0.0";
      const pnlSign = b.pnl >= 0 ? "+" : "";
      const pnlClass = b.pnl >= 0 ? "success" : "danger";
      
      const weights = (data.learning_insights && data.learning_insights.weights) || {};
      const weight = weights[k] !== undefined ? weights[k] : 1.0;
      const weightClass = weight >= 1.15 ? 'boosted' : (weight <= 0.85 ? 'defensive' : 'normal');

      return `
        <tr>
          <td class="bot-name-cell">${b.name}</td>
          <td class="bot-role-cell">${roles[k] || ''}</td>
          <td class="mono">${b.trades}</td>
          <td class="mono">${winRate}% (${b.wins}W)</td>
          <td><span class="weight-badge ${weightClass}">${weight.toFixed(2)}x</span></td>
          <td class="mono ${pnlClass}">${pnlSign}$${b.pnl.toFixed(2)}</td>
        </tr>
      `;
    }).join('');
  }
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
  if (mode === 'BINANCE_LIVE') {
    badge.className = 'mode-badge live';
    text.textContent = 'BINANCE LIVE (REAL MONEY)';
  } else if (mode === 'BINANCE_TESTNET') {
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
  initTimeMachineCanvas();
  setupEventListeners();
  connectWebSocket();
});

// ==========================================================================
// ANIMATED TIME MACHINE CANVAS ENGINE (LIVE MONTE CARLO TRAJECTORIES)
// ==========================================================================
let tmCanvas = null;
let tmCtx = null;
let currentTmData = null;
let tmAnimFrame = 0;
let tmParticleOffset = 0;

function initTimeMachineCanvas() {
  tmCanvas = document.getElementById('timemachine-canvas');
  if (!tmCanvas) return;
  tmCtx = tmCanvas.getContext('2d');

  function resizeCanvas() {
    if (!tmCanvas || !tmCanvas.parentElement) return;
    const rect = tmCanvas.parentElement.getBoundingClientRect();
    if (rect.width > 0) {
      const dpr = window.devicePixelRatio || 1;
      tmCanvas.width = rect.width * dpr;
      tmCanvas.height = 230 * dpr;
      tmCanvas.style.width = `${rect.width}px`;
      tmCanvas.style.height = `230px`;
    }
  }

  window.addEventListener('resize', resizeCanvas);
  resizeCanvas();

  // 60 FPS Continuous Render Loop
  requestAnimationFrame(animateTimeMachineCanvas);
}

function updateTimeMachineData(tm) {
  if (!tm) return;
  currentTmData = tm;
}

function animateTimeMachineCanvas(timestamp) {
  tmAnimFrame++;
  tmParticleOffset = (timestamp * 0.05) % 100;

  drawTimeMachineCanvas();
  requestAnimationFrame(animateTimeMachineCanvas);
}

function drawTimeMachineCanvas() {
  if (!tmCanvas || !tmCtx) return;
  const ctx = tmCtx;
  const dpr = window.devicePixelRatio || 1;
  const width = tmCanvas.width;
  const height = tmCanvas.height;

  ctx.save();
  ctx.clearRect(0, 0, width, height);

  // Background
  const bgGrad = ctx.createLinearGradient(0, 0, 0, height);
  bgGrad.addColorStop(0, '#060a12');
  bgGrad.addColorStop(1, '#090e18');
  ctx.fillStyle = bgGrad;
  ctx.fillRect(0, 0, width, height);

  const padLeft = 45 * dpr;
  const padRight = 85 * dpr;
  const padTop = 26 * dpr;
  const padBottom = 26 * dpr;
  const plotWidth = width - padLeft - padRight;
  const plotHeight = height - padTop - padBottom;

  if (!currentTmData || !currentTmData.sample_paths || currentTmData.sample_paths.length === 0) {
    ctx.fillStyle = '#4a5568';
    ctx.font = `${11 * dpr}px 'JetBrains Mono', monospace`;
    ctx.textAlign = 'center';
    ctx.fillText('CALCULATING 1,000 MONTE CARLO TRAJECTORIES...', width / 2, height / 2);
    ctx.restore();
    return;
  }

  const tm = currentTmData;
  const livePrice = state.currentPrice > 0 ? state.currentPrice : (tm.entry_price || 80000);
  const entry = tm.entry_price || livePrice;
  const target = tm.target_price || (entry * 1.025);
  const stop = tm.stop_price || (entry * 0.985);

  let minP = stop * 0.995;
  let maxP = target * 1.005;

  if (tm.cone_bounds && tm.cone_bounds.p90 && tm.cone_bounds.p10) {
    minP = Math.min(minP, Math.min(...tm.cone_bounds.p10));
    maxP = Math.max(maxP, Math.max(...tm.cone_bounds.p90));
  }

  const priceRange = Math.max(0.01, maxP - minP);

  function priceToY(p) {
    return padTop + plotHeight - ((p - minP) / priceRange) * plotHeight;
  }

  const steps = tm.horizon_steps || 30;
  function stepToX(step) {
    return padLeft + (step / steps) * plotWidth;
  }

  // 1. Grid Lines & Time Markers
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
  ctx.lineWidth = 1 * dpr;
  ctx.setLineDash([4 * dpr, 4 * dpr]);

  ctx.fillStyle = 'rgba(255, 255, 255, 0.35)';
  ctx.font = `${9 * dpr}px 'JetBrains Mono', monospace`;
  ctx.textAlign = 'center';

  const timeIntervals = [0, 5, 10, 15, 20, 25, 30];
  timeIntervals.forEach(st => {
    const x = stepToX(st);
    ctx.beginPath();
    ctx.moveTo(x, padTop);
    ctx.lineTo(x, padTop + plotHeight);
    ctx.stroke();

    const label = st === 0 ? 'NOW' : `+${st}m`;
    ctx.fillText(label, x, height - 8 * dpr);
  });

  // 2. Stop Loss (1R) Line
  const stopY = priceToY(stop);
  ctx.strokeStyle = 'rgba(255, 51, 102, 0.75)';
  ctx.lineWidth = 1.5 * dpr;
  ctx.setLineDash([5 * dpr, 4 * dpr]);
  ctx.beginPath();
  ctx.moveTo(padLeft, stopY);
  ctx.lineTo(padLeft + plotWidth, stopY);
  ctx.stroke();

  ctx.fillStyle = '#ff3366';
  ctx.textAlign = 'left';
  ctx.font = `bold ${9 * dpr}px 'JetBrains Mono', monospace`;
  ctx.fillText(`1R: $${formatCurrency(stop)}`, padLeft + plotWidth + 6 * dpr, stopY + 3 * dpr);

  // 3. Take Profit (2R) Target Line
  const targetY = priceToY(target);
  ctx.strokeStyle = 'rgba(0, 245, 155, 0.75)';
  ctx.lineWidth = 1.5 * dpr;
  ctx.beginPath();
  ctx.moveTo(padLeft, targetY);
  ctx.lineTo(padLeft + plotWidth, targetY);
  ctx.stroke();

  ctx.fillStyle = '#00f59b';
  ctx.fillText(`2R: $${formatCurrency(target)}`, padLeft + plotWidth + 6 * dpr, targetY + 3 * dpr);

  // 4. Confidence Cone (P10 to P90 Cloud)
  ctx.setLineDash([]);
  if (tm.cone_bounds && tm.cone_bounds.p10 && tm.cone_bounds.p90) {
    const p10 = tm.cone_bounds.p10;
    const p90 = tm.cone_bounds.p90;

    ctx.beginPath();
    ctx.moveTo(stepToX(0), priceToY(entry));

    for (let s = 0; s <= steps && s < p90.length; s++) {
      ctx.lineTo(stepToX(s), priceToY(p90[s]));
    }
    for (let s = Math.min(steps, p10.length - 1); s >= 0; s--) {
      ctx.lineTo(stepToX(s), priceToY(p10[s]));
    }
    ctx.closePath();

    const coneGrad = ctx.createLinearGradient(padLeft, 0, padLeft + plotWidth, 0);
    coneGrad.addColorStop(0, 'rgba(0, 245, 212, 0.08)');
    coneGrad.addColorStop(0.5, 'rgba(67, 97, 238, 0.12)');
    coneGrad.addColorStop(1, 'rgba(0, 180, 216, 0.05)');
    ctx.fillStyle = coneGrad;
    ctx.fill();

    ctx.strokeStyle = 'rgba(0, 245, 212, 0.22)';
    ctx.lineWidth = 1 * dpr;
    ctx.stroke();
  }

  // 5. Draw Simulated Forward Pathways
  if (tm.sample_paths && Array.isArray(tm.sample_paths)) {
    tm.sample_paths.forEach((sp, idx) => {
      const pts = sp.points;
      if (!pts || pts.length === 0) return;

      ctx.beginPath();
      ctx.moveTo(stepToX(0), priceToY(pts[0]));

      for (let s = 1; s < pts.length; s++) {
        const prevX = stepToX(s - 1);
        const prevY = priceToY(pts[s - 1]);
        const currX = stepToX(s);
        const currY = priceToY(pts[s]);
        const cpX = (prevX + currX) / 2;
        ctx.quadraticCurveTo(cpX, prevY, currX, currY);
      }

      if (sp.type === 'target') {
        ctx.strokeStyle = 'rgba(0, 245, 155, 0.38)';
        ctx.lineWidth = 1.2 * dpr;
      } else if (sp.type === 'stop') {
        ctx.strokeStyle = 'rgba(255, 51, 102, 0.32)';
        ctx.lineWidth = 1.1 * dpr;
      } else {
        ctx.strokeStyle = 'rgba(76, 201, 240, 0.25)';
        ctx.lineWidth = 1 * dpr;
      }
      ctx.stroke();

      // Traveling animated particle
      const pathProgress = ((tmParticleOffset + idx * 8.5) % 100) / 100;
      const targetStep = Math.min(pts.length - 1, Math.floor(pathProgress * (pts.length - 1)));
      const nextStep = Math.min(pts.length - 1, targetStep + 1);
      const subProg = (pathProgress * (pts.length - 1)) - targetStep;

      const partX = stepToX(targetStep) + (stepToX(nextStep) - stepToX(targetStep)) * subProg;
      const partY = priceToY(pts[targetStep]) + (priceToY(pts[nextStep]) - priceToY(pts[targetStep])) * subProg;

      ctx.fillStyle = sp.type === 'target' ? '#00f59b' : (sp.type === 'stop' ? '#ff3366' : '#00f5d4');
      ctx.shadowColor = ctx.fillStyle;
      ctx.shadowBlur = 6 * dpr;
      ctx.beginPath();
      ctx.arc(partX, partY, 2 * dpr, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;
    });
  }

  // 6. Draw Central Median Path (P50)
  if (tm.cone_bounds && tm.cone_bounds.p50) {
    const p50 = tm.cone_bounds.p50;
    ctx.beginPath();
    ctx.moveTo(stepToX(0), priceToY(p50[0]));
    for (let s = 1; s < p50.length; s++) {
      const prevX = stepToX(s - 1);
      const prevY = priceToY(p50[s - 1]);
      const currX = stepToX(s);
      const currY = priceToY(p50[s]);
      ctx.quadraticCurveTo((prevX + currX) / 2, prevY, currX, currY);
    }
    ctx.strokeStyle = '#00f5d4';
    ctx.lineWidth = 2.2 * dpr;
    ctx.shadowColor = 'rgba(0, 245, 212, 0.85)';
    ctx.shadowBlur = 8 * dpr;
    ctx.stroke();
    ctx.shadowBlur = 0;
  }

  // 7. Live Origin Dot tracking live price
  const originX = stepToX(0);
  const originY = priceToY(livePrice);
  const haloR = 4 + 3 * Math.sin(tmAnimFrame * 0.08);

  ctx.strokeStyle = 'rgba(0, 245, 212, 0.45)';
  ctx.lineWidth = 1.5 * dpr;
  ctx.beginPath();
  ctx.arc(originX, originY, haloR * dpr, 0, Math.PI * 2);
  ctx.stroke();

  ctx.fillStyle = '#00f5d4';
  ctx.shadowColor = '#00f5d4';
  ctx.shadowBlur = 10 * dpr;
  ctx.beginPath();
  ctx.arc(originX, originY, 3.5 * dpr, 0, Math.PI * 2);
  ctx.fill();
  ctx.shadowBlur = 0;

  // Live Price Label
  ctx.fillStyle = '#fff';
  ctx.font = `bold ${10 * dpr}px 'JetBrains Mono', monospace`;
  ctx.textAlign = 'left';
  ctx.fillText(`NOW: $${formatCurrency(livePrice)}`, padLeft + plotWidth + 6 * dpr, originY + 3 * dpr);

  ctx.restore();
}

// ==========================================================================
// LIVE MARKET TRENDS & FLOW VISUALIZER
// ==========================================================================
function updateMarketTrendsUI(tr) {
  if (!tr) return;

  // Trend Badge Pill
  const badge = document.getElementById('trend-live-badge');
  if (badge && tr.trend_direction) {
    badge.textContent = tr.trend_direction;
    badge.className = `trend-badge-pill ${tr.trend_class || 'neutral'}`;
  }

  // Flow Meter Fill & Score
  const strengthVal = document.getElementById('trend-strength-val');
  if (strengthVal && tr.trend_strength_pct !== undefined) {
    strengthVal.textContent = `${tr.trend_strength_pct}%`;
  }

  const barFill = document.getElementById('trend-bar-fill');
  if (barFill && tr.trend_strength_pct !== undefined) {
    barFill.style.width = `${Math.min(100, Math.max(5, tr.trend_strength_pct))}%`;
  }

  // Multi-Timeframe Matrix (1m, 3m, 5m, 15m)
  if (tr.multi_timeframe && Array.isArray(tr.multi_timeframe)) {
    tr.multi_timeframe.forEach(item => {
      const cell = document.getElementById(`mtf-${item.tf}`);
      const arrow = document.getElementById(`mtf-arrow-${item.tf}`);
      const status = document.getElementById(`mtf-status-${item.tf}`);

      if (cell) cell.className = `mtf-cell ${item.class}`;
      if (arrow) arrow.textContent = item.trend === 'BULL' ? '▲' : (item.trend === 'BEAR' ? '▼' : '◆');
      if (status) status.textContent = item.trend;
    });
  }

  // Metrics: Volume Surge, EMA Spread, Volatility Regime
  if (tr.volume_surge_ratio !== undefined) {
    const volEl = document.getElementById('trend-vol-surge');
    if (volEl) {
      volEl.textContent = `${tr.volume_surge_ratio.toFixed(2)}x`;
      volEl.className = 'stat-data mono ' + (tr.volume_surge_ratio >= 1.2 ? 'success' : 'neutral');
    }
  }

  if (tr.ema_spread_usd !== undefined) {
    const spreadEl = document.getElementById('trend-ema-spread');
    if (spreadEl) {
      const sign = tr.ema_spread_usd >= 0 ? '+' : '';
      spreadEl.textContent = `${sign}$${tr.ema_spread_usd.toFixed(2)}`;
      spreadEl.className = 'stat-data mono ' + (tr.ema_spread_usd >= 0 ? 'success' : 'danger');
    }
  }

  if (tr.volatility_regime) {
    const regEl = document.getElementById('trend-vol-regime');
    if (regEl) {
      regEl.textContent = tr.volatility_regime.replace(' VOLATILITY', '').slice(0, 11);
    }
  }
}

