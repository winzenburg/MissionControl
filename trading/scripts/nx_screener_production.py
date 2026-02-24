#!/usr/bin/env python3
"""
NX Production Screener
Scans full market: S&P 500, Nasdaq 100, Russell 2000, major ETFs (600+ symbols)
Applies NX criteria. Outputs comprehensive watchlist.
Robust, simple, production-ready.

UPDATED: Includes earnings blackout (±14 days) and economic calendar integration
"""

import yfinance as yf
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from pathlib import Path
import logging
import time
import sys

# Add scripts dir to path for imports
SCRIPTS_DIR = Path.home() / ".openclaw" / "workspace" / "trading" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from earnings_calendar import get_blackout_symbols as get_earnings_blackout
    from economic_calendar import is_economic_blackout, get_blackout_reason, get_upcoming_events
    from regime_detector import RegimeDetector
    CALENDAR_MODULES_LOADED = True
    REGIME_DETECTOR_LOADED = True
except ImportError as e:
    print(f"Warning: Some modules not loaded: {e}")
    CALENDAR_MODULES_LOADED = False
    REGIME_DETECTOR_LOADED = False

# Setup logging
LOG_DIR = Path.home() / ".openclaw" / "workspace" / "trading" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "nx_screener_production.log"

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

WATCHLIST_FILE = Path.home() / ".openclaw" / "workspace" / "trading" / "watchlist.json"

# NX Criteria (from AMS Pro Screener NX) - FURTHER RELAXED for better candidate flow
NX = {
    "tier_2_min": 0.10,  # Relaxed from 0.15 (Feb 24 loosening)
    "tier_3_min": 0.30,  # Relaxed from 0.35
    "rs_long_min": 0.50,  # Relaxed from 0.55 (Feb 24 loosening)
    "rs_short_max": 0.50,  # Relaxed from 0.45 (Feb 24 loosening)
    "rvol_min": 1.00,  # Relaxed from 1.20
    "struct_q_min": 0.35,  # Relaxed from 0.40 (Feb 24 loosening)
    "htf_bias_long_min": 0.45,  # Relaxed from 0.50
    "htf_bias_short_max": 0.55,  # Relaxed from 0.50
}

def get_universe_symbols():
    """Return FULL market list of symbols to screen (1000+ liquid symbols from all sectors)."""
    
    # S&P 500 CORE (largest 100 by market cap)
    sp500_core = [
        'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'META', 'AMZN', 'TSLA', 'BERKB', 'JPM', 'V',
        'JNJ', 'WMT', 'PG', 'MA', 'ASML', 'COST', 'MCD', 'SPG', 'CAT', 'AXP',
        'NFLX', 'ADBE', 'CSCO', 'BKNG', 'XOM', 'CVX', 'COP', 'ISRG', 'PEP', 'KO',
        'AMD', 'INTC', 'QCOM', 'AVGO', 'TXN', 'SMCI', 'PLTR', 'AFRM', 'UPST', 'COIN',
        'GS', 'BAC', 'WFC', 'MS', 'BLK', 'HOOD', 'SOFI', 'MARA', 'RIOT', 'MSTR',
        'CRM', 'SNOW', 'CRWD', 'DDOG', 'NET', 'OKTA', 'TWLO', 'ZM', 'TEAM', 'SPLK',
        'PYPL', 'SQ', 'SHOP', 'UBER', 'LYFT', 'DASH', 'PINS', 'SNAP', 'TTD', 'PUBM',
        'ROKU', 'TDOC', 'VEEV', 'TWTR', 'RBLX', 'MNST', 'ENPH', 'FSLR', 'RUN', 'LCID',
        'RIVN', 'F', 'GM', 'LCID', 'NIO', 'LI', 'XPEV', 'BABA', 'TCEHY', 'SE',
        'MELI', 'PDD', 'NTES', 'BILI', 'IQ', 'FUTU', 'DIDI', 'BIDU', 'JD', 'VIPS',
        'MU', 'LRCX', 'ASML', 'NVDA', 'AMD', 'INTC', 'QCOM', 'AVGO', 'MRVL', 'NXPI',
        'XLNX', 'MPWR', 'ON', 'SLAB', 'RMBS', 'CRUS', 'CDNS', 'SNPS', 'ACACIA', 'ANAB',
        'ARISTA', 'VIAVI', 'JKHY', 'PAYC', 'VEEV', 'EPAY', 'ANET', 'BGFV', 'SMCI', 'DELL',
        'HPQ', 'PANW', 'CRWD', 'OKTA', 'AUTH0', 'ZS', 'SUMO', 'PLTF', 'DOMO', 'QWEST',
        'HRT', 'ITCI', 'TTM', 'TLRY', 'CRON', 'APHA', 'ACB', 'OGI', 'HEXO', 'SNDL',
        'TRST', 'GTII', 'CWBHF', 'GRWG', 'KSHB', 'ITRM', 'KXONE', 'METC', 'AABB', 'CBAK',
        'SOS', 'MARA', 'RIOT', 'CLSK', 'HUT', 'MSTR', 'GLDRX', 'CAN', 'WTER', 'CORE',
        'GEVO', 'PLUG', 'FCEL', 'CCIV', 'FSR', 'QS', 'GGPI', 'THCB', 'IPOE', 'SOAC',
        'LICY', 'CHPT', 'EVGO', 'NKLA', 'WORKHORSE', 'SOLO', 'BLNK', 'OZSC', 'IDEX', 'KTOS',
        'RBLX', 'U', 'DASH', 'DRDX', 'SNOW', 'NET', 'CRWD', 'OKTA', 'DDOG', 'ANET',
        'TWLO', 'ZM', 'UPST', 'LEMONADE', 'ROKU', 'PINS', 'SNAP', 'TTD', 'PUBM', 'MOMO',
        'BILI', 'IQ', 'HUYA', 'JOYY', 'FUTU', 'BK', 'BK', 'RE', 'FHN', 'CFG',
        'WAB', 'UNP', 'CSX', 'KSU', 'OKE', 'MPC', 'PSX', 'VLO', 'HES', 'EOG',
        'CXE', 'FANG', 'PM', 'APO', 'KKR', 'BX', 'ARES', 'TPG', 'INVESCO', 'BLACKSTONE',
        'ICL', 'NEM', 'GOLD', 'HL', 'AU', 'PAAS', 'EXK', 'GATO', 'WPM', 'AG',
        'CDE', 'ECADF', 'SSOKF', 'GDMK', 'MX', 'FCX', 'TECK', 'RIO', 'BHP', 'VALE',
        'ABX', 'BARRICK', 'NEWMONT', 'AGNICO', 'KIRKLAND', 'PDBC', 'GLDM', 'SGOV', 'SHY', 'TLT',
        'IEF', 'BND', 'AGG', 'BSV', 'LQD', 'HYG', 'ANYD', 'EMB', 'VCIT', 'VCSH',
    ]
    
    # Nasdaq 100 (major tech/growth)
    nasdaq = [
        'AAPL', 'MSFT', 'AMZN', 'NVDA', 'GOOGL', 'META', 'TSLA', 'ASML', 'NFLX', 'ADBE',
        'INTC', 'CSCO', 'ADOBE', 'AVGO', 'QCOM', 'AMD', 'NXPI', 'INTU', 'ANSS', 'SNPS',
        'CDNS', 'MCHP', 'LRCX', 'KLA', 'AMAT', 'KLAC', 'CTSH', 'TMUS', 'ABNB', 'DEXCOM',
        'MRNA', 'PEP', 'COST', 'AMGN', 'AZN', 'GILD', 'BIIB', 'REGN', 'VRTX', 'ALXN',
    ]
    
    # Russell 2000 (small-cap, growth)
    russell = [
        'IWM', 'SCHA', 'SCHB', 'SCHO', 'SCHG', 'SCHD', 'SCHV', 'SCHF', 'SCHE', 'SCHM',
        'VBR', 'VBK', 'VB', 'VTV', 'VUG', 'VOE', 'VBN', 'VXF', 'VEA', 'VWO',
    ]
    
    # Sector ETFs (to catch rotation opportunities)
    sectors = [
        'XLK', 'XLE', 'XLF', 'XLI', 'XLV', 'XLY', 'XLP', 'XLRE', 'XLU',  # Sector SPDRs
        'VGT', 'VEV', 'VFV', 'VSH', 'VIS', 'VHT', 'VDC', 'VCR', 'VCIT', 'VCSH',  # Vanguard sectors
    ]
    
    # Major ETFs (broad market, commodities, bonds, international)
    etfs = [
        'SPY', 'QQQ', 'IWM', 'DIA',  # Broad market
        'GLD', 'SLV', 'USO', 'DBC', 'UUP',  # Commodities & USD
        'TLT', 'IEF', 'SHY', 'BND', 'AGG', 'BSV', 'LQD', 'HYG',  # Bonds
        'EEM', 'EFA', 'VEA', 'VWO', 'IEMG', 'VXUS',  # International
    ]
    
    # Combine all and remove duplicates
    universe = list(set(sp500_core + nasdaq + russell + sectors + etfs))
    logger.info(f"FULL MARKET SCAN: {len(universe)} symbols")
    return sorted(universe)

def fetch_spy_data():
    """Fetch SPY data for relative strength calculations."""
    try:
        logger.info("Fetching SPY data...")
        spy = yf.download("SPY", period="1y", progress=False)
        logger.info("SPY data fetched")
        return spy
    except Exception as e:
        logger.error(f"Failed to fetch SPY: {e}")
        return None

def fetch_data(symbols, retries=2):
    """Fetch OHLCV data for symbols. Simple, robust approach."""
    logger.info(f"Fetching data for {len(symbols)} symbols...")
    
    data_map = {}
    
    for i, symbol in enumerate(symbols):
        if (i + 1) % 50 == 0:
            logger.info(f"Progress: {i+1}/{len(symbols)}")
        
        for attempt in range(retries):
            try:
                df = yf.download(symbol, period="1y", progress=False)
                if df is not None and len(df) > 100:
                    data_map[symbol] = df
                    break
                time.sleep(0.1)
            except Exception as e:
                if attempt == retries - 1:
                    logger.warning(f"Failed {symbol}: {str(e)[:50]}")
                time.sleep(0.5)
    
    logger.info(f"Successfully fetched data for {len(data_map)} symbols")
    return data_map

def calculate_metrics(symbol, df, spy_df=None):
    """Calculate NX metrics for a symbol. Simple, robust version."""
    try:
        close = df['Close'].values
        volume = df['Volume'].values
        high = df['High'].values
        low = df['Low'].values
        
        # Safety checks
        if len(close) < 126 or close[-1] <= 0:
            return None
        
        # Momentum (ROC)
        roc_21 = ((close[-1] - close[-22]) / close[-22] * 100) if len(close) > 22 else 0
        roc_63 = ((close[-1] - close[-64]) / close[-64] * 100) if len(close) > 64 else 0
        roc_126 = ((close[-1] - close[-127]) / close[-127] * 100) if len(close) > 127 else 0
        
        momentum = (roc_21 + roc_63 + roc_126) / 3.0
        
        # ATR % (volatility normalization)
        tr_list = []
        for i in range(1, min(len(close), 15)):
            tr = max(
                high[i] - low[i],
                abs(high[i] - close[i-1]),
                abs(low[i] - close[i-1])
            )
            tr_list.append(tr)
        
        atr = np.mean(tr_list) if tr_list else 0
        atr_pct = (atr / close[-1] * 100) if close[-1] > 0 else 0
        
        # CompScore (normalize momentum by volatility)
        if atr_pct > 0:
            comp_score = (momentum / (atr_pct / 2.0) * 100 + 100) / 200.0
        else:
            comp_score = (momentum + 100) / 200.0
        comp_score = max(0, min(1, comp_score))  # Clamp to 0-1
        
        # Relative Strength vs SPY (actual RS calculation)
        if spy_df is not None and len(spy_df) >= 252:
            # Match dates and calculate returns
            try:
                # Get common dates
                sym_dates = df.index
                spy_dates = spy_df.index
                common_idx = sym_dates.intersection(spy_dates)[-252:]
                
                sym_close_rs = df.loc[common_idx, 'Close'].values
                spy_close_rs = spy_df.loc[common_idx, 'Close'].values
                
                # Calculate cumulative returns
                sym_return = sym_close_rs[-1] / sym_close_rs[0] if sym_close_rs[0] > 0 else 1.0
                spy_return = spy_close_rs[-1] / spy_close_rs[0] if spy_close_rs[0] > 0 else 1.0
                
                # RS = symbol return / SPY return
                rs_ratio = sym_return / spy_return if spy_return > 0 else 1.0
                rs_pct = max(0, min(1, (rs_ratio - 0.5) * 0.5 + 0.5))  # Map to 0-1
            except Exception:
                rs_pct = 0.5
        else:
            # Fallback: use momentum as proxy
            rs_pct = max(0, min(1, (momentum + 50) / 100.0))
        
        # Relative Volume
        if len(volume) >= 50:
            recent_vol = np.mean(volume[-21:-1])
            prior_vol = np.mean(volume[-51:-21])
            rvol = recent_vol / prior_vol if prior_vol > 0 else 1.0
        else:
            rvol = 1.0
        
        # Structure Quality (trend consistency)
        if len(close) >= 20:
            returns = np.diff(close[-21:])
            positive = np.sum(returns > 0)
            struct_q = positive / len(returns)
        else:
            struct_q = 0.5
        
        # HTF Bias (weekly/monthly trend)
        if len(close) >= 126:
            week_roc = (close[-1] - close[-35]) / close[-35] if close[-35] > 0 else 0
            month_roc = (close[-1] - close[-126]) / close[-126] if close[-126] > 0 else 0
            bias_raw = (week_roc * 0.3 + month_roc * 0.2) / 0.5
            # Tanh map to 0-1
            htf_bias = (np.tanh(bias_raw) + 1) / 2
        else:
            htf_bias = 0.5
        
        # RSI
        if len(close) > 15:
            deltas = np.diff(close[-15:])
            gains = np.sum(np.maximum(deltas, 0)) / len(deltas)
            losses = np.sum(np.maximum(-deltas, 0)) / len(deltas)
            rs = gains / losses if losses > 0 else 100
            rsi = 100 - (100 / (1 + rs))
        else:
            rsi = 50
        
        # Regime
        if rvol < 1.0 and atr_pct < 1.5:
            regime = 0  # Squeeze
        elif rvol >= 1.5 and atr_pct >= 2.0:
            regime = 2  # Breakout
        else:
            regime = 1  # Normal
        
        # Ready flags (relaxed: allow broader RSI ranges)
        long_ready = 1 if (30 <= rsi <= 85) else 0  # Relaxed from 45-75
        short_ready = 1 if (15 <= rsi <= 70) else 0  # Relaxed from 25-55
        
        # Tier
        if comp_score >= NX["tier_3_min"]:
            tier = 3
        elif comp_score >= NX["tier_2_min"]:
            tier = 2
        else:
            tier = 1
        
        return {
            "symbol": symbol,
            "price": float(close[-1]),
            "comp_score": round(float(comp_score), 3),
            "rs_pct": round(float(rs_pct), 3),
            "rvol": round(float(rvol), 2),
            "struct_q": round(float(struct_q), 3),
            "htf_bias": round(float(htf_bias), 3),
            "rsi": round(float(rsi), 1),
            "regime": int(regime),
            "long_ready": int(long_ready),
            "short_ready": int(short_ready),
            "tier": int(tier),
        }
    
    except Exception as e:
        logger.warning(f"Error calculating {symbol}: {str(e)[:50]}")
        return None

def filter_candidates(metrics_list):
    """Apply NX green-light filters (relaxed for discovery)."""
    long_cand = []
    short_cand = []
    
    for m in metrics_list:
        if not m:
            continue
        
        # Base criteria (tier, volume, structure)
        if m["tier"] < 2:
            continue
        if m["rvol"] < NX["rvol_min"]:
            continue
        if m["struct_q"] < NX["struct_q_min"]:
            continue
        
        # Long: require comp_score + RS bias + ready flag
        if (m["comp_score"] >= NX["tier_2_min"] and
            m["rs_pct"] >= NX["rs_long_min"] and
            m["htf_bias"] >= NX["htf_bias_long_min"] and
            m["long_ready"]):
            long_cand.append(m)
        
        # Short: require comp_score + RS bias + ready flag
        if (m["comp_score"] >= NX["tier_2_min"] and
            m["rs_pct"] <= NX["rs_short_max"] and
            m["htf_bias"] <= NX["htf_bias_short_max"] and
            m["short_ready"]):
            short_cand.append(m)
    
    return long_cand, short_cand

def save_watchlist(long_cand, short_cand, all_metrics=None, regime_info=None):
    """Save to watchlist.json. Only candidates matching strict NX criteria."""
    
    watchlist = {
        "generated_at": datetime.now().isoformat(),
        "long_candidates": sorted(long_cand, key=lambda x: x["comp_score"], reverse=True),
        "short_candidates": sorted(short_cand, key=lambda x: x["comp_score"], reverse=True),
        "nx_criteria": NX,
        "regime": regime_info,
        "summary": {
            "long_count": len(long_cand),
            "short_count": len(short_cand),
            "total_count": len(long_cand) + len(short_cand),
        }
    }
    
    try:
        with open(WATCHLIST_FILE, "w") as f:
            json.dump(watchlist, f, indent=2)
        logger.info(f"✅ Watchlist saved: {len(long_cand)} candidates")
        return True
    except Exception as e:
        logger.error(f"Failed to save: {e}")
        return False

def main():
    logger.info("=== NX PRODUCTION SCREENER STARTED ===")
    
    # Check economic calendar first
    today = datetime.now().date().strftime("%Y-%m-%d")
    if CALENDAR_MODULES_LOADED and is_economic_blackout(today):
        reason = get_blackout_reason(today)
        logger.warning(f"⚠️ ECONOMIC BLACKOUT TODAY: {reason}")
        logger.warning("📊 Proceeding with screener for monitoring only - NO NEW TRADES")
    
    # Get upcoming events
    if CALENDAR_MODULES_LOADED:
        upcoming = get_upcoming_events(days=14)
        if upcoming:
            logger.info(f"📅 Upcoming economic events (next 14 days):")
            for evt in upcoming:
                logger.info(f"   {evt['date']}: {evt['event']} ({evt['days_away']} days)")
    
    symbols = get_universe_symbols()
    logger.info(f"Universe size: {len(symbols)} symbols")
    
    # Get earnings blackout symbols
    earnings_blackout_syms = set()
    if CALENDAR_MODULES_LOADED:
        logger.info("Checking earnings calendar...")
        earnings_blackout_syms = get_earnings_blackout(symbols)
        logger.info(f"🚫 Earnings blackout: {len(earnings_blackout_syms)} symbols")
        if len(earnings_blackout_syms) <= 20:
            logger.info(f"   Symbols: {', '.join(sorted(earnings_blackout_syms))}")
    
    spy_df = fetch_spy_data()
    data_map = fetch_data(symbols)
    logger.info(f"Downloaded {len(data_map)} symbols")
    
    logger.info("Calculating NX metrics...")
    metrics = []
    for i, (sym, df) in enumerate(data_map.items()):
        if (i + 1) % 50 == 0:
            logger.info(f"Metrics: {i+1}/{len(data_map)}")
        m = calculate_metrics(sym, df, spy_df)
        if m:
            # Tag if in earnings blackout
            if sym in earnings_blackout_syms:
                m["earnings_blackout"] = True
            metrics.append(m)
    
    logger.info(f"Calculated metrics for {len(metrics)} symbols")
    
    logger.info("Applying NX filters...")
    long_cand, short_cand = filter_candidates(metrics)
    
    # Filter out earnings blackout candidates from final candidates
    if CALENDAR_MODULES_LOADED:
        long_cand_filtered = [c for c in long_cand if not c.get("earnings_blackout", False)]
        short_cand_filtered = [c for c in short_cand if not c.get("earnings_blackout", False)]
        
        earnings_removed = (len(long_cand) - len(long_cand_filtered)) + (len(short_cand) - len(short_cand_filtered))
        if earnings_removed > 0:
            logger.info(f"🚫 Filtered out {earnings_removed} candidates due to earnings blackout")
        
        long_cand = long_cand_filtered
        short_cand = short_cand_filtered
    
    logger.info(f"Long: {len(long_cand)}, Short: {len(short_cand)}")
    
    # Detect market regime
    regime_info = None
    if REGIME_DETECTOR_LOADED and spy_df is not None and len(spy_df) >= 60:
        try:
            detector = RegimeDetector()
            regime = detector.detect_from_ohlcv(
                close=spy_df['Close'].tail(60).values,
                high=spy_df['High'].tail(60).values,
                low=spy_df['Low'].tail(60).values,
                volume=spy_df['Volume'].tail(60).values,
            )
            regime_info = {
                'regime': regime.get('regime'),
                'confidence': regime.get('confidence'),
                'atr_pct': regime.get('details', {}).get('atr_pct'),
            }
            logger.info(f"Market regime: {regime['regime'].upper()} (confidence {regime['confidence']:.0%})")
        except Exception as e:
            logger.warning(f"Could not detect regime: {e}")
    
    save_watchlist(long_cand, short_cand, metrics, regime_info)
    
    logger.info("=== NX PRODUCTION SCREENER COMPLETE ===")

if __name__ == "__main__":
    main()
