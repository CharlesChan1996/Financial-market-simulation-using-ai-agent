from typing import List, Dict, Any, Optional
import datetime # For more robust date handling if needed in future
import os # For path operations in the example

# Import necessary classes from other modules
from financial_market_simulator.agents import Agent, RandomAgent, TechnicalAgent, FundamentalAgent # Import all agent types
from financial_market_simulator.market_simulation.environment import MarketEnvironment, Order
# Import analysis functions if they are to be called from here (typically in main script or __main__ block)
from financial_market_simulator.results_analysis.analysis import (
    plot_agent_wealth_over_time,
    plot_final_wealth_distribution,
    print_profit_loss_summary
)

class Simulation:
    """
    Manages the overall financial market simulation process.

    This class coordinates the interactions between the market environment and various trading agents.
    It handles the simulation loop, agent creation, order submission, market state updates,
    and collection of results.
    """
    def __init__(self, market_env: MarketEnvironment, agents_config: List[Dict[str, Any]]):
        """
        Initializes the Simulation.

        Args:
            market_env: An instance of MarketEnvironment that defines the market for the simulation.
            agents_config: A list of dictionaries, where each dictionary specifies the configuration
                           for a group of agents to be created. Expected keys per dictionary:
                           - 'type' (str): The type of agent (e.g., "random", "technical").
                           - 'count' (int): The number of agents of this type to create.
                           - 'initial_capital' (float): The initial capital for each agent in this group.
                           - (Optional) 'tradable_instruments' (List[str]): Instruments specific to this agent group.
                               If not provided, defaults to all tradable instruments in the market_env.
                           - (Optional) Other agent-specific parameters can be included and should be handled
                             by the respective agent's __init__ method if passed through.
        """
        self.market_env: MarketEnvironment = market_env
        self.agents: List[Agent] = [] # List to store all agent instances
        self.agents_by_id: Dict[str, Agent] = {} # For quick lookup of agents by their ID
        self.results: List[Dict[str, Any]] = [] # Stores per-step simulation data

        # Mapping of agent type strings (from config) to their respective classes.
        agent_type_map = {
            "random": RandomAgent,
            "technical": TechnicalAgent,
            "fundamental": FundamentalAgent,
            "base": Agent # Allow creation of base Agent if specified, though it won't trade.
        }

        current_agent_numeric_id_counter = 0 # Used to generate unique numeric parts of agent IDs
        for config_item in agents_config:
            agent_type_str = config_item.get('type', 'random').lower() # Default to 'random' if type not specified
            count = config_item.get('count', 1)
            initial_capital = config_item.get('initial_capital', 10000.0)

            # Agents can trade all instruments in the market by default, or a specific list from config.
            agent_tradable_instruments = config_item.get('tradable_instruments') or self.market_env.tradable_instruments

            agent_class_to_create = agent_type_map.get(agent_type_str)
            if not agent_class_to_create:
                # print(f"Warning (Simulation Init): Unknown agent type '{agent_type_str}' in config. Defaulting to RandomAgent.")
                agent_class_to_create = RandomAgent # Fallback for unknown types

            for _ in range(count):
                # Generate a unique agent ID.
                agent_id = f"{agent_type_str}_{current_agent_numeric_id_counter}"
                current_agent_numeric_id_counter += 1

                # Instantiate the agent.
                # trading_belief is now typically set within each agent's __init__ method.
                agent_instance = agent_class_to_create(
                    agent_id=agent_id,
                    initial_capital=initial_capital,
                    tradable_instruments=agent_tradable_instruments,
                    market_env_ref=self.market_env
                    # Specific agent subclasses handle their `trading_belief` internally.
                )

                # Allow overriding learning_params from config if provided
                if 'learning_params' in config_item and hasattr(agent_instance, 'learning_params'):
                    agent_instance.learning_params.update(config_item['learning_params'])

                self.agents.append(agent_instance)
                self.agents_by_id[agent_id] = agent_instance

        # print(f"Info (Simulation Init): Simulation initialized with {len(self.agents)} agents.")


    def run(self, num_steps: Optional[int] = None) -> None:
        """
        Runs the main simulation loop for a specified number of steps or until the market end date.

        In each step (typically representing one day):
        1.  Agents receive current market prices and make trading decisions (generating orders).
        2.  Submitted orders are processed by the market environment.
        3.  The market time advances, and trade confirmations are generated.
        4.  Agents' portfolios, cash, and memory are updated based on trade outcomes.
        5.  Data for the step (agent wealth, trades) is collected.

        Args:
            num_steps: The number of simulation steps (days) to run.
                       If None, the simulation runs until `market_env.current_date`
                       exceeds `market_env.end_date`.
        """
        steps_taken = 0
        max_steps_defined = num_steps is not None

        # print(f"Info (Simulation Run): Starting simulation from {self.market_env.current_date} to {self.market_env.end_date}.")
        # if max_steps_defined:
        #     print(f"Info (Simulation Run): Simulation will run for a maximum of {num_steps} steps.")

        # Main simulation loop
        while True:
            current_sim_date_for_step = self.market_env.current_date # Date at the beginning of the step

            # --- Termination Conditions ---
            if max_steps_defined and steps_taken >= num_steps:
                # print(f"Info (Simulation Run): Ended after {num_steps} specified steps.")
                break
            if current_sim_date_for_step > self.market_env.end_date:
                # print(f"Info (Simulation Run): Loop terminating. Current step date {current_sim_date_for_step} is beyond end date {self.market_env.end_date}.")
                break

            # print(f"\n--- Simulation Step {steps_taken + 1}: Date {current_sim_date_for_step} ---")

            # --- Agent Decision Phase ---
            current_market_prices = self.market_env.get_current_prices() # Prices for current_sim_date_for_step
            if not current_market_prices and current_sim_date_for_step <= self.market_env.end_date:
                # Only warn if prices are expected (i.e., not past end_date where data might be missing)
                # print(f"Warning (Simulation Run): No market prices available for {current_sim_date_for_step}. Agents may not trade effectively.")
                pass


            for agent in self.agents:
                # Agents make decisions based on prices at the start of the day.
                agent_orders: List[Order] = agent.make_decision(dict(current_market_prices)) # Pass a copy
                for order in agent_orders:
                    # Ensure agent_id in order matches the agent submitting it (consistency check)
                    if order.agent_id != agent.agent_id:
                        # print(f"Warning (Simulation Run): Agent {agent.agent_id} submitted order with mismatched ID {order.agent_id}. Correcting.")
                        order = order._replace(agent_id=agent.agent_id)
                    # print(f"Trace (Simulation Run): Agent {agent.agent_id} submits order: {order}")
                    self.market_env.submit_order(order)

            # --- Market Update Phase ---
            # advance_time() moves to the *next* day and processes orders based on the state *before* advancing.
            # Trade confirmations are for trades executed based on orders submitted for current_sim_date_for_step.
            trade_confirmations: List[Dict[str, Any]] = self.market_env.advance_time()

            # --- Agent Update Phase (Post-Trade) ---
            for confirmation in trade_confirmations:
                executed_order: Order = confirmation['executed_order']
                agent_id_from_conf = confirmation['agent_id'] # Agent ID involved in the trade

                agent_to_update = self.agents_by_id.get(agent_id_from_conf)
                if agent_to_update:
                    instrument = executed_order.instrument
                    order_type = confirmation['order_type'] # 'buy' or 'sell' from confirmation
                    executed_quantity = confirmation['quantity']
                    executed_price = confirmation['price']

                    # Update cash and portfolio
                    if order_type == 'buy':
                        agent_to_update.cash -= executed_quantity * executed_price
                        agent_to_update.portfolio[instrument] = agent_to_update.portfolio.get(instrument, 0) + executed_quantity
                    elif order_type == 'sell':
                        agent_to_update.cash += executed_quantity * executed_price
                        agent_to_update.portfolio[instrument] = agent_to_update.portfolio.get(instrument, 0) - executed_quantity
                        if agent_to_update.portfolio[instrument] == 0:
                            del agent_to_update.portfolio[instrument] # Clean up portfolio if quantity is zero

                    # Update agent's memory
                    # Prices for memory context are from the day the trade executed (current_sim_date_for_step)
                    prices_on_trade_date = self.market_env.get_market_data_for_date(current_sim_date_for_step)
                    agent_to_update.update_memory(confirmation, prices_on_trade_date)

                    # print(f"Trace (Simulation Run): Agent {agent_to_update.agent_id} updated. Cash: {agent_to_update.cash:.2f}, Portfolio: {agent_to_update.portfolio}")
                # else:
                    # print(f"Warning (Simulation Run): Agent with ID {agent_id_from_conf} from trade confirmation not found.")


            # --- Data Collection for Results (End of Step) ---
            # Agent valuations are based on market prices at current_sim_date_for_step (end of that day).
            valuation_prices_for_step = self.market_env.get_market_data_for_date(current_sim_date_for_step)
            if not valuation_prices_for_step and current_sim_date_for_step <= self.market_env.end_date:
                # print(f"Warning (Simulation Run): No market prices for valuation on {current_sim_date_for_step}. Agent values may be based on last known or zero.")
                pass


            agent_values_this_step = []
            for agent in self.agents:
                total_value = agent.get_total_value(valuation_prices_for_step)
                agent_values_this_step.append({
                    'agent_id': agent.agent_id,
                    'value': total_value,
                    'cash': agent.cash,
                    'portfolio': dict(agent.portfolio) # Store a copy of portfolio state
                })

            self.results.append({
                'date': current_sim_date_for_step, # Date for which decisions were made and trades occurred
                'agent_values': agent_values_this_step,
                'trades_this_step': len(trade_confirmations) // 2 # Each trade generates two confirmations (buyer/seller)
            })

            steps_taken += 1

            # Check if simulation should end *after* this step because advance_time() might have pushed
            # self.market_env.current_date past self.market_env.end_date.
            if self.market_env.current_date > self.market_env.end_date and \
               current_sim_date_for_step <= self.market_env.end_date:
                # print(f"Info (Simulation Run): Market period ended. current_date {self.market_env.current_date} is past end_date {self.market_env.end_date} "
                #       f"after step for {current_sim_date_for_step}.")
                break

        # print(f"\nInfo (Simulation Run): Simulation finished. Total steps: {steps_taken}. Results collected for {len(self.results)} days.")

    def get_results(self) -> List[Dict[str, Any]]:
        """Returns the collected simulation results."""
        return self.results

# Example Usage: This block demonstrates how to set up and run a simulation.
# It's typically run when this script is executed directly.
if __name__ == '__main__':
    # 1. Define Market Environment
    tradable_instruments_main = ['AAPL', 'GOOG']
    market_main = MarketEnvironment(
        start_date='2023-01-01',
        end_date='2023-01-05', # Extended for a few more steps to observe behavior
        tradable_instruments=tradable_instruments_main
    )
    # Manually add a bit more market data for the extended dates if _initialize_market_data is static
    # This ensures agents have prices to react to.
    if 'AAPL' in market_main.tradable_instruments:
        market_main.market_data.setdefault('AAPL', {}).update({
            '2023-01-04': 150.50, '2023-01-05': 149.75
        })
    if 'GOOG' in market_main.tradable_instruments:
        market_main.market_data.setdefault('GOOG', {}).update({
            '2023-01-04': 2700.00, '2023-01-05': 2680.50
        })


    # 2. Define Agent Configuration for the Simulation
    # This list of dictionaries drives the creation of different agent types.
    agents_config_main = [
        {'type': 'random', 'count': 2, 'initial_capital': 100000},
        {'type': 'technical', 'count': 1, 'initial_capital': 150000}, # Placeholder agent
        {'type': 'fundamental', 'count': 1, 'initial_capital': 120000}, # Placeholder agent
        # Example of overriding learning_params for a specific group, if Agent class supports it in __init__ or a setter.
        # Current Agent class __init__ doesn't directly take learning_params, but they can be set post-init.
        # The updated __init__ in this pass handles 'learning_params' from config.
        {'type': 'random', 'count': 1, 'initial_capital': 50000, 'learning_params': {'price_drop_threshold': 0.03, 'cooldown_period_days': 1}},
    ]

    # 3. Create Simulation with the configuration
    simulation_main = Simulation(market_env=market_main, agents_config=agents_config_main)

    # Example: Accessing and modifying an agent's parameter post-initialization if needed.
    # This demonstrates how one might fine-tune individual agents after batch creation.
    # Note: Agent IDs are generated (e.g., "random_0", "random_1", ... "random_3" for the last one here)
    # if "random_3" in simulation_main.agents_by_id: # Check if agent exists
    #    agent_to_modify = simulation_main.agents_by_id["random_3"]
    #    if hasattr(agent_to_modify, 'learning_params'):
    #        agent_to_modify.learning_params['price_drop_threshold'] = 0.02
    #        # print(f"Debug: Updated learning_params for {agent_to_modify.agent_id} to {agent_to_modify.learning_params}")


    # 4. Run Simulation
    simulation_main.run() # Runs until market_env.end_date or num_steps if provided

    # 5. Get and Analyze Results
    results = simulation_main.get_results()

    # Prepare directory for saving plots
    output_plot_dir = "financial_market_simulator/results/plots"
    if not os.path.exists(output_plot_dir):
        os.makedirs(output_plot_dir)
        # print(f"Info: Created directory for plots: {output_plot_dir}")

    # --- Print Summaries and Save Plots ---
    print("\n" + "="*30 + " AGENT FINAL STATES " + "="*30)
    for agent_instance in simulation_main.agents:
        print(f"Agent ID: {agent_instance.agent_id} (Type: {agent_instance.trading_belief})")
        print(f"  Cash: {agent_instance.cash:.2f}, Portfolio: {agent_instance.portfolio}")

        # Calculate final total value for display using prices from the market's end date
        final_day_prices = market_main.get_market_data_for_date(market_main.end_date)
        if not final_day_prices and results: # Fallback to last simulated day's prices if end_date has no data
            last_sim_date = results[-1]['date']
            final_day_prices = market_main.get_market_data_for_date(last_sim_date)
        total_value = agent_instance.get_total_value(final_day_prices if final_day_prices else {})
        print(f"  Final Calculated Value (EOD {market_main.end_date}): {total_value:.2f}")

        if hasattr(agent_instance, 'recent_bad_buys') and agent_instance.recent_bad_buys:
             cooldown_str = {k: v.strftime('%Y-%m-%d') for k,v in agent_instance.recent_bad_buys.items()}
             print(f"  Active Cooldowns: {cooldown_str}")
        # print(f"  Memory entries: {len(agent_instance.memory)}") # Memory can be extensive
    print("="*78)

    print(f"\nFinal state of Order Book: {market_main.order_book if market_main.order_book else 'Empty'}")

    print("\n" + "="*30 + " SIMULATION ANALYSIS " + "="*30)
    print_profit_loss_summary(results, simulation_main.agents)

    plot_agent_wealth_path = os.path.join(output_plot_dir, "agent_wealth_over_time.png")
    plot_agent_wealth_over_time(results, output_path=plot_agent_wealth_path)

    plot_final_wealth_dist_path = os.path.join(output_plot_dir, "final_wealth_distribution.png")
    plot_final_wealth_distribution(results, output_path=plot_final_wealth_dist_path)

    print(f"\nNote: Plots have been saved to '{os.path.abspath(output_plot_dir)}'.")
    print("To display plots interactively when running in a suitable environment, you might need to uncomment 'plt.show()' calls within the plotting functions in 'analysis.py'.")
```
