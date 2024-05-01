import yfinance as yf
import pandas as pd
from statsmodels.tsa.ar_model import AutoReg
import seaborn as sns
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from io import BytesIO
import matplotlib.pyplot as plt
import boto3
import os
from dotenv import load_dotenv
import uuid

load_dotenv()

aws_secret_access_key = os.getenv("aws_secret_access_key")
aws_access_key_id = os.getenv("aws_access_key_id")


def get_stock_info(symbol):
    """
    Retrieve detailed information and historical OHLC prices for a given stock symbol.
    Args:
    - symbol (str): Stock symbol for which to retrieve information.
    Returns:
    - info (dict): Detailed information about the stock.
    - history (DataFrame): Historical OHLC prices and other financial data.
    - df_info (DataFrame): Returning dataframe from info dictonary
    """
    # Create Ticker object for the specified symbol
    ticker = yf.Ticker(symbol)
    # Get detailed information about the stock symbol
    info = ticker.info
    # Get historical OHLC prices and other financial data
    history = ticker.history(period="6mo")
    history.reset_index(drop=False, inplace=True)
    history['Date'] = history['Date'].dt.date
    history['symbol'] = symbol

    # Create DataFrame for detailed information
    keys = list(info.keys())
    values = list(info.values())
    df_info = pd.DataFrame({'Key': keys, 'Value': values})
    return df_info, history


def EDA_analysis(data):
    company_name = data.symbol.unique()[0]
    data = data.drop(columns=['symbol'])

    # Initialize Boto3 S3 client
    s3 = boto3.client('s3', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
    bucket_name = 'rjbigdataimages'
    unique_id = uuid.uuid4()
    file_name = f'{company_name}_{unique_id}.png'

    # Store URLs of uploaded images
    uploaded_image_urls = []

    # Time Series Plot
    plt.figure(figsize=(10, 6))
    plt.plot(data['Date'], data['High'], label='High', marker='o')
    plt.plot(data['Date'], data['Low'], label='Low', marker='o')
    plt.plot(data['Date'], data['Open'], label='Open', marker='o')
    plt.plot(data['Date'], data['Close'], label='Close', marker='o')
    plt.title('Stock Prices Over Time')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    upload_plot(plt, f'time_series_{file_name}', s3, bucket_name, uploaded_image_urls)
    plt.close()

    # Volume Plot 
    plt.figure(figsize=(10, 6))
    plt.plot(data['Date'], data['Volume'], label='Volume', color='orange', marker='o')
    plt.title('Trading Volume Over Time')
    plt.xlabel('Date')
    plt.ylabel('Volume')
    plt.gca().get_yaxis().get_major_formatter().set_scientific(False)  # Display actual numbers on the y-axis
    plt.legend()
    upload_plot(plt, f'volume_vs_date_{file_name}', s3, bucket_name, uploaded_image_urls)
    plt.close()

    # Average Price by Month
    data['Date'] = pd.to_datetime(data['Date'])
    data['Month'] = data['Date'].dt.month
    seasonal_data = data.groupby('Month')['High'].mean()
    seasonal_data.plot(kind='bar')
    plt.title('Average High Price by Month')
    plt.xlabel('Month')
    plt.ylabel('Average High Price: ' + company_name)
    upload_plot(plt, f'avg_high_price_{file_name}', s3, bucket_name, uploaded_image_urls)
    plt.close()

    #Time Series Decomposition
    result = seasonal_decompose(data['High'], model='additive', period=1)  # Assuming no seasonality
    result.plot()
    upload_plot(plt, f'series_decomposition_{file_name}', s3, bucket_name, uploaded_image_urls)
    plt.close()

    print("All images uploaded successfully to S3.")
    print("Uploaded Image URLs:")
    file_urls_dict = {}
    for url in uploaded_image_urls:
        file_name = url.split("/")[-1].split("_")[0]
        file_urls_dict[file_name] = url

    return file_urls_dict


def upload_plot(plt, filename, s3, bucket_name, uploaded_image_urls):
    # Save plot to BytesIO object
    img_data = BytesIO()
    plt.savefig(img_data, format='png')
    img_data.seek(0)  # Rewind the buffer

    # Upload to S3
    s3.upload_fileobj(img_data, bucket_name, filename)

    # Create public URL
    image_url = f"https://{bucket_name}.s3.amazonaws.com/{filename}"
    uploaded_image_urls.append(image_url)

    print(f"Image '{filename}' uploaded successfully to S3.")
    print(f"URL: {image_url}")



# Function to predict next day's high and low prices for each company
def predict_next_day_prices(company_df):
    # Shift the high and low prices to get next day's high and low
    company_df['Next_High'] = company_df['High'].shift(-1)
    company_df['Next_Low'] = company_df['Low'].shift(-1)
    print("company next data", company_df['Next_Low'])
    # Drop NaN rows resulting from the shift
    company_df.dropna(inplace=True)

    # Features and target variables
    X = company_df[['Open', 'Close', 'Low', 'High', 'Volume']]
    y_high = company_df['Next_High']
    y_low = company_df['Next_Low']

    # Fit autoregressive model for high price
    model_high = AutoReg(y_high, lags=1).fit()

    # Fit autoregressive model for low price
    model_low = AutoReg(y_low, lags=1).fit()

    # Predict high and low prices for the next day
    predicted_high = model_high.predict(start=len(company_df), end=len(company_df))
    predicted_low = model_low.predict(start=len(company_df), end=len(company_df))

    return predicted_high.values[0], predicted_low.values[0]

