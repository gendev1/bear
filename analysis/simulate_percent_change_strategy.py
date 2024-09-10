import pandas as pd
import matplotlib.pyplot as plt

# Load the price feed data
price_feed_file = 'eth_usdc_price_data.csv'
price_feed_df = pd.read_csv(price_feed_file)

# Convert the 'timestamp' column to datetime format
price_feed_df['timestamp'] = pd.to_datetime(price_feed_df['timestamp'])

# Initial conditions
initial_eth_amount = 0.4  # 0.4 ETH
initial_eth_price = price_feed_df['price'].iloc[0]  # Use the first price from the data
initial_usdc_value = initial_eth_amount * initial_eth_price  # Initial capital in USDC

# Fees and slippage
uniswap_fee_rate = 0.003  # 0.3% Uniswap fee
slippage_rate = 0.005  # 0.5% slippage
gas_fee_per_swap = 0.0007  # Gas fee per swap in USD (approximation)

def simulate_trading_strategy(trigger_percentage=5):
    """
    Simulates the trading strategy based on a given trigger percentage for price fluctuations.
    Swaps ETH to USDC when price increases by trigger_percentage,
    and swaps USDC back to ETH when price decreases by trigger_percentage.
    """
    # Initialize variables
    current_position = "ETH"
    eth_amount = initial_eth_amount
    usdc_amount = 0
    last_swap_price = initial_eth_price
    trades = []
    portfolio_values = []

    for _, row in price_feed_df.iterrows():
        current_price = row['price']
        current_time = row['timestamp']

        # Calculate current portfolio value
        if current_position == "ETH":
            portfolio_value = eth_amount * current_price
        else:
            portfolio_value = usdc_amount
        portfolio_values.append((current_time, portfolio_value))

        # ETH to USDC swap
        if current_position == "ETH" and current_price >= last_swap_price * (1 + trigger_percentage / 100):
            usdc_amount = eth_amount * current_price
            usdc_amount -= usdc_amount * (uniswap_fee_rate + slippage_rate)
            eth_amount = 0
            current_position = "USDC"
            last_swap_price = current_price
            trades.append((current_time, "ETH to USDC", current_price))

        # USDC to ETH swap
        elif current_position == "USDC" and current_price <= last_swap_price * (1 - trigger_percentage / 100):
            eth_amount = usdc_amount / current_price
            eth_amount -= eth_amount * (uniswap_fee_rate + slippage_rate)
            usdc_amount = 0
            current_position = "ETH"
            last_swap_price = current_price
            trades.append((current_time, "USDC to ETH", current_price))

    # Calculate final portfolio value
    if current_position == "ETH":
        final_value = eth_amount * price_feed_df['price'].iloc[-1]
    else:
        final_value = usdc_amount

    # Calculate net profit
    net_profit = final_value - initial_usdc_value - (len(trades) * gas_fee_per_swap)

    return net_profit, trades, portfolio_values

def plot_results(trigger_percentage, portfolio_values, trades):
    """
    Plots the portfolio value over time with trade points marked.
    """
    df = pd.DataFrame(portfolio_values, columns=['timestamp', 'value'])
    df.set_index('timestamp', inplace=True)

    plt.figure(figsize=(12, 6))
    plt.plot(df.index, df['value'], label='Portfolio Value')
    
    for trade in trades:
        plt.scatter(trade[0], trade[2] * initial_eth_amount, color='red', zorder=5)

    plt.title(f'Portfolio Value Over Time ({trigger_percentage}% Trigger)')
    plt.xlabel('Date')
    plt.ylabel('Portfolio Value (USDC)')
    plt.legend()
    plt.grid(True)
    plt.savefig(f'portfolio_value_{trigger_percentage}percent.png')
    plt.close()

# Test different trigger percentages and plot results
trigger_percentages = [3, 4, 5, 6, 10]
results = []

for trigger in trigger_percentages:
    profit, trades, portfolio_values = simulate_trading_strategy(trigger_percentage=trigger)
    results.append((trigger, profit))
    print(f"Net Profit with {trigger}% trigger: ${profit:.2f}")
    print(f"Number of trades: {len(trades)}")
    plot_results(trigger, portfolio_values, trades)

# Plot comparison of different trigger percentages
triggers, profits = zip(*results)
plt.figure(figsize=(10, 6))
plt.plot(triggers, profits, marker='o')
plt.title('Net Profit vs Trigger Percentage')
plt.xlabel('Trigger Percentage')
plt.ylabel('Net Profit (USDC)')
plt.grid(True)
plt.savefig('profit_vs_trigger.png')
plt.close()

# Find the best performing trigger percentage
best_trigger, best_profit = max(results, key=lambda x: x[1])
print(f"\nBest performing trigger: {best_trigger}% with a net profit of ${best_profit:.2f}")