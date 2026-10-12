import io

import matplotlib.pyplot as plt
import seaborn as sns
from arabic_reshaper import reshape
from bidi.algorithm import get_display
from matplotlib.gridspec import GridSpec

from database import databaseHandler
from ExchangeClients import BingXClient, ByBitClient, CoinexClient
from exchanges import active_exchanges, get_api_credentials
from helperfunctions import addDict

sns.set_theme(style="ticks", color_codes=True)

async def calculateStatementData(user_id:int, dbh:databaseHandler):
    statement_data = {}

    userStatementSymbols = dbh.get('user', {'userId':user_id}, 'statementSymbols')
    exchanges = active_exchanges(user_id, dbh)

    for exchange, is_active in exchanges.items():
        if is_active:
            if exchange == 'coinex':
                print(exchange)
                client = CoinexClient(*get_api_credentials(user_id, 'coinex', dbh))
                coinexStatement = client.calculate_statement(userStatementSymbols)
                statement_data = await addDict(statement_data, coinexStatement)

            if exchange == 'bingx':
                print(exchange)
                client = BingXClient(*get_api_credentials(user_id, exchange, dbh))
                bingxStatement = client.calculate_statement(userStatementSymbols)
                statement_data = await addDict(statement_data, bingxStatement)

            if exchange == 'bybit':
                print(exchange)
                client = ByBitClient(*get_api_credentials(user_id, exchange, dbh))
                bybitStatement = client.calculate_statement(userStatementSymbols)
                statement_data = await addDict(statement_data, bybitStatement)

            if exchange == 'binance':
                print(exchange)
                binanceStatement = {'binanceTradesCount':0}
                statement_data = await addDict(statement_data, binanceStatement)
                pass

    return statement_data


def sort_list_by_list(list1, list2):
    return [x for _,x in sorted(zip(list1,list2))][::-1]

def display_persian(text):
    return get_display(reshape(text))

def calculate_data(data:dict):
    symbols = []
    win = []
    lose = []
    profit = []
    
    for key, _ in data.items():
        if key.find('WinTrade') >= 0:
            symbols.append(key.split('WinTrade')[0])
    symbols.remove('num')
    
    for symbol in symbols:
        win.append(data[symbol+'WinTrade'] / (data[symbol+'WinTrade'] + data[symbol+'LoseTrade']))
        lose.append(data[symbol+'LoseTrade'] / (data[symbol+'WinTrade'] + data[symbol+'LoseTrade']))
        profit.append(data[symbol+'Profit'])
        
    symbols = sort_list_by_list(win, symbols)
    lose = sort_list_by_list(win, lose)
    profit = sort_list_by_list(win, profit)
    win = sorted(win)[::-1]
    
    return symbols, win, lose, profit


def create_pie_chart(ax, data:list, labels:list, title:str, legend_loc:tuple, title_font_size:int=50, legend_font_size=30, legend_title:str=None, colors:list=None):

    ax.pie(
        x = data,    
        colors = colors,
        wedgeprops=dict(width=0.5),
    )

    percentages = [str(float("{:.2f}".format((i/sum(data))*100))) for i in data]
    labels = [l+'  '+p+'%' for l, p in zip(labels, percentages)]
    ax.legend(
        labels = labels,
        fontsize = legend_font_size,
        loc=legend_loc
    )
    ax.set_title(display_persian(title), fontdict={'fontsize':title_font_size})
    return ax

def create_profit_loss_value_chart(ax, data:list, labels:list, title:str, legend_loc:tuple, title_font_size:int=50, legend_font_size=30, legend_title:str=None, colors:list=['green', 'red'], offset=0):
    
    width = 0.2
    values = [float(data[i+'Profit']) for i in labels]
    ax.bar([l for l, v in zip(labels, values) if v>= 0], 
           [v for v in values if v>=0], 
           width, 
           color=colors[0],
           label='Profit')
    
    ax.bar([l for l, v in zip(labels, values) if v<0], 
           [-v for v in values if v<0], 
           width, 
           color=colors[1],
           label='Loss')
    
    plt.xlim((0-offset,1+offset))
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.set_title(display_persian(title), fontdict={'fontsize':title_font_size})
    ax.tick_params(axis='x', labelsize=legend_font_size)
    ax.tick_params(axis='y', labelsize=legend_font_size)
    return ax



async def plotStatement(data):
    width = 0.9
    legend_font_size = 13
    title_font_size = 20 
    fig = plt.figure(figsize = (10,20))
    gs = GridSpec(30, 60)
    ax1 = fig.add_subplot(gs[0:10 , 16:47])
    ax2 = fig.add_subplot(gs[10:18, :30])
    ax3 = fig.add_subplot(gs[9:19, 35:])
    ax4 = fig.add_subplot(gs[20:28, :30])
    ax5 = fig.add_subplot(gs[19:29, 35:])

    d = []
    l = []
    c = []

    if 'binanceTradesCount' in list(data.keys()):
        d.append(data['binanceTradesCount'])
        l.append('Binance')
        c.append('#F3BA2F')
    if 'bybitTradesCount' in list(data.keys()):
        d.append(data['bybitTradesCount'])
        l.append('ByBit')
        c.append('#120f16')
    if 'bingxTradesCount' in list(data.keys()):
        d.append(data['bingxTradesCount'])
        l.append('BingX')
        c.append('#015ac0')
    if 'coinexTradesCount' in list(data.keys()):
        d.append(data['coinexTradesCount'])
        l.append('Coinex')
        c.append('#0EAD98')
        
    print('====')
    print(d)
    print('====')

    create_pie_chart(ax1,
                     data=d,
                     labels=l,
                     title="درصد معاملات در هر یک از صرافی ها",
                     legend_loc=(1, 0.35),
                     title_font_size=title_font_size,
                     legend_font_size=legend_font_size,
                     legend_title=None,
                     colors=c)


    symbols, win, lose, profit = calculate_data(data)
    ax2.barh(symbols, win, width, color='green')
    ax2.barh(symbols, lose, width, left=win, color='red')
    ax2.get_xaxis().set_visible(False)
    ax2.spines['top'].set_visible(False)
    ax2.spines['bottom'].set_visible(False)
    ax2.spines['left'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    ax2.set_title(display_persian('درصد معاملات برنده و بازنده در جفت ارز های مختلف'), fontdict={'fontsize':title_font_size})
    ax2.tick_params(axis='y', labelsize=legend_font_size )


    create_pie_chart(ax3,
                     data=[data['numWinTrade'], data['numLoseTrade']],
                     labels=['Profit','Loss'],
                     title="درصد کل معاملات برنده و بازنده",
                     legend_loc=(1, 0.4),
                     title_font_size=title_font_size,
                     legend_font_size=legend_font_size,
                     legend_title=None,
                     colors=['green', 'red'])

    create_profit_loss_value_chart(ax4, 
                                   data,
                                   labels=symbols,
                                   title="مقدار سود و ضرر در هر جفت ارز",
                                   legend_loc=(1,1),
                                   title_font_size=title_font_size,
                                   legend_font_size=legend_font_size,
                                   colors=['green', 'red'],
                                   offset=0)


    create_pie_chart(ax5,
                     data=[data['numBuyPositions'], data['numSellPositions']],
                     labels=['Long','Short'],
                     title="درصد معاملات Long و Short",
                     legend_loc=(1, 0.4),
                     title_font_size=title_font_size,
                     legend_font_size=legend_font_size,
                     legend_title=None,
                     colors=['green', 'red'])

    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)

    return buf
