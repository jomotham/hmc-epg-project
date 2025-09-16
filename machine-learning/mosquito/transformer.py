import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from positional_encodings.torch_encodings import PositionalEncoding1D
from torch.utils.data import Dataset, DataLoader
import tqdm
import matplotlib.pyplot as plt
import optuna

class Model:
    def __init__(self, trial = None, sample_rate = 100, embed_dim = 32, epochs = 32, save_path = None, lr = 5e-4, transformer_layers = 2, nhead = 16):
        self.sample_rate = sample_rate
        self.stride = self.sample_rate // 2
        self.window_size = self.sample_rate * 1
        self.transformer_layers = transformer_layers
        self.nhead = nhead
        self.batch_size = 1
        self.embed_dim = embed_dim
        self.lr = lr
        self.epochs = epochs
        if trial:
            self.window_size = self.sample_rate * trial.suggest_int("window_size", 1, 3)
            self.transformer_layers = trial.suggest_categorical("transformer_layers", [1, 2, 4, 8])
            self.nhead = trial.suggest_categorical("nhead factor", [1, 2, 4, 8, 16])
            self.embed_dim = self.nhead * trial.suggest_categorical("embedding factor", [1, 2, 4, 8])
            self.lr = trial.suggest_categorical("learning rate", [5e-3, 5e-4, 5e-5, 5e-6, 5e-7])
            self.epochs = trial.suggest_categorical("epochs", [8, 16, 32, 64])
   
        self.model = TransformerLabeler(self.sample_rate, 
                                        self.stride, 
                                        self.window_size,
                                        self.embed_dim,
                                        self.transformer_layers,
                                        self.nhead,
                                        7)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.save_path = save_path

    def train(self, probes, test_probes = None, fold = None):
        """
        probes is expected to be a list of probe dataframes
        """
        tr_dataset = EPGDataset(probes)
        tr_dataloader = DataLoader(tr_dataset, batch_size = self.batch_size, 
                                      shuffle = True)
        """
        test_dataset = EPGDataset(probes)
        test_dataloader = DataLoader(test_dataset, batch_size = self.batch_size, 
                                      shuffle = True)
        """
        
        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.lr, capturable=False)

        self.model = self.model.to(self.device)

        train_losses = []
        test_losses = []
        for epoch in tqdm.tqdm(range(self.epochs)):
            self.model.train()
            running_loss = 0.0
            for batch in tr_dataloader:
                x, y = batch
                x, y = x.to(self.device), y.to(self.device).float()
                optimizer.zero_grad()
                outputs = self.model(x)
                loss = criterion(outputs, y.squeeze(0))
                loss.backward()
                optimizer.step()
                running_loss += loss.item()            

            train_losses.append(running_loss / len(tr_dataloader))
        """
            # Get test loss
            running_loss = 0
            with torch.no_grad():
                self.model.eval() 
                for batch in test_dataloader:
                    x, y = batch
                    x, y = x.to(self.device).float(), y.to(self.device).float()
                    outputs = self.model(x)
                    loss = criterion(outputs, y.squeeze(0))
                    running_loss += loss.item()                    
                test_losses.append(running_loss / len(test_dataloader))
        plt.figure()
        plt.plot(train_losses, label = "Train")
        plt.plot(test_losses, label = "Test")
        plt.xlabel("Epochs")
        plt.ylabel("Loss")
        plt.legend()
        #plt.savefig(f"{self.save_path}/loss_curve_fold{fold}.png")
        """

    def predict(self, probes, return_logits = False):
        self.model.eval()
        for probe in probes:
            if "labels" not in probe.columns:
                probe["labels"] = "NP"
        dataset = EPGDataset(probes)
        dataloader = DataLoader(dataset, batch_size = self.batch_size)
        all_predictions = []
        all_logits = []
        for probe in dataloader:
            x, _ = probe
            x = x.to(self.device)
            
            outputs = self.model(x)
            if return_logits:
                all_logits.append(outputs.cpu())
            outputs = outputs.argmax(dim=1).view(-1).cpu().tolist()
            output_labels = [dataset.inv_label_map[x] for x in outputs]
            all_predictions.append(output_labels)
        if return_logits:
            return all_predictions, all_logits
        else:
            return all_predictions

    def save(self):
        torch.save(self.model.state_dict(), "transformer_weights")

    def load(self, path = None):
        self.model = TransformerLabeler(self.sample_rate, 
                                        self.stride, 
                                        self.window_size,
                                        self.embed_dim,
                                        self.transformer_layers,
                                        self.nhead,
                                        7)
        self.model.load_state_dict(torch.load(path, weights_only=True, map_location = self.device))
        self.model = self.model.to(self.device)



class TransformerLabeler(nn.Module):
    def __init__(self, sample_rate, stride, window_size, embed_dim, transformer_layers, nhead, classes):
        super(TransformerLabeler, self).__init__()
        self.stride = window_size #replace with stride for overlapping...
        self.window_size = window_size
        self.embed_dim = embed_dim
        
        # Layers
        self.linear_embed = nn.Linear(self.window_size, self.embed_dim)
        self.act = nn.GELU()
        self.positional_encoder = PositionalEncoding1D(self.embed_dim)
        self.transformer_layer = nn.TransformerEncoderLayer(d_model = self.embed_dim, nhead = nhead)
        self.transformer_encoder = nn.TransformerEncoder(self.transformer_layer, num_layers = transformer_layers)
        self.linear_decode = nn.Linear(self.embed_dim, classes)
        self.conv1d = torch.nn.Conv1d(7,7,2) # 7 features in and out, kernel of 2
        self.instnorm1d = torch.nn.InstanceNorm1d(7) # same here

    def forward(self, probe):
        """
        probe: a (probe length), tensor of volt values
        returns a (probe length) tensor of label logits
        """
        # Break data up into windows
        probe_windows = probe.squeeze().unfold(0, self.window_size, self.stride)
        # Embed probe data by applying a linear layer to each window
        probe_embeddings = torch.vmap(self.linear_embed)(probe_windows)
        probe_embeddings = torch.vmap(self.act)(probe_embeddings)
        # Apply a positional embedding
        probe_embeddings = probe_embeddings + \
                           self.positional_encoder(probe_embeddings.unsqueeze(0)).squeeze(0)
        # Transformer Encoding
        encoded = self.transformer_encoder(src = probe_embeddings)
        # Decoder
        output_decoded = torch.vmap(self.linear_decode)(encoded) # (windows, features)
        output_decode = torch.vmap(self.act)(output_decoded)
        # Progressive Upsampling, double length and conv until its almost the same size
        for i in range(int(np.log2(probe.shape[1] / output_decoded.shape[0]))):
            output_length = output_decoded.shape[0]
            upsampler = torch.nn.Upsample(size = output_length * 2, mode = 'linear')
            output_decoded = upsampler(output_decoded.unsqueeze(0).permute(0, 2, 1)).squeeze().permute(1, 0)
            output_decoded = self.conv1d(output_decoded.permute(1, 0)) # (features, windows)
            output_decoded = self.instnorm1d(output_decoded)
            output_decode = self.act(output_decode)
            output_decoded = self.conv1d(output_decoded).permute(1, 0)
        # Bring back up to original length in a final step
        upsampler = torch.nn.Upsample(size = probe.shape[1], mode = 'linear')
        output = upsampler(output_decoded.unsqueeze(0).permute(0, 2, 1)).squeeze().permute(1, 0)
        return output

class EPGDataset(Dataset):
    def __init__(self, probes, data_column="post_rect"):
        """
        probes: a list of probe dataframes
        """
        self.label_map = {"NP" : 0,
                          "J"  : 1,
                          "K"  : 2,
                          "L"  : 3,
                          "M"  : 4,
                          "N"  : 5,
                          "W"  : 6}
        self.inv_label_map = {i: label for label,i in self.label_map.items()}

        self.probe_tensors = []
        self.label_tensors = []
        for probe in probes:
            self.probe_tensors.append(torch.tensor(probe[data_column], dtype = torch.float32))
            # We need to turn the labels into one-hot encodings
            labels = probe["labels"].replace("Z", "W")
            labels = list(map(lambda x : self.label_map[x], labels))
            labels = torch.tensor(labels)
            labels = F.one_hot(labels, num_classes = len(self.label_map))
            self.label_tensors.append(labels)

    def __len__(self):
        return len(self.probe_tensors)

    def __getitem__(self, idx):
        return self.probe_tensors[idx], self.label_tensors[idx]
