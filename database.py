from curses.ascii import TAB
from logging import exception
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta
from config import *
from helperfunctions import createSecret, days_hours_minutes

engine = create_engine(SQL_DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class databaseHandler(object):

	def __init__(self, session, models):
		self.session = session
		self.user = models.user
		self.group = models.group
		self.channel = models.channel
		self.user_group = models.user_group
		self.user_channel = models.user_channel
		self.user_copytradeadmin_group = models.user_copytradeadmin_group
		self.user_copytradeadmin_channel = models.user_copytradeadmin_channel
		self.transaction = models.transaction
		self.pair = models.pair
		self.exchange = models.exchange

	def commit(self):
		try:
			self.session.commit()
			return True
		except Exception as e:
			self.session.rollback()
			print("Commit Failed !", e)
			return False

	def choose_table(self, table_name: str):
		return getattr(self, table_name)

	def get_records(self, table_name, att_val: dict):
		this_table = self.choose_table(table_name)
		these_record = self.session.query(this_table)
		for attribute, value in att_val.items():
			these_record = these_record.filter(getattr(this_table, attribute) == value)
		return these_record.all()

	def get_column_values(self, table_name, attribute) -> list:
		this_table = self.choose_table(table_name)
		all_column_values = self.session.query(getattr(this_table, attribute)).all()
		all_column_values = [i[0] for i in all_column_values]
		return all_column_values

	def start(self, update):
		user_id = update.effective_chat.id
		all_users_id = self.get_column_values('user', 'userId')
		if user_id not in all_users_id:
			new_user = self.user()
			new_user.id = len(self.get_column_values("user", "id")) + 1
			new_user.userId = user_id
			new_user.username = update.effective_user.username
			new_user.joinedOn = datetime.now()
			try:
				new_user.name = update.effective_user.first_name + ' ' + update.effective_user.last_name
			except:
				new_user.name = update.effective_user.first_name

			new_user.subscriptionEndingTime = datetime.now() + timedelta(days=1)
			new_user.secret = createSecret(SECRET_KEY_LENGTH)

			self.session.add(new_user)
			self.commit()

			print(f"New User : user id = {user_id}, name = {new_user.name}")
		else:
			print('Old User')

	def set_states(self, user_id, this_state, previous_state):
		this_record = self.get_records('user', {'userId': user_id})[0]
		this_record.thisState = this_state
		this_record.previousState = previous_state
		self.commit()


	def set(self, table_name, att_val: dict, new_att_val: dict):
		try:
			these_records = self.get_records(table_name, att_val)
			if len(these_records) == 0:
				return 0

			for this_record in these_records:
				for att, new_val in new_att_val.items():
					setattr(this_record, att, new_val)
				self.commit()
			return 1
		except:
			return 0

	def get(self, table_name, att_val: dict, attributes, first=True):
		these_records = self.get_records(table_name, att_val)
		if first:
			if len(these_records) == 0:
				return None

			if type(attributes) == list:
				return [getattr(these_records[0], attribute) for attribute in attributes]
			elif type(attributes) == str:
				return getattr(these_records[0], attributes)

		if len(these_records) == 0:
			return []

		if type(attributes) == list:
			result = []
			for this_record in these_records:
				result.append([getattr(this_record, attribute) for attribute in attributes])
			return result
		elif type(attributes) == str:
			return [getattr(this_record, attributes) for this_record in these_records]
		

	def update_value(self, table_name, att_val: dict, attributes, action, value) -> bool:
		# try:
		these_records = self.get_records(table_name, att_val)
		if len(these_records) == 0:
			return False
		
		if type(attributes) == str:
			attributes = [attributes]

		for this_record in these_records:
			for attribute in attributes:
				if action == '+':
					setattr(this_record, attribute, getattr(this_record, attribute)+float(value))
				elif action == '-':
					setattr(this_record, attribute, getattr(this_record, attribute)-float(value))
				elif action == 'concat':
					if getattr(this_record, attribute) == None:
						setattr(this_record, attribute, str(value))
					else:
						setattr(this_record, attribute, str(getattr(this_record, attribute))+'#'+str(value))
		
		self.commit()
		# 	return True
		# except:
		# 	return False

		
	def add(self, table_name, att_val: dict):
		try:
			this_table = self.choose_table(table_name)
			this_record = this_table()
			for attribute, value in att_val.items():
				setattr(this_record, attribute, value)
			self.session.add(this_record)
			self.commit()
			return 1
		except:
			return 0

	def remove(self, table_name, att_val: dict):
		these_records = self.get_records(table_name, att_val)
		for this_record in these_records:
			self.session.delete(this_record)
			self.commit()

	def get_user(self, user_id):
		return self.session.query(self.user).filter(self.user.userId == user_id).first()

	def has_subscription(self, user_id):
		deadline = self.get('user', {'userId': user_id}, 'subscriptionEndingTime')
		d, h, m = days_hours_minutes(deadline - datetime.now())
		return False if d < 0 and h < 0 and m < 0 else True

	def subscribe(self, user_id, duration, amount=0, tx_id=0, referral=False):
		if tx_id not in self.get_column_values('transaction', 'transactionId') or referral:
			this_user = self.get_user(user_id)
			this_user.subscriptionEndingTime = max(this_user.subscriptionEndingTime, datetime.now()) + timedelta(days=duration)

			if not referral:
				this_user.purchaseAmount += amount
				this_transaction = self.transaction()
				this_transaction.transactionId = tx_id
				self.session.add(this_transaction)
				if this_user.referredBy != None:
					self.get_user(this_user.referredBy.userId).referralIncome += float(amount) * REFERRAL_CASHBACK_PERCENTAGE / 100

			self.commit()
			return True
		return False

	def exchanges_set(self, user_id):
		exchanges = []
		this_user = self.get_user(user_id)

		if this_user.binance_api is not None:
			exchanges.append(BINANCE)
		if this_user.coinex_api is not None:
			exchanges.append(COINEX)
		if this_user.bybit_api is not None:
			exchanges.append(BYBIT)
		if this_user.bingx_api is not None:
			exchanges.append(BINGX)

		return exchanges

	def message_counter(self, user_id, last_message_id):
		this_user = self.get_user(user_id)
		this_user.numMessages = last_message_id + 1

	def reset(self, user_id):
		this_user = self.get_user(user_id)

		this_user.back = False
		this_user.specificMessage = None
		this_user.tradeExchange = None
		this_user.tradeMarket = None
		this_user.tradePair = None
		this_user.tradeSide = None
		this_user.tradeVolume = None
		this_user.tradeEntryNum = 0
		this_user.tradeEntry = None
		this_user.tradeEntryVol = None
		this_user.tradeLeverage = None
		this_user.tradeStoplossNum = 0
		this_user.tradeStoploss = None
		this_user.tradeStoplossVol = None
		this_user.tradeTakeprofitNum = 0
		this_user.tradeTakeprofit = None
		this_user.tradeTakeprofitVol = None

	def order_info(self, user_id):
		this_user = self.get_user(user_id)
		return {
			"tradeExchange" : this_user.tradeExchange,
			"tradeMarket" : this_user.tradeMarket,
			"tradePair" : this_user.tradePair,
			"tradeSide" : this_user.tradeSide,
			"tradeLeverage" : this_user.tradeLeverage,
			"tradeVolume" : this_user.tradeVolume,
			"tradeEntryNum" : this_user.tradeEntryNum,
			"tradeEntry" : this_user.tradeEntry,
			"tradeEntryVol" : this_user.tradeEntryVol,
			"tradeStoplossNum" : this_user.tradeStoplossNum,
			"tradeStoploss" : this_user.tradeStoploss,
			"tradeStoplossVol" : this_user.tradeStoplossVol,
			"tradeTakeprofitNum" : this_user.tradeTakeprofitNum,
			"tradeTakeprofit" : this_user.tradeTakeprofit,
			"tradeTakeprofitVol" : this_user.tradeTakeprofitVol,
		}

	def get_another_column(self, table_name, att_vals, att):
		atts = []
		for attribute, values in att_vals.items():
			for value in values:
				try:
					atts.append(self.get(table_name, {attribute: value}, att))
				except:
					atts.append("-")
		return atts

	def get_following(self, user_id, group_channel):
		following_id = self.get(f'user_{group_channel}', {'userId': user_id}, f'{group_channel}Id', False)
		following_title = self.get_another_column(f'{group_channel}', {f'{group_channel}Id': following_id},
		                                          f'{group_channel}Title')
		followings = [f"{i} # {t}" for i, t in zip(following_id, following_title)]
		return followings

	def get_copytrade_admin(self, user_id, group_channel):
		if group_channel in ["group", "channel"]:
			follower_id = self.get(f'user_copytradeadmin_{group_channel}', {'userId': user_id}, f'{group_channel}Id', False)
			follower_title = self.get_another_column(f'{group_channel}', {f'{group_channel}Id': follower_id},
													f'{group_channel}Title')
			followers = [f"{i} # {t}" for i, t in zip(follower_id, follower_title)]
			return followers, [], []
		
		elif group_channel == "both":
			follower_groups, _, _ = self.get_copytrade_admin(user_id, "group")
			follower_channels, _, _ = self.get_copytrade_admin(user_id, "channel")
			followers = follower_groups + follower_channels
			return followers, follower_groups, follower_channels
