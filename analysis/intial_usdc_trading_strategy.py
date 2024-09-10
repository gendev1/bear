import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np

def load_and_clean_data(file_path):
    df = pd.read_csv(file_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')
    
    # Remove rows with price <= 0 or extreme values
    df = df[(df['price'] > 0) & (df['price'] < 10000)]
    
    # Calculate price changes
    df['price_change'] = df['price'].pct_change()
    
    # Remove extreme price changes
    df = df[df['price_change'].abs() < 0.5]  # Remove changes greater than 50%
    
    return df

def simulate_trading(df, initial_usdc, trigger_percentage):
    position = "USDC"
    usdc_amount = initial_usdc
    eth_amount = 0
    entry_price = 0
    trades = []
    portfolio_values = []

    for _, row in df.iterrows():
        current_price = row['price']
        current_time = row['timestamp']

        if position == "USDC":
            portfolio_value = usdc_amount
        else:
            portfolio_value = eth_amount * current_price
        portfolio_values.append((current_time, portfolio_value))

        if position == "USDC" and entry_price > 0:
            price_change = (current_price - entry_price) / entry_price
            if price_change <= -trigger_percentage:
                eth_amount = usdc_amount / current_price
                usdc_amount = 0
                position = "ETH"
                trades.append((current_time, "Buy ETH", current_price, eth_amount))
                entry_price = current_price

        elif position == "ETH":
            price_change = (current_price - entry_price) / entry_price
            if price_change >= trigger_percentage:
                usdc_amount = eth_amount * current_price
                eth_amount = 0
                position = "USDC"
                trades.append((current_time, "Sell ETH", current_price, usdc_amount))
                entry_price = current_price

        if entry_price == 0:
            entry_price = current_price

    # Final portfolio value
    if position == "ETH":
        final_value = eth_amount * df['price'].iloc[-1]
    else:
        final_value = usdc_amount

    return trades, portfolio_values, final_value

def plot_results(df, portfolio_values, trades, trigger_percentage):
    plt.figure(figsize=(12, 6))
    plt.plot(df['timestamp'], df['price'], label='ETH Price')
    
    portfolio_df = pd.DataFrame(portfolio_values, columns=['timestamp', 'value'])
    plt.plot(portfolio_df['timestamp'], portfolio_df['value'], label='Portfolio Value')
    
    for trade in trades:
        if trade[1] == "Buy ETH":
            plt.scatter(trade[0], trade[2], color='g', marker='^')
        else:
            plt.scatter(trade[0], trade[2], color='r', marker='v')
    
    plt.title(f'ETH Price and Portfolio Value Over Time ({trigger_percentage*100}% Trigger)')
    plt.xlabel('Date')
    plt.ylabel('Price/Value (USDC)')
    plt.legend()
    plt.savefig(f'trading_simulation_{trigger_percentage*100}percent.png')
    plt.close()

def main():
    df = load_and_clean_data('eth_usdc_price_data.csv')
    initial_usdc = 1000
    trigger_percentages = [0.03, 0.05, 0.07, 0.10]
    
    results = []
    
    for trigger in trigger_percentages:
        trades, portfolio_values, final_value = simulate_trading(df, initial_usdc, trigger)
        profit = final_value - initial_usdc
        roi = (profit / initial_usdc) * 100
        
        print(f"\nResults for {trigger*100}% trigger:")
        print(f"Number of trades: {len(trades)}")
        print(f"Final portfolio value: ${final_value:.2f}")
        print(f"Profit: ${profit:.2f}")
        print(f"ROI: {roi:.2f}%")
        
        # Check for infinite or NaN values
        if np.isinf(final_value) or np.isnan(final_value):
            print("Warning: Infinite or NaN value detected in final portfolio value.")
            continue
        
        plot_results(df, portfolio_values, trades, trigger)
        results.append((trigger, profit, roi))
    
    if results:
        # Find best performing trigger
        best_trigger = max(results, key=lambda x: x[1])
        print(f"\nBest performing trigger: {best_trigger[0]*100}% with profit ${best_trigger[1]:.2f} and ROI {best_trigger[2]:.2f}%")
    else:
        print("\nNo valid results to determine the best performing trigger.")

if __name__ == "__main__":
    main()