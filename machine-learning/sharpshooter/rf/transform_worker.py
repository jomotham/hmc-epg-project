import numpy as np
import pandas as pd



def transform_single_probe(probe, chunk_size, sample_rate, num_freqs, training):
    """
    Takes a single probe and extracts its top N freqs, mean, and std.

    Defined outside of RF Model class so it can be parallelized.
    """
    freq_bins = np.fft.fftfreq(chunk_size, 1 / sample_rate)[1:chunk_size // 2]

    # Normalize column
    if "pre_rect" in probe.columns:
        probe = probe.rename(columns={"pre_rect": "voltage"})

    num_chunks = len(probe) // chunk_size
    if num_chunks == 0:
        return None

    voltage = probe["voltage"].values[:num_chunks * chunk_size]
    voltage_chunks = voltage.reshape(num_chunks, chunk_size)
    fft_mag = np.abs(np.fft.fft(voltage_chunks))[:, 1:chunk_size // 2]

    result = {f"F{i}": np.zeros(num_chunks) for i in range(num_freqs)}
    result["mean"] = np.mean(voltage_chunks, axis=1)
    result["std"] = np.std(voltage_chunks, axis=1)

    # === Vectorized FFT peak frequency extraction ===
    top_n_idx = np.argpartition(-fft_mag, num_freqs, axis=1)[:, :num_freqs]
    top_n_vals = np.take_along_axis(fft_mag, top_n_idx, axis=1)
    sort_order = np.argsort(-top_n_vals, axis=1)
    sorted_top_idx = np.take_along_axis(top_n_idx, sort_order, axis=1)
    top_freqs_sorted = freq_bins[sorted_top_idx]

    for j in range(num_freqs):
        result[f"F{j}"] = top_freqs_sorted[:, j]

    if training:
        label_array = probe["labels"].values[:num_chunks * chunk_size]
        label_chunks = label_array.reshape(num_chunks, chunk_size)
        from collections import Counter
        result["label"] = [Counter(chunk).most_common(1)[0][0] for chunk in label_chunks]

    return pd.DataFrame(result)
