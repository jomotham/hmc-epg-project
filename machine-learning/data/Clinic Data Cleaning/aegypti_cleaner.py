import windaq as wdq
import pandas as pd
import numpy as np
import os
import glob
import sys
import re
import subprocess
import shutil

data_dir = "OSU AeA data"
out_dir = "aegypti_data_clean"

# clean output directory
if os.path.isdir(out_dir):
    shutil.rmtree(out_dir)
os.makedirs(out_dir)

# spreadsheet contains waveform start and end timestamps
df = pd.read_excel(os.path.join(data_dir, "fall_2019_aa_epg_data_victoria.xlsx"))

# extract file names from spreadsheet
fns = df["File name"][df["File name"].notnull()]
start_index = fns.index
end_index   = np.append(start_index[1:], df.index[-1] + 1)

# get filenames of all the windaq files
paths = glob.glob('OSU AeA data/**/*.WDQ', recursive=True)
files       = [os.path.basename(p) for p in paths]
files_noext = [f.split('.')[0] for f in files]

for fn, start, end in zip(fns, start_index, end_index):

    clean = lambda x: x.replace(' ', '').lower()
    cleaned_fn = clean(fn)
    cleaned_files_noext = list(map(clean, files_noext))

    if fn in files_noext:
        idx = files_noext.index(fn)
        print(f"{fn} -> {paths[idx]} [exact match]")
    elif cleaned_fn in cleaned_files_noext:
        idx = cleaned_files_noext.index(cleaned_fn)
        print(f"{fn} -> {paths[idx]} [near match]")
    else:
        print(f"{fn} [NOT FOUND]")
        continue

    dfn = df[start:end]

    daq = wdq.windaq(paths[idx])
    times = daq.time()

    # get columns that label start and end times
    labelcols = list(filter(lambda c: re.match(r'. (start|end).*', c), dfn.columns))

    labels = np.empty(times.shape, dtype=object)

    for _, row in dfn.iterrows():
        # To check that within a row, the end of 1 label should be the start of the next
        ends = []
        cols = []
        for c1, c2 in zip(labelcols[::2], labelcols[1::2]):
            type1 = re.match(r'(.) start.*', c1).group(1)
            type2 = re.match(r'(.) end.*',   c2).group(1)
            assert type1 == type2
            t1 = row[c1]
            t2 = row[c2]
            if not np.isnan([t1, t2]).any():
                if len(ends) > 0:
                    if ends[-1] != t1:
                        print(f"\ttime break: {ends[-1]}, {t1} ({cols[-1]}, {c1})")
                ends.append(t2)
                cols.append(c2)
                where1 = np.where(np.abs(times - t1) < 1e-9)[0]
                where2 = np.where(np.abs(times - t2) < 1e-9)[0]
                assert where1 and where2
                labels[where1[0]:where2[0]] = type1
            else:
                assert np.isnan([t1, t2]).all()

    # Fill unlabeled (should only be at start/end and between rows) with NP
    # NOTE: will fill the 'time breaks' found above (possibly typos?)
    labels[labels == None] = 'NP'

    assert len(labels[labels != "NP"]) > 0

    data = {
        "time":      daq.time(),
        "pre_rect":  daq.data(1),
        "post_rect": daq.data(2),
        "labels":    labels
    }

    pd.DataFrame(data).to_csv(os.path.join(out_dir, f"{fn}.csv"))

print()
subprocess.run(f"zip -r {out_dir}.zip {out_dir}", shell=True)


