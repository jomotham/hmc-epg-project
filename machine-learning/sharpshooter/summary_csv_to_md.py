import pandas as pd
from pathlib import Path


"""
Takes an summary output csv from optuna and formats it as a markdown tables
"""

# Load CSV
df = pd.read_csv(r".\RF_SummaryStats.csv")

# Get the list of metric-label pairs from column headers
metric_cols = df.columns[df.columns.str.contains("precision_|recall_|fscore_")]

# Parse out label names
label_metrics = {}
for col in metric_cols:
    metric, label = col.split("_", 1)
    if label not in label_metrics:
        label_metrics[label] = {}
    label_metrics[label][metric] = col

# Display each label in its own table
for label, metrics in sorted(label_metrics.items()):
    print(f"\n Metrics for label: **{label}**")
    
    # Collect the precision, recall, and fscore columns
    subset = df[[metrics.get("precision", None),
                 metrics.get("recall", None),
                 metrics.get("fscore", None)]].copy()
    subset.columns = ["Precision", "Recall", "F1 Score"]

    subset = subset.fillna(0.0)

    # Add Fold numbers and Summary row label
    subset.index = [f"Fold {i}" for i in range(len(subset)-1)] + ["Summary"] if len(subset) > 1 else ["Summary"]

    print(subset.round(3).to_markdown())
