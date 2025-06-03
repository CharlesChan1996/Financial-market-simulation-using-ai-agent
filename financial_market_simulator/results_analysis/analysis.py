import matplotlib.pyplot as plt
import numpy as np
from typing import List, Dict, Optional, TYPE_CHECKING, Any

if TYPE_CHECKING:
    # For type hinting Agent objects without causing circular imports at runtime.
    from financial_market_simulator.agents.agent import Agent


def plot_agent_wealth_over_time(simulation_results: List[Dict[str, Any]], output_path: Optional[str] = None) -> None:
    """
    Plots the wealth of each agent over the course of the simulation.

    Each agent's wealth trajectory is plotted as a line on a time series graph.
    This helps visualize individual agent performance and overall wealth dynamics.

    Args:
        simulation_results: A list of dictionaries, where each dictionary represents
                            a time step (day) of the simulation. Each dictionary should contain:
                            - 'date' (str): The date of the simulation step.
                            - 'agent_values' (List[Dict[str, Any]]): A list where each sub-dictionary
                              contains 'agent_id' (str) and 'value' (float) for an agent's wealth.
        output_path: Optional. If provided, the plot is saved to this file path (e.g., "path/to/plot.png").
                     If None, the plot is displayed using `plt.show()`.
    """
    if not simulation_results:
        # print("Warning (plot_agent_wealth): No simulation results provided. Cannot generate plot.")
        return

    dates = [res['date'] for res in simulation_results if 'date' in res]
    if not dates:
        # print("Warning (plot_agent_wealth): 'date' key missing in simulation results.")
        return

    # Prepare data structure to hold wealth history for each agent.
    # Initialize with all known agent IDs from the first step's agent_values.
    first_step_agent_values = simulation_results[0].get('agent_values')
    if not first_step_agent_values or not isinstance(first_step_agent_values, list):
        # print("Warning (plot_agent_wealth): 'agent_values' is missing or invalid in the first simulation result.")
        return

    agent_ids = [av['agent_id'] for av in first_step_agent_values if 'agent_id' in av]
    if not agent_ids:
        # print("Warning (plot_agent_wealth): No 'agent_id' found in the first step's 'agent_values'.")
        return

    agent_wealth_history: Dict[str, List[Optional[float]]] = {agent_id: [] for agent_id in agent_ids}

    # Populate wealth history for each agent across all time steps.
    for result_step in simulation_results:
        current_step_agent_values_map = {av['agent_id']: av.get('value')
                                         for av in result_step.get('agent_values', []) if 'agent_id' in av}
        for agent_id in agent_ids:
            # Append wealth if found, otherwise append None (or np.nan) to maintain sequence length.
            agent_wealth_history[agent_id].append(current_step_agent_values_map.get(agent_id))

    plt.figure(figsize=(14, 8)) # Larger figure size for better readability

    for agent_id, wealth_history in agent_wealth_history.items():
        # Convert list with Nones to numpy array with NaNs for plotting compatibility if some agents drop out.
        plottable_wealth_history = [w if w is not None else np.nan for w in wealth_history]
        if not all(np.isnan(w) for w in plottable_wealth_history): # Plot if there's at least one non-NaN value
            plt.plot(dates, plottable_wealth_history, label=agent_id, marker='.', linestyle='-', markersize=5)

    plt.title("Agent Wealth Over Time", fontsize=16)
    plt.xlabel("Time Step (Day)", fontsize=12)
    plt.ylabel("Total Wealth (Cash + Portfolio Value)", fontsize=12)

    # Improve date label display: show fewer labels if too many dates to avoid overlap.
    num_dates = len(dates)
    if num_dates > 20: # Heuristic: if more than 20 dates, show every Nth label.
        step = max(1, num_dates // 10) # Show around 10 labels
        plt.xticks(ticks=np.arange(0, num_dates, step), labels=[dates[i] for i in np.arange(0, num_dates, step)], rotation=45, ha="right")
    else:
        plt.xticks(rotation=45, ha="right")

    plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize=10) # Place legend outside plot area.
    plt.grid(True, linestyle=':', alpha=0.6) # Lighter grid
    plt.tight_layout(rect=[0, 0, 0.85, 1]) # Adjust layout to make room for legend outside

    if output_path:
        try:
            plt.savefig(output_path)
            # print(f"Info (plot_agent_wealth): Plot saved to {output_path}")
        except Exception as e:
            print(f"Error (plot_agent_wealth): Failed to save plot to {output_path}. Error: {e}")
        plt.close() # Close the figure to free memory, especially important in loops or batch runs.
    else:
        plt.show() # Display the plot if no output path is given.


def plot_final_wealth_distribution(simulation_results: List[Dict[str, Any]], output_path: Optional[str] = None, num_bins: int = 10) -> None:
    """
    Plots a histogram of the final wealth distribution of all agents at the end of the simulation.

    This helps understand the inequality or spread of wealth among agents.

    Args:
        simulation_results: The list of simulation step results.
        output_path: Optional. If provided, saves the histogram to this file path. Otherwise, displays it.
        num_bins: The number of bins to use for the histogram.
    """
    if not simulation_results:
        # print("Warning (plot_final_wealth_dist): No simulation results provided.")
        return

    final_step_results = simulation_results[-1] # Get the last day's results
    if not final_step_results.get('agent_values') or not isinstance(final_step_results['agent_values'], list):
        # print("Warning (plot_final_wealth_dist): 'agent_values' missing or invalid in the final simulation result.")
        return

    final_wealths = [av['value'] for av in final_step_results['agent_values'] if isinstance(av, dict) and av.get('value') is not None]

    if not final_wealths:
        # print("Warning (plot_final_wealth_dist): No final wealth data found to plot.")
        return

    plt.figure(figsize=(10, 6))
    plt.hist(final_wealths, bins=num_bins, edgecolor='black', alpha=0.75, color='skyblue')

    plt.title("Final Wealth Distribution of Agents", fontsize=16)
    plt.xlabel("Final Wealth", fontsize=12)
    plt.ylabel("Number of Agents", fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7) # Horizontal grid lines
    plt.tight_layout()

    if output_path:
        try:
            plt.savefig(output_path)
            # print(f"Info (plot_final_wealth_dist): Histogram saved to {output_path}")
        except Exception as e:
            print(f"Error (plot_final_wealth_dist): Failed to save histogram to {output_path}. Error: {e}")
        plt.close()
    else:
        plt.show()


def print_profit_loss_summary(simulation_results: List[Dict[str, Any]], agents: List['Agent']) -> None:
    """
    Calculates and prints a summary of profit and loss (P&L) for each agent,
    as well as total initial and final capital for all agents.

    Agents are sorted by their P&L in descending order for easier review.

    Args:
        simulation_results: The list of simulation step results from `Simulation.run()`.
        agents: The list of Agent objects that participated in the simulation,
                used to fetch their initial capital and trading belief.
    """
    if not simulation_results:
        # print("Warning (print_pnl_summary): No simulation results provided.")
        return
    if not agents:
        # print("Warning (print_pnl_summary): No agent data provided.")
        return

    # Map agent_id to their initial capital and trading belief for easy lookup.
    agent_details_map: Dict[str, Dict[str, Any]] = {
        agent.agent_id: {'initial_capital': agent.initial_capital, 'belief': agent.trading_belief}
        for agent in agents
    }

    final_step_results = simulation_results[-1]
    if not final_step_results.get('agent_values') or not isinstance(final_step_results['agent_values'], list):
        # print("Warning (print_pnl_summary): 'agent_values' missing or invalid in the final simulation result.")
        return

    # Extract final wealth for each agent from the last simulation step.
    agent_final_wealths_map: Dict[str, float] = {
        av['agent_id']: av['value']
        for av in final_step_results['agent_values'] if isinstance(av, dict) and 'agent_id' in av and 'value' in av
    }

    print("\n" + "="*27 + " PROFIT/LOSS SUMMARY " + "="*28) # Total 78 chars

    agent_pnl_data = []
    total_initial_capital_all_agents = 0.0
    total_final_wealth_all_agents = 0.0

    for agent_id, details in agent_details_map.items():
        initial_capital = details['initial_capital']
        belief = details['belief']

        final_wealth = agent_final_wealths_map.get(agent_id)
        if final_wealth is None:
            # This might happen if an agent somehow doesn't have a value in the last step's results.
            # print(f"Warning (print_pnl_summary): Agent {agent_id} - Final wealth not found. Using initial capital for P&L calculation.")
            final_wealth = initial_capital # Assume no change if final wealth is missing.

        profit_loss = final_wealth - initial_capital
        agent_pnl_data.append({
            'id': agent_id,
            'belief': belief,
            'initial': initial_capital,
            'final': final_wealth,
            'pnl': profit_loss,
        })
        total_initial_capital_all_agents += initial_capital
        total_final_wealth_all_agents += final_wealth

    # Sort agents by P&L in descending order for display.
    agent_pnl_data.sort(key=lambda x: x['pnl'], reverse=True)

    # Print table header
    header = f"{'Agent ID':<18} {'Belief':<28} {'Initial Cap.':>15} {'Final Wealth':>15} {'P&L':>15}"
    print(header)
    print("-" * len(header))

    # Print data for each agent
    for data in agent_pnl_data:
        print(f"{data['id']:<18} {data['belief']:<28} {data['initial']:>15.2f} {data['final']:>15.2f} {data['pnl']:>15.2f}")

    print("-" * len(header))
    # Print totals
    total_pnl = total_final_wealth_all_agents - total_initial_capital_all_agents
    print(f"{'TOTALS':<46} {total_initial_capital_all_agents:>15.2f} {total_final_wealth_all_agents:>15.2f} {total_pnl:>15.2f}")
    print("=" * len(header))
```
