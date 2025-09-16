import os
import json
import pandas as pd
from collections import defaultdict
from typing import Optional

NON_PROBING_LABELS = {"N", "Z"} # NOTE: update and rebuild map as needed


def load_label_map(save_path: str) -> Optional[tuple[dict, dict]]:
    """
    Load a label map from disk.

    Parameters:
        save_path (str): Path to load label_map.json

    Returns:
        label_map (Dict[str, int]): normalized to uppercase
        inv_label_map (Dict[int, str]): inverse mapping
    """
    if not os.path.exists(save_path):
        return None
    
    with open(save_path, "r") as f:
        raw_label_map = json.load(f)

    label_map = {k.upper(): int(v) for k, v in raw_label_map.items()}

    inv_label_map = defaultdict(list)
    for label, value in label_map.items():
        inv_label_map[value].append(label)
    return label_map, dict(inv_label_map)

def build_label_map(dataframes: list[pd.DataFrame], label_column = "labels") -> tuple[dict, dict]:
    """
    Build probing label map from a list of DataFrames and writes to `label_map.json`.
    "N" and "Z" are non-probing (0), all other labels are probing (1).    

    Parameters:
        dataframes: List of pandas DataFrames with a column containing labels.
        label_column (str): Column containing label strings (e.g. "Z", "D", "F1")

    Returns:
        label_map (Dict[str, int]): mapping of each original label to 0 or 1
        inv_label_map (Dict[int, list[str]]): reverse mapping from 0/1 to original labels
    """
    all_labels = set()
    for df in dataframes:
        labels = df[label_column].dropna().unique()
        all_labels.update(label.upper() for label in labels)

    label_map = {
        label: 0 if label in NON_PROBING_LABELS else 1
        for label in sorted(all_labels)
    }
    
    inv_label_map = {0: [], 1: []}
    for label, val in label_map.items():
        inv_label_map[val].append(label)

    output_path = os.path.join(os.path.dirname(__file__), 'label_map.json')
    with open(output_path, "w") as f:
        json.dump(label_map, f, indent=4)

    return label_map, inv_label_map