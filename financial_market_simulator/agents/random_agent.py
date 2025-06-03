import random
from typing import List, Dict, TYPE_CHECKING

from .agent import Agent # Import base Agent class
from financial_market_simulator.market_simulation.environment import Order # Import Order

if TYPE_CHECKING:
    from financial_market_simulator.market_simulation.environment import MarketEnvironment

class RandomAgent(Agent):
    """
    An agent that makes random trading decisions (buy or sell).

    This agent demonstrates basic trading behavior. It randomly chooses whether to attempt
    a buy or a sell for tradable instruments. Buy decisions are subject to a cooldown
    mechanism inherited from the base `Agent` class, where recently unprofitable buys
    for an instrument will temporarily prevent new buys of that same instrument.
    Sell decisions are made if the agent possesses the instrument.
    All trades are for a fixed quantity of 1 unit.
    """
    def __init__(self,
                 agent_id: str,
                 initial_capital: float,
                 tradable_instruments: List[str],
                 market_env_ref: 'MarketEnvironment',
                 trading_belief: str = "random_learner"): # Default belief for this agent type
        """
        Initializes a RandomAgent.

        Args:
            agent_id: Unique identifier for the agent.
            initial_capital: Starting cash for the agent.
            tradable_instruments: List of instrument symbols the agent can trade.
            market_env_ref: Reference to the market environment.
            trading_belief: The agent's belief system (defaults to "random_learner").
        """
        super().__init__(agent_id, initial_capital, tradable_instruments, trading_belief, market_env_ref)

    def make_decision(self, current_day_market_prices: Dict[str, float]) -> List[Order]:
        """
        Makes random trading decisions (buy or sell) based on current market prices
        and any learned cooldowns from past unprofitable buy trades.

        The agent iterates through tradable instruments. For each, it randomly decides
        whether to trade. If it decides to trade, it randomly chooses between buying
        (if not on cooldown and affordable) or selling (if shares are held).

        Args:
            current_day_market_prices: A dictionary of current market prices for tradable instruments.

        Returns:
            A list of Order objects representing the trades the agent decides to make.
        """
        # First, call the learning evaluation from the base class to update cooldowns
        super().evaluate_past_trades(current_day_market_prices) # This updates self.recent_bad_buys

        orders: List[Order] = []

        if not self.market_env_ref: # Should be set during __init__
            # print(f"Warning (Agent {self.agent_id}): Market environment reference not set. Cannot make decisions.")
            return []

        current_sim_date_str = self.market_env_ref.current_date
        current_sim_datetime = self._str_to_datetime(current_sim_date_str)

        if not current_sim_datetime:
            # print(f"Warning (Agent {self.agent_id}): Could not parse current simulation date for decision: {current_sim_date_str}")
            return []

        # Iterate through each instrument the agent is allowed to trade
        for instrument in self.tradable_instruments:
            instrument_price = current_day_market_prices.get(instrument)
            if instrument_price is None:
                # If no price data for the instrument today, cannot trade it.
                # print(f"Trace (Agent {self.agent_id}): No price for {instrument} on {current_sim_date_str}, cannot trade.")
                continue

            # Random chance to consider trading this instrument
            if random.random() < 0.15: # e.g., 15% chance to consider a trade for this instrument per day

                # Determine if buying is an option (not on cooldown)
                can_buy = True
                if instrument in self.recent_bad_buys:
                    if self.recent_bad_buys[instrument] > current_sim_datetime:
                        # print(f"Trace (Agent {self.agent_id}): Cooldown active for {instrument}. No buy consideration.")
                        can_buy = False # Cooldown is active for this instrument

                # Determine if selling is an option (owns the instrument)
                can_sell = self.portfolio.get(instrument, 0) > 0

                possible_actions = []
                if can_buy and self.cash >= instrument_price: # Check affordability for buying
                    possible_actions.append('buy')
                if can_sell:
                    possible_actions.append('sell')

                if not possible_actions: # No actions possible for this instrument (e.g., on cooldown and no shares to sell)
                    continue

                chosen_action = random.choice(possible_actions)
                quantity_to_trade = 1 # Simple: trade 1 unit

                if chosen_action == 'buy':
                    # print(f"INFO (Agent {self.agent_id}): Decides to BUY {quantity_to_trade} of {instrument} at {instrument_price:.2f}")
                    orders.append(Order(
                        agent_id=self.agent_id,
                        instrument=instrument,
                        quantity=quantity_to_trade,
                        order_type='buy',
                        price=instrument_price, # Placing a limit order at the current market price for simplicity
                        timestamp=current_sim_date_str # Timestamp of order creation
                    ))

                elif chosen_action == 'sell':
                    # print(f"INFO (Agent {self.agent_id}): Decides to SELL {quantity_to_trade} of {instrument} at {instrument_price:.2f}")
                    orders.append(Order(
                        agent_id=self.agent_id,
                        instrument=instrument,
                        quantity=quantity_to_trade,
                        order_type='sell',
                        price=instrument_price, # Using current price as limit price for simplicity
                        timestamp=current_sim_date_str
                    ))
        return orders
```
