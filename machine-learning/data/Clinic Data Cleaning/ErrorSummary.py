import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

error_files = [
	"Expt2 errors - P-E1 removed, partly corrected.xlsx",
	"Expt3 errors - P-E1 removed.xlsx",
	"Expt4 errors - P-E1 removed.xlsx",
	"Expt5 errors - P-E1 removed.xlsx",
]

dfs = []
for file in error_files:
	dfs.append(pd.read_excel(file))

error_data = pd.concat(dfs)
error_data["Repeat"] = error_data["Transition"].apply(lambda x : x[0] in x[1:])
relevant_data = error_data[error_data["Repeat"] == False]
relevant_data["Transition"] = relevant_data["Transition"].astype("category")

"""
sns.countplot(	data = relevant_data, 
		x = "Transition",
		order = relevant_data['Transition'].value_counts().index)
plt.show()
"""

label_files = [
	"Expt2 non inoculative CTV cotton aphids on mv and ml - corrected.csv",
	"Expt3 non inoculative CTV melon aphids on MV and ML TE - partly corrected.csv",
	"Expt4 infected cotton aphids on mv and ml TE.csv",
	"Expt5 infected melon aphids on mv and ml TE.csv"
]
dfs = []
for file in label_files:
	dfs.append(pd.read_csv(file))
label_data = pd.concat(dfs)

plot_dict = {"Label Type" : ["Error", "Correct"], "Count" : [relevant_data.shape[0], label_data.shape[0] - relevant_data.shape[0]]}
plot_df = pd.DataFrame(plot_dict)

"""
plt.pie(plot_df["Count"], labels = plot_df["Label Type"], autopct='%1.1f%%')
plt.show()
"""

error_locations = (label_data.index[label_data["TBF2"].isin(error_data["TBF2"])] + 1).tolist()
error_duration = label_data["waveform_duration"][error_locations].sum()
print(error_duration)
print(label_data["waveform_duration"].sum())
print(error_duration / label_data["waveform_duration"].sum())
