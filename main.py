import ccxt
import os
import time
import statistics
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configurações
DRY_RUN = False  # Real trading mode enabled
TIMEFRAME = '1h'  # 1-hour candlesticks for analysis
SHORT_MA = 5      # Short-term Simple Moving Average period
LONG_MA = 20      # Long-term Simple Moving Average period
CHECK_INTERVAL = 60  # Check interval in seconds

# Configurações de saldo em BRL - VALORES REDUZIDOS PARA TESTES REAIS
INITIAL_BALANCE_BRL = 20.0   # Saldo inicial em reais (reduzido para testes)
MIN_TRADE_AMOUNT_BRL = 1.0   # Valor mínimo por operação em reais (reduzido para testes)

# Converter para USD (será calculado dinamicamente)
def get_initial_balance_usd():
    return INITIAL_BALANCE_BRL / get_usd_to_brl_rate()

def get_trade_amount_usd():
    return MIN_TRADE_AMOUNT_BRL / get_usd_to_brl_rate()

# Global variables for portfolio tracking (will be initialized in main)
portfolio_balance = 0.0
portfolio_holdings = {}  # {symbol: {'amount': float, 'avg_price': float}}
total_trades = 0
successful_trades = 0

def get_usd_to_brl_rate():
    """Get current USD to BRL exchange rate"""
    try:
        response = requests.get('https://open.er-api.com/v6/latest/USD', timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data['rates']['BRL']
        else:
            # Fallback rate if API fails
            return 5.2
    except Exception as e:
        print(f"[WARNING] Failed to fetch USD/BRL rate: {e}. Using fallback rate.")
        return 5.2

def usd_to_brl(usd_amount):
    """Convert USD amount to BRL"""
    rate = get_usd_to_brl_rate()
    return usd_amount * rate

def format_currency(amount, currency='USD'):
    """Format currency with proper symbols"""
    if currency == 'USD':
        return f"${amount:,.2f}"
    elif currency == 'BRL':
        return f"R${amount:,.2f}"
    else:
        return f"{amount:,.2f} {currency}"

def update_portfolio(symbol, action, amount, price):
    """Update portfolio holdings and balance"""
    global portfolio_balance, portfolio_holdings, total_trades, successful_trades
    
    base_currency = symbol.split('/')[0]
    
    if action == "BUY":
        total_cost = amount * price
        if portfolio_balance >= total_cost:
            portfolio_balance -= total_cost
            
            if base_currency in portfolio_holdings:
                # Update average price
                current_amount = portfolio_holdings[base_currency]['amount']
                current_avg_price = portfolio_holdings[base_currency]['avg_price']
                total_amount = current_amount + amount
                new_avg_price = ((current_amount * current_avg_price) + (amount * price)) / total_amount
                
                portfolio_holdings[base_currency] = {
                    'amount': total_amount,
                    'avg_price': new_avg_price
                }
            else:
                portfolio_holdings[base_currency] = {
                    'amount': amount,
                    'avg_price': price
                }
            
            total_trades += 1
            successful_trades += 1
            return True
        else:
            return False
            
    elif action == "SELL":
        if base_currency in portfolio_holdings and portfolio_holdings[base_currency]['amount'] >= amount:
            portfolio_holdings[base_currency]['amount'] -= amount
            portfolio_balance += amount * price
            
            if portfolio_holdings[base_currency]['amount'] <= 0:
                del portfolio_holdings[base_currency]
            
            total_trades += 1
            successful_trades += 1
            return True
        else:
            return False
    
    return False

def calculate_portfolio_value(exchange):
    """Calculate total portfolio value in USD"""
    global portfolio_balance, portfolio_holdings
    
    total_value = portfolio_balance
    
    for currency, holding in portfolio_holdings.items():
        try:
            symbol = f"{currency}/USD"
            ticker = exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            holding_value = holding['amount'] * current_price
            total_value += holding_value
        except:
            # If can't get current price, use average price
            holding_value = holding['amount'] * holding['avg_price']
            total_value += holding_value
            
    return total_value

def print_portfolio_summary(exchange, cycle_count):
    """Print detailed portfolio summary"""
    global portfolio_balance, portfolio_holdings, total_trades, successful_trades
    
    print("\n" + "="*80)
    print(f"📊 RESUMO DO PORTFÓLIO - CICLO {cycle_count}")
    print("="*80)
    
    # Current balance and trading status
    print(f"💰 Saldo em Caixa: {format_currency(portfolio_balance)} | {format_currency(usd_to_brl(portfolio_balance), 'BRL')}")
    
    # Check if we can buy more assets
    trade_amount_usd = get_trade_amount_usd()
    if portfolio_balance < trade_amount_usd:
        print(f"⚠️  Modo: APENAS VENDAS (saldo < {format_currency(trade_amount_usd)})")
    else:
        remaining_trades = int(portfolio_balance / trade_amount_usd)
        print(f"✅ Modo: COMPRA E VENDA (trades restantes: {remaining_trades})")
    
    # Holdings
    if portfolio_holdings:
        print("\n📈 POSIÇÕES ABERTAS:")
        holdings_value_usd = 0
        for currency, holding in portfolio_holdings.items():
            try:
                symbol = f"{currency}/USD"
                ticker = exchange.fetch_ticker(symbol)
                current_price = ticker['last']
                holding_value = holding['amount'] * current_price
                profit_loss = (current_price - holding['avg_price']) * holding['amount']
                profit_loss_pct = ((current_price - holding['avg_price']) / holding['avg_price']) * 100
                
                holdings_value_usd += holding_value
                
                status = "🟢" if profit_loss >= 0 else "🔴"
                print(f"  {status} {currency}: {holding['amount']:.6f} @ {format_currency(holding['avg_price'])} "
                      f"(atual: {format_currency(current_price)}) | "
                      f"Valor: {format_currency(holding_value)} | "
                      f"P&L: {format_currency(profit_loss)} ({profit_loss_pct:+.2f}%)")
            except:
                holding_value = holding['amount'] * holding['avg_price']
                holdings_value_usd += holding_value
                print(f"  ⚠️  {currency}: {holding['amount']:.6f} @ {format_currency(holding['avg_price'])} "
                      f"| Valor estimado: {format_currency(holding_value)}")
        
        print(f"\n📊 Total em Posições: {format_currency(holdings_value_usd)} | {format_currency(usd_to_brl(holdings_value_usd), 'BRL')}")
    else:
        print("\n📊 Nenhuma posição aberta")
        holdings_value_usd = 0
    
    # Total portfolio value
    total_portfolio_value = portfolio_balance + holdings_value_usd
    initial_balance_usd = get_initial_balance_usd()
    current_value_brl = usd_to_brl(total_portfolio_value)
    total_profit_loss = total_portfolio_value - initial_balance_usd
    total_profit_loss_pct = (total_profit_loss / initial_balance_usd) * 100
    
    print(f"\n💎 VALOR TOTAL DO PORTFÓLIO:")
    print(f"   Inicial: {format_currency(initial_balance_usd)} | {format_currency(INITIAL_BALANCE_BRL, 'BRL')}")
    print(f"   Atual:   {format_currency(total_portfolio_value)} | {format_currency(current_value_brl, 'BRL')}")
    
    status_emoji = "🟢" if total_profit_loss >= 0 else "🔴"
    print(f"   {status_emoji} P&L Total: {format_currency(total_profit_loss)} | "
          f"{format_currency(usd_to_brl(total_profit_loss), 'BRL')} ({total_profit_loss_pct:+.2f}%)")
    
    # Trading statistics
    success_rate = (successful_trades / total_trades * 100) if total_trades > 0 else 0
    print(f"\n📈 ESTATÍSTICAS DE TRADING:")
    print(f"   Total de Trades: {total_trades}")
    print(f"   Trades Bem-sucedidos: {successful_trades}")
    print(f"   Taxa de Sucesso: {success_rate:.1f}%")
    
    print("="*80)

def initialize_exchange():
    """Initialize exchange connection with fallback options"""
    try:
        # First try Coinbase Advanced Trade
        api_key = os.getenv('COINBASE_API_KEY', '')
        api_secret = os.getenv('COINBASE_API_SECRET', '')
        api_passphrase = os.getenv('COINBASE_API_PASSPHRASE', '')
        
        if all([api_key, api_secret, api_passphrase]) and not DRY_RUN:
            print("[INFO] Attempting Coinbase Advanced Trade connection...")
            try:
                exchange = ccxt.coinbaseadvanced({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'password': api_passphrase,
                    'enableRateLimit': True,
                    'sandbox': False,
                })
                
                # Test with balance check
                balance = exchange.fetch_balance()
                print(f"[INFO] Coinbase Advanced Trade connected successfully")
                return exchange
                
            except Exception as auth_error:
                print(f"[WARNING] Coinbase authentication failed: {auth_error}")
                print("[INFO] Falling back to public exchange...")
        
        # Fallback to Binance public API for market data
        try:
            print("[INFO] Using Binance as public data source...")
            exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot'
                }
            })
            
            # Test with public API call
            ticker = exchange.fetch_ticker('BTC/USDT')
            print(f"[INFO] Public exchange connected successfully. BTC price: ${ticker['last']:,.2f}")
            return exchange
            
        except Exception as binance_error:
            print(f"[ERROR] Binance fallback failed: {binance_error}")
            
        # Final fallback to any working exchange
        print("[INFO] Trying alternative exchanges...")
        fallback_exchanges = ['kraken', 'bitfinex', 'coinbasepro']
        
        for exchange_name in fallback_exchanges:
            try:
                exchange_class = getattr(ccxt, exchange_name)
                exchange = exchange_class({'enableRateLimit': True})
                ticker = exchange.fetch_ticker('BTC/USD')
                print(f"[INFO] Connected to {exchange_name.upper()}. BTC price: ${ticker['last']:,.2f}")
                return exchange
            except:
                continue
                
        print("[ERROR] All exchange connections failed")
        return None
        
    except Exception as e:
        print(f"[ERROR] Failed to initialize any exchange: {e}")
        return None

def get_sma(values, period):
    """Calculate Simple Moving Average for given period"""
    if len(values) < period:
        return None
    return statistics.mean(values[-period:])

def fetch_market_data(exchange, symbol):
    """Fetch OHLCV data for the given symbol"""
    try:
        # Fetch candlestick data
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=LONG_MA + 5)
        if len(ohlcv) < LONG_MA:
            print(f"[WARNING] Insufficient data for {symbol} (need {LONG_MA}, got {len(ohlcv)})")
            return None
            
        # Extract closing prices
        closes = [candle[4] for candle in ohlcv]  # Index 4 is close price
        return closes
        
    except Exception as e:
        print(f"[ERROR] Failed to fetch data for {symbol}: {e}")
        return None

def analyze_market(exchange, symbol):
    """Analyze market using SMA crossover strategy"""
    try:
        # Get market data
        closes = fetch_market_data(exchange, symbol)
        if not closes:
            return
            
        # Calculate SMAs
        short_sma = get_sma(closes, SHORT_MA)
        long_sma = get_sma(closes, LONG_MA)
        
        if short_sma is None or long_sma is None:
            print(f"[WARNING] Cannot calculate SMAs for {symbol}")
            return
            
        current_price = closes[-1]
        
        # Determine signal
        if short_sma > long_sma:
            signal = "BUY"
            signal_strength = ((short_sma - long_sma) / long_sma) * 100
        elif short_sma < long_sma:
            signal = "SELL"
            signal_strength = ((long_sma - short_sma) / long_sma) * 100
        else:
            signal = "HOLD"
            signal_strength = 0
            
        # Print analysis with BRL values
        timestamp = time.strftime('%H:%M:%S')
        price_brl = usd_to_brl(current_price)
        print(f"[{timestamp}] {symbol}: Price=${current_price:.2f} (R${price_brl:.2f}) | "
              f"SMA{SHORT_MA}=${short_sma:.2f} | SMA{LONG_MA}=${long_sma:.2f} | "
              f"Signal={signal} ({signal_strength:.2f}%)")
        
        # Execute simulated trade in DRY_RUN mode or real trade
        if signal in ["BUY", "SELL"]:
            if DRY_RUN:
                execute_simulated_trade(symbol, signal, current_price)
            else:
                execute_trade(exchange, symbol, signal, current_price)
            
    except Exception as e:
        print(f"[ERROR] Error analyzing {symbol}: {e}")

def execute_simulated_trade(symbol, signal, current_price):
    """Execute simulated trade for DRY_RUN mode with sequential trading logic"""
    global portfolio_balance, total_trades, successful_trades
    
    try:
        base_currency = symbol.split('/')[0]
        
        if signal == "BUY":
            # Only buy if we don't already have this position AND have sufficient balance
            if base_currency in portfolio_holdings:
                # Skip buy if we already have this asset
                return
                
            trade_amount_usd = get_trade_amount_usd()
            
            # Check if we have sufficient balance for this trade
            if portfolio_balance < trade_amount_usd:
                # Don't print warning for insufficient balance anymore - just skip
                return
            
            amount = trade_amount_usd / current_price
            if update_portfolio(symbol, "BUY", amount, current_price):
                amount_brl = usd_to_brl(trade_amount_usd)
                print(f"[SIMULAÇÃO] ✅ Compra executada: {amount:.6f} {base_currency} "
                      f"por {format_currency(trade_amount_usd)} ({format_currency(amount_brl, 'BRL')})")
                total_trades += 1
                successful_trades += 1
                
        elif signal == "SELL":
            # Only sell if we have this position
            if base_currency not in portfolio_holdings:
                return  # Don't print message for positions we don't have
                
            # Sell the entire position when signal is triggered
            available_amount = portfolio_holdings[base_currency]['amount']
            
            if available_amount > 0 and update_portfolio(symbol, "SELL", available_amount, current_price):
                sell_value_usd = available_amount * current_price
                sell_value_brl = usd_to_brl(sell_value_usd)
                
                # Calculate profit/loss
                avg_buy_price = portfolio_holdings[base_currency]['avg_price'] if base_currency in portfolio_holdings else current_price
                profit_loss = (current_price - avg_buy_price) * available_amount
                profit_loss_pct = ((current_price - avg_buy_price) / avg_buy_price) * 100 if avg_buy_price > 0 else 0
                profit_emoji = "🟢" if profit_loss >= 0 else "🔴"
                
                print(f"[SIMULAÇÃO] ✅ Venda executada: {available_amount:.6f} {base_currency} "
                      f"por {format_currency(sell_value_usd)} ({format_currency(sell_value_brl, 'BRL')}) "
                      f"{profit_emoji} P&L: {format_currency(profit_loss)} ({profit_loss_pct:+.2f}%)")
                total_trades += 1
                successful_trades += 1
                
    except Exception as e:
        print(f"[ERROR] Erro na simulação de trade para {symbol}: {e}")

def execute_trade(exchange, symbol, signal, current_price):
    """Execute actual trade orders (only when DRY_RUN is False)"""
    try:
        if signal == "BUY":
            # Calculate amount to buy
            trade_amount_usd = get_trade_amount_usd()
            amount = trade_amount_usd / current_price
            print(f"[TRADE] Executing BUY order for {amount:.8f} {symbol.split('/')[0]} (${trade_amount_usd})")
            
            # Create market buy order
            order = exchange.create_market_buy_order(symbol, amount)
            print(f"[SUCCESS] Buy order executed: {order['id']}")
            
        elif signal == "SELL":
            # For sell orders, you would need to track your holdings
            # This is a simplified example
            trade_amount_usd = get_trade_amount_usd()
            amount = trade_amount_usd / current_price
            print(f"[TRADE] Executing SELL order for {amount:.8f} {symbol.split('/')[0]}")
            
            # Create market sell order
            order = exchange.create_market_sell_order(symbol, amount)
            print(f"[SUCCESS] Sell order executed: {order['id']}")
            
    except Exception as e:
        print(f"[ERROR] Failed to execute {signal} order for {symbol}: {e}")

def get_available_symbols(exchange):
    """Get all available USD/USDT trading pairs"""
    try:
        markets = exchange.load_markets()
        
        # First try USD pairs, then USDT as fallback
        quote_currencies = ['USD', 'USDT']
        active_symbols = []
        
        for quote in quote_currencies:
            symbols = [symbol for symbol in markets.keys() if symbol.endswith(f'/{quote}')]
            
            for symbol in symbols:
                market_info = markets[symbol]
                if market_info.get('active', True):
                    active_symbols.append(symbol)
            
            if active_symbols:
                print(f"[INFO] Found {len(active_symbols)} active {quote} trading pairs")
                return active_symbols[:15]  # Limit to 15 pairs for performance
        
        return []
        
    except Exception as e:
        print(f"[ERROR] Failed to load markets: {e}")
        print("[INFO] Using fallback symbol list")
        
        # Dynamic fallback based on exchange
        exchange_name = exchange.__class__.__name__.lower()
        
        if 'binance' in exchange_name:
            fallback_symbols = [
                'BTC/USDT', 'ETH/USDT', 'ADA/USDT', 'XRP/USDT', 'LTC/USDT',
                'LINK/USDT', 'DOT/USDT', 'BCH/USDT', 'ALGO/USDT', 'MATIC/USDT'
            ]
        else:
            fallback_symbols = [
                'BTC/USD', 'ETH/USD', 'ADA/USD', 'XRP/USD', 'LTC/USD',
                'LINK/USD', 'DOT/USD', 'BCH/USD', 'ALGO/USD', 'MATIC/USD'
            ]
        
        return fallback_symbols

def print_startup_info():
    """Print startup information and configuration"""
    print("=" * 60)
    print("🚀 CRYPTOCURRENCY TRADING BOT - SMA CROSSOVER STRATEGY")
    print("=" * 60)
    print(f"📊 Strategy: SMA{SHORT_MA} vs SMA{LONG_MA} Crossover")
    print(f"⏱️  Timeframe: {TIMEFRAME}")
    print(f"🔄 Check Interval: {CHECK_INTERVAL} seconds")
    trade_amount_usd = get_trade_amount_usd()
    print(f"💰 Trade Amount: {format_currency(trade_amount_usd)} | {format_currency(MIN_TRADE_AMOUNT_BRL, 'BRL')} per trade")
    
    if DRY_RUN:
        initial_balance_usd = get_initial_balance_usd()
        print(f"💼 Initial Balance: {format_currency(initial_balance_usd)} | {format_currency(INITIAL_BALANCE_BRL, 'BRL')}")
        print("🧪 Dry Run Mode: ENABLED")
        print("⚠️  NO REAL TRADES WILL BE EXECUTED (Simulation Mode)")
    else:
        print("🧪 Dry Run Mode: DISABLED")
        print("🚨 REAL TRADING MODE - TRADES WILL BE EXECUTED!")
        
    print("=" * 60)

def main():
    """Main trading bot loop"""
    global portfolio_balance
    
    # Initialize portfolio balance with the USD equivalent
    portfolio_balance = get_initial_balance_usd()
    
    print_startup_info()
    
    # Initialize exchange
    exchange = initialize_exchange()
    if not exchange:
        print("[FATAL] Cannot proceed without exchange connection")
        return
        
    # Get available trading symbols
    symbols = get_available_symbols(exchange)
    if not symbols:
        print("[FATAL] No trading symbols available")
        return
        
    print(f"[INFO] Monitoring {len(symbols)} USD pairs...")
    print(f"[INFO] Symbols: {', '.join(symbols[:10])}{'...' if len(symbols) > 10 else ''}")
    print("-" * 60)
    
    # Main trading loop
    cycle_count = 0
    try:
        while True:
            cycle_count += 1
            print(f"\n[CYCLE {cycle_count}] Starting market analysis...")
            
            # Analyze each symbol
            for i, symbol in enumerate(symbols, 1):
                try:
                    analyze_market(exchange, symbol)
                    
                    # Add small delay between API calls to respect rate limits
                    if i < len(symbols):
                        time.sleep(1)
                        
                except Exception as e:
                    print(f"[ERROR] Failed to analyze {symbol}: {e}")
                    continue
                    
            print(f"[CYCLE {cycle_count}] Analysis complete.")
            
            # Print portfolio summary at the end of each cycle
            if DRY_RUN:
                print_portfolio_summary(exchange, cycle_count)
            
            print(f"Waiting {CHECK_INTERVAL} seconds...")
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n[INFO] Trading bot stopped by user (Ctrl+C)")
    except Exception as e:
        print(f"\n[FATAL] Unexpected error in main loop: {e}")
    finally:
        print("[INFO] Trading bot shutting down...")

if __name__ == "__main__":
    main()
