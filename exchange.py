import requests as req
import json
import re
import datetime
from collections import OrderedDict
import asyncio
import util
from data import BTCLast, USDTLast, KRWLast, BNBLast, ETHLast, PercentChanges
from network import JsonLoaderAsync, JsonLoaderRQ

class Exchange:
    name = ""
    msg = ""
    symbol = ""
    version = ""
    rst = False
    json_time = datetime.datetime.now()
    last_time = datetime.datetime.now()
    def get_json(self, currency_list): # 거래소 별 json 다운로드 로직
        pass
    def get_last(self, currency_list): # 거래소 별 last price parsing 로직
        pass
    def debug(self, error_msg):
        print(error_msg)
    def _run(self, currency_list):
        try:
            self.get_json(currency_list)
            self.json_time = datetime.datetime.now()
        except:
            self.debug("ERROR : %s get_json : %s" % (self.name, self.msg))
            return False
        try:
            self.get_last(currency_list)
            self.last_time = datetime.datetime.now()
            return True
        except Exception as e:
            self.debug("ERROR : %s get_last : %s" % (self.name, self.msg))
            return False
    def run(self, currency_list):
        self._run(currency_list)
    async def async_run(self, currency_list):
        self._run(currency_list)

class Poloniex(Exchange, JsonLoaderRQ, BTCLast, USDTLast, PercentChanges):
    name = "Poloniex"
    symbol = "polo"
    version = "Poloniex 1.0 JsonLoaderRQ"
    def get_json(self, currency_list):
        self.json = self.load_single_json("https://poloniex.com/public?command=returnTicker")
    def get_last(self, currency_list):
        self.msg = "usdt_last btc"
        self.USDT_last['BTC'] = float(self.json["USDT_BTC"]['last'])
        for currency in currency_list:
            if "BTC_"+currency in self.json:
                self.msg = "percent_changes %s" % currency
                self.percent_changes[currency] = float(self.json["BTC_"+currency]['percentChange'])
                self.msg = "btc_last %s" % currency
                self.BTC_last[currency] = float(self.json["BTC_"+currency]['last'])
            if "USDT_"+currency in self.json:
                self.msg = "usdt_last %s" % currency
                self.USDT_last[currency] = float(self.json["USDT_"+currency]['last'])

class Binance(Exchange, JsonLoaderRQ, BTCLast, USDTLast, ETHLast, BNBLast):
    name = "Binance"
    symbol = "bin"
    version = "Binance 1.0 JsonLoaderRQ"
    def get_json(self, currency_list):
        self.json = {}
        self.rawJson = self.load_single_json("https://api.binance.com/api/v1/ticker/allPrices")
        self.json = dict(map(lambda dict:(dict['symbol'], dict['price']), self.rawJson))
    def get_last(self, currency_list):
        self.msg = "get_last"
        patch = {"BCH":"BCC"}
        for currency in currency_list:
            currency_str = currency
            if currency in patch:
                currency_str = patch[currency]
            self.msg = "get_last : %s" % currency_str
            for kv in {"BTC":self.BTC_last, "USDT":self.USDT_last, "ETH":self.ETH_last, "BNB":self.BNB_last}.items():
                self.msg = "get_last : %s %s " % (currency, kv[0])
                if "%s%s" % (currency_str, kv[0]) in self.json:
                    self.msg = "get_last parse : %s%s" % (currency, kv[0])
                    kv[1][currency] = float(self.json['%s%s' % (currency_str, kv[0])])

class Gopax(Exchange, JsonLoaderAsync, KRWLast):
    name = "Gopax"
    symbol = "go"
    version = "Gopax 1.0 JsonLoaderAsync"
    supported_currencies = []
    #def __init__(self):
        #https://api.gopax.co.kr/trading-pairs
        #loop = asyncio.get_event_loop()
        #task = asyncio.ensure_future(self.load_single_json(url = "https://api.gopax.co.kr/trading-pairs"))
        #loop.run_until_complete(task)
        #loop.close()
        #for record in task.result():
        #   self.supported_currencies.append(record["baseAsset"])
    def get_json(self, currency_list):
        #https://api.gopax.co.kr/trading-pairs/BTC-KRW/ticker
        #C = set(self.supported_currencies).intersection(set(currency_list))
        C = ['BTC'] + currency_list
        self.krw_urls = dict(map(lambda currency:(currency, "https://api.gopax.co.kr/trading-pairs/%s-KRW/ticker" % currency), C))
        temp_jsons = self.load_multiple_json(self.krw_urls)
        self.json = dict(map(lambda json:(json['currency'], json), temp_jsons))
    def get_last(self, currency_list):
        C = ['BTC'] + currency_list
        for currency in C:
           self.msg = "get_last : %s" % currency
           #print(self.json)
           if currency in self.json:
               if 'price' in self.json[currency]:
                   self.KRW_last[currency] = self.json[currency]['price']

class Coinone(Exchange, JsonLoaderRQ, KRWLast):
    name = "Coinone"
    symbol = "co"
    version = "Coinone 1.0 JsonLoaderRQ"
    def get_json(self, currency_list):
        self.json = self.load_single_json("https://api.coinone.co.kr/ticker/?format=json&currency=btn")
    def get_last(self, currency_list):
        for currency in currency_list:
            self.msg = "krw_last %s" % currency
            if currency.lower() in self.json:
                if 'last' in self.json[currency.lower()]:
                    self.KRW_last[currency] = float(self.json[currency.lower()]['last'])
            
class Upbit(Exchange, JsonLoaderAsync, KRWLast, BTCLast, USDTLast):
    name = "Upbit"
    symbol = "up"
    version = "Upbit 1.1 JsonLoaderAsync"
    history = ["1.1 / 20180104 / fix BCH(BCC)"]
    patch = {"BCH":"BCC"}
    def get_json(self, currency_list):
        # https://crix-api-endpoint.upbit.com/v1/crix/trades/ticks?code=CRIX.UPBIT.KRW-BTC&count=1
        # https://crix-api-endpoint.upbit.com/v1/crix/candles/minutes/1?code=CRIX.UPBIT.KRW-BTC&count=1
        currency_list = list(map(lambda c:self.patch[c] if c in self.patch else c,currency_list))
        self.krw_urls = dict(map(lambda currency:(currency, "https://crix-api-endpoint.upbit.com/v1/crix/candles/minutes/60?code=CRIX.UPBIT.KRW-%s&count=1" % currency), currency_list))
        self.usdt_urls = dict(map(lambda currency:(currency, "https://crix-api-endpoint.upbit.com/v1/crix/candles/minutes/60?code=CRIX.UPBIT.USDT-%s&count=1" % currency), currency_list))
        self.btc_urls = dict(map(lambda currency:(currency, "https://crix-api-endpoint.upbit.com/v1/crix/candles/minutes/60?code=CRIX.UPBIT.BTC-%s&count=1" % currency), currency_list))
        self.krw_jsons = self.load_multiple_json(self.krw_urls, option='CRIX')
        self.usdt_jsons = self.load_multiple_json(self.usdt_urls, option='CRIX')
        self.btc_jsons = self.load_multiple_json(self.btc_urls, option='CRIX')
    def get_last(self, currency_list):
        extype_dict = {'usdt_last' : (self.usdt_jsons, self.USDT_last), 'krw_last' : (self.krw_jsons, self.KRW_last), 'btc_last' : (self.btc_jsons, self.BTC_last)}
        for currency in currency_list:
            for extype in list(extype_dict.items()):
                currency_str = currency
                if currency in self.patch:
                    currency_str = self.patch[currency]
                #print(extype)
                for json in filter(lambda json:len(json) > 0 and json['currency'] == currency_str, extype[1][0]):
                    self.msg = "%s %s" % (extype[0], currency)
                    extype[1][1][currency] = json['tradePrice']

class GateIO(Exchange, JsonLoaderRQ, BTCLast, USDTLast, ETHLast):
    name = "Gate.IO"
    symbol = "gate"
    version = "Gate.IO 1.0 JsonLoaderRQ"
    def get_json(self, currency_list):
        self.rawJson = self.load_single_json("http://data.gate.io/api2/1/tickers")
        self.json = dict(map(lambda dict:(dict[0], dict[1]['last']), self.rawJson.items()))
    def get_last(self, currency_list):
        self.msg = "get_last"
        for currency in currency_list:
            self.msg = "get_last : %s" % currency
            for kv in {"btc":self.BTC_last, "usdt":self.USDT_last, "ETH":self.ETH_last}.items():
                self.msg = "get_last : %s %s " % (currency, kv[0])
                if "%s_%s" % (currency.lower(), kv[0]) in self.json:
                    self.msg = "get_last parse : %s %s" % (currency, kv[0])
                    kv[1][currency] = float(self.json['%s_%s' % (currency.lower(), kv[0])])

class Cpdax(Exchange, JsonLoaderRQ, KRWLast):
    name = "CPDAX"
    symbol = "cpdax"
    version = "CPDAX 1.0 JsonLoaderRQ"
    def get_json(self, currency_list):
        self.rawJson = self.load_single_json("https://api.cpdax.com/v1/tickers")
        self.json = dict(map(lambda dict:(dict['currency_pair'], dict['last']), self.rawJson))
    def get_last(self, currency_list):
        self.msg = "get_last"
        for currency in currency_list:
            currency_str = "%s-KRW" % currency
            self.msg = "get_last : %s" % currency
            if currency_str in self.json:
                self.KRW_last[currency] = float(self.json[currency_str])

class Kucoin(Exchange, JsonLoaderRQ, BTCLast, USDTLast, ETHLast):
    name = "Kucoin"
    symbol = "KCS"
    version = "Kucoin 1.0 JsonLoaderRQ"
    def get_json(self, currency_list):
        self.json = {}
        self.rawJson = self.load_single_json("https://api.kucoin.com/v1/open/tick")
        dp = filter(lambda dict:'lastDealPrice' in dict, self.rawJson['data'])
        self.json = dict(map(lambda dict:(dict['symbol'], dict['lastDealPrice']), dp))
    def get_last(self, currency_list):
        self.msg = "get_last"
        patch = {}
        for currency in currency_list:
            currency_str = currency
            if currency in patch:
                currency_str = patch[currency]
            self.msg = "get_last : %s" % currency_str
            for kv in {"BTC":self.BTC_last, "USDT":self.USDT_last, "ETH":self.ETH_last}.items():
                self.msg = "get_last : %s %s " % (currency, kv[0])
                if "%s-%s" % (currency_str, kv[0]) in self.json:
                    self.msg = "get_last parse : %s-%s" % (currency, kv[0])
                    kv[1][currency] = float(self.json['%s-%s' % (currency_str, kv[0])])

class Coinrail(Exchange, JsonLoaderAsync, BTCLast, KRWLast):
    name = "Coinrail"
    symbol = "CR"
    version = "Coinrail 1.0 JsonLoaderAsync"
    def get_json(self, currency_list):
        C = currency_list
        self.krw_urls = dict(map(lambda currency:("%s-krw" % currency.lower(), "https://api.coinrail.co.kr/public/last/order?currency=%s-krw" % currency.lower()), C))
        self.btc_urls = dict(map(lambda currency:("%s-btc" % currency.lower(), "https://api.coinrail.co.kr/public/last/order?currency=%s-btc" % currency.lower()), C))
        self.urls = {}
        self.urls.update(self.krw_urls)
        self.urls.update(self.btc_urls)
        temp_jsons = self.load_multiple_json(self.urls)
        self.json = dict(map(lambda json:(json['currency'], json), temp_jsons))
    def get_last(self, currency_list):
        C = currency_list
        for kv in {'krw':self.KRW_last, 'btc':self.BTC_last}.items():
            for currency in C:
                self.msg = "get_last : %s-%s" % (currency, kv[0])
                if "%s-%s"%(currency.lower(), kv[0]) in self.json:
                    if 'last_price' in self.json["%s-%s"%(currency.lower(), kv[0])]:
                        kv[1][currency] = float(self.json["%s-%s"%(currency.lower(), kv[0])]['last_price'])

class Bittrex(Exchange, JsonLoaderRQ, BTCLast, ETHLast, USDTLast):
    name = "Bittrex"
    symbol = "BTX"
    versin = "Bittrex 1.0 JsonLoaderRQ"
    def get_json(self, currency_list):
        self.rawJson = self.load_single_json("https://bittrex.com/api/v1.1/public/getmarketsummaries")
        self.json = dict(map(lambda x:(x['MarketName'], x), self.rawJson['result']))

class Coinnest(Exchange, JsonLoaderAsync, KRWLast):
    name = "Coinnest"
    symbol = "CN"
    version = "Coinnest 1.0 JsonLoaderAsync"
    def get_json(self, currency_list):
        self.krw_urls = dict(map(lambda currency:("%s" % currency.lower(), "https://api.coinnest.co.kr/api/pub/ticker?coin=%s" % currency.lower()), currency_list))
        temp_jsons = self.load_multiple_json(self.krw_urls)
        self.json = dict(map(lambda json:(json['currency'], json), temp_jsons))
    def get_last(self, currency_list):
        for currency in currency_list:
            self.msg = "get_last : %s" % (currency)
            if "%s"%(currency.lower()) in self.json:
                if 'last' in self.json["%s"%(currency.lower())]:
                    self.KRW_last[currency] = float(self.json["%s"%(currency.lower())]['last'])

def get_bittrex_currency(currency, json):
    x = list(filter(lambda x: x['MarketName'] == currency, json['result']))
    if len(x) == 0:
        return None
    return x[0]

def get_bittrex_last(currency_list):
    #https://bittrex.com/api/v1.1/public/getmarketsummaries   
    BTC_last = OrderedDict()
    USDT_last = OrderedDict()
    res = req.get("https://bittrex.com/api/v1.1/public/getmarketsummaries")
    if res.ok != True :
        return BTC_last, USDT_last
    bittrex = json.loads(res.text)
    if bittrex['success'] != True:
        return BTC_last, USDT_last
    USDT_last['BTC'] = float(get_bittrex_currency('USDT-BTC', bittrex)['Last'])
    for currency in currency_list:
        if currency == 'BCH':
            x = get_bittrex_currency("BTC-BCC", bittrex)
        else:
            x = get_bittrex_currency("BTC-"+currency, bittrex)
        if x != None:
            BTC_last[currency] = float(x['Last'])
    return BTC_last, USDT_last

def Bithumb(Exchange, JsonLoaderAsync, KRWLast):
    name = "Bithumb"
    symbol = "bt"
    version = "Bithumb 1.0 JsonLoaderAsync"
    def get_json(self, currency_list):
        self.krw_urls = dict(map(lambda currency:(currency, self.get_bithumb_url(currency), currency_list)))
        temp_jsons = self.load_multiple_json(self.krw_urls)
        self.json = dict(map(lambda json:(json['currency'], json), temp_jsons))
    def get_bithumb_url(self, currency):
        if(currency == "BTC"):
            return "https://api.bithumb.com/public/ticker"
        else:
            return "https://api.bithumb.com/public/ticker/"+currency
    def get_last(self, currency_list):
        for currency in currency_list:
            if "data" in json[currency] and "closing_price" in json[currency]['data']:
                self.KRW_last[currency] = float(self.json[currency]['data']['closing_price'])

def Coinis(Exchange, JsonLoaderAsync, KRWLast):
    name = "Coinis"
    symbol = "CI"
    version = "Coinis 1.0 JsonLoaderAsync"
    def get_json(self, currency_list):
        patch = {'BCH':'BCC'}
        ignore = ['ETH','ETC']
        C = filter(lambda currency:currency not in ignore,currency_list)
        krw_urls = {}
        for currency in C:
            if(currency in patch):
                krw_urls[currency] = "http://coinis.co.kr/api/sise/ticker?itemcode=%sKRW" % patch[currency]
            else:
                krw_urls[currency] = "http://coinis.co.kr/api/sise/ticker?itemcode=%sKRW" % currency
        temp_jsons = self.load_multiple_json(self.krw_urls)
        self.json = dict(map(lambda json:(json['currency'], json), temp_jsons))
    def get_last(self, currency_list):
        for currency in currency_list:
            if 'data' in json[currency] and 'ClosePrice' in json[currency]['data']:
                self.KRW_last[currency] = float(self.json[currency]['data']['ClosePrice'])

def get_coinis_last(currency_list):
    BTC_last = OrderedDict()
    KRW_last = OrderedDict()
    res = req.get("http://coinis.co.kr/api/sise/ticker?itemcode=BTCKRW")
    ticker = json.loads(res.text)
    if ticker['result'] == -1 :
        return BTC_last, KRW_last
    btc_krw = ticker["data"]['ClosePrice']
    KRW_last["BTC"] = float(btc_krw)
    for currency in currency_list:
        if currency == "ETH" or currency == "ETC":
            continue
        if currency == "BCH":
            res = req.get("http://coinis.co.kr/api/sise/ticker?itemcode=BCCKRW")
        else:
            res = req.get("http://coinis.co.kr/api/sise/ticker?itemcode="+currency+"KRW")
        if(res.ok):
            ticker = json.loads(res.text)
            if(len(ticker['data']) > 0):
                BTC_last[currency] = float(ticker['data']['ClosePrice']) / float(btc_krw)
                KRW_last[currency] = float(ticker['data']['ClosePrice'])
    return BTC_last, KRW_last

#class Bittrex(Exchange, JsonLoaderRQ, )

def get_bithumb_json(str):
    m = re.search('{.*}', str)
    return m.group(0)

def get_bithumb_last(currency_list):
    BTC_last = OrderedDict()
    KRW_last = OrderedDict()
    btc_res = req.get("https://api.bithumb.com/public/ticker")
    btc_ticker = json.loads(get_bithumb_json(btc_res.text))
    if btc_ticker['status'] == 5600:
        return BTC_last, KRW_last;
    btc_krw = btc_ticker['data']['closing_price']
    KRW_last["BTC"] = float(btc_krw)
    for currency in currency_list:
        res = req.get("https://api.bithumb.com/public/ticker/"+currency)
        if(res.ok):
            ticker = json.loads(get_bithumb_json(res.text))
            BTC_last[currency] = float(ticker['data']['closing_price']) / float(btc_krw)
            KRW_last[currency] = float(ticker['data']['closing_price'])
    return BTC_last, KRW_last

def get_bitfinex_last(currency_list):
    BTC_last = OrderedDict()
    USDT_last = OrderedDict()
    btc_res = req.get("https://api.bitfinex.com/v1/pubticker/BTCUSD")
    btc_ticker = json.loads(btc_res.text)
    btc_USDT = float(btc_ticker['last_price'])
    for currency in currency_list:
        if currency == "DASH":
            res = req.get("https://api.bitfinex.com/v1/pubticker/DSHBTC")
        else:
            res = req.get("https://api.bitfinex.com/v1/pubticker/"+currency+"BTC")
        if res.ok:
            ticker = json.loads(res.text)
            if 'last_price' in ticker:
                BTC_last[currency] = float(ticker['last_price'])
                USDT_last[currency] = float(ticker['last_price']) * btc_USDT
    return BTC_last, USDT_last

def get_liqui_last(currency_list):
    BTC_last = OrderedDict()
    for currency in currency_list:
        if currency == "STEEM" or currency == "SBD":
            continue
        if currency == "BCH":
            res = req.get("https://api.liqui.io/api/3/ticker/bcc_btc")
        else:
            res = req.get("https://api.liqui.io/api/3/ticker/"+currency.lower()+"_btc")
        if res.ok:
            ticker = json.loads(res.text)
            if currency == "BCH":
                BTC_last[currency] = float(ticker['bcc_btc']['last'])
            if currency.lower()+'_btc' in ticker:
                BTC_last[currency] = float(ticker[currency.lower()+'_btc']['last'])
    return BTC_last

def get_hitbtc_last(currency_list):
    BTC_last = OrderedDict()
    res = req.get("https://api.hitbtc.com/api/1/public/ticker")
    hitbtc = json.loads(res.text)
    for currency in currency_list:
        if currency+"BTC" in hitbtc:
            BTC_last[currency] = float(hitbtc[currency+"BTC"]['last'])
    return BTC_last

def get_cex_io_last():
    USDT_last = OrderedDict()
    btc_res = req.get("https://cex.io/api/last_price/BTC/USD")
    if btc_res.ok:
        btc_ticker = json.loads(btc_res.text)
        USDT_last["BTC"] = float(btc_ticker["lprice"])
        USDT_last["buy"] = USDT_last["BTC"] * 1.07
        USDT_last["visa"] = USDT_last["buy"] * 1.035
        USDT_last["fee"] = USDT_last["visa"] * 1.02
    return USDT_last