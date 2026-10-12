# pylint: disable=unused-argument, wrong-import-position

import logging
import os
import sys
from datetime import datetime, time
from re import UNICODE, U, match, split
from shutil import which

import requests
from sqlalchemy.orm import Session
from telegram import (ForceReply, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update)
from telegram.constants import ChatType, ParseMode, ChatMemberStatus
from telegram.ext import (Application, CommandHandler, ContextTypes, ConversationHandler, JobQueue, MessageHandler,
                          filters)
from telegram.helpers import escape_markdown

import config
import models
from database import SessionLocal, databaseHandler, engine
from ExchangeClients import exchangeClient
from exchanges import *
from helperfunctions import *
from makestatement import calculateStatementData, plotStatement
from texts import t
from trading_bot.parsing import parse_stored_list

models.Base.metadata.create_all(bind=engine)
session = Session(engine)
dbh = databaseHandler(session, models)

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

(MAINMENU, AUTOMATION_MENU, STATEMENT_MENU, MANAGEMENT_MENU, ACCOUNTSTATUS_MENU, COPYTRADEADMINS_MENU, CREATENEWSIGNAL_MENU, 
 MYFOLLOWERS_MENU, APIMANAGEMENT_MENU,TRADINGCONSTANTS_MENU, TELEGRAMGROUP_MENU, TELEGRAMCHANNEL_MENU, SENDSIGNALDIRECTLY_MENU, 
 SUBSCRIBE_MENU, ADMIN_MENU, REFERRAL_MENU) = range(16)


def user_id(update: Update):
	return update.message.from_user.id


async def check_transaction(hash: str, required_amount: float) -> bool:
	headers = {
	    'TRON-PRO-API-KEY': config.TRONSCAN_APIKEY
	}
	data = {
	    'hash': hash
	}
	r = requests.get(url=config.TRONSCAN_API_BASE + '/transaction-info', data=data, headers=headers)
	j = r.json()
	confirmed = j["confirmed"]
	tokenTransferInfo = j["tokenTransferInfo"]
	symbol = tokenTransferInfo["symbol"]
	to_address = tokenTransferInfo["to_address"]
	amount = int(tokenTransferInfo["amount_str"]) / (10**int(tokenTransferInfo["decimals"]))
	if confirmed:
		if symbol == "USDT":
			if to_address == config.USDT_TRC20_WALLET_ADDRESS:
				if amount == required_amount:
					return True, round(amount)
	return False, -1


async def check_wallet_address(address: str) -> bool:
	if len(address) == 34:
		if address[0] == 'T':
			headers = {
			    'TRON-PRO-API-KEY': config.TRONSCAN_APIKEY
			}
			data = {
			    'address': address,
			    'asset_type': 0
			}
			r = requests.get(url=config.TRONSCAN_API_BASE + '/account/wallet', data=data, headers=headers)
			j = r.json()
			if j['data'] != '[null]':
				return True
	return False


async def check_float(string: str) -> bool:
	try:
		float(string)
		return True
	except ValueError:
		return False


async def unrecognized(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	order_message_id = dbh.get("user", {"userId": user_id(update)}, "specificMessage")
	await remove_until_message(update, context, order_message_id)
	# user = update.message.from_user
	# logger.info("User %s sent an unrecognized message.", user.first_name)
	await send_message(update, t('UNRECOGNIZED'))

	return await refresh(update, context)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
	if config.OFFLINE:
		if user_id(update) not in config.ADMINS_ID:
			return

	dbh.start(update)
	dbh.set_states(user_id(update), "mainmenu", "mainmenu")
	dbh.reset(user_id(update))

	if bool(match("^\/start [0-9]+$", update.message.text)):
		referralCode = update.message.text.split('/start ')[1]
		if int(referralCode) != int(user_id(update)):
			if dbh.get("user", {"userId": user_id(update)}, "referredBy") == None:
				if int(referralCode) in dbh.get_column_values("user", "userId"):
					referrerUser = dbh.get_user(referralCode)
					if referrerUser.referredBy != user_id(update):
						if dbh.get_user(user_id(update)).joinedOn >= referrerUser.joinedOn:
							if dbh.set("user", {"userId": user_id(update)}, {"referredBy": referrerUser}):
								dbh.subscribe(user_id(update), 5, referral=True)
								msg = t("REFERRAL_CODE_ACCEPTED")
							else:
								msg = t("GET_DATA_UNSUCCESSFUL")
						else:
							msg = t("ENTER_REFERRAL_CODE_E1")
					else:
						msg = t("ENTER_REFERRAL_CODE_E2")
				else:
					msg = t("ENTER_REFERRAL_CODE_E3")
			else:
				msg = t("ENTER_REFERRAL_CODE_E4")
		else:
			msg = t("ENTER_REFERRAL_CODE_E5")
		await send_message(update, msg)

	await send_message(
	    update,
	    t('START'),
	    config.Main_Menu if user_id(update) not in config.ADMINS_ID else createMenu([config.ADMIN], config.Main_Menu),
	)

	return MAINMENU


async def mainmenu(update: Update, context: ContextTypes.DEFAULT_TYPE, back_call = False):
	dbh.set_states(user_id(update), "mainmenu", "mainmenu")
	dbh.reset(user_id(update))

	await send_message(
	    update,
	    t("MAINMENU"),
	    config.Main_Menu if user_id(update) not in config.ADMINS_ID else createMenu([config.ADMIN], config.Main_Menu),
	)

	return MAINMENU


async def automation(update: Update, context: ContextTypes.DEFAULT_TYPE, back_call = False):
	dbh.set_states(user_id(update), "automation", "mainmenu")
	await send_message(update, t('AUTOMATION'), config.Automation_Menu)
	return AUTOMATION_MENU


async def statement(update: Update, context: ContextTypes.DEFAULT_TYPE, back_call = False):
	dbh.set_states(user_id(update), "statement", "mainmenu")
	await send_message(update, t('STATEMENT'), config.Statement_Menu)
	return STATEMENT_MENU


async def management(update: Update, context: ContextTypes.DEFAULT_TYPE, back_call = False):
	dbh.set_states(user_id(update), "management", "mainmenu")
	await send_message(update, t('MANAGEMENT'), config.Management_Menu)
	return MANAGEMENT_MENU


async def copytradeadmins(update: Update, context: ContextTypes.DEFAULT_TYPE, back_call = False):
	dbh.set_states(user_id(update), "copytradeadmins", "mainmenu")
	await send_message(update, t("COPYTRADEADMINS"), config.CopyTradeAdmins_Menu)
	return COPYTRADEADMINS_MENU


async def account_status(update: Update, context: ContextTypes.DEFAULT_TYPE, back_call = False):
	dbh.set_states(user_id(update), "account_status", "mainmenu")
	deadline = dbh.get("user", {"userId": user_id(update)}, "subscriptionEndingTime")
	d, h, m = days_hours_minutes(deadline - datetime.now())
	expired = False
	if d < 0 or h < 0 or m < 0:
		d, h, m = 0, 0, 0
		expired = True

	msg = t("ACCOUNT_STATUS", [d, h, m])
	if expired:
		msg += '\n' + t("SUBSCRIPTION_EXPIRED")
	await send_message(update, msg, config.AccountStatus_Menu)

	return ACCOUNTSTATUS_MENU


async def contact_us(update: Update, context: ContextTypes.DEFAULT_TYPE, back_call = False):
	dbh.set_states(user_id(update), "contact_us", "mainmenu")
	await send_message(update, t("CONTACT_US"), escape=False)
	return await back(update, context)


async def instruction(update: Update, context: ContextTypes.DEFAULT_TYPE, back_call = False):
	dbh.set_states(user_id(update), "instruction", "mainmenu")
	await send_message(update, t("AUTOMATION_INSTRUCTION"))
	await send_message(update, t("STATEMENT_INSTRUCTION"))
	await send_message(update, t("MANAGEMENT_INSTRUCTION"))
	await send_message(update, t("ACCOUNT_STATUS_INSTRUCTION"))
	await send_message(update, t("CONTACT_US_INSTRUCTION"))
	return await back(update, context)


#list of users should be reversed or not?
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE, back_call = False):
	if user_id(update) not in config.ADMINS_ID:
		return await mainmenu(update, context)

	dbh.set_states(user_id(update), "admin", "mainmenu")

	user_ids = list(reversed(dbh.get_column_values('user', 'id')))
	user_userIds = list(reversed(dbh.get_column_values('user', 'userId')))
	user_usernames = list(reversed(dbh.get_column_values('user', 'username')))
	if update.message.text == config.ADMIN:
		await send_message(
		    update,
		    t("ADMIN", [len(user_ids)]),
		)
		await send_message(
		    update,
		    ''.join(t("USER_INFO", [i, j, k]) for i, j, k in zip(user_ids, user_usernames, user_userIds)),
		    config.Admin_Menu,
		    escape=False,
		)
		return ADMIN_MENU

	if update.message.text == config.SEND_MESSAGE_TO_ALL:
		await send_message(
		    update,
		    t("SEND_MESSAGE_TO_ALL"),
		    config.BackHome_Menu,
		)
		return ADMIN_MENU

	else:
		all_users_id = dbh.get_column_values("user", "userId")
		for uid in all_users_id:
			await context.bot.send_message(uid, update.message.text)
		await send_message(update, t("SENT"), config.BackHome_Menu)
		return ADMIN_MENU


async def tradingview(update: Update, context: ContextTypes.DEFAULT_TYPE, back_call = False):
	dbh.set_states(user_id(update), "tradingview", "automation")
	await send_message(update, t("TRADINGVIEW"))
	await send_message(
	    update,
	    t("TRADINGVIEWALERT", [user_id(update), dbh.get('user', {'userId': user_id(update)}, 'secret')]),
	    config.BackHome_Menu,
	)

	return await back(update, context)


async def telegram_group(update: Update, context: ContextTypes.DEFAULT_TYPE, back_call = False):
	dbh.set_states(user_id(update), "telegram_group", "automation")
	following = dbh.get_following(user_id(update), "group")

	if bool(match("^[-+]?[0-9]*\s#\s.*$", update.message.text)):
		if update.message.text in following:
			dbh.remove(
			    "user_group",
			    {
			        "userId": user_id(update),
			        "groupId": update.message.text.split(" # ")[0],
			    },
			)
			following = dbh.get_following(user_id(update), "group")
			await send_message(
			    update,
			    t("TELEGRAM_GROUP_REMOVED"),
			    createMenu(following, config.BackHome_Menu),
			)
		else:
			try:
				chatInfo = await context.bot.get_chat(int(update.message.text.split(" # ")[0]))
				chatType = chatInfo['type']
			except:
				chatType = None

			if chatType == ChatType.GROUP:
				dbh.add(
					"user_group",
					{
						"userId": user_id(update),
						"groupId": update.message.text.split(" # ")[0],
					},
				)
				following = dbh.get_following(user_id(update), "group")
				await send_message(
					update,
					t("TELEGRAM_GROUP_ADDED"),
					createMenu(following, config.BackHome_Menu),
				)
			else:
				following = dbh.get_following(user_id(update), "group")
				await send_message(
					update,
					t("TELEGRAM_GROUP_ADD_UNSUCCESSFUL"),
					createMenu(following, config.BackHome_Menu),
				)

		return TELEGRAMGROUP_MENU

	await send_message(
	    update,
	    t("TELEGRAM_GROUP"),
	    createMenu(following, config.BackHome_Menu),
	)
	return TELEGRAMGROUP_MENU


async def telegram_channel(update: Update, context: ContextTypes.DEFAULT_TYPE, back_call = False):
	dbh.set_states(user_id(update), "telegram_channel", "automation")
	following = dbh.get_following(user_id(update), "channel")

	if bool(match("^[-+]?[0-9]*\s#\s.*$", update.message.text)):
		if update.message.text in following:
			dbh.remove(
			    "user_channel",
			    {
			        "userId": user_id(update),
			        "channelId": update.message.text.split(" # ")[0],
			    },
			)
			following = dbh.get_following(user_id(update), "channel")
			await send_message(
			    update,
			    t("TELEGRAM_CHANNEL_REMOVED"),
			    createMenu(following, config.BackHome_Menu),
			)
		else:
			try:
				chatInfo = await context.bot.get_chat(int(update.message.text.split(" # ")[0]))
				chatType = chatInfo['type']
			except:
				chatType = None
			
			if chatType == ChatType.CHANNEL:
				dbh.add(
					"user_channel",
					{
						"userId": user_id(update),
						"channelId": update.message.text.split(" # ")[0],
					},
				)
				following = dbh.get_following(user_id(update), "channel")
				await send_message(
					update,
					t("TELEGRAM_CHANNEL_ADDED"),
					createMenu(following, config.BackHome_Menu),
				)

			else:
				following = dbh.get_following(user_id(update), "channel")
				await send_message(
					update,
					t("TELEGRAM_CHANNEL_ADD_UNSUCCESSFUL"),
					createMenu(following, config.BackHome_Menu),
				)

		return TELEGRAMCHANNEL_MENU

	await send_message(
	    update,
	    t("TELEGRAM_CHANNEL"),
	    createMenu(following, config.BackHome_Menu),
	)
	return TELEGRAMCHANNEL_MENU


async def api_management(update: Update, context: ContextTypes.DEFAULT_TYPE, back_call = False):
	dbh.set_states(user_id(update), "api_management", "management")
	await send_message(
	    update,
	    t("API_MANAGEMENT"),
	    config.Management_ApiManagement_Menu,
	)
	return APIMANAGEMENT_MENU


async def trading_constants(update: Update, context: ContextTypes.DEFAULT_TYPE, back_call = False):
	dbh.set_states(user_id(update), "trading_constants", "management")
	await send_message(
	    update,
	    t("TRADING_CONSTANTS"),
	    config.Management_TradingConstants_Menu,
	)
	return TRADINGCONSTANTS_MENU


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE, back_call = False):
	if not config.payments_configured():
		await send_message(update, "Subscription payments are disabled.")
		return ACCOUNTSTATUS_MENU
	dbh.set_states(user_id(update), "subscribe", "account_status")

	await send_message(
	    update,
	    t("SUBSCRIBE"),
	    config.AccountStatus_Subscribe_Menu,
	)
	return SUBSCRIBE_MENU


async def subscribe2(update: Update, context: ContextTypes.DEFAULT_TYPE, back_call = False):
	if not config.payments_configured():
		await send_message(update, "Subscription payments are disabled.")
		return ACCOUNTSTATUS_MENU
	dbh.set_states(user_id(update), "subscribe", "subscribe")

	if bool(match(f"^([0-9]|[a-z]){{{config.TRC20_TRANSACTION_ID_LENGTH}}}$", update.message.text)):

		transaction_accepted, amount = await check_transaction(
		    update.message.text,
		    dbh.get("user", {"userId": user_id(update)}, "payingSubscriptionPrice"),
		)
		if transaction_accepted:
			duration = dbh.get("user", {"userId": user_id(update)}, "payingSubscriptionDuration")
			if dbh.subscribe(user_id(update), duration, amount, update.message.text):
				await send_message(update, t("TRANSACTION_ACCEPTED"))
			else:
				await send_message(update, t("TRANSACTION_REJECTED"))
		else:
			await send_message(update, t("TRANSACTION_REJECTED"))

		return await back(update, context)

	price = -1
	duration = -1
	if update.message.text == config.MONTH1:
		price = config.MONTH1PRICEDOLLAR
		duration = 1 * 30
	elif update.message.text == config.MONTH3:
		price = config.MONTH3PRICEDOLLAR
		duration = 3 * 30
	elif update.message.text == config.MONTH6:
		price = config.MONTH6PRICEDOLLAR
		duration = 6 * 30
	elif update.message.text == config.MONTH12:
		price = config.MONTH12PRICEDOLLAR
		duration = 12 * 30

	price -= dbh.get("user", {"userId": user_id(update)}, "id") / (10**config.USDT_DECIMAL_POINTS)
	dbh.set("user", {"userId": user_id(update)}, {"payingSubscriptionPrice": price})
	dbh.set("user", {"userId": user_id(update)}, {"payingSubscriptionDuration": duration})

	await send_message(
	    update,
	    t("SUBSCRIBE2", [duration, price, config.USDT_TRC20_WALLET_ADDRESS]),
	    config.BackHome_Menu,
	)

	return SUBSCRIBE_MENU


async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE, back_call = False):
	if not config.referrals_configured():
		await send_message(update, "Referrals are disabled.")
		return ACCOUNTSTATUS_MENU
	gettingdata = dbh.get("user", {"userId": user_id(update)}, "gettingdata")

	if update.message.text == config.ENTER_REFERRAL_CODE or gettingdata == "referredBy":
		dbh.set_states(user_id(update), "referral", "referral")
		if gettingdata == "referredBy":
			if bool(match("^[0-9]+$", update.message.text)):
				if int(update.message.text) != int(user_id(update)):
					if dbh.get("user", {"userId": user_id(update)}, "referredBy") == None:
						if int(update.message.text) in dbh.get_column_values("user", "userId"):
							referrerUser = dbh.get_user(update.message.text)
							if referrerUser.referredBy != user_id(update):
								if dbh.get_user(user_id(update)).joinedOn >= referrerUser.joinedOn:
									if dbh.set("user", {"userId": user_id(update)}, {"referredBy": referrerUser}):
										dbh.subscribe(user_id(update), 5, referral=True)
										msg = t("REFERRAL_CODE_ACCEPTED")
										await send_message(update, msg, config.BackHome_Menu)
										return await back(update, context)
									else:
										msg = t("GET_DATA_UNSUCCESSFUL")
								else:
									msg = t("ENTER_REFERRAL_CODE_E1")
							else:
								msg = t("ENTER_REFERRAL_CODE_E2")
						else:
							msg = t("ENTER_REFERRAL_CODE_E3")
					else:
						msg = t("ENTER_REFERRAL_CODE_E4")
				else:
					msg = t("ENTER_REFERRAL_CODE_E5")
			else:
				msg = t("ENTER_REFERRAL_CODE_E6")
		else:
			if dbh.get("user", {"userId": user_id(update)}, "referredBy"):
				msg = t("PURCHASE_AMOUNT_REFER_CASHBACK", [
				    config.REFERRAL_CASHBACK_PERCENTAGE *
				    float(dbh.get("user", {"userId": user_id(update)}, "purchaseAmount")) / 100
				])
			else:
				msg = t("ENTER_REFERRAL_CODE")
				dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "referredBy"})

		await send_message(
		    update,
		    msg,
		    config.BackHome_Menu,
		)

	elif update.message.text == config.WITHDRAW_CASHBACK or gettingdata == "referralIncomeWithdraw":
		dbh.set_states(user_id(update), "referral", "referral")
		if gettingdata == "referralIncomeWithdraw":
			splittedMessage = split(r'[ #]+', update.message.text)
			if len(splittedMessage) == 2:
				if await check_float(splittedMessage[1]):
					if float(splittedMessage[1]) >= config.MIN_REFERRAL_WITHDRAW:
						if float(splittedMessage[1]) < float(
						    dbh.get("user", {"userId": user_id(update)}, "referralIncome")):
							if await check_wallet_address(splittedMessage[0]):
								if float(dbh.get("user", {"userId": user_id(update)},
								                 "referralIncome")) >= config.MIN_REFERRAL_BALANCE_WITHDRAW:
									condition1 = dbh.update_value("user", {"userId": user_id(update)}, "referralIncome",
									                              "-", float(splittedMessage[1]))
									condition2 = dbh.update_value("user", {"userId": user_id(update)},
									                              "referralIncomeWithdraw", "+",
									                              float(splittedMessage[1]))
									if condition1 and condition2:
										await context.bot.send_message(
										    config.OPERATIONS_CHAT_ID,
										    t("WITHDRAW_CASHBACK_REQUEST", [user_id(update), *splittedMessage]))
										msg = t("WITHDRAW_CASHBACK_ACCEPTED")
										await send_message(update, msg, config.BackHome_Menu)
										return await back(update, context)
									else:
										msg = t("GET_DATA_UNSUCCESSFUL")
								else:
									msg = t("WITHDRAW_CASHBACK_E1")
							else:
								msg = t("WITHDRAW_CASHBACK_E2")
						else:
							msg = t("WITHDRAW_CASHBACK_E3",
							        [dbh.get("user", {"userId": user_id(update)}, "referralIncome")])
					else:
						msg = t("WITHDRAW_CASHBACK_E4")
				else:
					msg = t("WITHDRAW_CASHBACK_E56")
			else:
				msg = t("WITHDRAW_CASHBACK_E56")
		else:
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "referralIncomeWithdraw"})
			msg = t("WITHDRAW_CASHBACK", [dbh.get("user", {"userId": user_id(update)}, "referralIncome")])

		await send_message(
		    update,
		    msg,
		    config.BackHome_Menu,
		)

	elif update.message.text == config.DISCOUNTED_SUB or gettingdata == "referralIncomeSubscribe":
		dbh.set_states(user_id(update), "referral", "referral")
		if gettingdata == "referralIncomeSubscribe":
			if await check_float(update.message.text):
				referralIncome = dbh.get("user", {"userId": user_id(update)}, "referralIncome")
				if float(update.message.text) <= referralIncome:
					if referralIncome >= config.MIN_REFERRAL_BALANCE_SUBSCRIBE:
						if float(update.message.text) >= config.MIN_REFERRAL_SUBSCRIBE:
							condition1 = dbh.update_value("user", {"userId": user_id(update)}, "referralIncome", "-",
							                              update.message.text)
							condition2 = dbh.update_value("user", {"userId": user_id(update)},
							                              "referralIncomeSubscribe", "+", update.message.text)
							if condition1 and condition2:
								duration = float(update.message.text) * 30 / (
								    (1 - config.REFERRAL_DISCOUNTED_SUB_PERCENTAGE / 100) * config.MONTH1PRICEDOLLAR)
								dbh.subscribe(user_id(update), duration, referral=True)
								msg = t("SUBSCRIBE_CASHBACK_ACCEPTED", [duration])
								await send_message(update, msg, config.BackHome_Menu)
								return await back(update, context)
							else:
								msg = t("GET_DATA_UNSUCCESSFUL")
						else:
							msg = t("SUBSCRIBE_CASHBACK_E1")
					else:
						msg = t("SUBSCRIBE_CASHBACK_E2")
				else:
					msg = t("SUBSCRIBE_CASHBACK_E3", [dbh.get("user", {"userId": user_id(update)}, "referralIncome")])
			else:
				msg = t("SUBSCRIBE_CASHBACK_E4")
		else:
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "referralIncomeSubscribe"})
			msg = t("DISCOUNTED_SUB", [dbh.get("user", {"userId": user_id(update)}, "referralIncome")])

		await send_message(
		    update,
		    msg,
		    config.BackHome_Menu,
		)

	else:
		dbh.set_states(user_id(update), "referral", "account_status")
		await send_message(
		    update,
		    t("REFERRAL",
		      [user_id(update), dbh.get("user", {"userId": user_id(update)}, "referralIncome")]),
		    config.AccountStatus_Referral_Menu,
		)

	return REFERRAL_MENU


async def setting_trading_constants(update: Update, context: ContextTypes.DEFAULT_TYPE, back_call = False):
	dbh.set_states(user_id(update), "setting_trading_constants", "trading_constants")

	if bool(match("^[+-]?([0-9]*[.])?[0-9]+$", update.message.text)):
		return await get_data(update, context)

	if update.message.text == config.VOLUME:
		dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "volume"})
	elif update.message.text == config.LEVERAGE:
		dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "leverage"})
	elif update.message.text == config.STOPLOSS:
		dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "stoploss"})
	elif update.message.text == config.TAKEPROFIT:
		dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "takeprofit"})
	else:
		print("Something Wrong")

	value = dbh.get(
	    "user",
	    {"userId": user_id(update)},
	    dbh.get("user", {"userId": user_id(update)}, "gettingdata"),
	)
	value = "Not Set" if value == None else value

	await send_message(
	    update,
	    f"{getattr(config, dbh.get('user', {'userId': user_id(update)}, 'gettingdata').upper())} = {value}",
	)
	await send_message(update, t("SETTING_TRADING_CONSTANTS"), config.Back_Menu)

	return TRADINGCONSTANTS_MENU


async def set_api(update: Update, context: ContextTypes.DEFAULT_TYPE, back_call = False):
	dbh.set_states(user_id(update), "set_api", "api_management")

	which_api = dbh.get("user", {"userId": user_id(update)}, "gettingdata")

	if which_api != None and which_api.count("api"):
		is_active_attribute = which_api.split("api")[0] + "active"
		is_active = dbh.get("user", {"userId": user_id(update)}, is_active_attribute)

	if bool(match("^.+#.+$", update.message.text)):
		dbh.set("user", {"userId": user_id(update)}, {is_active_attribute: True})
		return await get_data(update, context)

	if update.message.text == config.DEACTIVATE and is_active:
		dbh.set("user", {"userId": user_id(update)}, {is_active_attribute: False})
		await send_message(update, t("API_ACTIVATED"))
		return await refresh(update, context)

	if update.message.text == config.ACTIVATE and not is_active:
		dbh.set("user", {"userId": user_id(update)}, {is_active_attribute: True})
		await send_message(update, t("API_DEACTIVATED"))
		return await refresh(update, context)

	api_key = "Not Set"
	api_secret = "Not Set"

	if update.message.text == config.BINANCE:
		which_api = "binance_api"
	elif update.message.text == config.BYBIT:
		which_api = "bybit_api"
	elif update.message.text == config.COINEX:
		which_api = "coinex_api"
	elif update.message.text == config.BINGX:
		which_api = "bingx_api"

	if which_api == None:
		which_api = dbh.get("user", {"userId": user_id(update)}, "gettingdata")

	dbh.set("user", {"userId": user_id(update)}, {"gettingdata": which_api})
	api = dbh.get("user", {"userId": user_id(update)}, which_api)

	if api != None:
		api_key, api_secret = [i.strip() for i in api.split("#")]

	is_active_attribute = which_api.split("api")[0] + "active"
	is_active = dbh.get("user", {"userId": user_id(update)}, is_active_attribute)

	await send_message(
	    update,
	    t("API_INFO", [api_key, api_secret, is_active]),
	)

	await send_message(
	    update,
	    t("INPUT_API"),
	    createMenu(
	        [None if api_key == "Not Set" else config.DEACTIVATE if is_active else config.ACTIVATE],
	        config.BackHome_Menu,
	    ),
	)
	return APIMANAGEMENT_MENU


async def getting_statement(update: Update, context: ContextTypes.DEFAULT_TYPE, back_call = False):
	dbh.set_states(user_id(update), "getting_statement", "statement")

	if bool(match("^([a-zA-Z]*:)+[a-zA-Z]*$", update.message.text)):
		return await get_data(update, context)

	if update.message.text == config.CHANGESTATEMENTSYMBOLS:
		await send_message(
		    update,
		    t("CHANGE_STATEMENT_SYMBOLS", [dbh.get('user', {'userId': user_id(update)}, 'statementSymbols')]),
		    config.BackHome_Menu,
		)
		dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "statementSymbols"})
		return STATEMENT_MENU

	if update.message.text == config.GETSTATEMENT:
		await send_message(update, t("GETSTATEMENT"), config.BackHome_Menu)
		statement_data = await calculateStatementData(user_id(update), dbh)
		StatementPicture = await plotStatement(statement_data)

		await update.message.reply_photo(StatementPicture)

		return STATEMENT_MENU


async def get_data(update: Update, context: ContextTypes.DEFAULT_TYPE, silent=False):
	gettingdata = dbh.get("user", {"userId": user_id(update)}, "gettingdata")
	successful = True
	if not dbh.set(
	    "user",
	    {"userId": user_id(update)},
	    {gettingdata: update.message.text},
	):
		successful = False

	dbh.reset(user_id(update))
	if silent:
		return successful
	else:
		await send_message(update, t("GET_DATA_SUCCESSFUL" if successful else "GET_DATA_UNSUCCESSFUL"))
	return await back(update, context)


async def remove_until_message(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id=None):
	if message_id:
		try:
			last_message_id = dbh.get("user", {"userId": user_id(update)}, "numMessages")
			while last_message_id != message_id:
				await context.bot.deleteMessage(update.message.chat_id, last_message_id)
				last_message_id -= 1
		except Exception as e:
			# print("EXCEPTION remove_until_message", e)
			pass
	else:
		print("remove_until_message Message ID None")


async def check_pair(data, userId):
	pairAdjusted = data.upper()
	if not bool(match("^[A-Za-z0-9]+\/[A-Za-z0-9]+$", pairAdjusted)):
		return False, 1, pairAdjusted

	valid, error = True, 0

	orderInfo = dbh.order_info(userId)
	tradeExchange = orderInfo["tradeExchange"]
	tradeMarket = orderInfo["tradeMarket"]

	if not bool(
	    dbh.get(
	        "pair",
	        {
	            "exchange": tradeExchange,
	            "symbol": pairAdjusted,
	            "perp": True if tradeMarket == config.FUTURES else False,
	        },
	        "symbol",
	    )):
		valid, error = False, 2

	if not bool(
	    dbh.get(
	        "pair",
	        {
	            "exchange": tradeExchange,
	            "symbol": pairAdjusted,
	            "perp": True if tradeMarket == config.FUTURES else False,
	        },
	        "available",
	    )):

		valid, error = False, 3

	return valid, error, pairAdjusted


async def check_price(data, userId):
	if data == config.MARKET:
		return True, 0, config.MARKET, config.MARKET, -1, -1, ''
	if not bool(match("^(([0-9]+[.]?[0-9]*)|([0-9]*[.]?[0-9]+))$", data)):
		return False, 1, -1, -1, -1, -1, ''

	price = float(data)
	valid, error = True, 0

	orderInfo = dbh.order_info(userId)
	tradeExchange = orderInfo["tradeExchange"]
	tradeMarket = orderInfo["tradeMarket"]
	tradePair = orderInfo["tradePair"]
	tradeSide = orderInfo["tradeSide"]
	minPrice, maxPrice, priceTickSize = dbh.get("pair", {
	    "exchange": tradeExchange,
	    "symbol": tradePair,
	    "perp": True if tradeMarket == config.FUTURES else False,
	}, ['minPrice', 'maxPrice', 'priceTickSize'])
	priceAdjusted = round_to_multiple(price, priceTickSize) if priceTickSize != -1 else price
	asset, currency = orderInfo["tradePair"].split('/')
	volumeAsset   = currency if orderInfo["tradeSide"] == config.BUY or orderInfo["tradeMarket"] == config.FUTURES else asset

	client = exchangeClient(tradeExchange, *get_api_credentials(userId, tradeExchange, dbh), dbh).client
	currentPrice = client.get_price(tradePair, True if tradeMarket == config.FUTURES else False)

	if tradeSide == config.BUY and price > currentPrice:
		valid, error = False, 2
	elif tradeSide == config.SELL and price < currentPrice:
		valid, error = False, 3

	if minPrice != -1:
		if price < minPrice:
			valid, error = False, 4
	if maxPrice != -1:
		if price > maxPrice:
			valid, error = False, 5

	return valid, error, currentPrice, priceAdjusted, minPrice, maxPrice, volumeAsset


async def check_volume(data, userId):
	if not bool(match("^(([0-9]+[.]?[0-9]*)|([0-9]*[.]?[0-9]+))[%]?$", data)):
		return False, 1, -1, -1, '', -1, -1, -1, -1, -1

	valid, error  = True, 0

	orderInfo     = dbh.order_info(userId)
	tradeExchange = orderInfo["tradeExchange"]
	tradeMarket   = orderInfo["tradeMarket"]
	tradePair     = orderInfo["tradePair"]
	tradeSide     = orderInfo["tradeSide"]
	tradeLeverage = orderInfo["tradeLeverage"]

	asset, currency = orderInfo["tradePair"].split('/')
	volumeAsset = currency if orderInfo["tradeSide"] == config.BUY or orderInfo["tradeMarket"] == config.FUTURES else asset

	minOrderQty, maxOrderQty, assetTickSize, minOrderAmt, maxOrderAmt, currencyTickSize = dbh.get(
	    "pair", {
	        "exchange": tradeExchange,
	        "symbol": tradePair,
	        "perp": True if tradeMarket == config.FUTURES else False,
	    }, ['minOrderQty', 'maxOrderQty', 'assetTickSize', 'minOrderAmt', 'maxOrderAmt', 'currencyTickSize'])

	client = exchangeClient(tradeExchange, *get_api_credentials(userId, tradeExchange, dbh), dbh).client

	try:
		balance = client.get_balance(coins=[volumeAsset], perp=True if tradeMarket == config.FUTURES else False)['balance']
	except:
		balance = 0

	if data[-1] == '%':
		volumePercentage = float(data[:-1])
		if volumePercentage < 0 or volumePercentage > 100:
			valid, error = False, 2
		volume = balance * (volumePercentage / 100) * (tradeLeverage if tradeMarket == config.FUTURES else 1)
		unleveragedVolume = volume / tradeLeverage if tradeMarket == config.FUTURES else volume

	else:
		volume = float(data)
		unleveragedVolume = volume / tradeLeverage if tradeMarket == config.FUTURES else volume
		if volume <= 0:
			valid, error = False, 3
		if unleveragedVolume > balance:
			valid, error = False, 4

	# volume = volume * tradeLeverage if tradeMarket == config.FUTURES else volume
	
	if tradeSide == config.BUY or tradeMarket == config.FUTURES:
		volumeAdjusted = round_to_multiple(volume, currencyTickSize)
		if maxOrderAmt not in [-1, -2] and volume > maxOrderAmt:
			valid, error = False, 7
		elif minOrderAmt not in [-1, -2] and volume < minOrderAmt:
			valid, error = False, 8
	
	elif tradeSide == config.SELL:
		volumeAdjusted = round_to_multiple(volume, assetTickSize)
		if maxOrderQty != -1 and volume > maxOrderQty:
			valid, error = False, 5
		elif minOrderQty != -1 and volume < minOrderQty:
			valid, error = False, 6
	return valid, error, volumeAdjusted, balance, volumeAsset, maxOrderQty, minOrderQty, maxOrderAmt, minOrderAmt, unleveragedVolume

	
async def check_volume_entry_exit(data, userId, entry_sl_tp=0, isLast=False):
	if isLast and entry_sl_tp==0 and data != config.REST:
		return False, 11, -1, -1, '', -1, -1, -1, -1, -1
	if not bool(match("^(([0-9]+[.]?[0-9]*)|([0-9]*[.]?[0-9]+))[%]?$", data)) and not(data == config.REST and isLast):
		return False, 1, -1, -1, '', -1, -1, -1, -1, -1

	valid, error    = True, 0

	orderInfo       = dbh.order_info(userId)
	tradeExchange   = orderInfo["tradeExchange"]
	tradeMarket     = orderInfo["tradeMarket"]
	tradePair       = orderInfo["tradePair"]
	tradeSide       = orderInfo["tradeSide"]
	tradeVolume     = orderInfo["tradeVolume"]
	asset, currency = orderInfo["tradePair"].split('/')
	volumeAsset     = currency if orderInfo["tradeSide"] == config.BUY or orderInfo["tradeMarket"] == config.FUTURES else asset
	
	client              = exchangeClient(tradeExchange, *get_api_credentials(userId, tradeExchange, dbh), dbh).client
	if   entry_sl_tp == 0:
		used            = orderInfo["tradeEntryVol"]
		tradeEntry      = orderInfo["tradeEntry"].split("#")[-1]
		tradeEntry      = config.MARKET if tradeEntry == config.MARKET else float(tradeEntry)
		priceInAction   = tradeEntry if tradeEntry != config.MARKET else client.get_price(tradePair, True if tradeMarket == config.FUTURES else False)
	elif entry_sl_tp == 1:
		used            = orderInfo["tradeStoplossVol"]
		tradeStoploss   = orderInfo["tradeStoploss"].split("#")[-1]
		tradeStoploss   = config.MARKET if tradeStoploss == config.MARKET else float(tradeStoploss)
		priceInAction   = tradeStoploss if tradeStoploss != config.MARKET else client.get_price(tradePair, True if tradeMarket == config.FUTURES else False)
	elif entry_sl_tp == 2:
		used            = orderInfo["tradeTakeprofitVol"]
		tradeTakeprofit = orderInfo["tradeTakeprofit"].split("#")[-1]
		tradeTakeprofit = config.MARKET if tradeTakeprofit == config.MARKET else float(tradeTakeprofit)
		priceInAction   = tradeTakeprofit if tradeTakeprofit != config.MARKET else client.get_price(tradePair, True if tradeMarket == config.FUTURES else False)

	minOrderQty, maxOrderQty, assetTickSize, minOrderAmt, maxOrderAmt, currencyTickSize = dbh.get(
	    "pair", {
	        "exchange": tradeExchange,
	        "symbol": tradePair,
	        "perp": True if tradeMarket == config.FUTURES else False,
	    }, ['minOrderQty', 'maxOrderQty', 'assetTickSize', 'minOrderAmt', 'maxOrderAmt', 'currencyTickSize'])
	

	if data == config.REST:
		if used is not None:
			volume           = tradeVolume - sum([float(i.split("|")[0]) for i in used.split("#")])
			volumePercentage = 100 - sum([float(i.split("|")[1]) for i in used.split("#")])
		else:
			volume, volumePercentage = tradeVolume, 100

	elif data[-1] == '%':
		volumePercentage = float(format(float(data[:-1]), '.2f'))
		if volumePercentage <= 0 or volumePercentage > 100:
			valid, error = False, 2
		volume = volumePercentage * tradeVolume / 100

	else:
		if entry_sl_tp != 0:
			valid, error = False, 3
		volume = float(data)
		if volume <= 0:
			valid, error = False, 4
		if volume > tradeVolume:
			valid, error = False, 5
		volumePercentage = volume * 100 / tradeVolume

	volumeAdjusted = round_to_multiple(volume, currencyTickSize if orderInfo["tradeSide"] == config.BUY or orderInfo["tradeMarket"] == config.FUTURES else assetTickSize)

	if entry_sl_tp == 0:
		if used is not None:
			rest = tradeVolume - sum([float(i.split("|")[0]) for i in used.split("#")])
			if volume > rest:
				valid, error = False, 6
		else:
			rest = tradeVolume
	else:
		if used is not None:
			rest = 100 - sum([float(i.split("|")[1]) for i in used.split("#")])
			if volumePercentage > rest:
				valid, error = False, 6
		else:
			rest = 100

	if valid:
		if tradeSide == config.BUY or tradeMarket == config.FUTURES:
			if minOrderAmt == -2 or maxOrderAmt == -2:
				if minOrderAmt == -2:
					minOrderAmt = priceInAction * minOrderQty
				if maxOrderAmt == -2:
					maxOrderAmt = priceInAction * maxOrderQty

			if maxOrderAmt != -1 and volume > maxOrderAmt:
				valid, error = False, 7
			elif minOrderAmt != -1 and volume < minOrderAmt:
				valid, error = False, 8
		
		elif tradeSide == config.SELL:
			if maxOrderQty != -1 and volume > maxOrderQty:
				valid, error = False, 9
			elif minOrderQty != -1 and volume < minOrderQty:
				valid, error = False, 10

	return valid, error, volumePercentage, volumeAdjusted, volumeAsset, rest, maxOrderQty, minOrderQty, maxOrderAmt, minOrderAmt


async def check_tp_sl(data, gettingdata, userId):
	if data in [config.NO_SL, config.NO_TP]:
		return True, -1, -1, -1, ''
	if not bool(match("^(([0-9]+[.]?[0-9]*)|([0-9]*[.]?[0-9]+))[%]?$", data)):
		return False, 1, -1, -1, ''

	valid, error = True, 0

	orderInfo = dbh.order_info(userId)
	tradeExchange = orderInfo['tradeExchange']
	tradeMarket = orderInfo['tradeMarket']
	tradePair = orderInfo['tradePair']
	tradeSide = orderInfo['tradeSide']
	tradeEntry = orderInfo["tradeEntry"].split("#")
	asset, currency = orderInfo["tradePair"].split('/')
	volumeAsset   = currency if orderInfo["tradeSide"] == config.BUY or orderInfo["tradeMarket"] == config.FUTURES else asset
	if config.MARKET in tradeEntry:
		client = exchangeClient(tradeExchange, *get_api_credentials(userId, tradeExchange, dbh), dbh).client
		currentPrice = client.get_price(tradePair, True if tradeMarket == config.FUTURES else False)
		tradeEntry = [currentPrice if i == config.MARKET else i for i in tradeEntry]
	tradeEntry = [float(i) for i in tradeEntry]

	if data[-1] == '%':
		data = float(data[:-1])
		if gettingdata == "tradeStoploss":
			if data > 100 or data < 0:
				valid, error = False, 2
		if gettingdata == "tradeTakeprofit":
			if data < 0:
				valid, error = False, 3
	else:
		data = float(data)
		if tradeSide == config.BUY:
			if gettingdata == "tradeStoploss" and data > min(tradeEntry):
				valid, error = False, 4
			elif gettingdata == "tradeTakeprofit" and data < max(tradeEntry):
				valid, error = False, 5
		elif tradeSide == config.SELL:
			if gettingdata == "tradeStoploss" and data < max(tradeEntry):
				valid, error = False, 6
			elif gettingdata == "tradeTakeprofit" and data > min(tradeEntry):
				valid, error = False, 7

	return valid, error, min(tradeEntry), max(tradeEntry), volumeAsset


async def check_leverage(data, userId):
	if not bool(match("^(([0-9]+[.]?[0-9]*)|([0-9]*[.]?[0-9]+))$", data)):
		return False, 1, -1, [-1, -1, [-1]]

	valid, error = True, 0
	leverage = float(data)

	orderInfo = dbh.order_info(userId)
	tradeExchange = orderInfo["tradeExchange"]
	tradeMarket = orderInfo["tradeMarket"]
	tradePair = orderInfo["tradePair"]

	maxLeverage, stepLeverage, suggestedLeverage = dbh.get(
	    "pair",
	    {
	        "exchange": tradeExchange,
	        "symbol": tradePair,
	        "perp": True if tradeMarket == config.FUTURES else False
	    },
	    ["maxLeverage", "stepLeverage", "suggestedLeverage"],
	)
	leverageAdjusted = round_to_multiple(leverage, stepLeverage) if stepLeverage != -1 else leverage

	if tradeExchange == config.COINEX:
		if leverageAdjusted not in parse_stored_list(suggestedLeverage):
			valid, error = False, 2

	if leverageAdjusted < 1:
		valid, error = False, 3
	elif leverageAdjusted > maxLeverage:
		valid, error = False, 4

	return valid, error, leverageAdjusted, [maxLeverage, stepLeverage, suggestedLeverage]


async def check_num_entry_exit(data, min=0, max=config.MAX_ENTRY_EXIT):
	if data in [config.NO_SL, config.NO_TP]:
		return True, 0
	if not data.isdecimal():
		return False, 1
	num = int(data)
	if num < min:
		return False, 2
	if num > max:
		return False, 3
	return True, 0


async def check_percentage(data, min=0, max=100):
	if not bool(match("^(([0-9]+[.]?[0-9]*)|([0-9]*[.]?[0-9]+))[%]$", data)):
		return False, 1, data
	if float(data[:-1]) <= min:
		return False, 2, data
	elif float(data[:-1]) > max:
		return False, 3, data
	return True, 0, data


async def check_percentage_volume_entry_exit(data, userId, entry_sl_tp=0, isLast=False):
	if isLast and entry_sl_tp==0 and data != config.REST:
		return False, 1, -1, -1, -1
		
	if not bool(match("^(([0-9]+[.]?[0-9]*)|([0-9]*[.]?[0-9]+))[%]$", data)) and not(data == config.REST and isLast):
		return False, 2, -1, -1, -1
	
	valid, error    = True, 0

	orderInfo       = dbh.order_info(userId)
	asset, currency = orderInfo["tradePair"].split('/')
	volumeAsset     = currency if orderInfo["tradeSide"] == config.BUY or orderInfo["tradeMarket"] == config.FUTURES else asset

	if   entry_sl_tp == 0:
		used = orderInfo["tradeEntryVol"]
	elif entry_sl_tp == 1:
		used = orderInfo["tradeStoplossVol"]
	elif entry_sl_tp == 2:
		used = orderInfo["tradeTakeprofitVol"]

	if data == config.REST:
		if used is not None:
			volumePercentage = 100 - sum([float(i.split("|")[1]) for i in used.split("#")])
		else:
			volumePercentage = 100
	elif data[-1] == '%':
		volumePercentage = float(format(float(data[:-1]), '.2f'))
		if volumePercentage <= 0 or volumePercentage > 100:
			valid, error = False, 3

	if used is not None:
		rest = 100 - sum([float(i.split("|")[1]) for i in used.split("#")])
		if volumePercentage > rest:
			valid, error = False, 4
	else:
		rest = 100

	return valid, error, volumePercentage, rest, volumeAsset
	

async def send_signal_directly(update: Update, context: ContextTypes.DEFAULT_TYPE, back_call = False):
	gettingdata = dbh.get("user", {"userId": user_id(update)}, "gettingdata")

	order_message_id = dbh.get("user", {"userId": user_id(update)}, "specificMessage")
	orderInfo = dbh.order_info(user_id(update))

	if not (update.message.text == config.SEND_SIGNAL_DIRECTLY or update.message.text == "/direct"):
		await remove_until_message(update, context, order_message_id)

	if update.message.text == config.SEND_SIGNAL_DIRECTLY or update.message.text == "/direct":
		dbh.set_states(user_id(update), "send_signal_directly", "automation")
		dbh.reset(user_id(update))

		if dbh.exchanges_set(user_id(update)):
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeExchange"})
			gettingdata = dbh.get("user", {"userId": user_id(update)}, "gettingdata")

			msg = await send_message(update, createOrderInfo(dbh.order_info(user_id(update)), gettingdata))
			dbh.set("user", {"userId": user_id(update)}, {"specificMessage": msg.message_id})

			await send_message(
			    update,
			    t("INPUT_EXCHANGE"),
			    createMenu(dbh.exchanges_set(user_id(update)), config.BackHome_Menu),
			)

		else:
			await send_message(
			    update,
			    t("NO_EXCHANGE"),
			    config.BackHome_Menu,
			)

	elif gettingdata == "tradeExchange" or (back_call and gettingdata == "tradeMarket"):
		dbh.set_states(user_id(update), "send_signal_directly", "automation")

		if back_call:
			dbh.set("user", {"userId": user_id(update)}, {"tradeExchange": None})
			dbh.set("user", {"userId": user_id(update)}, {"tradeMarket": None})
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeExchange"})

		if update.message.text in config.EXCHANGE_NAMES:
			dbh.set(
			    "user",
			    {"userId": user_id(update)},
			    {gettingdata: update.message.text},
			)

			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeMarket"})
			await send_message(
			    update,
			    t("INPUT_MARKET"),
			    createMenu(config.MARKET_TYPES, config.BackHome_Menu),
			)
			dbh.set_states(user_id(update), "send_signal_directly", "send_signal_directly")

		else:
			await send_message(
			    update,
			    t("INPUT_EXCHANGE"),
			    createMenu(dbh.exchanges_set(user_id(update)), config.BackHome_Menu),
			)

	elif gettingdata == "tradeMarket" or (back_call and gettingdata == "tradePair"):
		dbh.set_states(user_id(update), "send_signal_directly", "send_signal_directly")
		if back_call:
			dbh.set("user", {"userId": user_id(update)}, {"tradeMarket": None})
			dbh.set("user", {"userId": user_id(update)}, {"tradePair": None})
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeMarket"})
			
		if update.message.text in config.MARKET_TYPES:
			dbh.set(
			    "user",
			    {"userId": user_id(update)},
			    {gettingdata: update.message.text},
			)
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradePair"})
			await send_message(
			    update,
			    t("INPUT_PAIR"),
			    createMenu(
			        createMenuFromList(
			            parse_stored_list(
			                dbh.get(
			                    "exchange",
			                    {"name": dbh.get("user", {"userId": user_id(update)}, "tradeExchange")},
			                    "highVolumePairsPerp" if dbh.get("user", {"userId": user_id(update)}, "tradeMarket")
			                    == config.FUTURES else "highVolumePairsSpot",
			                ))),
			        config.BackHome_Menu,
			    ),
			)

		else:
			await send_message(
			    update,
			    t("INPUT_MARKET"),
			    createMenu(config.MARKET_TYPES, config.BackHome_Menu),
			)

	elif gettingdata == "tradePair" or (back_call and gettingdata == "tradeSide"):
		dbh.set_states(user_id(update), "send_signal_directly", "send_signal_directly")
		if back_call:
			dbh.set("user", {"userId": user_id(update)}, {"tradePair": None})
			dbh.set("user", {"userId": user_id(update)}, {"tradeSide": None})
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradePair"})
			valid, error = False, 1
		else:
			valid, error, pairAdjusted = await check_pair(update.message.text, user_id(update))

		if valid:
			dbh.set(
			    "user",
			    {"userId": user_id(update)},
			    {gettingdata: pairAdjusted},
			)
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeSide"})
			await send_message(
			    update,
			    t("INPUT_SIDE"),
			    createMenu(config.TRADE_SIDES, config.BackHome_Menu),
			)

		else:
			if error == 1:
				msg = t("INPUT_PAIR")
			elif error == 2:
				msg = t("INPUT_PAIR_E2")
			elif error == 3:
				msg = t("INPUT_PAIR_E3")

			await send_message(
			    update,
			    msg,
			    createMenu(
			        createMenuFromList(
			            parse_stored_list(
			                dbh.get(
			                    "exchange",
			                    {"name": dbh.get("user", {"userId": user_id(update)}, "tradeExchange")},
			                    "highVolumePairsPerp" if dbh.get("user", {"userId": user_id(update)}, "tradeMarket")
			                    == config.FUTURES else "highVolumePairsSpot",
			                ))),
			        config.BackHome_Menu,
			    ),
			)

	elif gettingdata == "tradeSide" or (back_call and gettingdata == "tradeLeverage") or (back_call and gettingdata == "tradeVolume" and orderInfo["tradeMarket"] != config.FUTURES):
		dbh.set_states(user_id(update), "send_signal_directly", "send_signal_directly")
		if back_call:
			dbh.set("user", {"userId": user_id(update)}, {"tradeSide": None})
			dbh.set("user", {"userId": user_id(update)}, {"tradeLeverage": None})
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeSide"})

		if update.message.text in config.TRADE_SIDES:
			dbh.set(
			    "user",
			    {"userId": user_id(update)},
			    {gettingdata: update.message.text},
			)

			if dbh.get("user", {"userId": user_id(update)}, "tradeMarket") == config.FUTURES:
				dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeLeverage"})
				await send_message(
				    update,
				    t("INPUT_LEVERAGE"),
				    createMenu(
				        createMenuFromList(
				            parse_stored_list(
				                dbh.get(
				                    "pair",
				                    {
				                        "exchange": dbh.get("user", {"userId": user_id(update)}, "tradeExchange"),
				                        "symbol": dbh.get("user", {"userId": user_id(update)}, "tradePair"),
				                        "perp": True,
				                    },
				                    "suggestedLeverage",
				                ))),
				        config.BackHome_Menu,
				    ),
				)
			elif dbh.get("user", {"userId": user_id(update)}, "tradeMarket") == config.SPOT:
				dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeVolume"})
				await send_message(update, t("INPUT_VOLUME"), createMenu(config.SUGGESTED_VOLUME_PERCENTAGE, config.BackHome_Menu))

		else:
			await send_message(
			    update,
			    t("INPUT_SIDE"),
			    createMenu(config.TRADE_SIDES, config.BackHome_Menu),
			)

	elif gettingdata == "tradeLeverage" or (back_call and gettingdata == "tradeVolume" and orderInfo["tradeMarket"] == config.FUTURES):
		dbh.set_states(user_id(update), "send_signal_directly", "send_signal_directly")
		if back_call:
			dbh.set("user", {"userId": user_id(update)}, {"tradeLeverage": None})
			dbh.set("user", {"userId": user_id(update)}, {"tradeVolume": None})
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeLeverage"})
			valid, error = False, 1
		else:
			valid, error, leverageAdjusted, leverage_info = await check_leverage(update.message.text, user_id(update))

		if valid:
			dbh.set(
			    "user",
			    {"userId": user_id(update)},
			    {gettingdata: leverageAdjusted},
			)
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeVolume"})
			await send_message(update, t("INPUT_VOLUME"), createMenu(config.SUGGESTED_VOLUME_PERCENTAGE, config.BackHome_Menu))

		else:
			if error == 1:
				msg = t("INPUT_LEVERAGE")
			elif error == 2:
				msg = t("INPUT_LEVERAGE_E2", [str(leverage_info[2]).replace("]", "").replace("[", "").replace("'", "")])
			elif error == 3:
				msg = t("INPUT_LEVERAGE_E3")
			elif error == 4:
				msg = t("INPUT_LEVERAGE_E4", [leverage_info[0]])


			await send_message(
			    update,
			    msg,
			    createMenu(
			        createMenuFromList(
			            parse_stored_list(
			                dbh.get(
			                    "pair",
			                    {
			                        "exchange": dbh.get("user", {"userId": user_id(update)}, "tradeExchange"),
			                        "symbol": dbh.get("user", {"userId": user_id(update)}, "tradePair"),
			                        "perp": True,
			                    },
			                    "suggestedLeverage",
			                ))),
			        config.BackHome_Menu,
			    ),
			)

	elif gettingdata == "tradeVolume" or (back_call and gettingdata == "tradeEntryNum"):
		dbh.set_states(user_id(update), "send_signal_directly", "send_signal_directly")
		if back_call:
			dbh.set("user", {"userId": user_id(update)}, {"tradeVolume": None})
			dbh.set("user", {"userId": user_id(update)}, {"tradeEntryNum": 0})
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeVolume"})
			valid, error = False, 1
		else:
			valid, error, volumeAdjusted, balance, volumeAsset, maxOrderQty, minOrderQty, maxOrderAmt, minOrderAmt, unleveragedVolume = await check_volume(update.message.text, user_id(update))
		
		if valid:
			dbh.set(
			    "user",
			    {"userId": user_id(update)},
			    {gettingdata: volumeAdjusted},
			)
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeEntryNum"})
			await send_message(update, t("INPUT_ENTRY_NUM"), createMenu([1, 2, 3], config.BackHome_Menu))
		
		else:
			if error == 1:
				msg = t("INPUT_VOLUME")
			elif error == 2:
				msg = t("INPUT_VOLUME_E2")
			elif error == 3:
				msg = t("INPUT_VOLUME_E3")
			elif error == 4:
				msg = t("INPUT_VOLUME_E4", [unleveragedVolume, balance, volumeAsset])
			elif error == 5:
				msg = t("INPUT_VOLUME_E5", [maxOrderQty])
			elif error == 6:
				msg = t("INPUT_VOLUME_E6", [minOrderQty])
			elif error == 7:
				msg = t("INPUT_VOLUME_E7", [maxOrderAmt])
			elif error == 8:
				msg = t("INPUT_VOLUME_E8", [minOrderAmt])
			if error in [5, 6, 7, 8] and update.message.text[-1] == '%':
				msg += '\n' + t("INPUT_VOLUME_E5678", [volumeAdjusted, volumeAsset])
			await send_message(update, msg, createMenu(config.SUGGESTED_VOLUME_PERCENTAGE, config.BackHome_Menu))


	elif gettingdata == "tradeEntryNum" or (back_call and gettingdata in ["tradeEntry", "tradeEntryVol", "tradeStoplossNum"]):
		dbh.set_states(user_id(update), "send_signal_directly", "send_signal_directly")
		if back_call:
			dbh.set("user", {"userId": user_id(update)}, {"tradeEntryNum": 0})
			dbh.set("user", {"userId": user_id(update)}, {"tradeEntry": None})
			dbh.set("user", {"userId": user_id(update)}, {"tradeEntryVol": None})
			dbh.set("user", {"userId": user_id(update)}, {"tradeStoplossNum": 0})
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeEntryNum"})
			valid, error = False, 1
		else:
			valid, error = await check_num_entry_exit(update.message.text, min=1)

		if valid:
			dbh.set(
			    "user",
			    {"userId": user_id(update)},
			    {gettingdata: update.message.text},
			)
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeEntry"})
			await send_message(update, t("INPUT_PRICE"), createMenu(config.MARKET, config.BackHome_Menu))

		else:
			if error == 1:
				msg = t("INPUT_ENTRY_NUM")
			elif error == 2:
				msg = t("INPUT_ENTRY_SL_TP_NUM_E2", [0])
			elif error == 3:
				msg = t("INPUT_ENTRY_SL_TP_NUM_E3", [10])
			await send_message(update, msg, createMenu([1, 2, 3], config.BackHome_Menu))

	elif gettingdata == "tradeEntry":
		dbh.set_states(user_id(update), "send_signal_directly", "send_signal_directly")
		valid, error, currentPrice, priceAdjusted, minPrice, maxPrice, volumeAsset = await check_price(
		    update.message.text, user_id(update))

		if valid:
			dbh.update_value(
			    "user",
			    {"userId": user_id(update)},
			    gettingdata,
			    'concat',
			    priceAdjusted,
			)
			
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeEntryVol"})
			numEntries = int(dbh.get("user", {"userId": user_id(update)}, "tradeEntryNum"))
			numEntered = len(dbh.get("user", {"userId": user_id(update)}, "tradeEntry").split("#"))
			isLast = bool(numEntries == numEntered)
			menu = createMenu(config.REST if isLast else config.SUGGESTED_VOLUME_PERCENTAGE, config.BackHome_Menu)
			msg = t("INPUT_LAST_ENTRY_VOLUME") if isLast else t("INPUT_ENTRY_VOLUME")
			await send_message(update, msg,menu)

		else:
			if error == 1:
				msg = t("INPUT_PRICE")
			elif error == 2:
				msg = t("INPUT_PRICE_E2")
			elif error == 3:
				msg = t("INPUT_PRICE_E3")
			elif error == 4:
				msg = t("INPUT_PRICE_E4", [minPrice])
			elif error == 5:
				msg = t("INPUT_PRICE_E5", [maxPrice])

			if error in [2, 3]:
				msg += '\n'
				msg += t("INPUT_PRICE_E23", [currentPrice, volumeAsset])
			await send_message(update, msg, createMenu(config.MARKET, config.BackHome_Menu))

	elif gettingdata == "tradeEntryVol":
		dbh.set_states(user_id(update), "send_signal_directly", "send_signal_directly")
		numEntries = int(dbh.get("user", {"userId": user_id(update)}, "tradeEntryNum"))
		numEntered = len(dbh.get("user", {"userId": user_id(update)}, "tradeEntry").split("#"))
		isLast = bool(numEntries == numEntered)
		valid, error, volumePercentage, volumeAdjusted, volumeAsset, rest, maxOrderQty, minOrderQty, maxOrderAmt, minOrderAmt = await check_volume_entry_exit(update.message.text, user_id(update), entry_sl_tp=0, isLast=isLast)

		if valid:
			dbh.update_value(
			    "user",
			    {"userId": user_id(update)},
			    gettingdata,
			    'concat',
			    str(volumeAdjusted)+"|"+str(volumePercentage),
			)

			if isLast:
				dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeStoplossNum"})
				await send_message(update, t("INPUT_NUM_SL"), createMenu([config.NO_SL, 1, 2, 3], config.BackHome_Menu))
			else:
				dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeEntry"})
				await send_message(update, t("INPUT_PRICE"), createMenu(config.MARKET, config.BackHome_Menu))

		else:
			if error == 1:
				msg = t("INPUT_ENTRY_VOLUME")
			elif error == 2:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E2")
			elif error == 3:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E3")
			elif error == 4:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E4")
			elif error == 5:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E5")
			elif error == 6:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E6", [rest])
			elif error == 7:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E7", [maxOrderAmt])
			elif error == 8:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E8", [minOrderAmt])
			elif error == 9:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E9", [maxOrderQty])
			elif error == 10:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E10", [minOrderQty])
			elif error == 11:
				msg = t("INPUT_LAST_ENTRY_VOLUME")
			if error in [7, 8, 9, 10] and update.message.text[-1] == '%':
				msg += '\n' + t("INPUT_VOLUME_E5678", [volumeAdjusted, volumeAsset])
			
			menu = createMenu(config.REST if isLast else config.SUGGESTED_VOLUME_PERCENTAGE, config.BackHome_Menu)
			await send_message(update, msg, menu)

	elif gettingdata == "tradeStoplossNum" or (back_call and gettingdata in ["tradeStoploss", "tradeStoplossVol", "tradeTakeprofitNum"]):
		dbh.set_states(user_id(update), "send_signal_directly", "send_signal_directly")
		if back_call:
			dbh.set("user", {"userId": user_id(update)}, {"tradeStoplossNum": 0})
			dbh.set("user", {"userId": user_id(update)}, {"tradeStoploss": None})
			dbh.set("user", {"userId": user_id(update)}, {"tradeStoplossVol": None})
			dbh.set("user", {"userId": user_id(update)}, {"tradeTakeprofitNum": 0})
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeStoplossNum"})
			valid, error = False, 1
		else:
			valid, error = await check_num_entry_exit(update.message.text)

		if valid:
			dbh.set(
			    "user",
			    {"userId": user_id(update)},
			    {gettingdata: update.message.text},
			)
			if update.message.text in [0, config.NO_SL]:
				dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeTakeprofitNum"})
				await send_message(update, t("INPUT_NUM_TP"), createMenu([config.NO_TP, 1, 2, 3], config.BackHome_Menu))
			else:
				dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeStoploss"})
				await send_message(update, t("INPUT_SL"), config.BackHome_Menu)

		else:
			if error == 1:
				msg = t("INPUT_NUM_SL")
			elif error == 2:
				msg = t("INPUT_ENTRY_SL_TP_NUM_E2", [0])
			elif error == 3:
				msg = t("INPUT_ENTRY_SL_TP_NUM_E3", [10])
			await send_message(update, msg, createMenu([config.NO_SL, 1, 2, 3], config.BackHome_Menu))

	elif gettingdata == "tradeStoploss":
		dbh.set_states(user_id(update), "send_signal_directly", "send_signal_directly")
		valid, error, minTradeEntry, maxTradeEntry, volumeAsset = await check_tp_sl(update.message.text, gettingdata, user_id(update))

		if valid:
			dbh.update_value(
			    "user",
			    {"userId": user_id(update)},
			    gettingdata,
			    'concat',
			    update.message.text,
			)
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeStoplossVol"})
			numExits   = int(dbh.get("user", {"userId": user_id(update)}, "tradeStoplossNum"))
			numEntered = len(dbh.get("user", {"userId": user_id(update)}, "tradeStoploss").split("#"))
			isLast = bool(numExits == numEntered)
			menu = createMenu([config.REST]+config.SUGGESTED_VOLUME_PERCENTAGE if isLast else config.SUGGESTED_VOLUME_PERCENTAGE, config.BackHome_Menu)
			msg = t("INPUT_LAST_SL_VOLUME") if isLast else t("INPUT_SL_VOLUME")
			await send_message(update, msg, menu)

		else:
			if error == 1:
				msg = t("INPUT_SL")
			elif error == 2:
				msg = t("INPUT_SL_E2")
			elif error == 4:
				msg = t("INPUT_SL_E4")
				msg += '\n' + t("INPUT_SLTP_E47", [minTradeEntry, volumeAsset])
			elif error == 6:
				msg = t("INPUT_SL_E6")
				msg += '\n' + t("INPUT_SLTP_E56", [maxTradeEntry, volumeAsset])

			await send_message(update, msg, config.BackHome_Menu)

	elif gettingdata == "tradeStoplossVol":
		dbh.set_states(user_id(update), "send_signal_directly", "send_signal_directly")
		numExits   = int(dbh.get("user", {"userId": user_id(update)}, "tradeStoplossNum"))
		numEntered = len(dbh.get("user", {"userId": user_id(update)}, "tradeStoploss").split("#"))
		isLast = bool(numExits == numEntered)
		valid, error, volumePercentage, volumeAdjusted, volumeAsset, rest, maxOrderQty, minOrderQty, maxOrderAmt, minOrderAmt = await check_volume_entry_exit(update.message.text, user_id(update), entry_sl_tp=1, isLast=isLast)

		if valid:
			dbh.update_value(
			    "user",
			    {"userId": user_id(update)},
			    gettingdata,
			    'concat',
			    str(volumeAdjusted)+"|"+str(volumePercentage),
			)

			if isLast:
				dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeTakeprofitNum"})
				await send_message(update, t("INPUT_NUM_TP"), createMenu([config.NO_TP, 1, 2, 3], config.BackHome_Menu))
			else:
				dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeStoploss"})
				await send_message(update, t("INPUT_SL"), config.BackHome_Menu)

		else:
			if error == 1:
				if isLast:
					msg = t("INPUT_LAST_SL_VOLUME")
				else:
					msg = t("INPUT_SL_VOLUME")
			elif error == 2:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E2")
			elif error == 3:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E3")
			elif error == 4:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E4")
			elif error == 5:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E5")
			elif error == 6:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E6", [rest])
			elif error == 7:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E7", [maxOrderAmt])
			elif error == 8:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E8", [minOrderAmt])
			elif error == 9:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E9", [maxOrderQty])
			elif error == 10:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E10", [minOrderQty])
			if error in [7, 8, 9, 10] and update.message.text[-1] == '%':
				msg += '\n' + t("INPUT_VOLUME_E5678", [volumeAdjusted, volumeAsset])
			menu = createMenu([config.REST]+config.SUGGESTED_VOLUME_PERCENTAGE if isLast else config.SUGGESTED_VOLUME_PERCENTAGE, config.BackHome_Menu)
			await send_message(update, msg, menu)

	elif gettingdata == "tradeTakeprofitNum" or (back_call and gettingdata in ["tradeTakeprofit", "tradeTakeprofitVol", "submit"]):
		dbh.set_states(user_id(update), "send_signal_directly", "send_signal_directly")
		if back_call:
			dbh.set("user", {"userId": user_id(update)}, {"tradeTakeprofitNum": 0})
			dbh.set("user", {"userId": user_id(update)}, {"tradeTakeprofit": None})
			dbh.set("user", {"userId": user_id(update)}, {"tradeTakeprofitVol": None})
			dbh.set("user", {"userId": user_id(update)}, {"submit": None})
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeTakeprofitNum"})
			valid, error = False, 1
		else:
			valid, error = await check_num_entry_exit(update.message.text)

		if valid:
			dbh.set(
			    "user",
			    {"userId": user_id(update)},
			    {gettingdata: update.message.text},
			)
			if update.message.text in [0, config.NO_TP]:
				dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "submit"})
				await send_message(update, t("SUBMIT_ORDER"), createMenu([config.SUBMIT], config.BackHome_Menu))
			else:
				dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeTakeprofit"})
				await send_message(update, t("INPUT_TP"), config.BackHome_Menu)

		else:
			if error == 1:
				msg = t("INPUT_NUM_TP")
			elif error == 2:
				msg = t("INPUT_ENTRY_SL_TP_NUM_E2", [0])
			elif error == 3:
				msg = t("INPUT_ENTRY_SL_TP_NUM_E3", [10])
			await send_message(update, msg, createMenu([config.NO_TP, 1, 2, 3], config.BackHome_Menu))

	elif gettingdata == "tradeTakeprofit":
		dbh.set_states(user_id(update), "send_signal_directly", "send_signal_directly")
		valid, error, minTradeEntry, maxTradeEntry, volumeAsset = await check_tp_sl(update.message.text, gettingdata, user_id(update))

		if valid:
			dbh.update_value(
			    "user",
			    {"userId": user_id(update)},
			    gettingdata,
			    'concat',
			    update.message.text,
			)
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeTakeprofitVol"})
			numExits   = int(dbh.get("user", {"userId": user_id(update)}, "tradeTakeprofitNum"))
			numEntered = len(dbh.get("user", {"userId": user_id(update)}, "tradeTakeprofit").split("#"))
			isLast = bool(numExits == numEntered)
			menu = createMenu([config.REST]+config.SUGGESTED_VOLUME_PERCENTAGE if isLast else config.SUGGESTED_VOLUME_PERCENTAGE, config.BackHome_Menu)
			msg = t("INPUT_LAST_TP_VOLUME") if isLast else t("INPUT_TP_VOLUME")
			await send_message(update, msg, menu)

		else:
			if error == 1:
				msg = t("INPUT_TP")
			elif error == 3:
				msg = t("INPUT_TP_E3")
			elif error == 5:
				msg = t("INPUT_TP_E5")
				msg += '\n' + t("INPUT_SLTP_E56", [maxTradeEntry, volumeAsset])
			elif error == 7:
				msg = t("INPUT_TP_E7")
				msg += '\n' + t("INPUT_SLTP_E47", [minTradeEntry, volumeAsset])

			await send_message(update, msg, config.BackHome_Menu)

	elif gettingdata == "tradeTakeprofitVol":
		dbh.set_states(user_id(update), "send_signal_directly", "send_signal_directly")
		numExits   = int(dbh.get("user", {"userId": user_id(update)}, "tradeTakeprofitNum"))
		numEntered = len(dbh.get("user", {"userId": user_id(update)}, "tradeTakeprofit").split("#"))
		isLast = bool(numExits == numEntered)
		valid, error, volumePercentage, volumeAdjusted, volumeAsset, rest, maxOrderQty, minOrderQty, maxOrderAmt, minOrderAmt = await check_volume_entry_exit(update.message.text, user_id(update), entry_sl_tp=2, isLast=isLast)

		if valid:
			dbh.update_value(
			    "user",
			    {"userId": user_id(update)},
			    gettingdata,
			    'concat',
			    str(volumeAdjusted)+"|"+str(volumePercentage),
			)

			if isLast:
				dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "submit"})
				await send_message(update, t("SUBMIT_ORDER") ,createMenu(config.SUBMIT, config.BackHome_Menu))
			else:
				dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeTakeprofit"})
				await send_message(update, t("INPUT_TP"), config.BackHome_Menu)

		else:
			if error == 1:
				if isLast:
					msg = t("INPUT_LAST_TP_VOLUME")
				else:
					msg = t("INPUT_TP_VOLUME")
			elif error == 2:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E2")
			elif error == 3:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E3")
			elif error == 4:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E4")
			elif error == 5:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E5")
			elif error == 6:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E6", [rest])
			elif error == 7:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E7", [maxOrderAmt])
			elif error == 8:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E8", [minOrderAmt])
			elif error == 9:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E9", [maxOrderQty])
			elif error == 10:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E10", [minOrderQty])
			if error in [7, 8, 9, 10] and update.message.text[-1] == '%':
				msg += '\n' + t("INPUT_VOLUME_E5678", [volumeAdjusted, volumeAsset])
			menu = createMenu([config.REST]+config.SUGGESTED_VOLUME_PERCENTAGE if isLast else config.SUGGESTED_VOLUME_PERCENTAGE, config.BackHome_Menu)
			await send_message(update, msg, menu)

	elif gettingdata == "submit":
		if update.message.text == config.SUBMIT:
			await send_message(update, t("PROCESSING"))
			await back(update, context)

		else:
			await send_message(update, t("SUBMIT_ORDER") ,createMenu(config.SUBMIT, config.BackHome_Menu))


	try:
		gettingdata = dbh.get("user", {"userId": user_id(update)}, "gettingdata")
		await context.bot.editMessageText(
			createOrderInfo(dbh.order_info(user_id(update)), gettingdata),
			update.message.chat_id,
			order_message_id,
		)
	except Exception as e:
		# print("Exception : edit message", e)
		pass

	return SENDSIGNALDIRECTLY_MENU


async def create_new_signal(update: Update, context: ContextTypes.DEFAULT_TYPE, back_call = False):
	gettingdata = dbh.get("user", {"userId": user_id(update)}, "gettingdata")

	order_message_id = dbh.get("user", {"userId": user_id(update)}, "specificMessage")
	orderInfo = dbh.order_info(user_id(update))

	if not (update.message.text == config.CREATE_NEW_SIGNAL or update.message.text == "/create_signal"):
		await remove_until_message(update, context, order_message_id)

	if update.message.text == config.CREATE_NEW_SIGNAL or update.message.text == "/create_signal":
		dbh.set_states(user_id(update), "create_new_signal", "copytradeadmins")
		dbh.reset(user_id(update))

		if dbh.exchanges_set(user_id(update)):
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeExchange"})
			gettingdata = dbh.get("user", {"userId": user_id(update)}, "gettingdata")

			msg = await send_message(update, createOrderInfo(dbh.order_info(user_id(update)), gettingdata, public=True))
			dbh.set("user", {"userId": user_id(update)}, {"specificMessage": msg.message_id})

			await send_message(
			    update,
			    t("INPUT_EXCHANGE"),
			    createMenu(dbh.exchanges_set(user_id(update)), config.BackHome_Menu),
			)

		else:
			await send_message(
			    update,
			    t("NO_EXCHANGE"),
			    config.BackHome_Menu,
			)

	elif gettingdata == "tradeExchange" or (back_call and gettingdata == "tradeMarket"):
		dbh.set_states(user_id(update), "create_new_signal", "copytradeadmins")

		if back_call:
			dbh.set("user", {"userId": user_id(update)}, {"tradeExchange": None})
			dbh.set("user", {"userId": user_id(update)}, {"tradeMarket": None})
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeExchange"})

		if update.message.text in config.EXCHANGE_NAMES:
			dbh.set(
			    "user",
			    {"userId": user_id(update)},
			    {gettingdata: update.message.text},
			)

			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeMarket"})
			await send_message(
			    update,
			    t("INPUT_MARKET"),
			    createMenu(config.MARKET_TYPES, config.BackHome_Menu),
			)
			dbh.set_states(user_id(update), "create_new_signal", "create_new_signal")

		else:
			await send_message(
			    update,
			    t("INPUT_EXCHANGE"),
			    createMenu(dbh.exchanges_set(user_id(update)), config.BackHome_Menu),
			)

	elif gettingdata == "tradeMarket" or (back_call and gettingdata == "tradePair"):
		dbh.set_states(user_id(update), "create_new_signal", "create_new_signal")
		if back_call:
			dbh.set("user", {"userId": user_id(update)}, {"tradeMarket": None})
			dbh.set("user", {"userId": user_id(update)}, {"tradePair": None})
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeMarket"})
			
		if update.message.text in config.MARKET_TYPES:
			dbh.set(
			    "user",
			    {"userId": user_id(update)},
			    {gettingdata: update.message.text},
			)
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradePair"})
			await send_message(
			    update,
			    t("INPUT_PAIR"),
			    createMenu(
			        createMenuFromList(
			            parse_stored_list(
			                dbh.get(
			                    "exchange",
			                    {"name": dbh.get("user", {"userId": user_id(update)}, "tradeExchange")},
			                    "highVolumePairsPerp" if dbh.get("user", {"userId": user_id(update)}, "tradeMarket")
			                    == config.FUTURES else "highVolumePairsSpot",
			                ))),
			        config.BackHome_Menu,
			    ),
			)

		else:
			await send_message(
			    update,
			    t("INPUT_MARKET"),
			    createMenu(config.MARKET_TYPES, config.BackHome_Menu),
			)

	elif gettingdata == "tradePair" or (back_call and gettingdata == "tradeSide"):
		dbh.set_states(user_id(update), "create_new_signal", "create_new_signal")
		if back_call:
			dbh.set("user", {"userId": user_id(update)}, {"tradePair": None})
			dbh.set("user", {"userId": user_id(update)}, {"tradeSide": None})
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradePair"})
			valid, error = False, 1
		else:
			valid, error, pairAdjusted = await check_pair(update.message.text, user_id(update))

		if valid:
			dbh.set(
			    "user",
			    {"userId": user_id(update)},
			    {gettingdata: pairAdjusted},
			)
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeSide"})
			await send_message(
			    update,
			    t("INPUT_SIDE"),
			    createMenu(config.TRADE_SIDES, config.BackHome_Menu),
			)

		else:
			if error == 1:
				msg = t("INPUT_PAIR")
			elif error == 2:
				msg = t("INPUT_PAIR_E2")
			elif error == 3:
				msg = t("INPUT_PAIR_E3")

			await send_message(
			    update,
			    msg,
			    createMenu(
			        createMenuFromList(
			            parse_stored_list(
			                dbh.get(
			                    "exchange",
			                    {"name": dbh.get("user", {"userId": user_id(update)}, "tradeExchange")},
			                    "highVolumePairsPerp" if dbh.get("user", {"userId": user_id(update)}, "tradeMarket")
			                    == config.FUTURES else "highVolumePairsSpot",
			                ))),
			        config.BackHome_Menu,
			    ),
			)

	elif gettingdata == "tradeSide" or (back_call and gettingdata == "tradeLeverage") or (back_call and gettingdata == "tradeVolume" and orderInfo["tradeMarket"] != config.FUTURES):
		dbh.set_states(user_id(update), "create_new_signal", "create_new_signal")
		if back_call:
			dbh.set("user", {"userId": user_id(update)}, {"tradeSide": None})
			dbh.set("user", {"userId": user_id(update)}, {"tradeLeverage": None})
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeSide"})

		if update.message.text in config.TRADE_SIDES:
			dbh.set(
			    "user",
			    {"userId": user_id(update)},
			    {gettingdata: update.message.text},
			)

			if dbh.get("user", {"userId": user_id(update)}, "tradeMarket") == config.FUTURES:
				dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeLeverage"})
				await send_message(
				    update,
				    t("INPUT_LEVERAGE"),
				    createMenu(
				        createMenuFromList(
				            parse_stored_list(
				                dbh.get(
				                    "pair",
				                    {
				                        "exchange": dbh.get("user", {"userId": user_id(update)}, "tradeExchange"),
				                        "symbol": dbh.get("user", {"userId": user_id(update)}, "tradePair"),
				                        "perp": True,
				                    },
				                    "suggestedLeverage",
				                ))),
				        config.BackHome_Menu,
				    ),
				)
			elif dbh.get("user", {"userId": user_id(update)}, "tradeMarket") == config.SPOT:
				dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeVolume"})
				await send_message(update, t("INPUT_VOLUME_PUBLIC"), createMenu(config.SUGGESTED_VOLUME_PERCENTAGE, config.BackHome_Menu))

		else:
			await send_message(
			    update,
			    t("INPUT_SIDE"),
			    createMenu(config.TRADE_SIDES, config.BackHome_Menu),
			)

	elif gettingdata == "tradeLeverage" or (back_call and gettingdata == "tradeVolume" and orderInfo["tradeMarket"] == config.FUTURES):
		dbh.set_states(user_id(update), "create_new_signal", "create_new_signal")
		if back_call:
			dbh.set("user", {"userId": user_id(update)}, {"tradeLeverage": None})
			dbh.set("user", {"userId": user_id(update)}, {"tradeVolume": None})
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeLeverage"})
			valid, error = False, 1
		else:
			valid, error, leverageAdjusted, leverage_info = await check_leverage(update.message.text, user_id(update))

		if valid:
			dbh.set(
			    "user",
			    {"userId": user_id(update)},
			    {gettingdata: leverageAdjusted},
			)
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeVolume"})
			await send_message(update, t("INPUT_VOLUME_PUBLIC"), createMenu(config.SUGGESTED_VOLUME_PERCENTAGE, config.BackHome_Menu))

		else:
			if error == 1:
				msg = t("INPUT_LEVERAGE")
			elif error == 2:
				msg = t("INPUT_LEVERAGE_E2", [str(leverage_info[2]).replace("]", "").replace("[", "").replace("'", "")])
			elif error == 3:
				msg = t("INPUT_LEVERAGE_E3")
			elif error == 4:
				msg = t("INPUT_LEVERAGE_E4", [leverage_info[0]])


			await send_message(
			    update,
			    msg,
			    createMenu(
			        createMenuFromList(
			            parse_stored_list(
			                dbh.get(
			                    "pair",
			                    {
			                        "exchange": dbh.get("user", {"userId": user_id(update)}, "tradeExchange"),
			                        "symbol": dbh.get("user", {"userId": user_id(update)}, "tradePair"),
			                        "perp": True,
			                    },
			                    "suggestedLeverage",
			                ))),
			        config.BackHome_Menu,
			    ),
			)

	elif gettingdata == "tradeVolume" or (back_call and gettingdata == "tradeEntryNum"):
		dbh.set_states(user_id(update), "create_new_signal", "create_new_signal")
		if back_call:
			dbh.set("user", {"userId": user_id(update)}, {"tradeVolume": None})
			dbh.set("user", {"userId": user_id(update)}, {"tradeEntryNum": 0})
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeVolume"})
			valid, error = False, 1
		else:
			valid, error, volumeAdjusted = await check_percentage(update.message.text, min=config.MIN_VOLUME_PERCENTAGE_PUBLIC, max=config.MAX_VOLUME_PERCENTAGE_PUBLIC)
		
		if valid:
			dbh.set(
			    "user",
			    {"userId": user_id(update)},
			    {gettingdata: volumeAdjusted},
			)
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeEntryNum"})
			await send_message(update, t("INPUT_ENTRY_NUM"), createMenu([1, 2, 3], config.BackHome_Menu))
		
		else:
			if error == 1:
				msg = t("INPUT_VOLUME_PUBLIC")
			elif error == 2:
				msg = t("INPUT_VOLUME_PUBLIC_E2")
			elif error == 3:
				msg = t("INPUT_VOLUME_PUBLIC_E3")
			await send_message(update, msg, createMenu(config.SUGGESTED_VOLUME_PERCENTAGE, config.BackHome_Menu))

	elif gettingdata == "tradeEntryNum" or (back_call and gettingdata in ["tradeEntry", "tradeEntryVol", "tradeStoplossNum"]):
		dbh.set_states(user_id(update), "create_new_signal", "create_new_signal")
		if back_call:
			dbh.set("user", {"userId": user_id(update)}, {"tradeEntryNum": 0})
			dbh.set("user", {"userId": user_id(update)}, {"tradeEntry": None})
			dbh.set("user", {"userId": user_id(update)}, {"tradeEntryVol": None})
			dbh.set("user", {"userId": user_id(update)}, {"tradeStoplossNum": 0})
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeEntryNum"})
			valid, error = False, 1
		else:
			valid, error = await check_num_entry_exit(update.message.text, min=1)

		if valid:
			dbh.set(
			    "user",
			    {"userId": user_id(update)},
			    {gettingdata: update.message.text},
			)
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeEntry"})
			await send_message(update, t("INPUT_PRICE"), createMenu(config.MARKET, config.BackHome_Menu))

		else:
			if error == 1:
				msg = t("INPUT_ENTRY_NUM")
			elif error == 2:
				msg = t("INPUT_ENTRY_SL_TP_NUM_E2", [0])
			elif error == 3:
				msg = t("INPUT_ENTRY_SL_TP_NUM_E3", [10])
			await send_message(update, msg, createMenu([1, 2, 3], config.BackHome_Menu))

	elif gettingdata == "tradeEntry":
		dbh.set_states(user_id(update), "create_new_signal", "create_new_signal")
		valid, error, currentPrice, priceAdjusted, minPrice, maxPrice, volumeAsset = await check_price(
		    update.message.text, user_id(update))

		if valid:
			dbh.update_value(
			    "user",
			    {"userId": user_id(update)},
			    gettingdata,
			    'concat',
			    priceAdjusted,
			)
			
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeEntryVol"})
			numEntries = int(dbh.get("user", {"userId": user_id(update)}, "tradeEntryNum"))
			numEntered = len(dbh.get("user", {"userId": user_id(update)}, "tradeEntry").split("#"))
			isLast = bool(numEntries == numEntered)
			menu = createMenu(config.REST if isLast else config.SUGGESTED_VOLUME_PERCENTAGE, config.BackHome_Menu)
			msg = t("INPUT_LAST_ENTRY_VOLUME") if isLast else t("INPUT_ENTRY_VOLUME")
			await send_message(update, msg,menu)

		else:
			if error == 1:
				msg = t("INPUT_PRICE")
			elif error == 2:
				msg = t("INPUT_PRICE_E2")
			elif error == 3:
				msg = t("INPUT_PRICE_E3")
			elif error == 4:
				msg = t("INPUT_PRICE_E4", [minPrice])
			elif error == 5:
				msg = t("INPUT_PRICE_E5", [maxPrice])

			if error in [2, 3]:
				msg += '\n'
				msg += t("INPUT_PRICE_E23", [currentPrice, volumeAsset])
			await send_message(update, msg, createMenu(config.MARKET, config.BackHome_Menu))

	elif gettingdata == "tradeEntryVol":
		dbh.set_states(user_id(update), "create_new_signal", "create_new_signal")
		numEntries = int(dbh.get("user", {"userId": user_id(update)}, "tradeEntryNum"))
		numEntered = len(dbh.get("user", {"userId": user_id(update)}, "tradeEntry").split("#"))
		isLast = bool(numEntries == numEntered)
		valid, error, volumePercentage, rest, volumeAsset = await check_percentage_volume_entry_exit(update.message.text, user_id(update), entry_sl_tp=0, isLast=isLast)

		if valid:
			dbh.update_value(
			    "user",
			    {"userId": user_id(update)},
			    gettingdata,
			    'concat',
			    "-1|"+str(volumePercentage),
			)

			if isLast:
				dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeStoplossNum"})
				await send_message(update, t("INPUT_NUM_SL"), createMenu([config.NO_SL, 1, 2, 3], config.BackHome_Menu))
			else:
				dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeEntry"})
				await send_message(update, t("INPUT_PRICE"), createMenu(config.MARKET, config.BackHome_Menu))

		else:
			if error == 1:
				msg = t("INPUT_LAST_ENTRY_VOLUME")
			elif error == 2:
				msg = t("INPUT_VOLUME_PUBLIC")
			elif error == 3:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E2")
			elif error == 4:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E6", [rest])

			menu = createMenu(config.REST if isLast else config.SUGGESTED_VOLUME_PERCENTAGE, config.BackHome_Menu)
			await send_message(update, msg, menu)

	elif gettingdata == "tradeStoplossNum" or (back_call and gettingdata in ["tradeStoploss", "tradeStoplossVol", "tradeTakeprofitNum"]):
		dbh.set_states(user_id(update), "create_new_signal", "create_new_signal")
		if back_call:
			dbh.set("user", {"userId": user_id(update)}, {"tradeStoplossNum": 0})
			dbh.set("user", {"userId": user_id(update)}, {"tradeStoploss": None})
			dbh.set("user", {"userId": user_id(update)}, {"tradeStoplossVol": None})
			dbh.set("user", {"userId": user_id(update)}, {"tradeTakeprofitNum": 0})
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeStoplossNum"})
			valid, error = False, 1
		else:
			valid, error = await check_num_entry_exit(update.message.text)

		if valid:
			dbh.set(
			    "user",
			    {"userId": user_id(update)},
			    {gettingdata: update.message.text},
			)
			if update.message.text in [0, config.NO_SL]:
				dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeTakeprofitNum"})
				await send_message(update, t("INPUT_NUM_TP"), createMenu([config.NO_TP, 1, 2, 3], config.BackHome_Menu))
			else:
				dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeStoploss"})
				await send_message(update, t("INPUT_SL"), config.BackHome_Menu)

		else:
			if error == 1:
				msg = t("INPUT_NUM_SL")
			elif error == 2:
				msg = t("INPUT_ENTRY_SL_TP_NUM_E2", [0])
			elif error == 3:
				msg = t("INPUT_ENTRY_SL_TP_NUM_E3", [10])
			await send_message(update, msg, createMenu([config.NO_SL, 1, 2, 3], config.BackHome_Menu))

	elif gettingdata == "tradeStoploss":
		dbh.set_states(user_id(update), "create_new_signal", "create_new_signal")
		valid, error, minTradeEntry, maxTradeEntry, volumeAsset = await check_tp_sl(update.message.text, gettingdata, user_id(update))

		if valid:
			dbh.update_value(
			    "user",
			    {"userId": user_id(update)},
			    gettingdata,
			    'concat',
			    update.message.text,
			)
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeStoplossVol"})
			numExits   = int(dbh.get("user", {"userId": user_id(update)}, "tradeStoplossNum"))
			numEntered = len(dbh.get("user", {"userId": user_id(update)}, "tradeStoploss").split("#"))
			isLast = bool(numExits == numEntered)
			menu = createMenu([config.REST]+config.SUGGESTED_VOLUME_PERCENTAGE if isLast else config.SUGGESTED_VOLUME_PERCENTAGE, config.BackHome_Menu)
			msg = t("INPUT_LAST_SL_VOLUME") if isLast else t("INPUT_SL_VOLUME")
			await send_message(update, msg, menu)

		else:
			if error == 1:
				msg = t("INPUT_SL")
			elif error == 2:
				msg = t("INPUT_SL_E2")
			elif error == 4:
				msg = t("INPUT_SL_E4")
				msg += '\n' + t("INPUT_SLTP_E47", [minTradeEntry, volumeAsset])
			elif error == 6:
				msg = t("INPUT_SL_E6")
				msg += '\n' + t("INPUT_SLTP_E56", [maxTradeEntry, volumeAsset])

			await send_message(update, msg, config.BackHome_Menu)

	elif gettingdata == "tradeStoplossVol":
		dbh.set_states(user_id(update), "create_new_signal", "create_new_signal")
		numExits   = int(dbh.get("user", {"userId": user_id(update)}, "tradeStoplossNum"))
		numEntered = len(dbh.get("user", {"userId": user_id(update)}, "tradeStoploss").split("#"))
		isLast = bool(numExits == numEntered)
		valid, error, volumePercentage, rest, volumeAsset = await check_percentage_volume_entry_exit(update.message.text, user_id(update), entry_sl_tp=1, isLast=isLast)

		if valid:
			dbh.update_value(
			    "user",
			    {"userId": user_id(update)},
			    gettingdata,
			    'concat',
			    "-1|"+str(volumePercentage),
			)

			if isLast:
				dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeTakeprofitNum"})
				await send_message(update, t("INPUT_NUM_TP"), createMenu([config.NO_TP, 1, 2, 3], config.BackHome_Menu))
			else:
				dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeStoploss"})
				await send_message(update, t("INPUT_SL"), config.BackHome_Menu)

		else:
			if error == 1:
				if isLast:
					msg = t("INPUT_LAST_SL_VOLUME")
				else:
					msg = t("INPUT_SL_VOLUME")
			elif error == 2:
				msg = t("INPUT_VOLUME_PUBLIC")
			elif error == 3:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E2")
			elif error == 4:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E6", [rest])

			menu = createMenu(config.REST if isLast else config.SUGGESTED_VOLUME_PERCENTAGE, config.BackHome_Menu)
			await send_message(update, msg, menu)

	elif gettingdata == "tradeTakeprofitNum" or (back_call and gettingdata in ["tradeTakeprofit", "tradeTakeprofitVol", "copy"]):
		dbh.set_states(user_id(update), "create_new_signal", "create_new_signal")
		if back_call:
			dbh.set("user", {"userId": user_id(update)}, {"tradeTakeprofitNum": 0})
			dbh.set("user", {"userId": user_id(update)}, {"tradeTakeprofit": None})
			dbh.set("user", {"userId": user_id(update)}, {"tradeTakeprofitVol": None})
			dbh.set("user", {"userId": user_id(update)}, {"submit": None})
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeTakeprofitNum"})
			valid, error = False, 1
		else:
			valid, error = await check_num_entry_exit(update.message.text)

		if valid:
			dbh.set(
			    "user",
			    {"userId": user_id(update)},
			    {gettingdata: update.message.text},
			)
			if update.message.text in [0, config.NO_TP]:
				dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "submit"})
				await send_message(update, t("SUBMIT_ORDER"), createMenu([config.SUBMIT], config.BackHome_Menu))
			else:
				dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeTakeprofit"})
				await send_message(update, t("INPUT_TP"), config.BackHome_Menu)

		else:
			if error == 1:
				msg = t("INPUT_NUM_TP")
			elif error == 2:
				msg = t("INPUT_ENTRY_SL_TP_NUM_E2", [0])
			elif error == 3:
				msg = t("INPUT_ENTRY_SL_TP_NUM_E3", [10])
			await send_message(update, msg, createMenu([config.NO_TP, 1, 2, 3], config.BackHome_Menu))

	elif gettingdata == "tradeTakeprofit":
		dbh.set_states(user_id(update), "create_new_signal", "create_new_signal")
		valid, error, minTradeEntry, maxTradeEntry, volumeAsset = await check_tp_sl(update.message.text, gettingdata, user_id(update))

		if valid:
			dbh.update_value(
			    "user",
			    {"userId": user_id(update)},
			    gettingdata,
			    'concat',
			    update.message.text,
			)
			dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeTakeprofitVol"})
			numExits   = int(dbh.get("user", {"userId": user_id(update)}, "tradeTakeprofitNum"))
			numEntered = len(dbh.get("user", {"userId": user_id(update)}, "tradeTakeprofit").split("#"))
			isLast = bool(numExits == numEntered)
			menu = createMenu([config.REST]+config.SUGGESTED_VOLUME_PERCENTAGE if isLast else config.SUGGESTED_VOLUME_PERCENTAGE, config.BackHome_Menu)
			msg = t("INPUT_LAST_TP_VOLUME") if isLast else t("INPUT_TP_VOLUME")
			await send_message(update, msg, menu)

		else:
			if error == 1:
				msg = t("INPUT_TP")
			elif error == 3:
				msg = t("INPUT_TP_E3")
			elif error == 5:
				msg = t("INPUT_TP_E5")
				msg += '\n' + t("INPUT_SLTP_E56", [maxTradeEntry, volumeAsset])
			elif error == 7:
				msg = t("INPUT_TP_E7")
				msg += '\n' + t("INPUT_SLTP_E47", [minTradeEntry, volumeAsset])

			await send_message(update, msg, config.BackHome_Menu)

	elif gettingdata == "tradeTakeprofitVol":
		dbh.set_states(user_id(update), "create_new_signal", "create_new_signal")
		numExits   = int(dbh.get("user", {"userId": user_id(update)}, "tradeTakeprofitNum"))
		numEntered = len(dbh.get("user", {"userId": user_id(update)}, "tradeTakeprofit").split("#"))
		isLast = bool(numExits == numEntered)
		valid, error, volumePercentage, rest, volumeAsset = await check_percentage_volume_entry_exit(update.message.text, user_id(update), entry_sl_tp=2, isLast=isLast)

		if valid:
			dbh.update_value(
			    "user",
			    {"userId": user_id(update)},
			    gettingdata,
			    'concat',
			    "-1|"+str(volumePercentage),
			)

			if isLast:
				dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "copy"})
				await send_message(update, t("COPY_ORDER"), config.BackHome_Menu)
			else:
				dbh.set("user", {"userId": user_id(update)}, {"gettingdata": "tradeTakeprofit"})
				await send_message(update, t("INPUT_TP"), config.BackHome_Menu)

		else:
			if error == 1:
				if isLast:
					msg = t("INPUT_LAST_TP_VOLUME")
				else:
					msg = t("INPUT_TP_VOLUME")
			elif error == 2:
				msg = t("INPUT_VOLUME_PUBLIC")
			elif error == 3:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E2")
			elif error == 4:
				msg = t("INPUT_VOLUME_ENTRY_SL_TP_E6", [rest])

			menu = createMenu(config.REST if isLast else config.SUGGESTED_VOLUME_PERCENTAGE, config.BackHome_Menu)
			await send_message(update, msg, menu)

	elif gettingdata == "copy":
		await send_message(update, t("COPY_ORDER"), config.BackHome_Menu)


	try:
		gettingdata = dbh.get("user", {"userId": user_id(update)}, "gettingdata")
		await context.bot.editMessageText(
			createOrderInfo(dbh.order_info(user_id(update)), gettingdata, public=True),
			update.message.chat_id,
			order_message_id,
		)
	except Exception as e:
		# print("Exception : edit message", e)
		pass

	return CREATENEWSIGNAL_MENU


async def my_followers(update: Update, context: ContextTypes.DEFAULT_TYPE, back_call = False):
	dbh.set_states(user_id(update), "my_followers", "copytradeadmins")
	followers, follower_groups, follower_channels = dbh.get_copytrade_admin(user_id(update), "both")
	numFollowersGroups   = sum([len(dbh.get("user_group",   {"groupId"   : i.split(" # ")[0]}, "userId", first=False)) for i in follower_groups])
	numFollowersChannels = sum([len(dbh.get("user_channel", {"channelId" : i.split(" # ")[0]}, "userId", first=False)) for i in follower_channels])
	numFollowers = numFollowersGroups + numFollowersChannels
	
	msg = t("MY_FOLLOWERS", [numFollowers, numFollowersGroups, numFollowersChannels])

	if bool(match("^[-+]?[0-9]*\s#\s.*$", update.message.text)):
		chatId = int(update.message.text.split(" # ")[0])

		if update.message.text in follower_groups:
			dbh.remove(
			    "user_copytradeadmin_group",
			    {
			        "userId": user_id(update),
			        "groupId": chatId,
			    },
			)
			msg = "1"

		elif update.message.text in follower_channels:
			dbh.remove(
			    "user_copytradeadmin_channel",
			    {
			        "userId": user_id(update),
			        "channelId": chatId,
			    },
			)
			msg = "2"
		else:
			if chatId in dbh.get_column_values("group", "groupId"):
				chatMember = await context.bot.get_chat_member(chatId, user_id(update))
				if chatMember["status"] in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER]:
					dbh.add(
						"user_copytradeadmin_group",
						{
							"userId": user_id(update),
							"groupId": chatId,
						},
					)
					msg = "3"
				else:
					msg = "4"
			elif chatId in dbh.get_column_values("channel", "channelId"):
				chatMember = await context.bot.get_chat_member(chatId, user_id(update))
				if chatMember["status"] in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
					dbh.add(
						"user_copytradeadmin_channel",
						{
							"userId": user_id(update),
							"channelId": chatId,
						},
					)
					msg = "5"
				else:
					msg = "6"
		
	followers, follower_groups, follower_channels = dbh.get_copytrade_admin(user_id(update), "both")
	print(followers, follower_groups, follower_channels)
	await send_message(update, msg, createMenu(followers, config.BackHome_Menu))

	return MYFOLLOWERS_MENU


# Only known handlers may be invoked from a persisted navigation state.
_NAVIGATION_HANDLERS = {
    "account_status": account_status,
    "admin": admin,
    "api_management": api_management,
    "automation": automation,
    "contact_us": contact_us,
    "copytradeadmins": copytradeadmins,
    "create_new_signal": create_new_signal,
    "getting_statement": getting_statement,
    "instruction": instruction,
    "mainmenu": mainmenu,
    "management": management,
    "my_followers": my_followers,
    "referral": referral,
    "send_signal_directly": send_signal_directly,
    "set_api": set_api,
    "setting_trading_constants": setting_trading_constants,
    "statement": statement,
    "subscribe": subscribe,
    "telegram_channel": telegram_channel,
    "telegram_group": telegram_group,
    "trading_constants": trading_constants,
    "tradingview": tradingview,
}


def _navigation_handler(name):
    handler = _NAVIGATION_HANDLERS.get(name)
    if handler is None:
        logger.warning("Invalid stored navigation state: %r", name)
        return mainmenu
    return handler


async def back(update: Update, context: ContextTypes.DEFAULT_TYPE, back_call = False):
	dbh.set("user", {"userId": user_id(update)}, {"back": True})
	function = dbh.get("user", {"userId": user_id(update)}, "previousState")
	return await _navigation_handler(function)(update, context, back_call=True)


async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE, back_call = False):
	function = dbh.get("user", {"userId": user_id(update)}, "thisState")
	return await _navigation_handler(function)(update, context)


async def tradingview_handler_func(update: Update, context: ContextTypes.DEFAULT_TYPE, back_call = False):
	try:
		process_tradingview_signal(update.channel_post.text, dbh)
	except:
		print("Wrong Tradingview Signal")


async def group_handler_func(update: Update, context: ContextTypes.DEFAULT_TYPE, back_call = False):
	if update.message.text == "/get_id":
		await send_message(update, f"`{str(update.effective_chat.id)} # {update.effective_chat.title}`")
		try:
			dbh.add(
			    "group",
			    {
			        "groupId": update.effective_chat.id,
			        "groupTitle": update.effective_chat.title,
			    },
			)
		except Exception as e:
			print("EXCEPTION group_handler_func", e)
			pass

	try:
		process_telegram_signal(update.message.text, update.message.chat_id, "group", dbh)
	except:
		print("Wrong Group Signal")


async def channel_handler_func(update: Update, context: ContextTypes.DEFAULT_TYPE, back_call = False):
	if update.channel_post.text == "/get_id":
		await send_message(update, f"`{str(update.effective_chat.id)} # {update.effective_chat.title}`")
		try:
			dbh.add(
			    "channel",
			    {
			        "channelId": update.effective_chat.id,
			        "channelTitle": update.effective_chat.title,
			    },
			)
		except Exception as e:
			print("EXCEPTION channel_handler_func", e)
			pass

	try:
		process_telegram_signal(update.channel_post.text, update.channel_post.chat_id, "channel", dbh)
	except:
		print("Wrong Group Signal")


async def send_message(update: Update, message, menu=None, escape=True):
	try:
		if menu is not None:
			msg = await update.effective_message.reply_text(
			    escape_markdown(message, version=2) if escape else message,
			    parse_mode=ParseMode.MARKDOWN_V2,
			    reply_markup=ReplyKeyboardMarkup(menu, one_time_keyboard=True, resize_keyboard=True),
			)
		else:
			msg = await update.effective_message.reply_text(escape_markdown(message, version=2) if escape else message,
			                                                parse_mode=ParseMode.MARKDOWN_V2)

		try:
			dbh.message_counter(user_id(update), msg.message_id)
		except Exception as e:
			print("EXCEPTION send_message counter", e)
			pass

		return msg

	except Exception as e:
		print("EXCEPTION send_message", e)


async def update_pairs_info(context: ContextTypes.DEFAULT_TYPE):
	for i in config.EXCHANGE_NAMES:
		if i == config.BINANCE:
			continue

		client = exchangeClient(i, *get_api_credentials(-1, i, dbh), dbh).client

		futures, spot = client.get_pairs_info()

		for k in futures + spot:
			if not dbh.set(
			    "pair",
			    {
			        "exchange": i,
			        "symbol": k['symbol'],
			        "perp": k['perp']
			    },
			    {
			        "symbolUnstructured": k['symbolUnstructured'],
			        "maxLeverage": float(k['leverageInfo'][0]),
			        "stepLeverage": float(k['leverageInfo'][2]),
			        "suggestedLeverage": str(k['leverageInfo'][1]),
			        "minOrderQty": float(k["minOrderQty"]),
			        "maxOrderQty": float(k["maxOrderQty"]),
			        "assetTickSize": float(k["assetTickSize"]),
			        "minOrderAmt": float(k["minOrderAmt"]),
			        "maxOrderAmt": float(k["maxOrderAmt"]),
			        "currencyTickSize": float(k["currencyTickSize"]),
			        "minPrice": float(k["minPrice"]),
			        "maxPrice": float(k["maxPrice"]),
			        "priceTickSize": float(k["priceTickSize"]),
			        "available": k["available"],
			    },
			):
				dbh.add(
				    "pair",
				    {
				        "exchange": i,
				        "symbol": k['symbol'],
				        "perp": k['perp'],
				        "symbolUnstructured": k['symbolUnstructured'],
				        "maxLeverage": float(k['leverageInfo'][0]),
				        "stepLeverage": float(k['leverageInfo'][2]),
				        "suggestedLeverage": str(k['leverageInfo'][1]),
				        "minOrderQty": float(k["minOrderQty"]),
				        "maxOrderQty": float(k["maxOrderQty"]),
				        "assetTickSize": float(k["assetTickSize"]),
				        "minOrderAmt": float(k["minOrderAmt"]),
				        "maxOrderAmt": float(k["maxOrderAmt"]),
				        "currencyTickSize": float(k["currencyTickSize"]),
				        "minPrice": float(k["minPrice"]),
				        "maxPrice": float(k["maxPrice"]),
				        "priceTickSize": float(k["priceTickSize"]),
				        "available": k["available"],
				    },
				)

		high_volume_pairs_perp = client.get_high_volume_pairs(perp=True)
		if not dbh.set("exchange", {"name": i}, {"highVolumePairsPerp": str(high_volume_pairs_perp)}):
			dbh.add("exchange", {
			    "name": i,
			    "highVolumePairsPerp": str(high_volume_pairs_perp)
			})

		high_volume_pairs_spot = client.get_high_volume_pairs(perp=False)
		if not dbh.set("exchange", {"name": i}, {"highVolumePairsSpot": str(high_volume_pairs_spot)}):
			dbh.add("exchange", {
			    "name": i,
			    "highVolumePairsSpot": str(high_volume_pairs_spot)
			})


def main() -> None:
	if not config.MAIN_BOT_TOKEN:
		raise RuntimeError("MAIN_BOT_TOKEN is required to start the Telegram bot")
	if config.OFFLINE and config.ADMINS_ID == [0]:
		raise RuntimeError("Set TELEGRAM_ADMIN_IDS to use the default offline mode")
	application = Application.builder().token(config.MAIN_BOT_TOKEN).build()
	conv_handler = ConversationHandler(
	    entry_points=[MessageHandler(filters.ChatType.PRIVATE, start)],
	    states={
	        MAINMENU: [
	            MessageHandler(filters.Text(config.AUTOMATION), automation),
	            MessageHandler(filters.Text(config.STATEMENT), statement),
	            MessageHandler(filters.Text(config.MANAGEMENT), management),
	            MessageHandler(filters.Text(config.ACCOUNT_STATUS), account_status),
	            MessageHandler(filters.Text(config.COPYTRADE_ADMINS), copytradeadmins),
	            MessageHandler(filters.Text(config.CONTACT_US), contact_us),
	            MessageHandler(filters.Text(config.INSTRUCTION), instruction),
	            MessageHandler(filters.Text(config.ADMIN) & filters.Chat(config.ADMINS_ID), admin),
	        ],
	        AUTOMATION_MENU: [
	            MessageHandler(filters.Text(config.TRADINGVIEW), tradingview),
	            MessageHandler(filters.Text(config.TELEGRAM_GROUP), telegram_group),
	            MessageHandler(filters.Text(config.TELEGRAM_CHANNEL), telegram_channel),
	            MessageHandler(filters.Text(config.SEND_SIGNAL_DIRECTLY), send_signal_directly),
	        ],
	        STATEMENT_MENU: [
	            MessageHandler(
	                filters.Regex(
	                    createRegex([
	                        config.CHANGESTATEMENTSYMBOLS,
	                        config.GETSTATEMENT,
	                        "([a-zA-Z]*:)+[a-zA-Z]*",
	                    ])),
	                getting_statement,
	            )
	        ],
	        MANAGEMENT_MENU: [
	            MessageHandler(filters.Text(config.API_MANAGEMENT), api_management),
	            MessageHandler(filters.Text(config.TRADING_CONSTANTS), trading_constants),
	        ],
	        ACCOUNTSTATUS_MENU: [
	            MessageHandler(filters.Text(config.SUBSCRIBE), subscribe),
	            MessageHandler(filters.Text(config.REFERRAL), referral),
	        ],
			COPYTRADEADMINS_MENU: [
				MessageHandler(filters.Text(config.CREATE_NEW_SIGNAL), create_new_signal),
				MessageHandler(filters.Text(config.MY_FOLLOWERS), my_followers),
			],
	        CREATENEWSIGNAL_MENU: [
	            MessageHandler(
	                filters.ALL & ~(filters.COMMAND | filters.Regex(createRegex([config.BACK,
																				 config.HOME,
																				]))),
	                create_new_signal,
	            )
	        ],
			MYFOLLOWERS_MENU: [
	            MessageHandler(
	                filters.ALL & ~(filters.COMMAND | filters.Regex(createRegex([config.BACK,
																				 config.HOME,
																				]))),
	                my_followers,
	            )
			],
	        SUBSCRIBE_MENU: [
	            MessageHandler(
	                filters.Regex(
	                    createRegex([
	                        config.MONTH1, config.MONTH3, config.MONTH6, config.MONTH12,
	                        f"([0-9]|[a-z]){{{config.TRC20_TRANSACTION_ID_LENGTH}}}", f"([0-9]|[a-z])+"
	                    ])),
	                subscribe2,
	            ),
	        ],
	        REFERRAL_MENU: [
	            MessageHandler(
	                filters.Regex(
	                    createRegex([
	                        config.ENTER_REFERRAL_CODE,
	                        "[0-9]+",
	                        config.WITHDRAW_CASHBACK,
	                        config.DISCOUNTED_SUB,
	                    ])),
	                referral,
	            ),
	        ],
	        APIMANAGEMENT_MENU: [
	            MessageHandler(
	                filters.Regex(
	                    createRegex([
	                        config.BINANCE,
	                        config.COINEX,
	                        config.BYBIT,
	                        config.BINGX,
	                        config.ACTIVATE,
	                        config.DEACTIVATE,
	                        ".+#.+",
	                    ])),
	                set_api,
	            ),
	        ],
	        TRADINGCONSTANTS_MENU: [
	            MessageHandler(
	                filters.Regex(
	                    createRegex([
	                        config.VOLUME,
	                        config.LEVERAGE,
	                        config.STOPLOSS,
	                        config.TAKEPROFIT,
	                        "[+-]?([0-9]*[.])?[0-9]+",
	                    ])),
	                setting_trading_constants,
	            ),
	        ],
	        TELEGRAMGROUP_MENU: [MessageHandler(filters.Regex("^[-+]?[0-9]*\s#\s.*$"), telegram_group)],
	        TELEGRAMCHANNEL_MENU: [MessageHandler(filters.Regex("^[-+]?[0-9]*\s#\s.*$"), telegram_channel)],
	        SENDSIGNALDIRECTLY_MENU: [
	            MessageHandler(
	                filters.ALL & ~(filters.COMMAND | filters.Regex(createRegex([config.BACK,
																				 config.HOME,
																				]))),
	                send_signal_directly,
	            )
	        ],
	        ADMIN_MENU: [
	            MessageHandler(filters.Text(config.SEND_MESSAGE_TO_ALL), admin),
	            MessageHandler(filters.ALL & ~filters.Text([config.BACK, config.HOME]), admin),
	        ],
	    },
	    fallbacks=[
	        CommandHandler("menu", mainmenu),
	        CommandHandler("automation", automation),
	        CommandHandler("tradingview", tradingview),
	        CommandHandler("group", telegram_group),
	        CommandHandler("channel", telegram_channel),
	        CommandHandler("direct", send_signal_directly),
	        CommandHandler("statement", statement),
	        CommandHandler("management", management),
	        CommandHandler("api", api_management),
	        CommandHandler("status", account_status),
	        CommandHandler("subscribe", subscribe),
	        CommandHandler("contact", contact_us),
	        MessageHandler(filters.Text(config.BACK), back),
	        MessageHandler(filters.Text(config.HOME), mainmenu),
	        MessageHandler(filters.ALL, unrecognized),
	    ],
	)

	tradingview_handler = MessageHandler(
	    filters.TEXT & filters.SenderChat(config.TRADINGVIEW_ALERTS_CHANNEL_ID),
	    tradingview_handler_func,
	)
	group_handler = MessageHandler(filters.TEXT & filters.ChatType.GROUPS, group_handler_func)
	channel_handler = MessageHandler(filters.TEXT & filters.ChatType.CHANNEL, channel_handler_func)

	application.add_handler(conv_handler)
	application.add_handler(tradingview_handler)
	application.add_handler(group_handler)
	application.add_handler(channel_handler)

	# application.job_queue.run_once(update_pairs_info, 0, data=True)
	# application.job_queue.run_daily(update_pairs_info, time())
	application.run_polling()


if __name__ == "__main__":
	main()
