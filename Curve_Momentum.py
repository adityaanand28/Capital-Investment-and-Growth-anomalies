from blueshift.finance import commission, slippage
from blueshift.api import(  symbol,
                            order_target_percent,
                            order_target,
                            order_target_value,
                            set_commission,
                            set_slippage,
                            schedule_function,
                            date_rules,
                            time_rules,
                            order,
                        )
import numpy as np
from scipy.signal import savgol_filter
from blueshift.library.technicals.indicators import bollinger_band, ema

def initialize(context):
    """
        A function to define things to do at the start of the strategy
    """
    # universe selection
    context.securities = [symbol('NIFTY-II'), symbol('NIFTY-I')]

    # define strategy parameters
    context.params = {'indicator_lookback':375,
                      'indicator_freq':'1m',
                      'buy_signal_threshold':0.5,
                      'sell_signal_threshold':-0.5,
                      'SMA_period_short':15,
                      'SMA_period_long':60,
                      'BBands_period':300,
                      'trade_freq':5,
                      'leverage':1}

    # variables to track signals and target portfolio
    context.signals = dict((security,0) for security in context.securities)
    context.target_position = dict((security,0) for security in context.securities)
    context.k = 0
    context.qt = 0

    context.exponentialavg = dict((security,[]) for security in context.securities)
    context.iterator = dict((security, 0) for security in context.securities)

    # set trading cost and slippage to zero
    set_commission(commission.PerShare(cost=0.0, min_trade_cost=0.0))
    set_slippage(slippage.FixedSlippage(0.0005))
    
    freq = int(context.params['trade_freq'])
    schedule_function(run_strategy, date_rules.every_day(),
                      time_rules.every_nth_minute(freq))
    
    schedule_function(stop_trading, date_rules.every_day(),
                      time_rules.market_close(minutes=30))
    
    context.trade = True

def before_trading_start(context, data):
    context.trade = True
    
def stop_trading(context, data):
    context.trade = False

def run_strategy(context, data):
    """
        A function to define core strategy steps
    """
    if not context.trade:
        return
    
    generate_signals(context, data)
    generate_target_position(context, data)

def logic(pivot, points, context, security):
    count = 0
    flag = 0
    maxx = []
    maxy = []
    minx = []
    miny = []

    for i in range(len(pivot)-1, -1, -1):
        if (pivot[i] == 1 and flag == 0):
            m = i + context.iterator[security] - 375
            if (m >0):
                if (context.exponentialavg[m] - points[i] > 0.001 * points[i] ):
                    return 0,0
            minx.append(i)
            miny.append(points[i])
            count += 1
            flag = 1
            if (count ==5):         
                if (miny[1] < miny[0] and miny[1] < miny[2]):
                    avgmin = (miny[0] + miny[2])/2
                    avgmax = (maxy[0] + maxy[1])/2
                    if (abs(miny[0] - avgmin) <= (0.04 * avgmin) and abs(miny[2] - avgmin) <= (0.04 * avgmin) and abs(maxy[0] - avgmax) <= (0.04 * avgmax) and abs(maxy[1] - avgmax) <= (0.04 * avgmax)):
                        slope = (maxy[0] - maxy[1]) / (maxx[0] - maxx[1])
                        c = maxy[0] - (slope * maxx[0])
                        y = (slope * 375) + c
                        y2 = (slope * minx[1]) + c - miny[1]
                        return y, y2
        elif (pivot[i] == 2 and flag == 1):
            m = i + context.iterator[security] - 375
            if (m >0):
                if (context.exponentialavg[security][m] - points[i] > 0.01 * points[i] ):
                    return 0,0
            maxx.append(i)
            maxy.append(points[i])
            count +=1
            flag =0
        elif (pivot[i] == 2 or pivot[i] == 1):
            return 0,0

    return 0,0


def vix_val(px, params, context, security):

    pivot = []
    month_diff = len(px) // 30      #df shape is (249, 8)
    if month_diff == 0:
        month_diff = 1
    smooth = int(2*month_diff + 3)
    points = savgol_filter(px, smooth , 3)
    ind = ema(px , 150)
    context.exponentialavg[security].append(ind)
    context.iterator[security] = context.iterator[security] + 1
    for i in range(6, len(points)-6):
        pividlow=1
        pividhigh=1
        for j in range(i-6, i+7):
            if(points[i]>points[j]):
                pividlow=0
            if(points[i]<points[j]):
                pividhigh=0
        if pividlow and pividhigh:
            pivot.append(3)
        elif pividlow:
            pivot.append(1)
        elif pividhigh:
            pivot.append(2)
        else:
            pivot.append(0)
    (y, y2) = logic(pivot, points, context, security)
    y2 = y + y2
    if ((y - px[-1]) < 0 and (px[-1] - y) < 0.005 * px[-1]):
        return 1
    elif ((px[-1] - y2) < 0.005 * px[-1] or (y2 - px[-1]) < 0.005 * px[-1]):
        return -1
    else:   
        return 0

def vix_bbands(px, params):
    upper, mid, lower = bollinger_band(px,params['BBands_period'])
    if upper - lower == 0:
        return 0
    
    ind2 = ema(px, params['SMA_period_short'])
    ind3 = ema(px, params['SMA_period_long'])
    last_px = px[-1]
    dist_to_upper = 100*(upper - last_px)/(upper - lower)

    if dist_to_upper > 95:
        return -1
    elif dist_to_upper < 5:
        return 1
    elif dist_to_upper > 40 and dist_to_upper < 60 and ind2-ind3 < 0:
        return -1
    elif dist_to_upper > 40 and dist_to_upper < 60 and ind2-ind3 > 0:
        return 1
    else:
        return 0
   
def vix_bullish(px, params):
    close = px.close.values[-1]
    prev_close = px.close.values[-2]
    open = px.open.values[-1]
    prev_open = px.open.values[-2]

    if ((close >= prev_open > prev_close) and (close > open) and (prev_close >= open) and (close - open > prev_open - prev_close)):
        return 1
    if ((open >= prev_close > prev_open) and (open > close) and (prev_open >= close) and (open - close > prev_close - prev_open)):
        return -1
    return 0

def vix_harami(px, params):
    close = px.close.values[-1]
    prev_close = px.close.values[-2]
    open = px.open.values[-1]
    prev_open = px.open.values[-2]

    if ((prev_open > prev_close) and (prev_close <= open < close <= prev_open) and ((close - open) < (prev_open - prev_close))):
        return 1
    if ((prev_close > prev_open) and (prev_open <= close < open <= prev_close) and ((open - close) < (prev_close - prev_open))):
        return -1
    return 0

def vix_marubozu(px, params):
    close = px.close.values
    high = px.high.values
    low = px.low.values
    open = px.open.values

    if(len(close)<1):
        return 0
        
    if (close[-1] > open[-1] and high[-1] == close[-1] and low[-1] == open[-1]):
        return 1
    elif (close[-1] < open[-1] and high[-1] == open[-1] and low[-1] == close[-1]):
        return -1
    else:
        return 0

def generate_target_position(context, data):
    """
        A function to define target portfolio
    """
    num_secs = len(context.securities) - 1

    security = context.securities[1]
    overall = context.portfolio.portfolio_value
    curr_price = data.current(context.securities[1], 'close')
    idc = context.account.net_exposure
    na_cash = overall - idc

    # Next 2 lines are the method to get_curr_time
    px = data.history(context.securities[0], ['open', 'high'], 2, '1m')
    curr_time = px.index[-1]

    if (context.k==0) and (context.signals[security] > context.params['buy_signal_threshold']):
        context.qt = ((overall // curr_price) // 50)*50
        context.k = 1
        order_target(security, context.qt)
        # print(f"{curr_time},{context.portfolio.portfolio_value},{context.portfolio.positions_exposure},{context.portfolio.cash},{context.portfolio.starting_cash},{context.portfolio.positions_value},{context.portfolio.pnl},{context.portfolio.start_date},1,{context.qt}")
        # print(f"{curr_time},{context.account.margin},{context.account.leverage},{context.account.gross_leverage},{context.account.net_leverage},{context.account.gross_exposure},{context.account.long_exposure},{context.account.short_exposure},{context.account.net_exposure},{context.account.net_liquidation},{context.account.total_positions_exposure},{context.account.available_funds},{context.account.total_positions_value}")

        # print(curr_time, overall, idc, na_cash, context.k, context.qt, 1)

    elif (context.k==0) and (context.signals[security] < context.params['sell_signal_threshold']):
        context.qt = -1*(((overall // curr_price) // 50)*50)
        context.k = -1
        order_target(security, context.qt)
        # print(f"{curr_time},{context.portfolio.portfolio_value},{context.portfolio.positions_exposure},{context.portfolio.cash},{context.portfolio.starting_cash},{context.portfolio.positions_value},{context.portfolio.pnl},{context.portfolio.start_date},2,{context.qt}")
        # print(f"{curr_time},{context.account.margin},{context.account.leverage},{context.account.gross_leverage},{context.account.net_leverage},{context.account.gross_exposure},{context.account.long_exposure},{context.account.short_exposure},{context.account.net_exposure},{context.account.net_liquidation},{context.account.total_positions_exposure},{context.account.available_funds},{context.account.total_positions_value}")

        # print(curr_time, overall, idc, na_cash, context.k, context.qt, 1)

    elif (context.k>0) and (context.signals[security] < context.params['sell_signal_threshold']):
        context.qt = 0
        context.k = 0
        order_target(security, context.qt)
        # print(f"{curr_time},{context.portfolio.portfolio_value},{context.portfolio.positions_exposure},{context.portfolio.cash},{context.portfolio.starting_cash},{context.portfolio.positions_value},{context.portfolio.pnl},{context.portfolio.start_date},3,{context.qt}")
        # print(f"{curr_time},{context.account.margin},{context.account.leverage},{context.account.gross_leverage},{context.account.net_leverage},{context.account.gross_exposure},{context.account.long_exposure},{context.account.short_exposure},{context.account.net_exposure},{context.account.net_liquidation},{context.account.total_positions_exposure},{context.account.available_funds},{context.account.total_positions_value}")

        # print(curr_time, overall, idc, na_cash, context.k, context.qt, 1)

    elif (context.k<0) and (context.signals[security] > context.params['buy_signal_threshold']):
        context.qt = 0
        context.k = 0
        order_target(security, context.qt)
        # print(f"{curr_time},{context.portfolio.portfolio_value},{context.portfolio.positions_exposure},{context.portfolio.cash},{context.portfolio.starting_cash},{context.portfolio.positions_value},{context.portfolio.pnl},{context.portfolio.start_date},4,{context.qt}")
        # print(f"{curr_time},{context.account.margin},{context.account.leverage},{context.account.gross_leverage},{context.account.net_leverage},{context.account.gross_exposure},{context.account.long_exposure},{context.account.short_exposure},{context.account.net_exposure},{context.account.net_liquidation},{context.account.total_positions_exposure},{context.account.available_funds},{context.account.total_positions_value}")

        # print(curr_time, overall, idc, na_cash, context.k, context.qt, 1)



def generate_signals(context, data):
    """
        A function to define define the signal generation
    """
    try:
        # price_data = data.history(context.securities[1:], ['open','high','low','close'],
        #     context.params['indicator_lookback'], context.params['indicator_freq'])
        price_data_vix = data.history(context.securities[0], ['open','high','low','close'],
            context.params['indicator_lookback'], context.params['indicator_freq'])
    except:
        return

    for security in context.securities[1:]:
        context.signals[security] = signal_function(context, price_data_vix, context.params, security)

def signal_function(context, px_vix, params, security):
    """
        The main trading logic goes here, called by generate_signals above
    """
    vix = px_vix

    # Specifying Stoploss Condition 
    curr_time = vix.index[-1].time()
    hour = curr_time.hour
    minute = curr_time.minute
    stoploss = 0

    if (hour < 10) or (hour == 10 and minute <= 30):
        stoploss = 0.05
    elif ((hour == 10 and minute > 30) or hour > 10) and (hour < 13 or (hour == 13 and minute <= 30)):
        stoploss = 0.05
    elif (hour == 13 and minute > 30) or (hour > 13):
        stoploss = 0.05

    # # Checking 
    positions = context.portfolio.positions

    quant = 0
    pricee = 0
    pnl = 0
    position = -1
    for key in positions.keys():
        if positions[key].position_side == 0: # LONG
            quant += positions[key].buy_quantity
            pricee = positions[key].buy_price
            pnl += positions[key].unrealized_pnl
            position = 0

        if positions[key].position_side == 1: # SHORT
            quant += positions[key].sell_quantity
            pricee = positions[key].sell_price
            pnl += positions[key].unrealized_pnl
            position = 1
    

    # # Checking for Stoploss
    if (quant != 0 and pricee != 0) and (pnl/(quant*pricee)) <= (-1*stoploss):
        if position == 0: # LONG
            return -1
        if position == 1: # SHORT
            return 1

    take_profit = 0.10
    # # Applying Take Profit
    if (quant != 0 and pricee != 0) and (pnl/(quant*pricee)) >= take_profit:
        if position == 0: # LONG
            return -1
        if position == 1: # SHORT
            return 1
            
    return -vix_bullish(vix, params)