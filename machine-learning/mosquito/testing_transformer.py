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
model_path = r"c:\Users\milok\USDA-Auburn\ML\transformer.py"
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

model = model_import.Model()
model.window_size = 300
model.transformer_layers=8
model.nhead=2

data_to_train = train_data if not augment else augmented_train_data
trained_model = model.train(train_data, test_data)

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
