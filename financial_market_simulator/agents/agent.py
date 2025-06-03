from typing import List, Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime, timedelta
import random # Keep random for subclasses that might want it directly, though RandomAgent imports it too.

# Assuming Order is importable from environment.py
from financial_market_simulator.market_simulation.environment import Order

# Forward class declaration for type hinting to avoid circular imports
if TYPE_CHECKING:
    from financial_market_simulator.market_simulation.environment import MarketEnvironment

class Agent:
    """
    Represents a base trading agent in the financial market simulator.

    This class provides the fundamental attributes and methods for an agent,
    including managing capital, portfolio, memory of past trades, and a basic
    learning mechanism to avoid recently unprofitable buy trades.

    Specific trading logic (how an agent decides to buy or sell) is intended
    to be implemented in subclasses (e.g., RandomAgent, TechnicalAgent).
    """
    def __init__(self,
                 agent_id: str,
                 initial_capital: float,
                 tradable_instruments: List[str],
                 trading_belief: str,
                 market_env_ref: 'MarketEnvironment'):
        """
        Initializes a new Agent.

        Args:
            agent_id: A unique identifier for the agent.
            initial_capital: The amount of cash the agent starts with.
            tradable_instruments: A list of instrument symbols (e.g., stock tickers)
                                  that the agent is allowed to trade.
            trading_belief: A string describing the agent's general trading strategy or type
                            (e.g., "random_learner", "technical_placeholder"). This is primarily for categorization.
            market_env_ref: A reference to the main MarketEnvironment instance. This allows the agent
                            to access current market information, like the date.
        """
        self.agent_id: str = agent_id
        self.initial_capital: float = initial_capital # Store for reference and P&L calculation
        self.cash: float = initial_capital
        self.portfolio: Dict[str, int] = {} # Key: instrument symbol, Value: quantity (shares)
        self.tradable_instruments: List[str] = tradable_instruments
        self.trading_belief: str = trading_belief
        self.memory: List[Dict[str, Any]] = [] # Stores dictionaries representing past trade outcomes and context
        self.pnl: float = 0.0 # Overall profit and loss; can be updated periodically or at the end.

        # A reference to the market environment, crucial for accessing current_date for decisions and learning.
        self.market_env_ref: 'MarketEnvironment' = market_env_ref

        # Learning-related attributes:
        # Stores instruments that recently resulted in "bad" buy trades.
        # Key: instrument symbol, Value: datetime object representing when the cooldown expires.
        self.recent_bad_buys: Dict[str, datetime] = {}
        self.learning_params: Dict[str, Any] = {
            'price_drop_threshold': 0.05,  # Percentage drop from buy price to trigger cooldown (e.g., 0.05 for 5%).
            'cooldown_period_days': 2      # Number of simulation days to avoid buying the instrument.
        }

    def __str__(self) -> str:
        """Returns a concise string representation of the agent."""
        return (f"Agent(id='{self.agent_id}', cash={self.cash:.2f}, "
                f"belief='{self.trading_belief}', portfolio_items={len(self.portfolio)})")

    def __repr__(self) -> str:
        """Returns a detailed string representation of the agent, useful for debugging."""
        cooldowns_str = {k: v.strftime('%Y-%m-%d') for k, v in self.recent_bad_buys.items()}
        return (f"Agent(id='{self.agent_id}', cash={self.cash:.2f}, portfolio={self.portfolio}, "
                f"belief='{self.trading_belief}', tradable_instruments={self.tradable_instruments}, "
                f"initial_capital={self.initial_capital}, memory_size={len(self.memory)}, "
                f"active_cooldowns={cooldowns_str}, learning_params={self.learning_params})")

    def _str_to_datetime(self, date_str: str) -> Optional[datetime]:
        """
        Helper function to convert a date string in 'YYYY-MM-DD' format to a datetime object.
        Returns None if parsing fails.
        """
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except (ValueError, TypeError):
            # Optional: Log this warning for debugging if date string format issues are suspected.
            # print(f"Warning (Agent {self.agent_id}): Could not parse date string: {date_str}")
            return None

    def get_total_value(self, current_market_prices: Dict[str, float]) -> float:
        """
        Calculates the agent's current total wealth (cash + value of portfolio holdings).

        Args:
            current_market_prices: A dictionary mapping instrument symbols to their current market prices.
                                   It's crucial that these prices correspond to the intended valuation time.

        Returns:
            The total calculated value of the agent. If an instrument in the portfolio
            does not have a price in `current_market_prices`, its value is considered 0 for this calculation.
        """
        portfolio_value = 0.0
        for instrument, quantity in self.portfolio.items():
            price = current_market_prices.get(instrument, 0.0) # Default to 0.0 if price not found
            portfolio_value += quantity * price
        return self.cash + portfolio_value

    def update_memory(self, trade_confirmation: Dict[str, Any], prices_at_trade_execution_date: Dict[str, float]) -> None:
        """
        Updates the agent's memory with details of an executed trade and relevant market context at that time.
        The memory entry helps in evaluating trade performance and learning.

        Args:
            trade_confirmation: A dictionary containing details of the trade execution,
                                expected to include `executed_order` (an Order object), `price` (execution price),
                                `quantity`, and `timestamp` (execution date string).
            prices_at_trade_execution_date: A dictionary of market prices for all tradable instruments
                                            on the date the trade was executed. This provides context
                                            of the general market price when the trade occurred.
        """
        executed_order = trade_confirmation.get('executed_order')

        # Validate that executed_order is a valid Order object (NamedTuple in this case)
        # It should have attributes like 'instrument' and 'order_type'.
        if not isinstance(executed_order, tuple) or not hasattr(executed_order, '_fields') or \
           'instrument' not in executed_order._fields or 'order_type' not in executed_order._fields:
            # print(f"Warning (Agent {self.agent_id}): Invalid 'executed_order' structure in trade_confirmation: {executed_order}")
            return

        instrument = executed_order.instrument

        memory_entry: Dict[str, Any] = {
            'timestamp': trade_confirmation.get('timestamp'), # Execution date string from environment
            'instrument': instrument,
            'order_type': executed_order.order_type,
            'price': trade_confirmation.get('price'),        # Actual execution price for the trade
            'quantity': trade_confirmation.get('quantity'),
            # Market price of the traded instrument on the day of execution.
            # This helps evaluate if the buy/sell was at a good price relative to that day's general price level.
            'market_price_on_trade_date': prices_at_trade_execution_date.get(instrument)
        }

        # Ensure all essential keys for learning/evaluation are present before appending to memory.
        # 'market_price_on_trade_date' can legitimately be None if data wasn't available for that instrument on that day.
        if all(memory_entry.get(k) is not None for k in ['timestamp', 'instrument', 'order_type', 'price', 'quantity']):
            self.memory.append(memory_entry)
        # else:
            # print(f"Warning (Agent {self.agent_id}): Memory entry missing some essential data and was not recorded: {memory_entry}")


    def evaluate_past_trades(self, current_day_market_prices: Dict[str, float]) -> None:
        """
        Evaluates past 'buy' trades to identify underperforming assets and potentially
        put them on a temporary cooldown for future buy considerations.

        This method implements a basic learning mechanism:
        1.  It cleans up any expired cooldowns from `self.recent_bad_buys`.
        2.  It iterates through the agent's trade memory. If a previously bought instrument
            is now trading at a price significantly lower than its purchase price (as defined
            by `self.learning_params['price_drop_threshold']`), that instrument is
            added to `self.recent_bad_buys` with a cooldown period.

        Args:
            current_day_market_prices: A dictionary of current market prices for all tradable instruments,
                                       representing the market state for the current simulation day.
        """
        if not self.market_env_ref:
            return # Cannot get current_date without market_env_ref

        current_sim_date_str = self.market_env_ref.current_date
        current_sim_datetime = self._str_to_datetime(current_sim_date_str)

        if not current_sim_datetime:
            return # Failed to parse current date, cannot proceed with time-based evaluation

        # 1. Clean up expired cooldowns from self.recent_bad_buys.
        # Cooldowns are stored as datetime objects indicating when they expire.
        # Rebuild the dictionary with only active cooldowns.
        active_bad_buys = {}
        for instrument, expiry_dt in self.recent_bad_buys.items():
            if expiry_dt > current_sim_datetime: # If expiry is still in the future
                active_bad_buys[instrument] = expiry_dt
        self.recent_bad_buys = active_bad_buys

        # 2. Evaluate trades from memory to identify new "bad buys".
        for trade_mem in self.memory:
            # Only interested in 'buy' trades for this learning mechanism.
            # And only if the instrument is not already on a cooldown (to avoid redundant checks
            # or re-triggering cooldown from the same old trade memory).
            if trade_mem['order_type'] == 'buy' and trade_mem['instrument'] not in self.recent_bad_buys:
                instrument = trade_mem['instrument']
                buy_price = trade_mem['price']

                current_price_of_instrument = current_day_market_prices.get(instrument)

                if current_price_of_instrument is None or buy_price is None:
                    # Cannot evaluate if current price or original buy price is unknown.
                    continue

                price_drop_threshold = self.learning_params['price_drop_threshold']
                if current_price_of_instrument < buy_price * (1 - price_drop_threshold):
                    # Condition met: current price is significantly lower than buy price.
                    cooldown_days = self.learning_params['cooldown_period_days']
                    cooldown_expiry_dt = current_sim_datetime + timedelta(days=cooldown_days)
                    self.recent_bad_buys[instrument] = cooldown_expiry_dt
                    # Optional: logging for when an instrument is put on cooldown can be useful for debugging.
                    # print(f"INFO (Agent {self.agent_id}): Instrument {instrument} on buy cooldown until "
                    #       f"{cooldown_expiry_dt.strftime('%Y-%m-%d')} due to price drop from {buy_price:.2f} "
                    #       f"to {current_price_of_instrument:.2f} (on {current_sim_date_str}).")

    def make_decision(self, current_day_market_prices: Dict[str, float]) -> List[Order]:
        """
        Core logic for the agent to make trading decisions.

        The base Agent class's implementation only calls `evaluate_past_trades`
        to update its learning state (e.g., cooldowns based on past performance).
        It does not generate any orders itself.

        Subclasses are expected to override this method to implement their specific
        trading strategies. They should typically call `super().evaluate_past_trades(current_day_market_prices)`
        or `self.evaluate_past_trades(current_day_market_prices)` at the beginning of their
        `make_decision` method to ensure the learning mechanism is active.

        Args:
            current_day_market_prices: A dictionary of current market prices for tradable instruments.

        Returns:
            A list of Order objects representing the trades the agent wants to make.
            An empty list if no trades are decided by this base implementation.
        """
        self.evaluate_past_trades(current_day_market_prices) # Update learning state (cooldowns)
        return [] # Base agent makes no actual trading decisions
```
