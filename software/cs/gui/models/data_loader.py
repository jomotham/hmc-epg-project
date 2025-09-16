import os
import pandas as pd
from pathlib import Path
from typing import Union, Optional
from collections import Counter
from collections.abc import Iterable

from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from sklearn.model_selection import train_test_split


def import_data(
    data_path: Union[str, Path],
    filetype: str,
    exclude: Optional[Iterable[str]] = None,
    include: Optional[Iterable[str]] = None
):
    """
    Loads and processes EPG datasets into a list of DataFrames, each with metadata in attrs["file"].

    Parameters:
    -----------
    data_path : str or Path
        Directory containing the data files.
    filetype : str
        File extension to match (".csv" or ".parquet").
    exclude : iterable of str, optional
        Substrings to exclude from filenames.
    include : iterable of str, optional
        Substrings to include in filenames (must match at least one to be included).

    Returns:
    --------
    list[pd.DataFrame]
        A list of DataFrames with the source filename stored in .attrs["file"].
    """
    exclude = set(s.lower() for s in exclude) if exclude else set()
    include = set(s.lower() for s in include) if include else None

    # collect files to be read
    filepaths = []
    for f in Path(data_path).expanduser().glob(f"*{filetype}"):
        fname = f.name.lower()
        if exclude and any(s in fname for s in exclude):
            continue
        if include and not any(s in fname for s in include):
            continue
        filepaths.append(str(f))

    def read_file(filepath):
        """Helper function to read and clean a single file based on extension."""
        if filepath.endswith(".csv"):
            df = pd.read_csv(filepath, index_col=0, engine="pyarrow")
            df.drop(columns=["post_rect"], errors="ignore", inplace=True)
        elif filepath.endswith(".parquet"):
            df = pd.read_parquet(filepath, columns=["time", "pre_rect", "labels"], engine="pyarrow")
            df.reset_index(drop=True, inplace=True)
        else:
            return None
        
        if 'CD' in df["labels"].values:
            df.loc[df['labels'] == 'CD', 'labels'] = 'D'
        
        df.rename(columns={"pre_rect": "voltage"}, inplace=True)
        df.attrs["file"] = filepath
        return df

    # multi-threaded reading
    dataframes = []
    total_bytes = 0
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(read_file, path): path for path in filepaths}
        progress_bar = tqdm(
            as_completed(futures),total=len(futures), 
            desc=f"Reading {len(futures)} {filetype} files"
        )
        for future in progress_bar:
            df = future.result()
            if df is not None:
                dataframes.append(df)
                total_bytes += os.path.getsize(futures[future])
    elapsed_time = progress_bar.format_dict["elapsed"]
    total_gb = total_bytes / (1024 * 1024 * 1024)

    tqdm.write(f"Loaded {len(dataframes)} files ({total_gb:.2f} GB) in {elapsed_time:.2f} seconds.")

    dataframes.sort(key=lambda df: df.attrs.get("file", ""))
    return dataframes


def stratified_split(
    dfs, 
    quality_map,
    train_size=0.8, val_size=0.0, test_size=0.2,
    fallback="random",
    random_state=42
):
    assert fallback in ("random", "hybrid"), "fallback must be 'random' or 'hybrid'"
    
    def extract_id_from_filename(filename: str) -> str:
        import re
        match = re.search(r"sharpshooter_([a-zA-Z0-9]+)_labeled\.parquet", filename)
        if match:
            return match.group(1)
        raise ValueError(f"Could not extract ID from filename: {filename}")

    items = []
    for df in dfs:
        filename = df.attrs.get("file", "")
        recording_id = extract_id_from_filename(filename)
        quality = quality_map.get(recording_id)
        if quality is None:
            raise ValueError(f"No quality label found for recording ID '{recording_id}'")
        items.append((df, quality))

    dfs_list, qualities = zip(*items)

    # === SPECIAL CASE: only train split ===
    if val_size == 0.0 and test_size == 0.0:
        return list(dfs_list), [], []

    # === SPECIAL CASE: train/val only ===
    if test_size == 0.0:
        train_dfs, val_dfs, _, _ = train_test_split(
            dfs_list, qualities,
            stratify=qualities,
            test_size=val_size,
            random_state=random_state
        )
        return train_dfs, val_dfs, []

    # === NORMAL 3-WAY SPLIT ===
    train_dfs, temp_dfs, train_quals, temp_quals = train_test_split(
        dfs_list, qualities,
        stratify=qualities,
        test_size=(val_size + test_size),
        random_state=random_state
    )

    val_ratio = val_size / (val_size + test_size)
    temp_class_counts = Counter(temp_quals)

    if all(count >= 2 for count in temp_class_counts.values()):
        val_dfs, test_dfs, _, _ = train_test_split(
            temp_dfs, temp_quals,
            stratify=temp_quals,
            test_size=(1 - val_ratio),
            random_state=random_state
        )
    elif fallback == "random":
        print("Not enough samples in some classes - using random val/test split.")
        val_dfs, test_dfs = train_test_split(
            temp_dfs,
            test_size=(1 - val_ratio),
            random_state=random_state
        )
    elif fallback == "hybrid":
        print("Not enough samples in some classes - using hybrid val/test split.")
        common = [(x, y) for x, y in zip(temp_dfs, temp_quals) if temp_class_counts[y] >= 2]
        rare = [(x, y) for x, y in zip(temp_dfs, temp_quals) if temp_class_counts[y] < 2]

        val_common, test_common, val_rare, test_rare = [], [], [], []

        if common:
            common_X, common_y = zip(*common)
            val_common, test_common = train_test_split(
                common_X, stratify=common_y,
                test_size=(1 - val_ratio),
                random_state=random_state
            )
        if rare:
            rare_X = [x for x, _ in rare]
            val_rare, test_rare = train_test_split(
                rare_X,
                test_size=(1 - val_ratio),
                random_state=random_state
            )

        val_dfs = list(val_common) + list(val_rare)
        test_dfs = list(test_common) + list(test_rare)

    return train_dfs, val_dfs, test_dfs
