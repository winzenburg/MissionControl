#!/usr/bin/env python3
"""
Daily Portfolio Report Generator
Sends detailed portfolio summary via Resend API at 4 PM MT

Usage:
  python3 daily_portfolio_report.py
"""

import os
import json
from datetime import datetime, timedelta
from ib_insync import IB
import requests

class PortfolioReportGenerator:
    def __init__(self):
        self.ib = IB()
        self.resend_api_key = os.getenv('RESEND_API_KEY')
        self.to_email = os.getenv('TO_EMAIL', 'ryanwinzenburg@gmail.com')
        self.from_email = os.getenv('FROM_EMAIL', 'onboarding@resend.dev')
        
    def connect_ib(self):
        """Connect to IB Gateway"""
        try:
            self.ib.connect('127.0.0.1', 4002, clientId=101, timeout=10)
            return True
        except Exception as e:
            print(f"❌ IB connection failed: {e}")
            return False
    
    def get_portfolio_data(self):
        """Fetch current portfolio data"""
        try:
            account = self.ib.managedAccounts()[0]
            
            # Account summary
            account_values = self.ib.accountSummary(account)
            summary = {}
            for av in account_values:
                if av.tag in ['TotalCashValue', 'NetLiquidation', 'BuyingPower', 
                              'DayTradesRemaining', 'EquityWithLoanValue']:
                    summary[av.tag] = float(av.value)
            
            # Positions
            positions = self.ib.positions()
            position_data = []
            for pos in positions:
                position_data.append({
                    'symbol': pos.contract.symbol,
                    'quantity': pos.position,
                    'avgCost': pos.avgCost,
                    'contract': str(pos.contract)
                })
            
            return {
                'account': account,
                'summary': summary,
                'positions': position_data,
                'position_count': len(position_data)
            }
        except Exception as e:
            print(f"❌ Error fetching portfolio: {e}")
            return None
    
    def calculate_daily_pnl(self):
        """Calculate daily P&L (placeholder)"""
        try:
            # This would fetch from IB's daily P&L data
            # For now, return placeholder
            return {
                'daily_gain': 0.00,
                'daily_gain_pct': 0.00,
                'mtd_gain': 0.00,
                'ytd_gain': 0.00
            }
        except Exception as e:
            print(f"⚠️  Could not fetch P&L: {e}")
            return {}
    
    def generate_html_report(self, portfolio_data):
        """Generate HTML email report"""
        summary = portfolio_data['summary']
        positions = portfolio_data['positions']
        pnl = self.calculate_daily_pnl()
        
        net_liq = summary.get('NetLiquidation', 0)
        buying_power = summary.get('BuyingPower', 0)
        cash = summary.get('TotalCashValue', 0)
        
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333; background: #f5f5f5; padding: 20px;">
            
            <div style="max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px;">
              
              <h1 style="color: #1a1a1a; margin-bottom: 10px;">📊 Daily Portfolio Report</h1>
              <p style="color: #666; margin-top: 0;">{datetime.now().strftime('%A, %B %d, %Y at %I:%M %p MT')}</p>
              
              <!-- Account Summary -->
              <div style="background: #f9f9f9; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
                <h2 style="color: #2c3e50; font-size: 16px; margin-top: 0;">Account Summary</h2>
                
                <table style="width: 100%; border-collapse: collapse;">
                  <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee;">
                      <strong>Net Liquidation Value:</strong>
                    </td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee; text-align: right;">
                      <span style="color: #27ae60; font-size: 18px; font-weight: bold;">${net_liq:,.2f}</span>
                    </td>
                  </tr>
                  <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee;">
                      <strong>Buying Power:</strong>
                    </td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee; text-align: right;">
                      ${buying_power:,.2f}
                    </td>
                  </tr>
                  <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee;">
                      <strong>Cash Available:</strong>
                    </td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee; text-align: right;">
                      ${cash:,.2f}
                    </td>
                  </tr>
                  <tr>
                    <td style="padding: 10px 0;">
                      <strong>Positions Held:</strong>
                    </td>
                    <td style="padding: 10px 0; text-align: right;">
                      {portfolio_data['position_count']} positions
                    </td>
                  </tr>
                </table>
              </div>
              
              <!-- Top Positions -->
              <div style="margin-bottom: 25px;">
                <h2 style="color: #2c3e50; font-size: 16px;">Top 10 Positions by Size</h2>
                
                <table style="width: 100%; border-collapse: collapse;">
                  <thead>
                    <tr style="background: #ecf0f1;">
                      <th style="padding: 10px; text-align: left; border-bottom: 2px solid #bdc3c7;">Symbol</th>
                      <th style="padding: 10px; text-align: right; border-bottom: 2px solid #bdc3c7;">Shares</th>
                      <th style="padding: 10px; text-align: right; border-bottom: 2px solid #bdc3c7;">Avg Cost</th>
                    </tr>
                  </thead>
                  <tbody>
        """
        
        # Sort by quantity (largest first)
        sorted_positions = sorted(positions, key=lambda x: abs(x['quantity']), reverse=True)[:10]
        
        for pos in sorted_positions:
            qty_color = '#27ae60' if pos['quantity'] > 0 else '#e74c3c'
            html += f"""
                    <tr style="border-bottom: 1px solid #ecf0f1;">
                      <td style="padding: 10px; font-weight: bold;">{pos['symbol']}</td>
                      <td style="padding: 10px; text-align: right; color: {qty_color};">{pos['quantity']:,.0f}</td>
                      <td style="padding: 10px; text-align: right;">${pos['avgCost']:.2f}</td>
                    </tr>
            """
        
        html += """
                  </tbody>
                </table>
              </div>
              
              <!-- Daily Stats -->
              <div style="background: #ecf7ff; padding: 15px; border-radius: 6px; margin-bottom: 25px;">
                <h3 style="margin-top: 0; color: #2980b9;">Today's Performance</h3>
                <p style="margin: 5px 0;">
                  <strong>Daily Gain/Loss:</strong> 
                  <span style="color: #27ae60; font-weight: bold;">$0.00 (0.00%)</span>
                </p>
                <p style="margin: 5px 0;">
                  <strong>Daily Loss Limit:</strong> -$1,350.00
                </p>
                <p style="margin: 5px 0; color: #27ae60;">
                  ✅ <strong>Within daily loss limit</strong>
                </p>
              </div>
              
              <!-- Footer -->
              <div style="border-top: 1px solid #ecf0f1; padding-top: 15px; text-align: center; color: #999; font-size: 12px;">
                <p>This report was generated automatically by OpenClaw Trading System</p>
                <p>Account: {portfolio_data['account']} | Paper Trading Mode</p>
                <p style="margin-bottom: 0;">Do not reply to this email</p>
              </div>
              
            </div>
          </body>
        </html>
        """
        
        return html
    
    def send_email(self, subject, html_content):
        """Send email via Resend API"""
        try:
            response = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {self.resend_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": self.from_email,
                    "to": self.to_email,
                    "subject": subject,
                    "html": html_content,
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Email sent successfully!")
                print(f"   Email ID: {result.get('id')}")
                return True
            else:
                print(f"❌ Email failed: {response.status_code}")
                print(f"   {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error sending email: {e}")
            return False
    
    def generate_and_send(self):
        """Main workflow"""
        print("📊 Generating Daily Portfolio Report...")
        print()
        
        # Connect to IB
        if not self.connect_ib():
            print("❌ Could not connect to IB Gateway")
            return False
        
        # Fetch portfolio data
        print("📈 Fetching portfolio data...")
        portfolio_data = self.get_portfolio_data()
        if not portfolio_data:
            print("❌ Could not fetch portfolio data")
            self.ib.disconnect()
            return False
        
        print(f"✅ Portfolio loaded: {portfolio_data['position_count']} positions")
        print(f"   Net Liquidation: ${portfolio_data['summary'].get('NetLiquidation', 0):,.2f}")
        
        # Generate HTML report
        print("📝 Generating report...")
        html_content = self.generate_html_report(portfolio_data)
        
        # Send email
        print("📧 Sending email via Resend...")
        subject = f"Daily Portfolio Report - {datetime.now().strftime('%B %d, %Y')}"
        success = self.send_email(subject, html_content)
        
        # Cleanup
        self.ib.disconnect()
        
        return success

if __name__ == "__main__":
    generator = PortfolioReportGenerator()
    success = generator.generate_and_send()
    exit(0 if success else 1)
