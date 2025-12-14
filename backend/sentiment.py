import yfinance as yf
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import logging

# Ensure VADER lexicon is downloaded
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon')

def get_stock_sentiment(symbol: str) -> dict:
    """
    Fetches news for a stock symbol from yfinance and calculates average sentiment.
    Returns:
        dict: {
            "score": float (-1 to 1),
            "label": str (Bullish/Bearish/Neutral),
            "news_count": int
        }
    """
    try:
        if not symbol.endswith(".NS"):
            symbol = f"{symbol}.NS"
            
        ticker = yf.Ticker(symbol)
        news = ticker.news
        
        if not news:
            return {"score": 0, "label": "Neutral", "news_count": 0}
            
        sia = SentimentIntensityAnalyzer()
        total_score = 0
        count = 0
        
        for article in news:
            title = article.get('title', '')
            if title:
                # Compound score ranges from -1 (Extremely Negative) to 1 (Extremely Positive)
                score = sia.polarity_scores(title)['compound']
                total_score += score
                count += 1
                
        if count == 0:
             return {"score": 0, "label": "Neutral", "news_count": 0}
             
        avg_score = total_score / count
        
        # Determine Label
        if avg_score > 0.05:
            label = "Bullish"
        elif avg_score < -0.05:
            label = "Bearish"
        else:
            label = "Neutral"
            
        return {
            "score": round(avg_score, 2),
            "label": label,
            "news_count": count
        }
        
    except Exception as e:
        logging.error(f"Error fetching sentiment for {symbol}: {e}")
        return {"score": 0, "label": "Neutral", "error": str(e), "news_count": 0}
