import os

from binance.client import Client
from pycoingecko import CoinGeckoAPI

MAKE_TRADE = False

CG = CoinGeckoAPI()

BinanceClient = Client(os.environ['BinanceApi'],os.environ['BinanceSecret'])

INDEX_COIN_COUNT = 10
STABLECOINS = ('usdt', 'usdc', 'busd', 'dai', 'ust', 'lusd', 'pax', 'fei', 'tusd', 'husd', 'usdn', 'susd', 'vai', 'usdp', 'frax', 'gusd', 'esd', 'usdx', 'seur', 'krt', 'eurs', 'musd', 'usdk', 'tryb', 'bac', 'dusd', 'ousd', 'dsd', 'bitcny', 'eosdt', 'mic', 'rsv', 'debase', 'onc', 'saud', 'bsd', 'sac', 'qusd', 'qc', 'usd', 'xdai', 'iron', 'usds', 'thkd', 'ebase', 'usnbt', 'bdo')
PRIVACY_COINS = ('xmr','dash','zec','dcr','dgb','zen','arrr','xvg','xhv','scrt','firo','mask','bcn','beam','grs','pivx','sero','dusk','oxen','dero','apl','grin','nav','trtl','part','zano','flux','onion','nix','eng','phr','btcz','prcy','ccx','ghost','daps','epic','sumo','alias','veil','zcl','zer','bc','msr','krb','hush','axe','crp','btcn','anc','dev','btcx','lithn','kurt','hatch','xfg','wscrt','aeon','hopr','bdx')
TRADING_QUOTE_ASSET = 'usdt'

DUST_AMOUNT = 1

MIN_ORDER_SIZE = 10
ORDER_SIZE_BUFFER = 1.01
ADJUST_MIN_ORDER_SIZE = MIN_ORDER_SIZE*ORDER_SIZE_BUFFER

TRADING_FEE = 0.001

# Apply a root to the marketcap so that it doesn't skew too much to large caps
# 1: true market cap weighting
# 0: even weighting
DOMINANCE_ADJUST = 0.4

def RebalancePortfolio():
    # Get the market data from the coingecko api
    marketData = CG.get_coins_markets(vs_currency='usd', per_page=250)

    # Get the exchange info from the binance api
    binanceData = BinanceClient.get_exchange_info()

    # Get account info from the binance api
    accountData = BinanceClient.get_account()
    accountBalanceUSD = CurrentAccountBalance(accountData, marketData)
    accountBalanceTotal = SumBalance(accountBalanceUSD)

    binanceValidCoins = GetValidBinanceTrades(binanceData)
    indexCoinCaps = GetIndexCoins(marketData, binanceValidCoins)
    totalMarketCap = GetTotalMarketCap(indexCoinCaps)
    indexCoinWeights = GetIndexWeighting(indexCoinCaps, totalMarketCap)
    
    indexCoinIdealPrices = GetIndexIdealPrices(indexCoinWeights, accountBalanceTotal)
    allocationDifferences = GetAllocationDifference(indexCoinIdealPrices, accountBalanceUSD)
    overweightedCoins = GetOverweightedCoins(allocationDifferences)
    underweightedCoins = GetUnderweightedCoins(allocationDifferences)

    """
    print('ACCOUNT BALANCE')
    for accountCoin in accountBalanceUSD:
        print(f"{accountCoin[0]} : ${accountCoin[1]:.2f}")
    print(f"TOTAL : ${accountBalanceTotal:.2f}")
    print()

    print('IDEAL ALLOCATION')
    for coinData in indexCoinWeights:
        print(f"{coinData[0]} : {coinData[1]*100:.2f}%")
    print()

    print('IDEAL PRICES')
    for coinData in indexCoinIdealPrices:
        print(f"{coinData[0]} : ${coinData[1]:.2f}")
    print()

    print("ALLOCATION DIFFERENCES")
    for coinData in allocationDifferences:
        print(f"{coinData[0]} : ${coinData[1]:.2f}")
    print()

    print('OVERWEIGHTED COINS')
    for coinData in overweightedCoins:
        print(f"{coinData[0]} : ${coinData[1]:.2f}")
    print()

    print('UNDERWEIGHTED COINS')
    for coinData in underweightedCoins:
        print(f"{coinData[0]} : ${coinData[1]:.2f}")
    print()
    """

    if MAKE_TRADE:
        # Sell overweighted assets for USDT
        SellOverweightedCoins(overweightedCoins, marketData)

        # Buy underweighted assets using USDT
        BuyUnderweightedCoins(underweightedCoins, marketData)

        accountData = BinanceClient.get_account()
        accountBalanceUSD = CurrentAccountBalance(accountData, marketData)
        accountBalanceTotal = SumBalance(accountBalanceUSD)

        """
        print()
        print('NEW ALLOCATION')
        for coinData in accountBalanceUSD:
            percentage = (coinData[1]/accountBalanceTotal)*100
            print(f"{coinData[0]} : {percentage:.2f}%")
        """

# Get the top non-stablecoin/privacycoins cryptos that would be used for the index portfolio
def GetIndexCoins(marketData, binanceVaildCoins):
    indexCoinCaps = []
    currentCoinCount = 0

    # Loop through all the coins descending order from market cap to find candidates for the index
    for coinData in marketData:

        # Return when the amount of needed coins in the index is reached
        if currentCoinCount == INDEX_COIN_COUNT:
            return indexCoinCaps

        # Filter out the stablecoins and privacy coins
        if coinData['symbol'] not in STABLECOINS and coinData['symbol'] not in PRIVACY_COINS and coinData['symbol'] in binanceVaildCoins:
            indexCoinCaps.append((coinData['symbol'], coinData['market_cap']))
            currentCoinCount += 1
    return indexCoinCaps

# Find coins that can be traded in binance
def GetValidBinanceTrades(binanceData):
    binanceValidCoins = []
    for tradingPair in binanceData['symbols']:
        if tradingPair['quoteAsset'].lower() == TRADING_QUOTE_ASSET:
            binanceValidCoins.append(tradingPair['baseAsset'].lower())
    return binanceValidCoins

# Add up all the market caps from the index coins
def GetTotalMarketCap(indexCoinData):
    totalMarketCap = 0
    for coinData in indexCoinData:

        # Apply a root to the coin's marketcap to avoid large cap dominance
        totalMarketCap += coinData[1]**DOMINANCE_ADJUST
    return totalMarketCap

# Calculate all the coin percentages in the portolio
def GetIndexWeighting(indexCoinData, totalMarketCap):
    indexCoinWeights = []
    for coinData in indexCoinData:
        indexCoinWeights.append((coinData[0], coinData[1]**DOMINANCE_ADJUST/totalMarketCap))
    return indexCoinWeights

# Gets the account balance in USD
def CurrentAccountBalance(accountData, marketData):
    accountBalances = []
    for coin in accountData['balances']:
        coinBalanceUSD = float(coin['free']) * CurrentCoinPrice(coin['asset'].lower(), marketData)
        if coinBalanceUSD > DUST_AMOUNT:
            accountBalances.append((coin['asset'].lower(), coinBalanceUSD))
    return accountBalances

# Get the current market price given the coin symbol
def CurrentCoinPrice(symbol, marketData):
    for coinData in marketData:
        if coinData['symbol'] == symbol:
            return float(coinData['current_price'])
    return 0

# Sum all the coin balanace in the account
def SumBalance(accountBalanceUSD):
    total = 0
    for coinBalance in accountBalanceUSD:
        total += coinBalance[1]
    return total

# Get the price of each asset in the new portfolio given the current account total
def GetIndexIdealPrices(indexCoinWeights, balanceTotal):
    indexCoinIdealPrices = []
    for coinWeight in indexCoinWeights:
        indexCoinIdealPrices.append((coinWeight[0],coinWeight[1]*balanceTotal))
    return indexCoinIdealPrices

# Get the differece between the current account portfolio and the new portfolio
def GetAllocationDifference(indexCoinIdealPrices, accountBalances):
    allocationDifferencesAccount = []
    for accountCoin in accountBalances:
        if accountCoin[0] not in STABLECOINS and accountCoin[0] not in PRIVACY_COINS:
            difference = GetPriceFromIdealIndex(accountCoin[0],indexCoinIdealPrices) - accountCoin[1]
            allocationDifferencesAccount.append((accountCoin[0],difference))     
    
    allocationDifferencesIndex = []
    for indexCoin in indexCoinIdealPrices:
        if indexCoin[0] not in STABLECOINS and accountCoin[0] not in PRIVACY_COINS:
            difference = indexCoin[1] - GetPriceFromAccount(indexCoin[0],accountBalances)
            allocationDifferencesIndex.append((indexCoin[0],difference))   

    allocationDifferences = list(set(allocationDifferencesAccount).union(allocationDifferencesIndex))

    return allocationDifferences

def GetPriceFromAccount(symbol, accountBalances):
    for accountCoin in accountBalances:
        if accountCoin[0] == symbol:
            return accountCoin[1]
    return 0

# Get the price of a specific coin from the ideal index
def GetPriceFromIdealIndex(symbol, indexCoinIdealPrices):
    for indexCoin in indexCoinIdealPrices:
        if indexCoin[0] == symbol:
            return indexCoin[1]
    return 0

# Get coins that are currently overweighted
def GetOverweightedCoins(allocationDifferences):
    overweightedCoins = []
    for coinData in allocationDifferences:
        if -coinData[1] > ADJUST_MIN_ORDER_SIZE:
            overweightedCoins.append((coinData[0],-coinData[1]))
    return overweightedCoins

# Get coins that are currently underweighted
def GetUnderweightedCoins(allocationDifferences):
    underweightedCoins = []
    for coinData in allocationDifferences:
        if coinData[1] > ADJUST_MIN_ORDER_SIZE:
            underweightedCoins.append((coinData[0],coinData[1]))
    return underweightedCoins

# Sell overweighted coins so that it matches the ideal allocation
def SellOverweightedCoins(overweightedCoins, marketData):
    for coinData in overweightedCoins:
        tradingPair = (coinData[0]+TRADING_QUOTE_ASSET).upper()
        amount = coinData[1] / CurrentCoinPrice(coinData[0],marketData)
        convertedAmount = ConvertToStepSize(tradingPair,amount)
        #print(f"SELL: {tradingPair} : {convertedAmount}")
        BinanceClient.order_market_sell(symbol = tradingPair, quantity = convertedAmount)

# Buy underweighted coins so that it matches the ideal allocation
def BuyUnderweightedCoins(underweightedCoins, marketData):
    for i in range(0,len(underweightedCoins)):
        coinData = underweightedCoins[i]
        tradingPair = (coinData[0]+TRADING_QUOTE_ASSET).upper()
        amount = 0

        # Buy the calulated amount on all buy the last coin
        # Buy the maximum possible amount given the account balance on the last coin
        # This is done because the weighted is calculated based on the coinGecko API but binance could have different prices
        if(i < len(underweightedCoins)-1):
            amount = coinData[1] / CurrentCoinPrice(coinData[0],marketData)
        else:
            newAccountData = BinanceClient.get_account()
            amount = GetCoinAccountBalance(TRADING_QUOTE_ASSET,newAccountData) / BinanceGetLatestPrice(tradingPair)
            amount -= amount*TRADING_FEE
        convertedAmount = ConvertToStepSize(tradingPair,amount)
        if(convertedAmount > 0):
            #print(f"BUY: {tradingPair} : {convertedAmount}")
            BinanceClient.order_market_buy(symbol = tradingPair, quantity = convertedAmount)

# Get the current trading price on binance
def BinanceGetLatestPrice(tradingPair):
    binanceTickers = BinanceClient.get_symbol_ticker()
    for ticker in binanceTickers:
        if ticker['symbol'] == tradingPair:
            return float(ticker['price'])
    return 0

# Convert the buy/sell amount to the right exchange step size so that it can be executed on binance
def ConvertToStepSize(tradingPair, amount):
    info = BinanceClient.get_symbol_info(tradingPair)
    stepSize = float(info['filters'][2]['stepSize'])
    converted = (amount//stepSize)*stepSize
    formatted = float(f'{converted:g}')
    return formatted

# Get the current balance of a specific coin in the account
def GetCoinAccountBalance(symbol, accountData):
    for coinData in accountData['balances']:
        if coinData['asset'].lower() == symbol:
            return float(coinData['free'])
    return 0