from flask import Flask, request, jsonify, session
from flask_cors import CORS
import pandas as pd
from urllib.parse import quote_plus
from pymongo import MongoClient
import urllib
from Yahoo_finance_script import get_stock_info, predict_next_day_prices, EDA_analysis
from News_data_vader_sentiments import get_news_sentiment
global symbol
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_PASSWORD = os.getenv("MongoPassword")

app = Flask(__name__)

app.secret_key = os.urandom(24)

CORS(app, resources={r"/*": {"origins": "*"}})

# Define the MongoDB connection string
conn_string = "mongodb+srv://wetrade:" + urllib.parse.quote(MONGO_PASSWORD) + \
              "@cluster0.soxdr7e.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Connect to MongoDB using pymongo
client = MongoClient(conn_string)

# Specify the database name
db = client['weTrade']

# Specify the collection name


def predict_stocks(symbol):
    symbol_data = get_stock_info(symbol)
    df_info, stock_price_data = symbol_data
    stock_json = stock_price_data.to_dict(orient='records')
    collection = db['Stock_data']
    # collection.insert_many(stock_json)
    stock_price_data = stock_price_data.drop(columns=['Dividends', 'Stock Splits'])
    predicted_high, predicted_low = predict_next_day_prices(stock_price_data)
    print(predicted_high, predicted_low)




    return predicted_high, predicted_low, stock_price_data


def delete_data(db,collection_name):

        db.drop_collection(collection_name)
        print(f" documents deleted from {collection_name}.")


# User registration endpoint
@app.route('/register', methods=['POST'])
def register():
    collection = db['users']
    try:
        # Ensure the request has JSON data
        if request.is_json:
            # Extract user data from the JSON request
            user_data = request.json
            print("user data:", user_data)

            phone_number = user_data['phone_number']
            name = user_data['name']
            dob = user_data['dob']
            city = user_data['city']
            trading_exp = user_data['trading_exp']
            collection.insert_one({
                'name': name,
                'phone_number': phone_number,
                'dob': dob,
                'city': city,
                'trading_exp': trading_exp
            })

            # Your code to process user data and save it to MongoDB goes here
            # Return a JSON response indicating successful registration
            return jsonify({'message': 'User registered successfully', 'data': user_data})
        else:
            # If the request does not have JSON data, return an error response
            return jsonify({'error': 'Request must contain JSON data'}), 415
    except Exception as e:
        # If an error occurs during processing, return an error response
        return jsonify({'error': str(e)}), 500
    

# User patch endpoint to update user data
@app.route('/update', methods=['PATCH'])
def update_user():
    collection = db['users']
    try:
        # Ensure the request has JSON data
        if request.is_json:
            # Extract user data from the JSON request
            user_data = request.json
            phone_number = user_data['phone_number']
            api_key = user_data['API_KEY']
            api_secret = user_data['API_SECRET']
            # Update the user data in MongoDB
            collection.update_one({'phone_number': phone_number}, {'$set': {'api_key': api_key, 'api_secret': api_secret}})
            # Return a JSON response indicating successful update
            return jsonify({'message': 'User data updated successfully', 'data':user_data})
        else:
            # If the request does not have JSON data, return an error response
            return jsonify({'error': 'Request must contain JSON data'}), 415
    except Exception as e:
        # If an error occurs during processing, return an error response
        return jsonify({'error': str(e)}), 500


# User login endpoint
@app.route('/login', methods=['GET'])
def get_data():
    collection = db['users']
    parameter_value = request.args.get('phone_number')
    print("param", parameter_value)

    if parameter_value:
        # Find a single document in the collection where phone_number matches the parameter
        data = collection.find_one({"phone_number": parameter_value}, {'_id': 0})
    else:
        # If phone_number parameter is not provided, set data to None
        data = None

    if data:
        print(data)
        return jsonify({'data': data, 'message': True}), 200
    else:
        return jsonify({'message': False}), 200



@app.route('/process_data', methods=['GET'])
def process_data():
    # symbol = request.json  # Assuming JSON data is sent from the frontend for now(discuss with gaurav)
    # symbol = symbol['symbol']
    symbol = request.args.get('symId')
    session['symbol'] = symbol
    today_date = datetime.today().date()
    today_date = str(today_date)
    collection = db['Output']
    document = collection.find_one({'symbol': symbol, 'date':today_date})

    if document:
        predict_high = document.get('high')
        predict_low = document.get('low')
        sentiment = document.get('average_sentiment')
        analysis = document.get('analysis')

        return jsonify({'exists': True, 'sentiment': sentiment, 'predicted_low': predict_low, 'predicted_high': predict_high, 'analysis':analysis})

    else:
        #for sentiemnts file:
        # if():
        # deleting data from news collection if anything older than today's date in the data
        # delete_data(db,'News_data')
        # deleting data from stocks collection if anything older than today's date in the data
        # delete_data(db,'Stock_data')

        news_symbol = get_news_sentiment(symbol)
        print(news_symbol)
        if news_symbol.empty:
            overall_sentiment = 'neutral'
        else:
            
            overall_sentiment = (news_symbol.Description_sentiment.value_counts()).index[0]
            news_json = news_symbol.to_dict(orient='records')
            collection = db['News_data']

        
        # Insert data into MongoDB collection
        # collection.insert_many(news_json)

        predicted_high, predicted_low, stock_price_data = predict_stocks(symbol)
        analysis_url_dict = EDA_analysis(stock_price_data)
        analysis = [analysis_url_dict]

        final_df = {
            'symbol': [symbol],
            'date': [today_date],
            'high': [predicted_high],
            'low': [predicted_low],
            'average_sentiment': [overall_sentiment],
            'analysis': [analysis]
        }
        df = pd.DataFrame(final_df)

        # Convert DataFrame to JSON format
        output_json = df.to_dict(orient='records')



        # output_json = {'Symbol':symbol,'Date':today_date,'high':predicted_high,'low':predicted_low, 'average_sentiment': overall_sentiment}
        collection = db['Output']
        collection.insert_many(output_json)
        # output_df = pd.DataFrame(symbol, today_date, predicted_high, predicted_low, columns=['symbol', 'today_date', 'predicted_high', 'predicted_low'])
        print("**********", overall_sentiment,predicted_high, predicted_low, "*********")

        return jsonify({'exists': False, 'sentiment': overall_sentiment, 'predicted_low': predicted_low, 'predicted_high': predicted_high, 'analysis': analysis})



if __name__ == '__main__':
    app.run(debug=True)