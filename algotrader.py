#!/home/entropy/anaconda3/bin/python3


"""

Simplified Inverse Head and Shoulders Day Trader Strategy

Results:
    For highest volume traded stocks on 5/29
    STOCKS: GE, BAC, F, UBER, MRO, NCLH, AMD, UAL, SIRI, ZNGA, COTY, ABEV,
            OXY, AAL, NLY, SNAP, WFC, DAL, KO, CCL 

    On 5/29 only, made 0.89%, SPY did ~0.63%:
    $100889 Total Assets, profitLimit = .02, lossLimit = -0.02

    From 5/8 to 5/29, made 9.47%, SPY did ~4.06%
    $109469 Total Assets, profitLimit = .02, lossLimit = -0.02

    Analyzed ~100 different profit/loss limits and settled on .02/-0.02

"""

from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.techindicators import TechIndicators
from matplotlib.pyplot import figure
import matplotlib.pyplot as plt
import requests
from bs4 import BeautifulSoup
import re
import pprint

apiKey = 'IFP09U6GQ81JV2PE'
tradingLogFile = "trades.log"
SP500TickersFile = "SP500tickers.txt"
pp = pprint.PrettyPrinter(indent=4)
ts = TimeSeries(apiKey, output_format="pandas")


def createSP500File(fName):
    """
    This webscrapes wikipedia to write the tickers in the S&P500 to file

    Args:
        fName: This is the file name where the tickers are saved on disk

    Returns:
        Nothing
    """
    #Get a list of all stock in the S&P500
    sp500Url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    page = requests.get(sp500Url)
    soup = BeautifulSoup(page.content, 'html.parser')
    allLinks = soup.find_all('a', class_="external text")

    tickers = []
    for link in allLinks:

        match = re.search(r"[A-Z]+", link.get_text())
        if match:
            tickers.append(match.group(0))
            if match.group(0) == 'ZTS':
                break

    f = open(fName, "a")
    for ticker in tickers:
        f.write(ticker+"\n")
    f.close()
    print("File '" + fName + "' has been created.")


def getSP500Tickers(fName):
    """
    This function gets the tickers from a file

    Args:
        fName: This is the file name where the tickers are saved on disk

    Returns:
        tickerSegments: A list of lists breaking the ~500 stocks into 5 segments
    """
    #Get S&P500 tickers
    tickers = []
    #We can only make ~100 calls/minute, split the stocks up into groups of ~100
    tickerSegments = [[],[],[],[],[]]
    f = open(fName, "r")
    count = 0
    segment = 0

    for line in f:

        line = line.strip("\n") 
        tickerSegments[segment].append(line)
        if count == 101:
            count = 0
            segment += 1 
        count += 1
    f.close()

    return tickerSegments


def getInterestingStocks():
    """
    This function webscrapes yahoo finance to discover the most active stocks
    of the day

    Args:
        None
    
    Returns:
        A tuple: 
            topStockChanges: stocks that have the largest daily % change
            topStockVolume: stocks that have the largest daily volume traded
    """
    #Get a list of all volatile stock for today
    activeStocks1 = "https://finance.yahoo.com/most-active/?offset=0&count=100"
    page1 = requests.get(activeStocks1)
    soup1 = BeautifulSoup(page1.content, 'html.parser')
    rows1 = soup1.find_all('tr', class_="simpTblRow")

    activeStocks2= "https://finance.yahoo.com/most-active/?count=100&offset=100"
    page2 = requests.get(activeStocks2)
    soup2 = BeautifulSoup(page2.content, 'html.parser')
    rows2 = soup2.find_all('tr', class_="simpTblRow")

    stocks = []
    for row in rows1:
        stocks.append( 
            {"ticker" : row.find_all('a')[0].get_text(),
             "pctChange" : float(row.find_all('td')[4].get_text().strip("%+-")),
             "volume" : float(row.find_all('td')[5].get_text().strip("M"))
            } 
        )

    for row in rows2:
        stocks.append( 
            {"ticker" : row.find_all('a')[0].get_text(),
             "pctChange" : float(row.find_all('td')[4].get_text().strip("%+-")),
             "volume" : float(row.find_all('td')[5].get_text().strip("M"))
            } 
        )

    sortedStocksChange = sorted(
        stocks, reverse=True, 
        key=lambda item: item["pctChange"])

    topStockChanges = []
    for index in range(0,20):

        topStockChanges.append(sortedStocksChange[index])

    sortedStocksVolume = sorted(
        stocks, reverse=True, 
        key=lambda item: item["volume"])

    topStockVolume = []
    for index in range(0,20):

        topStockVolume.append(sortedStocksVolume[index])

    return (topStockChanges, topStockVolume)



def frange(start, stop=None, step=None):
    """
    This function provides a way to loop over floats as range() does not
    From: https://pynative.com/python-range-for-float-numbers/

    Args:
        start: The beginning of the range to loop
        stop: The end of the range to loop, not inclusive
        step: The incremental interval the loop adjusts by

    Returns:
        This is a generator and the next number in sequence is returned
    """
    # if stop and step argument is None set start=0.0 and step = 1.0
    start = float(start)
    if stop == None:
        stop = start + 0.0
        start = 0.0
    if step == None:
        step = 1.0

    count = 0
    while True:
        temp = float(start + count * step)
        if step > 0 and temp >= stop:
            break
        elif step < 0 and temp <= stop:
            break
        yield temp
        count += 1


def headShouldersRatioResearch():
    """
    This function studies the variable profit and loss limits to find the best
    thresholds to buy and sell at to maximize alpha. Largest volume stocks
    are targeted as volatility may be increased as many buy and sell and this
    strategy counts on many small purchases and sales throughout the day

    Args:
        None

    Returns:
        None
    """
    (largestChanges, largestVolumes) = getInterestingStocks()

    tickers = largestVolumes

    for profitLimit in frange(.005, .065, .005):
        for lossLimit in frange(-.02, -.11, -.01):
            simulation = trading(cashOnHand=100000.00, logName=tradingLogFile,
                                 enableLog=0)

            for tickerDict in tickers:

                ticker = tickerDict["ticker"]
                tickerDataIntraPd, meta = ts.get_intraday(symbol=ticker,
                                                          interval="5min", 
                                                          outputsize="full")

                simulation.simulateDay(ticker, tickerDataIntraPd, profitLimit,
                                       lossLimit)

            print("ProfitLimit: ",profitLimit,"LossLimit: ",lossLimit)
            simulation.printTotalAssets()


class trading():

    def __init__(self, cashOnHand=0, logName="trading.log", enableLog=0):
        self.money = cashOnHand 
        self.positions = {} 
        self.logFile = logName 
        self.enableLog = enableLog 

    def buy(self, ticker, price, cash):
        """
        This will simulate a purchase of stock

        Args:
            ticker: The stock symbol to buy
            price: The price at which to purchase the stock
            cash: How much cash we're limiting our purchase to

        Returns:
            Nothing
        """
        sharesPurchased = int( cash / price)

        #If we already have shares of this stock, update the amount and
        #average the price
        if ticker in self.positions:
            self.positions[ticker] = [ 
                 sharesPurchased + self.positions[ticker][0], 
                 round((price + self.positions[ticker][1])/2, 4)]

        else:
            self.positions[ticker] =  [sharesPurchased, price]

        #deduct amount of cash allotted for purchase and add back the remainder
        self.money -= cash
        self.money += round(cash - (sharesPurchased * price), 4)

        text = "Buying \t" + str(sharesPurchased) + " shares of " 
        text += str(ticker)+" at \t"+str(price)+"\n"
        text += "Cash: "+str(self.money)+"\n"
        text += "Positions: "+str(self.positions)+"\n"

        print(text)

        if self.enableLog:
            self.log(text)



    def sell(self, ticker, price):
        """
        This will simulate a selling of stock

        Args:
            ticker: The stock symbol to sell
            price: The price at which we're selling the stock

        Returns:
            Nothing
        """
        sharesSold = self.positions[ticker][0]
        self.money += round(self.positions[ticker][0] * price, 4)
        self.positions.pop(ticker)

        text = "Selling " + str(sharesSold) + " shares of " 
        text += str(ticker)+" at \t"+str(price)+"\n"
        text += "Cash: "+str(self.money)+"\n"
        text += "Positions: "+str(self.positions)+"\n"

        print(text)

        if self.enableLog:
            self.log(text)



    def log(self, text):
        """
        This will write data to a log file

        Args:
            text: The text that we will write to the file
    
        Returns:
            Nothing
        """
        f = open(self.logFile, "a")
        f.write(text)
        f.close()


    def print(self):
        """
        Print cash on hand, current stock positions and the amount of total
        assets that we own

        Args:
            None
        
        Returns:
            Nothing
        """
        print("\nCash: ",self.money)
        print("Positions: ")
        pp.pprint(self.positions)

        totalAssets = self.money 

        for ticker, stock in self.positions.items():

            tickerDataPd, meta = ts.get_intraday(symbol=ticker, 
                                 interval="5min", outputsize="compact")

            totalAssets += stock[0] * tickerDataPd['4. close'][0]

        print("Total Assets: ", totalAssets)


    def printTotalAssets(self):
        """
        Print out the total assets only
        
        Args:
            None
        
        Returns:
            Nothing
        """    
        totalAssets = self.money

        for ticker, stock in self.positions.items():

            tickerDataPd, meta = ts.get_intraday(symbol=ticker,
                                 interval="5min", outputsize="compact")

            totalAssets += stock[0] * tickerDataPd['4. close'][0]

        print("Total Assets: ", totalAssets)



    def simulateDay(self, ticker, pdData, profitLimit=.005, lossLimit=-.05):
        """
        This function takes all the stock data provided and runs the strategy
        on the data to see what profit/loss would have occured. A simplified
        version of inverse head and shoulders is implemented.  More tweaking
        could probably increase accuracy.

        Args:
            ticker: Deprecated
            pdData: All the stock data we'll be running the strategy over
            profitLimit: How high the stock will go in reference to our 
                         purchase prince before we sell
            lossLimit: How low the stock will go in reference to ourt 
                       purchase price before we sell

        Returns:
            Nothing
        """
        closeData = pdData['4. close'] 

        fridaysData = pdData[:"2020-05-29"]
        fridaysCloseData = fridaysData['4. close']
        fridaysCloseReversed = fridaysCloseData[::-1]

        trend = 0
        lastClose = 0
        streak = 0
        lastStreak = 0
        localMax = 0
        localMin = 0
        localMaxHits = 0

        #for 5/29 only
        #for closePrice in fridaysCloseReversed:
        #for dates since 5/8
        for closePrice in pdData['4. close'][::-1]:

            if ticker in self.positions:

                buyPrice = self.positions[ticker][1]
                profitRatio = ((closePrice - buyPrice) / buyPrice)

                if ( ( trend == -1 and profitRatio >= profitLimit ) or
                   ( profitRatio <= lossLimit) ):
                    self.sell(ticker, closePrice)

            if lastClose < closePrice:
                if trend == 1:
                    streak += 1
                else:
                    trend = 1
                    lastStreak = streak
                    streak = 0
                    localMax = closePrice 
                    localMaxHits += 1 
                
            elif lastClose > closePrice:
                if trend == -1:
                    streak += 1
                else:
                    trend = -1
                    lastStreak = streak
                    streak = 0
                    localMin = closePrice

            
            if localMaxHits >= 4:
                if ticker not in self.positions:
                    self.buy(ticker, closePrice, self.money/10)

                localMaxHits = 0

            lastClose = closePrice

        """
        figure(num=None, figsize=(15, 6), dpi=80, facecolor='w', edgecolor='k')
        fridaysCloseData.plot()
        plt.tight_layout()
        plt.grid()
        plt.show()
        """


def main():

    #headShouldersRatioResearch()
    #createSP500File(SP500TickersFile)
    #segmentedSP500Tickers = getSP500Tickers(SP500TickersFile)
    
    simulation = trading(cashOnHand=100000.00, logName=tradingLogFile, 
                         enableLog=0)

    (largestChanges, largestVolumes) = getInterestingStocks() 

    tickers = largestVolumes 

    for tickerDict in tickers:

        ticker = tickerDict["ticker"]

        tickerDataIntraPd, meta = ts.get_intraday(symbol=ticker, 
                                                  interval="5min", 
                                                  outputsize="full")

        profitLimit = 0.02
        lossLimit = -0.02
        simulation.simulateDay(ticker, tickerDataIntraPd, 
                               profitLimit, lossLimit)
    simulation.print()

    """
    figure(num=None, figsize=(15, 6), dpi=80, facecolor='w', edgecolor='k')
    tickerDataIntraPd['4. close'].plot()
    plt.tight_layout()
    plt.grid()
    plt.show()
    """


if __name__ == "__main__":
    main()






