"""
Blog Creation and Content Management AI Agent

This agent generates blog posts based on news and market data collected by the News and Market Data Agent.
It creates engaging, informative content and manages the publishing workflow.
"""

import sys
import os

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass
import sqlite3
from threading import Thread
import re
import random

from mcp_agent_base import SimpleFlaskAgent

@dataclass
class BlogPost:
    """Data class for blog posts"""
    title: str
    content: str
    summary: str
    tags: List[str]
    category: str
    status: str  # draft, published, scheduled
    created_at: datetime
    published_at: Optional[datetime] = None
    author: str = "AI Market Analyst"
    featured_image_url: Optional[str] = None

class BlogCreationAgent(SimpleFlaskAgent):
    """AI Agent for creating and managing blog content"""
    
    def __init__(self):
        super().__init__(
            agent_id="blog-creation-agent",
            name="Blog Creation and Content Management Agent",
            description="Generates blog posts based on market data and news analysis",
            mcp_endpoint="http://localhost:5001",
            agent_port=5003,
            capabilities=[
                "blog_generation",
                "content_creation",
                "market_analysis_writing",
                "news_summarization",
                "content_management"
            ]
        )
        
        # News and Market Data Agent endpoint
        self.news_agent_endpoint = "http://localhost:5002"
        
        # Database setup
        self.db_path = os.path.join(os.path.dirname(__file__), 'database', 'blog_content.db')
        self.init_database()
        
        # Content templates and styles
        self.blog_templates = {
            "market_update": {
                "title_templates": [
                    "Market Update: {focus} Shows {trend} Movement",
                    "Today's Market Spotlight: {focus} {trend}",
                    "Market Analysis: {focus} Trends and Insights",
                    "Financial Focus: Understanding {focus} Performance"
                ],
                "intro_templates": [
                    "In today's dynamic financial landscape, {focus} has captured the attention of investors and analysts alike.",
                    "The financial markets continue to evolve, with {focus} emerging as a key area of interest.",
                    "Market participants are closely watching {focus} as recent developments shape investment strategies."
                ]
            },
            "crypto_analysis": {
                "title_templates": [
                    "Cryptocurrency Spotlight: {crypto} Analysis and Trends",
                    "Digital Assets Update: {crypto} Market Movement",
                    "Crypto Market Insights: {crypto} Performance Review",
                    "Blockchain Focus: {crypto} Investment Perspective"
                ],
                "intro_templates": [
                    "The cryptocurrency market remains one of the most dynamic sectors in finance, with {crypto} showing notable activity.",
                    "Digital asset investors are keeping a close eye on {crypto} as market conditions continue to evolve.",
                    "In the ever-changing world of cryptocurrencies, {crypto} presents interesting opportunities and challenges."
                ]
            },
            "news_summary": {
                "title_templates": [
                    "Market News Roundup: Key Developments and Analysis",
                    "Financial News Digest: Today's Important Updates",
                    "Market Movers: News That's Shaping Today's Trading",
                    "Economic Insights: Breaking Down Today's Headlines"
                ],
                "intro_templates": [
                    "Today's financial news brings several important developments that could impact market sentiment and investment decisions.",
                    "Staying informed about market-moving news is crucial for investors navigating today's complex financial environment.",
                    "The intersection of global events and financial markets creates opportunities for informed investors to understand emerging trends."
                ]
            }
        }
    
    def init_database(self):
        """Initialize SQLite database for storing blog content"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create blog posts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blog_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                summary TEXT,
                tags TEXT,  -- JSON string
                category TEXT,
                status TEXT DEFAULT 'draft',
                author TEXT DEFAULT 'AI Market Analyst',
                featured_image_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                published_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create content sources table (tracks what data was used)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                blog_post_id INTEGER,
                source_type TEXT,  -- news, stock, crypto
                source_data TEXT,  -- JSON string of source data
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (blog_post_id) REFERENCES blog_posts (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        self.logger.info("Blog database initialized successfully")
    
    def fetch_market_data(self) -> Dict[str, Any]:
        """Fetch latest market data from the News and Market Data Agent"""
        try:
            # Fetch news data
            news_response = requests.get(f"{self.news_agent_endpoint}/api/data/news?limit=5", timeout=10)
            news_data = news_response.json() if news_response.status_code == 200 else {"data": []}
            
            # Fetch stock data
            stocks_response = requests.get(f"{self.news_agent_endpoint}/api/data/stocks?limit=10", timeout=10)
            stocks_data = stocks_response.json() if stocks_response.status_code == 200 else {"data": []}
            
            # Fetch crypto data
            crypto_response = requests.get(f"{self.news_agent_endpoint}/api/data/crypto?limit=8", timeout=10)
            crypto_data = crypto_response.json() if crypto_response.status_code == 200 else {"data": []}
            
            return {
                "news": news_data.get("data", []),
                "stocks": stocks_data.get("data", []),
                "crypto": crypto_data.get("data", [])
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching market data: {str(e)}")
            return {"news": [], "stocks": [], "crypto": []}
    
    def analyze_market_trends(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market data to identify trends and insights"""
        analysis = {
            "top_gainers": [],
            "top_losers": [],
            "market_sentiment": "neutral",
            "key_themes": [],
            "crypto_trends": [],
            "news_sentiment": "neutral"
        }
        
        try:
            # Analyze stock performance
            stocks = market_data.get("stocks", [])
            if stocks:
                # Sort by change percentage
                sorted_stocks = sorted(stocks, key=lambda x: x.get("change_percent", 0), reverse=True)
                analysis["top_gainers"] = sorted_stocks[:3]
                analysis["top_losers"] = sorted_stocks[-3:]
                
                # Calculate overall market sentiment
                positive_changes = sum(1 for stock in stocks if stock.get("change_percent", 0) > 0)
                total_stocks = len(stocks)
                if total_stocks > 0:
                    positive_ratio = positive_changes / total_stocks
                    if positive_ratio > 0.6:
                        analysis["market_sentiment"] = "bullish"
                    elif positive_ratio < 0.4:
                        analysis["market_sentiment"] = "bearish"
            
            # Analyze crypto trends
            crypto = market_data.get("crypto", [])
            if crypto:
                crypto_sorted = sorted(crypto, key=lambda x: x.get("change_percent_24h", 0), reverse=True)
                analysis["crypto_trends"] = crypto_sorted[:5]
            
            # Analyze news sentiment
            news = market_data.get("news", [])
            if news:
                sentiments = [article.get("sentiment", 0) for article in news if article.get("sentiment") is not None]
                if sentiments:
                    avg_sentiment = sum(sentiments) / len(sentiments)
                    if avg_sentiment > 0.2:
                        analysis["news_sentiment"] = "positive"
                    elif avg_sentiment < -0.2:
                        analysis["news_sentiment"] = "negative"
                
                # Extract key themes from news titles
                themes = []
                for article in news:
                    title = article.get("title", "").lower()
                    if "bitcoin" in title or "crypto" in title:
                        themes.append("cryptocurrency")
                    if "fed" in title or "interest" in title or "rate" in title:
                        themes.append("monetary_policy")
                    if "tech" in title or "ai" in title:
                        themes.append("technology")
                    if "market" in title or "stock" in title:
                        themes.append("equity_markets")
                
                analysis["key_themes"] = list(set(themes))
        
        except Exception as e:
            self.logger.error(f"Error analyzing market trends: {str(e)}")
        
        return analysis
    
    def generate_blog_content(self, content_type: str, market_data: Dict[str, Any], analysis: Dict[str, Any]) -> BlogPost:
        """Generate blog post content based on market data and analysis"""
        
        if content_type == "market_update":
            return self._generate_market_update(market_data, analysis)
        elif content_type == "crypto_analysis":
            return self._generate_crypto_analysis(market_data, analysis)
        elif content_type == "news_summary":
            return self._generate_news_summary(market_data, analysis)
        else:
            # Default to market update
            return self._generate_market_update(market_data, analysis)
    
    def _generate_market_update(self, market_data: Dict[str, Any], analysis: Dict[str, Any]) -> BlogPost:
        """Generate a market update blog post"""
        
        # Determine focus based on market sentiment
        sentiment = analysis.get("market_sentiment", "neutral")
        trend_word = "Mixed" if sentiment == "neutral" else ("Strong" if sentiment == "bullish" else "Cautious")
        
        # Select template
        template = self.blog_templates["market_update"]
        title = random.choice(template["title_templates"]).format(
            focus="Technology Stocks" if "technology" in analysis.get("key_themes", []) else "Major Indices",
            trend=trend_word
        )
        
        intro = random.choice(template["intro_templates"]).format(
            focus="the technology sector" if "technology" in analysis.get("key_themes", []) else "major market indices"
        )
        
        # Generate content sections
        content_sections = []
        content_sections.append(f"## Market Overview\n\n{intro}")
        
        # Top performers section
        if analysis.get("top_gainers"):
            content_sections.append("\n## Top Performers\n")
            content_sections.append("Several stocks demonstrated strong performance in today's trading session:")
            for i, stock in enumerate(analysis["top_gainers"][:3], 1):
                symbol = stock.get("symbol", "N/A")
                price = stock.get("price", 0)
                change_pct = stock.get("change_percent", 0)
                content_sections.append(f"\n**{i}. {symbol}** - ${price:.2f} ({change_pct:+.2f}%)")
                
                # Add context based on stock
                if symbol == "AAPL":
                    content_sections.append("Apple continues to benefit from strong iPhone demand and services growth.")
                elif symbol == "TSLA":
                    content_sections.append("Tesla's performance reflects ongoing investor confidence in electric vehicle adoption.")
                elif symbol == "NVDA":
                    content_sections.append("NVIDIA remains at the forefront of the artificial intelligence revolution.")
                else:
                    content_sections.append(f"{symbol} showed resilience amid current market conditions.")
        
        # Market challenges section
        if analysis.get("top_losers"):
            content_sections.append("\n## Market Challenges\n")
            content_sections.append("Some sectors faced headwinds during today's session:")
            for i, stock in enumerate(analysis["top_losers"][:3], 1):
                symbol = stock.get("symbol", "N/A")
                price = stock.get("price", 0)
                change_pct = stock.get("change_percent", 0)
                content_sections.append(f"\n**{symbol}** - ${price:.2f} ({change_pct:+.2f}%)")
        
        # News impact section
        news_articles = market_data.get("news", [])
        if news_articles:
            content_sections.append("\n## Market-Moving News\n")
            content_sections.append("Today's market movement was influenced by several key developments:")
            
            for article in news_articles[:3]:
                title = article.get("title", "")
                description = article.get("description", "")
                source = article.get("source", "")
                
                content_sections.append(f"\n**{title}** ({source})")
                content_sections.append(f"{description}")
        
        # Outlook section
        content_sections.append("\n## Market Outlook\n")
        if sentiment == "bullish":
            content_sections.append("The current market environment suggests continued optimism among investors. Key factors supporting this positive sentiment include strong corporate earnings, technological innovation, and favorable economic indicators. However, investors should remain vigilant about potential volatility and maintain diversified portfolios.")
        elif sentiment == "bearish":
            content_sections.append("Market participants are exercising caution as various headwinds create uncertainty. While challenges exist, experienced investors often view market corrections as opportunities to reassess portfolios and identify quality investments at attractive valuations.")
        else:
            content_sections.append("The market is currently in a consolidation phase, with investors weighing various economic and geopolitical factors. This environment often presents opportunities for selective stock picking and strategic portfolio positioning.")
        
        content_sections.append("\n## Investment Considerations\n")
        content_sections.append("As always, investors should conduct thorough research and consider their risk tolerance before making investment decisions. Diversification across asset classes and geographic regions remains a fundamental principle of sound portfolio management. Market volatility, while challenging, can also create opportunities for long-term investors with patience and discipline.")
        
        # Combine all sections
        full_content = "\n".join(content_sections)
        
        # Generate summary
        summary = f"Today's market analysis covering top performers, key challenges, and market-moving news. {trend_word} sentiment observed across major indices with insights for investors."
        
        # Generate tags
        tags = ["market-analysis", "stocks", "investing", "financial-markets"]
        if "technology" in analysis.get("key_themes", []):
            tags.append("technology")
        if "cryptocurrency" in analysis.get("key_themes", []):
            tags.append("crypto")
        
        return BlogPost(
            title=title,
            content=full_content,
            summary=summary,
            tags=tags,
            category="Market Analysis",
            status="draft",
            created_at=datetime.now()
        )
    
    def _generate_crypto_analysis(self, market_data: Dict[str, Any], analysis: Dict[str, Any]) -> BlogPost:
        """Generate a cryptocurrency analysis blog post"""
        
        crypto_data = market_data.get("crypto", [])
        if not crypto_data:
            # Fallback to market update if no crypto data
            return self._generate_market_update(market_data, analysis)
        
        # Find Bitcoin data for focus
        bitcoin_data = next((crypto for crypto in crypto_data if crypto.get("symbol") == "bitcoin"), crypto_data[0])
        
        template = self.blog_templates["crypto_analysis"]
        title = random.choice(template["title_templates"]).format(
            crypto="Bitcoin" if bitcoin_data.get("symbol") == "bitcoin" else bitcoin_data.get("name", "Cryptocurrency")
        )
        
        intro = random.choice(template["intro_templates"]).format(
            crypto="Bitcoin" if bitcoin_data.get("symbol") == "bitcoin" else bitcoin_data.get("name", "this cryptocurrency")
        )
        
        content_sections = []
        content_sections.append(f"## Cryptocurrency Market Overview\n\n{intro}")
        
        # Bitcoin/main crypto analysis
        btc_price = bitcoin_data.get("price", 0)
        btc_change = bitcoin_data.get("change_percent_24h", 0)
        btc_name = bitcoin_data.get("name", "Bitcoin")
        
        content_sections.append(f"\n## {btc_name} Performance Analysis\n")
        content_sections.append(f"{btc_name} is currently trading at ${btc_price:,.2f}, representing a {btc_change:+.2f}% change over the past 24 hours.")
        
        if btc_change > 2:
            content_sections.append(f"This positive momentum reflects growing institutional adoption and increased retail interest in digital assets. The cryptocurrency market continues to mature, with {btc_name} leading the charge as the flagship digital currency.")
        elif btc_change < -2:
            content_sections.append(f"The recent price movement reflects normal market volatility that is characteristic of the cryptocurrency space. Long-term investors often view such corrections as opportunities to accumulate positions in quality digital assets.")
        else:
            content_sections.append(f"The relatively stable price action suggests a period of consolidation, which often precedes significant market movements. This stability can be viewed positively as it demonstrates the maturing nature of the cryptocurrency market.")
        
        # Top crypto performers
        crypto_trends = analysis.get("crypto_trends", [])
        if crypto_trends:
            content_sections.append("\n## Cryptocurrency Market Leaders\n")
            content_sections.append("Several digital assets are showing notable performance:")
            
            for i, crypto in enumerate(crypto_trends[:5], 1):
                name = crypto.get("name", "Unknown")
                price = crypto.get("price", 0)
                change = crypto.get("change_percent_24h", 0)
                market_cap = crypto.get("market_cap", 0)
                
                content_sections.append(f"\n**{i}. {name}** - ${price:,.4f} ({change:+.2f}%)")
                if market_cap:
                    content_sections.append(f"Market Cap: ${market_cap:,.0f}")
        
        # Market insights
        content_sections.append("\n## Market Insights and Trends\n")
        content_sections.append("The cryptocurrency market continues to evolve with several key trends shaping its development:")
        
        content_sections.append("\n**Institutional Adoption**: Major corporations and financial institutions are increasingly recognizing cryptocurrencies as legitimate asset classes, driving long-term demand and market stability.")
        
        content_sections.append("\n**Regulatory Clarity**: Ongoing regulatory developments worldwide are providing clearer frameworks for cryptocurrency operations, reducing uncertainty and encouraging institutional participation.")
        
        content_sections.append("\n**Technological Innovation**: Continuous improvements in blockchain technology, including scalability solutions and energy efficiency, are enhancing the utility and appeal of cryptocurrencies.")
        
        # Investment perspective
        content_sections.append("\n## Investment Perspective\n")
        content_sections.append("Cryptocurrency investments require careful consideration of several factors. While the potential for significant returns exists, investors must also acknowledge the inherent volatility and regulatory risks associated with digital assets.")
        
        content_sections.append("\nDiversification within the cryptocurrency space, as well as across traditional asset classes, remains crucial for risk management. Investors should only allocate capital they can afford to lose and should conduct thorough research before making investment decisions.")
        
        content_sections.append("\nThe long-term outlook for cryptocurrencies remains positive, driven by increasing adoption, technological advancement, and growing recognition as a legitimate asset class. However, short-term volatility should be expected and planned for accordingly.")
        
        full_content = "\n".join(content_sections)
        
        summary = f"Comprehensive analysis of {btc_name} and the broader cryptocurrency market, including performance insights and investment considerations."
        
        tags = ["cryptocurrency", "bitcoin", "blockchain", "digital-assets", "investing"]
        
        return BlogPost(
            title=title,
            content=full_content,
            summary=summary,
            tags=tags,
            category="Cryptocurrency Analysis",
            status="draft",
            created_at=datetime.now()
        )
    
    def _generate_news_summary(self, market_data: Dict[str, Any], analysis: Dict[str, Any]) -> BlogPost:
        """Generate a news summary blog post"""
        
        news_articles = market_data.get("news", [])
        if not news_articles:
            # Fallback to market update if no news
            return self._generate_market_update(market_data, analysis)
        
        template = self.blog_templates["news_summary"]
        title = random.choice(template["title_templates"])
        intro = random.choice(template["intro_templates"])
        
        content_sections = []
        content_sections.append(f"## Today's Financial News Digest\n\n{intro}")
        
        # Key headlines section
        content_sections.append("\n## Key Headlines\n")
        for i, article in enumerate(news_articles[:5], 1):
            article_title = article.get("title", "")
            description = article.get("description", "")
            source = article.get("source", "")
            sentiment = article.get("sentiment", 0)
            
            content_sections.append(f"\n### {i}. {article_title}")
            content_sections.append(f"*Source: {source}*")
            content_sections.append(f"\n{description}")
            
            # Add sentiment context
            if sentiment > 0.3:
                content_sections.append("\n*Market Impact: Positive sentiment - This development could support market confidence.*")
            elif sentiment < -0.3:
                content_sections.append("\n*Market Impact: Cautious sentiment - Investors may exercise increased vigilance.*")
            else:
                content_sections.append("\n*Market Impact: Neutral sentiment - Balanced implications for market participants.*")
        
        # Market implications
        content_sections.append("\n## Market Implications\n")
        news_sentiment = analysis.get("news_sentiment", "neutral")
        
        if news_sentiment == "positive":
            content_sections.append("Today's news flow carries predominantly positive implications for financial markets. The combination of favorable economic indicators, corporate developments, and policy announcements suggests a supportive environment for investor confidence.")
        elif news_sentiment == "negative":
            content_sections.append("The current news environment presents some challenges for market participants. While negative headlines can create short-term volatility, experienced investors often view such periods as opportunities to reassess market conditions and identify potential value.")
        else:
            content_sections.append("Today's news presents a balanced mix of developments, reflecting the complex nature of modern financial markets. This environment requires careful analysis and selective decision-making from investors.")
        
        # Key themes analysis
        key_themes = analysis.get("key_themes", [])
        if key_themes:
            content_sections.append("\n## Emerging Themes\n")
            content_sections.append("Several key themes are emerging from today's news flow:")
            
            for theme in key_themes:
                if theme == "cryptocurrency":
                    content_sections.append("\n**Digital Assets**: Continued evolution in the cryptocurrency space with regulatory and adoption developments.")
                elif theme == "monetary_policy":
                    content_sections.append("\n**Monetary Policy**: Central bank communications and interest rate considerations remain focal points for investors.")
                elif theme == "technology":
                    content_sections.append("\n**Technology Innovation**: Ongoing developments in artificial intelligence and digital transformation continue to shape market dynamics.")
                elif theme == "equity_markets":
                    content_sections.append("\n**Equity Markets**: Stock market performance and corporate earnings remain central to investor decision-making.")
        
        # Investor takeaways
        content_sections.append("\n## Investor Takeaways\n")
        content_sections.append("In navigating today's news environment, investors should consider several key principles:")
        
        content_sections.append("\n**Stay Informed**: Regular monitoring of financial news helps investors understand market-moving developments and their potential implications.")
        
        content_sections.append("\n**Maintain Perspective**: While daily news can create short-term market movements, long-term investment success typically depends on fundamental analysis and strategic planning.")
        
        content_sections.append("\n**Risk Management**: Diversification and appropriate position sizing remain essential tools for managing portfolio risk in dynamic market conditions.")
        
        content_sections.append("\n**Opportunity Recognition**: Market volatility driven by news events can create opportunities for disciplined investors with clear investment criteria.")
        
        full_content = "\n".join(content_sections)
        
        summary = "Comprehensive roundup of today's key financial news with market implications and investor insights."
        
        tags = ["financial-news", "market-analysis", "investing", "economic-updates"]
        if "cryptocurrency" in key_themes:
            tags.append("cryptocurrency")
        if "technology" in key_themes:
            tags.append("technology")
        
        return BlogPost(
            title=title,
            content=full_content,
            summary=summary,
            tags=tags,
            category="News Analysis",
            status="draft",
            created_at=datetime.now()
        )
    
    def save_blog_post(self, blog_post: BlogPost, source_data: Dict[str, Any]) -> int:
        """Save blog post to database and return post ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Insert blog post
        cursor.execute('''
            INSERT INTO blog_posts 
            (title, content, summary, tags, category, status, author, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            blog_post.title,
            blog_post.content,
            blog_post.summary,
            json.dumps(blog_post.tags),
            blog_post.category,
            blog_post.status,
            blog_post.author,
            blog_post.created_at
        ))
        
        blog_post_id = cursor.lastrowid
        
        # Insert source data references
        for source_type, data in source_data.items():
            if data:  # Only insert if there's actual data
                cursor.execute('''
                    INSERT INTO content_sources 
                    (blog_post_id, source_type, source_data)
                    VALUES (?, ?, ?)
                ''', (
                    blog_post_id,
                    source_type,
                    json.dumps(data)
                ))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Blog post saved with ID: {blog_post_id}")
        return blog_post_id
    
    def get_blog_posts(self, limit: int = 10, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve blog posts from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT id, title, content, summary, tags, category, status, author, 
                   featured_image_url, created_at, published_at, updated_at
            FROM blog_posts
        '''
        params = []
        
        if status:
            query += ' WHERE status = ?'
            params.append(status)
        
        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        columns = ['id', 'title', 'content', 'summary', 'tags', 'category', 'status', 
                  'author', 'featured_image_url', 'created_at', 'published_at', 'updated_at']
        
        posts = []
        for row in rows:
            post = dict(zip(columns, row))
            # Parse JSON fields
            post['tags'] = json.loads(post['tags']) if post['tags'] else []
            posts.append(post)
        
        return posts
    
    def publish_blog_post(self, post_id: int) -> bool:
        """Publish a blog post (change status to published)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE blog_posts 
                SET status = 'published', published_at = ?, updated_at = ?
                WHERE id = ?
            ''', (datetime.now(), datetime.now(), post_id))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Blog post {post_id} published successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error publishing blog post {post_id}: {str(e)}")
            return False
    
    def execute_task(self, task_id: str, task_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tasks assigned by MCP"""
        try:
            if task_type == "generate_blog":
                content_type = parameters.get("content_type", "market_update")
                
                # Fetch market data
                market_data = self.fetch_market_data()
                
                # Analyze trends
                analysis = self.analyze_market_trends(market_data)
                
                # Generate blog post
                blog_post = self.generate_blog_content(content_type, market_data, analysis)
                
                # Save to database
                post_id = self.save_blog_post(blog_post, market_data)
                
                return {
                    "status": "success",
                    "post_id": post_id,
                    "title": blog_post.title,
                    "category": blog_post.category,
                    "word_count": len(blog_post.content.split()),
                    "tags": blog_post.tags
                }
            
            elif task_type == "publish_blog":
                post_id = parameters.get("post_id")
                if not post_id:
                    return {"status": "error", "message": "Missing post_id parameter"}
                
                success = self.publish_blog_post(post_id)
                return {
                    "status": "success" if success else "error",
                    "message": f"Blog post {post_id} {'published' if success else 'failed to publish'}"
                }
            
            elif task_type == "get_blog_posts":
                limit = parameters.get("limit", 10)
                status = parameters.get("status")
                
                posts = self.get_blog_posts(limit, status)
                return {
                    "status": "success",
                    "count": len(posts),
                    "posts": posts
                }
            
            elif task_type == "generate_daily_content":
                # Generate multiple types of content for daily publishing
                results = []
                
                market_data = self.fetch_market_data()
                analysis = self.analyze_market_trends(market_data)
                
                # Generate market update
                market_post = self.generate_blog_content("market_update", market_data, analysis)
                market_id = self.save_blog_post(market_post, market_data)
                results.append({"type": "market_update", "post_id": market_id, "title": market_post.title})
                
                # Generate crypto analysis if crypto data available
                if market_data.get("crypto"):
                    crypto_post = self.generate_blog_content("crypto_analysis", market_data, analysis)
                    crypto_id = self.save_blog_post(crypto_post, market_data)
                    results.append({"type": "crypto_analysis", "post_id": crypto_id, "title": crypto_post.title})
                
                # Generate news summary if news available
                if market_data.get("news"):
                    news_post = self.generate_blog_content("news_summary", market_data, analysis)
                    news_id = self.save_blog_post(news_post, market_data)
                    results.append({"type": "news_summary", "post_id": news_id, "title": news_post.title})
                
                return {
                    "status": "success",
                    "generated_posts": len(results),
                    "posts": results
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
            "generate_blog",
            "publish_blog",
            "get_blog_posts",
            "generate_daily_content"
        ]


if __name__ == "__main__":
    # Create and start the agent
    agent = BlogCreationAgent()
    
    # Create Flask app
    app = agent.create_flask_app()
    
    # Add custom routes for blog management
    @app.route('/api/blog/posts')
    def get_posts_endpoint():
        from flask import request, jsonify
        limit = request.args.get('limit', 10, type=int)
        status = request.args.get('status')
        posts = agent.get_blog_posts(limit, status)
        return jsonify({
            'count': len(posts),
            'posts': posts
        })
    
    @app.route('/api/blog/posts/<int:post_id>')
    def get_post_endpoint(post_id):
        from flask import jsonify
        posts = agent.get_blog_posts(limit=1)
        post = next((p for p in posts if p['id'] == post_id), None)
        if post:
            return jsonify(post)
        else:
            return jsonify({'error': 'Post not found'}), 404
    
    @app.route('/api/blog/generate', methods=['POST'])
    def generate_blog_endpoint():
        from flask import request, jsonify
        try:
            data = request.json or {}
            content_type = data.get('content_type', 'market_update')
            
            # Execute blog generation
            result = agent.execute_task(
                task_id="manual_generation",
                task_type="generate_blog",
                parameters={"content_type": content_type}
            )
            
            return jsonify(result)
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    @app.route('/api/blog/posts/<int:post_id>/publish', methods=['POST'])
    def publish_post_endpoint(post_id):
        from flask import jsonify
        try:
            result = agent.execute_task(
                task_id="manual_publish",
                task_type="publish_blog",
                parameters={"post_id": post_id}
            )
            return jsonify(result)
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    # Start the agent
    if agent.start():
        # Run Flask app
        agent.run_flask_app()
    else:
        print("Failed to start agent")

