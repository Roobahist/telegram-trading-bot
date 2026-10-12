import itertools
import json
import random
import string
import decimal
from datetime import timedelta

import config


def createSecret(N):
	return "".join(
	    random.SystemRandom().choice(string.ascii_uppercase + string.digits + string.ascii_lowercase) for _ in range(N))


def flatten(List) -> list:
	return list(itertools.chain(*List))


def pprintupdate(update):
	print(json.dumps(json.loads(update.to_json()), indent=4, sort_keys=True))


def createMenu(other_items, baseMenu: list = []):
	menu = baseMenu[:]
	if type(other_items) == str:
		menu.append([other_items])
	elif type(other_items) == list:
		for item in other_items:
			if item not in [None, []]:
				if type(item) == list:
					menu.append(list(item))
				else:
					menu.append([item])
	return menu


def createMenuFromList(items: list, columns=None, rows=None):
	menu = []

	if len(items) == 0:
		return menu

	if columns is None and rows is None:
		columns = 3

	if rows != None:
		while len(items) < rows:
			rows -= 1
		in_each_row = len(items) // rows
		row_counter = 0
		while row_counter < rows - 1:
			menu.append(items[row_counter * in_each_row:(row_counter+1) * in_each_row])
			row_counter += 1
		menu.append(items[row_counter * in_each_row:])

	elif columns != None:
		while len(items) < columns:
			columns -= 1
		in_each_row = columns
		item_counter = 0
		while len(items) - item_counter > in_each_row:
			menu.append(items[item_counter:item_counter + in_each_row])
			item_counter += in_each_row
		menu.append(items[item_counter:])

	return menu


def createRegex(possible_patterns: list, any: bool = True):
	final_pattern = "^("
	for pattern in possible_patterns:
		final_pattern += "^" + str(pattern) + "$" + "|"
	final_pattern = "^" + final_pattern[:-1] + "$" + ")$"
	return final_pattern


def days_hours_minutes(td: timedelta):
	return td.days, td.seconds // 3600, (td.seconds // 60) % 60


async def addDict(dict1: dict, dict2: dict):
	for key, value in dict2.items():
		if key in list(dict1.keys()):
			dict1[key] += value
		else:
			dict1[key] = value

	return dict1


def createOrderInfo(orderInfo: dict, gettingdata: str, public=False):
	volumeAsset = ''
	currency = ''
	if gettingdata == "tradeVolume" or orderInfo["tradeVolume"] is not None:
		asset, currency = orderInfo["tradePair"].split('/')
		volumeAsset = currency if orderInfo["tradeSide"] == config.BUY or orderInfo["tradeMarket"] == config.FUTURES else asset

	# print('*****************')
	# for k, v in orderInfo.items():
	# 	print(k, '=', v)
	# print('*****************')
	
	message = ''
	message += f'Exchange : {orderInfo["tradeExchange"]} \n'
	message += f'Market : {orderInfo["tradeMarket"]} \n'
	message += f'Pair : {orderInfo["tradePair"]} \n'
	message += f'Side : {orderInfo["tradeSide"]} \n'

	message += '\n'
	if orderInfo["tradeMarket"] != config.SPOT:
		message += f'Leverage : {orderInfo["tradeLeverage"]} \n'
	message += f'Volume : {orderInfo["tradeVolume"]} {volumeAsset}\n'
	message += '\n'
	for i in range(int(orderInfo["tradeEntryNum"])):
		try:
			price = orderInfo["tradeEntry"].split("#")[i]
		except:
			price = None
		try:
			if not public:
				volume = orderInfo["tradeEntryVol"].split("#")[i].split("|")[0] + f" {volumeAsset}"
			else:
				volume = orderInfo["tradeEntryVol"].split("#")[i].split("|")[1] + "%"
		except:
			volume = None
		
		message += f'\U0001F53A Entry {number_to_emoji(i+1)}\n'
		message += f'┝━ Price : {price} {currency if price != config.MARKET else ""}\n'
		message += f'┕━ Volume : {volume}\n'

		# message += f'Entry {i} Price : {price} {currency if price != config.MARKET else ""}\n'
		# message += f'Entry {i} Volume : {volume} {volumeAsset}\n'
		
	if orderInfo["tradeStoplossNum"] != config.NO_SL:
		message += '\n'
		for i in range(int(orderInfo["tradeStoplossNum"])):
			try:
				price = orderInfo["tradeStoploss"].split("#")[i]
			except:
				price = None
			try:
				volume = orderInfo["tradeStoplossVol"].split("#")[i].split("|")[1] + "%"
			except:
				volume = None

			message += f'\U0001F53B StopLoss {number_to_emoji(i+1)}\n'
			message += f'┝━ Price : {price} {currency if price != config.MARKET else ""}\n'
			message += f'┕━ Volume : {volume}\n'

	if orderInfo["tradeTakeprofitNum"] != config.NO_TP:
		message += '\n'
		for i in range(int(orderInfo["tradeTakeprofitNum"])):
			try:
				price = orderInfo["tradeTakeprofit"].split("#")[i]
			except:
				price = None
			try:
				volume = orderInfo["tradeTakeprofitVol"].split("#")[i].split("|")[1] + "%"
			except:
				volume = None

			print(price, volume)
			message += f'\U0001F53B TakeProfit {number_to_emoji(i+1)}\n'
			message += f'┝━ Price : {price} {currency if price != config.MARKET else ""}\n'
			message += f'┕━ Volume : {volume}\n'

	message = message.replace('None', '\U00002049')
	if message.find('\U00002049') >= 0:
		index = message.find('\U00002049')
		message = message[:index] + "\U00002754" + message[index+1:]

	return message


def round_to_multiple(number, multiple, down=False):
	lenDecimal = abs(decimal.Decimal(str(multiple)).as_tuple().exponent)
	valueAdjusted = multiple * round(number / multiple)
	if down and valueAdjusted > number:
		return float(format(valueAdjusted - multiple, f'.{lenDecimal}f'))
	return float(format(valueAdjusted, f'.{lenDecimal}f'))


def number_to_emoji(num:int, number_sign=False):
	if number_sign:
		converted = "#️⃣"
	else:
		converted = ""

	if   num == 0:
		converted += "0️⃣"
	elif num == 1:
		converted += "1️⃣"
	elif num == 2:
		converted += "2️⃣"
	elif num == 3:
		converted += "3️⃣"
	elif num == 4:
		converted += "4️⃣"
	elif num == 5:
		converted += "5️⃣"
	elif num == 6:
		converted += "6️⃣"
	elif num == 7:
		converted += "7️⃣"
	elif num == 8:
		converted += "8️⃣"
	elif num == 9:
		converted += "9️⃣"
	elif num == 10:
		converted += "🔟"

	return converted

	
