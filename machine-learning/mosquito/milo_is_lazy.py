# %%
from model_eval import *
from data_augmentation import build_augmented_dataset, Probe
import numpy as np
import torch
import random

random.seed(42)
torch.manual_seed(42)
np.random.seed(42)
# python -m model_eval --data_path c:\Users\milok\clasp_transitions --model_path c:\Users\milok\USDA-Auburn\ML\unet.py --save_path c:\Users\milok\USDA-Auburn\ML\UNET_POST --model_name UNET_POST --augment True --post_process V --epochs 45
data_path = r"c:\Users\milok\clasp_transitions"
model_path = r"c:\Users\milok\USDA-Auburn\ML\unet.py"
save_path = r"c:\Users\milok\USDA-Auburn\ML\NEW_UNET"
model_name = r"NEW_UNET"
save = False
augment = False
show_train_curve=True

data = DataImport(data_path, folds=2)
train_data, test_data, test_names = data.get_train_test_split()

if augment:
    augmented_train_data = build_augmented_dataset(train_data)
    print(len(train_data), len(augmented_train_data))

model_import = dynamic_importer(model_path)

attention_config = {
    "epochs": 50,
    "lr": 5e-4,
    "num_layers": 9,
    "growth_factor": 2,
    "features": 16,
    "n_conv_steps_per_block": 2,
    "block_kernel_size": 3,
    "up_down_sample_kernel_size": 2,
    "block_padding": 1,
    "weight_decay": 0,
    "dropout_rate": 0,
    "save_path": save_path,
    "bottleneck_type":"attention",
    "transformer_window_size":None,
    "embed_dim":None,
    "transformer_layers":2,
    "transformer_nhead":None,
}

# acc: 0.7830572376442279, precision: 0.5903082133102512, recall: 0.5430666576497235, fscore: 0.5152501525680674
windowed_attention_config = {
    "epochs": 30,
    "lr": 5e-4,
    "num_layers": 4,
    "growth_factor": 1,
    "features": 16,
    "n_conv_steps_per_block": 2,
    "block_kernel_size": 3,
    "up_down_sample_kernel_size": 2,
    "block_padding": 1,
    "weight_decay": 0,
    "dropout_rate": 0,
    "save_path": save_path,
    "bottleneck_type":"windowed_attention",
    "transformer_window_size":150,
    "embed_dim":16,
    "transformer_layers":1,
    "transformer_nhead":1,
}

flat_unet_windowed_attention_config = {
    "epochs": 1,
    "lr": 5e-4,
    "num_layers": 0,
    "growth_factor": 1,
    "features": 16,
    "n_conv_steps_per_block": 2,
    "block_kernel_size": 3,
    "up_down_sample_kernel_size": 2,
    "block_padding": 1,
    "weight_decay": 0,
    "dropout_rate": 0,
    "save_path": save_path,
    "bottleneck_type":"windowed_attention",
    "transformer_window_size":100,
    "embed_dim":8,
    "transformer_layers":4,
    "transformer_nhead":1,
}

block_config = {
    "epochs": 50,
    "lr": 5e-4,
    "num_layers": 4,
    "growth_factor": 2,
    "features": 16,
    "n_conv_steps_per_block": 2,
    "block_kernel_size": 3,
    "up_down_sample_kernel_size": 2,
    "block_padding": 1,
    "weight_decay": 0,
    "dropout_rate": 0.0,
    "save_path": save_path,
    "bottleneck_type":"block",
    "transformer_window_size":None,
    "embed_dim":None,
    "transformer_layers":None,
    "transformer_nhead":None,
}

# acc: 0.7623329274886051, precision: 0.7313863706208621, recall: 0.6660977450946134, fscore: 0.670917510803723
current_best = {
    "epochs": 50,
    "lr": 5e-4,
    "num_layers": 8,
    "growth_factor": 1,
    "features": 32,
    "n_conv_steps_per_block": 2,
    "block_kernel_size": 3,
    "up_down_sample_kernel_size": 2,
    "block_padding": 1,
    "weight_decay": 1e-6,
    "dropout_rate": 1e-6,
    "save_path": save_path,
    "bottleneck_type":"block",
    "transformer_window_size":None,
    "embed_dim":None,
    "transformer_layers":None,
    "transformer_nhead":None,
    "ignore_N":True,
}

#Trial 36 finished with value: 0.7402015172114621 and parameters: {'epochs': 64, 'lr': 0.0005, 'dropout': 1e-05, 'weight_decay': 1e-05, 'num_layers': 8, 'features': 64, 'transformer_window_size': 200, 'transformer_layers': 2, 'heads_per_channel': 32}

model = model_import.Model(**current_best)
data_to_train = train_data if not augment else augmented_train_data
trained_model = model.train(train_data, test_data, save_train_curve=save, show_train_curve=False)

predicted_labels, logits = model.predict(test_data, return_logits=True)

if save:
    generate_report(test_data, predicted_labels, test_names, save_path, model_name)
else:
    labels_true = []
    labels_pred = []
    for df, preds in zip(test_data, predicted_labels):
        labels_true.extend(df["labels"].values)
        labels_pred.extend(preds)
    labels = sorted(np.unique(labels_true))
    precision, recall, fscore, _ = precision_recall_fscore_support(labels_true, labels_pred, 
                                                            labels=labels, average = 'macro')
    accuracy = accuracy_score(labels_true, labels_pred)
    print(f"acc: {accuracy}, precision: {precision}, recall: {recall}, fscore: {fscore}")
print(f"Peak Allocated: {torch.cuda.max_memory_allocated() / 1024**2:.2f} MB")

# %%
import numpy as np
import matplotlib.pyplot as plt
from scipy.special import softmax
import torch
import torch.nn.functional as F
from scipy.signal import savgol_filter

label_to_color = {
        "NP": "red",
        "J": "blue",
        "K": "green",
        "L": "purple",
        "M": "pink",
        "N": "cyan",
        "Z": "orange",
        "W": "orange"
}

def moving_average_smoothing(logit, window_size=1001):    
    kernel = torch.ones(1, 1, window_size) / window_size  # [1, 1, window_size]
    logit = logit.unsqueeze(1)  # Shape: [6, 1, n]

    padding = window_size // 2
    smoothed_logit = F.conv1d(logit, kernel, padding=padding, groups=1)

    # Remove the added channel dimension
    return smoothed_logit.squeeze(1)  # Shape: [6, n]

def savitzky_golay_smoothing(logits, window_size=301, poly_order=3):
    return torch.tensor(savgol_filter(logits.numpy(), window_size, poly_order, axis=1))

def plot_changepoints(ax, labels):
    change_points = labels.ne(labels.shift()).cumsum()
    segments = labels.groupby(change_points).apply(lambda g: (g.iloc[0], g.index[0], g.index[-1])).tolist()
    names = [s[0] for s in segments]
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
    if ax is not None:
        ax.text(1.05, 0.5, f"Number of unique states {len(names)}", transform=ax.transAxes, fontsize=12,
                verticalalignment='center', bbox=props)
    return segments

def simple_plot(time, voltage, true_labels):
    fig, axs = plt.subplots(1, 1, sharex = True, figsize=(10, 6))
    fill_min, fill_max = voltage.min(), voltage.max()

    axs = [axs]
    
    # First plot will be the true labels
    #axs[0].plot(time, voltage, color = "black")
    for label, color in label_to_color.items():
        fill = axs[0].fill_between(time, fill_min, fill_max, 
                where = (true_labels == label), color=color, alpha = 0.5)
        fill.set_label(label)
    axs[0].legend(bbox_to_anchor=(0.5, 1), 
                  bbox_transform=fig.transFigure, loc="upper center", ncol=9)
    axs[0].set_title("True Labels")
    axs[0].set_ylabel("Volts")

    fig.supxlabel("Time (s)")  
    
    fig.tight_layout()

def plot_labels(time, voltage, true_labels, logit, inv_label_map):
    """
    plot_labels produced a matplotlib figure containing three subplots
        that visualize a wave+form along with the true and predicted labels
    Input:
        time: a series of time values
        voltage: a time series of voltage values from the waveform
        true_labels: a time series of the true label for each time point
        pred_labels: a time series of the predicted labels for each time point
    Output:
        (fig, axs): a tuple
    """

    fig, axs = plt.subplots(6, 1, sharex = True, figsize=(10, 6))
    fill_min, fill_max = voltage.min(), voltage.max()
    
    # First plot will be the true labels
    #axs[0].plot(time, voltage, color = "black")
    for label, color in label_to_color.items():
        fill = axs[0].fill_between(time, fill_min, fill_max, 
                where = (true_labels == label), color=color, alpha = 0.5)
        fill.set_label(label)
    axs[0].legend(bbox_to_anchor=(0.5, 1), 
                  bbox_transform=fig.transFigure, loc="upper center", ncol=9)
    axs[0].set_title("True Labels")
    axs[0].set_ylabel("Volts")

    # Second plot will be the predicted labels
    probs = softmax(logit, axis=0)
    labels = [inv_label_map[i] for i in range(len(probs))]
    colors = [label_to_color[label] for label in labels]
    axs[1].stackplot(time, probs, labels=labels, colors=colors, alpha=0.5)
    axs[1].set_title("Stacked Logit Probs")
    axs[1].set_ylabel("Probability")

    # Third plot
    smooth_logit = savitzky_golay_smoothing(logit)
    smooth_probs = softmax(smooth_logit, axis=0)
    labels = [inv_label_map[i] for i in range(len(probs))]
    colors = [label_to_color[label] for label in labels]
    axs[2].stackplot(time, smooth_probs, labels=labels, colors=colors, alpha=0.5)
    axs[2].set_title("Stacked Smoothed Logit Probs")
    axs[2].set_ylabel("Probability")


    # Fourth plot
    preds = logit.argmax(dim=0).view(-1).tolist()
    pred_labels = pd.Series([inv_label_map[p] for p in preds])
    #axs[3].plot(time, voltage, color = "black")
    for label, color in label_to_color.items():
        axs[3].fill_between(time, fill_min, fill_max, 
                where = (pred_labels == label), color=color, alpha = 0.5)
    axs[3].set_title("Predicted Labels")
    raw_prediction_segments = plot_changepoints(axs[3], pred_labels)


    # Fifth plot
    preds = smooth_logit.argmax(dim=0).view(-1).tolist()
    pred_labels = pd.Series([inv_label_map[p] for p in preds])
    #axs[4].plot(time, voltage, color = "black")
    for label, color in label_to_color.items():
        axs[4].fill_between(time, fill_min, fill_max, 
                where = (pred_labels == label), color=color, alpha = 0.5)
    axs[4].set_title("Predicted Smooth Labels")
    smoothed_prediction_segments = plot_changepoints(axs[4], pred_labels)

    # # Sixth plot
    # pred_labels = pd.Series(generate_viterbi(logit, alpha=0.5))
    # #axs[5].plot(time, voltage, color = "black")
    # for label, color in label_to_color.items():
    #     axs[5].fill_between(time, fill_min, fill_max, 
    #             where = (pred_labels == label), color=color, alpha = 0.5)
    # axs[5].set_title("Markovian Labels")
    # markov_prediction_segments = plot_changepoints(axs[5], pred_labels)
    markov_prediction_segments = None
    #Axes titles and such
    fig.supxlabel("Time (s)")  
    
    fig.tight_layout()
    return fig, (raw_prediction_segments, smoothed_prediction_segments, markov_prediction_segments)


# 1 is easy
# 2 looks good
# 4 is kinda sus
idx = 1
df = test_data[idx]
logit = logits[idx]
logit = logit.squeeze(0).detach()  
fig, (raw_prediction_segments, smoothed_prediction_segments, markov_prediction_segments) = plot_labels(df["time"], df["pre_rect"], df["labels"].values, logit, inv_label_map=model.inv_label_map)
plt.show()



# %%
from collections import defaultdict
import networkx as nx
EPS = 1e-9

from transition_matrix import transition_matrix_dict
transition_matrix_df = pd.DataFrame(transition_matrix_dict)
probes = [Probe().init_df(p) for p in train_data]
lens = defaultdict(list)
for probe in probes:
    for state_df, state_name in zip(probe.state_dfs, probe.state_names):
        lens[state_name].append(len(state_df))
average_length_dict = {state_name:np.mean(lens) for state_name, lens in lens.items()}
lambda_list = np.array([1/(average_length_dict[state_name]+EPS) for state_name in transition_matrix_df.columns if state_name != "NP"])

starting_probs = (transition_matrix_df.loc["NP"]).drop(index="NP").values
transition_matrix_without_NP = transition_matrix_df.drop(columns="NP", index="NP")
transition_matrix_without_NP_normed = transition_matrix_without_NP.div(transition_matrix_without_NP.sum(axis=1), axis=0).fillna(0)

def extract_label_sequences(probes):
    sequences = []
    for df in probes:
        sequences.append(tuple(key for key, _ in groupby(df['labels'])))
    return sequences

list_sequences = extract_label_sequences(train_data+test_data)
all_sequences = set(list_sequences)



# problems: 48, 51
'''
cxtonhand6dec2021no2 has a probe with only 'J', 'K', 'L' (skips W)
handcxt23aug2021no8 has a probe with only 'J', 'K', 'W' (skips L)
'''

transition_matrix_without_NP_LOOP = transition_matrix_without_NP.copy()
transition_matrix_without_NP_LOOP.loc["L", "M"] = 0
transition_matrix_without_NP_LOOP_normed = transition_matrix_without_NP_LOOP.div(transition_matrix_without_NP_LOOP.sum(axis=1), axis=0).fillna(0)

G = nx.from_pandas_adjacency(transition_matrix_df, create_using=nx.DiGraph)

pos = nx.spring_layout(G)
nx.draw(G, pos, with_labels=True, node_color='lightgreen', node_size=2000, arrows=True)

#edge_labels = nx.get_edge_attributes(G, 'weight')
#nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)

plt.title("Weighted Directed Graph (from DataFrame)")
plt.show()

print("IS DAG?", nx.is_directed_acyclic_graph(G))
#print("Cycles:", list(nx.simple_cycles(G)))

endings_from_ = {
    "M": list(nx.all_simple_paths(G, source="M", target="W")),
    "L": list(nx.all_simple_paths(G, source="L", target="W"))
}

paths_to_ = {
    "L": list(nx.all_simple_paths(G, source="NP", target="L")),
    "M": list(nx.all_simple_paths(G, source="NP", target="M"))
}

other_dict = {"L":"M", "M":"L"}
allowed_repeats = 1

'''
repeat = 0
L (0)

repeat = 1
L->M->L (2)
L->M (1)

repeat = 2
L->M->L->M->L (4)
L->M->L->M (3)
'''
cur_path = ["L"]
middles = [cur_path[:]]
for num_repeats in range(0, 2*allowed_repeats):
    cur_path.append(other_dict[cur_path[-1]])
    middles.append(cur_path[:]) # copy

augmented_paths = set()
for start_path in paths_to_["L"]:
    for middle_path in middles:
        middle_end = middle_path[-1]
        for end_path in endings_from_[middle_end]:
            if "NP" in end_path:
                continue

            augmented_paths.add(tuple(
                start_path[1:-1] # skip NP and start of mid
                + middle_path
                + end_path[1:] # skip end of mid
                ))

for path in augmented_paths:
    print("->".join(path))

print("combined len", sum(len(p) for p in augmented_paths))

print("subset?", all_sequences < augmented_paths)
print(len(all_sequences), len(all_sequences - augmented_paths))
print(all_sequences - augmented_paths)
for seq in augmented_paths:
    print(repr(seq)+",")


'''
NP>J
NP>K
J>K
J>NP (I sometimes see this transition, but I only scored probes in the TXT files, and surface salivation (J) without penetration of the skin (K) does not qualify as a probe, so I have no records of which files this transition occurred in) 
K>L
K>M (I’ve never seen this occur during probing on a human/animal host; however, on artificial substrates (blood feeders, synthetic skin, sucrose solution), the voltage rises when mouthparts are inserted, and then waveform M immediately starts. The initial voltage rise from insertion into artificial substrates does not look like a normal waveform K on a natural host, but it is correlated with penetration of the membrane/liquid, so it might qualify as K. Then again, it might be more appropriate to name the initial voltage rise associated with “penetration” of a liquid/membrane/artificial substrate as something other than K.  Not relevant to this dataset, but it might be helpful to build in this transition as a possibility because one of our funder’s goals long term goals is to use EPG to study disease transmission in artificial systems and reduce the need for animal research subjects) 
K>W (This can happen in some mosquitoes under specific conditions, but it does not occur in this dataset, or if it did, I was unable to detect it)
L>M
L>N (This can happen in some mosquitoes under specific conditions, but it does not occur in this dataset, or if it did, I was unable to detect it)
L>W
M>L
M>N
M>W
N>L (this can happen in some mosquitoes under specific conditions, but it does not occur in this dataset, or if it did, I was unable to detect it)
N>W
W>NP


'''