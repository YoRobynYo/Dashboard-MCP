"""
Enhanced Trading Analysis Module for News and Market Data Agent

This module adds sophisticated technical analysis capabilities specifically focused on Bitcoin
and cryptocurrency trading patterns. It provides analytical insights without giving financial advice.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import sqlite3
import logging

class TechnicalAnalyzer:
    """Technical analysis tools for cryptocurrency market data"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
    
    def get_historical_data(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """Retrieve historical price data for analysis"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Get data from the last N days
            cutoff_date = datetime.now() - timedelta(days=days)
            
            query = '''
                SELECT price, change_24h, change_percent_24h, volume_24h, timestamp
                FROM crypto_data 
                WHERE symbol = ? AND timestamp >= ?
                ORDER BY timestamp ASC
            '''
            
            df = pd.read_sql_query(query, conn, params=(symbol, cutoff_date))
            conn.close()
            
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error retrieving historical data for {symbol}: {str(e)}")
            return pd.DataFrame()
    
    def calculate_moving_averages(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate various moving averages"""
        if df.empty or len(df) < 7:
            return {}
        
        try:
            prices = df['price']
            
            ma_data = {}
            
            # Short-term moving averages
            if len(prices) >= 7:
                ma_data['ma_7'] = prices.tail(7).mean()
            if len(prices) >= 14:
                ma_data['ma_14'] = prices.tail(14).mean()
            if len(prices) >= 21:
                ma_data['ma_21'] = prices.tail(21).mean()
            
            # Current price for comparison
            ma_data['current_price'] = prices.iloc[-1]
            
            return ma_data
            
        except Exception as e:
            self.logger.error(f"Error calculating moving averages: {str(e)}")
            return {}
    
    def calculate_volatility(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate price volatility metrics"""
        if df.empty or len(df) < 7:
            return {}
        
        try:
            prices = df['price']
            returns = prices.pct_change().dropna()
            
            volatility_data = {
                'daily_volatility': returns.std(),
                'price_range_7d': (prices.tail(7).max() - prices.tail(7).min()) / prices.tail(7).mean(),
                'avg_daily_change': abs(df['change_percent_24h'].tail(7).mean())
            }
            
            return volatility_data
            
        except Exception as e:
            self.logger.error(f"Error calculating volatility: {str(e)}")
            return {}
    
    def identify_price_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Identify basic price patterns and trends"""
        if df.empty or len(df) < 7:
            return {}
        
        try:
            prices = df['price'].tail(7)  # Last 7 data points
            
            patterns = {}
            
            # Trend analysis
            if len(prices) >= 3:
                recent_trend = "neutral"
                price_changes = prices.diff().dropna()
                
                positive_changes = sum(1 for change in price_changes if change > 0)
                negative_changes = sum(1 for change in price_changes if change < 0)
                
                if positive_changes > negative_changes * 1.5:
                    recent_trend = "upward"
                elif negative_changes > positive_changes * 1.5:
                    recent_trend = "downward"
                
                patterns['recent_trend'] = recent_trend
            
            # Support and resistance levels (simplified)
            if len(prices) >= 5:
                patterns['recent_high'] = prices.max()
                patterns['recent_low'] = prices.min()
                patterns['price_position'] = (prices.iloc[-1] - prices.min()) / (prices.max() - prices.min()) if prices.max() != prices.min() else 0.5
            
            # Volume analysis if available
            if 'volume_24h' in df.columns:
                volumes = df['volume_24h'].tail(7)
                patterns['avg_volume'] = volumes.mean()
                patterns['volume_trend'] = "increasing" if volumes.iloc[-1] > volumes.mean() else "decreasing"
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Error identifying price patterns: {str(e)}")
            return {}
    
    def analyze_market_momentum(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze market momentum indicators"""
        if df.empty or len(df) < 7:
            return {}
        
        try:
            momentum_data = {}
            
            # Price momentum
            prices = df['price']
            if len(prices) >= 7:
                momentum_data['price_momentum_7d'] = (prices.iloc[-1] - prices.iloc[-7]) / prices.iloc[-7] * 100
            
            # Change consistency
            changes = df['change_percent_24h'].tail(7)
            positive_days = sum(1 for change in changes if change > 0)
            momentum_data['positive_days_ratio'] = positive_days / len(changes)
            
            # Momentum strength
            avg_abs_change = abs(changes).mean()
            momentum_data['momentum_strength'] = "high" if avg_abs_change > 3 else ("medium" if avg_abs_change > 1.5 else "low")
            
            return momentum_data
            
        except Exception as e:
            self.logger.error(f"Error analyzing momentum: {str(e)}")
            return {}
    
    def generate_market_insights(self, symbol: str) -> Dict[str, Any]:
        """Generate comprehensive market insights for a cryptocurrency"""
        try:
            # Get historical data
            df = self.get_historical_data(symbol, days=30)
            
            if df.empty:
                return {"error": "Insufficient data for analysis"}
            
            insights = {
                "symbol": symbol,
                "analysis_timestamp": datetime.now().isoformat(),
                "data_points": len(df)
            }
            
            # Technical indicators
            insights["moving_averages"] = self.calculate_moving_averages(df)
            insights["volatility"] = self.calculate_volatility(df)
            insights["patterns"] = self.identify_price_patterns(df)
            insights["momentum"] = self.analyze_market_momentum(df)
            
            # Generate summary insights
            insights["summary"] = self._generate_insight_summary(insights)
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error generating market insights for {symbol}: {str(e)}")
            return {"error": str(e)}
    
    def _generate_insight_summary(self, insights: Dict[str, Any]) -> Dict[str, str]:
        """Generate human-readable summary of technical analysis"""
        summary = {}
        
        try:
            # Moving average analysis
            ma_data = insights.get("moving_averages", {})
            if ma_data:
                current_price = ma_data.get("current_price", 0)
                ma_7 = ma_data.get("ma_7", 0)
                
                if current_price and ma_7:
                    if current_price > ma_7 * 1.02:
                        summary["price_vs_ma"] = "Price is trading above short-term average, suggesting recent strength"
                    elif current_price < ma_7 * 0.98:
                        summary["price_vs_ma"] = "Price is trading below short-term average, indicating recent weakness"
                    else:
                        summary["price_vs_ma"] = "Price is trading near short-term average, showing consolidation"
            
            # Volatility analysis
            volatility = insights.get("volatility", {})
            if volatility:
                avg_change = volatility.get("avg_daily_change", 0)
                if avg_change > 5:
                    summary["volatility"] = "High volatility observed - significant price movements expected"
                elif avg_change > 2:
                    summary["volatility"] = "Moderate volatility - normal market fluctuations"
                else:
                    summary["volatility"] = "Low volatility - relatively stable price action"
            
            # Trend analysis
            patterns = insights.get("patterns", {})
            if patterns:
                trend = patterns.get("recent_trend", "neutral")
                if trend == "upward":
                    summary["trend"] = "Recent upward trend observed in price action"
                elif trend == "downward":
                    summary["trend"] = "Recent downward trend noted in price movement"
                else:
                    summary["trend"] = "Sideways price action with no clear directional bias"
            
            # Momentum analysis
            momentum = insights.get("momentum", {})
            if momentum:
                strength = momentum.get("momentum_strength", "medium")
                positive_ratio = momentum.get("positive_days_ratio", 0.5)
                
                if positive_ratio > 0.7:
                    summary["momentum"] = f"Strong positive momentum with {strength} intensity"
                elif positive_ratio < 0.3:
                    summary["momentum"] = f"Negative momentum observed with {strength} intensity"
                else:
                    summary["momentum"] = f"Mixed momentum signals with {strength} intensity"
            
        except Exception as e:
            self.logger.error(f"Error generating insight summary: {str(e)}")
            summary["error"] = "Unable to generate summary"
        
        return summary


class TradingInsightGenerator:
    """Generates trading-focused insights and educational content"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_daily_trading_insights(self, market_data: Dict[str, Any], technical_analysis: Dict[str, Any]) -> str:
        """Generate daily trading insights based on market data and technical analysis"""
        
        insights_sections = []
        
        # Header
        insights_sections.append("# Daily Bitcoin Trading Analysis")
        insights_sections.append(f"*Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}*")
        insights_sections.append("\n**Disclaimer**: This analysis is for educational purposes only and does not constitute financial advice. Always conduct your own research and consider your risk tolerance before making trading decisions.")
        
        # Current Market Overview
        bitcoin_data = None
        crypto_data = market_data.get("crypto", [])
        for crypto in crypto_data:
            if crypto.get("symbol") == "bitcoin":
                bitcoin_data = crypto
                break
        
        if bitcoin_data:
            price = bitcoin_data.get("price", 0)
            change_24h = bitcoin_data.get("change_percent_24h", 0)
            volume = bitcoin_data.get("volume_24h", 0)
            
            insights_sections.append("\n## Current Market Snapshot")
            insights_sections.append(f"**Bitcoin Price**: ${price:,.2f}")
            insights_sections.append(f"**24h Change**: {change_24h:+.2f}%")
            insights_sections.append(f"**24h Volume**: ${volume:,.0f}")
            
            # Price action context
            if abs(change_24h) > 3:
                insights_sections.append(f"\n*Notable price movement of {change_24h:+.2f}% indicates increased market activity and potential trading opportunities.*")
            elif abs(change_24h) < 1:
                insights_sections.append(f"\n*Relatively stable price action with {change_24h:+.2f}% change suggests consolidation phase.*")
            else:
                insights_sections.append(f"\n*Moderate price movement of {change_24h:+.2f}% reflects normal market dynamics.*")
        
        # Technical Analysis Insights
        if technical_analysis and "summary" in technical_analysis:
            insights_sections.append("\n## Technical Analysis Highlights")
            
            summary = technical_analysis["summary"]
            for key, insight in summary.items():
                if key != "error":
                    insights_sections.append(f"**{key.replace('_', ' ').title()}**: {insight}")
        
        # Market Context and News Impact
        news_data = market_data.get("news", [])
        crypto_related_news = [article for article in news_data if 
                             "bitcoin" in article.get("title", "").lower() or 
                             "crypto" in article.get("title", "").lower()]
        
        if crypto_related_news:
            insights_sections.append("\n## News Impact Analysis")
            insights_sections.append("Recent cryptocurrency-related news that may influence trading sentiment:")
            
            for article in crypto_related_news[:3]:
                title = article.get("title", "")
                sentiment = article.get("sentiment", 0)
                
                sentiment_text = "Positive" if sentiment > 0.2 else ("Negative" if sentiment < -0.2 else "Neutral")
                insights_sections.append(f"\n- **{title}** (Sentiment: {sentiment_text})")
        
        # Trading Considerations
        insights_sections.append("\n## Key Trading Considerations")
        
        # Volatility considerations
        if technical_analysis and "volatility" in technical_analysis:
            volatility = technical_analysis["volatility"]
            avg_change = volatility.get("avg_daily_change", 0)
            
            if avg_change > 4:
                insights_sections.append("**High Volatility Environment**: Current market conditions show elevated volatility. This can create opportunities for experienced traders but also increases risk. Consider using smaller position sizes and tighter risk management.")
            elif avg_change < 2:
                insights_sections.append("**Low Volatility Environment**: Reduced price swings may limit short-term trading opportunities but could indicate accumulation phases. Range-bound strategies might be more suitable.")
            else:
                insights_sections.append("**Moderate Volatility**: Normal market conditions with typical price fluctuations. Standard trading approaches and risk management techniques apply.")
        
        # Trend considerations
        if technical_analysis and "patterns" in technical_analysis:
            patterns = technical_analysis["patterns"]
            trend = patterns.get("recent_trend", "neutral")
            
            if trend == "upward":
                insights_sections.append("**Upward Trend Observed**: Recent price action suggests bullish momentum. Traders might consider trend-following strategies while being mindful of potential resistance levels.")
            elif trend == "downward":
                insights_sections.append("**Downward Trend Noted**: Recent price movement indicates bearish pressure. Caution is advised, and traders should be aware of potential support levels.")
            else:
                insights_sections.append("**Sideways Movement**: Lack of clear directional bias suggests range-bound trading. Support and resistance levels become more important in this environment.")
        
        # Risk Management Reminders
        insights_sections.append("\n## Risk Management Principles")
        insights_sections.append("Regardless of market conditions, fundamental risk management principles remain crucial:")
        insights_sections.append("- Never risk more than you can afford to lose")
        insights_sections.append("- Use appropriate position sizing based on your account size")
        insights_sections.append("- Set clear entry and exit criteria before entering trades")
        insights_sections.append("- Consider using stop-loss orders to limit potential losses")
        insights_sections.append("- Diversify across different time frames and strategies")
        insights_sections.append("- Keep detailed records of your trading decisions and outcomes")
        
        # Educational Note
        insights_sections.append("\n## Educational Focus")
        insights_sections.append("Successful trading requires continuous learning and adaptation. Key areas for ongoing education include:")
        insights_sections.append("- Understanding market cycles and their characteristics")
        insights_sections.append("- Learning to read price charts and identify patterns")
        insights_sections.append("- Developing emotional discipline and psychological resilience")
        insights_sections.append("- Staying informed about regulatory developments and market news")
        insights_sections.append("- Practicing with small amounts before scaling up")
        
        return "\n".join(insights_sections)
    
    def generate_weekly_trading_summary(self, weekly_data: List[Dict[str, Any]]) -> str:
        """Generate weekly trading summary and insights"""
        
        if not weekly_data:
            return "Insufficient data for weekly analysis."
        
        summary_sections = []
        
        summary_sections.append("# Weekly Bitcoin Trading Summary")
        summary_sections.append(f"*Week ending: {datetime.now().strftime('%Y-%m-%d')}*")
        
        # Calculate weekly statistics
        prices = [day.get("price", 0) for day in weekly_data if day.get("price")]
        if prices:
            week_high = max(prices)
            week_low = min(prices)
            week_range = ((week_high - week_low) / week_low) * 100
            
            summary_sections.append(f"\n## Weekly Price Action")
            summary_sections.append(f"**Weekly High**: ${week_high:,.2f}")
            summary_sections.append(f"**Weekly Low**: ${week_low:,.2f}")
            summary_sections.append(f"**Weekly Range**: {week_range:.2f}%")
            
            if week_range > 10:
                summary_sections.append("\n*High weekly volatility observed - significant trading opportunities but increased risk.*")
            elif week_range < 5:
                summary_sections.append("\n*Low weekly volatility - more stable conditions but limited short-term opportunities.*")
        
        # Weekly trend analysis
        if len(prices) >= 2:
            weekly_change = ((prices[-1] - prices[0]) / prices[0]) * 100
            summary_sections.append(f"\n**Weekly Performance**: {weekly_change:+.2f}%")
            
            if weekly_change > 5:
                summary_sections.append("Strong weekly performance suggests bullish sentiment.")
            elif weekly_change < -5:
                summary_sections.append("Weak weekly performance indicates bearish pressure.")
            else:
                summary_sections.append("Moderate weekly performance shows balanced market conditions.")
        
        return "\n".join(summary_sections)

