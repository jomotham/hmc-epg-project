import windaq as wdq
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from os import walk

def label_importer(filename):
	with open(filename) as file:
		lines = [eval(line.replace("W", "Z").rstrip()) for line in file]	
	# Remove leading whitespace
	lines = [line.strip() if type(line) == str else line for line in lines]
	total_indices = int(round((lines[1][0] - lines[1][1]) * 100, 0) + 1)
	output = np.empty(total_indices, dtype="U2")
	# Turn into a list
	for i in range(0, len(lines), 2):
		start = None
		if i == 0:
			start = 0
		else:
			start = int(round(lines[i - 1][0] * 100, 0))

		end = int(round(lines[i + 1][0] * 100, 0))
		output[start:end + 1] = lines[i].upper()

	# Rest of file is NP
	output[end:] = "NP" # make use of fact that end is still saved
	
	return output

print("Indexing Data...")
# Data Inventory, gives Ri, Voltage, Current information
data_inventory = pd.read_excel("Tarsalis\\Tarsalis data for CS HMC\\File inventory for CxT library.xlsx", skiprows=1)
# Fix inconsistent data entry
data_inventory["Name of data file"] = data_inventory["Name of data file"].apply(lambda x : x.replace(" ", ""))
data_inventory["Name of data file"] = data_inventory["Name of data file"].apply(lambda x : x[:-2] + x[-1:] if x[-2] == "0" else x)
data_inventory["Name of data file"] = data_inventory["Name of data file"].apply(lambda x : x.replace("test", ""))
data_inventory["Name of data file"] = data_inventory["Name of data file"].apply(lambda x : x.lower())
data_inventory["Name of data file"] = data_inventory["Name of data file"].apply(lambda x : x.replace("*", ""))

# Get the paths to all the windaq files
ws = [w for w in walk("Tarsalis\\Tarsalis data for CS HMC\\Waveform Library Files")]
windaq_files = []
for w in ws:
	for file in w[2]:
		if file.endswith(".WDQ"):
			windaq_files.append(w[0] + "//" + file)

# Import all the label files
labels = {}
for w in ws:
	for file in w[2]:
		if file.endswith(".txt"):
			name = file.split("//")[-1].split(".")[0]
			labels[name] = label_importer(w[0] + "//" + file)

dfs = {}
print("Cleaning Data...")
for file in windaq_files:
	# Dealing with typos and the like
	name = file.split("//")[-1].split(".")[0].replace(" ", "") # Ignore whitespace...
	name = name.lower()
	if name[-2] == "0":
		name = name[:-2] + name[-1:]
	name = name.replace("2011", "2021")
	name = name.replace("test", "")
	wfile = wdq.windaq(file)
	try:
		data_row = data_inventory[data_inventory["Name of data file"] == name].iloc[0]
	except:
		print(f"Issue importing: {name}")
		continue

	label_series = labels[data_row["Notepad file name"]]

	data_length = min(len(label_series), len(wfile.data(1)))

	data = {
		"resistance" : 	[data_row["Ri level (10^x Ω)"]] * data_length,
		"voltage" : 	[data_row["Voltage (mV)"]] * data_length,
		"current" : 	[data_row["Current"]] * data_length,
		"time":		wfile.time(),
		"pre_rect":	wfile.data(1),
		"post_rect":	wfile.data(2),
		"labels":	label_series
	}
	
	df = pd.DataFrame(data)
	# df = df[df["labels"].apply(lambda x : len(x) > 0)]
	
	dfs[name] = df

# Save everything to files
print("Saving Data")
for name, df in dfs.items():
	df.to_csv(f"tarsalis_data_clean//{name}.csv")
