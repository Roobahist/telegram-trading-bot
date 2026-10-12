import base64
import copy
import hashlib
import hmac
import logging
import time
import traceback
import urllib.request
from hashlib import sha256

import requests
from pybit.unified_trading import HTTP

import config
from database import databaseHandler


# generate apikey and secret with more permissions and test, switch margin mode, leverage size and placing orders.
class BingXClient(object):

	def __init__(self,
	             api_key=config.BINGX_APIKEY,
	             api_secret=config.BINGX_APISECRET,
	             dbh: databaseHandler = None,
	             http_client=None,
	             request_timeout=10.0) -> None:
		self.http_client = http_client or requests
		self.request_timeout = request_timeout
		self.api_key = api_key
		self.api_secret = api_secret
		self.API_URL = "https://open-api.bingx.com"
		self.headers = {
		    "X-BX-APIKEY": self.api_key
		}
		self.dbh = dbh

	def get_sign(self, api_secret, payload):
		signature = hmac.new(api_secret.encode("utf-8"), payload.encode("utf-8"), digestmod=sha256).hexdigest()
		return signature

	def parseParam(self, paramsMap):
		paramsMap["timestamp"] = int(time.time() * 1000)
		sortedKeys = sorted(paramsMap)
		paramsStr = "&".join(["%s=%s" % (x, paramsMap[x]) for x in sortedKeys])
		return paramsStr

	def send_request(self, methed, path, urlpa=None, payload=None):
		paramsStr = self.parseParam(dict(urlpa or {}))
		url = "%s%s?%s&signature=%s" % (
		    self.API_URL,
		    path,
		    paramsStr,
		    self.get_sign(self.api_secret, paramsStr),
		)

		headers = {
		    "X-BX-APIKEY": self.api_key,
		}

		response = self.http_client.request(methed, url, headers=headers, data=payload, timeout=self.request_timeout)
		response.raise_for_status()
		return response.json()

	def resolve_side(self, side, reverse=False):
		if not reverse:
			return "BUY" if side == "buy" else "SELL"
		return "SELL" if side == "buy" else "BUY"

	def resolve_symbol(self, symbol, forward=True):
		if forward:
			return symbol.replace("/", "-")
		return self.dbh.get("pair", {
		    "exchange": config.BINGX,
		    "symbolUnstructured": symbol,
		    "perp": True
		}, "symbol")

	def getPositions(self, symbol):
		paramsMap = {
		    "symbol": self.resolve_symbol(symbol),
		}
		path = "/openApi/swap/v2/user/positions"
		return self.send_request("GET", path, paramsMap)

	def placeOrder(self, symbol, side, price, volume, tradeType, tp=None, sl=None):
		path = "/openApi/swap/v2/trade/order"

		paramsMap = {
		    "symbol": self.resolve_symbol(symbol),
		    "side": self.resolve_side(side),
		    "price": price,
		    "quantity": volume,
		    "type": tradeType,  # LIMIT, MARKET, STOP_MARKET, TAKE_PROFIT_MARKET, TRIGGER_LIMIT, TRIGGER_MARKET
		}
		self.send_request("POST", path, paramsMap)

		if tp != None:
			paramsMap = {
			    "symbol": self.resolve_symbol(symbol),
			    "side": self.resolve_side(side, reverse=True),
			    "stopPrice": tp,
			    "quantity": volume,
			    "type": "TAKE_PROFIT_MARKET",
			}
			self.send_request("POST", path, paramsMap)

		if sl != None:
			paramsMap = {
			    "symbol": self.resolve_symbol(symbol),
			    "side": self.resolve_side(side, reverse=True),
			    "stopPrice": sl,
			    "quantity": volume,
			    "type": "STOP_MARKET",
			}
			self.send_request("POST", path, paramsMap)

	def switch_leverage(self, symbol, side, leverage):
		paramsMap = {
		    "symbol": self.resolve_symbol(symbol),
		    "side": self.resolve_side(side),
		    "leverage": leverage,
		}

		path = "/openApi/swap/v2/trade/leverage"

		return self.send_request("POST", path, paramsMap)

	def swith_margin_mode(self, symbol, margin_mode):
		paramsMap = {
		    "symbol": self.resolve_symbol(symbol),
		    "marginType": margin_mode,  # ISOLATED, CROSSED
		}

		path = "/openApi/swap/v2/trade/marginType"

		return self.send_request("POST", path, paramsMap)

	def get_price(self, symbol, perp=True):
		if perp:
			paramsMap = {
			    "symbol": self.resolve_symbol(symbol)
			}
			path = "/openApi/swap/v2/quote/price"
			# return self.send_request("GET", path, paramsMap)
			return float(self.send_request("GET", path, paramsMap)["data"]["price"])
		else:
			paramsMap = {
			    "symbol": self.resolve_symbol(symbol),
			    "limit": 1
			}
			path = "/openApi/spot/v1/market/trades"
			# return self.send_request("GET", path, paramsMap)
			return float(self.send_request("GET", path, paramsMap)["data"][0]["price"])

	def get_order_history(self, symbol):
		result = []

		try:
			paramsMap = {
			    "symbol": self.resolve_symbol(symbol),
			    "orderId": 0,
			    "limit": 1000,
			}

			path = "/openApi/swap/v2/trade/allOrders"
			result = self.send_request("POST", path, paramsMap)["data"]["orders"]

			if len(result) == 1000:
				ended = False
				while not ended:
					paramsMap["orderId"] = result[-1]["orderId"]

					extra_results = self.send_request("POST", path, paramsMap)["data"]["orders"]
					if extra_results == []:
						ended = True
						continue

					result.extend(extra_results)

			result = [i for i in result if i["action"] == "Close"]

		except:
			pass

		finally:
			return result

	def get_pairs_info(self):
		f = self.send_request("GET", "/openApi/swap/v2/quote/contracts")["data"]
		s = self.send_request("GET", "/openApi/spot/v1/common/symbols")["data"]["symbols"]
		futures, spot = [], []
		for i in f:
			record = {}
			record["symbolUnstructured"] = i["symbol"]
			record["symbol"] = i["asset"] + "/" + i["currency"]
			record['leverageInfo'] = [
			    float(i["maxLongLeverage"]),
			    self.suggest_leverage(float(i["maxLongLeverage"])), 1
			]
			record['perp'] = True
			record['available'] = True if i['status'] else False
			record['minOrderQty'] = float(i['size'])
			record['maxOrderQty'] = -1
			record['assetTickSize'] = 10**-float(i['quantityPrecision'])
			record['minOrderAmt'] = -2  # should be calculated directly from minOrderQty
			record['maxOrderAmt'] = -1
			record['currencyTickSize'] = 10**-float(i['pricePrecision'])
			record['minPrice'] = -1
			record['maxPrice'] = -1
			record['priceTickSize'] = 10**-float(i['pricePrecision'])
			futures.append(record)

		for i in s:
			record = {}
			record["symbolUnstructured"] = i["symbol"]
			record["symbol"] = i["symbol"].replace("-", "/")
			record['leverageInfo'] = [-1, -1, -1]
			record['perp'] = False
			record['available'] = True if i['status'] else False
			record['minOrderQty'] = float(i['minQty'])
			record['maxOrderQty'] = float(i['maxQty'])
			record['assetTickSize'] = float(i['stepSize'])
			record['minOrderAmt'] = float(i['minNotional'])
			record['maxOrderAmt'] = float(i['maxNotional'])
			record['currencyTickSize'] = float(i['tickSize'])
			record['minPrice'] = -1
			record['maxPrice'] = -1
			record['priceTickSize'] = float(i['tickSize'])
			spot.append(record)

		return futures, spot

	def suggest_leverage(self, maxLeverage):
		if maxLeverage == 5:
			return [2, 3, 5]
		elif maxLeverage == 10:
			return [2, 3, 4, 5, 6, 10]
		elif maxLeverage == 25:
			return [2, 3, 5, 10, 15, 25]
		elif maxLeverage == 50:
			return [5, 10, 15, 20, 25, 50]
		elif maxLeverage == 75:
			return [5, 10, 20, 35, 50, 75]
		elif maxLeverage == 100:
			return [5, 10, 25, 50, 75, 100]
		elif maxLeverage == 125:
			return [5, 10, 25, 50, 75, 125]
		elif maxLeverage == 150:
			return [5, 10, 25, 50, 75, 150]
		else:
			print(f"WARNING - New Max Leverage Added! {maxLeverage}")
			return [1, maxLeverage]

	def get_high_volume_pairs(self, num=9, perp=True):
		# bingx api doesn't offer information on pair volume in spot market so we won't use perp variable
		info = {}
		path = "/openApi/swap/v2/quote/ticker"
		r = self.send_request("GET", path)["data"]
		for i in r:
			try:
				symbol = self.resolve_symbol(i["symbol"], forward=False)
				info[symbol] = float(i["quoteVolume"])
			except:
				continue
		return list(dict(sorted(info.items(), key=lambda item: item[1])).keys())[-1:-(1 + num):-1]

	def calculate_statement(self, statementSymbols: str):
		symbols = statementSymbols.split(":")

		result = {
		    "bingxTradesCount": 0,
		    "allSymbolsProfit": 0,
		    "numBuyPositions": 0,
		    "numSellPositions": 0,
		    "numWinTrade": 0,
		    "numLoseTrade": 0,
		    # 'numIsolatedPositions' : None,
		    # 'numCrossPositions' : None
		}

		for symbol in symbols:
			try:
				symbol_positions = self.get_order_history(symbol)
				if len(symbol_positions) == 0:
					continue

				result[symbol + "TradesCount"] = len(symbol_positions)
				result["bingxTradesCount"] += result[symbol + "TradesCount"]

				result[symbol + "Profit"] = 0
				result[symbol + "LoseTrade"] = 0
				result[symbol + "WinTrade"] = 0
				for position in symbol_positions:
					profit = float(position["profit"]) - float(position["commission"])
					result[symbol + "Profit"] += profit
					if profit >= 0:
						result["numWinTrade"] += 1
						result[symbol + "WinTrade"] += 1
					else:
						result["numLoseTrade"] += 1
						result[symbol + "LoseTrade"] += 1

					if position["side"] == "Ask":
						result["numBuyPositions"] += 1
					else:
						result["numSellPositions"] += 1

				result["allSymbolsProfit"] += result[symbol + "Profit"]

			except Exception as e:
				print(e)
				pass

		return result

	def get_balance(self, coins: list = None, perp=True):
		if perp:
			path = '/openApi/swap/v2/user/balance'
			r = self.send_request("GET", path)["data"]["balance"]

			r['balance'] = float(r['balance'])
			r["equity"] = float(r['equity'])
			r["unrealizedProfit"] = float(r['unrealizedProfit'])
			r["realisedProfit"] = float(r['realisedProfit'])
			r["availableMargin"] = float(r['availableMargin'])
			r["usedMargin"] = float(r['usedMargin'])
			r["locked"] = float(r.pop('freezedMargin'))

			r = [r]

		else:
			path = '/openApi/spot/v1/account/balance'
			r = self.send_request("GET", path)["data"]["balances"]
			for i in r:
				i['balance'] = float(i.pop('free'))
				i['locked'] = float(i['locked'])

		if len(r) == 0:
			return []
		if coins not in [None, []]:
			if len(coins) == 1:
				return [i for i in r if i['asset'] == coins[0]][0]
			return [i for i in r if i['asset'] in coins]
		return r


class ByBitClient(object):

	def __init__(self,
	             api_key=config.BYBIT_APIKEY,
	             api_secret=config.BYBIT_APISECRET,
	             dbh:databaseHandler=None,
				 testnet=True):
		
		self.session = HTTP(
		    api_key=api_key,
		    api_secret=api_secret,
		    testnet=testnet,
		    log_requests=True,
		)
		self.dbh = dbh

	def resolve_side(self, side):
		return "Buy" if side == "buy" else "Sell"

	def resolve_symbol(self, symbol, forward=True, perp=True):
		if forward:
			return symbol.replace("/", "")
		return self.dbh.get("pair", {
		    "exchange": config.BYBIT,
		    "symbolUnstructured": symbol,
		    "perp": perp
		}, "symbol")

	def placeOrder(self, category, symbol, side, price, qty, order_type, tp=None, sl=None):
		r = self.session.place_order(
		    category=category,  # spot or linear
		    side=self.resolve_side(side),
		    symbol=self.resolve_symbol(symbol),
		    order_type=order_type,
		    qty=float("{:.3f}".format(qty)),
		    price=price,
		    time_in_force="GTC",
		    reduce_only=False,
		    close_on_trigger=False,
		    take_profit=tp,
		    stop_loss=sl,
		)
		print(r)

	def full_partial_position_tp_sl_switch(self, symbol, perp=True):
		return self.session.set_tp_sl_mode(category="linear" if perp else "spot",
		                                   symbol=self.resolve_symbol(symbol),
		                                   tp_sl_mode="Partial")

	def set_trading_stop(self, symbol, side, take_profit=None, tp_size=0, perp=True):
		return self.session.set_trading_stop(
		    category="linear" if perp else "spot",
		    symbol=self.resolve_symbol(symbol),
		    side=self.resolve_side(side),
		    take_profit=take_profit,
		    tp_size=tp_size,
		    positionIdx=0,
		)

	def adjust_leverage_margin(self, symbol, leverage, is_isolated, perp=True):
		try:
			self.session.switch_margin_mode(
			    category="linear" if perp else "spot",
			    symbol=self.resolve_symbol(symbol),
			    tradeMode=bool(is_isolated),
			    buyLeverage=leverage,
			    sellLeverage=leverage,
			)
		except Exception as e:
			try:
				self.session.set_leverage(
				    category="linear" if perp else "spot",
				    symbol=self.resolve_symbol(symbol),
				    buyLeverage=leverage,
				    sellLeverage=leverage,
				)
			except Exception as e:
				pass

	def get_price(self, symbol, perp=True):
		return float(
		    self.session.get_public_trade_history(category="linear" if perp else "spot",
		                                          symbol=self.resolve_symbol(symbol),
		                                          limit=1)["result"]["list"][0]["price"])

	def get_pairs_info(self):
		f = self.session.get_instruments_info(category="linear")["result"]["list"]
		s = self.session.get_instruments_info(category="spot")["result"]["list"]
		futures, spot = [], []

		for i in f:
			record = {}
			record["symbolUnstructured"] = i["baseCoin"] + i["quoteCoin"]
			record["symbol"] = i["baseCoin"] + "/" + i["quoteCoin"]
			record['leverageInfo'] = [
			    float(i["leverageFilter"]["maxLeverage"]),
			    self.suggest_leverage(float(i["leverageFilter"]["maxLeverage"])),
			    float(i["leverageFilter"]["leverageStep"]),
			]
			record['perp'] = True
			record['available'] = True if i['status'] == "Trading" else False
			record['minOrderQty'] = float(i['lotSizeFilter']['minOrderQty'])
			record['maxOrderQty'] = float(i['lotSizeFilter']['maxOrderQty'])
			record['assetTickSize'] = float(i['lotSizeFilter']['qtyStep'])
			record['minOrderAmt'] = -2
			record['maxOrderAmt'] = -2
			record['currencyTickSize'] = float(i['priceFilter']['tickSize'])
			record['minPrice'] = float(i['priceFilter']['minPrice'])
			record['maxPrice'] = float(i['priceFilter']['maxPrice'])
			record['priceTickSize'] = float(i['priceFilter']['tickSize'])
			futures.append(record)

			if float(i["leverageFilter"]["minLeverage"]) != 1:
				print(f"WARNING - {record['symbol']} - minLeverage != 1")
			if float(i["leverageFilter"]["leverageStep"]) != 0.01:
				print(f"WARNING - {record['symbol']} - leverageStep != 0.01")

		for i in s:
			record = {}
			record["symbolUnstructured"] = i["baseCoin"] + i["quoteCoin"]
			record["symbol"] = i["baseCoin"] + "/" + i["quoteCoin"]
			record['leverageInfo'] = [-1, -1, -1]
			record['perp'] = False
			record['available'] = True if i['status'] == "Trading" else False
			record['minOrderQty'] = float(i['lotSizeFilter']['minOrderQty'])
			record['maxOrderQty'] = float(i['lotSizeFilter']['maxOrderQty'])
			record['assetTickSize'] = float(i['lotSizeFilter']['basePrecision'])
			record['minOrderAmt'] = float(i['lotSizeFilter']['minOrderAmt'])
			record['maxOrderAmt'] = float(i['lotSizeFilter']['maxOrderAmt'])
			record['currencyTickSize'] = float(i['lotSizeFilter']['quotePrecision'])
			record['minPrice'] = -1
			record['maxPrice'] = -1
			record['priceTickSize'] = float(i['priceFilter']['tickSize'])
			spot.append(record)

		return futures, spot

	def suggest_leverage(self, maxLeverage):
		if maxLeverage == 12.5:
			return [2, 3, 4, 5, 10, 12.5]
		elif maxLeverage == 25:
			return [2, 3, 4, 5, 10, 25]
		elif maxLeverage == 50:
			return [2, 3, 5, 10, 15, 50]
		elif maxLeverage == 66.67:
			return [2, 3, 5, 10, 25, 66.67]
		elif maxLeverage == 100:
			return [3, 5, 10, 25, 50, 100]
		elif maxLeverage == 125:
			return [3, 5, 10, 25, 50, 125]
		else:
			print(f"WARNING - New Max Leverage Added! {maxLeverage}")
			return [1, 2, 3]

	def get_high_volume_pairs(self, num=9, perp=True):
		info = {}
		r = self.session.get_tickers(category="linear" if perp else "spot")["result"]["list"]
		counter = 0
		for i in r:
			try:
				symbol = i["symbol"]
				if symbol.endswith("PERP") or symbol.count("-"):
					continue
				info[self.resolve_symbol(symbol, forward=False, perp=perp)] = float(i["volume24h"]) * float(i["lastPrice"])
			except:
				continue
		return list(dict(sorted(info.items(), key=lambda item: item[1])).keys())[-1:-(1 + num):-1]

	# Add pagination
	def get_order_history(self, symbol):
		result = []

		try:
			result = self.session.get_closed_pnl(category="linear", symbol=self.resolve_symbol(symbol),
			                                     limit=100)["result"]["list"]
			# current_page = r['result']['current_page']

			# for i in range (current_page - 1):
			#     r = self.session.get_closed_pnl(
			#         category = category,
			#         symbol = symbol,
			#         limit = 100,
			#         cursor = i+2
			#     )

			#     result.extend(r['result']['list'])

		except:
			pass

		finally:
			return result

	def calculate_statement(self, statementSymbols: str):
		symbols = statementSymbols.split(":")

		result = {
		    "bybitTradesCount": 0,
		    "allSymbolsProfit": 0,
		    "numBuyPositions": 0,
		    "numSellPositions": 0,
		    "numWinTrade": 0,
		    "numLoseTrade": 0,
		    # 'numIsolatedPositions' : None,
		    # 'numCrossPositions' : None
		}

		for symbol in symbols:
			try:
				symbol_positions = self.get_order_history(symbol)
				if len(symbol_positions) == 0:
					continue

				result[symbol + "TradesCount"] = len(symbol_positions)
				result["bybitTradesCount"] += result[symbol + "TradesCount"]

				result[symbol + "Profit"] = 0
				result[symbol + "LoseTrade"] = 0
				result[symbol + "WinTrade"] = 0

				for position in symbol_positions:
					profit = float(position["closedPnl"])
					result[symbol + "Profit"] += profit
					if profit >= 0:
						result["numWinTrade"] += 1
						result[symbol + "WinTrade"] += 1
					else:
						result["numLoseTrade"] += 1
						result[symbol + "LoseTrade"] += 1

					if position["side"] == "Sell":
						result["numBuyPositions"] += 1
					else:
						result["numSellPositions"] += 1

				result["allSymbolsProfit"] += result[symbol + "Profit"]

			except Exception as e:
				print(e)
				pass

		return result

	def get_balance(self, coins: list = None, perp=True):
		accountType = "CONTRACT" if perp else "SPOT"
		coins = None if coins == None else ','.join(coins)
		balance = self.session.get_coins_balance(accountType=accountType, coin=coins)['result']['balance']
		for i in balance:
			i['asset'] = i.pop('coin')
			i['balance'] = float(i.pop('transferBalance'))
			i['locked'] = float(i.pop('walletBalance')) - i['balance']
			i.pop('bonus')
		if len(balance) == 1:
			return balance[0]
		return balance


class CoinexClient(object):
	__headers = {
	    "Content-Type":
	        "application/json; charset=utf-8",
	    "Accept":
	        "application/json",
	    "User-Agent":
	        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36",
	}

	def __init__(
	    self,
	    access_id=config.COINEX_APIKEY,
	    secret_key=config.COINEX_APISECRET,
	    dbh: databaseHandler = None,
	    logger=None,
	    debug=False,
	):
		self.access_id = access_id
		self.secret_key = secret_key
		self.headers = self.__headers
		self.host = "https://api.coinex.com"
		self.host_perp_suffix = "/perpetual"
		session = requests.Session()
		self.dbh = dbh
		session.mount("http://", requests.adapters.HTTPAdapter())
		session.mount("https://", requests.adapters.HTTPAdapter())
		self.http_client = session
		self.logger = logger or logging

	def resolve_side(self, side, perp=True):
		if perp:
			return 2 if side == "buy" else 1
		else:
			return side

	def resolve_symbol(self, symbol, forward=True):
		if forward:
			return symbol.replace("/", "")
		return self.dbh.get("pair", {
		    "exchange": config.COINEX,
		    "symbolUnstructured": symbol,
		    "perp": True
		}, "symbol")

	def get_sign(self, params, secret_key, perp):
		sort_params = sorted(params)
		data = []
		for item in sort_params:
			data.append(item + '=' + str(params[item]))

		str_params = "{0}&secret_key={1}".format("&".join(data), secret_key).encode()

		if perp:
			return hashlib.sha256(str_params).hexdigest()
		return hashlib.md5(str_params).hexdigest().upper()
		

	def set_authorization(self, params, headers, perp=True):
		headers["AccessId"] = self.access_id
		headers["Authorization"] = self.get_sign(params, self.secret_key, perp)

	def get(
	    self,
	    path,
	    params=None,
	    sign=True,
	    perp=True,
	):
		url = self.host + perp * self.host_perp_suffix + "/v1" + path

		params = params or {}
		params["access_id"] = self.access_id
		if perp:
			params["timestamp"] = int(time.time() * 1000)
		else:
			params["tonce"] = int(time.time() * 1000)
		headers = copy.copy(self.headers)
		if sign:
			self.set_authorization(params, headers, perp)
		try:
			response = self.http_client.get(url, params=params, headers=headers, timeout=5)
			if response.status_code == requests.codes.ok:
				return response.json()
			else:
				self.logger.error("URL: {0}\nSTATUS_CODE: {1}\nResponse: {2}".format(
				    response.request.url, response.status_code, response.text))
				return None
		except Exception as ex:
			trace_info = traceback.format_exc()
			self.logger.error("GET {url} failed: \n{trace_info}".format(url=url, trace_info=trace_info))
			return None

	def post(self, path, data=None, perp=True):
		url = self.host + perp * self.host_perp_suffix + "/v1" + path
		data = data or {}
		data["access_id"] = self.access_id
		if perp:
			data["timestamp"] = int(time.time() * 1000)
		else:
			data["tonce"] = int(time.time() * 1000)
		headers = copy.copy(self.headers)
		self.set_authorization(data, headers, perp)
		try:
			response = self.http_client.post(url, data=data, headers=headers, timeout=10)
			# self.logger.info(response.request.url)
			if response.status_code == requests.codes.ok:
				return response.json()
			else:
				self.logger.error("URL: {0}\nSTATUS_CODE: {1}\nResponse: {2}".format(
				    response.request.url, response.status_code, response.text))
				return None
		except Exception as ex:
			trace_info = traceback.format_exc()
			self.logger.error("POST {url} failed: \n{trace_info}".format(url=url, trace_info=trace_info))
			return None

	def adjust_leverage(self, market, position_type, leverage):
		path = "/market/adjust_leverage"
		data = {
		    "market": self.resolve_symbol(market),
		    "position_type": position_type,
		    "leverage": leverage
		}
		return self.post(path, data)

	def get_price(self, market, perp=True):
		path = "/market/ticker"
		data = {
		    "market": self.resolve_symbol(market)
		}
		a = self.get(path, data, perp=perp)
		print(a)
		return float(a["data"]["ticker"]["last"])

	def put_market_order(self, market, side, amount, perp=True):
		if perp:
			path = "/order/put_market"
			data = {
			    "market": self.resolve_symbol(market),
			    "amount": str(amount),
			    "side": self.resolve_side(side, perp),
			}
			return self.post(path, data)
		else:
			path = "/order/market"
			data = {
			    "market": self.resolve_symbol(market),
			    "amount": str(amount),
			    "type": self.resolve_side(side, perp),
			    "access_id": self.access_id,
			}
			return self.post(path, data, perp=False)

	def put_limit_order(self, market, side, amount, price, effect_type=1, perp=True):
		if perp:
			path = "/order/put_limit"
			data = {
			    "market": self.resolve_symbol(market),
			    "effect_type": effect_type,
			    "side": self.resolve_side(side, perp),
			    "amount": str(amount),
			    "price": str(price),
			}
			return self.post(path, data)
		else:
			path = "/order/limit"
			data = {
			    "market": self.resolve_symbol(market),
			    "type": self.resolve_side(side, perp),
			    "amount": str(amount),
			    "price": str(price),
			    "access_id": self.access_id,
			}
			return self.post(path, data, perp=False)

	def put_stop_market_order(self, market, side, amount, stop_price, stop_type=2, perp=True):
		if perp:
			path = "/order/put_stop_market"
			data = {
			    "market": self.resolve_symbol(market),
			    "side": self.resolve_side(side, perp),
			    "amount": str(amount),
			    "stop_price": str(stop_price),
			    "stop_type": stop_type,
			}
			return self.post(path, data)
		else:
			path = "/order/stop/market"
			data = {
			    "market": self.resolve_symbol(market),
			    "type": self.resolve_side(side, perp),
			    "amount": str(amount),
			    "stop_price": str(stop_price),
			    "access_id": self.access_id,
			}
			return self.post(path, data, perp=False)

	def get_order_history(self, market):
		result = []

		try:
			path = "/market/user_deals"
			data = {
			    "market": self.resolve_symbol(market),
			    "side": 0,
			    "offset": 0,
			    "limit": 100
			}
			result = self.get(path, data)["data"]["records"]
			if len(result) == data["limit"]:
				ended = False
				cnt = 1
				while not ended:
					data["offset"] = data["limit"] * cnt
					extra_results = self.get(path, data)["data"]["records"]
					if extra_results == []:
						ended = True
						continue
					result.extend(extra_results)

					cnt += 1

			result = [i for i in result if i["deal_type"] == 4]

		except:
			pass

		finally:
			return result

	def get_pairs_info(self):
		f = self.get("/market/list")["data"]
		s = [v for k, v in self.get("/market/info", perp=False)["data"].items()]
		futures, spot = [], []

		for i in f:
			record = {}
			record["symbolUnstructured"] = i.pop("name")
			record["symbol"] = i["stock"] + "/" + i["money"]
			record['leverageInfo'] = [float(i["leverages"][-1]), [int(l) for l in i["leverages"]], -1]
			record['perp'] = True
			record['available'] = i['available']
			record['minOrderQty'] = float(i['amount_min'])
			record['maxOrderQty'] = -1
			record['assetTickSize'] = 10**-float(i['stock_prec'])
			record['minOrderAmt'] = -2
			record['maxOrderAmt'] = -1
			record['currencyTickSize'] = 10**-float(i['money_prec'])
			record['minPrice'] = -1
			record['maxPrice'] = -1
			record['priceTickSize'] = float(i['tick_size'])
			futures.append(record)

		for i in s:
			record = {}
			record["symbolUnstructured"] = i.pop("name")
			record["symbol"] = i["trading_name"] + "/" + i["pricing_name"]
			record['leverageInfo'] = [-1, -1, -1]
			record['perp'] = False
			record['available'] = True
			record['minOrderQty'] = float(i['min_amount'])
			record['maxOrderQty'] = -1
			record['assetTickSize'] = 10**-float(i['trading_decimal'])
			record['minOrderAmt'] = -2
			record['maxOrderAmt'] = -1
			record['currencyTickSize'] = 10**-float(i['trading_decimal'])
			record['minPrice'] = -1
			record['maxPrice'] = -1
			record['priceTickSize'] = 10**-float(i['pricing_decimal'])
			spot.append(record)

		return futures, spot

	def get_high_volume_pairs(self, num=9, perp=True):
		info = {}
		path = "/market/ticker/all"
		r = self.get(path, perp=perp)["data"]["ticker"]

		for k, v in r.items():
			try:
				symbol = self.resolve_symbol(k.split("_")[0], forward=False)
				info[symbol] = float(v["vol"]) * float(v["last"])
			except:
				continue
		return list(dict(sorted(info.items(), key=lambda item: item[1])).keys())[-1:-(1 + num):-1]

	def calculate_statement(self, statementSymbols: str):
		symbols = statementSymbols.split(":")

		result = {
		    "coinexTradesCount": 0,
		    "allSymbolsProfit": 0,
		    "numBuyPositions": 0,
		    "numSellPositions": 0,
		    "numWinTrade": 0,
		    "numLoseTrade": 0,
		    # 'numIsolatedPositions' : 0,
		    # 'numCrossPositions' : 0
		}

		for symbol in symbols:
			try:
				symbol_positions = self.get_order_history(symbol)
				if len(symbol_positions) == 0:
					continue

				result[symbol + "TradesCount"] = len(symbol_positions)
				result["coinexTradesCount"] += result[symbol + "TradesCount"]

				result[symbol + "Profit"] = 0
				result[symbol + "LoseTrade"] = 0
				result[symbol + "WinTrade"] = 0
				for position in symbol_positions:
					profit = float(position["deal_profit"]) - float(position["deal_fee"])
					result[symbol + "Profit"] += profit
					if profit >= 0:
						result["numWinTrade"] += 1
						result[symbol + "WinTrade"] += 1
					else:
						result["numLoseTrade"] += 1
						result[symbol + "LoseTrade"] += 1

					if position["side"] == 1:
						result["numBuyPositions"] += 1
					else:
						result["numSellPositions"] += 1

					# if position['position_type'] == 1:
					#     result['numIsolatedPositions'] += 1
					# else:
					#     result['numCrossPositions'] += 1

				result["allSymbolsProfit"] += result[symbol + "Profit"]

			except Exception as e:
				print(e)
				pass

		return result

	def get_balance(self, coins: list = None, perp=True):
		if perp:
			path = '/asset/query'
			r = self.get(path, perp=True)["data"]
			for k, v in r.items():
				v['asset'] = k
				v['balance'] = float(v.pop('available'))
				v['locked'] = float(v.pop('frozen'))
				v['transfer'] = float(v['transfer'])
				v['balance_total'] = float(v['balance_total'])
				v['margin'] = float(v['margin'])
				v['profit_unreal'] = float(v['profit_unreal'])
			r = list(r.values())

		else:
			path = '/balance/info'
			r = self.get(path, perp=False)["data"]
			for k, v in r.items():
				v['asset'] = k
				v['balance'] = float(v.pop('available'))
				v['locked'] = float(v.pop('frozen'))
			r = list(r.values())

		if len(r) == 0:
			return []
		if coins not in [None, []]:
			if len(coins) == 1:
				return [i for i in r if i['asset'] == coins[0]][0]
			return [i for i in r if i['asset'] in coins]
		return r


class exchangeClient(object):

	def __init__(self, exchangeName, API_Key, API_Secret, dbh) -> None:
		if exchangeName == config.BINGX:
			self.client = BingXClient(API_Key, API_Secret, dbh)

		elif exchangeName == config.BYBIT:
			self.client = ByBitClient(API_Key, API_Secret, dbh)

		elif exchangeName == config.COINEX:
			self.client = CoinexClient(API_Key, API_Secret, dbh)