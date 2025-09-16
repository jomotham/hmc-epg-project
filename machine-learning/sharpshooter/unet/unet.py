import pandas as pd
import numpy as np
import os
import json
from pathlib import Path
from collections import Counter
import torch
from torch import nn
import torch.optim as optim
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import random
import tqdm
import distinctipy
from matplotlib import pyplot as plt
from positional_encodings.torch_encodings import PositionalEncoding1D
from sklearn.metrics import (
    precision_recall_fscore_support, confusion_matrix, 
    ConfusionMatrixDisplay, accuracy_score, f1_score
)

from concurrent.futures import ThreadPoolExecutor, as_completed

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))) # root ML folder

from label_mapper import load_label_map, build_label_map
from data_loader import import_data, stratified_split


class Model:
    def __init__(
            self, 
            epochs=64, 
            lr=5e-4, 
            num_layers=6, 
            growth_factor=1, 
            features=64, 
            n_conv_steps_per_block=2, 
            block_kernel_size=3, 
            up_down_sample_kernel_size=2, 
            block_padding=1, 
            weight_decay=1e-6, 
            dropout_rate=1e-6, 
            bottleneck_type="block", 
            ignore_N=None,
            transformer_window_size=None, 
            embed_dim=None, 
            transformer_layers=None, 
            transformer_nhead=None, 
            save_path=None, 
            trial = None
        ):
        random.seed(42)  

        binary_label_map = load_label_map("../label_map.json")[0]
        self.label_map = {k: i for i, k in enumerate(sorted(binary_label_map))}
        self.inv_label_map = {i:label for label, i in self.label_map.items()}


        self.data_columns = ["voltage"]
        
        self.batch_size = 1
        self.epochs=epochs
        self.lr=lr
        self.weight_decay = weight_decay
        self.dropout_rate = dropout_rate
        self.block_kernel_size = block_kernel_size
        self.up_down_sample_kernel_size = up_down_sample_kernel_size
        self.block_padding = block_padding
        self.n_conv_steps_per_block = n_conv_steps_per_block
        self.num_layers = num_layers
        self.growth_factor = growth_factor
        self.features = features
        self.bottleneck_type = bottleneck_type
        self.transformer_window_size = transformer_window_size
        self.ignore_N = ignore_N
        
        
        if embed_dim is None:
            if self.bottleneck_type == "windowed_attention":
                self.embed_dim = self.features * (self.growth_factor**self.num_layers)
            elif self.bottleneck_type == "attention":
                self.embed_dim = self.features * (self.growth_factor**self.num_layers)
            else:
                self.embed_dim = None
        else:
            self.embed_dim = embed_dim

        self.transformer_layers = transformer_layers

        if transformer_nhead is None:
            if self.bottleneck_type == "windowed_attention":
                self.transformer_nhead = self.embed_dim // 32
            elif self.bottleneck_type == "attention":
                self.transformer_nhead = self.transformer_window_size // 32
            else:
                self.transformer_nhead = None
        else:
            self.transformer_nhead = transformer_nhead

        if trial:
            self.epochs = trial.suggest_categorical("epochs", [8, 16, 32, 64])
            self.lr = trial.suggest_categorical("lr", [5e-3, 5e-4, 5e-5, 5e-6])
            self.dropout_rate = trial.suggest_categorical("dropout", [0, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1])
            self.weight_decay = trial.suggest_categorical("weight_decay", [0, 1e-8, 1e-7, 1e-6, 1e-5, 1e-4])
            self.num_layers = trial.suggest_categorical("num_layers", [2, 4, 6, 8])
            self.features = trial.suggest_categorical("features", [8, 16, 32, 64])

            # special params for attention
            if self.bottleneck_type == "windowed_attention":                
                self.transformer_window_size = trial.suggest_categorical("transformer_window_size", [50, 100, 150, 200, 250])
                self.embed_dim = self.features # force to be same size as features
                self.transformer_layers = trial.suggest_categorical("transformer_layers", [2,4,6])
                self.transformer_nhead = max(self.features // trial.suggest_categorical("heads_per_channel", [16, 32]), 1)
            else:
                self.bottleneck_type = "block"
            """
            self.growth_factor = trial.suggest_categorical("growth_factor", [1, 2])
            self.bottleneck_type = trial.suggest_categorical("bottleneck_type", ["windowed_attention", "attention", "block"])
            self.transformer_window_size = trial.suggest_categorical("transformer_window_size", [100, 150])
            self.transformer_layers = trial.suggest_categorical("transformer_layers", [1, 2, 4])
            self.transformer_nhead = trial.suggest_categorical("transformer_nhead", [1, 2, 4])
            self.features = trial.suggest_categorical("features", [16, 32])
            if self.bottleneck_type == "attention" or self.bottleneck_type == "windowed_attention":
                self.embed_dim = self.features * (self.growth_factor**self.num_layers)
            else:
                self.embed_dim = trial.suggest_categorical("embed_dim", [16, 32])
            """
        # if not a block, i.e actually used, make sure divisible 
        if self.bottleneck_type != "block":
            assert self.embed_dim % self.transformer_nhead == 0


        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        self.num_classes = len(self.label_map)
            
        self.model = UNet1D(input_size=len(self.data_columns), 
                            output_size=self.num_classes,
                            growth_factor=self.growth_factor,
                            features=self.features,
                            num_layers=self.num_layers, 
                            n_conv_steps_per_block=self.n_conv_steps_per_block, 
                            dropout_rate=self.dropout_rate, 
                            block_kernel_size=self.block_kernel_size,
                            up_down_sample_kernel_size=self.up_down_sample_kernel_size,
                            block_padding=self.block_padding,
                            bottleneck_type=self.bottleneck_type, 
                            transformer_window_size=self.transformer_window_size, 
                            embed_dim=self.embed_dim, 
                            transformer_layers=self.transformer_layers, 
                            transformer_nhead=self.transformer_nhead) 

        dirname = os.path.dirname(__file__)
        self.save_path = save_path

    def train(self, tr_probes, val_probes = None, fold = None, save_train_curve=False, show_train_curve=False):
        self.model = self.model.to(self.device)

        tr_dfs, _ = self.load_probes(tr_probes)
        tr_dataset = TimeSeriesDataset(tr_dfs, self.label_map, data_columns=self.data_columns, 
                                       class_column = "labels", ignore_N=self.ignore_N)
        tr_dataloader = DataLoader(tr_dataset, batch_size=self.batch_size, shuffle=True)

        # Compute label frequencies for weighting
        label_counts = Counter()
        for df in tr_dfs:
            label_counts.update(df["labels"].map(self.label_map).values)
        total_labels = sum(label_counts.values())

        # Compute weights: weight[c] = 1 / freq[c]
        num_classes = len(self.label_map)
        weights = torch.ones(num_classes, dtype=torch.float32)
        for label_idx in range(num_classes):
            count = label_counts.get(label_idx, 0)
            if count > 0:
                weights[label_idx] = total_labels / count
            else:
                weights[label_idx] = 0.0  # or a large value to penalize unseen class
        weights = weights.to(self.device)
            

        criterion = nn.CrossEntropyLoss(weight=weights)
        optimizer = optim.Adam(self.model.parameters(), lr=self.lr, weight_decay=self.weight_decay, capturable=False)

        train_losses = []
        validation_losses = []
        for epoch in tqdm.tqdm(range(self.epochs)):
            self.model.train()
            running_loss = 0.0
            for batch in tr_dataloader:
                x, y, weights = batch
                x, y, weights = x.to(self.device), y.to(self.device), \
                                weights.to(self.device)

                optimizer.zero_grad()
                #print(x.shape)
                outputs = self.model(x.permute(0,2,1))
                
                loss = criterion(outputs, y)

                weighted_loss = (loss) * weights
                weighted_loss = weighted_loss.mean()
                weighted_loss.backward()
                optimizer.step()
                
                running_loss += weighted_loss.item()
            train_loss = running_loss / len(tr_dataloader)
            train_losses.append(train_loss)

            # Get the validation loss
            if val_probes:
                val_dfs, _= self.load_probes(val_probes)
                val_dataset = TimeSeriesDataset(val_dfs, self.label_map, data_columns=self.data_columns,
                                                class_column = "labels",ignore_N=self.ignore_N)
                val_dataloader = DataLoader(val_dataset, batch_size=self.batch_size, shuffle=False)

                self.model.eval()
                with torch.no_grad():
                    running_loss = 0
                    for batch in val_dataloader:
                        x, y, weights = batch
                        x, y, weights = x.to(self.device), y.to(self.device), \
                                        weights.to(self.device)
                        outputs = self.model(x.permute(0,2,1))
                        loss = criterion(outputs, y)
                        
                        weighted_loss = loss * weights
                        weighted_loss = weighted_loss.mean()
                        running_loss += weighted_loss.item()
                    val_loss = running_loss / len(val_dataloader)
                    validation_losses.append(val_loss)
        
        def draw_loss_plot(tr_losses, val_losses):
            plt.plot(tr_losses, label = "Train")
            plt.plot(val_losses, label = "Validation")
            plt.xlabel("Epochs")
            plt.ylabel("Loss")
            plt.legend()

        if save_train_curve:
            draw_loss_plot(train_losses, validation_losses)
            if not os.path.isdir(self.save_path):
                os.mkdir(self.save_path)
            plt.savefig(f"{self.save_path}/loss_curve_fold{fold}.png")
        if show_train_curve:
            draw_loss_plot(train_losses, validation_losses)
            plt.show()

    def predict(self, probes, preprocess = False, return_logits=False):
        test_dataset = TimeSeriesDataset(probes, self.label_map, data_columns=self.data_columns,
                                         class_column = "labels", ignore_N=self.ignore_N)
        test_dataloader = DataLoader(test_dataset, batch_size=self.batch_size, shuffle=False)
        all_predictions = []
        all_logits = []
        self.model.eval()
        with torch.no_grad():
            for probe in test_dataloader:
                x, _, _ = probe
                x = x.to(self.device)

                outputs = self.model.forward(x.permute(0,2,1))
                if return_logits:
                    all_logits.append(outputs.cpu())
                outputs = outputs.argmax(dim=1).view(-1).cpu().tolist()
                output_labels = [self.inv_label_map[x] for x in outputs]
                all_predictions.append(output_labels)
            if return_logits:
                return all_predictions, all_logits
            else:
                return all_predictions

    def load_probes(self, probes):
        big_probe = pd.concat(probes, axis=0)
        return probes, big_probe

    def save(self):
        torch.save(self.model.state_dict(), "unet_weights")

    def load(self, path = None):
        self.model = UNet1D(input_size=len(self.data_columns), 
                            output_size=self.num_classes,
                            growth_factor=self.growth_factor,
                            features=self.features,
                            num_layers=self.num_layers, 
                            n_conv_steps_per_block=self.n_conv_steps_per_block, 
                            dropout_rate=self.dropout_rate, 
                            block_kernel_size=self.block_kernel_size,
                            up_down_sample_kernel_size=self.up_down_sample_kernel_size,
                            block_padding=self.block_padding,
                            bottleneck_type=self.bottleneck_type, 
                            transformer_window_size=self.transformer_window_size, 
                            embed_dim=self.embed_dim, 
                            transformer_layers=self.transformer_layers, 
                            transformer_nhead=self.transformer_nhead) 
        self.model.load_state_dict(torch.load(path, weights_only=True, map_location = self.device))
        self.model = self.model.to(self.device)

class TimeSeriesDataset(Dataset):
    def __init__(self, dfs, label_map, data_columns, class_column, transform=None, weight=False, ignore_N=False):
        """
        dfs: List of DataFrames, each containing 'x' (time series) and 'labels' columns.
        label_map: Dictionary mapping each letter to a number for prediction (should be a function that can be applied to a tensor).
        transform: Optional transform to be applied on the data.
        weight: Optional bool whether to weight by class or not.
        split_by_probes: Optional bool whether to split by probes or not.
        """
        self.data_columns = data_columns
        self.class_column = class_column
        self.transform = transform

        # Process each dataframe in the list of dfs
        self.x = []
        self.y = []
        self.weights = []

        # process splitting by probes and provide names for each file
        self.names = [df.attrs["file"] for df in dfs]

        for df in dfs:
            # Extract time series data and labels for each df
            x_tensor = torch.tensor(df[self.data_columns].values, dtype=torch.float32)
            y_tensor = torch.tensor(df[self.class_column].map(label_map).values, dtype=torch.long)
            self.x.append(x_tensor)
            self.y.append(y_tensor)

            # Handle weights if requested
            if weight:
                weights_tensor = torch.tensor(self.calculate_weights(df).tolist(), dtype=torch.float32)
            else:
                weights_tensor = torch.ones(x_tensor.shape, dtype=torch.float32)

            if ignore_N:
                mask = (df[self.class_column] == "N").values
                weights_tensor[mask] = 0.0

            self.weights.append(weights_tensor)

        # Pad sequences to the length of the longest time series in all datasets
        self.x = self.x
        self.y = self.y
        self.weights = self.weights

    def calculate_weights(self, df):
        '''
        calculate weights based on class makeup
        '''
        class_counts = df[self.class_column].value_counts().to_dict()
        total_samples = len(df)
        weights_by_class = {cls: total_samples / (len(class_counts) * count) for cls, count in class_counts.items()}
        return df[self.class_column].map(weights_by_class)

    def __len__(self):
        return len(self.x)

    def __getitem__(self, idx):
        x = self.x[idx]
        y = self.y[idx]
        weight = self.weights[idx]
        if self.transform:
            x = self.transform(x)
        return x, y, weight

def crop_after_upsampling(upsampled, downsampled, pad_left, pad_right):
    # Calculate the size difference and crop accordingly
    upsampled_size = upsampled.size(-1)
    downsampled_size = downsampled.size(-1)
    
    # Crop the tensor to match the size of the downsampled feature map
    if upsampled_size > downsampled_size:
        crop_left = pad_left
        crop_right = upsampled_size - downsampled_size - pad_right
        upsampled = upsampled[:, :, crop_left:upsampled_size - crop_right]
    
    return upsampled


def add_padding_for_downsampling(x, kernel_size, stride):
    # Calculate the necessary padding to keep the size even after downsampling
    pad_total = (stride - (x.size(-1) % stride)) % stride
    pad_left = pad_total // 2
    pad_right = pad_total - pad_left
    # Apply padding
    x_padded = F.pad(x, (pad_left, pad_right))
    return x_padded, (pad_left, pad_right)  # Return padding values to track for cropping


def pad_or_crop(tensor, dim, target_size):
    # Calculate the difference in size
    current_size = tensor.size(dim)
    diff = target_size - current_size
    if diff > 0:
        # Padding is needed: apply symmetric padding on both sides along the target dimension
        pad = [0] * (2 * tensor.dim())
        pad[-(2 * dim + 1)] = diff // 2       # pad before
        pad[-(2 * dim + 2)] = diff - diff // 2 # pad after
        tensor = F.pad(tensor, pad)
        
    elif diff < 0:
        # Cropping is needed: calculate the crop indices for symmetric cropping
        crop_start = (-diff) // 2
        crop_end = crop_start + target_size
        tensor = tensor.narrow(dim, crop_start, target_size)
        
    # If diff == 0, no operation is needed; the size is already correct
    return tensor



class UNet1D(nn.Module):
    def __init__(self, input_size, output_size, growth_factor, features, num_layers, n_conv_steps_per_block, dropout_rate, block_kernel_size, up_down_sample_kernel_size, block_padding, bottleneck_type, transformer_window_size, embed_dim, transformer_layers, transformer_nhead):
        super(UNet1D, self).__init__()
        self.num_layers = num_layers
        self.features = features
        self.growth_factor = growth_factor
        self.bottleneck_type = bottleneck_type
        self.transformer_window_size = transformer_window_size
        self.embed_dim = embed_dim
        self.transformer_layers = transformer_layers
        self.transformer_nhead = transformer_nhead


        # input layer
        self.in_conv = nn.Conv1d(in_channels=input_size, out_channels=features, kernel_size=1)

        # Encoding layers
        self.encoders = nn.ModuleList()
        self.pools = nn.ModuleList()
        for i in range(num_layers):
            encoder = EncoderBlock(features, growth_factor*features, n_conv_steps_per_block=n_conv_steps_per_block, dropout_rate=dropout_rate, block_kernel_size=block_kernel_size, block_padding=block_padding, growth_factor=growth_factor)
            self.encoders.append(encoder)
            self.pools.append(nn.MaxPool1d(kernel_size=up_down_sample_kernel_size, stride=2))
            features *= growth_factor  # Increase feature size

        # Bottleneck
        if self.bottleneck_type == "block":
            # in the bottleneck, we don't do any growth and just map features-->features
            self.bottleneck = EncoderBlock(features, features, n_conv_steps_per_block=n_conv_steps_per_block, dropout_rate=dropout_rate, block_kernel_size=block_kernel_size, block_padding=block_padding, growth_factor=1)
        elif self.bottleneck_type == "windowed_attention":
            self.bottleneck = WindowedTransformerBotleneck(features, self.transformer_window_size, self.embed_dim, self.transformer_layers, self.transformer_nhead)
        elif self.bottleneck_type == "attention":
            self.bottleneck = TransformerBotleneck(self.embed_dim, self.transformer_layers, self.transformer_nhead)
        else:
            assert False
        

        # Decoding layers
        self.upconvs = nn.ModuleList()
        self.decoders = nn.ModuleList()
        for i in range(num_layers):
            upconv = nn.ConvTranspose1d(features, features, kernel_size=up_down_sample_kernel_size, stride=up_down_sample_kernel_size)
            self.upconvs.append(upconv)
            decoder = DecoderBlock(features, features // growth_factor, n_conv_steps_per_block=n_conv_steps_per_block, dropout_rate=dropout_rate, block_kernel_size=block_kernel_size, block_padding=block_padding, growth_factor=growth_factor)
            self.decoders.append(decoder)
            features //= growth_factor  # Decrease feature size

        # output layer
        self.out_conv = nn.Conv1d(in_channels=features, out_channels=output_size, kernel_size=1)

    def forward(self, x):
        # Encoding path
        encodings = []
        paddings = []
        x = self.in_conv(x)

        initial_size = x.shape[2]

        for i in range(self.num_layers):
            x = self.encoders[i](x)
            # if growth factor is not 1, then downconv
            x = self.pools[i](x)
            encodings.append(x)

        # Bottleneck
        x = self.bottleneck(x)

        # Decoding path
        for i in range(self.num_layers):
            prev_encoding = encodings[-(i+1)]
            x = pad_or_crop(x, dim=2, target_size=prev_encoding.shape[2])
            x = torch.add(x, prev_encoding)
            x = self.upconvs[i](x)
            x = self.decoders[i](x)

        # pad up to the inital size
        x = pad_or_crop(x, dim=2, target_size=initial_size)
        x = self.out_conv(x)
        return x
    
    
    def predict_batch(self, batch, device):
        self.model.eval()
        with torch.no_grad():
            x, y, weights = batch
            x = x.unsqueeze(0).to(device)
            y = y.unsqueeze(0).to(device)

            outputs = self.forward(x.permute(0,2,1))

            masked_preds = outputs.argmax(dim=1).view(-1).cpu().tolist()
            masked_labels = y.cpu().view(-1).tolist()
            return masked_preds, masked_labels
        
    def predict(self, test_dataloader, device):
        all_preds = []
        all_labels = []
        self.model.eval()
        with torch.no_grad():
            for batch in test_dataloader:
                masked_preds, masked_labels = self.predict_batch(batch, device=device)

                all_preds.extend(masked_preds)
                all_labels.extend(masked_labels)

        return all_labels, all_preds

class EncoderBlock(nn.Module):
    def __init__(self, in_channels, out_channels, n_conv_steps_per_block, dropout_rate, block_kernel_size, block_padding, growth_factor):
        """
        Defines a single encoding block consisting of nX: Conv1d, InstanceNorm1d, GELU, dropout.
        """
        super(EncoderBlock, self).__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.growth_factor = growth_factor
        self.block = nn.Sequential()

        self.block.append(nn.Conv1d(in_channels, out_channels, kernel_size=block_kernel_size, padding=block_padding))
        self.block.append(nn.InstanceNorm1d(out_channels))
        self.block.append(nn.GELU())
        self.block.append(nn.Dropout(p=dropout_rate))
        
        for _ in range(n_conv_steps_per_block-1):
            self.block.append(nn.Conv1d(out_channels, out_channels, kernel_size=block_kernel_size, padding=block_padding))
            self.block.append(nn.InstanceNorm1d(out_channels))
            self.block.append(nn.GELU())
            self.block.append(nn.Dropout(p=dropout_rate))

    def forward(self, x):
        if self.growth_factor == 1:
            return self.block(x) + x # add skip connection
        elif self.growth_factor == 2:
            return self.block(x)

    def __repr__(self):
        return f"EncoderBlock({self.in_channels}, {self.out_channels})" + super(EncoderBlock, self).__repr__()[12:]


class DecoderBlock(nn.Module):
    def __init__(self, in_channels, out_channels, n_conv_steps_per_block, dropout_rate, block_kernel_size, block_padding, growth_factor):
        """
        Defines a single decoding block consisting of nX: Conv1d, InstanceNorm1d, and GELU.
        """
        super(DecoderBlock, self).__init__()
        self.growth_factor = growth_factor
        self.block = nn.Sequential()

        self.block.append(nn.Conv1d(in_channels, out_channels, kernel_size=block_kernel_size, padding=block_padding))
        self.block.append(nn.InstanceNorm1d(out_channels))
        self.block.append(nn.GELU())
        for _ in range(n_conv_steps_per_block-1):
            self.block.append(nn.Conv1d(out_channels, out_channels, kernel_size=block_kernel_size, padding=block_padding))
            self.block.append(nn.InstanceNorm1d(out_channels))
            self.block.append(nn.GELU())
            
    def forward(self, x):
        if self.growth_factor == 1:
            return self.block(x) + x # add skip connection
        elif self.growth_factor == 2:
            return self.block(x)

import torch.nn.functional as F

class WindowedTransformerBotleneck(nn.Module):
    def __init__(self, in_channels, window_size, embed_dim, transformer_layers, nhead):
        super(WindowedTransformerBotleneck, self).__init__()
        self.stride = window_size  # replace with stride for overlapping...
        self.window_size = window_size
        self.embed_dim = embed_dim
        self.in_channels = in_channels

        if self.in_channels != self.embed_dim:
            print("WARNING: USING EMBEDDING LAYERS IN TRANSFORMER")
            self.linear_embed = nn.Linear(self.in_channels, self.embed_dim)
            self.linear_decode = nn.Linear(self.embed_dim, self.in_channels)

        self.positional_encoder = PositionalEncoding1D(self.embed_dim)
        self.transformer_layer = nn.TransformerEncoderLayer(d_model=self.embed_dim, nhead=nhead)
        self.transformer_encoder = nn.TransformerEncoder(self.transformer_layer, num_layers=transformer_layers)
    
    def forward(self, x):
        batch, channels, seq_len = x.shape

        # --- Padding ---
        # Calculate the amount of padding needed to make seq_len a multiple of window_size
        pad_len = (self.window_size - (seq_len % self.window_size)) % self.window_size
        if pad_len > 0:
            # Pad on the right side of the sequence dimension
            x = F.pad(x, (0, pad_len))
        new_seq_len = x.shape[-1]  # = seq_len + pad_len

        # --- Windowing ---
        # x has shape: (batch, channels, new_seq_len)
        # Use unfold on the last dimension to create windows of size window_size
        # The resulting shape is (batch, channels, num_windows, window_size)
        x_windowed = x.unfold(dimension=2, size=self.window_size, step=self.stride)
        batch, channels, num_windows, window_size = x_windowed.shape
        
        # Rearrange dimensions to prepare for transformer encoding:
        # We want shape: (window_size, batch*num_windows, channels)
        x_windowed = x_windowed.permute(3, 0, 2, 1).reshape(window_size, batch * num_windows, channels)
        
        if self.in_channels != self.embed_dim:
            x_windowed = torch.vmap(self.linear_embed)(x_windowed)

        # --- Positional Encoding ---
        x_windowed = x_windowed + self.positional_encoder(x_windowed)
        
        # --- Transformer Encoding ---
        #print("TRANSFORMER", x_windowed.shape)
        encoded = self.transformer_encoder(src=x_windowed)
 
        if self.in_channels != self.embed_dim:
            encoded = torch.vmap(self.linear_decode)(encoded)
        # --- Reassemble ---
        encoded = encoded.reshape(window_size, batch, num_windows, channels).permute(1, 3, 2, 0)
        # Merge windows along the sequence dimension: (batch, channels, num_windows * window_size)
        output = encoded.reshape(batch, channels, -1)
        
        # Remove extra padded positions to recover the original sequence length
        if pad_len > 0:
            output = output[:, :, :seq_len]
        return output

    
class TransformerBotleneck(nn.Module):
    def __init__(self, embed_dim, transformer_layers, nhead):
        super(TransformerBotleneck, self).__init__()
        self.embed_dim = embed_dim

        self.positional_encoder = PositionalEncoding1D(self.embed_dim)
        self.transformer_layer = nn.TransformerEncoderLayer(d_model = self.embed_dim, nhead = nhead)
        self.transformer_encoder = nn.TransformerEncoder(self.transformer_layer, num_layers = transformer_layers)
    
    def forward(self, x):
        # Apply a positional embedding
        x = x.permute(2, 0, 1) # seq_len, batch, channels
        x_positional_encoded = x + self.positional_encoder(x)
        # Transformer Encoding
        encoded = self.transformer_encoder(src = x_positional_encoded)
        encoded = encoded.permute(1, 2, 0)
        return encoded
    
# NOTE: no longer in use
class MaxPool1dWithOddInputHandling(nn.Module):
    def __init__(self, pool_kernel_size, stride=None, padding=0, dilation=1, ceil_mode=False):
        super(MaxPool1dWithOddInputHandling, self).__init__()
        self.pool = nn.MaxPool1d(kernel_size=pool_kernel_size, stride=stride, padding=padding, dilation=dilation, ceil_mode=ceil_mode)

    def forward(self, x):
        # Check if the sequence length (dimension 2) is odd
        if x.size(2) % 2 != 0:
            # If odd, pad by 1 on the right side
            x = F.pad(x, (0, 1))
        # Apply the MaxPool1d operation
        return self.pool(x)


from sklearn.model_selection import KFold

class DataImport:
    """
    A class for importing and organizing labeled time-series datasets from CSV or Parquet files.

    Attributes:
    -----------
    df_list : list[pd.DataFrame]
        A list of preprocessed DataFrames, each storing its source filename in df.attrs["file"].
    random_state : int
        Random seed used for reproducibility in KFold shuffling.
    cross_val_iter : list[tuple]
        A list of (train_index, test_index) tuples for K-fold cross-validation splits.
    """
    def __init__(self, data_path, filetype: str, exclude=[], include = [], folds=5):
        """
        Initializes the DataImport class.

        Parameters:
        -----------
        data_path : str or Path
            Directory containing the data files (.csv or .parquet).
        filetype : str
            File extension to filter files by (e.g., ".csv" or ".parquet").
        exclude : list[str], optional
            Substrings; any file whose name contains one will be excluded.
        folds : int, optional
            Number of folds to use for K-fold cross-validation (default is 5).
        """
        self.df_list = import_data(data_path, filetype, exclude, include)
        self.random_state = 42
        kf = KFold(n_splits=folds, random_state=self.random_state, shuffle=True)
        self.cross_val_iter = list(kf.split(self.df_list))

    def process_df(self,  df: pd.DataFrame):
        labels = df["labels"].values
        probe_indices = self.leak_probe_finder(labels)
        filename_base = Path(df.attrs["file"]).stem

        probes = []
        names = []

        for i, (start, end) in enumerate(probe_indices):
            probe = df.iloc[start:end]
            probe.attrs["file"] = df.attrs["file"]
            probe.attrs["probe_index"] = i
            probes.append(probe)
            names.append(f"{filename_base}_{i}")

        return probes, names

    
    def get_probes(self, dfs: list[pd.DataFrame]) -> tuple[list[pd.DataFrame], list[str]]:
        """
        Extract probing segments from a list of DataFrames in parllel.

        Returns:
            all_probes: List of individual probe DataFrames
            all_probe_names: List of names (e.g., file_0, file_1, ...)
        """
        all_probes = []
        all_probe_names = []

        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.process_df, df) for df in dfs]
            for future in tqdm.tqdm(
                as_completed(futures),
                total=len(futures),
                desc="Getting probes",
                position=2,
                leave=False
            ):
                probes, names = future.result()
                all_probes.extend(probes)
                all_probe_names.extend(names)

        sorted_pairs = sorted(
            zip(all_probes, all_probe_names),
            key=lambda pair: pair[0].attrs.get("file", "")
        )

        sorted_probes, sorted_names = zip(*sorted_pairs) if sorted_pairs else ([], [])
        return list(sorted_probes), list(sorted_names)

    
    def leak_probe_finder(self, labels):
        """
        Returns (start, end) index tuples for contiguous probe segments
        with labels not in NON_PROBING_LABELS.
        """
        NON_PROBING_LABELS = {"N", "Z"}

        upper_labels = np.char.upper(labels.astype(str))
        mask = ~np.isin(upper_labels, list(NON_PROBING_LABELS))
        probe_indices = np.where(mask)[0]

        if probe_indices.size == 0:
            return []

        breaks = np.where(np.diff(probe_indices) > 1)[0]
        segment_starts = np.insert(probe_indices[breaks + 1], 0, probe_indices[0])
        segment_ends = np.append(probe_indices[breaks], probe_indices[-1])

        return list(zip(segment_starts, segment_ends))






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


    def generate_label_colors(labels):
        labels = sorted(set(labels))
        colors = distinctipy.get_colors(len(labels))
        hex_colors = [distinctipy.get_hex(color) for color in colors]
        return dict(zip(labels, hex_colors))
    
    unique_labels = ['B', 'B2', 'B4', 'C', 'CG', 'D', 'DG', 'F', 'F1', 'F2', 'F3', 'F4', 'FB', 'G', 'N', 'P', 'Z']
    label_to_color = generate_label_colors(unique_labels)

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
    precision, recall, fscore, _ = precision_recall_fscore_support(
        labels_true, labels_pred, labels=labels, average=None, zero_division=0
    )
    metrics = {}
    for label, p, r, f in zip(labels, precision, recall, fscore):
        metrics[f"{label}_precision"] = p
        metrics[f"{label}_recall"] = r
        metrics[f"{label}_fscore"] = f

    out_dataframe = pd.DataFrame([metrics])

    # accuracy
    accuracy = accuracy_score(labels_true, labels_pred)
    out_dataframe["accuracy"] = accuracy

    # confusion matrix
    ConfusionMatrixDisplay.from_predictions(labels_true, labels_pred, \
                                            normalize = 'true')
    plt.savefig(rf"{save_path}/{model_name}_ConfusionMatrix_Fold{fold}.png")

    # difference plots
    base_name = Path(model_name).name
    for df, preds, name in zip(test_data, predicted_labels, test_names):
        fig = plot_labels(
            df["time"],
            df["voltage"],
            df["labels"].values,
            np.asarray(preds)
        )
        file_stem = Path(name).stem
        fig_path = Path(save_path) / "difference_plots" / f"{base_name}_{file_stem}_Fold{fold}.png"
        fig_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(fig_path)
        plt.close(fig)

    print(f"Fold {fold} Overall Accuracy: {accuracy}")
    return labels_true, labels_pred, out_dataframe







if __name__ == "__main__":
    EXCLUDE = {
        "a01", "a02", "a03", "a10", "a15",
        "b01", "b02", "b04", "b07", "b12", "b188", "b202", "b206", "b208",
        "c046", "c07", "c09", "c10",
        "d01", "d03", "d056", "d058", "d12",
        "_b", "_c"
    }
    NUM_FOLDS = 5

    with open("../data_quality_map.json", "r") as f:
        QUALITY_MAP = json.load(f)

    data = DataImport("../data", ".parquet", exclude=EXCLUDE)
    all_probes, all_names = data.get_probes(data.df_list)
    df_list = data.df_list

    if len(df_list) == 0:
        assert "No data loaded. Is the path to the data directory correct?"

    # === K-Fold Cross-Validation ===
    NUM_FOLDS = 5
    kf = KFold(n_splits=NUM_FOLDS, shuffle=True, random_state=42)

    for fold_idx, (train_idx, test_idx) in enumerate(kf.split(all_probes)):
        print(f"\n===== Fold {fold_idx + 1}/{NUM_FOLDS} =====")

        train_probes = [all_probes[i] for i in train_idx]
        test_probes  = [all_probes[i] for i in test_idx]
        test_names   = [all_names[i] for i in test_idx]

        # Init model (no save path)
        unet = Model()
        unet.epochs=32
        print("Training model...")
        unet.train(train_probes, val_probes=None, show_train_curve=False, save_train_curve=False)

        print("Testing model...")
        predicted_labels = unet.predict(test_probes)

        print("Generating report...")
        # You can hardcode or parametrize the output folder
        report_dir = f"./out/unet_crossval/fold_{fold_idx}"
        Path(report_dir).mkdir(parents=True, exist_ok=True)
        _, _, stats = generate_report(test_probes, predicted_labels, test_names, report_dir, "UNet", fold=fold_idx)
        print(stats)

    print("Cross-validation complete.")




    # unet = Model()

    # unet.save_path = "./out"

    # EXCLUDE = {
    #     "a01", "a02", "a03", "a10", "a15",
    #     "b01", "b02", "b04", "b07", "b12", "b188", "b202", "b206", "b208",
    #     "c046", "c07", "c09", "c10",
    #     "d01", "d03", "d056", "d058", "d12",
    # }

    # with open("../data_quality_map.json", "r") as f:
    #     QUALITY_MAP = json.load(f)  



    # data = DataImport("../data", ".parquet", exclude=EXCLUDE)
    # full_data, _ = data.get_probes(data.df_list)
       
    # print("Training model on full dataset (no validation/test)...")
    # unet.train(full_data, val_probes=None, show_train_curve=True, save_train_curve=True)

    # print("Saving trained model...")
    # unet.save()

    # print("Full training complete.")

