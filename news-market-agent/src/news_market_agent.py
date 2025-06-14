"""
News and Market Data AI Agent

This agent collects, processes, and analyzes news, stock market data, and cryptocurrency information.
It integrates with the MCP system for task management and coordination.
"""

import sys
import os

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
sys.path.append('/opt/.manus/.sandbox-runtime')

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass
import sqlite3
from threading import Thread
import schedule

from mcp_agent_base import SimpleFlaskAgent
from data_api import ApiClient

@dataclass
class NewsArticle:
    """Data class for news articles"""
    title: str
    description: str
    url: str
    source: str
    published_at: datetime
    sentiment: Optional[float] = None
    category: Optional[str] = None

@dataclass
class StockData:
    """Data class for stock market data"""
    symbol: str
    price: float
    change: float
    change_percent: float
    volume: int
    timestamp: datetime
    high_52w: Optional[float] = None
    low_52w: Optional[float] = None

@dataclass
class CryptoData:
    """Data class for cryptocurrency data"""
    symbol: str
    name: str
    price: float
    change_24h: float
    change_percent_24h: float
    timestamp: datetime
    market_cap: Optional[float] = None
    volume_24h: Optional[float] = None

class NewsMarketAgent(SimpleFlaskAgent):
    """AI Agent for collecting and processing news and market data"""
    
    def __init__(self):
        super().__init__(
            agent_id="news-market-agent-enhanced",
            name="News and Market Data Agent with Trading Analysis",
            description="Collects and analyzes news, stock market data, and cryptocurrency information with enhanced trading insights",
            mcp_endpoint="http://localhost:5001",
            agent_port=5004,
            capabilities=[
                "news_collection",
                "stock_data_collection", 
                "crypto_data_collection",
                "sentiment_analysis",
                "market_analysis",
                "trading_insights",
                "technical_analysis"
            ]
        )
        
        # Initialize API client for stock data
        self.api_client = ApiClient()
        
        # Database setup
        self.db_path = os.path.join(os.path.dirname(__file__), 'database', 'market_data.db')
        self.init_database()
        
        # Configuration
        self.news_sources = [
            "https://newsapi.org/v2/top-headlines",
            "https://www.thenewsapi.com/api/v1/news/top"
        ]
        
        # Default stock symbols to track
        self.default_stocks = [
            "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", 
            "NVDA", "META", "NFLX", "AMD", "INTC"
        ]
        
        # Default crypto symbols to track
        self.default_cryptos = [
            "bitcoin", "ethereum", "cardano", "polkadot", 
            "chainlink", "litecoin", "stellar", "dogecoin"
        ]
        
        # Start background data collection
        self.start_background_tasks()
    
    def init_database(self):
        """Initialize SQLite database for storing collected data"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                url TEXT UNIQUE,
                source TEXT,
                published_at TIMESTAMP,
                sentiment REAL,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                change_amount REAL,
                change_percent REAL,
                volume INTEGER,
                high_52w REAL,
                low_52w REAL,
                timestamp TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS crypto_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                name TEXT,
                price REAL NOT NULL,
                change_24h REAL,
                change_percent_24h REAL,
                market_cap REAL,
                volume_24h REAL,
                timestamp TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
        self.logger.info("Database initialized successfully")
    
    def collect_news_data(self) -> List[NewsArticle]:
        """Collect news data from various sources"""
        articles = []
        
        try:
            # Try to get news from free sources
            # Note: In production, you would use actual API keys
            
            # Simulate news collection (replace with actual API calls)
            sample_articles = [
                {
                    "title": "Market Update: Tech Stocks Rally",
                    "description": "Technology stocks showed strong performance today as investors remain optimistic about AI developments.",
                    "url": "https://example.com/tech-rally",
                    "source": "Financial News",
                    "publishedAt": datetime.now().isoformat()
                },
                {
                    "title": "Bitcoin Reaches New Monthly High",
                    "description": "Bitcoin price surged to a new monthly high amid institutional adoption news.",
                    "url": "https://example.com/bitcoin-high",
                    "source": "Crypto News",
                    "publishedAt": datetime.now().isoformat()
                },
                {
                    "title": "Federal Reserve Announces Interest Rate Decision",
                    "description": "The Federal Reserve announced its latest interest rate decision affecting market sentiment.",
                    "url": "https://example.com/fed-rates",
                    "source": "Economic Times",
                    "publishedAt": datetime.now().isoformat()
                }
            ]
            
            for article_data in sample_articles:
                article = NewsArticle(
                    title=article_data["title"],
                    description=article_data["description"],
                    url=article_data["url"],
                    source=article_data["source"],
                    published_at=datetime.fromisoformat(article_data["publishedAt"].replace('Z', '+00:00'))
                )
                articles.append(article)
            
            self.logger.info(f"Collected {len(articles)} news articles")
            
        except Exception as e:
            self.logger.error(f"Error collecting news data: {str(e)}")
        
        return articles
    
    def collect_stock_data(self, symbols: Optional[List[str]] = None) -> List[StockData]:
        """Collect stock market data"""
        if symbols is None:
            symbols = self.default_stocks
        
        stock_data = []
        
        for symbol in symbols:
            try:
                # Use the Yahoo Finance API from Manus API Hub
                response = self.api_client.call_api(
                    'YahooFinance/get_stock_chart',
                    query={
                        'symbol': symbol,
                        'region': 'US',
                        'interval': '1d',
                        'range': '1d'
                    }
                )
                
                if response and 'chart' in response and 'result' in response['chart']:
                    result = response['chart']['result'][0]
                    meta = result.get('meta', {})
                    
                    # Extract current price and other data
                    current_price = meta.get('regularMarketPrice', 0)
                    previous_close = meta.get('chartPreviousClose', current_price)
                    change = current_price - previous_close
                    change_percent = (change / previous_close * 100) if previous_close > 0 else 0
                    
                    stock = StockData(
                        symbol=symbol,
                        price=current_price,
                        change=change,
                        change_percent=change_percent,
                        volume=meta.get('regularMarketVolume', 0),
                        timestamp=datetime.now(),
                        high_52w=meta.get('fiftyTwoWeekHigh'),
                        low_52w=meta.get('fiftyTwoWeekLow')
                    )
                    
                    stock_data.append(stock)
                    self.logger.info(f"Collected data for {symbol}: ${current_price:.2f}")
                
            except Exception as e:
                self.logger.error(f"Error collecting data for {symbol}: {str(e)}")
                continue
        
        return stock_data
    
    def collect_crypto_data(self, symbols: Optional[List[str]] = None) -> List[CryptoData]:
        """Collect cryptocurrency data"""
        if symbols is None:
            symbols = self.default_cryptos
        
        crypto_data = []
        
        try:
            # Use CoinGecko API (free tier)
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': ','.join(symbols),
                'vs_currencies': 'usd',
                'include_24hr_change': 'true',
                'include_market_cap': 'true',
                'include_24hr_vol': 'true'
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                for symbol, coin_data in data.items():
                    crypto = CryptoData(
                        symbol=symbol,
                        name=symbol.replace('-', ' ').title(),
                        price=coin_data.get('usd', 0),
                        change_24h=coin_data.get('usd_24h_change', 0),
                        change_percent_24h=coin_data.get('usd_24h_change', 0),
                        market_cap=coin_data.get('usd_market_cap'),
                        volume_24h=coin_data.get('usd_24h_vol'),
                        timestamp=datetime.now()
                    )
                    
                    crypto_data.append(crypto)
                
                self.logger.info(f"Collected data for {len(crypto_data)} cryptocurrencies")
            
        except Exception as e:
            self.logger.error(f"Error collecting crypto data: {str(e)}")
        
        return crypto_data
    
    def analyze_sentiment(self, text: str) -> float:
        """Simple sentiment analysis (placeholder for more sophisticated analysis)"""
        # This is a very basic sentiment analysis
        # In production, you would use proper NLP libraries like VADER, TextBlob, or transformers
        
        positive_words = ['good', 'great', 'excellent', 'positive', 'up', 'rise', 'gain', 'bull', 'rally', 'surge']
        negative_words = ['bad', 'terrible', 'negative', 'down', 'fall', 'loss', 'bear', 'crash', 'decline', 'drop']
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count + negative_count == 0:
            return 0.0  # Neutral
        
        sentiment = (positive_count - negative_count) / (positive_count + negative_count)
        return sentiment
    
    def store_news_data(self, articles: List[NewsArticle]):
        """Store news articles in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for article in articles:
            # Calculate sentiment
            sentiment = self.analyze_sentiment(f"{article.title} {article.description}")
            
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO news_articles 
                    (title, description, url, source, published_at, sentiment, category)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    article.title,
                    article.description,
                    article.url,
                    article.source,
                    article.published_at,
                    sentiment,
                    article.category
                ))
            except sqlite3.IntegrityError:
                # Article already exists
                continue
        
        conn.commit()
        conn.close()
    
    def store_stock_data(self, stocks: List[StockData]):
        """Store stock data in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for stock in stocks:
            cursor.execute('''
                INSERT INTO stock_data 
                (symbol, price, change_amount, change_percent, volume, high_52w, low_52w, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                stock.symbol,
                stock.price,
                stock.change,
                stock.change_percent,
                stock.volume,
                stock.high_52w,
                stock.low_52w,
                stock.timestamp
            ))
        
        conn.commit()
        conn.close()
    
    def store_crypto_data(self, cryptos: List[CryptoData]):
        """Store cryptocurrency data in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for crypto in cryptos:
            cursor.execute('''
                INSERT INTO crypto_data 
                (symbol, name, price, change_24h, change_percent_24h, market_cap, volume_24h, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                crypto.symbol,
                crypto.name,
                crypto.price,
                crypto.change_24h,
                crypto.change_percent_24h,
                crypto.market_cap,
                crypto.volume_24h,
                crypto.timestamp
            ))
        
        conn.commit()
        conn.close()
    
    def get_latest_data(self, data_type: str, limit: int = 10) -> List[Dict]:
        """Get latest data from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if data_type == 'news':
            cursor.execute('''
                SELECT title, description, url, source, published_at, sentiment, category
                FROM news_articles 
                ORDER BY published_at DESC 
                LIMIT ?
            ''', (limit,))
            
            columns = ['title', 'description', 'url', 'source', 'published_at', 'sentiment', 'category']
            
        elif data_type == 'stocks':
            cursor.execute('''
                SELECT symbol, price, change_amount, change_percent, volume, high_52w, low_52w, timestamp
                FROM stock_data 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            
            columns = ['symbol', 'price', 'change_amount', 'change_percent', 'volume', 'high_52w', 'low_52w', 'timestamp']
            
        elif data_type == 'crypto':
            cursor.execute('''
                SELECT symbol, name, price, change_24h, change_percent_24h, market_cap, volume_24h, timestamp
                FROM crypto_data 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            
            columns = ['symbol', 'name', 'price', 'change_24h', 'change_percent_24h', 'market_cap', 'volume_24h', 'timestamp']
        
        else:
            conn.close()
            return []
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]
    
    def collect_all_data(self):
        """Collect all types of data"""
        try:
            self.logger.info("Starting data collection cycle")
            
            # Collect news
            news_articles = self.collect_news_data()
            if news_articles:
                self.store_news_data(news_articles)
            
            # Collect stock data
            stock_data = self.collect_stock_data()
            if stock_data:
                self.store_stock_data(stock_data)
            
            # Collect crypto data
            crypto_data = self.collect_crypto_data()
            if crypto_data:
                self.store_crypto_data(crypto_data)
            
            self.logger.info("Data collection cycle completed")
            
        except Exception as e:
            self.logger.error(f"Error in data collection cycle: {str(e)}")
    
    def start_background_tasks(self):
        """Start background data collection tasks"""
        # Schedule data collection every 15 minutes
        schedule.every(15).minutes.do(self.collect_all_data)
        
        # Run initial data collection
        Thread(target=self.collect_all_data, daemon=True).start()
        
        # Start scheduler thread
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        
        Thread(target=run_scheduler, daemon=True).start()
        self.logger.info("Background data collection tasks started")
    
    def execute_task(self, task_id: str, task_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tasks assigned by MCP"""
        try:
            if task_type == "collect_news":
                articles = self.collect_news_data()
                self.store_news_data(articles)
                return {
                    "status": "success",
                    "articles_collected": len(articles),
                    "data": [{"title": a.title, "source": a.source} for a in articles[:5]]
                }
            
            elif task_type == "collect_stocks":
                symbols = parameters.get("symbols", self.default_stocks)
                stocks = self.collect_stock_data(symbols)
                self.store_stock_data(stocks)
                return {
                    "status": "success",
                    "stocks_collected": len(stocks),
                    "data": [{"symbol": s.symbol, "price": s.price, "change_percent": s.change_percent} for s in stocks]
                }
            
            elif task_type == "collect_crypto":
                symbols = parameters.get("symbols", self.default_cryptos)
                cryptos = self.collect_crypto_data(symbols)
                self.store_crypto_data(cryptos)
                return {
                    "status": "success",
                    "cryptos_collected": len(cryptos),
                    "data": [{"symbol": c.symbol, "price": c.price, "change_percent_24h": c.change_percent_24h} for c in cryptos]
                }
            
            elif task_type == "get_latest_data":
                data_type = parameters.get("data_type", "news")
                limit = parameters.get("limit", 10)
                data = self.get_latest_data(data_type, limit)
                return {
                    "status": "success",
                    "data_type": data_type,
                    "count": len(data),
                    "data": data
                }
            
            elif task_type == "get_trading_insights":
                symbol = parameters.get("symbol", "bitcoin")
                insights = self.get_trading_insights(symbol)
                return insights
            
            elif task_type == "get_bitcoin_analysis":
                analysis = self.get_bitcoin_analysis_summary()
                return analysis
            
            elif task_type == "collect_all":
                self.collect_all_data()
                return {
                    "status": "success",
                    "message": "All data collection completed"
                }
            
            else:
                return {
                    "status": "error",
                    "message": f"Unknown task type: {task_type}"
                }
                
        except Exception as e:
            self.logger.error(f"Error executing task {task_type}: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_supported_task_types(self) -> List[str]:
        """Return supported task types"""
        return [
            "collect_news",
            "collect_stocks", 
            "collect_crypto",
            "get_latest_data",
            "get_trading_insights",
            "get_bitcoin_analysis",
            "collect_all"
        ]
    
    def get_trading_insights(self, symbol: str = "bitcoin") -> Dict[str, Any]:
        """Generate comprehensive trading insights for a cryptocurrency"""
        try:
            from trading_analysis import TechnicalAnalyzer, TradingInsightGenerator
            
            # Initialize technical analyzer
            analyzer = TechnicalAnalyzer(self.db_path)
            insight_generator = TradingInsightGenerator()
            
            # Get technical analysis
            technical_analysis = analyzer.generate_market_insights(symbol)
            
            # Get current market data
            market_data = {
                "crypto": self.get_latest_data("crypto", 10),
                "news": self.get_latest_data("news", 5)
            }
            
            # Generate trading insights
            daily_insights = insight_generator.generate_daily_trading_insights(
                market_data, technical_analysis
            )
            
            return {
                "status": "success",
                "symbol": symbol,
                "technical_analysis": technical_analysis,
                "daily_insights": daily_insights,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error generating trading insights: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_bitcoin_analysis_summary(self) -> Dict[str, Any]:
        """Get a focused Bitcoin analysis summary for trading purposes"""
        try:
            # Get Bitcoin-specific data
            bitcoin_data = None
            crypto_data = self.get_latest_data("crypto", 10)
            
            for crypto in crypto_data:
                if crypto.get("symbol") == "bitcoin":
                    bitcoin_data = crypto
                    break
            
            if not bitcoin_data:
                return {"status": "error", "message": "Bitcoin data not available"}
            
            # Get trading insights
            trading_insights = self.get_trading_insights("bitcoin")
            
            # Create focused summary
            summary = {
                "current_price": bitcoin_data.get("price", 0),
                "change_24h": bitcoin_data.get("change_percent_24h", 0),
                "volume_24h": bitcoin_data.get("volume_24h", 0),
                "market_cap": bitcoin_data.get("market_cap", 0),
                "timestamp": bitcoin_data.get("timestamp", ""),
                "trading_insights": trading_insights.get("daily_insights", ""),
                "technical_summary": trading_insights.get("technical_analysis", {}).get("summary", {}),
                "analysis_timestamp": datetime.now().isoformat()
            }
            
            return {
                "status": "success",
                "bitcoin_analysis": summary
            }
            
        except Exception as e:
            self.logger.error(f"Error generating Bitcoin analysis summary: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }


if __name__ == "__main__":
    # Create and start the agent
    agent = NewsMarketAgent()
    
    # Create Flask app
    app = agent.create_flask_app()
    
    # Add custom routes for data access
    @app.route('/api/data/<data_type>')
    def get_data_endpoint(data_type):
        from flask import request, jsonify
        limit = request.args.get('limit', 10, type=int)
        data = agent.get_latest_data(data_type, limit)
        return jsonify({
            'data_type': data_type,
            'count': len(data),
            'data': data
        })
    
    @app.route('/api/collect/<data_type>', methods=['POST'])
    def collect_data_endpoint(data_type):
        from flask import jsonify
        try:
            if data_type == 'news':
                articles = agent.collect_news_data()
                agent.store_news_data(articles)
                return jsonify({'status': 'success', 'collected': len(articles)})
            elif data_type == 'stocks':
                stocks = agent.collect_stock_data()
                agent.store_stock_data(stocks)
                return jsonify({'status': 'success', 'collected': len(stocks)})
            elif data_type == 'crypto':
                cryptos = agent.collect_crypto_data()
                agent.store_crypto_data(cryptos)
                return jsonify({'status': 'success', 'collected': len(cryptos)})
            elif data_type == 'all':
                agent.collect_all_data()
                return jsonify({'status': 'success', 'message': 'All data collected'})
            else:
                return jsonify({'status': 'error', 'message': 'Invalid data type'}), 400
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    # Start the agent
    if agent.start():
        # Run Flask app
        agent.run_flask_app()
    else:
        print("Failed to start agent")


    def get_trading_insights(self, symbol: str = "bitcoin") -> Dict[str, Any]:
        """Generate comprehensive trading insights for a cryptocurrency"""
        try:
            from trading_analysis import TechnicalAnalyzer, TradingInsightGenerator
            
            # Initialize technical analyzer
            analyzer = TechnicalAnalyzer(self.db_path)
            insight_generator = TradingInsightGenerator()
            
            # Get technical analysis
            technical_analysis = analyzer.generate_market_insights(symbol)
            
            # Get current market data
            market_data = {
                "crypto": self.get_latest_data("crypto", 10),
                "news": self.get_latest_data("news", 5)
            }
            
            # Generate trading insights
            daily_insights = insight_generator.generate_daily_trading_insights(
                market_data, technical_analysis
            )
            
            return {
                "status": "success",
                "symbol": symbol,
                "technical_analysis": technical_analysis,
                "daily_insights": daily_insights,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error generating trading insights: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_bitcoin_analysis_summary(self) -> Dict[str, Any]:
        """Get a focused Bitcoin analysis summary for trading purposes"""
        try:
            # Get Bitcoin-specific data
            bitcoin_data = None
            crypto_data = self.get_latest_data("crypto", 10)
            
            for crypto in crypto_data:
                if crypto.get("symbol") == "bitcoin":
                    bitcoin_data = crypto
                    break
            
            if not bitcoin_data:
                return {"status": "error", "message": "Bitcoin data not available"}
            
            # Get trading insights
            trading_insights = self.get_trading_insights("bitcoin")
            
            # Create focused summary
            summary = {
                "current_price": bitcoin_data.get("price", 0),
                "change_24h": bitcoin_data.get("change_percent_24h", 0),
                "volume_24h": bitcoin_data.get("volume_24h", 0),
                "market_cap": bitcoin_data.get("market_cap", 0),
                "timestamp": bitcoin_data.get("timestamp", ""),
                "trading_insights": trading_insights.get("daily_insights", ""),
                "technical_summary": trading_insights.get("technical_analysis", {}).get("summary", {}),
                "analysis_timestamp": datetime.now().isoformat()
            }
            
            return {
                "status": "success",
                "bitcoin_analysis": summary
            }
            
        except Exception as e:
            self.logger.error(f"Error generating Bitcoin analysis summary: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }

