import re
import argparse
import traceback
import pandas as pd
import windaq as wdq
from pathlib import Path
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed


################################################################################################################
# This parser pairs time-voltage data from .WDQ files with the corresponding labels from the label .CSV 
# based on the ID of the bug (see structure below). It is written specifically for the HPR 2017 sharpshooter 
# dataset (06/2017-07/2017, .WDQs and .CSV) provided by Dr. Backus, though may be expandable in the future 
# if all of their data is structured according to these bug IDs.
#
# In the provided dataset, the first 10hrs of recordings are labeled, with the second 10hrs unlabeled.
#
# It creates 4 directories:
#   sharpshooter_parsed: contains CSV-ified .WDQs with both labeled and unlabeled data
#   sharpshooter_labeled: the first 10hrs of the above CSVs
#   sharpshooter_unlabeled: the second 10hrs of the above CSVs
#   sharpshooter_parquet: .parquet versions of sharpshooter_labeled (format used for faster loading)  
#
# Each of the stages of the parsing process can be skipped with the following command-line flags:
#   --skip-wdq: skips the initial parsing of .WDQ files to raw .CSV format.
#   --skip-split: skips the split of raw .CSV files into labeled and unlabeled sections.
#   --skip-parquet: skips the conversion of labeled .CSV files to .parquet format.
################################################################################################################

# Bug ID Structure:
# letter: treatment
#       a: clean-grape
#       b: infec-grape
#       c: clean-wild
#       d: infec-wild
# first two numbers: rep number
#       e.g., 144 -> rep14
# third number: channel number (1-indexed w/ odd being pre-rect, even being post-rect)
#       e.g., 144 -> rep14 channel 4
#
# IDs need to be two numbers for the label CSV, so for three digit IDs:
#       0XX - drop the 0 (e.g., a082 -> a82 in csv)
#       1XX - drop the 1 (e.g., a144 -> a44 in csv)
#       20X - drop the 0 (e.g., c204 -> c24 in csv)
#   (this is their system, not ours)



ROOT_DIR = ROOT_DIR = Path(__file__).resolve().parent

# INPUT
WDQ_DIR = ROOT_DIR / "windaq_files"
LABEL_CSV_PATH = ROOT_DIR / "Backus BGSS 2017 HPR data - for Mudd CS.csv"

# OUTPUT
PARSED_OUTPUT_DIR = ROOT_DIR / "sharpshooter_parsed"
LABELED_OUTPUT_DIR = ROOT_DIR / "sharpshooter_labeled"
UNLABELED_OUTPUT_DIR = ROOT_DIR / "sharpshooter_unlabeled"
PARQUET_OUTPUT_DIR = ROOT_DIR / "sharpshooter_parquet"

PARSED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LABELED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
UNLABELED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PARQUET_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# hardcoded IDs from legend
BUG_IDS = [
    "a01", "a02", "a03", "a04", "a05", "a06", "a07", "a09", "a10", "a11",
    "a12", "a13", "a15", "a16", "a17", "a082", "a088", "a144", "a148", "a192",
    "b01", "b02", "b03", "b04", "b05", "b06", "b07", "b09", "b10", "b11",
    "b12", "b13", "b15", "b16", "b17", "b184", "b188", "b196", "b202", "b206", "b208", 
    "c01", "c02", "c03", "c06", "c07", "c08", "c09", "c10", "c11", "c12",
    "c13", "c14", "c15", "c16", "c17", "c046", "c048", "c182", "c186", "c204",
    "d01", "d02", "d03", "d06", "d07", "d08", "d09", "d10", "d11", "d12",
    "d13", "d14", "d15", "d16", "d17", "d056", "d058", "d194", "d196", "d198",
]

TREATMENT_MAP = {
    "a": "clean-grape",
    "b": "infec-grape",
    "c": "clean-wild",
    "d": "infec-wild",
}

def parse_bug_id(bug_id: str):
    """
    Extracts rep, csv_id, and channel_id from a bug_id like 'a144' or 'c204'
    """
    match = re.fullmatch(r"([a-d])(\d{2,3})", bug_id)
    if not match:
        raise ValueError(f"Invalid bug ID: {bug_id}")
    
    treatment, digits = match.groups()

    if len(digits) == 2:
        # e.g. 'a01' → rep1, channel=None, csv_id=a01
        rep = f"rep{int(digits)}"
        channel_id = None
        csv_id = bug_id

    elif len(digits) == 3:
        first, second, third = digits[0], digits[1], digits[2]

        if first == "0":
            # a082 → rep8, channel=2, csv_id=a82
            rep = f"rep{int(second)}"
            channel_id = int(third)
            csv_id = f"{treatment}{second}{third}"

        elif first == "1":
            # a144 → rep14, channel=4, csv_id=a44
            rep = f"rep{first}{second}"
            channel_id = int(third)
            csv_id = f"{treatment}{second}{third}"

        elif first == "2":
            # c204 → rep20, channel=4, csv_id=c24
            rep = f"rep{first}{second}"
            channel_id = int(third)
            csv_id = f"{treatment}{first}{third}"

        else:
            raise ValueError(f"Unhandled bug ID format: {bug_id}")

    else:
        raise ValueError(f"Unexpected bug ID length: {bug_id}")

    return rep, channel_id, csv_id

def wdq_parser(bug_id: str, label_df: pd.DataFrame):
    """
    Takes in a bug ID and dataframe of all labels, and converts the .WDQ files corresponding
    to this bug ID into a CSV, assigning it a "labels" column from the data in the label dataframe.
    """
    try:
        rep, channel_id, csv_id = parse_bug_id(bug_id)

        # Only works if there is are no duplicate reps. Additional duplicate reps are ignored
        pattern = re.compile(rf"(?:^|_)({re.escape(rep)})(?:_|$)")
        filepath = [
            str(path) for path in Path(WDQ_DIR).rglob(f"*{rep}*")
            if pattern.search(path.stem)
        ][0]

        daq = wdq.windaq(filepath)

        # Find channel ID of post-rect if it's not in bug ID
        if channel_id is None:
            treatment = TREATMENT_MAP.get(bug_id[0])
            if treatment is None:
                return f"{bug_id}: Unknown treatment"
            # Normalize for their treatment typos (- vs _, infec vs infect)
            treatment_regex = treatment.replace("-", "[-_]").replace("infec", "infect?")
            treatment_pattern = re.compile(treatment_regex, re.IGNORECASE)

            # Normalize for their post typos (post vs pos)
            post_pattern = re.compile(r"\bpos(?:t)?\b", re.IGNORECASE)
            channel_annotations = [daq.chAnnotation(x+1) for x in range(8)]

            # Find channel ID
            channel_id = next(
                (
                    i + 1
                    for i, annot in enumerate(channel_annotations)
                    if treatment_pattern.search(annot) and post_pattern.search(annot)
                ),
                None
            )

            if channel_id is None:
                if bug_id[1:] == "06": # hardcode for file w/ missing channel annotations
                    hardcoded_a06_map = {
                        "infec-grape": 2,
                        "clean-wild": 4,
                        "clean-grape": 6,
                        "infec-wild": 8
                    }
                    channel_id = hardcoded_a06_map.get(treatment)
                else:
                    return f"{bug_id}: Channel not found"

        df = pd.DataFrame(columns=["time", "pre_rect", "post_rect", "labels"])
        df["time"] = daq.time().astype("float32").round(3)
        df["pre_rect"] = daq.data(channel_id - 1).astype("float32")
        df["post_rect"] = daq.data(channel_id).astype("float32")

        # Get label data for this bug ID
        bug_labels = label_df[label_df["insectno"] == csv_id]
        if bug_labels.empty:
            return f"{bug_id}: No labels found"
        
        # Get end times and waveform labels
        label_end_times = bug_labels["tbf"].to_numpy()
        label_names = bug_labels["waveform"].to_numpy()

        # Prepend 0
        label_bins = [0] + list(label_end_times)

        # Assign label to each timestamp in the waveform
        df["labels"] = pd.cut(
            df["time"], bins=label_bins, labels=label_names,
            include_lowest=True, right=True, ordered=False
        )

        output_path = rf"{PARSED_OUTPUT_DIR}\sharpshooter_{bug_id}_raw.csv" # raw = contains both the labeled and unlabeled 10hr sections
        df.to_csv(output_path, index=True)
        return f"{bug_id}: Success"

    except Exception as e:
        return f"{bug_id}: Error - {e, traceback.print_exc()}"


def split_csv(csv_path: str, labeled_dir: str, unlabeled_dir: str):
    """
    Splits and writes a parsed CSV into labeled and unlabeled sections.
    """
    try:
        df = pd.read_csv(csv_path, index_col=0, low_memory=False)
        label_col = "labels"

        label_series = df[label_col]
        first_unlabeled_idx = label_series.isna() | (label_series == "")
        cutoff = first_unlabeled_idx.idxmax() if first_unlabeled_idx.any() else len(df)

        labeled = df.loc[:cutoff - 1]
        unlabeled = df.loc[cutoff:].drop(columns=[label_col])

        base_name = csv_path.stem.replace("_raw", "")
        labeled_path = labeled_dir / f"{base_name}_labeled.csv"
        unlabeled_path = unlabeled_dir / f"{base_name}_unlabeled.csv"

        labeled.to_csv(labeled_path)
        unlabeled.to_csv(unlabeled_path)

        return f"{csv_path.name}: {len(labeled)} labeled, {len(unlabeled)} unlabeled rows written"
    
    except Exception as e:
        return f"{csv_path.name}: Error - {e, traceback.print_exc()}"
    
def convert_csv_to_parquet(csv_path, index=True):
    output_file = PARQUET_OUTPUT_DIR / (Path(csv_path).stem + ".parquet")
    try:
        df = pd.read_csv(csv_path, low_memory=False)
        df.to_parquet(output_file, index=index)
        return f"Success: {csv_path} -> {output_file}"
    except Exception as e:
        return f"{csv_path.name}: Error - {e, traceback.print_exc()}"

def main():
    parser = argparse.ArgumentParser(description="Parse WDQ files and convert them to labeled/unlabeled CSVs and Parquet format.")
    parser.add_argument("--skip-wdq", action="store_true", help="Skip parsing .WDQ files into CSV")
    parser.add_argument("--skip-split", action="store_true", help="Skip splitting labeled/unlabeled sections")
    parser.add_argument("--skip-parquet", action="store_true", help="Skip converting labeled CSVs to Parquet")
    args = parser.parse_args()


    
    label_df = pd.read_csv(LABEL_CSV_PATH)
    if not args.skip_wdq:
        with ProcessPoolExecutor() as executor:
            futures = {executor.submit(wdq_parser, bug_id, label_df): bug_id for bug_id in BUG_IDS}
            for future in tqdm(as_completed(futures), total=len(futures), desc="Parsing WDQs to CSVs"):
                result = future.result()
                if "Error" in result:
                    print(result)

    parsed_files = list(PARSED_OUTPUT_DIR.glob("*.csv"))
    if not args.skip_split:
        with ProcessPoolExecutor() as executor:
            futures = {executor.submit(split_csv, path, LABELED_OUTPUT_DIR, UNLABELED_OUTPUT_DIR): path for path in parsed_files}
            for future in tqdm(as_completed(futures), total=len(futures), desc="Splitting CSVs"):
                result = future.result()
                if "Error" in result:
                    print(result)

    labeled_files = list(LABELED_OUTPUT_DIR.glob("*.csv"))
    if not args.skip_parquet:
        with ProcessPoolExecutor() as executor:
            futures = {executor.submit(convert_csv_to_parquet, path, True) for path in labeled_files}
            for future in tqdm(as_completed(futures), total=len(futures), desc="Converting to Parquet"):
                result = future.result()
                if "Error" in result:
                    print(result)

    print("Parsing complete.")


if __name__ == "__main__":
    main()


    
            



