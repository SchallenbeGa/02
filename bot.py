import websocket, json, config, aiofiles,pandas as pd,asyncio
from binance.client import Client
from binance.enums import *
from datetime import datetime
from dateutil import tz

#https://developer.twitter.com/
#https://developer.twitter.com/en/apps
#click on app and write "auth-settings" in url,
#https://developer.twitter.com/en/portal/projects/xxxx/apps/xxxx/ <- !auth-settings
#oauth 1.0a put on
#Callback URI / Redirect URL -> http://twitter.com
#Website URL -> http://twitter.com
#save
import tweepy

consumer_key = 'nGZ2GOUnmJhsecretagsdHDKG'
consumer_secret = 'Yc7iFcuDFlNxQsecretdOGjFjgy'
access_token = '126528594162481152secretcjINAvSFWmHLCFcqHfHSQPKplJZ'
access_token_secret = 'NkvqRUgBuhX9xSAjCDWsecret2EHO3S640KOIxDgCaVuGC'

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)


SOCKET = "wss://stream.binance.com:9443/ws/"+config.PAIR+"@kline_1m"

TRADE_SYMBOL = config.PAIR_M
TRADE_QUANTITY = config.QUANTITY
TEST = config.DEBUG

order_id = 0
in_position = False
sell_price = 0

with open("tst.csv", "r") as f:
    data = f.readlines()

with open("tst.csv", "w") as f:
    for line in data :
        if line.strip("\n") == "Date,Open,High,Low,Close,Volume" : 
            f.write(line)


with open("trade.csv", "w") as f: 
    f.write("Date,Type,Price,Quantity\n")

with open("order.csv", "w") as f:
    f.write("Date,Type,Price,Quantity\n")

#save trade form the bot in trade.csv
async def save_trade(b_s,price):
    async with aiofiles.open('trade.csv', mode='r') as f:
        contents = await f.read()
        now = datetime.now()
        current_time = now.strftime("%Y-%m-%d %H:%M:%S")
        contents = contents+str(str(current_time)+","+str(b_s)+","+str(price)+","+str(TRADE_QUANTITY)+"\n")
    async with aiofiles.open('trade.csv', mode='w') as f:
        await f.write(contents)

#save sell order form the bot in order.csv
async def save_order(price):
    async with aiofiles.open('order.csv', mode='w') as f:
        now = datetime.now()
        current_time = now.strftime("%Y-%m-%d %H:%M:%S")
        print("here")
        await f.write("Date,Price,Quantity"+"\n"+str(str(current_time)+","+str(price)+","+str(TRADE_QUANTITY)))
        
async def save_data():
    klines = client_data.get_historical_klines(config.PAIR_M, Client.KLINE_INTERVAL_1MINUTE, "1 hour ago UTC")
    async with aiofiles.open('tst.csv', mode='w') as f:
        await f.write("Date,Open,High,Low,Close,Volume")
        for line in klines:
            await f.write(f'\n{datetime.fromtimestamp(line[0]/1000)}, {line[1]}, {line[2]}, {line[3]}, {line[4]},{line[5]}')

async def save_close(tim,data):
    async with aiofiles.open('tst.csv', mode='r') as f:
        contents = await f.read()
        now = datetime.now()
        current_time = now.strftime("%Y-%m-%d %H:%M:%S")
        contents = contents+"\n"+str(current_time)+","+str(data['o'])+","+str(data['h'])+","+str(data['l'])+","+str(data['c'])+","+str(data['v'])
    async with aiofiles.open('tst.csv', mode='w') as f:
        await f.write(contents)

def order(limit,side, quantity, symbol,order_type=ORDER_TYPE_MARKET):
    global order_id
    try:
        if limit > 0:
            print("test")
            order = client.create_order(symbol=symbol,side=side,type=ORDER_TYPE_LIMIT,quantity=TRADE_QUANTITY,price=limit,timeInForce=TIME_IN_FORCE_GTC)
        else:
            order = client.create_order(symbol=symbol,side=side,type=order_type, quantity=quantity)
        print("sending order")
        print(order)
        order_id = order['orderId']
    except Exception as e:
        print("an exception occured - {}".format(e))
        return False

    return True
    
client = Client(config.API_KEY, config.API_SECRET, tld='com')
client_data = Client(config.API_KEY, config.API_SECRET, tld='com')
asyncio.run(save_data())
if TEST :
    client.API_URL = 'https://testnet.binance.vision/api'#test

def on_open(ws):
    print('opened connection')

def on_close(ws):
    print('closed connection')

def on_message(ws, message):
    global in_position,order_id,sell_price,api

    json_message = json.loads(message)  
    candle = json_message['k']
    is_candle_closed = candle['x']

    asyncio.run(save_data())

    #asyncio.run(save_close(json_message['E'],candle))
    data = pd.read_csv('tst.csv').set_index('Date')
    data.index = pd.to_datetime(data.index)

    sma = data['Close'][-8:].mean()
    close = float(candle['c'])

    if (is_candle_closed):
        if in_position:
            print("okay")
            tweet = "buy at : "+str(sell_price-0.002)+"\nlast price : "+str(data['Close'][-1])+"\nactual profit : "+str(data['Close'][1]-(sell_price-0.002))
            api.update_status(tweet)

    print("current price :",close)
    print("cross price   :",sma)

    if in_position:
        sorder = client.get_order(symbol=TRADE_SYMBOL,orderId=order_id)
        if TEST:
            print("Ready")
            print(type(sorder['price']))
            print(type(close))
            if sell_price<=close:
                tweet = "sell at: "+close
                api.update_status(tweet)
                print("selll")
                print("cross price :",sma)
                print(sorder['price'])
                asyncio.run(save_trade("sell",sorder['price']))
                print('\a')
                print('\a')
                in_position = False
                with open("order.csv", "w") as f:
                    f.write("Date,Type,Price,Quantity\n")
        else: 
            if sorder['status'] == 'FILLED':
                print("cross price :",sma)
                print(sorder['price'])
                asyncio.run(save_trade("sell",sorder['price']))
                print('\a')
                print('\a')
                in_position = False
            else:  
                print("waiting for sell : ",sorder)
 
    if (close < sma):# if last price < last 10 trade's price avg = buy
        if in_position == False:
            order_succeeded = order(0,SIDE_BUY, TRADE_QUANTITY, TRADE_SYMBOL)
            if order_succeeded:
                in_position = True
                print("here")
                tweet = "buy at: "+str(close)
                api.update_status(tweet)
                asyncio.run(save_trade("buy",close))
                print("hoo")
                print('\a')
                sell_price = close+0.002
                order_sell = order(close+0.002,SIDE_SELL, TRADE_QUANTITY, TRADE_SYMBOL) # sell at : buy price + 0.0005%
                if order_sell:
                    print("here")
                    asyncio.run(save_order(close+0.002))
                    print("success sell limit")
                else:
                    print("fail sell limit")
            else:
                print("fail buy")
    
ws = websocket.WebSocketApp(SOCKET, on_open=on_open, on_close=on_close, on_message=on_message)
ws.run_forever()
