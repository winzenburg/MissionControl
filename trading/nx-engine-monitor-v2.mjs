#!/usr/bin/env node
/**
 * AMS NX Trade Engine v2 — Autonomous Monitor & Executor (FIXED)
 * 
 * V2 FIXES:
 * - Position state tracking (prevents duplicate entries)
 * - Entry/exit state machine
 * - Stop loss enforcement
 * - Take profit logic
 * - Proper risk checks per position
 * 
 * Run: node trading/nx-engine-monitor-v2.mjs
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { execSync } from 'child_process';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WORKSPACE = path.resolve(__dirname, '..');
const DASHBOARD_DATA = path.join(WORKSPACE, 'dashboard-data.json');
const TRADE_LOG = path.join(WORKSPACE, 'logs/trades.log');
const POSITIONS_LOG = path.join(WORKSPACE, 'logs/open-positions.json');

// ===================================================================
// POSITION STATE MANAGER
// ===================================================================

class PositionManager {
  constructor() {
    this.positions = this.loadPositions();
  }

  loadPositions() {
    try {
      if (fs.existsSync(POSITIONS_LOG)) {
        return JSON.parse(fs.readFileSync(POSITIONS_LOG, 'utf-8'));
      }
    } catch (e) {
      console.warn(`Failed to load positions:`, e.message);
    }
    return {};
  }

  savePositions() {
    fs.writeFileSync(POSITIONS_LOG, JSON.stringify(this.positions, null, 2));
  }

  openPosition(ticker, entryPrice, quantity, stopPrice, targetPrice) {
    /**
     * Open a new position
     */
    if (this.positions[ticker]) {
      return null; // Position already exists
    }

    this.positions[ticker] = {
      ticker,
      entryPrice,
      quantity,
      stopPrice,
      targetPrice,
      openedAt: new Date().toISOString(),
      status: 'OPEN',
    };

    this.savePositions();
    return this.positions[ticker];
  }

  closePosition(ticker, exitPrice, exitReason) {
    /**
     * Close a position
     */
    if (!this.positions[ticker]) {
      return null; // No position to close
    }

    const pos = this.positions[ticker];
    const pnl = (exitPrice - pos.entryPrice) * pos.quantity;
    const pnlPct = ((exitPrice - pos.entryPrice) / pos.entryPrice) * 100;

    pos.exitPrice = exitPrice;
    pos.exitReason = exitReason;
    pos.closedAt = new Date().toISOString();
    pos.status = 'CLOSED';
    pos.pnl = pnl;
    pos.pnlPct = pnlPct;

    this.savePositions();
    
    return pos;
  }

  getPosition(ticker) {
    return this.positions[ticker];
  }

  getOpenPositions() {
    return Object.values(this.positions).filter(p => p.status === 'OPEN');
  }

  hasOpenPosition(ticker) {
    const pos = this.positions[ticker];
    return pos && pos.status === 'OPEN';
  }

  checkStopLoss(ticker, currentPrice) {
    /**
     * Check if stop loss is hit
     */
    const pos = this.getPosition(ticker);
    if (!pos || pos.status !== 'OPEN') return null;

    if (currentPrice <= pos.stopPrice) {
      return { triggered: true, reason: 'STOP_LOSS', price: currentPrice };
    }

    return { triggered: false };
  }

  checkTakeProfit(ticker, currentPrice) {
    /**
     * Check if take profit is hit
     */
    const pos = this.getPosition(ticker);
    if (!pos || pos.status !== 'OPEN') return null;

    if (currentPrice >= pos.targetPrice) {
      return { triggered: true, reason: 'TAKE_PROFIT', price: currentPrice };
    }

    return { triggered: false };
  }
}

// ===================================================================
// NX TRADE ENGINE v2 (Replicated Logic)
// ===================================================================

class NXTradeEngine {
  constructor(ticker, ohlcvData) {
    this.ticker = ticker;
    this.data = ohlcvData;
    this.n = ohlcvData.length;
  }

  epsilon(x) { return Math.max(x, 1e-9); }

  roc(source, len) {
    if (this.n < len) return 0;
    return ((source[this.n - 1] - source[this.n - 1 - len]) / this.epsilon(source[this.n - 1 - len])) * 100;
  }

  rsi(source, len) {
    if (this.n < len) return 50;
    const closes = source.slice(-len);
    let gains = 0, losses = 0;
    for (let i = 1; i < closes.length; i++) {
      const change = closes[i] - closes[i - 1];
      if (change > 0) gains += change;
      else losses -= change;
    }
    const avgGain = gains / len;
    const avgLoss = losses / len;
    const rs = avgGain / this.epsilon(avgLoss);
    return 100 - (100 / (1 + rs));
  }

  analyze() {
    const closes = this.data.map(d => d.close);
    const rocS = this.roc(closes, 21);
    const rocM = this.roc(closes, 63);
    const rocL = this.roc(closes, 126);
    const compMom = 0.2 * rocS + 0.3 * rocM + 0.5 * rocL;
    const rsi14 = this.rsi(closes, 14);
    const ema200 = closes.length >= 200 ? this.sma(closes, 200) : closes[this.n - 1];

    return {
      close: closes[this.n - 1],
      compMom,
      rsi14,
      bullish: closes[this.n - 1] > ema200,
      rocL,
    };
  }

  sma(source, len) {
    if (this.n < len) return source[this.n - 1];
    return source.slice(-len).reduce((a, b) => a + b, 0) / len;
  }

  getSignal() {
    const analysis = this.analyze();

    // Entry signal
    if (analysis.rsi14 > 50 && analysis.compMom > 0 && analysis.bullish) {
      return { type: 'LONG_ENTRY', analysis };
    }

    // Exit signal
    if (analysis.rsi14 < 50 || analysis.compMom < 0) {
      return { type: 'EXIT', analysis };
    }

    return { type: 'WAIT', analysis };
  }
}

// ===================================================================
// RISK MANAGER
// ===================================================================

class RiskManager {
  constructor(accountValue = 1000000) {
    this.accountValue = accountValue;
    this.maxLossPerTrade = accountValue * 0.005; // 0.5%
    this.maxConcurrentPositions = 2;
  }

  canOpenPosition(openPositions) {
    return openPositions.length < this.maxConcurrentPositions;
  }

  calculatePositionSize(entryPrice, stopPrice) {
    const riskPerShare = Math.abs(entryPrice - stopPrice);
    if (riskPerShare <= 0) return 0;

    const maxShares = Math.floor(this.maxLossPerTrade / riskPerShare);
    return Math.max(maxShares, 1);
  }
}

// ===================================================================
// MAIN MONITOR LOOP
// ===================================================================

async function fetchLiveData(ticker) {
  try {
    const pythonCmd = `python3 << 'EOF'
import yfinance as yf
import json
ticker = "${ticker}"
data = yf.download(ticker, period="1y", progress=False)
if data.empty:
    print(json.dumps({"error": "No data"}))
else:
    ohlcv = []
    for date, row in data.iterrows():
        ohlcv.append({
            "time": date.strftime("%Y-%m-%d"),
            "open": float(row['Open']),
            "high": float(row['High']),
            "low": float(row['Low']),
            "close": float(row['Close']),
            "volume": int(row['Volume'])
        })
    print(json.dumps(ohlcv))
EOF`;

    const output = execSync(pythonCmd, { encoding: 'utf-8', timeout: 30000 });
    const data = JSON.parse(output);
    if (data.error) return null;
    return data;
  } catch (e) {
    return null;
  }
}

async function monitorCandidates() {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`AMS NX TRADE ENGINE v2 — FIXED MONITOR RUN`);
  console.log(`Time: ${new Date().toLocaleTimeString()}`);
  console.log(`${'='.repeat(60)}\n`);

  // Load screener results
  let dashboardData = {};
  if (fs.existsSync(DASHBOARD_DATA)) {
    dashboardData = JSON.parse(fs.readFileSync(DASHBOARD_DATA, 'utf-8'));
  }

  const candidates = [
    ...(dashboardData.screener?.tier3 || []),
    ...(dashboardData.screener?.tier2 || []),
  ].slice(0, 20);

  if (!candidates || candidates.length === 0) {
    console.log('No candidates in dashboard.\n');
    return;
  }

  // Initialize managers
  const positionMgr = new PositionManager();
  const riskMgr = new RiskManager();

  console.log(`Monitoring ${candidates.length} candidates...`);
  console.log(`Open positions: ${positionMgr.getOpenPositions().length}\n`);

  // Scan each candidate
  let entries = 0, exits = 0;

  for (const candidate of candidates) {
    const ticker = candidate.symbol;
    const ohlcv = await fetchLiveData(ticker);
    
    if (!ohlcv || ohlcv.length < 126) continue;

    const currentPrice = ohlcv[ohlcv.length - 1].close;
    const engine = new NXTradeEngine(ticker, ohlcv);
    const signal = engine.getSignal();

    // CHECK EXITS FIRST
    if (positionMgr.hasOpenPosition(ticker)) {
      const pos = positionMgr.getPosition(ticker);

      // Check stop loss
      const stopCheck = positionMgr.checkStopLoss(ticker, currentPrice);
      if (stopCheck.triggered) {
        const closed = positionMgr.closePosition(ticker, currentPrice, 'STOP_LOSS_HIT');
        console.log(`  🛑 ${ticker}: CLOSED (Stop Loss) | PnL: ${closed.pnlPct.toFixed(2)}%`);
        exits++;
        continue;
      }

      // Check take profit
      const tpCheck = positionMgr.checkTakeProfit(ticker, currentPrice);
      if (tpCheck.triggered) {
        const closed = positionMgr.closePosition(ticker, currentPrice, 'TAKE_PROFIT_HIT');
        console.log(`  ✅ ${ticker}: CLOSED (Take Profit) | PnL: ${closed.pnlPct.toFixed(2)}%`);
        exits++;
        continue;
      }

      // Check exit signal
      if (signal.type === 'EXIT') {
        const closed = positionMgr.closePosition(ticker, currentPrice, 'SIGNAL_EXIT');
        console.log(`  📉 ${ticker}: CLOSED (Exit Signal) | PnL: ${closed.pnlPct.toFixed(2)}%`);
        exits++;
        continue;
      }

      // Position still open, skip entry check
      continue;
    }

    // CHECK ENTRIES (only if no open position)
    if (signal.type === 'LONG_ENTRY') {
      // Refresh open positions count
      const currentOpenPositions = positionMgr.getOpenPositions();
      
      // Can we open?
      if (!riskMgr.canOpenPosition(currentOpenPositions)) {
        console.log(`  ⏸️  ${ticker}: Signal detected but max positions reached (${currentOpenPositions.length}/${riskMgr.maxConcurrentPositions})`);
        continue;
      }

      // Calculate position size
      const stopPrice = currentPrice * 0.95; // 5% stop
      const quantity = riskMgr.calculatePositionSize(currentPrice, stopPrice);
      const targetPrice = currentPrice * 1.075; // 1.5R target (1.5 * 5%)

      // Open position
      const pos = positionMgr.openPosition(ticker, currentPrice, quantity, stopPrice, targetPrice);
      if (pos) {
        console.log(`  🎯 ${ticker}: OPENED | ${quantity} shares @ ${currentPrice.toFixed(2)} | Stop: ${stopPrice.toFixed(2)} | Target: ${targetPrice.toFixed(2)}`);
        entries++;
      }
    }
  }

  console.log(`\n${'='.repeat(60)}`);
  console.log(`Entries: ${entries} | Exits: ${exits} | Open: ${positionMgr.getOpenPositions().length}`);
  console.log(`${'='.repeat(60)}\n`);
}

// ===================================================================
// ENTRY POINT
// ===================================================================

async function main() {
  try {
    await monitorCandidates();
  } catch (e) {
    console.error('\n❌ Monitor failed:', e.message);
    process.exit(1);
  }
}

main();
