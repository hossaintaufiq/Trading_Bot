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
  chartMarkers: [],
  chartStyle: 'candles', // 'candles' | 'line'
  showEmaFast: true,
  showEmaSlow: true,
  showBrackets: true,
  watchlist: [],
  prices: {},
  activePositions: [],
  activeGraphView: 'price', // 'price' | 'equity' | 'subbots' | 'fleet'
  moneyManagement: null,
  equityHistory: [],
  allTrades: [],
  tmHorizon: 30,
  tmReplays: 1000,
  tmTargetMode: '2R',
  tmSymbol: 'BTC/USDT',
  tmViewMode: 'cone', // 'cone' | 'paths' | 'dist'
  tradeFilterOutcome: 'ALL',
  tradeFilterBot: 'ALL',
  tradeDetailsMode: 'normal',
  priceLines: {
    entry: null,
    tp: null,
    sl: null
  }
};

// Global Chart References
let chart = null;
let candleSeries = null;
let areaSeries = null;
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

  const getContainerWidth = () => {
    return Math.max(280, container.clientWidth || (container.parentElement ? container.parentElement.clientWidth : 0) || 600);
  };
  const getContainerHeight = () => {
    return Math.max(260, container.clientHeight || 520);
  };

  chart = LightweightCharts.createChart(container, {
    width: getContainerWidth(),
    height: getContainerHeight(),
    layout: {
      background: { type: 'solid', color: '#090d16' },
      textColor: '#94a3b8',
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: 11
    },
    grid: {
      vertLines: { color: 'rgba(255, 255, 255, 0.02)' },
      horzLines: { color: 'rgba(255, 255, 255, 0.02)' }
    },
    crosshair: {
      mode: LightweightCharts.CrosshairMode.Normal,
      vertLine: {
        color: 'rgba(56, 189, 248, 0.35)',
        width: 1,
        style: LightweightCharts.LineStyle.Dashed
      },
      horzLine: {
        color: 'rgba(56, 189, 248, 0.35)',
        width: 1,
        style: LightweightCharts.LineStyle.Dashed
      }
    },
    rightPriceScale: {
      borderColor: 'rgba(255, 255, 255, 0.06)',
      scaleMargins: { top: 0.1, bottom: 0.15 }
    },
    timeScale: {
      borderColor: 'rgba(255, 255, 255, 0.06)',
      timeVisible: true,
      secondsVisible: false
    }
  });

  // Candlestick Series (Ergonomic Emerald & Rose)
  candleSeries = chart.addSeries(LightweightCharts.CandlestickSeries, {
    upColor: '#10b981',
    downColor: '#f43f5e',
    borderVisible: false,
    wickUpColor: '#10b981',
    wickDownColor: '#f43f5e'
  });

  // Area Series (Smooth line & soft glow for line view)
  areaSeries = chart.addSeries(LightweightCharts.AreaSeries, {
    topColor: 'rgba(56, 189, 248, 0.28)',
    bottomColor: 'rgba(56, 189, 248, 0.01)',
    lineColor: '#38bdf8',
    lineWidth: 2,
    visible: false
  });

  // Fast EMA (9) - Sky Cyan
  emaFastSeries = chart.addSeries(LightweightCharts.LineSeries, {
    color: '#38bdf8',
    lineWidth: 2,
    title: 'EMA 9',
    crosshairMarkerVisible: false
  });

  // Slow EMA (21) - Indigo
  emaSlowSeries = chart.addSeries(LightweightCharts.LineSeries, {
    color: '#818cf8',
    lineWidth: 2,
    title: 'EMA 21',
    crosshairMarkerVisible: false
  });

  // Responsive Resize Observer with requestAnimationFrame Debouncing
  let resizeRaf = null;
  let lastChartW = 0;
  let lastChartH = 0;

  const performChartResize = (targetW, targetH) => {
    if (!chart || !container) return;
    const parentW = container.parentElement ? container.parentElement.clientWidth : 0;
    const w = Math.floor(targetW || container.clientWidth || parentW || 300);
    const h = Math.floor(targetH || container.clientHeight || 440);
    if (w > 0 && h > 0 && (Math.abs(w - lastChartW) > 1 || Math.abs(h - lastChartH) > 1)) {
      lastChartW = w;
      lastChartH = h;
      chart.applyOptions({ width: w, height: h });
    }
  };

  const resizeObserver = new ResizeObserver(entries => {
    if (!entries || entries.length === 0) return;
    const { width, height } = entries[0].contentRect;
    if (resizeRaf) cancelAnimationFrame(resizeRaf);
    resizeRaf = requestAnimationFrame(() => {
      performChartResize(width, height);
    });
  });
  resizeObserver.observe(container);

  // Fallback Window Resize Listener with RAF debouncing
  window.addEventListener('resize', () => {
    if (resizeRaf) cancelAnimationFrame(resizeRaf);
    resizeRaf = requestAnimationFrame(() => {
      performChartResize();
    });
  });
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

  state.activePositions = data.portfolio?.active_positions || (data.portfolio?.active_position ? [data.portfolio.active_position] : []);

  // Render Top Watchlist Ticker Tape & Chart Fleet Tabs
  renderWatchlistTape(state.watchlist, state.prices, state.symbol, state.activePositions);
  renderChartFleetTabs(state.watchlist, state.prices, state.symbol, state.activePositions);
  updateChartPositionBanner(state.symbol, state.activePositions);
  updateChartPriceLines(state.symbol, state.activePositions);

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
  const stratSelect = document.getElementById('strategy-select');
  if (stratSelect && data.active_strategy) stratSelect.value = data.active_strategy;

  const cfg = data.config || {};
  if (cfg.trade_amount_usdt) {
    const el = document.getElementById('input-trade-amount');
    if (el) el.value = cfg.trade_amount_usdt;
    const disp = document.getElementById('val-trade-amount-disp');
    if (disp) disp.textContent = `$${cfg.trade_amount_usdt}`;
  }
  if (cfg.stop_loss_pct) {
    const el = document.getElementById('input-stop-loss');
    if (el) el.value = cfg.stop_loss_pct;
    const disp = document.getElementById('val-stop-loss-disp');
    if (disp) disp.textContent = `-${cfg.stop_loss_pct}%`;
  }
  if (cfg.take_profit_pct) {
    const el = document.getElementById('input-take-profit');
    if (el) el.value = cfg.take_profit_pct;
    const disp = document.getElementById('val-take-profit-disp');
    if (disp) disp.textContent = `+${cfg.take_profit_pct}%`;
  }
  if (cfg.trailing_stop_enabled !== undefined) {
    const el = document.getElementById('check-trailing-stop');
    if (el) el.checked = cfg.trailing_stop_enabled;
  }
  if (cfg.binance_testnet) {
    const k = document.getElementById('testnet-api-key');
    if (k && cfg.binance_testnet.api_key) k.value = cfg.binance_testnet.api_key;
    const s = document.getElementById('testnet-api-secret');
    if (s && cfg.binance_testnet.api_secret) s.value = cfg.binance_testnet.api_secret;
  }
  if (cfg.binance_live) {
    const k = document.getElementById('live-api-key');
    if (k && cfg.binance_live.api_key) k.value = cfg.binance_live.api_key;
    const s = document.getElementById('live-api-secret');
    if (s && cfg.binance_live.api_secret) s.value = cfg.binance_live.api_secret;
  }

  // Populate Candles on Chart
  if (data.candles && data.candles.length > 0) {
    if (candleSeries) candleSeries.setData(data.candles);
    if (areaSeries) areaSeries.setData(data.candles.map(c => ({ time: c.time, value: c.close })));

    // Compute basic initial EMA series for chart lines
    const emaFastData = [];
    const emaSlowData = [];
    data.candles.forEach(c => {
      emaFastData.push({ time: c.time, value: c.close });
      emaSlowData.push({ time: c.time, value: c.close });
    });
    if (emaFastSeries) emaFastSeries.setData(emaFastData);
    if (emaSlowSeries) emaSlowSeries.setData(emaSlowData);
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
    if (data.portfolio.equity_history) {
      state.equityHistory = data.portfolio.equity_history;
      if (state.activeGraphView === 'equity') renderEquityCurveChart(state.equityHistory);
    }
    if (data.portfolio.recent_trades) {
      state.allTrades = data.portfolio.recent_trades;
      filterAndRenderTrades();
    }
  }

  // Money Management Engine Telemetry
  if (data.money_management) {
    updateMoneyManagementUI(data.money_management);
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
    if (data.candle) {
      if (candleSeries) candleSeries.update(data.candle);
      if (areaSeries) areaSeries.update({ time: data.candle.time, value: data.candle.close });
    }
  }

  // Update Portfolio Equity & Positions Basket in real time
  if (data.portfolio) {
    updatePortfolioUI(data.portfolio);
  } else if (state.activePositions && state.activePositions.length > 0) {
    updateChartPositionBanner(state.symbol, state.activePositions);
  }

  // Update Live Market Trends as price ticks
  if (data.market_trends && isCurrent) {
    updateMarketTrendsUI(data.market_trends);
  }

  // Update Fleet Radar live if currently visible
  if (state.activeGraphView === 'fleet') {
    renderFleetRadarChart();
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

  // Prepend trade to recent executions table and update internal trade store
  if (trade) {
    state.allTrades.unshift(trade);
    if (state.allTrades.length > 200) state.allTrades.pop();
    filterAndRenderTrades();
  }

  // Update Equity Chart if open
  if (data.portfolio) {
    updatePortfolioUI(data.portfolio);
    if (data.portfolio.equity_history) {
      state.equityHistory = data.portfolio.equity_history;
      if (state.activeGraphView === 'equity') renderEquityCurveChart(state.equityHistory);
    }
  }
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

  // Allocation Bar & Card 2 (Active Capital in Trades)
  const totalVal = p.total_equity > 0 ? p.total_equity : 10000;
  const positionsVal = p.total_positions_value || (p.active_position ? p.active_position.market_value : 0);
  const allocPct = Math.min(100, Math.max(0, (positionsVal / totalVal) * 100));
  document.getElementById('allocation-bar-fill').style.width = `${allocPct.toFixed(1)}%`;

  const activePositions = p.active_positions || (p.active_position ? [p.active_position] : []);
  const basketCount = activePositions.length;
  const maxSlots = 5;

  document.getElementById('allocation-pct-label').textContent = `${allocPct.toFixed(1)}% Allocated (${basketCount}/${maxSlots} Slots in Trade)`;
  document.getElementById('asset-holding-label').textContent = `${basketCount} COINS IN TRADE ($${formatCurrency(positionsVal)})`;

  // Active Basket Card (Card 3: Net Live PnL & Interactive Traded Coin Chips)
  const posBadge = document.getElementById('pos-status-badge');
  const posPnlDisp = document.getElementById('pos-pnl-display');
  const posPnlPct = document.getElementById('pos-pnl-pct');
  const posDetails = document.getElementById('pos-details-text');
  const chipsContainer = document.getElementById('positions-chips-container');

  if (basketCount > 0) {
    posBadge.textContent = `${basketCount} / ${maxSlots} ACTIVE TRADES`;
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

    posDetails.innerHTML = `Active Trades Mark: <strong>$${formatNumber(positionsVal)}</strong> across <strong>${basketCount}</strong> coins`;

    if (chipsContainer) {
      chipsContainer.innerHTML = activePositions.map(pos => {
        const s = pos.unrealized_pnl >= 0 ? '+' : '';
        const pnlCls = pos.unrealized_pnl >= 0 ? 'profit' : 'loss';
        const base = pos.symbol.split('/')[0];
        return `
          <button type="button" class="pos-chip ${pnlCls}" onclick="switchMarket('${pos.symbol}')" title="Inspect ${pos.symbol} on chart">
            <span class="chip-sym">${base}</span>
            <span class="chip-pnl">${s}$${pos.unrealized_pnl.toFixed(2)}</span>
          </button>
        `;
      }).join('');
    }
  } else {
    posBadge.textContent = `0 / ${maxSlots} SLOTS`;
    posBadge.className = 'pos-badge none';
    posPnlDisp.textContent = '$0.00';
    posPnlPct.textContent = '(0.00%)';
    posPnlDisp.className = 'metric-value mono neutral';
    posPnlPct.className = 'pos-pnl-pct mono neutral';
    posDetails.textContent = 'Fleet scanning 8 high-volume markets';
    if (chipsContainer) chipsContainer.innerHTML = '';
  }

  state.activePositions = activePositions;

  // Update Basket Tray Section
  renderBasketTray(activePositions, positionsVal);

  // Update Top Watchlist Tape
  renderWatchlistTape(state.watchlist || [], state.prices || {}, state.symbol, activePositions);

  // Update Chart Fleet Tabs & Position Overlays on Graph
  renderChartFleetTabs(state.watchlist || [], state.prices || {}, state.symbol, activePositions);
  updateChartPositionBanner(state.symbol, activePositions);
  updateChartPriceLines(state.symbol, activePositions);

  // Populate recent trades table if available
  if (p.recent_trades && Array.isArray(p.recent_trades)) {
    renderTradesTable(p.recent_trades);
  }
}

function renderWatchlistTape(watchlist, prices, activeSymbol, activePositions) {
  const container = document.getElementById('watchlist-tape-items');
  if (!container) return;

  const posMap = {};
  (activePositions || []).forEach(p => { posMap[p.symbol] = p; });

  const coins = Array.isArray(watchlist) && watchlist.length > 0 ? watchlist : [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "SUI/USDT", "DOGE/USDT", "XRP/USDT", "PEPE/USDT"
  ];

  container.innerHTML = coins.map(sym => {
    const isActive = sym === activeSymbol;
    const pos = posMap[sym];
    const base = sym.split('/')[0];
    const px = prices[sym] || (isActive ? state.currentPrice : 0);
    const pxStr = px > 0 ? `$${formatCurrency(px)}` : '---';

    if (pos) {
      const s = pos.unrealized_pnl >= 0 ? '+' : '';
      const pnlCls = pos.unrealized_pnl >= 0 ? 'profit' : 'loss';
      return `
        <div class="tape-coin-pill has-position ${isActive ? 'active' : ''}" onclick="switchMarket('${sym}')" title="Click to view ${sym} chart (Active Position)">
          <span class="tape-coin-pos-dot"></span>
          <strong class="tape-coin-sym">${base}</strong>
          <span class="tape-pos-badge">LONG</span>
          <span class="tape-coin-price mono" id="tape-px-${base}">${pxStr}</span>
          <span class="tab-pnl ${pnlCls}">${s}$${pos.unrealized_pnl.toFixed(2)}</span>
        </div>
      `;
    } else {
      return `
        <div class="tape-coin-pill ${isActive ? 'active' : ''}" onclick="switchMarket('${sym}')" title="Click to view ${sym} chart">
          <strong class="tape-coin-sym">${base}</strong>
          <span class="tape-coin-price mono" id="tape-px-${base}">${pxStr}</span>
        </div>
      `;
    }
  }).join('');
}

function renderBasketTray(activePositions, positionsVal) {
  const container = document.getElementById('basket-grid-container');
  const countBadge = document.getElementById('basket-count-badge');
  const eqTag = document.getElementById('basket-equity-tag');

  const positions = activePositions || [];
  if (countBadge) countBadge.textContent = positions.length;
  if (eqTag) eqTag.textContent = `ALLOCATED: $${formatCurrency(positionsVal)}`;

  if (!container) return;

  if (positions.length === 0) {
    container.innerHTML = `
      <div class="basket-empty-state">
        <span>No open coin positions. The fleet is actively watching top volume coins and will auto-enter on high-probability setups.</span>
      </div>
    `;
    return;
  }

  container.innerHTML = positions.map(pos => {
    const s = pos.unrealized_pnl >= 0 ? '+' : '';
    const pnlCls = pos.unrealized_pnl >= 0 ? 'profit' : 'loss';
    const isChartActive = pos.symbol === state.symbol;

    // Distances to TP and SL
    let tpDist = '---';
    let slDist = '---';
    if (pos.current_price && pos.take_profit_price) {
      const tpDiffPct = ((pos.take_profit_price - pos.current_price) / pos.current_price) * 100;
      tpDist = `${tpDiffPct >= 0 ? '+' : ''}${tpDiffPct.toFixed(1)}%`;
    }
    if (pos.current_price && pos.stop_loss_price) {
      const slDiffPct = ((pos.stop_loss_price - pos.current_price) / pos.current_price) * 100;
      slDist = `${slDiffPct.toFixed(1)}%`;
    }

    return `
      <div class="basket-coin-card ${pnlCls}">
        <div class="basket-card-header">
          <div class="basket-card-title">
            <span class="basket-pulse-dot"></span>
            <strong class="basket-card-sym">${pos.symbol}</strong>
            <span class="basket-strat-tag">LONG</span>
          </div>
          <span class="basket-pnl-pill ${pnlCls}">${s}$${pos.unrealized_pnl.toFixed(2)} (${s}${pos.unrealized_pnl_pct.toFixed(2)}%)</span>
        </div>
        <div class="basket-card-body">
          <div class="basket-stat-row">
            <span class="basket-stat-lbl">MARK / ENTRY:</span>
            <span class="basket-stat-val">$${formatCurrency(pos.current_price || pos.entry_price)} / $${formatCurrency(pos.entry_price)}</span>
          </div>
          <div class="basket-stat-row">
            <span class="basket-stat-lbl">ALLOCATION:</span>
            <span class="basket-stat-val">$${formatCurrency(pos.cost_usdt)} &bull; ${pos.quantity}</span>
          </div>
          <div class="basket-stat-row">
            <span class="basket-stat-lbl">TARGET (2R):</span>
            <span class="basket-stat-val text-success">$${formatCurrency(pos.take_profit_price)} (${tpDist})</span>
          </div>
          <div class="basket-stat-row">
            <span class="basket-stat-lbl">STOP (1R):</span>
            <span class="basket-stat-val text-danger">$${formatCurrency(pos.stop_loss_price)} (${slDist})</span>
          </div>
        </div>
        <div class="basket-card-actions">
          <button type="button" class="basket-btn-chart" onclick="switchMarket('${pos.symbol}')" title="Inspect ${pos.symbol} on chart">
            <svg class="svg-icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>
            <span>${isChartActive ? 'Viewing' : 'Inspect Chart'}</span>
          </button>
          <button type="button" class="basket-btn-close" onclick="closePosition('${pos.symbol}')" title="Close this position">
            <svg class="svg-icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
            <span>Close Position</span>
          </button>
        </div>
      </div>
    `;
  }).join('');
}

function renderChartFleetTabs(watchlist, prices, activeSymbol, activePositions) {
  const container = document.getElementById('chart-fleet-tabs');
  if (!container) return;

  const posMap = {};
  (activePositions || []).forEach(p => { posMap[p.symbol] = p; });

  const coins = Array.isArray(watchlist) && watchlist.length > 0 ? watchlist : [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "SUI/USDT", "DOGE/USDT", "XRP/USDT", "PEPE/USDT"
  ];

  container.innerHTML = coins.map(sym => {
    const isActive = sym === activeSymbol;
    const pos = posMap[sym];
    const px = prices[sym] || (isActive ? state.currentPrice : 0);
    const pxStr = px > 0 ? `$${formatCurrency(px)}` : '---';

    if (pos) {
      const s = pos.unrealized_pnl >= 0 ? '+' : '';
      const pnlCls = pos.unrealized_pnl >= 0 ? 'profit' : 'loss';
      return `
        <button type="button" class="chart-coin-tab in-trade ${isActive ? 'active' : ''}" onclick="switchMarket('${sym}')" title="Click to view ${sym} chart with active trade brackets">
          <span class="tab-pos-dot"></span>
          <strong class="tab-sym">${sym}</strong>
          <span class="tab-badge-pos">LONG</span>
          <span class="tab-pnl ${pnlCls}">${s}$${pos.unrealized_pnl.toFixed(2)} (${s}${pos.unrealized_pnl_pct.toFixed(1)}%)</span>
        </button>
      `;
    } else {
      return `
        <button type="button" class="chart-coin-tab ${isActive ? 'active' : ''}" onclick="switchMarket('${sym}')" title="Click to view ${sym} chart">
          <span class="tab-sym">${sym}</span>
          <span class="tab-px mono">${pxStr}</span>
        </button>
      `;
    }
  }).join('');
}

function updateChartPositionBanner(symbol, activePositions) {
  const banner = document.getElementById('chart-position-banner');
  if (!banner) return;

  const pos = (activePositions || []).find(p => p.symbol === symbol);
  if (!pos) {
    banner.classList.add('hidden');
    return;
  }

  banner.classList.remove('hidden');
  const symEl = document.getElementById('pos-banner-sym');
  if (symEl) symEl.textContent = pos.symbol;

  const entryEl = document.getElementById('pos-banner-entry');
  if (entryEl) entryEl.textContent = `$${formatCurrency(pos.entry_price)}`;

  const tpEl = document.getElementById('pos-banner-tp');
  if (tpEl) tpEl.textContent = pos.take_profit_price ? `$${formatCurrency(pos.take_profit_price)} (+3.0%)` : '---';

  const slEl = document.getElementById('pos-banner-sl');
  if (slEl) slEl.textContent = pos.stop_loss_price ? `$${formatCurrency(pos.stop_loss_price)} (-1.5%)` : '---';

  const pnlEl = document.getElementById('pos-banner-pnl');
  if (pnlEl) {
    const s = pos.unrealized_pnl >= 0 ? '+' : '';
    pnlEl.textContent = `${s}$${pos.unrealized_pnl.toFixed(2)} (${s}${pos.unrealized_pnl_pct.toFixed(2)}%)`;
    pnlEl.className = 'mono font-bold pos-pnl-val ' + (pos.unrealized_pnl >= 0 ? 'text-success' : 'text-danger');
  }

  const closeBtn = document.getElementById('pos-banner-close-btn');
  if (closeBtn) {
    closeBtn.onclick = () => closePosition(pos.symbol);
  }
}

function updateChartPriceLines(symbol, activePositions) {
  if (!candleSeries) return;

  // Clear existing price lines
  if (state.priceLines.entry) {
    try { candleSeries.removePriceLine(state.priceLines.entry); } catch (e) {}
    state.priceLines.entry = null;
  }
  if (state.priceLines.tp) {
    try { candleSeries.removePriceLine(state.priceLines.tp); } catch (e) {}
    state.priceLines.tp = null;
  }
  if (state.priceLines.sl) {
    try { candleSeries.removePriceLine(state.priceLines.sl); } catch (e) {}
    state.priceLines.sl = null;
  }

  if (!state.showBrackets) return;

  const pos = (activePositions || []).find(p => p.symbol === symbol);
  if (!pos) return;

  if (pos.entry_price && pos.entry_price > 0) {
    state.priceLines.entry = candleSeries.createPriceLine({
      price: pos.entry_price,
      color: '#38bdf8',
      lineWidth: 2,
      lineStyle: LightweightCharts.LineStyle.Solid,
      axisLabelVisible: true,
      title: `ENTRY $${formatCurrency(pos.entry_price)}`
    });
  }

  if (pos.take_profit_price && pos.take_profit_price > 0) {
    state.priceLines.tp = candleSeries.createPriceLine({
      price: pos.take_profit_price,
      color: '#10b981',
      lineWidth: 2,
      lineStyle: LightweightCharts.LineStyle.Dashed,
      axisLabelVisible: true,
      title: `TARGET (2R) $${formatCurrency(pos.take_profit_price)}`
    });
  }

  if (pos.stop_loss_price && pos.stop_loss_price > 0) {
    state.priceLines.sl = candleSeries.createPriceLine({
      price: pos.stop_loss_price,
      color: '#f43f5e',
      lineWidth: 2,
      lineStyle: LightweightCharts.LineStyle.Dashed,
      axisLabelVisible: true,
      title: `STOP (1R) $${formatCurrency(pos.stop_loss_price)}`
    });
  }
}

function setChartStyle(style) {
  state.chartStyle = style;
  const btnCandles = document.getElementById('btn-chart-style-candles');
  const btnLine = document.getElementById('btn-chart-style-line');

  if (style === 'candles') {
    if (btnCandles) btnCandles.classList.add('active');
    if (btnLine) btnLine.classList.remove('active');
    if (candleSeries) candleSeries.applyOptions({ visible: true });
    if (areaSeries) areaSeries.applyOptions({ visible: false });
  } else {
    if (btnCandles) btnCandles.classList.remove('active');
    if (btnLine) btnLine.classList.add('active');
    if (candleSeries) candleSeries.applyOptions({ visible: false });
    if (areaSeries) areaSeries.applyOptions({ visible: true });
  }
}

function toggleOverlay(name) {
  if (name === 'ema9') {
    state.showEmaFast = !state.showEmaFast;
    const btn = document.getElementById('btn-overlay-ema9');
    if (btn) btn.classList.toggle('active', state.showEmaFast);
    if (emaFastSeries) emaFastSeries.applyOptions({ visible: state.showEmaFast });
  } else if (name === 'ema21') {
    state.showEmaSlow = !state.showEmaSlow;
    const btn = document.getElementById('btn-overlay-ema21');
    if (btn) btn.classList.toggle('active', state.showEmaSlow);
    if (emaSlowSeries) emaSlowSeries.applyOptions({ visible: state.showEmaSlow });
  } else if (name === 'brackets') {
    state.showBrackets = !state.showBrackets;
    const btn = document.getElementById('btn-overlay-brackets');
    if (btn) btn.classList.toggle('active', state.showBrackets);
    updateChartPriceLines(state.symbol, state.activePositions);
  }
}

async function switchMarket(symbol) {
  try {
    state.symbol = symbol;
    state.tmSymbol = symbol;
    const pairSelect = document.getElementById('pair-select');
    if (pairSelect) pairSelect.value = symbol;

    const tmSelect = document.getElementById('tm-select-coin');
    if (tmSelect) tmSelect.value = symbol;

    // Immediately update tab highlights and position banner
    renderChartFleetTabs(state.watchlist, state.prices, state.symbol, state.activePositions);
    updateChartPositionBanner(state.symbol, state.activePositions);
    updateChartPriceLines(state.symbol, state.activePositions);

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
  if (!ind) return;
  const emaFastEl = document.getElementById('val-ema-fast');
  if (emaFastEl && ind.ema_fast !== undefined) emaFastEl.textContent = formatCurrency(ind.ema_fast);

  const emaSlowEl = document.getElementById('val-ema-slow');
  if (emaSlowEl && ind.ema_slow !== undefined) emaSlowEl.textContent = formatCurrency(ind.ema_slow);

  if (ind.rsi !== undefined) {
    const rsi = ind.rsi;
    const rsiEl = document.getElementById('val-rsi');
    if (rsiEl) {
      rsiEl.textContent = rsi.toFixed(1);

      // Color code RSI
      if (rsi <= 30) rsiEl.className = 'chip-val mono success';
      else if (rsi >= 70) rsiEl.className = 'chip-val mono danger';
      else rsiEl.className = 'chip-val mono';
    }

    // Update RSI Gauge in Sidebar if elements exist
    const gaugeVal = document.getElementById('gauge-rsi-val');
    if (gaugeVal) gaugeVal.textContent = rsi.toFixed(1);
    const needle = document.getElementById('rsi-pointer');
    if (needle) {
      needle.style.left = `${Math.min(100, Math.max(0, rsi))}%`;
    }
  }
}

function updateSignalCard(sig) {
  if (!sig) return;
  const actionBadge = document.getElementById('val-signal-action');
  const action = sig.action || 'HOLD';
  if (actionBadge) {
    actionBadge.textContent = action;
    actionBadge.className = `signal-badge ${action.toLowerCase()}`;
  }

  const reasonEl = document.getElementById('signal-reason-text');
  if (reasonEl) reasonEl.textContent = sig.reason || 'Analyzing market trend...';
  const confEl = document.getElementById('signal-confidence');
  if (confEl) {
    const confPct = Math.round((sig.confidence || 0) * 100);
    confEl.textContent = `${confPct}% CONFIDENCE`;
  }
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
      { setup: "RECLAIM_MA20", name: "20-MA Support Reclaim", badge: "RECLAIM", idle: "Tracking 20 SMA" },
      { setup: "BOLLINGER_REVERSION", name: "Bollinger Range Hunter", badge: "RANGE", idle: "Within Bollinger Bands" }
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
  const activeForSymbol = (state.activePositions || []).find(p => p.symbol === state.symbol);
  if (activeForSymbol) {
    document.getElementById('plan-entry-price').textContent = `$${formatCurrency(activeForSymbol.entry_price)}`;
    document.getElementById('plan-stop-price').textContent = `$${formatCurrency(activeForSymbol.stop_loss_price)}`;
    document.getElementById('plan-target-price').textContent = `$${formatCurrency(activeForSymbol.take_profit_price)}`;
    const distTarget = activeForSymbol.take_profit_price && activeForSymbol.entry_price ? Math.abs(activeForSymbol.take_profit_price - activeForSymbol.entry_price) : 0;
    const distStop = activeForSymbol.stop_loss_price && activeForSymbol.entry_price ? Math.abs(activeForSymbol.entry_price - activeForSymbol.stop_loss_price) : 0;
    const rr = distStop > 0 ? (distTarget / distStop).toFixed(2) : '2.00';
    document.getElementById('plan-rr-ratio').textContent = `${rr}R (ACTIVE)`;
    const reasonEl = document.getElementById('signal-reason-text');
    if (reasonEl) reasonEl.textContent = activeForSymbol.reason ? activeForSymbol.reason.replace(/\[.*?\]\s*/g, '') : `Active position in ${state.symbol}`;
  } else if (suite.plan) {
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
    if (suite.timemachine.return_distribution) {
      renderTimeMachineDistribution(suite.timemachine.return_distribution);
    }
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

function filterAndRenderTrades() {
  const tbody = document.getElementById('trades-table-body');
  if (!tbody) return;

  const outcomeFilter = state.tradeFilterOutcome || 'ALL';
  const botFilter = state.tradeFilterBot || 'ALL';

  const filtered = (state.allTrades || []).filter(t => {
    // 1. Outcome filter
    if (outcomeFilter === 'WINS') {
      if (t.side === 'BUY' || (t.realized_pnl !== undefined && t.realized_pnl <= 0)) return false;
    } else if (outcomeFilter === 'LOSSES') {
      if (t.side === 'BUY' || (t.realized_pnl !== undefined && t.realized_pnl > 0)) return false;
    }

    // 2. Sub-bot filter
    if (botFilter !== 'ALL') {
      const matchStrat = t.strategy === botFilter || t.setup_id === botFilter;
      const matchReason = t.reason && t.reason.toLowerCase().includes(botFilter.toLowerCase());
      if (!matchStrat && !matchReason) return false;
    }

    return true;
  });

  if (filtered.length === 0) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="4">No matching trades found for active filter.</td></tr>';
    return;
  }

  tbody.innerHTML = '';
  // Show up to 50 most recent matching trades
  filtered.slice(0, 50).forEach(t => {
    renderSingleTradeRow(tbody, t);
  });
}

function renderSingleTradeRow(tbody, t) {
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

  const isDetailed = state.tradeDetailsMode === 'detailed';
  const sym = t.symbol ? `<span class="trade-sym-tag">${t.symbol.split('/')[0]}</span>` : '';
  const stratName = t.strategy ? `<span class="trade-strat-subtag">${t.strategy}</span>` : '';

  if (isDetailed) {
    const feeStr = t.fee ? `Fee: $${t.fee.toFixed(2)}` : '';
    const reasonStr = t.reason ? t.reason.replace(/\[.*?\]\s*/g, '').slice(0, 40) : '';
    tr.innerHTML = `
      <td>
        <div>${timeStr}</div>
        <div class="trade-meta-sub">${sym} ${stratName}</div>
      </td>
      <td>
        <span class="trade-side-badge ${sideClass}">${t.side}</span>
      </td>
      <td>
        <div>$${formatCurrency(t.price)}</div>
        <div class="trade-meta-sub">${feeStr}</div>
      </td>
      <td>
        <div>${pnlCell}</div>
        <div class="trade-meta-sub muted" title="${escapeHtml(t.reason || '')}">${escapeHtml(reasonStr)}</div>
      </td>
    `;
  } else {
    tr.innerHTML = `
      <td>${timeStr}</td>
      <td><span class="trade-side-badge ${sideClass}">${t.side}</span></td>
      <td>$${formatCurrency(t.price)}</td>
      <td>${pnlCell}</td>
    `;
  }

  tbody.appendChild(tr);
}

function toggleTradeDetails() {
  state.tradeDetailsMode = state.tradeDetailsMode === 'normal' ? 'detailed' : 'normal';
  const btn = document.getElementById('btn-toggle-trade-details');
  if (btn) {
    btn.textContent = state.tradeDetailsMode === 'detailed' ? 'Details: Verbose' : 'Details: Normal';
  }
  filterAndRenderTrades();
}

function prependTradeRow(t) {
  if (t) {
    state.allTrades.unshift(t);
    if (state.allTrades.length > 200) state.allTrades.pop();
    filterAndRenderTrades();
  }
}

function renderTradesTable(trades) {
  if (Array.isArray(trades)) {
    state.allTrades = trades;
    filterAndRenderTrades();
  }
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

  // Re-run Dynamic Time Machine Button
  const btnRunTM = document.getElementById('btn-run-timemachine');
  if (btnRunTM) {
    btnRunTM.addEventListener('click', () => {
      runDynamicTimeMachine();
    });
  }

  // Bot Start/Pause Button
  const btnToggle = document.getElementById('btn-bot-toggle');
  if (btnToggle) {
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
  }

  // Panic Button
  const btnPanic = document.getElementById('btn-panic');
  if (btnPanic) {
    btnPanic.addEventListener('click', async () => {
      initAudio();
      if (confirm('EMERGENCY PANIC:\n\nLiquidate all open positions at market price and halt trading?')) {
        await fetch('/api/bot/panic', { method: 'POST' });
        state.status = 'PAUSED';
        state.isRunning = false;
        updateBotButton(state.status);
      }
    });
  }

  // Chart Style Toggles (Candles vs Line)
  const btnCandles = document.getElementById('btn-chart-style-candles');
  const btnLine = document.getElementById('btn-chart-style-line');
  if (btnCandles && btnLine) {
    btnCandles.addEventListener('click', () => setChartStyle('candles'));
    btnLine.addEventListener('click', () => setChartStyle('line'));
  }

  // Chart Overlay Toggles (EMA 9, EMA 21, Brackets)
  const btnEma9 = document.getElementById('btn-overlay-ema9');
  const btnEma21 = document.getElementById('btn-overlay-ema21');
  const btnBrackets = document.getElementById('btn-overlay-brackets');
  if (btnEma9) btnEma9.addEventListener('click', () => toggleOverlay('ema9'));
  if (btnEma21) btnEma21.addEventListener('click', () => toggleOverlay('ema21'));
  if (btnBrackets) btnBrackets.addEventListener('click', () => toggleOverlay('brackets'));

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
  if (inputAmount) {
    inputAmount.addEventListener('input', e => {
      const disp = document.getElementById('val-trade-amount-disp');
      if (disp) disp.textContent = `$${e.target.value}`;
    });
  }

  const inputSL = document.getElementById('input-stop-loss');
  if (inputSL) {
    inputSL.addEventListener('input', e => {
      const disp = document.getElementById('val-stop-loss-disp');
      if (disp) disp.textContent = `-${parseFloat(e.target.value).toFixed(1)}%`;
    });
  }

  const inputTP = document.getElementById('input-take-profit');
  if (inputTP) {
    inputTP.addEventListener('input', e => {
      const disp = document.getElementById('val-take-profit-disp');
      if (disp) disp.textContent = `+${parseFloat(e.target.value).toFixed(1)}%`;
    });
  }

  // Apply Settings Button
  const btnApply = document.getElementById('btn-apply-settings');
  if (btnApply) {
    btnApply.addEventListener('click', async () => {
      const stratVal = document.getElementById('strategy-select') ? document.getElementById('strategy-select').value : 'adaptive_multi';
      const checkTrailing = document.getElementById('check-trailing-stop');
      const payload = {
        active_strategy: stratVal,
        trade_amount_usdt: inputAmount ? parseFloat(inputAmount.value) || 500 : 500,
        stop_loss_pct: inputSL ? parseFloat(inputSL.value) || 1.5 : 1.5,
        take_profit_pct: inputTP ? parseFloat(inputTP.value) || 3.0 : 3.0,
        trailing_stop_enabled: checkTrailing ? checkTrailing.checked : true
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
  }

  // Reset Paper Wallet Button
  const btnReset = document.getElementById('btn-reset-wallet');
  if (btnReset) {
    btnReset.addEventListener('click', async () => {
      if (confirm('Reset simulated wallet back to $10,000.00 USDT and clear trade history?')) {
        await fetch('/api/bot/reset-paper', { method: 'POST' });
      }
    });
  }

  // Sound Toggle Button
  const btnSound = document.getElementById('btn-sound-toggle');
  if (btnSound) {
    btnSound.addEventListener('click', () => {
      state.soundEnabled = !state.soundEnabled;
      btnSound.classList.toggle('active', state.soundEnabled);
      if (state.soundEnabled) {
        initAudio();
        playTradeSound('BUY');
      }
    });
  }

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
  if (btnToggleTerminal) {
    btnToggleTerminal.addEventListener('click', () => {
      const body = document.getElementById('terminal-log-stream');
      if (body) body.classList.toggle('collapsed');
    });
  }

  // Settings Modal Controls
  const modal = document.getElementById('settings-modal');
  const btnOpenModal = document.getElementById('btn-open-settings');
  const btnCloseModal = document.getElementById('btn-close-modal');
  const btnCancelModal = document.getElementById('btn-cancel-modal');
  const btnSaveModal = document.getElementById('btn-save-modal');

  if (btnOpenModal && modal) btnOpenModal.addEventListener('click', () => modal.classList.remove('hidden'));
  if (btnCloseModal && modal) btnCloseModal.addEventListener('click', () => modal.classList.add('hidden'));
  if (btnCancelModal && modal) btnCancelModal.addEventListener('click', () => modal.classList.add('hidden'));

  // Environment Mode Switcher inside modal (Paper, Testnet, Live)
  const btnEnvPaper = document.getElementById('tab-env-paper');
  const btnEnvTestnet = document.getElementById('tab-env-testnet');
  const btnEnvLive = document.getElementById('tab-env-live');
  const testnetBox = document.getElementById('testnet-credentials-box');
  const liveBox = document.getElementById('live-credentials-box');

  if (btnEnvPaper) {
    btnEnvPaper.addEventListener('click', () => {
      btnEnvPaper.classList.add('active');
      if (btnEnvTestnet) btnEnvTestnet.classList.remove('active');
      if (btnEnvLive) btnEnvLive.classList.remove('active');
      if (testnetBox) testnetBox.classList.add('hidden');
      if (liveBox) liveBox.classList.add('hidden');
      state.mode = 'PAPER';
    });
  }

  if (btnEnvTestnet) {
    btnEnvTestnet.addEventListener('click', () => {
      btnEnvTestnet.classList.add('active');
      if (btnEnvPaper) btnEnvPaper.classList.remove('active');
      if (btnEnvLive) btnEnvLive.classList.remove('active');
      if (testnetBox) testnetBox.classList.remove('hidden');
      if (liveBox) liveBox.classList.add('hidden');
      state.mode = 'BINANCE_TESTNET';
    });
  }

  if (btnEnvLive) {
    btnEnvLive.addEventListener('click', () => {
      btnEnvLive.classList.add('active');
      if (btnEnvPaper) btnEnvPaper.classList.remove('active');
      if (btnEnvTestnet) btnEnvTestnet.classList.remove('active');
      if (testnetBox) testnetBox.classList.add('hidden');
      if (liveBox) liveBox.classList.remove('hidden');
      state.mode = 'BINANCE_LIVE';
    });
  }

  // Verify Binance Live API Keys Button
  const btnVerifyLive = document.getElementById('btn-verify-live-keys');
  const liveFeedback = document.getElementById('live-verify-feedback');
  if (btnVerifyLive) {
    btnVerifyLive.addEventListener('click', async () => {
      const apiKey = document.getElementById('live-api-key') ? document.getElementById('live-api-key').value.trim() : '';
      const apiSecret = document.getElementById('live-api-secret') ? document.getElementById('live-api-secret').value.trim() : '';
      if (!apiKey || !apiSecret) {
        if (liveFeedback) {
          liveFeedback.className = 'verify-feedback error';
          liveFeedback.textContent = 'Please enter both API Key and Secret first.';
        }
        return;
      }
      btnVerifyLive.disabled = true;
      if (liveFeedback) {
        liveFeedback.className = 'verify-feedback';
        liveFeedback.textContent = 'Connecting to Binance Spot API...';
      }
      try {
        const resp = await fetch('/api/binance/validate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ api_key: apiKey, api_secret: apiSecret, is_testnet: false })
        });
        const res = await resp.json();
        if (res.valid) {
          if (liveFeedback) {
            liveFeedback.className = 'verify-feedback success';
            liveFeedback.textContent = `Connected! Spot Balance: $${res.usdt_balance.toFixed(2)} USDT`;
          }
        } else {
          if (liveFeedback) {
            liveFeedback.className = 'verify-feedback error';
            liveFeedback.textContent = `Connection failed: ${res.error}`;
          }
        }
      } catch (err) {
        if (liveFeedback) {
          liveFeedback.className = 'verify-feedback error';
          liveFeedback.textContent = 'Network error verifying keys.';
        }
      } finally {
        btnVerifyLive.disabled = false;
      }
    });
  }

  if (btnSaveModal) {
    btnSaveModal.addEventListener('click', async () => {
      const testnetKey = document.getElementById('testnet-api-key') ? document.getElementById('testnet-api-key').value.trim() : '';
      const testnetSecret = document.getElementById('testnet-api-secret') ? document.getElementById('testnet-api-secret').value.trim() : '';
      const liveKey = document.getElementById('live-api-key') ? document.getElementById('live-api-key').value.trim() : '';
      const liveSecret = document.getElementById('live-api-secret') ? document.getElementById('live-api-secret').value.trim() : '';
      const payload = {
        mode: state.mode,
        binance_testnet: {
          api_key: testnetKey,
          api_secret: testnetSecret
        },
        binance_live: {
          api_key: liveKey,
          api_secret: liveSecret
        }
      };
      await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      updateModeBadge(state.mode);
      if (modal) modal.classList.add('hidden');
      appendLog({
        time: new Date().toLocaleTimeString(),
        level: 'INFO',
        message: `Trading environment updated to [${state.mode}]`
      });
    });
  }

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

  // --- MONEY MANAGEMENT & CAPITAL ALLOCATION LISTENERS ---
  const btnSaveBudget = document.getElementById('btn-save-budget');
  if (btnSaveBudget) {
    btnSaveBudget.addEventListener('click', applyMoneyManagementUpdate);
  }

  // Budget Input Enter key
  const budgetInput = document.getElementById('input-total-budget');
  if (budgetInput) {
    budgetInput.addEventListener('keydown', e => {
      if (e.key === 'Enter') applyMoneyManagementUpdate();
    });
  }

  // Quick Preset Buttons ($50, $100, $200, $500, $1k)
  document.querySelectorAll('.mm-preset-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      if (budgetInput) {
        budgetInput.value = btn.dataset.budget;
        applyMoneyManagementUpdate();
      }
    });
  });

  // Division Mode, Slots, Max Loss & Break-Even Stop Lock Change
  const selAllocMode = document.getElementById('select-allocation-mode');
  if (selAllocMode) selAllocMode.addEventListener('change', applyMoneyManagementUpdate);

  const inputMaxSlots = document.getElementById('input-max-slots');
  if (inputMaxSlots) inputMaxSlots.addEventListener('change', applyMoneyManagementUpdate);

  const inputSessionLoss = document.getElementById('input-session-max-loss');
  if (inputSessionLoss) inputSessionLoss.addEventListener('change', applyMoneyManagementUpdate);

  const chkBreakeven = document.getElementById('toggle-breakeven-lock');
  if (chkBreakeven) chkBreakeven.addEventListener('change', applyMoneyManagementUpdate);

  // Circuit Breaker Reset
  const btnResetCb = document.getElementById('btn-reset-circuit-breaker');
  if (btnResetCb) {
    btnResetCb.addEventListener('click', resetCircuitBreaker);
  }

  // --- DYNAMIC GRAPH SWITCHER TABS (Price, Equity, Sub-Bots, Fleet) ---
  document.querySelectorAll('.graph-tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const view = btn.dataset.view;
      if (view) switchGraphView(view);
    });
  });

  // --- DYNAMIC TIME MACHINE CONTROLS ---
  const tmCoinSelect = document.getElementById('tm-select-coin');
  if (tmCoinSelect) {
    tmCoinSelect.addEventListener('change', e => {
      state.tmSymbol = e.target.value;
      runDynamicTimeMachine();
    });
  }

  // Horizon Pills (15m, 30m, 1h, 2h)
  document.querySelectorAll('.tm-pill-opt[data-horizon]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tm-pill-opt[data-horizon]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.tmHorizon = parseInt(btn.dataset.horizon, 10);
      runDynamicTimeMachine();
    });
  });

  // Replay Pills (500, 1k, 2.5k, 5k)
  document.querySelectorAll('.tm-pill-opt[data-replays]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tm-pill-opt[data-replays]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.tmReplays = parseInt(btn.dataset.replays, 10);
      runDynamicTimeMachine();
    });
  });

  // View Mode Pills (Cone, Paths, Dist)
  const btnTmCone = document.getElementById('btn-tm-view-cone');
  const btnTmPaths = document.getElementById('btn-tm-view-paths');
  const btnTmDist = document.getElementById('btn-tm-view-dist');
  const tmCanvasWrap = document.getElementById('tm-canvas-wrapper');
  const tmDistWrap = document.getElementById('tm-dist-wrapper');

  const setTmView = (mode) => {
    state.tmViewMode = mode;
    if (btnTmCone) btnTmCone.classList.toggle('active', mode === 'cone');
    if (btnTmPaths) btnTmPaths.classList.toggle('active', mode === 'paths');
    if (btnTmDist) btnTmDist.classList.toggle('active', mode === 'dist');

    if (mode === 'dist') {
      if (tmCanvasWrap) tmCanvasWrap.classList.add('hidden');
      if (tmDistWrap) tmDistWrap.classList.remove('hidden');
      if (currentTmData && currentTmData.return_distribution) {
        renderTimeMachineDistribution(currentTmData.return_distribution);
      }
    } else {
      if (tmCanvasWrap) tmCanvasWrap.classList.remove('hidden');
      if (tmDistWrap) tmDistWrap.classList.add('hidden');
    }
  };

  if (btnTmCone) btnTmCone.addEventListener('click', () => setTmView('cone'));
  if (btnTmPaths) btnTmPaths.addEventListener('click', () => setTmView('paths'));
  if (btnTmDist) btnTmDist.addEventListener('click', () => setTmView('dist'));

  // --- EXECUTION LOG TRADE FILTERS ---
  document.querySelectorAll('.trade-flt-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.trade-flt-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.tradeFilterOutcome = btn.dataset.tfilter;
      filterAndRenderTrades();
    });
  });

  const selTradeBot = document.getElementById('trade-filter-bot');
  if (selTradeBot) {
    selTradeBot.addEventListener('change', e => {
      state.tradeFilterBot = e.target.value;
      filterAndRenderTrades();
    });
  }

  const btnToggleTradeDetails = document.getElementById('btn-toggle-trade-details');
  if (btnToggleTradeDetails) {
    btnToggleTradeDetails.addEventListener('click', toggleTradeDetails);
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
      rIcon.innerHTML = `<svg class="panel-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`;
      rTitle.textContent = 'READY FOR REAL MONEY TRADING';
      rDesc.textContent = 'Your Neptune Bot fleet has maintained positive net returns and disciplined risk controls. You can safely proceed to Step 2 to trade real money on Binance Spot.';
    } else {
      banner.className = 'readiness-banner in-progress';
      rIcon.innerHTML = `<svg class="panel-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>`;
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

  let tmResizeRaf = null;
  function resizeCanvas() {
    if (!tmCanvas || !tmCanvas.parentElement) return;
    const rect = tmCanvas.parentElement.getBoundingClientRect();
    if (rect.width > 0) {
      const dpr = window.devicePixelRatio || 1;
      const newW = Math.floor(rect.width * dpr);
      const newH = Math.floor(230 * dpr);
      if (tmCanvas.width !== newW || tmCanvas.height !== newH) {
        tmCanvas.width = newW;
        tmCanvas.height = newH;
      }
      tmCanvas.style.width = '100%';
      tmCanvas.style.height = '230px';
    }
  }

  window.addEventListener('resize', () => {
    if (tmResizeRaf) cancelAnimationFrame(tmResizeRaf);
    tmResizeRaf = requestAnimationFrame(resizeCanvas);
  });
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

// ==========================================================================
// MONEY MANAGEMENT & CAPITAL ALLOCATION ENGINE UI
// ==========================================================================
function updateMoneyManagementUI(mm) {
  if (!mm) return;
  state.moneyManagement = mm;

  // 1. Status badge & Circuit Breaker Reset Button
  const badge = document.getElementById('mm-status-badge');
  const btnResetCb = document.getElementById('btn-reset-circuit-breaker');
  if (badge) {
    if (mm.circuit_breaker_tripped) {
      badge.textContent = 'CIRCUIT BREAKER TRIPPED (HALTED)';
      badge.className = 'mm-status-pill danger';
    } else {
      badge.textContent = `BUDGET ENFORCED ($${mm.total_budget_limit_usd.toFixed(0)})`;
      badge.className = 'mm-status-pill active';
    }
  }
  if (btnResetCb) {
    btnResetCb.classList.toggle('hidden', !mm.circuit_breaker_tripped);
  }

  // 2. Total Budget Input (update only if user is not currently editing)
  const budgetInput = document.getElementById('input-total-budget');
  if (budgetInput && document.activeElement !== budgetInput) {
    budgetInput.value = mm.total_budget_limit_usd.toFixed(2);
  }

  // Highlight active preset button if matched
  document.querySelectorAll('.mm-preset-btn').forEach(btn => {
    const val = parseFloat(btn.dataset.budget);
    btn.classList.toggle('active', Math.abs(val - mm.total_budget_limit_usd) < 0.01);
  });

  // 3. Portfolio Utilization Meter & Stats
  const utilPct = mm.utilization_pct !== undefined ? mm.utilization_pct : 0.0;
  const utilBadge = document.getElementById('mm-utilization-pct');
  if (utilBadge) {
    utilBadge.textContent = `${utilPct.toFixed(1)}% DEPLOYED`;
    utilBadge.className = 'mm-pct-badge mono ' + (utilPct >= 95 ? 'danger' : (utilPct >= 75 ? 'warning' : ''));
  }

  const fill = document.getElementById('mm-progress-fill');
  if (fill) {
    fill.style.width = `${Math.min(100, Math.max(0, utilPct))}%`;
    fill.className = 'mm-progress-fill ' + (utilPct >= 95 ? 'danger' : (utilPct >= 75 ? 'warning' : ''));
  }

  const statDeployed = document.getElementById('mm-stat-deployed');
  if (statDeployed) statDeployed.textContent = `$${formatCurrency(mm.allocated_budget_usd)}`;

  const statAvail = document.getElementById('mm-stat-available');
  if (statAvail) statAvail.textContent = `$${formatCurrency(mm.available_budget_usd)}`;

  const statSlot = document.getElementById('mm-stat-per-slot');
  if (statSlot) statSlot.textContent = `~$${formatCurrency(mm.per_slot_allocation_usd)}`;

  // 4. Division Controls
  const selMode = document.getElementById('select-allocation-mode');
  if (selMode && document.activeElement !== selMode && mm.allocation_mode) {
    selMode.value = mm.allocation_mode;
  }

  const inputSlots = document.getElementById('input-max-slots');
  if (inputSlots && document.activeElement !== inputSlots && mm.max_open_positions !== undefined) {
    inputSlots.value = mm.max_open_positions;
  }

  const inputLoss = document.getElementById('input-session-max-loss');
  if (inputLoss && document.activeElement !== inputLoss && mm.max_session_loss_usd !== undefined) {
    inputLoss.value = mm.max_session_loss_usd;
  }

  const chkBreakeven = document.getElementById('toggle-breakeven-lock');
  if (chkBreakeven && mm.breakeven_lock_enabled !== undefined) {
    chkBreakeven.checked = mm.breakeven_lock_enabled;
  }
}

async function applyMoneyManagementUpdate() {
  const budgetInput = document.getElementById('input-total-budget');
  const selMode = document.getElementById('select-allocation-mode');
  const inputSlots = document.getElementById('input-max-slots');
  const inputLoss = document.getElementById('input-session-max-loss');
  const chkBreakeven = document.getElementById('toggle-breakeven-lock');
  const btnSave = document.getElementById('btn-save-budget');

  const payload = {
    total_budget_limit_usd: budgetInput ? (parseFloat(budgetInput.value) || 200.0) : 200.0,
    allocation_mode: selMode ? selMode.value : 'EQUAL_SPLIT',
    max_open_positions: inputSlots ? (parseInt(inputSlots.value, 10) || 4) : 4,
    max_session_loss_usd: inputLoss ? (parseFloat(inputLoss.value) || 25.0) : 25.0,
    breakeven_lock_enabled: chkBreakeven ? chkBreakeven.checked : true
  };

  if (btnSave) {
    btnSave.textContent = 'SAVING...';
    btnSave.disabled = true;
  }

  try {
    const res = await fetch('/api/money-management/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.success && data.money_management) {
      updateMoneyManagementUI(data.money_management);
      if (btnSave) btnSave.textContent = '✓ APPLIED';
    } else {
      if (btnSave) btnSave.textContent = 'ERROR';
    }
  } catch (err) {
    console.error('Failed to update money management:', err);
    if (btnSave) btnSave.textContent = 'ERR';
  } finally {
    setTimeout(() => {
      if (btnSave) {
        btnSave.textContent = 'APPLY';
        btnSave.disabled = false;
      }
    }, 1200);
  }
}

async function resetCircuitBreaker() {
  const btn = document.getElementById('btn-reset-circuit-breaker');
  if (btn) {
    btn.textContent = 'Resetting...';
    btn.disabled = true;
  }
  try {
    const res = await fetch('/api/money-management/reset-circuit-breaker', { method: 'POST' });
    const data = await res.json();
    if (data.success && data.money_management) {
      updateMoneyManagementUI(data.money_management);
    }
  } catch (err) {
    console.error('Failed to reset circuit breaker:', err);
  } finally {
    if (btn) {
      btn.textContent = 'Reset Circuit Breaker';
      btn.disabled = false;
    }
  }
}

// ==========================================================================
// DYNAMIC MULTI-GRAPH VIEW CONTROLLER
// ==========================================================================
function switchGraphView(viewName) {
  state.activeGraphView = viewName;

  // Toggle Tab Button Active Class
  document.querySelectorAll('.graph-tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.view === viewName);
  });

  // Toggle Container Visibility
  const map = {
    price: 'tv-chart-container',
    equity: 'equity-chart-container',
    subbots: 'subbots-chart-container',
    fleet: 'fleet-chart-container'
  };

  Object.entries(map).forEach(([key, id]) => {
    const el = document.getElementById(id);
    if (el) {
      if (key === viewName) {
        el.classList.remove('hidden');
        el.classList.add('active');
      } else {
        el.classList.add('hidden');
        el.classList.remove('active');
      }
    }
  });

  // Trigger content render for active graph
  if (viewName === 'price') {
    if (chart && typeof chart.timeScale === 'function') {
      setTimeout(() => {
        chart.timeScale().fitContent();
      }, 50);
    }
  } else if (viewName === 'equity') {
    renderEquityCurveChart(state.equityHistory);
  } else if (viewName === 'subbots') {
    renderSubBotsChart();
  } else if (viewName === 'fleet') {
    renderFleetRadarChart();
  }
}

// ==========================================================================
// DYNAMIC GRAPH 2: EQUITY CURVE & DRAWDOWN CANVAS
// ==========================================================================
function renderEquityCurveChart(history) {
  const canvas = document.getElementById('equity-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const rect = canvas.parentElement ? canvas.parentElement.getBoundingClientRect() : canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const width = rect.width > 0 ? rect.width : 900;
  const height = 340;

  canvas.width = Math.floor(width * dpr);
  canvas.height = Math.floor(height * dpr);
  canvas.style.width = '100%';
  canvas.style.height = `${height}px`;

  ctx.save();
  ctx.scale(dpr, dpr);

  // Background
  ctx.fillStyle = '#080d18';
  ctx.fillRect(0, 0, width, height);

  // Parse history points
  let points = Array.isArray(history) && history.length > 0 ? [...history] : [];
  if (points.length < 2) {
    const now = Date.now();
    points = [
      { timestamp: now - 3600000 * 12, equity: 10000.0, realized_pnl: 0, drawdown_pct: 0 },
      { timestamp: now, equity: 10000.0, realized_pnl: 0, drawdown_pct: 0 }
    ];
  }

  // Calculate statistics
  let peak = 10000.0;
  let maxDD = 0.0;
  let currentEq = points[points.length - 1].equity;

  points.forEach(p => {
    if (p.equity > peak) peak = p.equity;
    const dd = peak > 0 ? ((peak - p.equity) / peak) * 100 : 0;
    if (dd > maxDD) maxDD = dd;
  });

  const totalPnL = currentEq - 10000.0;
  const pnlSign = totalPnL >= 0 ? '+' : '';

  // Update header metric displays
  const peakEl = document.getElementById('eq-chart-peak');
  if (peakEl) peakEl.textContent = `$${formatCurrency(peak)}`;

  const curEl = document.getElementById('eq-chart-current');
  if (curEl) curEl.textContent = `$${formatCurrency(currentEq)}`;

  const ddEl = document.getElementById('eq-chart-dd');
  if (ddEl) ddEl.textContent = `${maxDD.toFixed(1)}%`;

  const pnlEl = document.getElementById('eq-chart-pnl');
  if (pnlEl) {
    pnlEl.textContent = `${pnlSign}$${totalPnL.toFixed(2)}`;
    pnlEl.className = 'mono font-bold ' + (totalPnL >= 0 ? 'success' : 'danger');
  }

  // Margins
  const padLeft = 70;
  const padRight = 35;
  const padTop = 30;
  const padBottom = 35;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  let minVal = Math.min(...points.map(p => p.equity));
  let maxVal = Math.max(...points.map(p => p.equity));
  if (Math.abs(maxVal - minVal) < 1.0) {
    minVal -= 25;
    maxVal += 25;
  }
  const range = (maxVal - minVal) * 1.25;
  const midVal = (maxVal + minVal) / 2;
  const adjMin = midVal - range / 2;
  const adjMax = midVal + range / 2;

  const getX = idx => padLeft + (idx / (points.length - 1)) * plotW;
  const getY = val => padTop + plotH - ((val - adjMin) / (adjMax - adjMin)) * plotH;

  // Gridlines & Labels
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)';
  ctx.lineWidth = 1;
  const numGrid = 5;
  for (let i = 0; i <= numGrid; i++) {
    const yVal = adjMin + (i / numGrid) * (adjMax - adjMin);
    const y = getY(yVal);
    ctx.beginPath();
    ctx.moveTo(padLeft, y);
    ctx.lineTo(padLeft + plotW, y);
    ctx.stroke();

    ctx.fillStyle = '#64748b';
    ctx.font = '10px "JetBrains Mono", monospace';
    ctx.textAlign = 'right';
    ctx.fillText(`$${yVal.toFixed(0)}`, padLeft - 8, y + 3);
  }

  // Draw Initial $10,000 Baseline
  const base10kY = getY(10000.0);
  if (base10kY >= padTop && base10kY <= padTop + plotH) {
    ctx.setLineDash([4, 4]);
    ctx.strokeStyle = 'rgba(100, 116, 139, 0.45)';
    ctx.beginPath();
    ctx.moveTo(padLeft, base10kY);
    ctx.lineTo(padLeft + plotW, base10kY);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = '#64748b';
    ctx.textAlign = 'right';
    ctx.fillText('BASE $10k', padLeft + plotW - 4, base10kY - 6);
  }

  // Draw Gradient Fill under Equity Curve
  const grad = ctx.createLinearGradient(0, padTop, 0, padTop + plotH);
  grad.addColorStop(0, 'rgba(0, 245, 212, 0.28)');
  grad.addColorStop(0.7, 'rgba(0, 245, 212, 0.05)');
  grad.addColorStop(1, 'rgba(0, 245, 212, 0.0)');

  ctx.beginPath();
  ctx.moveTo(getX(0), getY(points[0].equity));
  for (let i = 1; i < points.length; i++) {
    const prevX = getX(i - 1);
    const prevY = getY(points[i - 1].equity);
    const currX = getX(i);
    const currY = getY(points[i].equity);
    ctx.bezierCurveTo((prevX + currX) / 2, prevY, (prevX + currX) / 2, currY, currX, currY);
  }
  ctx.lineTo(getX(points.length - 1), padTop + plotH);
  ctx.lineTo(getX(0), padTop + plotH);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();

  // Draw Neon Cyan Equity Line
  ctx.beginPath();
  ctx.moveTo(getX(0), getY(points[0].equity));
  for (let i = 1; i < points.length; i++) {
    const prevX = getX(i - 1);
    const prevY = getY(points[i - 1].equity);
    const currX = getX(i);
    const currY = getY(points[i].equity);
    ctx.bezierCurveTo((prevX + currX) / 2, prevY, (prevX + currX) / 2, currY, currX, currY);
  }
  ctx.strokeStyle = '#00f5d4';
  ctx.lineWidth = 2.4;
  ctx.shadowColor = 'rgba(0, 245, 212, 0.7)';
  ctx.shadowBlur = 8;
  ctx.stroke();
  ctx.shadowBlur = 0;

  // Draw End Dot
  const lastX = getX(points.length - 1);
  const lastY = getY(points[points.length - 1].equity);
  ctx.fillStyle = '#00f5d4';
  ctx.beginPath();
  ctx.arc(lastX, lastY, 4.5, 0, Math.PI * 2);
  ctx.fill();

  // Footer label
  ctx.fillStyle = '#94a3b8';
  ctx.textAlign = 'left';
  ctx.font = '11px "Inter", sans-serif';
  ctx.fillText(`Checkpoints: ${points.length} trades | Peak Capital: $${formatCurrency(peak)}`, padLeft, height - 12);

  ctx.restore();
}

// ==========================================================================
// DYNAMIC GRAPH 3: 6 SUB-BOT ALGORITHM ANALYTICS
// ==========================================================================
async function renderSubBotsChart() {
  const container = document.getElementById('subbots-chart-content');
  if (!container) return;

  container.innerHTML = '<div class="subbots-loading">Loading 6 Sub-Bot Quantitative Telemetry...</div>';

  try {
    const res = await fetch('/api/reports/sub-bots');
    const data = await res.json();
    const subBotsMap = data.sub_bots || data.bot_breakdown;
    if (!data.success || !subBotsMap) {
      container.innerHTML = '<div class="subbots-empty">Sub-bot metrics unavailable.</div>';
      return;
    }

    const regime = data.market_regime || { regime: 'RANGING_CHOP', adx: 18.0, description: 'Sideways Market Chop' };
    const bots = Object.entries(subBotsMap);

    const regimeHeader = `
      <div class="subbots-regime-banner">
        <div>
          <span class="regime-banner-title">DETECTED REGIME: <strong>${regime.regime.replace(/_/g, ' ')}</strong></span>
          <span class="regime-banner-sub mono">ADX Strength: ${regime.adx !== undefined ? regime.adx.toFixed(1) : '---'} &bull; Volatility Squeeze: ${regime.volatility_squeeze ? 'YES' : 'NO'}</span>
        </div>
        <span class="regime-banner-desc">${regime.description || ''}</span>
      </div>
    `;

    const cardsHtml = bots.map(([key, bot]) => {
      const winRate = bot.win_rate_pct || 0;
      const trades = bot.trades || 0;
      const wins = bot.wins || 0;
      const losses = bot.losses || 0;
      const pnl = bot.realized_pnl || 0;
      const pnlSign = pnl >= 0 ? '+' : '';
      const pnlClass = pnl >= 0 ? 'success' : 'danger';
      const weight = bot.weight !== undefined ? bot.weight : 1.0;
      const weightBadge = weight >= 1.15 ? 'boosted' : (weight <= 0.85 ? 'defensive' : 'normal');

      // Recommended status in current regime
      let regimeFit = 'NEUTRAL';
      let regimeClass = 'neutral';
      if (regime.regime === 'RANGING_CHOP' || regime.regime === 'VOLATILITY_SQUEEZE') {
        if (key === 'oversold_bounce' || key === 'bollinger_reversion') {
          regimeFit = 'PREFERRED (CHOP HUNTER)';
          regimeClass = 'preferred';
        } else if (key === 'ema_rsi') {
          regimeFit = 'SUPPRESSED (LOW ADX CHOP GUARD)';
          regimeClass = 'suppressed';
        }
      } else if (regime.regime.includes('TRENDING')) {
        if (key === 'orb' || key === 'bull_flag' || key === 'ema_rsi') {
          regimeFit = 'PREFERRED (TREND)';
          regimeClass = 'preferred';
        }
      }

      const barColor = winRate >= 60 ? 'var(--accent-cyan)' : (winRate >= 40 ? 'var(--accent-gold)' : 'var(--accent-crimson)');

      return `
        <div class="subbot-analytics-card">
          <div class="subbot-card-top">
            <div>
              <strong class="subbot-name">${bot.name}</strong>
              <div class="subbot-role">${bot.role}</div>
            </div>
            <span class="weight-badge ${weightBadge}">${weight.toFixed(2)}x WEIGHT</span>
          </div>

          <div class="subbot-stats-row">
            <div>
              <span class="subbot-stat-lbl">WIN RATE</span>
              <strong class="subbot-stat-val mono" style="color:${barColor}">${winRate.toFixed(1)}%</strong>
            </div>
            <div>
              <span class="subbot-stat-lbl">TRADES (W / L)</span>
              <strong class="subbot-stat-val mono">${trades} (${wins}W / ${losses}L)</strong>
            </div>
            <div>
              <span class="subbot-stat-lbl">REALIZED PNL</span>
              <strong class="subbot-stat-val mono ${pnlClass}">${pnlSign}$${pnl.toFixed(2)}</strong>
            </div>
          </div>

          <div class="subbot-progress-track">
            <div class="subbot-progress-bar" style="width: ${Math.min(100, Math.max(5, winRate))}%; background: ${barColor}"></div>
          </div>

          <div class="subbot-card-bottom">
            <span class="regime-fit-tag ${regimeClass}">REGIME: ${regimeFit}</span>
          </div>
        </div>
      `;
    }).join('');

    container.innerHTML = regimeHeader + `<div class="subbots-grid-inner">${cardsHtml}</div>`;
  } catch (err) {
    container.innerHTML = '<div class="subbots-error">Failed to fetch sub-bot reports.</div>';
  }
}

// ==========================================================================
// DYNAMIC GRAPH 4: MULTI-COIN FLEET RADAR
// ==========================================================================
function renderFleetRadarChart() {
  const container = document.getElementById('fleet-chart-content');
  if (!container) return;

  const coins = Array.isArray(state.watchlist) && state.watchlist.length > 0 ? state.watchlist : [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "SUI/USDT", "DOGE/USDT", "XRP/USDT", "PEPE/USDT"
  ];

  const posMap = {};
  (state.activePositions || []).forEach(p => { posMap[p.symbol] = p; });

  container.innerHTML = coins.map(sym => {
    const px = state.prices[sym] || (sym === state.symbol ? state.currentPrice : 0);
    const pos = posMap[sym];
    const isViewing = sym === state.symbol;

    let posBadge = '';
    let pnlClass = 'neutral';
    if (pos) {
      const s = pos.unrealized_pnl >= 0 ? '+' : '';
      pnlClass = pos.unrealized_pnl >= 0 ? 'success' : 'danger';
      posBadge = `<span class="fleet-pos-badge ${pnlClass}">LONG: ${s}$${pos.unrealized_pnl.toFixed(2)} (${s}${pos.unrealized_pnl_pct.toFixed(1)}%)</span>`;
    }

    return `
      <div class="fleet-coin-card ${pos ? 'in-trade' : ''}">
        <div class="fleet-card-header">
          <div class="fleet-card-title">
            <span class="fleet-pulse-dot ${pos ? 'active' : ''}"></span>
            <strong class="fleet-sym">${sym}</strong>
          </div>
          ${posBadge}
        </div>
        <div class="fleet-card-body">
          <div class="fleet-price-row">
            <span class="fleet-price-lbl">MARK PRICE</span>
            <strong class="fleet-price-val mono">${px > 0 ? '$' + formatCurrency(px) : '---'}</strong>
          </div>
        </div>
        <div class="fleet-card-actions">
          <button type="button" class="fleet-inspect-btn ${isViewing ? 'active' : ''}" onclick="switchMarket('${sym}'); switchGraphView('price');">
            <span>${isViewing ? '✓ Chart Active' : 'Inspect Candlestick Chart'}</span>
          </button>
        </div>
      </div>
    `;
  }).join('');
}

// ==========================================================================
// DYNAMIC TIME MACHINE: MONTE CARLO SIMULATOR RUNNER & RETURN DISTRIBUTION
// ==========================================================================
async function runDynamicTimeMachine() {
  const btnRunTM = document.getElementById('btn-run-timemachine');
  if (btnRunTM) {
    btnRunTM.textContent = 'Simulating...';
    btnRunTM.disabled = true;
  }

  const payload = {
    symbol: state.tmSymbol || state.symbol || 'BTC/USDT',
    replays: state.tmReplays || 1000,
    horizon: state.tmHorizon || 30,
    target_mode: state.tmTargetMode || '2R'
  };

  try {
    const res = await fetch('/api/bot/time-machine/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const d = await res.json();
    if (d.success) {
      updateDayTraderSuite(d);
      if (d.timemachine && d.timemachine.return_distribution) {
        renderTimeMachineDistribution(d.timemachine.return_distribution);
      }
    }
  } catch (e) {
    console.error('Dynamic time machine run failed:', e);
  } finally {
    if (btnRunTM) {
      setTimeout(() => {
        btnRunTM.textContent = 'Re-run';
        btnRunTM.disabled = false;
      }, 600);
    }
  }
}

function renderTimeMachineDistribution(dist) {
  const container = document.getElementById('tm-dist-bars');
  if (!container) return;

  if (!dist || !Array.isArray(dist) || dist.length === 0) {
    container.innerHTML = '<div class="tm-dist-empty">No distribution data available.</div>';
    return;
  }

  container.innerHTML = dist.map(b => {
    const pct = b.pct || 0;
    const lbl = b.label || b.range || '';
    const isWin = b.type === 'target' || lbl.startsWith('+') || lbl.includes('> +');
    const isLoss = b.type === 'stop' || lbl.startsWith('< -') || lbl.includes('-');
    const barClass = isWin ? 'win-bar' : (isLoss ? 'loss-bar' : 'neutral-bar');

    return `
      <div class="tm-dist-col">
        <div class="tm-dist-bar-track">
          <div class="tm-dist-bar-fill ${barClass}" style="height: ${Math.min(100, Math.max(5, pct * 2.2))}%"></div>
        </div>
        <span class="tm-dist-pct mono">${pct.toFixed(1)}%</span>
        <span class="tm-dist-lbl">${lbl}</span>
      </div>
    `;
  }).join('');
}

