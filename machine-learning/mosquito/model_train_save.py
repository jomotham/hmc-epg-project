import os
import glob
import numpy as np
import pandas as pd
import argparse
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_recall_fscore_support, ConfusionMatrixDisplay, accuracy_score
import importlib.util
from matplotlib import pyplot as plt
from itertools import groupby

class DataImport:
        def __init__(self, data_path):
            self.raw_dfs, _ = self.import_data(data_path)
            self.random_state = 42
            self.probe_finder = self.leak_probe_finder
            self.train_probes, _ = self.get_probes(self.probe_finder, self.raw_dfs)

        def get_train_test(self):
            return self.train_probes
            
        def import_data(self, data_path):
            """
            import_data takes in a path to cleaned data and returns it
            as a list of dataframes.
            """
            filenames = glob.glob(os.path.expanduser(f"{data_path}/*.csv"))
            dataframes = [pd.read_csv(f) for f in filenames]
            for file, df in zip(filenames, dataframes):
                df["file"] = file
                df['labels'] = df['labels'].replace('Z', 'W')
            return dataframes, filenames

        def leak_probe_finder(self, labels):
            non_np_indices = np.where(labels != 'NP')[0]
            probes = []
            start = 0
            end = 0
            for i in range(len(non_np_indices)):
                if i == 0:
                    start = non_np_indices[i]
                elif i == len(non_np_indices) - 1:
                    end = non_np_indices[i]
                elif abs(non_np_indices[i] - non_np_indices[i - 1]) > 1:
                    start = non_np_indices[i]
                elif abs(non_np_indices[i] - non_np_indices[i + 1]) > 1:
                    end = non_np_indices[i]
                if start > 0 and end > 0:
                    probes.append((start, end))
                    start = 0
                    end = 0
            return probes

        def get_probes(self, probe_finder_method, dfs):
            """
            Input: probe_finder_method: the method by which to find probes
            Output: a list of dataframes, each consisting of a probe along with a list of names
            """
            all_probes = []
            all_probe_names = []
            for df in dfs:
                probe_indices = probe_finder_method(df["labels"].values)
                probes = [df.iloc[start:end].reset_index(drop=True).copy() 
                          for start, end in probe_indices]
                probe_names = [df["file"][0][:-4] + f"_{str(i)}" 
                               for i, df in enumerate(probes)]
                
                all_probes.extend(probes)
                all_probe_names.extend(probe_names)

            return all_probes, all_probe_names

def dynamic_importer(path):
    spec = importlib.util.spec_from_file_location("model", path)
    model = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(model)

    return model

def main():
    parser = argparse.ArgumentParser(
        prog = "Model Trainer and Saver",
        description = "This program takes in EPG data and a \
                        labeler program, trains it, and then \
                        saves the model for use in the GUI."
    )
    parser.add_argument("--data_path", type = str, required = True)
    parser.add_argument("--model_path", type = str, required = True)
    parser.add_argument("--attention", action = "store_true")
    args = parser.parse_args()

    print("Loading Data...")
    data = DataImport(args.data_path)
    train_data = data.get_train_test()
    print(f"{len(train_data)} Training Probes")
    print(data.get_train_test()[0])
    model_import = dynamic_importer(args.model_path)

    kwargs = {}
    # UNet settings
    if args.model_path == "unet.py":
        if args.attention:
            kwargs['bottleneck_type'] = 'windowed_attention'
            kwargs = kwargs | {'epochs': 64, 'lr': 0.0005, 'dropout_rate': 1e-05, 'weight_decay': 1e-06, 'num_layers': 8, 'features': 32, 'transformer_window_size': 150, 'transformer_layers': 2}
            heads_per_channel = 32
            kwargs['transformer_nhead'] = max(kwargs['features'] // heads_per_channel, 1)
            kwargs['embed_dim'] = kwargs['features']
        else:
            kwargs['bottleneck_type'] = 'block'
            kwargs = kwargs | {'epochs': 64, 'lr': 0.0005, 'dropout_rate': 0.1, 'weight_decay': 1e-06, 'num_layers': 8, 'features': 32}

    model = model_import.Model(**kwargs)
    print("Training Model...")
    trained_model = model.train(train_data, None, fold = None) #None for no test probes
    print("Saving Model...")
    model.save()

if __name__ == "__main__":
    main()
