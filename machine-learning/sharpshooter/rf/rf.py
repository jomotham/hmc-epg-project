import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.fft import fft, fftfreq
from collections import defaultdict
from sklearn.ensemble import RandomForestClassifier
import pickle
import optuna
import warnings
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed
from transform_worker import transform_single_probe
warnings.simplefilter(action='ignore', category=FutureWarning)

class Model:
    def __init__(self, save_path = None, trial = None):
        self.chunk_seconds = 3#3
        self.num_estimators = 8#128
        self.num_freqs = 6#7
        self.max_depth = 32#16
        self.sample_rate = 100
        self.chunk_size = self.chunk_seconds * self.sample_rate
        self.random_state = 42
        dirname = os.path.dirname(__file__)
        self.model = None
        self.save_path = save_path
        self.model_path = r"D:\USDA-Auburn\CS-Repository\ML\rf.py"
        
        if trial:
            self.chunk_seconds = trial.suggest_int('chunk_seconds', 1, 10)
            self.num_freqs = trial.suggest_int('num_freqs', 3, 15)
            self.num_estimators = trial.suggest_categorical('num_estimators', [50, 100, 200, 300, 400, 500, 600])
            self.max_depth = trial.suggest_categorical('max_depth', [10, 20, 30, 40, 50, 60, None])

    
    def transform_data(self, probes, training=True):
        """
        Transforms a list of probe DataFrames into frequency-domain features using FFT.
        Runs per-probe processing in parallel using multiprocessing.
        """
        from functools import partial
        with ProcessPoolExecutor() as executor:
            futures = [
                executor.submit(
                    transform_single_probe,
                    probe,
                    self.chunk_size,
                    self.sample_rate,
                    self.num_freqs,
                    training
                ) for probe in probes
            ]

            transformed_probes = []
            for future in tqdm(as_completed(futures), total=len(futures), desc="Processing probes", position=2, leave=False):
                result = future.result()
                if result is None:
                    print("WARNING: Got None from transform_single_probe")
                else:
                    transformed_probes.append(result)

        return transformed_probes


    def train(self, probes, test_data = None, fold = None):
        transformed_probes = self.transform_data(probes)
        train = pd.concat(transformed_probes)
        X_train = train.drop(["label"], axis=1)
        Y_train = train["label"]
        rf = RandomForestClassifier(self.num_estimators, class_weight="balanced", max_depth = self.max_depth, n_jobs=-1)
        self.model = rf.fit(X_train, Y_train)

    
    def predict(self, probes):
        transformed_probes = self.transform_data(probes, training = False)
        predictions = []
        for transformed_probe, raw_probe in zip(transformed_probes, probes):
            test_probe = transformed_probe
            pred = self.model.predict(test_probe)

            # We need to expand the prediction based on the sample rate
            pred = np.repeat(pred, self.chunk_seconds * self.sample_rate)
            # Expand until the end since probe is never exactly divisible by window size
            diff = len(raw_probe) - len(pred)
            if diff > 0:
                pred = np.pad(pred, (0, diff), mode="edge")
            else:
                pred = pred[:len(raw_probe)]
            predictions.append(pred)
        return predictions

    def save(self):
        with open(self.model_path, 'ab') as model_save:
            pickle.dump(self.model, model_save)

    def load(self, path = None):
        with open(path, 'rb') as model_save:
            self.model = pickle.load(model_save)
