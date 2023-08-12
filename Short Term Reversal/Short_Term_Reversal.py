"""
    Title: Buy and Hold (NSE)
    Description: This is a long only strategy which rebalances the 
        portfolio weights every month at month start.
    Style tags: Systematic
    Asset class: Equities, Futures, ETFs, Currencies and Commodities
    Dataset: NSE
"""
from blueshift.api import(    symbol,
                            order_target_percent,
                            schedule_function,
                            date_rules,
                            time_rules,
                       )
import pandas as pd
def initialize(context):
    """
        A function to define things to do at the start of the strategy
    """
    
    # universe selection
    context.long_portfolio = [
                               symbol('ACC'),symbol('ADANIENT'),symbol('ADANIGREEN'),symbol('ADANIPORTS'),symbol('ATGL'),symbol('ADANITRANS'),symbol('AMBUJACEM'),symbol('APOLLOHOSP'),symbol('ASIANPAINT'),symbol('DMART'),symbol('AXISBANK'),symbol('BAJFINANCE'),symbol('BAJAJFINSV'),symbol('BAJAJHLDNG'),symbol('BANDHANBNK'),symbol('BANKBARODA'),symbol('BERGEPAINT'),symbol('BEL'),symbol('BPCL'),symbol('BHARTIARTL'),symbol('BIOCON'),symbol('BOSCHLTD'),symbol('BRITANNIA'),symbol('CHOLAFIN'),symbol('CIPLA'),symbol('COALINDIA'),symbol('COLPAL'),symbol('DLF'),symbol('DABUR'),symbol('DIVISLAB'),symbol('DRREDDY'),symbol('EICHERMOT'),symbol('NYKAA'),symbol('GAIL'),symbol('GLAND'),symbol('GODREJCP'),symbol('GRASIM'),symbol('HCLTECH'),symbol('HDFCAMC'),symbol('HDFCBANK'),symbol('HDFCLIFE'),symbol('HAVELLS'),symbol('HEROMOTOCO'),symbol('HINDALCO'),symbol('HAL'),symbol('HINDUNILVR'),symbol('HDFC'),symbol('ICICIBANK'),symbol('ICICIGI'),symbol('ICICIPRULI'),symbol('ITC'),symbol('IOC'),symbol('IRCTC'),symbol('INDUSTOWER'),symbol('INDUSINDBK'),symbol('NAUKRI'),symbol('INFY'),symbol('INDIGO'),symbol('JSWSTEEL'),symbol('KOTAKBANK'),symbol('LTIM'),symbol('LT'),symbol('LICI'),symbol('MARICO'),symbol('MARUTI'),symbol('MPHASIS'),symbol('MUTHOOTFIN'),symbol('NTPC'),symbol('NESTLEIND'),symbol('ONGC'),symbol('PAYTM'),symbol('PIIND'),symbol('PIDILITIND'),symbol('POWERGRID'),symbol('PGHH'),symbol('RELIANCE'),symbol('SBICARD'),symbol('SBILIFE'),symbol('SRF'),symbol('MOTHERSON'),symbol('SHREECEM'),symbol('SIEMENS'),symbol('SBIN'),symbol('SUNPHARMA'),symbol('TCS'),symbol('TATACONSUM'),symbol('TATAMOTORS'),symbol('TATAPOWER'),symbol('TATASTEEL'),symbol('TECHM'),symbol('TITAN'),symbol('TORNTPHARM'),symbol('UPL'),symbol('ULTRACEMCO'),symbol('VEDL'),symbol('WIPRO'),symbol('ZOMATO'),
                             ]
    context.stocks=[]
    # Call rebalance function on the first trading day of each month after 2.5 hours from market open
    schedule_function(rebalance,
                    date_rules.month_start(days_offset = 0),
                    time_rules.market_open(hours = 1, minutes = 5))


def rebalance(context,data):
    """
        A function to rebalance the portfolio, passed on to the call
        of schedule_function above.
    """

    if(context.stocks):
        for sell_stocks in context.stocks:
            order_target_percent(sell_stocks,0)
            # print("Sell", sell_stock)
        context.stocks.clear()
    
    stock_data = data.history(context.long_portfolio, 'open', 30, "1d")
    # print(stock_data)
    #     for asset in context.long_portfolio:
    #     print(asset)
    # print(stock_data)
        
    

    stock_data = stock_data.append(stock_data.max(), ignore_index=True)
    diff_stock = (stock_data.iloc[-1] - stock_data.iloc[-2])/stock_data.iloc[-1]
    stock_data = stock_data.append(diff_stock, ignore_index=True)
    stock_data = stock_data.sort_values(by=stock_data.index[-1], axis=1, ascending=False)
    context.stocks = stock_data.columns[:5].tolist()
    print(context.stocks)
    for buy_stock in context.stocks:
        # print("Buy", buy_stock)
        order_target_percent(buy_stock, 2.0/10)   
        

    
