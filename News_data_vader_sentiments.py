import yfinance as yf
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import requests
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv

# Download NLTK data for sentiment analysis
nltk.download('vader_lexicon')
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')

import re
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer, PorterStemmer
from nltk.tokenize import word_tokenize

load_dotenv()
NEWS_API = os.getenv("NewsApi")


def clean_text(text):
    # Remove special characters and digits
    text = re.sub(r'\W|\d', ' ', text)
    # Remove extra whitespaces
    text = re.sub(r'\s+', ' ', text)
    # Convert to lowercase
    text = text.lower()
    # Tokenize text
    tokens = word_tokenize(text)
    # Remove stopwords
    stop_words = set(stopwords.words('english'))
    filtered_tokens = [word for word in tokens if word not in stop_words]
    # Lemmatize tokens
    lemmatizer = WordNetLemmatizer()
    lemmatized_tokens = [lemmatizer.lemmatize(word) for word in filtered_tokens]
    # Stem tokens
    stemmer = PorterStemmer()
    stemmed_tokens = [stemmer.stem(word) for word in lemmatized_tokens]
    # Join tokens back into text
    cleaned_text = ' '.join(stemmed_tokens)
    return cleaned_text



# Function to analyze sentiment of a text
def analyze_sentiment(text):
    
    sia = SentimentIntensityAnalyzer()
    if text is not None:
        compound_score = sia.polarity_scores(text)['compound']
        if compound_score >= 0.05:
            return 'Positive'
        elif compound_score <= -0.05:
            return 'Negative'
        else:
            return 'Neutral'
    else:
        compound_score = 0  # Assign a neutral sentiment if text is None
    return 'Neutral'

# Function to get stock information using yfinance
def get_stock_info(ticker):
    stock_data = yf.Ticker(ticker)
    return stock_data.info

# Function to get financial news and analyze sentiment
def get_news_sentiment(ticker):
    news_url = f'https://newsapi.org/v2/everything?q={ticker}&apiKey={NEWS_API}'  # Replace 'your-api-key' with an actual API key if needed

    response = requests.get(news_url)
    news_data = response.json()
    news_list = []
    if 'articles' in news_data:
        for article in news_data['articles']:
            title = article['title']
            description = article.get('description', '')
            
            if title is not None:
                # Analyze sentiment of title and description
                clean_title = clean_text(title)
                title_sentiment = analyze_sentiment(clean_title)
            if description is not None:
                
                clean_description  = clean_text(description)
                description_sentiment = analyze_sentiment(clean_description)

            # print(f"Title: {title}")
            # print(f"Title_sentiment: {title_sentiment}")
            # print(f"Description: {description}")
            # print(f"Description_sentiment: {description_sentiment}")
            # print("\n")
            
            news_list.append({'Title': title, 'Title_sentiment': title_sentiment,
                              'Description': description, 'Description_sentiment': description_sentiment})
    news_df = pd.DataFrame(news_list)
    get_date = datetime.today().date()
    get_date = str(get_date)
    news_df['date'] = get_date

    
    return news_df

# # Example usage
# if __name__ == "__main__":
#     stock_ticker = 'paytm'  # Replace with the desired stock ticker
#     get_news_sentiment(stock_ticker)
#     stock_info = get_stock_info(stock_ticker)
#     print("Stock Information:")
#     display(stock_info)