from pandas import read_csv, DataFrame
import numpy as np
import pandas as pd
import re
import windaq
import os


class EPGData:
    """
    A class for interacting with and saving our waveform recordings
    """

    def __init__(self):
        self.dfs = {}  # A dictionary of filename : pandas dataframe objects
        self.label_column = "labels"
        self.probe_column = "probes"
        #self.prepost_suffix = "_rect"
        self.current_file = None
        self.dir_path = os.path.dirname(os.path.realpath(__file__))
        # self.current_file = os.path.join(
        #     os.path.abspath(os.path.join(self.dir_path, "..")), # root dir
        #     # r"GUI\test_sharpshooter.csv"
        #     #"/Users/ashleykim/Desktop/USDA/USDA-Auburn-Su25/export_Tes.csv"
        #     #r"GUI\test_mosquito.csv"
        #     r"Data\Sharpshooter Data - HPR 2017\sharpshooter_labeled\sharpshooter_a01_labeled.csv"
        #     #r"/Users/cole/coding/bugs2025/USDA-Auburn-Su25/GUI/test_sharpshooter.csv"
        # )          

    def load_data(self, file, channel_index: int = None):
        """
        load_data takes in either a Windaq or CSV file, converts it
        into a pandas dataframe, and makes it available for use
        Inputs:
                files: a filenames (either .DAQ or .csv) as a string
        Returns:
                True if successful, False otherwise
        """
        import time
        start_time = time.perf_counter()

        if re.search(r"\.(WDQ|DAQ|WDH)$", file, re.IGNORECASE):
            windaq_file = windaq.windaq(file)
            # TODO: don't hardcode channel count and names
            # TODO: add event markers as column
            df = DataFrame(
                # {
                #     "time": windaq_file.time(),
                #     "pre_rect": windaq_file.data(1),
                #     "post_rect": windaq_file.data(2),
                # }
                {
                    "time": windaq_file.time(),
                    "voltage": windaq_file.data(channel_index),
                }
            )
            # This will overwrite if there are multiple
            # markers pointing to the same index
            comments = [None for i in range(len(df))]
            # for event in windaq_file.eventmarkers:
            #     if "comment" in event:
            #         comments[event["index"]] = event["comment"]
            #     elif "timestamp" in event:
            #         comments[event["index"]] = event["timestamp"]
            #     else:
            #         comments[event["index"]] = ""
            df["comments"] = comments

            labels = [None for i in range(len(df))]
            df["labels"] = labels
            self.dfs[file] = df
        elif re.search(r"\.csv$", file, re.IGNORECASE):
            full_path = os.path.join(self.dir_path, file)
            try:
                # self.dfs[file]
                orig_df = read_csv(full_path, engine="pyarrow")
                self.dfs[file] = pd.DataFrame(columns=["time", "voltage", "labels", "comments"])

                if 'time' not in orig_df.columns:
                    raise ValueError("No Time Data")
                else:
                    self.dfs[file]['time'] = orig_df['time']
                
                if 'voltage' not in orig_df.columns:
                    if 'pre_rect' in orig_df.columns:
                        self.dfs[file]['voltage'] = orig_df['pre_rect']
                    else:
                        raise ValueError("No Voltage Data")
                else:
                    self.dfs[file]['voltage'] = orig_df['voltage']
                
                if 'labels' in orig_df.columns:
                    self.dfs[file]['labels'] = orig_df['labels']
                else:
                    self.dfs[file]['labels'] = np.nan

                if 'comments' in orig_df.columns:
                    self.dfs[file]['comments'] = orig_df['comments']
                else:
                    self.dfs[file]['comments'] = np.nan

            except FileNotFoundError:
                print(f"Could not find {full_path}")
                return False
        else:
            # unknown file extension
            print(f"Unknown file extension for: {file}")
            return False
    
        print(f"Data loaded in {time.perf_counter() - start_time:.4f}s")

        self.current_file = file
        if not self.label_column in self.dfs[file]:
            self.dfs[file][self.label_column] = np.nan
        return True

    def export_csv(self, file, destination):
        """
        export_csv saves a CSV of loaded EPG data to disk.
        Inputs:
                file: string containing the key of the recording in
                      self.dfs
                destination: where the file should be saved
        Returns:
                True if successful, False otherwise
        """

        try:
            self.dfs[file].to_csv(destination)
        except:
            return False
        return True

    # TODO: check if we need to return end time or begin time
    def export_txt(self, file, destination):
        """
        export_txt saves a plaintext file to disk with timestamps
        for the end of each label in the loaded EPG data.
        Inputs:
                file: string containing the key of the recording in
                      self.dfs
                destination: where the file should be saved
        Returns:
                True if successful, False otherwise
        """
        df = self.dfs[file]
        df1 = df[:-1].reset_index()["labels"]
        df2 = df[1:].reset_index()["labels"]
        where = np.where(~((df1 == df2) | (df1.isna() & df2.isna())))[0]
        where = np.append(where, [len(df) - 1])
        with open(destination, "w") as f:
            for i, row in df.iloc[where].iterrows():
                f.write(f'"{row["labels"]}"\n    {row["time"]:.02f}\n')

    def get_recording(self, file):
        """
        get_recording returns a tuple of numpy arrays containing time
        and voltage data only.

        Inputs:
                file: string containing the key of the recording
        Outputs:
                A tuple of numpy arrays containing the time and voltage data.
        """

       
        if not file in self.dfs:
            raise Exception(f"{file} is not a key in self.dfs")
        else:
            df = self.dfs[file]
            return df["time"].values, df["voltage"].values

    def set_labels(self, file: str, labels) -> None:
        """
        set_labels sets the labels of file to be those given in the
        input labels

        Inputs:
                file: string containing the key of the recording
                labels: a numpy array containing label strings of
                        the same length as the number of columns
                        in the recording dataframe

        Returns:
                None
        """
        if not file in self.dfs.keys():
            raise Exception(f"{file} is not a key in self.dfs")
        elif not self.dfs[file].shape[0] == len(labels):
            raise Exception(
                f"Input labels is of size {len(labels)}"
                f"but dataframe has length {self.dfs[file].shape[0]}"
            )
        else:
            self.dfs[file][self.label_column] = labels

    def set_transitions(self, file, transitions, section_type):
        """
        set_transitions takes in transitions in the format of get_transitions
        and writes them to the labels for files. Think of this as an alternative
        to set_labels that is sometime more convenient. Assumes file already has labels.
        Inputs:
                file: string containing the key of the recording
                transitions: a list of (time, label) tuples
        Returns:
                Nothing
        """
        if not file in self.dfs:
            raise Exception(f"{file} is not a key in self.dfs")
        

        df = self.dfs[file]
        section_to_column = {"labels": self.label_column}
        col = section_to_column[section_type]

        cleaned_transitions = [(round(t, 2), label) for t, label in transitions]

        if not cleaned_transitions:
            return
        
        # Build Series of transitions indexed by time
        times, labels = zip(*cleaned_transitions)
        transition_series = pd.Series(labels, index=times)

        # Align with the time column (assumed to already match transition rounding)
        aligned = transition_series.reindex(df["time"], method="ffill")

        # Update label column
        self.dfs[file][col] = aligned.reset_index(drop=True)

        # df = self.dfs[file].copy()
        # df["time"] = df["time"].round(2)
        # df = df.set_index("time")

        # section_to_column = {"labels": self.label_column, "probes": self.probe_column}
        # col = section_to_column[section_type]
        # df[col] = df[col].astype(str)
        # df[col] = pd.NA
        # for time, label in transitions:
        #     rounded_time = round(time, 2)
        #     df.loc[rounded_time, col] = label
        # new_labels = df.reset_index()[col].ffill()
        # self.dfs[file][col] = new_labels

    def get_transitions(self, file: str, section_type: str) -> list[tuple[float, str]]:
        """
        get_transitions looks at the labels from file and returns the times
        where transitions occur and the state that follows them. Always has
        a transition at time 0 for convenience.
        Inputs:
                file: string containing the key of the recording
        Outputs:
                a list of (time, label) tuples. If no labels, then just has
                one element at time 0.
        """
        if not file in self.dfs:
            raise Exception(f"{file} is not a key in self.dfs")
        

        df: DataFrame = self.dfs[file]
        times = df["time"].values

        if section_type == "labels":
            values = df[self.label_column].values
        elif section_type == "probes":
            values = df[self.probe_column].values
        else:
            raise ValueError(f"Unknown section_type: {section_type}")

        
        if pd.isna(values).all():
            return []

        # Find where the value changes (i.e., transitions)
        change_indices = np.flatnonzero(values[1:] != values[:-1]) + 1

        # Prepend time 0 with the initial label
        initial = np.array([[0.0, values[0]]], dtype=object)
        transitions = np.column_stack((times[change_indices], values[change_indices])) # combine elements pair-wise

        transitions = np.vstack((initial, transitions)) # prepend initial zero

        return transitions