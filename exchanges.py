from database import databaseHandler
from ExchangeClients import BingXClient, ByBitClient, CoinexClient
import config
from trading_bot.parsing import parse_tradingview_payload
from trading_bot.runtime import require_live_trading


def active_exchanges(user_id: int, dbh: databaseHandler) -> dict:
	binance_active = dbh.get('user', {'userId': user_id}, 'binance_active')
	bybit_active = dbh.get('user', {'userId': user_id}, 'bybit_active')
	coinex_active = dbh.get('user', {'userId': user_id}, 'coinex_active')
	bingx_active = dbh.get('user', {'userId': user_id}, 'bingx_active')

	return {
	    'binance': binance_active,
	    'bybit': bybit_active,
	    'coinex': coinex_active,
	    'bingx': bingx_active
	}


def get_api_credentials(user_id: int, exchange_name: str, dbh: databaseHandler) -> list:
	if user_id == -1:
		return getattr(config, exchange_name.upper() + '_APIKEY'), getattr(config, exchange_name.upper() + '_APISECRET')
	if exchange_name == config.COINEX:
		exchange_name = 'coinex'
	elif exchange_name == config.BYBIT:
		exchange_name = 'bybit'
	elif exchange_name == config.BINGX:
		exchange_name = 'bingx'

	return [i.strip() for i in dbh.get('user', {
	    'userId': user_id
	}, exchange_name + '_api').split("#")]


def reverse(side: int):
	return 'sell' if side == 'buy' else 'buy'


def process_tradingview_signal(order_message, dbh: databaseHandler) -> list:
	order_message = parse_tradingview_payload(order_message)
	user_id = order_message['id']
	if not dbh.has_subscription(user_id):
		return False

	secret = order_message['secret']
	if dbh.get('user', {'userId': user_id}, 'secret') != secret:
		print("Wrong secret")
		return False

	leverage = int(dbh.get('user', {'userId': user_id}, 'leverage'))
	market = order_message['ticker']
	strategy = order_message['strategy']
	side = strategy['order_action']
	amount = strategy['position_size']

	exchanges = active_exchanges(user_id, dbh)
	for exchange, is_active in exchanges.items():
		if is_active:
			require_live_trading()
			if exchange == 'coinex':
				client = CoinexClient(*get_api_credentials(user_id, 'coinex', dbh))
				try:
					client.adjust_leverage(market, 1, leverage)
				except:
					pass
				client.put_market_order(market, side, amount)

			if exchange == 'bingx':
				client = BingXClient(*get_api_credentials(user_id, exchange, dbh))
				try:
					client.switch_leverage(market, side, leverage)
					client.swith_margin_mode(market, "Isolated")
				except:
					pass
				client.placeOrder(market, side, 0, amount, 'Market', 'Open')

			if exchange == 'bybit':
				client = ByBitClient(*get_api_credentials(user_id, exchange, dbh))
				try:
					client.adjust_leverage_margin(market, leverage, is_isolated=True)
				except:
					pass
				client.placeOrder(market, side, 0, amount, 'Market')

			if exchange == 'binance':
				pass


def process_telegram_signal(order_message, chat_id, group_channel_direct, dbh: databaseHandler) -> list:

	market = order_message.split('\n')[0][6:-6].strip()
	side = order_message.split('Side:')[1].split('\n')[0].strip().lower()
	targets = [
	    float(i.split(')')[1].strip())
	    for i in order_message.split('Targets:')[1].split('Stop Loss:')[0].strip().split('\n')
	]
	sl = float(order_message.split('Stop Loss:')[1].strip())

	print(f'market = {market}, side = {side}, targets = {targets}, sl = {sl}')

	if group_channel_direct == 'group':
		user_ids = [ug.userId for ug in dbh.get_records('user_group', {'groupId': chat_id})]
	elif group_channel_direct == 'channel':
		user_ids = [uc.userId for uc in dbh.get_records('user_channel', {'channelId': chat_id})]
	elif group_channel_direct == 'direct':
		user_ids = [chat_id]

	print(f'user_ids = {user_ids}')

	for user_id in user_ids:
		if not dbh.has_subscription(user_id):
			continue

		leverage = int(dbh.get('user', {'userId': user_id}, 'leverage'))

		exchanges = active_exchanges(user_id, dbh)
		for exchange, is_active in exchanges.items():
			if is_active:
				require_live_trading()
				if exchange == 'coinex':
					print(f'=================={exchange}==================')
					client = CoinexClient(*get_api_credentials(user_id, exchange, dbh))
					amount = round(
					    float(dbh.get('user', {'userId': user_id}, 'volume')) * leverage / client.get_price(market), 3)
					try:
						client.adjust_leverage(market, 1, leverage)
					except:
						pass
					client.put_market_order(market, side, amount)
					for tp in targets:
						client.put_limit_order(market, reverse(side), round(amount / len(targets), 3), tp)
					client.put_stop_market_order(market, reverse(side), amount, sl)

				if exchange == 'bingx':
					print(f'=================={exchange}==================')
					client = BingXClient(*get_api_credentials(user_id, exchange, dbh))
					amount = round(
					    float(dbh.get('user', {'userId': user_id}, 'volume')) * leverage / client.get_price(market), 3)
					print(amount)
					try:
						client.switch_leverage(market, side, leverage)
						client.swith_margin_mode(market, "Isolated")
					except:
						pass
					r = client.placeOrder(market, side, 0, amount, 'Market', 'Open', tp=None, sl=sl)
					print(r)
					for tp in targets:
						r = client.placeOrder(market, reverse(side), tp, round(amount / len(targets), 3), 'Limit',
						                      'Open')
						print(r)

				if exchange == 'bybit':
					print(f'=================={exchange}==================')
					client = ByBitClient(*get_api_credentials(user_id, exchange, dbh))
					amount = round(
					    float(dbh.get('user', {'userId': user_id}, 'volume')) * leverage / client.get_price(market), 3)
					try:
						client.adjust_leverage_margin(market, leverage, is_isolated=True)
					except:
						pass
					try:
						client.full_partial_position_tp_sl_switch(market)
					except:
						pass
					client.placeOrder(market, side, 0, amount, 'Market', tp=None, sl=sl)

					each_tp_size = round(amount / len(targets), 3)
					for tp in targets[:-1]:
						client.set_trading_stop(market, side, tp, each_tp_size)
					client.set_trading_stop(market, side, targets[-1],
					                        round(amount - (len(targets) - 1) * each_tp_size, 3))

				if exchange == 'binance':
					pass
