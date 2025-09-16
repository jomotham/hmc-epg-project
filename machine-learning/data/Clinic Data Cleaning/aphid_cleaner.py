import windaq as wdq
import pandas as pd
import matplotlib.pyplot as plt
from os import listdir

# Return a dictionary of windaq objects indexed by date
def get_windaq(experiment):
	# Get the directory of the experiment
	experiments_directory = "Harvey Mudd Sep 2024\\WinDaq files from 5 aphid experiments"
	experiments = listdir(experiments_directory)
	experiment_name = None
	for e in experiments:
		if e.startswith(experiment):
			experiment_name = e
	# Get the right file
	windaq_files = listdir(experiments_directory + "\\" + experiment_name)
	output = {}
	for file in windaq_files:
		output[file[:-4]] = wdq.windaq(experiments_directory + "\\" + 
					       experiment_name + "\\" + file)
	return output

# Edit this as necessary
label_files = [
	"Expt2 non inoculative CTV cotton aphids on mv and ml - corrected.csv",
]

dfs = {}

dataset_directory = "Harvey Mudd Sep 2024\\Datasets and errors\\"
for file in label_files:
	# Open the label file for that experiment
	label_file = pd.read_csv(dataset_directory + file)
	# Get the windaq files for that experiment
	windaqs = get_windaq(file[:5])
	# Turn each insect's experiment into its own dataframe
	insects = label_file["insect_num"].unique()
	for insect in insects:
		# For finding errors in files
		try:
			w = windaqs[insect[:-3]]
		except:
			print((file, insect))
		time = w.time()
		volts = w.data(int(insect[-1]))
		labels = []
		# Also for finding errors in files
		for index, row in label_file[label_file["insect_num"] == insect].iterrows():
			try:
				labels += [row["waveform"]] * int(row["waveform_duration"] * 100)
			except:
				print(file, row)
		
		data_length = min([len(time), len(labels)])
		data = {
			"post_rect" : volts[:data_length],
			"time" : time[:data_length],
			"label" : labels[:data_length]
		}
		df = pd.DataFrame(data)
		dfs[file[:5] + "_" + insect] = df

# Export them to CSVs
for name, df in dfs.items():
	df.to_csv(f"clean_aphids//{name}.csv")
