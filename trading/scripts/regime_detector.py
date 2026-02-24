#!/usr/bin/env python3
"""
Market Regime Detector
Identifies market conditions:
- BREAKOUT: Strong trending with high volume (best for momentum)
- NORMAL: Steady trend with moderate volume (good for all strategies)
- CHOPPY: High volatility, unclear direction (avoid directional trades)
- SQUEEZE: Low volume, tight range (watch for breakout setup)

Uses: Range, volume, volatility, trend slope
"""

import numpy as np
import logging

logger = logging.getLogger(__name__)

class RegimeDetector:
    """Detects market regime from price/volume data"""
    
    @staticmethod
    def detect_from_ohlcv(close: np.ndarray, high: np.ndarray, low: np.ndarray, volume: np.ndarray) -> dict:
        """
        Detect regime from OHLCV data.
        
        Args:
            close: Close prices (last 60 values)
            high: High prices
            low: Low prices
            volume: Volume
        
        Returns: {
            'regime': 'breakout' | 'normal' | 'choppy' | 'squeeze',
            'confidence': float (0-1),
            'scores': { 'trend', 'volatility', 'volume', 'range' },
            'details': { 'atr', 'slope', 'vol_ratio', 'range_pct' },
        }
        """
        if len(close) < 20:
            return {
                'regime': 'unknown',
                'confidence': 0,
                'error': 'Insufficient data (need 20+ bars)',
            }
        
        # Calculate components
        
        # 1. TREND SLOPE (linear regression on last 20 bars)
        x = np.arange(len(close[-20:]))
        y = close[-20:]
        slope = np.polyfit(x, y, 1)[0]
        slope_pct = (slope / close[-1]) * 100 if close[-1] > 0 else 0
        
        # Normalize slope: ±3% per bar = extreme
        trend_score = min(1.0, abs(slope_pct) / 3.0)
        
        # 2. VOLATILITY (ATR % over last 14 bars)
        tr_list = []
        for i in range(1, min(len(close), 15)):
            tr = max(
                high[-(15-i)] - low[-(15-i)],
                abs(high[-(15-i)] - close[-(16-i)]),
                abs(low[-(15-i)] - close[-(16-i)])
            )
            tr_list.append(tr)
        
        atr = np.mean(tr_list) if tr_list else 0
        atr_pct = (atr / close[-1]) * 100 if close[-1] > 0 else 0
        
        # Normalize volatility: >2% ATR = high volatility
        vol_score = min(1.0, atr_pct / 2.0)
        
        # 3. VOLUME TREND (recent vs prior average)
        if len(volume) >= 50:
            recent_vol = np.mean(volume[-21:-1])
            prior_vol = np.mean(volume[-51:-21])
            vol_ratio = recent_vol / prior_vol if prior_vol > 0 else 1.0
        else:
            vol_ratio = 1.0
        
        # Normalize volume: 1.5x = elevated, 0.5x = depressed
        volume_score = min(1.0, max(0, vol_ratio - 0.5) / 1.0)  # 0.5 to 1.5 → 0 to 1
        
        # 4. RANGE (true range as % of close)
        range_pct = (high[-1] - low[-1]) / close[-1] * 100 if close[-1] > 0 else 0
        
        # Normalize range: 2% = normal, >3% = wide, <1% = tight
        range_score = min(1.0, range_pct / 2.0)
        
        # REGIME CLASSIFICATION
        # SQUEEZE: low vol, low volume, narrow range
        if vol_score < 0.3 and volume_score < 0.3 and range_score < 0.4:
            regime = 'squeeze'
            confidence = 0.8
        
        # CHOPPY: high vol, low trend, unclear direction
        elif vol_score > 0.7 and trend_score < 0.3:
            regime = 'choppy'
            confidence = 0.8
        
        # BREAKOUT: high trend, high vol, high volume
        elif trend_score > 0.6 and vol_score > 0.5 and volume_score > 0.5:
            regime = 'breakout'
            confidence = 0.8
        
        # NORMAL: moderate everything
        else:
            regime = 'normal'
            confidence = 0.6
        
        return {
            'regime': regime,
            'confidence': round(confidence, 2),
            'scores': {
                'trend': round(trend_score, 2),
                'volatility': round(vol_score, 2),
                'volume': round(volume_score, 2),
                'range': round(range_score, 2),
            },
            'details': {
                'atr_pct': round(atr_pct, 2),
                'slope_pct_per_bar': round(slope_pct, 3),
                'vol_ratio': round(vol_ratio, 2),
                'range_pct': round(range_pct, 2),
            },
        }
    
    @staticmethod
    def should_trade_in_regime(regime: str, strategy: str) -> dict:
        """
        Recommend if strategy should trade in this regime.
        
        Args:
            regime: Current regime
            strategy: 'momentum' | 'mean_reversion' | 'breakout' | 'premium_selling'
        
        Returns: {
            'allowed': bool,
            'confidence': float,
            'notes': [str],
        }
        """
        recommendations = {
            'momentum': {
                'breakout': {'allowed': True, 'confidence': 0.95, 'notes': ['Perfect regime for momentum']},
                'normal': {'allowed': True, 'confidence': 0.75, 'notes': ['Good regime, steady trend']},
                'choppy': {'allowed': False, 'confidence': 0.1, 'notes': ['Avoid: unclear direction, false breakouts']},
                'squeeze': {'allowed': False, 'confidence': 0.2, 'notes': ['Too narrow, limited movement']},
            },
            'mean_reversion': {
                'breakout': {'allowed': False, 'confidence': 0.1, 'notes': ['Trend too strong, avoid fading']},
                'normal': {'allowed': True, 'confidence': 0.7, 'notes': ['OK, but limited edge']},
                'choppy': {'allowed': True, 'confidence': 0.8, 'notes': ['Great regime: volatility + chop']},
                'squeeze': {'allowed': False, 'confidence': 0.2, 'notes': ['Too tight to mean-revert']},
            },
            'breakout': {
                'breakout': {'allowed': True, 'confidence': 0.95, 'notes': ['Perfect: already in breakout']},
                'normal': {'allowed': True, 'confidence': 0.6, 'notes': ['OK, watch for breakout setup']},
                'choppy': {'allowed': False, 'confidence': 0.2, 'notes': ['False breakouts likely']},
                'squeeze': {'allowed': True, 'confidence': 0.7, 'notes': ['Setup phase: watch for breakout']},
            },
            'premium_selling': {
                'breakout': {'allowed': False, 'confidence': 0.2, 'notes': ['Too much trend risk, avoid']},
                'normal': {'allowed': True, 'confidence': 0.8, 'notes': ['Good regime for premium']},
                'choppy': {'allowed': True, 'confidence': 0.9, 'notes': ['Excellent: high IV, defined risk']},
                'squeeze': {'allowed': False, 'confidence': 0.1, 'notes': ['Low IV = poor premium']},
            },
        }
        
        if strategy not in recommendations:
            return {'allowed': None, 'error': f'Unknown strategy: {strategy}'}
        
        if regime not in recommendations[strategy]:
            return {'allowed': None, 'error': f'Unknown regime: {regime}'}
        
        rec = recommendations[strategy][regime]
        return {
            'strategy': strategy,
            'regime': regime,
            'allowed': rec['allowed'],
            'confidence': rec['confidence'],
            'notes': rec['notes'],
        }

def get_regime_summary(price_data: dict) -> dict:
    """
    Quick regime summary for a symbol.
    
    Args:
        price_data: Dict with 'close', 'high', 'low', 'volume' arrays
    
    Returns: Summary dict
    """
    detector = RegimeDetector()
    regime = detector.detect_from_ohlcv(
        price_data.get('close'),
        price_data.get('high'),
        price_data.get('low'),
        price_data.get('volume'),
    )
    
    if 'error' in regime:
        return regime
    
    return {
        'regime': regime['regime'],
        'confidence': regime['confidence'],
        'atr_pct': regime['details']['atr_pct'],
        'trend_strength': 'strong' if regime['scores']['trend'] > 0.6 else 'weak',
        'volatility_level': 'high' if regime['scores']['volatility'] > 0.6 else 'normal' if regime['scores']['volatility'] > 0.3 else 'low',
        'volume_status': 'elevated' if regime['scores']['volume'] > 0.6 else 'normal',
        'summary': f"{regime['regime'].upper()} regime (confidence {regime['confidence']:.0%})",
    }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test data: simple uptrend with volume increase
    print("\n=== Test: Regime Detection ===")
    close = np.array([100 + i*0.5 for i in range(60)])  # Steady uptrend
    high = close + 0.5
    low = close - 0.5
    volume = np.array([1000000] * 30 + [1500000] * 30)  # Volume increase
    
    detector = RegimeDetector()
    result = detector.detect_from_ohlcv(close, high, low, volume)
    print(f"Regime: {result['regime'].upper()}")
    print(f"Confidence: {result['confidence']:.0%}")
    print(f"Scores: {result['scores']}")
    
    print("\n=== Test: Should Trade? ===")
    strategies = ['momentum', 'mean_reversion', 'breakout', 'premium_selling']
    for strat in strategies:
        rec = detector.should_trade_in_regime(result['regime'], strat)
        status = "✅ YES" if rec['allowed'] else "❌ NO"
        print(f"{strat:18}: {status} (confidence {rec['confidence']:.0%})")
        if rec['notes']:
            print(f"  {rec['notes'][0]}")
    
    print("\n=== Test: Choppy Regime ===")
    close_choppy = np.array([100 + np.random.normal(0, 1) for _ in range(60)])  # Random chop
    high_choppy = close_choppy + 2
    low_choppy = close_choppy - 2
    volume_choppy = np.random.normal(1000000, 100000, 60)
    
    result_choppy = detector.detect_from_ohlcv(close_choppy, high_choppy, low_choppy, volume_choppy)
    print(f"Regime: {result_choppy['regime'].upper()}")
    for strat in ['momentum', 'premium_selling']:
        rec = detector.should_trade_in_regime(result_choppy['regime'], strat)
        status = "✅" if rec['allowed'] else "❌"
        print(f"  {strat}: {status} {rec['notes'][0]}")
