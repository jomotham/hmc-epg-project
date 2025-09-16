import os
import glob
import numpy as np
import pandas as pd
import argparse
from sklearn.preprocessing import normalize
from sklearn.model_selection import KFold
from sklearn.metrics import precision_recall_fscore_support, \
                            confusion_matrix, \
                            ConfusionMatrixDisplay, \
                            accuracy_score, \
                            f1_score
import importlib.util
from matplotlib import pyplot as plt
from itertools import groupby
import optuna
from sklearn.model_selection import train_test_split

from data_augmentation import build_augmented_dataset
from postprocessing import PostProcessor

class DataImport:
        def __init__(self, data_path, folds):
            self.raw_dfs, _ = self.import_data(data_path)
            self.random_state = 42
            kf = KFold(n_splits = folds, random_state = self.random_state,\
                       shuffle = True)
            self.cross_val_iter = list(kf.split(self.raw_dfs))
            self.probe_finder_method = self.leak_probe_finder

        def get_train_test_split(self):
            train_dfs, test_dfs = train_test_split(self.raw_dfs, test_size = 0.2,
                                                             random_state = 42)
            
            train_probes, _ = self.get_probes(train_dfs)
            test_probes, test_names = self.get_probes(test_dfs)
            return train_probes, test_probes, test_names

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

        def simple_probe_finder(self, recording, window = 500, threshold = 0.1,
                         min_probe_length = 1500, np_pad = 500):
            """
            Input: recording: A pre-rectified mosquito recording as an 1-D nupmy 
                     array. Pre-rectified recordings are necessary as baseline is 
                     not 0 in post-rectified recordings.
                   window: Before NP regions can be identified, a rolling
                     average filter is applied to remove noise in the NP regions.
                     window is the size of this filter in samples.
                   threshold: The maximum value of an NP sample.
                   min_probe_length: The minimum acceptable length of a probe in
                     samples.
                   np_pad: the number of NP samples before and after each probe to
                     include. Note that high values might result in overlapping with
                     the next probe.
            Output: A list of (start sample, end sample) tuples for each probe. By 
                    default contains about 5 seconds of NPs at the beginning and end            
                    of each probe. We say "about" because this splitting is done
                    in an unsupervised manner, although it is largely pretty good.
            """
            
            smoothed = np.convolve(recording, np.ones(window), "same")/window
            is_NP = smoothed < threshold # NP is where the signal is close to 0
            
            # Find starts and ends, combine into tuple
            find_sequence = lambda l, seq : [i for i in range(len(l)) if l[i:i+len(seq)] == seq]
            is_NP_list = list(is_NP)
            probe_starts = find_sequence(is_NP_list, [True, False])
            probe_ends = find_sequence(is_NP_list, [False, True])
            probes = zip(probe_starts, probe_ends)
            
            # Remove probes that are too short and pad
            probes = [(max(0, start - np_pad), end + np_pad) for start, end in probes if end - start > min_probe_length]
            
            return probes

        def get_probes(self, dfs):
            """
            Input: probe_finder_method: the method by which to find probes
            Output: a list of dataframes, each consisting of a probe along with a list of names
            """
            all_probes = []
            all_probe_names = []
            for df in dfs:
                probe_indices = self.probe_finder_method(df["labels"].values)
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

def plot_labels(time, voltage, true_labels, pred_labels, probs = None):
    """
    plot_labels produced a matplotlib figure containing three subplots
        that visualize a waveform along with the true and predicted labels
    Input:
        time: a series of time values
        voltage: a time series of voltage values from the waveform
        true_labels: a time series of the true label for each time point
        pred_labels: a time series of the predicted labels for each time point
    Output:
        (fig, axs): a tuple
    """
    label_to_color = {
            "NP": "red",
            "J": "blue",
            "K": "green",
            "L": "purple",
            "M": "pink",
            "N": "cyan",
            "W": "orange"
    }

    fig, axs = plt.subplots(3, 1, sharex = True)
    recording = 1
    fill_min, fill_max = voltage.min(), voltage.max()
    
    # First plot will be the true labels
    axs[0].plot(time, voltage, color = "black")
    for label, color in label_to_color.items():
        fill = axs[0].fill_between(time, fill_min, fill_max, 
                where = (true_labels == label), color=color, alpha = 0.5)
        fill.set_label(label)
    axs[0].legend(bbox_to_anchor=(0.5, 1), 
                  bbox_transform=fig.transFigure, loc="upper center", ncol=9)
    axs[0].set_title("True Labels")
    # Second plot will be the predicted labels
    axs[1].plot(time, voltage, color = "black")
    for label, color in label_to_color.items():
        axs[1].fill_between(time, fill_min, fill_max, 
                where = (pred_labels == label), color=color, alpha = 0.5)
    axs[1].set_title("Predicted Labels")
    # Third plot will be marked where there is a difference between the two
    axs[2].plot(time, voltage, color = "black")
    axs[2].fill_between(time, fill_min, fill_max, 
            where = (pred_labels != true_labels), color = "gray", alpha = 0.5)
    axs[2].set_title("Incorrect Labels")
    # Axes titles and such
    fig.supxlabel("Time (s)")
    fig.supylabel("Volts")
    fig.tight_layout()
    return fig

def generate_report(test_data, predicted_labels, test_names, save_path, model_name, fold):
    # Flatten everything
    labels_true = []
    labels_pred = []
    for df, preds in zip(test_data, predicted_labels):
        labels_true.extend(df["labels"].values)
        labels_pred.extend(preds)

    # Make sure we have a place to save everything
    if not os.path.isdir(save_path):
        os.mkdir(save_path)

    # precision et. al
    labels = sorted(np.unique(labels_true))
    precision, recall, fscore, _ = precision_recall_fscore_support(labels_true, labels_pred, 
                                                            labels=labels, average = None, zero_division=0)
    temp_dict = {"precision" : precision, 
                 "recall" : recall, 
                 "fscore" : fscore}
    out_dataframe = pd.DataFrame(temp_dict, index=labels).stack()
    out_dataframe.index = out_dataframe.index.map('{0[1]}_{0[0]}'.format)
    out_dataframe = out_dataframe.to_frame().T

    # accuracy
    accuracy = accuracy_score(labels_true, labels_pred)
    out_dataframe["accuracy"] = accuracy

    # confusion matrix
    ConfusionMatrixDisplay.from_predictions(labels_true, labels_pred, \
                                            normalize = 'true')
    plt.savefig(rf"{save_path}/{model_name}_ConfusionMatrix_Fold{fold}.png")

    # difference plots
    for i, (df, preds, name) in enumerate(zip(test_data, predicted_labels, test_names)):
        fig = plot_labels(df["time"], df["pre_rect"], df["labels"].values, np.array(preds))
        fig.savefig(fr"{save_path}/{model_name}_{os.path.split(name)[1]}_Fold{fold}.png")
        plt.close(fig)

    print(f"Fold {fold} Overall Accuracy: {accuracy}")
    return labels_true, labels_pred, out_dataframe

def optuna_objective(data, args, trial, **kwargs):
    labels_true = []
    labels_pred = []
    for fold, (train_index, test_index) in enumerate(data.cross_val_iter):
        train_data = [data.raw_dfs[i] for i in train_index]
        test_data = [data.raw_dfs[i] for i in test_index]
        train_data, _ = data.get_probes(train_data)
        test_data, test_names = data.get_probes(test_data)

        augment_factor = trial.suggest_categorical("augment_factor", [1, 2, 4, 8])

        if args.augment:
            train_data = build_augmented_dataset(train_data, size = len(train_data) * augment_factor)

        model_import = dynamic_importer(args.model_path)
        
        model = model_import.Model(trial = trial, **kwargs)
        model.train(train_data, test_data, fold)
            
        predicted_labels = model.predict(test_data)

        # Flatten everything
        for df, preds in zip(test_data, predicted_labels):
            labels_true.extend(df["labels"].values)
            labels_pred.extend(preds)

    f1 = f1_score(labels_true, labels_pred, average="macro")
    print(f1_score(labels_true, labels_pred, average=None))
    with open(f"{args.model_name}_optuna.txt", "a") as f:
        print(trial.datetime_start, trial.number, trial.params, f1, file=f)
    return f1

def main():
    parser = argparse.ArgumentParser(
        prog = "Model Performance Evaluator",
        description = "This program takes in EPG data and a \
                        labeler program, trains it, and then \
                        generates statistics and figures to \
                        characterize the model's performance."
    )
    parser.add_argument("--data_path", type = str, required = True)
    parser.add_argument("--model_path", type = str, required = True)
    parser.add_argument("--save_path", type = str, required = True)
    parser.add_argument("--model_name", type = str, required = True)
    parser.add_argument("--augment", action="store_true")
    parser.add_argument("--post_process", type = str, required = False) # can either be s/smooth or viterbi/m
    parser.add_argument("--epochs", type = int, required=False)
    parser.add_argument("--optuna", action="store_true")
    parser.add_argument("--attention", action="store_true") # can only be used with UNet 
    args = parser.parse_args()

    print("Loading Data...")
    data = DataImport(args.data_path, 5)
    if args.optuna:
        study = optuna.create_study(direction='maximize')
        
        kwargs = dict()
        if args.model_path == "unet.py":
            if args.attention:
                # expected f1: 0.7402015172114621
                kwargs['bottleneck_type'] = 'windowed_attention'
                kwargs = kwargs | {'epochs': 64, 'lr': 0.0005, 'dropout_rate': 1e-05, 'weight_decay': 1e-05, 'num_layers': 8, 'features': 64, 'transformer_window_size': 150, 'transformer_layers': 2}
                heads_per_channel = 32
                kwargs['transformer_nhead'] = max(kwargs['features'] // heads_per_channel, 1)
                kwargs['embed_dim'] = kwargs['features']
            else:
                study.enqueue_trial(
                    {
                        "epochs" : 64,
                        "lr": 5e-4,
                        "dropout": 0.1,
                        "weight_decay": 1e-6,
                        "num_layers": 8,
                        "features": 32,
                        "augment_factor": 1
                    }
                )

                # expected f1: 0.694895
                kwargs['bottleneck_type'] = 'block'
                kwargs = kwargs | {'epochs': 64, 'lr': 0.0005, 'dropout_rate': 0.1, 'weight_decay': 1e-06, 'num_layers': 8, 'features': 32}

            if args.epochs:
                kwargs['epochs'] = args.epochs

        else:
            kwargs = {}

        study.optimize(lambda x : optuna_objective(data, args, x, **kwargs), n_trials = 100, show_progress_bar=True, )

        print(study.best_params)
        optuna.visualization.matplotlib.plot_optimization_history(study)
        plt.savefig(f"{args.model_name}_hyper.png")
        return

    summary_data = []
    labels_true = []
    labels_pred = []
    for fold, (train_index, test_index) in enumerate(data.cross_val_iter):
        print(f"Evaluating Fold {fold}")
        train_data = [data.raw_dfs[i] for i in train_index]
        test_data = [data.raw_dfs[i] for i in test_index]
        train_data, _ = data.get_probes(train_data)
        test_data, test_names = data.get_probes(test_data)

        if args.augment:
            augmented_train_data = build_augmented_dataset(train_data)
            print(f"{len(augmented_train_data)} Training Probes with Augment")
        
        model_import = dynamic_importer(args.model_path)
        
        kwargs = dict()
        if args.model_path == "unet.py":
            if args.attention:
                # expected f1: 0.7402015172114621
                kwargs['bottleneck_type'] = 'windowed_attention'
                kwargs = kwargs | {'epochs': 64, 'lr': 0.0005, 'dropout_rate': 1e-05, 'weight_decay': 1e-06, 'num_layers': 8, 'features': 32, 'transformer_window_size': 150, 'transformer_layers': 2}
                heads_per_channel = 32
                kwargs['transformer_nhead'] = max(kwargs['features'] // heads_per_channel, 1)
                kwargs['embed_dim'] = kwargs['features']
            else:
                # expected f1: 0.694895
                kwargs['bottleneck_type'] = 'block'
                kwargs = kwargs | {'epochs': 64, 'lr': 0.0005, 'dropout_rate': 0.1, 'weight_decay': 1e-06, 'num_layers': 8, 'features': 32}

            if args.epochs:
                kwargs['epochs'] = args.epochs

        model = model_import.Model(save_path = args.save_path, **kwargs)
        print("Training Model...")
        
        if args.augment:
            final_train_data = augmented_train_data
        else:
            final_train_data = train_data
        print(final_train_data[0].columns)
        model.train(final_train_data, test_data, fold)
            
        print("Evaluating Model...")
        
        if args.post_process is None:
            predicted_labels = model.predict(test_data)

        elif args.post_process.lower() == "viterbi" or args.post_process.lower() == "v":
            _, logits = model.predict(test_data, return_logits=True)
            logits = [l.squeeze(0).detach().numpy() for l in logits]
            post_process = PostProcessor(train_data, model.inv_label_map)
            predicted_labels = [post_process.postprocess_viterbi(logit) for logit in logits]

        elif args.post_process.lower() == "smooth" or args.post_process.lower() == "s":
            _, logits = model.predict(test_data, return_logits=True)
            post_process = PostProcessor(train_data, model.inv_label_map)
            predicted_labels = [post_process.postprocess_smooth(logit.squeeze(0).detach().numpy()) for logit in logits]
        elif args.post_process.lower() == "smooth" or args.post_process.lower() == "s":
            _, logits = model.predict(test_data, return_logits=True)
            logits = [l.squeeze(0).detach().numpy() for l in logits]
            post_process = PostProcessor(train_data, model.inv_label_map)
            predicted_labels = [post_process.postprocess_smooth(logit) for logit in logits]
        else:
            print("Choose a valid (case insensitive) post-processing arguement: either V/Viterbi or S/Smooth. Terminating program")
            assert False #TODO: make this better
            
        print("Generating Report...")
        true, pred, stats = generate_report(test_data, predicted_labels, test_names, args.save_path, args.model_name, fold)
        summary_data.append(stats)
        labels_true.extend(true)
        labels_pred.extend(pred)
        
    out_summary_data = pd.concat(summary_data)

    # Calculate statistics across every dataset
    labels = sorted(np.unique(labels_true))
    all_precision, all_recall, all_fscore, _ = precision_recall_fscore_support(labels_true, labels_pred, 
                                                            labels=labels, average = None, zero_division=0)
    temp_dict = {"precision" : all_precision, 
                 "recall" : all_recall, 
                 "fscore" : all_fscore}
    out_dataframe = pd.DataFrame(temp_dict, index=labels).stack()
    out_dataframe.index = out_dataframe.index.map('{0[1]}_{0[0]}'.format)
    out_dataframe = out_dataframe.to_frame().T
    out_dataframe["accuracy"] = accuracy_score(labels_true, labels_pred)

    out_summary_data = pd.concat([out_summary_data, out_dataframe])
    out_summary_data.to_csv(f"{args.save_path}/{args.model_name}_SummaryStats.csv")

    overall = ConfusionMatrixDisplay.from_predictions(labels_true, labels_pred, \
                                            normalize = 'true')
    overall.plot().figure_.savefig(rf"{args.save_path}/{args.model_name}_OverallConfusionMatrix.png")

    all_data = pd.DataFrame({'labels_true': labels_true,
                             'labels_pred': labels_pred})
    all_data.to_csv(f"{args.save_path}/{args.model_name}_allpredictions.csv")

if __name__ == "__main__":
    main()
