import os
import pandas as pd 
import numpy as np 
import torch
from torch import nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader, TensorDataset
from sklearn.preprocessing import LabelEncoder
import scipy
import random
from torch.nn.utils import weight_norm
from scipy.signal import stft
import tqdm

class Model():
    def __init__(self, save_path = None, epochs = 4, trial = None):
        random.seed(42)
        # Define all the model parameters
        self.SAMPLING_RATE = 100

        self.num_inputs = 52                      # Number of input channels (features per time step)
        self.num_classes = 6           # Number of classes for segmentation
        self.num_channels = [64, 96, 144, 216, 324] # Number of channels in each residual block
        self.kernel_size = 5         # Kernel size for convolutions
        self.dropout = 0.2           # Dropout rate
        self.dilation_base = 2       # Base for exponential dilation
        self.epochs = epochs

        self.batch_size = 64  # JH: tweaks this for GPU based on RAM limits
        self.ticks_before = int(self.SAMPLING_RATE*3)
        self.ticks_during = int(self.SAMPLING_RATE*0.5)
        self.ticks_after = int(self.SAMPLING_RATE*3)
        self.skip_num = int(self.SAMPLING_RATE*0.5)

        if trial:
            self.num_channels = self.num_channels[:trial.suggest_int("layers", 1, 5)]
            self.epochs = trial.suggest_categorical("epochs", [2, 4, 8])
            self.dropout = trial.suggest_categorical("dropout", [0.0001, 0.001, 0.01, 0.1])
        else:
            self.epochs = 8
            self.dropout = 0.001

        """
        if save_path:
            print("Saving Hyperparameters")
            hyperparameters = [ 
                ["num inputs", self.num_inputs],
                ["num channels", self.num_channels],
                ["kernel size", self.kernel_size],
                ["dropout", self.dropout],
                ["dilation base", self.dilation_base],
                ["epochs", self.epochs],
                ["ticks before", self.ticks_before],
                ["ticks during", self.ticks_during],
                ["ticks after", self.ticks_after],
                ["skip num", self.skip_num]
            ]

            df_hyper = pd.DataFrame(hyperparameters, 
                                    columns=["Parameter", "Value"])
            df_hyper.to_csv(f'{save_path}/hyperparameters.csv', index=False)
        """

        # This has to be set explicitly for now...
        self.label_map = {
            "J" : 0,
            "K" : 1,
            "L" : 2,
            "M" : 3,
            "N" : 4,
            "Z" : 5
        }
        self.inv_label_map = {i:label for label, i in self.label_map.items()}

        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        self.model = TCN(self.num_inputs, self.num_channels, 
                         self.num_classes, self.kernel_size, 
                         self.dropout, self.dilation_base)
        self.model.to(self.device)

        dirname = os.path.dirname(__file__)
        self.save_path = os.path.join(dirname, 'tcn_weights')

    def train(self, probes, test_probes = None, fold = None):
        tr_dfs, tr_df = self.load_probes(probes)
        tr_dataset = TimeSeriesDataset(tr_df, self.label_map, self.ticks_before, 
                                       self.ticks_during, self.ticks_after, 
                                       self.skip_num)
        tr_dataloader = DataLoader(tr_dataset, batch_size=self.batch_size, shuffle=True)

        """
        test_dfs, test_df = self.load_probes(test_probe)
        train_dataset = TimeSeriesDataset(test_dfs, self.label_map, self.ticks_before, 
                                       self.ticks_during, self.ticks_after, 
                                       self.skip_num)
        tr_dataloader = DataLoader(test_dataset, batch_size=self.batch_size, shuffle=True)
        """

        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=1e-3)

        train_losses = []
        test_losses = []
        for epoch in range(self.epochs):
            tot_loss = 0
            self.model.train()
            for batch_X, batch_y in tqdm.tqdm(tr_dataloader):
                batch_X = batch_X.permute(0, 2, 1).to(self.device)
                batch_y = batch_y.to(self.device)

                outputs = self.model(batch_X)
                loss = criterion(outputs, batch_y.reshape(-1))
                
                optimizer.zero_grad()
                loss.backward()
                tot_loss += loss.item()
                optimizer.step()
            train_losses.append(tot_loss / len(tr_dataloader))
            """
            # Get the test loss
            with torch.no_grad():
                running_loss = 0
                self.model.eval()
                for batch in test_dataloader:
                    x, y, weights = batch
                    x, y, weights = x.to(self.device), y.to(self.device), \
                                    weights.to(self.device)
                    outputs = self.model(x.permute(0,2,1))
                    loss = criterion(outputs, y)
                    
                    running_loss += loss.item()
                test_loss = running_loss / len(test_dataloader)
                test_losses.append(test_loss)
        plt.plot(train_losses, label = "Train")
        plt.plot(test_losses, label = "Test")
        plt.xlabel("Epochs")
        plt.ylabel("Loss")
        plt.savefig(f"{self.save_path}/loss_curve_fold{fold}.png")
            """

    def predict(self, probes):
        all_predictions = []
        for probe in tqdm.tqdm(probes):
            test_dfs, test_df = self.load_probes([probe])
            test_dataset = TimeSeriesDataset(test_df, self.label_map, self.ticks_before, 
                                             self.ticks_during, self.ticks_after, 
                                             self.skip_num)
            test_dataloader = DataLoader(test_dataset, batch_size=self.batch_size, shuffle=False)
            all_preds = []
            with torch.no_grad():
                for batch_X, _ in test_dataloader:
                    batch_X = batch_X.permute(0, 2, 1).to(self.device)
                    outputs = self.model(batch_X)
                    output_list = outputs.argmax(dim=1).reshape(-1).cpu().tolist()
                    output_labels = [self.inv_label_map[x] for x in output_list]
                    all_preds.extend(output_labels)
            # Expand the data to be the size of the original input
            all_preds = np.repeat(all_preds, self.skip_num)
            all_preds = np.pad(all_preds, (0, len(probe) - len(all_preds)), 'edge')
            all_predictions.append(all_preds)
        return all_predictions

    def apply_stft_to_df(self, df, target_column):
        # Perform STFT on the target column data
        f, t, Zxx = stft(df[target_column].values, fs=self.SAMPLING_RATE,
                         nperseg = self.SAMPLING_RATE, noverlap = self.SAMPLING_RATE - 1)
        
        # Create a DataFrame for the STFT magnitudes with frequency columns
        magnitude_df = pd.DataFrame(np.abs(Zxx).T, columns=[f"Frequency_{freq:.2f}" for freq in f])
        magnitude_df = magnitude_df.drop(magnitude_df.index[-1])
        # Concatenate the original DataFrame with the STFT DataFrame
        transformed_df = pd.concat([df.reset_index(drop=True), magnitude_df], axis=1)
        return transformed_df
    
    def load_probes(self, probes):
        dfs = []
        for df in probes:
            df["labels"] = df['labels'].str.upper().replace("Z","W")
            df['previous_label'] = df['labels'].shift(1)
            df_transformed = self.apply_stft_to_df(df, "post_rect")
            dfs.append(df_transformed)
            big_df = pd.concat(dfs, axis=0)
        return dfs, big_df

    def save(self):
        torch.save(self.model.state_dict(), self.save_path)

    def load(self, path = None):
        self.model = TCN(self.num_inputs, self.num_channels, 
                         self.num_classes, self.kernel_size, 
                         self.dropout, self.dilation_base)
        self.model.load_state_dict(torch.load(path, weights_only=True, map_location = self.device))
        self.model = self.model.to(self.device)
        self.model.eval()


class TimeSeriesDataset(Dataset):
    def __init__(self, df, label_map, ticks_before, ticks_during, ticks_after, skip_num):
        freq_cols = [c for c in df.columns if "Frequency_" in c]
        self.X = df[["pre_rect"]+freq_cols].values
        self.y = df["labels"].map(label_map).values

        self.ticks_before = ticks_before
        self.ticks_during = ticks_during
        self.ticks_after = ticks_after
        self.skip_num = skip_num
        self.total_length = self.X.shape[0]

        # Start and end index calculation now includes ticks_during
        self.start_index = self.ticks_before
        self.end_index = self.total_length - self.ticks_after - self.ticks_during + 1
        self.step = self.skip_num + 1

        self.num_samples = max(0, (self.end_index - self.start_index + self.step - 1) // self.step)

    def __len__(self):
        return self.num_samples

    def __getitem__(self, idx):
        # Map the dataset index to the actual index in the data
        i = self.start_index + idx * self.step

        if i >= self.end_index:
            raise IndexError(f"Index {idx} out of range.")

        # Define the range for x values (before, during, and after the current index)
        start = i - self.ticks_before
        end = i + self.ticks_during + self.ticks_after  # Includes 'during' ticks

        # Slice the x values without copying the entire array
        X_values = self.X[start:end, :]

        # Define the range for y values (for the 'during' period)
        y_start = i
        y_end = i + self.ticks_during
        y_values = np.nanmedian(self.y[y_start:y_end])
    

        # Convert to torch tensors
        X_values = torch.tensor(X_values, dtype = torch.float32)
        y_values = torch.tensor([y_values], dtype = torch.int64)

        return X_values, y_values

class ResidualBlock(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, dilation, dropout, is_last=False):
        super(ResidualBlock, self).__init__()
        padding = (kernel_size - 1) * dilation // 2  # For 'same' padding

        self.conv1 = nn.Conv1d(in_channels, out_channels, kernel_size, 
                               padding=padding, dilation=dilation)
        self.conv1 = nn.utils.weight_norm(self.conv1)
        self.relu1 = nn.ReLU()
        self.dropout1 = nn.Dropout(dropout)

        self.conv2 = nn.Conv1d(out_channels, out_channels, kernel_size,
                               padding=padding, dilation=dilation)
        self.conv2 = nn.utils.weight_norm(self.conv2)
        self.relu2 = nn.ReLU()
        self.dropout2 = nn.Dropout(dropout)

        # Adjust dimensions if the input and output channels are different
        self.downsample = nn.Conv1d(in_channels, out_channels, kernel_size=1) \
            if in_channels != out_channels else None
        self.is_last = is_last
        self.relu = nn.ReLU()

    def forward(self, x):
        out = self.conv1(x)
        out = self.relu1(out)
        out = self.dropout1(out)

        out = self.conv2(out)
        if not self.is_last:
            out = self.relu2(out)
        out = self.dropout2(out)

        # Apply skip connection
        res = x if self.downsample is None else self.downsample(x)
        return self.relu(out + res)

class TemporalConvNet(nn.Module):
    def __init__(self, num_inputs, num_channels, kernel_size=2, dropout=0.2, dilation_base=2):
        super(TemporalConvNet, self).__init__()
        layers = []
        num_levels = len(num_channels)
        for i in range(num_levels):
            is_last = (i==num_levels-1)
            dilation = dilation_base ** i
            in_channels = num_inputs if i == 0 else num_channels[i - 1]
            out_channels = num_channels[i]
            layers += [ResidualBlock(in_channels, out_channels, kernel_size, dilation, dropout, is_last)]

        self.network = nn.Sequential(*layers)

    def forward(self, x):
        return self.network(x)

class TCN(nn.Module):
    def __init__(self, num_inputs, num_channels, num_classes, kernel_size=2, dropout=0.2, dilation_base=2):
        super(TCN, self).__init__()
        self.tcn = TemporalConvNet(num_inputs, num_channels, kernel_size, dropout, dilation_base)
        self.global_avg_pool = nn.AdaptiveAvgPool1d(1)  # Global average pooling over the sequence length
        self.fc = nn.Linear(num_channels[-1], num_classes)  # Fully connected layer for classification

    def forward(self, x):
        # Input shape: (batch_size, num_inputs, seq_length)
        y = self.tcn(x)
        
        # Global average pooling across the sequence length
        y = self.global_avg_pool(y)  # Shape: (batch_size, num_channels[-1], 1)
        y = y.squeeze(-1)  # Remove the last dimension, shape: (batch_size, num_channels[-1])
        
        # Pass through fully connected layer for classification
        y = self.fc(y)  # Shape: (batch_size, num_classes)
        
        return y


