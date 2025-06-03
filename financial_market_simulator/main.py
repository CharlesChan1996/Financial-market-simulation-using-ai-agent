"""
Main entry point for running a basic Financial Market Simulation.

This script provides a simple example of how to set up and run the simulator
with a minimal configuration. For more detailed examples and analysis, refer to
`financial_market_simulator/market_simulation/simulation.py`.
"""
import os

# Import core simulation components
from financial_market_simulator.market_simulation.environment import MarketEnvironment
from financial_market_simulator.market_simulation.simulation import Simulation

# Import analysis functions (optional for a minimal main, but good for demonstration)
from financial_market_simulator.results_analysis.analysis import (
    print_profit_loss_summary,
    plot_agent_wealth_over_time
    # plot_final_wealth_distribution # Can be added if desired
)

def run_simple_simulation():
    """
    Sets up and runs a small-scale financial market simulation.
    """
    print("--- Starting Simple Financial Market Simulation ---")

    # 1. Define Market Environment
    # Using a small set of instruments and a short time period for simplicity.
    tradable_instruments = ['STOCK_A', 'STOCK_B']
    market = MarketEnvironment(
        start_date='2024-01-01',
        end_date='2024-01-10', # Simulate for 10 days
        tradable_instruments=tradable_instruments
    )

    # Manually add some basic market data for the instruments if not loaded from files.
    # This ensures the simulation can run. `_initialize_market_data` in MarketEnvironment
    # might already provide some, but explicitly adding ensures these instruments have data.
    for day in range(1, 11): # For 10 days
        date_str = f"2024-01-{day:02d}"
        market.market_data.setdefault('STOCK_A', {})[date_str] = 100.0 + day * 0.5 - (random.random() * 2)
        market.market_data.setdefault('STOCK_B', {})[date_str] = 75.0 - day * 0.2 + (random.random() * 1.5)
    # (Ensure random is imported if used here, or use a more deterministic pattern)
    import random # Added for the example market data generation above

    # 2. Define Agent Configuration
    # A small mix of agents for this simple run.
    agents_config = [
        {'type': 'random', 'count': 3, 'initial_capital': 50000},
        {'type': 'random', 'count': 2, 'initial_capital': 75000, 'learning_params': {'price_drop_threshold': 0.1, 'cooldown_period_days': 3}},
        # {'type': 'technical', 'count': 1, 'initial_capital': 100000}, # Placeholder agents
    ]

    # 3. Create and Run Simulation
    simulation = Simulation(market_env=market, agents_config=agents_config)
    simulation.run() # Runs until market.end_date

    # 4. Analyze Results
    results = simulation.get_results()

    if results: # Proceed only if simulation generated results
        print("\n--- Basic Simulation Analysis ---")
        print_profit_loss_summary(results, simulation.agents)

        # Optional: Generate and save a plot for agent wealth
        output_plot_dir = "financial_market_simulator/results/plots_main_example"
        if not os.path.exists(output_plot_dir):
            os.makedirs(output_plot_dir)
            print(f"Created directory for plots: {output_plot_dir}")

        plot_path = os.path.join(output_plot_dir, "simple_agent_wealth.png")
        plot_agent_wealth_over_time(results, output_path=plot_path)
        print(f"Agent wealth plot saved to: {os.path.abspath(plot_path)}")
    else:
        print("Simulation did not generate any results to analyze.")

    print("\n--- Simple Financial Market Simulation Finished ---")

if __name__ == '__main__':
    run_simple_simulation()
```
