import re
import ast
import math
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import argparse


"""
This script parses a text file containing hyperparameter search results and 
creates an interactive multi-panel plot of each hyperparameter value 
versus the optuna score using Plotly.

Each line in the input file is expected to be in the following format:
    <timestamp> <trial_id> <hyperparameter_dict> <optuna_score>

Example line:
    2025-07-24 02:28:19.851503 9 {'epochs': 32, 'lr': 0.005, 'dropout': 0.0001, 'weight_decay': 1e-07, 'num_layers': 8, 'features': 64} 0.5350332402949146

Usage:
    python hyperparameter_plot.py results.txt --output results_plot.html
"""

def parse_log_file(filepath):
    """
    Parses a log file where each line contains:
        <timestamp> <trial_id> <hyperparam_dict> <F1_score>

    Returns:
        pd.DataFrame: One row per trial, with hyperparameters and F1 score
    """
    pattern = re.compile(r"(\{.*?\})\s+([0-9.]+)$")
    records = []

    with open(filepath, "r") as file:
        for line in file:
            try:
                match = pattern.search(line.strip())
                if not match:
                    raise ValueError("No match found in line")

                dict_str, f1_str = match.groups()
                hyperparams = ast.literal_eval(dict_str)
                hyperparams["F1"] = float(f1_str)
                records.append(hyperparams)
            except Exception as e:
                print(f"Skipping line due to error: {e}\n  Line: {line.strip()}")

    return pd.DataFrame(records)

def create_plot(df, output_file="hyperparameter_plot.html"):
    """
    Creates interactive subplots for each hyperparameter vs. F1 score.

    Args:
        df (pd.DataFrame): DataFrame with hyperparameter columns and 'F1'
        output_file (str): Path to save the HTML output
    """
    param_names = [col for col in df.columns if col != "F1"]
    num_params = len(param_names)
    cols = 2
    rows = math.ceil(num_params / cols)

    fig = make_subplots(rows=rows, cols=cols, subplot_titles=param_names)

    for i, param in enumerate(param_names):
        row = i // cols + 1
        col = i % cols + 1

        x = df[param]
        y = df["F1"]

        fig.add_trace(go.Scatter(
            x=x,
            y=y,
            mode="markers",
            marker=dict(size=8, color='blue'),
            name=param,
            showlegend=False
        ), row=row, col=col)

    # Build list of xaxis keys to control
    axis_updates_linear = {}
    axis_updates_log = {}

    for i in range(1, num_params + 1):
        axis_key = "xaxis" if i == 1 else f"xaxis{i}"
        axis_updates_linear[f"{axis_key}.type"] = "linear"
        axis_updates_log[f"{axis_key}.type"] = "log"


        fig.update_layout({
            axis_key: dict(
                exponentformat="power",  # show multiplier
                showexponent="all",      # always display it
                tickformat=".1~g"         # control decimal formatting
            )
        })

    fig.update_layout(
        height=300 * rows,
        width=1000,
        title="Hyperparameter vs Weighted F1 Score",
        updatemenus=[
            {
                "buttons": [
                    {
                        "label": "Linear X-Scale",
                        "method": "relayout",
                        "args": [axis_updates_linear]
                    },
                    {
                        "label": "Log X-Scale",
                        "method": "relayout",
                        "args": [axis_updates_log]
                    }
                ],
                "type": "buttons",
                "direction": "left",
                "x": 0.0,
                "xanchor": "left",
                "y": 1.15,
                "yanchor": "top"
            }
        ]
    )

    fig.write_html(output_file)
    print(f"Plot saved to: {output_file}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", help="Path to .txt file with Optuna logs")
    parser.add_argument("--output", default="hyperparameter_plot.html", help="Output HTML file name")
    args = parser.parse_args()

    df = parse_log_file(args.input_file)
    if df.empty:
        print("No valid trials found.")
    else:
        create_plot(df, args.output)

if __name__ == "__main__":
    main()