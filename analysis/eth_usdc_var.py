import requests
import pandas as pd
from datetime import datetime, timedelta
import time
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()
GRAPH_API_KEY=os.getenv("GRAPH_API_KEY")

# Define the GraphQL endpoint for Uniswap V3
GRAPH_API_URL = f"https://gateway.thegraph.com/api/{GRAPH_API_KEY}/subgraphs/id/5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV"
# Token addresses
USDC_ADDRESS = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
WETH_ADDRESS = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"

def query_swaps(token0, token1, start_timestamp, end_timestamp):
    """Query swaps for a specific token pair between two timestamps."""
    swaps = []
    query_template = """
    {{
      swaps(
        first: 1000,
        orderBy: timestamp,
        orderDirection: asc,
        where: {{
          timestamp_gte: {start_timestamp},
          timestamp_lt: {end_timestamp},
          token0: "{token0}",
          token1: "{token1}"
        }}
      ) {{
        timestamp
        amount0
        amount1
      }}
    }}
    """

    current_timestamp = start_timestamp
    while current_timestamp < end_timestamp:
        query = query_template.format(
            start_timestamp=current_timestamp,
            end_timestamp=end_timestamp,
            token0=token0,
            token1=token1
        )
        try:
            response = requests.post(GRAPH_API_URL, json={'query': query}, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
            time.sleep(5)  # Wait before retrying
            continue

        if 'errors' in data:
            print("GraphQL errors:", data['errors'])
            break

        batch_swaps = data['data']['swaps']
        if not batch_swaps:
            break

        swaps.extend(batch_swaps)
        current_timestamp = int(batch_swaps[-1]['timestamp']) + 1

    return swaps

def get_historical_swaps(start_timestamp, end_timestamp):
    """Fetch historical ETH/USDC swaps between two timestamps by querying both token pair orders."""
    swaps_usdc_weth = query_swaps(USDC_ADDRESS, WETH_ADDRESS, start_timestamp, end_timestamp)
    swaps_weth_usdc = query_swaps(WETH_ADDRESS, USDC_ADDRESS, start_timestamp, end_timestamp)

    # Combine and sort all swaps
    all_swaps = swaps_usdc_weth + swaps_weth_usdc
    all_swaps.sort(key=lambda x: int(x['timestamp']))

    return all_swaps

def process_swap_data(swaps):
    """Process swap data into a DataFrame with calculated prices."""
    df = pd.DataFrame(swaps)
    df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='s')
    df['amount0'] = df['amount0'].astype(float)
    df['amount1'] = df['amount1'].astype(float)

    # Calculate price ensuring USDC is always the quote currency
    df['price'] = df.apply(lambda row: abs(row['amount1'] / row['amount0']) 
                           if row['amount0'] > row['amount1'] 
                           else abs(row['amount0'] / row['amount1']), axis=1)

    return df

def aggregate_data(df, interval='5T'):
    """Aggregate data into regular intervals."""
    df_agg = df.set_index('timestamp').resample(interval).agg({
        'amount0': 'sum',
        'amount1': 'sum'
    }).dropna()
    df_agg['price'] = df_agg.apply(lambda row: abs(row['amount1'] / row['amount0']) 
                                   if row['amount0'] > row['amount1'] 
                                   else abs(row['amount0'] / row['amount1']), axis=1)
    return df_agg.reset_index()

def detect_price_changes(df, threshold=0.05):
    """Detect significant price changes using a rolling window approach."""
    df['price_change'] = df['price'].pct_change()
    df['cumulative_change'] = (1 + df['price_change']).cumprod() - 1
    df['signal'] = ((df['cumulative_change'].abs() >= threshold) & 
                    (df['cumulative_change'].abs().shift(1) < threshold)).astype(int)
    return df[df['signal'] == 1]

def save_to_csv(df, significant_changes, file_name="eth_usdc_price_data.csv"):
    """Save the full data and significant price changes to CSV files."""
    df.to_csv(file_name, index=False)
    print(f"Price data saved to {file_name}")

    significant_changes_file = "significant_price_changes.csv"
    significant_changes.to_csv(significant_changes_file, index=False)
    print(f"Significant price changes saved to {significant_changes_file}")

def main():
    # Define the time range (e.g., last 7 days)
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=1)
    start_timestamp = int(start_time.timestamp())
    end_timestamp = int(end_time.timestamp())

    print(f"Fetching data from {start_time} to {end_time}")

    swaps = get_historical_swaps(start_timestamp, end_timestamp)
    if not swaps:
        print("No swap data found for the specified time range.")
        return

    df = process_swap_data(swaps)
    df_agg = aggregate_data(df)
    significant_changes = detect_price_changes(df_agg)

    # Save the data into CSV files
    save_to_csv(df_agg, significant_changes)

if __name__ == "__main__":
    main()