from tokenize import Double

from sqlalchemy import (
    DATETIME,
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    String,
    Table,
)
from sqlalchemy.orm import relationship, Mapped, backref
from traitlets import default
from typing import List

from database import Base

# class user_user(Base):
# 	__tablename__ = "user_user"

# 	userIdReferrer = Column(ForeignKey("user.userId"), primary_key=True)
# 	userIdReferred = Column(ForeignKey("user.userId"), primary_key=True)


class user_group(Base):
	__tablename__ = "user_group"

	userId = Column(ForeignKey("user.userId"), primary_key=True)
	groupId = Column(ForeignKey("group.groupId"), primary_key=True)


class user_channel(Base):
	__tablename__ = "user_channel"

	userId = Column(ForeignKey("user.userId"), primary_key=True)
	channelId = Column(ForeignKey("channel.channelId"), primary_key=True)


class user_copytradeadmin_group(Base):
	__tablename__ = "user_copytradeadmin_group"

	userId = Column(ForeignKey("user.userId"), primary_key=True)
	groupId = Column(ForeignKey("group.groupId"), primary_key=True)


class user_copytradeadmin_channel(Base):
	__tablename__ = "user_copytradeadmin_channel"

	userId = Column(ForeignKey("user.userId"), primary_key=True)
	channelId = Column(ForeignKey("channel.channelId"), primary_key=True)


class user(Base):
	__tablename__ = "user"

	userId = Column(Integer, primary_key=True)
	id = Column(Integer)
	username = Column(String)
	name = Column(String)
	thisState = Column(String)
	previousState = Column(String)
	back = Column(Boolean, default=False)
	subscriptionEndingTime = Column(DATETIME)
	joinedOn = Column(DATETIME)
	purchaseAmount = Column(Integer, default=0)
	leverage = Column(Integer)
	volume = Column(Integer)
	stoploss = Column(Integer)
	takeprofit = Column(Integer)
	binance_api = Column(String)
	coinex_api = Column(String)
	bybit_api = Column(String)
	bingx_api = Column(String)
	binance_active = Column(Boolean, default=False)
	coinex_active = Column(Boolean, default=False)
	bybit_active = Column(Boolean, default=False)
	bingx_active = Column(Boolean, default=False)
	secret = Column(String)
	gettingdata = Column(String)
	payingSubscriptionPrice = Column(Float)
	payingSubscriptionDuration = Column(Float)
	statementSymbols = Column(String, default="BTC/USDT:ETH/USDT:BNB/USDT:ADA/USDT")
	tradeExchange = Column(String)
	tradeMarket = Column(String)
	tradePair = Column(String)  # BTCUSDT
	tradeSide = Column(String)
	tradeLeverage = Column(Integer)
	tradeVolume = Column(Integer)
	tradeEntryNum = Column(Integer, default=0)
	tradeEntry = Column(String)  
	tradeEntryVol = Column(String)  # accepts both exact number and percentage of equity
	tradeStoplossNum = Column(Integer, default=0)
	tradeStoploss = Column(String)  # accepts both exact number and percentage of loss
	tradeStoplossVol = Column(String)
	tradeTakeprofitNum = Column(Integer, default=0)
	tradeTakeprofit = Column(String)  # accepts both exact number and percentage of profit
	tradeTakeprofitVol = Column(String)
	submit = Column(Boolean, default=False)
	numMessages = Column(Integer)
	specificMessage = Column(Integer)
	referralIncome = Column(Integer, default=0)
	referralIncomeWithdraw = Column(Integer, default=0)
	referralIncomeSubscribe = Column(Integer, default=0)
	_ = Column(String, ForeignKey('user.userId'))
	referredBy = relationship('user', backref='referred', remote_side=[userId])
	groups = relationship(user_group)
	channels = relationship(user_channel)


class group(Base):
	__tablename__ = "group"

	groupId = Column(Integer, primary_key=True)
	groupTitle = Column(String)
	users = relationship(user_group)


class channel(Base):
	__tablename__ = "channel"

	channelId = Column(Integer, primary_key=True)
	channelTitle = Column(String)
	users = relationship(user_channel)


class transaction(Base):
	__tablename__ = "transaction"

	transactionId = Column(String, primary_key=True)


class pair(Base):
	__tablename__ = "pair"

	exchange = Column(String, ForeignKey("exchange.name"), primary_key=True)
	symbol = Column(String, primary_key=True)
	perp = Column(Boolean, primary_key=True)
	symbolUnstructured = Column(String)
	maxLeverage = Column(Integer)
	stepLeverage = Column(Integer)
	suggestedLeverage = Column(String)
	minOrderQty = Column(Integer)
	maxOrderQty = Column(Integer)
	assetTickSize = Column(Integer)
	minOrderAmt = Column(Integer)
	maxOrderAmt = Column(Integer)
	currencyTickSize = Column(Integer)
	minPrice = Column(Integer)
	maxPrice = Column(Integer)
	priceTickSize = Column(Integer)
	available = Column(Boolean, default=True)


class exchange(Base):
	__tablename__ = "exchange"

	name = Column(String, primary_key=True)
	highVolumePairsPerp = Column(String)
	highVolumePairsSpot = Column(String)
