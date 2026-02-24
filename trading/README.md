# Trading Automation System - Quick Start

**Status:** ✅ FULLY OPERATIONAL & HARDENED  
**Last Updated:** February 21, 2026 @ 7:39 PM MST

---

## 🚀 What's Running

```
✅ Webhook Listener (5001)     → TradingView alerts to Telegram
✅ IB Gateway API (4002)       → Paper trading connected
✅ Daily P&L Tracker           → Enforces $1,350/day loss limit
✅ News Monitor                → Market-moving event alerts
✅ Automated Scanner           → Breakout detection (7:30-14:00 MT)
✅ Audit Logging               → All connections logged
```

---

## 🔐 Security Status

| Layer | Status | Location |
|-------|--------|----------|
| Credentials | ✅ Secure (600 perms) | `~/.openclaw/workspace/trading/.env` |
| Firewall | ✅ Hardened | Localhost-only (127.0.0.1) |
| Audit Trail | ✅ Active | `logs/audit.log` |
| Git Protection | ✅ Ready | `.env` in `.gitignore` |
| Auto-Disconnect | ✅ 30 min idle | IB API timeout |
| Rate Limiting | ✅ 100ms | API request delay |

---

## 📝 Daily Checklist

**Morning (7:00 AM)**
```bash
# Check if scanner is ready
ps aux | grep automated_scanner | grep -v grep
```

**Trading Hours (7:30 AM - 2:00 PM)**
```bash
# Monitor alerts
tail -f logs/audit.log

# Check daily loss limit
python3 scripts/daily_pnl_tracker.py
```

**End of Day (4:00 PM)**
```bash
# View portfolio summary
ps aux | grep webhook_listener | grep -v grep
```

---

## ⚠️ Critical Rules

1. **Never share `.env` file** — Contains secrets
2. **Never commit `.env` to git** — Already in `.gitignore`
3. **Monitor audit.log weekly** — Security review
4. **Keep IB Gateway running** — API depends on it

---

## 🆘 Emergency Commands

```bash
# Kill all trading services
pkill -f webhook_listener
pkill -f daily_pnl_tracker
pkill -f news_monitor
pkill -f automated_scanner

# Restart everything
cd ~/.openclaw/workspace/trading && python3 scripts/webhook_listener.py &

# Check status
ps aux | grep -E "webhook|pnl|news|scanner" | grep -v grep

# View real-time logs
tail -f logs/audit.log logs/portfolio_tracker.log logs/news_monitor.log
```

---

## 📚 Full Documentation

- **Detailed Setup:** `TRADING-AUTOMATION-BUILT.md`
- **Architecture:** See `trading/` directory structure
- **Logs:** All in `logs/` — organized by component

---

## 🎯 Next Steps (When Ready)

1. **Enable email reports** — Daily 4 PM portfolio summary
2. **Add SMS alerts** — For loss limit violations
3. **Position-level stops** — Automated stop-loss
4. **Advanced screening** — Custom screener integration

---

## 💬 Support

**System stable?** → Monitor `audit.log` for anomalies  
**Alert not working?** → Check Telegram bot token in `.env`  
**API disconnected?** → Restart IB Gateway, verify port 4002 open  
**High CPU?** → Scanner might be running outside hours (check logs)

---

**Everything is ready. Your trading infrastructure is live.** 🚀
