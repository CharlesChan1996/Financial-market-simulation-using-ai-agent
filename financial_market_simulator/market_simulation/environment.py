from typing import List, Dict, Any, Optional, NamedTuple
from collections import defaultdict

# Defines the structure of an order placed by an agent.
class Order(NamedTuple):
    """
    Represents a trading order in the market.

    Attributes:
        agent_id: The unique identifier of the agent placing the order.
        instrument: The symbol of the financial instrument to be traded (e.g., 'AAPL').
        quantity: The number of shares/units to trade.
        order_type: Type of order, either 'buy' or 'sell'.
        price: The limit price for the order. If None, it's treated as a market order
               (though current matching logic might require a price or use last known price).
        timestamp: The simulation date/time when the order was created by the agent.
    """
    agent_id: str
    instrument: str
    quantity: float # Number of shares/units
    order_type: str  # 'buy' or 'sell'
    price: Optional[float] = None  # For limit orders, None for market orders
    timestamp: str # Timestamp of order creation (e.g., YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)

class MarketEnvironment:
    """
    Simulates the market environment, including price data, an order book, and trade execution.

    This class is responsible for:
    - Maintaining the current simulation date.
    - Storing and providing access to market data (historical/current prices).
    - Managing an order book where agents submit buy and sell orders.
    - Processing these orders by matching compatible buys and sells to simulate trades.
    - Advancing simulation time.
    """
    def __init__(self, start_date: str, end_date: str, tradable_instruments: List[str]):
        """
        Initializes the MarketEnvironment.

        Args:
            start_date: The starting date of the simulation (e.g., 'YYYY-MM-DD').
            end_date: The ending date of the simulation (e.g., 'YYYY-MM-DD').
            tradable_instruments: A list of symbols for instruments that can be traded in this market.
        """
        self.start_date: str = start_date
        self.end_date: str = end_date
        self.current_date: str = start_date # Tracks the current day in the simulation
        self.tradable_instruments: List[str] = tradable_instruments

        # Stores market price history: Dict[instrument_symbol, Dict[date_str, price_float]]
        self.market_data: Dict[str, Dict[str, float]] = self._initialize_market_data()

        # Order book: Dict[instrument_symbol, Dict[order_type, List[Order]]]
        # e.g., self.order_book['AAPL']['buy'] = [Order(...), Order(...)]
        self.order_book: Dict[str, Dict[str, List[Order]]] = defaultdict(lambda: defaultdict(list))

    def _initialize_market_data(self) -> Dict[str, Dict[str, float]]:
        """
        Initializes with example market data.
        In a real scenario, this method would load data from a CSV file, database, or API.

        Returns:
            A dictionary containing sample price data for specified instruments over a few dates.
        """
        # Using the example data provided in the problem description for quick setup.
        # This should be replaced with more robust data loading for actual simulations.
        data = {
            'AAPL': {
                '2023-01-01': 150.00,
                '2023-01-02': 152.50,
                '2023-01-03': 151.75,
                '2023-01-04': 150.50, # Added data for example consistency
                '2023-01-05': 149.75, # Added data
            },
            'GOOG': {
                '2023-01-01': 2700.00,
                '2023-01-02': 2725.00,
                '2023-01-03': 2710.50,
                '2023-01-04': 2700.00, # Added data
                '2023-01-05': 2680.50, # Added data
            }
        }
        # Ensure all formally tradable instruments have at least an empty dict for data
        # to prevent KeyErrors if an agent tries to access an instrument with no sample data.
        for instrument in self.tradable_instruments:
            if instrument not in data:
                data[instrument] = {} # Initialize with no price points
        return data

    def get_market_data(self, date: str, instrument: str) -> Optional[float]:
        """
        Retrieves the price of a specific instrument on a specific date.

        Args:
            date: The date (YYYY-MM-DD string) for which to retrieve the price.
            instrument: The symbol of the instrument.

        Returns:
            The price (float) of the instrument on the given date, or None if data is not available.
        """
        return self.market_data.get(instrument, {}).get(date)

    def submit_order(self, order: Order) -> None:
        """
        Adds a trading order from an agent to the order book.
        The order book is sorted upon insertion to facilitate matching.
        Buy orders are sorted by highest price first, sell orders by lowest price first.

        Args:
            order: The Order object to be added.
        """
        if order.instrument not in self.tradable_instruments:
            # print(f"Warning (MarketEnv): Order submitted for non-tradable instrument {order.instrument}. Ignoring.")
            return

        if order.order_type not in ['buy', 'sell']:
            # print(f"Warning (MarketEnv): Order submitted with invalid order_type {order.order_type}. Ignoring.")
            return

        self.order_book[order.instrument][order.order_type].append(order)

        # Sort orders to facilitate matching:
        # Buy orders: highest price first (attractive to sellers). If prices are equal, FIFO (implicit by append).
        # Sell orders: lowest price first (attractive to buyers). If prices are equal, FIFO.
        if order.order_type == 'buy':
            # For market orders (price=None), they effectively have highest priority for buys.
            self.order_book[order.instrument]['buy'].sort(key=lambda o: o.price if o.price is not None else float('inf'), reverse=True)
        elif order.order_type == 'sell':
            # For market orders (price=None), they effectively have highest priority for sells (lowest price).
            self.order_book[order.instrument]['sell'].sort(key=lambda o: o.price if o.price is not None else float('-inf'))


    def get_current_prices(self) -> Dict[str, float]:
        """
        Returns a dictionary of current market prices for all tradable instruments
        for the `self.current_date`. Used by agents to make decisions.

        Returns:
            A dictionary mapping instrument symbols to their prices on `self.current_date`.
            Skips instruments if price data is not available for the current date.
        """
        prices: Dict[str, float] = {}
        for instrument in self.tradable_instruments:
            price = self.get_market_data(self.current_date, instrument)
            if price is not None:
                prices[instrument] = price
        return prices

    def get_market_data_for_date(self, date: str) -> Dict[str, float]:
        """
        Retrieves all available market prices for all tradable instruments on a *specific historical date*.
        Used for valuation or providing context to agents.

        Args:
            date: The specific date (YYYY-MM-DD string) for which to retrieve prices.

        Returns:
            A dictionary mapping instrument symbols to their prices on the given date.
        """
        prices_on_date: Dict[str, float] = {}
        for instrument in self.tradable_instruments:
            instrument_prices_over_time = self.market_data.get(instrument, {}) # Get all prices for the instrument
            price = instrument_prices_over_time.get(date) # Get price for the specific date
            if price is not None:
                prices_on_date[instrument] = price
        return prices_on_date

    def process_orders(self) -> List[Dict[str, Any]]:
        """
        Processes orders in the order book by attempting to match buy and sell orders.
        This is the core trade execution logic of the market.

        The current matching logic is simplified:
        - It iterates through instruments with pending orders.
        - For each instrument, it tries to match the best buy order (highest price)
          with the best sell order (lowest price).
        - A match occurs if the buy order price is greater than or equal to the sell order price,
          or if one or both are market orders (price=None).
        - Market orders are matched at the price of the limit order they are matched against,
          or against the last known market price if two market orders are matched.
        - Matched orders result in "trade confirmations" for both buyer and seller.
        - Partially filled orders remain in the book with adjusted quantity; fully filled orders are removed.

        Returns:
            A list of trade confirmation dictionaries. Each dictionary represents one side
            of an executed trade (i.e., two confirmations are generated per trade, one for
            the buyer and one for the seller). Each confirmation includes:
            `executed_order` (the Order object, with quantity adjusted to the traded amount),
            `price` (execution price), `quantity` (executed quantity), `timestamp` (execution date),
            and convenience fields like `agent_id`, `instrument`, `order_type`.
        """
        executed_trades_confirmations: List[Dict[str, Any]] = []

        # Iterate over a copy of instrument keys for safe modification of the order book during processing
        for instrument in list(self.order_book.keys()):
            buy_orders = self.order_book[instrument]['buy']
            sell_orders = self.order_book[instrument]['sell']

            # Indices for orders that have been fully matched and should be removed.
            matched_buy_indices: List[int] = []
            matched_sell_indices: List[int] = []

            b_idx = 0 # Pointer for buy orders
            s_idx = 0 # Pointer for sell orders

            # Loop while there are potential buy and sell orders to match
            while b_idx < len(buy_orders) and s_idx < len(sell_orders):
                buy_order = buy_orders[b_idx]
                sell_order = sell_orders[s_idx]

                can_match = False
                trade_price = 0.0 # Price at which the trade will be executed

                # Determine if orders can be matched and at what price
                if buy_order.price is not None and sell_order.price is not None: # Both are limit orders
                    if buy_order.price >= sell_order.price:
                        can_match = True
                        # Trade typically occurs at the price of the order that was already in the book,
                        # or a midpoint. Here, using sell_order.price (more favorable to buyer if orders crossed).
                        # A common rule is to use the price of the earlier order if they cross.
                        # For simplicity, let's assume sell price if sell order is "hit".
                        # Or, if buy is aggressive, could be buy_order.price if it "hits" a standing sell.
                        # Using sell_order.price is a common way to model a buy "lifting the offer".
                        trade_price = sell_order.price
                elif buy_order.price is None and sell_order.price is not None: # Market buy, limit sell
                    can_match = True
                    trade_price = sell_order.price # Market buy executes at the limit sell's price
                elif sell_order.price is None and buy_order.price is not None: # Market sell, limit buy
                    can_match = True
                    trade_price = buy_order.price # Market sell executes at the limit buy's price
                elif buy_order.price is None and sell_order.price is None: # Both are market orders
                    # Match at current market price (e.g., last traded price or a reference price for the day)
                    current_market_price = self.get_market_data(self.current_date, instrument)
                    if current_market_price is not None:
                        can_match = True
                        trade_price = current_market_price
                    else:
                        # Cannot execute if no reference price is available for two market orders.
                        # Advance both pointers to avoid getting stuck.
                        s_idx +=1
                        b_idx +=1
                        continue # Try next pair

                if can_match:
                    trade_quantity = min(buy_order.quantity, sell_order.quantity)

                    if trade_quantity > 0:
                        # Generate confirmations for both buyer and seller
                        common_trade_details = {
                            'price': trade_price,
                            'quantity': trade_quantity,
                            'timestamp': self.current_date, # Execution timestamp (current simulation date)
                            'instrument': instrument, # Included for convenience
                        }

                        buyer_confirmation = {
                            **common_trade_details,
                            'executed_order': buy_order._replace(quantity=trade_quantity), # Original order with traded quantity
                            'agent_id': buy_order.agent_id,
                            'order_type': 'buy'
                        }
                        executed_trades_confirmations.append(buyer_confirmation)

                        seller_confirmation = {
                            **common_trade_details,
                            'executed_order': sell_order._replace(quantity=trade_quantity),
                            'agent_id': sell_order.agent_id,
                            'order_type': 'sell'
                        }
                        executed_trades_confirmations.append(seller_confirmation)

                        # print(f"INFO (MarketEnv): Trade Executed: {buy_order.agent_id} (BUY) and {sell_order.agent_id} (SELL) "
                        #       f"for {trade_quantity} shares of {instrument} at {trade_price:.2f} on {self.current_date}")

                        # Update quantities on original orders or mark them for removal
                        new_buy_quantity = buy_order.quantity - trade_quantity
                        new_sell_quantity = sell_order.quantity - trade_quantity

                        if new_buy_quantity == 0:
                            matched_buy_indices.append(b_idx)
                        else:
                            # Update the order in the list with remaining quantity
                            buy_orders[b_idx] = buy_order._replace(quantity=new_buy_quantity)

                        if new_sell_quantity == 0:
                            matched_sell_indices.append(s_idx)
                        else:
                            sell_orders[s_idx] = sell_order._replace(quantity=new_sell_quantity)

                        # Advance pointers based on which order was filled
                        if new_buy_quantity == 0:
                            b_idx += 1
                        if new_sell_quantity == 0:
                            s_idx += 1
                        # If both were partially filled (should not happen if one is always fully consumed by the other's available Q),
                        # the loop continues with the updated quantities.
                    else: # trade_quantity is 0 (e.g., one order was for 0 quantity)
                        # This case should ideally not occur with valid positive quantities.
                        # Advance one pointer to avoid infinite loop.
                        s_idx += 1

                # If prices don't match for limit orders, advance the pointer of the order
                # that is less aggressive or further from the current market spread.
                elif buy_order.price is not None and sell_order.price is not None: # Both limit, but buy_order.price < sell_order.price
                    # If buy price is lower than sell price, no match.
                    # Advance pointer of the order that is "worse" or less likely to match.
                    # Typically, if a spread exists, both stay. But for iterative matching,
                    # if no match, you might advance the one with older timestamp or less aggressive price.
                    # Here, just advancing the buy order pointer if its price is too low.
                    # This simple logic might skip potential matches if order book isn't resorted/re-evaluated.
                    # For a basic CDA, we typically only match if best bid >= best ask.
                    # If not, no trade for this instrument in this iteration.
                    break # No match possible at the top of the book for this instrument currently
                else: # Unhandled case or one of the orders is market but didn't match (e.g. market buy but no sellers)
                    # If there's a market buy but no sell orders, b_idx will increment past available buys.
                    # If there's a market sell but no buy orders, s_idx will increment.
                    # To prevent infinite loops in complex scenarios, ensure pointers advance.
                    # If one is market and other is limit but no match, means no orders of the other type.
                    if buy_order.price is None and not sell_orders[s_idx:]: # Market buy, no more sell orders
                        break
                    if sell_order.price is None and not buy_orders[b_idx:]: # Market sell, no more buy orders
                        break
                    # Fallback if stuck (should be reviewed if this is hit often)
                    b_idx +=1; s_idx +=1


            # Remove fully matched orders from the book (in reverse to maintain index integrity)
            for idx in sorted(matched_buy_indices, reverse=True):
                del buy_orders[idx]
            for idx in sorted(matched_sell_indices, reverse=True):
                del sell_orders[idx]

            # If an instrument's order list (buy or sell) becomes empty, clean it up.
            if not self.order_book[instrument]['buy'] and not self.order_book[instrument]['sell']:
                del self.order_book[instrument] # Remove instrument key if no orders left
            elif not self.order_book[instrument]['buy']:
                 del self.order_book[instrument]['buy'] # Remove 'buy' key
            elif not self.order_book[instrument]['sell']:
                 del self.order_book[instrument]['sell'] # Remove 'sell' key


        return executed_trades_confirmations

    def advance_time(self) -> List[Dict[str, Any]]:
        """
        Advances the simulation time by one day and processes any outstanding orders.

        Returns:
            A list of trade confirmations from processing orders at the new (current) date.
            Returns an empty list if the simulation end date has been surpassed.
        """
        # This is a simplified way to advance dates. A more robust solution would use datetime objects
        # and calendar logic (e.g., skipping weekends, handling holidays if necessary for realism).
        try:
            current_dt = datetime.strptime(self.current_date, '%Y-%m-%d')
            current_dt += timedelta(days=1)
            self.current_date = current_dt.strftime('%Y-%m-%d')
        except ValueError:
            # print(f"Error (MarketEnv): Error parsing current_date: {self.current_date}. Cannot advance time.")
            return [] # Stop simulation or handle error

        if self.current_date > self.end_date:
            # print(f"Info (MarketEnv): Simulation period ended on {self.end_date}. Current date {self.current_date} is past end.")
            return [] # No more trades or actions

        # print(f"\n--- MarketEnv: Advancing time to {self.current_date} ---")

        # In a dynamic simulation, market data for self.current_date might be updated here
        # (e.g., from a data feed, or a model generating prices). For now, it's pre-loaded.

        trade_confirmations = self.process_orders() # Process orders at the start of the new day
        return trade_confirmations

# Example Usage (kept for quick, isolated testing of MarketEnvironment if needed)
# This would typically be commented out when running the full simulation via simulation.py
if __name__ == '__main__':
    env = MarketEnvironment(start_date='2023-01-01', end_date='2023-01-05', tradable_instruments=['AAPL', 'GOOG'])

    print(f"Initial Market Data for AAPL on 2023-01-01: {env.get_market_data('2023-01-01', 'AAPL')}")

    # Example Orders with timestamps
    order1 = Order(agent_id='Agent1', instrument='AAPL', quantity=10, order_type='buy', price=150.50, timestamp='2023-01-01')
    order2 = Order(agent_id='Agent2', instrument='AAPL', quantity=5, order_type='sell', price=150.00, timestamp='2023-01-01')
    env.submit_order(order1)
    env.submit_order(order2)

    print("\nOrder Book before processing:")
    # print(env.order_book)

    trades_today = env.process_orders()
    print("\nTrades executed today:", trades_today)

    print("\nOrder Book after processing:")
    # print(env.order_book)

    env.advance_time() # Advances to 2023-01-02
    # ... more test steps ...
```
