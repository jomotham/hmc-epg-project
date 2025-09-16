import numpy as np
import scipy.ndimage
import pandas as pd
import optuna
from sklearn.metrics import accuracy_score, classification_report, f1_score
import os # Import os module for path manipulation
import glob
import re
import random

# single file training
# Best Parameters:
#     window: 961
#     threshold: 0.09406124969163045
#     min_probe_length: 867
#     np_pad: 390

# --- Evaluation with Best Parameters ---
# Accuracy with best parameters: 0.9793
#               precision    recall  f1-score   support

#           NP       0.98      0.99      0.98   2379522
#            P       0.97      0.97      0.97   1220479

#     accuracy                           0.98   3600001
#    macro avg       0.98      0.98      0.98   3600001
# weighted avg       0.98      0.98      0.98   3600001

# 6 file training
# Best trial:
#   Value (Average Accuracy): 0.9660
#   Best Parameters:
#     window: 902
#     threshold: 0.16037791395522136
#     min_probe_length: 557
#     np_pad: 412

# --- Evaluation with Best Parameters on the FIRST file (for detailed report) ---
# Accuracy on first file with best parameters: 0.9757
#               precision    recall  f1-score   support

#           NP       0.97      0.99      0.98   2379522
#            P       0.98      0.95      0.96   1220479

#     accuracy                           0.98   3600001
#    macro avg       0.98      0.97      0.97   3600001
# weighted avg       0.98      0.98      0.98   3600001



# 56 file training
# Optimization finished.
# Number of finished trials: 53
# Best trial:
#   Value (Average Accuracy): 0.8976
#   Best Parameters:
#     window: 1095
#     threshold: 0.1604695760150232
#     min_probe_length: 681
#     np_pad: 416

# --- Evaluation with Best Parameters on the FIRST file (for detailed report) ---
# Accuracy on first file with best parameters: 0.9383
#               precision    recall  f1-score   support

#           NP       0.94      1.00      0.97   3157722
#            P       0.98      0.51      0.67    442367

#     accuracy                           0.94   3600089
#    macro avg       0.96      0.75      0.82   3600089
# weighted avg       0.94      0.94      0.93   3600089



# new tuning with g filter
# Number of finished trials: 20
# Best trial:
#   Value (Average F1-score for P): 0.9322
#   Best Parameters:
#     window: 887
#     threshold: 0.28767857660247903      
#     min_probe_length: 839
#     g_window_seconds: 0.39643541684062933
#     g_std_threshold: 0.00864373149647393
#     g_ptp_threshold: 0.018131705703547926

# --- Final Evaluation with Best Parameters on the Randomly Selected Test File ---
# Evaluating on test file: sharpshooter_d16_labeled.csv
# Accuracy on test file: 0.8576
#               precision    recall  f1-score   support

#           NP       0.54      0.97      0.69    591461
#            P       0.99      0.84      0.91   3008540

#     accuracy                           0.86   3600001
#    macro avg       0.76      0.90      0.80   3600001
# weighted avg       0.92      0.86      0.87   3600001


# new tuning with g filter increased window range, dilation
# Optimization finished.
# Number of finished trials: 3
# Best trial:
#   Value (Average F1-score for P): 0.9151
#   Best Parameters:
#     window: 887
#     threshold: 0.28767857660247903
#     min_probe_length: 839
#     np_pad: 420
#     g_window_seconds: 20.460652415485278
#     g_std_threshold: 0.0166995890252152
#     g_ptp_threshold: 0.14442471597135292
#     g_dilation_seconds: 17.323522915498703

# --- Final Evaluation with Best Parameters on the Randomly Selected Test File ---
# Evaluating on test file: sharpshooter_d16_labeled.csv
# Accuracy on test file: 0.9725
#               precision    recall  f1-score   support

#           NP       0.89      0.94      0.92    591461
#            P       0.99      0.98      0.98   3008540

#     accuracy                           0.97   3600001
#    macro avg       0.94      0.96      0.95   3600001
# weighted avg       0.97      0.97      0.97   3600001

class ProbeSplitter:
    def simple_probe_finder(recording, window = 1095, threshold = 0.1604695760150232,
                            min_probe_length = 681, np_pad = 416):
        """
        Input: recording: A pre-rectified mosquito recording as a 1-D nupmy 
                    array. Pre-rectified recordings are necessary as baseline is 
                    not 0 in post-rectified recordings.
                window: Before NP regions can be identified, a rolling
                    average filter is applied to remove noise in the NP regions.
                    window is the size of this filter in samples.
                threshold: The maximum value of an NP sample.
                min_probe_length: The minimum acceptable length of a probe in
                    samples.
                np_pad: the number of NP samples before and after each probe to
                    include. Note that high values might result in overlapping with
                    the next probe.
        Output: A list of (start sample, end sample) tuples for each probe. By 
                default contains about 5 seconds of NPs at the beginning and end            
                of each probe. We say "about" because this splitting is done
                in an unsupervised manner, although it is largely pretty good.
        """
        
        smoothed = np.convolve(recording, np.ones(window), "same")/window
        is_NP = smoothed < threshold # NP is where the signal is close to 0
        
        # Find starts and ends, combine into tuple
        find_sequence = lambda l, seq : [i for i in range(len(l)) if l[i:i+len(seq)] == seq] 
        is_NP_list = list(is_NP)
        probe_starts = find_sequence(is_NP_list, [True, False])
        probe_ends = find_sequence(is_NP_list, [False, True])
        probes = zip(probe_starts, probe_ends)
        
        # Remove probes that are too short and pad
        probes = [(max(0, start - np_pad), end + np_pad) for start, end in probes if end - start > min_probe_length]
        
        return probes
    
    
    

    def refine_predictions_for_g(initial_predicted_is_probe, raw_recording, sample_rate,
                                g_window_seconds, g_std_threshold, g_ptp_threshold,
                                g_mean_threshold,
                                g_dilation_seconds, min_g_length_seconds,
                                initial_probes_tuples):
        """
        Refines initial boolean predictions by re-classifying 'NP' segments as 'P'
        if they exhibit 'G'-like characteristics (high rolling std and peak-to-peak),
        applies dilation to bridge gaps within detected G regions, and then filters
        these detected G regions by a minimum length.
        """
        refined_pred_is_probe = np.copy(initial_predicted_is_probe)
        
        g_window_samples = int(g_window_seconds * sample_rate)
        g_window_samples = max(1, g_window_samples)

        g_dilation_samples = int(g_dilation_seconds * sample_rate)
        g_dilation_samples = max(0, g_dilation_samples) # Dilation can be 0 or more

        min_g_length_samples = int(min_g_length_seconds * sample_rate)
        min_g_length_samples = max(1, min_g_length_samples) # Ensure minimum length is at least 1 sample

        recording_length = len(raw_recording)

        np_segments_ranges = []
        current_np_start = 0

        for p_start, p_end in initial_probes_tuples:
            if p_start > current_np_start:
                np_segments_ranges.append((current_np_start, p_start))
            current_np_start = p_end

        if current_np_start < recording_length:
            np_segments_ranges.append((current_np_start, recording_length))

        for np_block_start, np_block_end in np_segments_ranges:
            np_segment = raw_recording[np_block_start:np_block_end]

            # Only apply G-signal detection if segment is long enough for the rolling window
            if len(np_segment) >= g_window_samples:
                segment_series = pd.Series(np_segment)

                rolling_std = segment_series.rolling(window=g_window_samples, center=True, min_periods=1).std().fillna(0).values
                rolling_max_series = segment_series.rolling(window=g_window_samples, center=True, min_periods=1).max()
                rolling_min_series = segment_series.rolling(window=g_window_samples, center=True, min_periods=1).min()
                rolling_ptp = (rolling_max_series - rolling_min_series).fillna(0).values
                rolling_mean = segment_series.rolling(window=g_window_samples, center=True, min_periods=1).mean().fillna(0).values

                # Initial detection of fluctuating 'G' parts within this NP segment
                is_g_in_segment_local = (rolling_std > g_std_threshold) & (rolling_ptp > g_ptp_threshold) & (np.abs(rolling_mean) > g_mean_threshold)
                
                # Apply dilation to bridge small gaps within these detected 'G' regions
                if g_dilation_samples > 0:
                    dilated_is_g_in_segment = scipy.ndimage.binary_dilation(
                        is_g_in_segment_local,
                        structure=np.ones(g_dilation_samples * 2 + 1, dtype=bool),
                        border_value=False
                    )
                else:
                    dilated_is_g_in_segment = is_g_in_segment_local

                # --- Filter by minimum G length within the NP segment ---
                # Find contiguous True regions in dilated_is_g_in_segment
                # Use np.diff to find start/end of True blocks
                # Pad with False at ends to catch blocks starting/ending at boundaries
                g_segment_diff = np.diff(np.concatenate(([False], dilated_is_g_in_segment, [False])))
                g_segment_starts_local = np.where(g_segment_diff == 1)[0]
                g_segment_ends_local = np.where(g_segment_diff == -1)[0]

                final_g_in_segment_local = np.zeros_like(is_g_in_segment_local, dtype=bool)
                for start_loc, end_loc in zip(g_segment_starts_local, g_segment_ends_local):
                    # Check if the length of the detected G segment meets the minimum requirement
                    if (end_loc - start_loc) >= min_g_length_samples:
                        final_g_in_segment_local[start_loc:end_loc] = True

                # Re-label the *filtered* and dilated 'G' parts as True (P) in the refined array
                refined_pred_is_probe[np_block_start:np_block_end][final_g_in_segment_local] = True
            
        return refined_pred_is_probe



base_directory = r"C:\Users\Clinic\Desktop\USDA-Auburn-Su25\Data\Sharpshooter Data - HPR 2017"
all_sharpshooter_files = glob.glob(os.path.join(base_directory, "sharpshooter_*_labeled.csv"))

NUM_TRAINING_FILES = 50

random.seed(42)

if len(all_sharpshooter_files) > NUM_TRAINING_FILES:
    sharpshooter_files = random.sample(all_sharpshooter_files, NUM_TRAINING_FILES)
else:
    sharpshooter_files = all_sharpshooter_files
    print(f"Warning: Not enough files found ({len(all_sharpshooter_files)}) to select {NUM_TRAINING_FILES} for training. Using all available files.")

training_file_set = set(sharpshooter_files)
test_file_candidates = [f for f in all_sharpshooter_files if f not in training_file_set]

if not test_file_candidates:
    print("Error: No files available for testing that were not used for training.")
    if sharpshooter_files:
        test_file_path = random.choice(sharpshooter_files)
        print(f"WARNING: Using a training file '{os.path.basename(test_file_path)} as test file due to lack of distinct test candidates.")
    else:
        test_file_path = None
else:
    test_file_path = random.choice(test_file_candidates)

print(f"Found {len(all_sharpshooter_files)} total sharpshooter files.")
print(f"Randomly selected on {len(sharpshooter_files)} files ({[os.path.basename(sharpshooter_file) for sharpshooter_file in sharpshooter_files]}) for optimization.")

if test_file_path:
    print(f"Randomly selected test file: {os.path.basename(test_file_path)}")
else:
    print("No test file could be selected.")

# --- Optuna Objective Function ---
def objective(trial, file_paths):
    """
    Objective function for Optuna to optimize the simple_probe_finder parameters
    and the G-signal refinement parameters.
    """
    # 1. Suggest parameters for simple_probe_finder (main stage)
    window = trial.suggest_int("window", 750, 1100)
    threshold = trial.suggest_float("threshold", 0.01, 0.2)
    min_probe_length = trial.suggest_int("min_probe_length", 700, 900)
    np_pad = trial.suggest_int("np_pad", 400, 450)

    # 2. Suggest parameters for G-signal refinement (secondary stage)
    # These ranges are suggestions; you might need to adjust them based on initial runs
    sample_rate = 100 # Assuming a fixed sample rate for the data
    g_window_seconds = trial.suggest_float('g_window_seconds', 5.0, 30.0) # Window for G-signal analysis (in seconds)
    g_std_threshold = trial.suggest_float('g_std_threshold', 0.02, 0.15) # Min std dev for G
    g_ptp_threshold = trial.suggest_float('g_ptp_threshold', 0.1, 3.0) # Min peak-to-peak for G
    g_mean_threshold = trial.suggest_float('g_mean_threshold', 0.1, 6)
    g_dilation_seconds = trial.suggest_float('g_dilation_seconds', 0.0, 40.0)
    min_g_length_seconds = trial.suggest_float('min_g_length_seconds', 0.5, 10.0)

    # print(f"Trial {trial.number} Parameters:")
    # for key, value in trial.params.items():
    #     print(f"    {key}: {value}")

    total_true_labels = []
    total_predicted_labels = []

    for file_path in file_paths:
        try:
            data = pd.read_csv(file_path)
        except FileNotFoundError:
            print(f"Warning: File not found at {file_path}. Skipping this file.")
            continue
        except Exception as e:
            print(f"Error loading {file_path}: {e}. Skipping this file.")
            continue

        pre_rect = data["pre_rect"].values
        ground_truth_labels = data["labels"].astype(str).str.lower()
        true_is_probe = ~ground_truth_labels.isin(["n", "z"]) # Boolean array (True for P, False for NP)

        # Stage 1: Run simple_probe_finder
        initial_probes_tuples = ProbeSplitter.simple_probe_finder(
            pre_rect,
            window=window,
            threshold=threshold,
            min_probe_length=min_probe_length,
            np_pad=np_pad
        )

        # Convert initial probe tuples to a boolean array
        initial_predicted_is_probe = np.zeros_like(pre_rect, dtype=bool)
        for start, end in initial_probes_tuples:
            start = max(0, start)
            end = min(len(initial_predicted_is_probe), end)
            initial_predicted_is_probe[start:end] = True

        # Stage 2: Refine predictions using G-signal detector
        final_predicted_is_probe = ProbeSplitter.refine_predictions_for_g(
            initial_predicted_is_probe,
            pre_rect,
            sample_rate,
            g_window_seconds,
            g_std_threshold,
            g_ptp_threshold,
            g_mean_threshold,
            g_dilation_seconds,
            min_g_length_seconds,
            initial_probes_tuples # Pass the initial probes list
        )
        
        # Ensure lengths match before appending for overall evaluation
        min_len = min(len(true_is_probe), len(final_predicted_is_probe))
        total_true_labels.extend(true_is_probe[:min_len])
        total_predicted_labels.extend(final_predicted_is_probe[:min_len])

    # If no files were processed successfully, return a very low value
    if not total_true_labels:
        return 0.0

    # Calculate F1-score for the 'P' class, as it's more robust for imbalance
    # Convert boolean arrays to 'P'/'NP' strings for f1_score
    true_labels_str = np.where(np.array(total_true_labels), 'P', 'NP')
    predicted_labels_str = np.where(np.array(total_predicted_labels), 'P', 'NP')
    
    f1 = f1_score(true_labels_str, predicted_labels_str, average='macro')
    
    return f1 # Optuna will maximize this F1-score

# --- Run Optuna Optimization ---
if __name__ == "__main__":
    if not sharpshooter_files:
        print("Error: No sharpshooter files found for optimization. Please check 'base_directory' and 'glob' pattern.")
        print("Exiting optimization.")
        exit()

    if test_file_path is None:
        print("Error: No suitable test file could be selected. Exiting optimization.")
        exit()

    print("Starting Optuna optimization across randomly selected files with G-signal refinement...")
    # Create an Optuna study. We want to maximize the average F1-score for 'P'.
    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
    # Pass the loaded file_paths to the objective function
    study.optimize(lambda trial: objective(trial, sharpshooter_files), n_trials=50)

    print("\nOptimization finished.")
    print(f"Number of finished trials: {len(study.trials)}")
    print("Best trial:")
    trial = study.best_trial

    print(f"  Value (Average Macro F1-score): {trial.value:.4f}")
    print("  Best Parameters:")
    for key, value in trial.params.items():
        print(f"    {key}: {value}")

    # --- Final Evaluation with Best Parameters on the Randomly Selected Test File ---
    print("\n--- Final Evaluation with Best Parameters on the Randomly Selected Test File ---")
    
    try:
        test_df = pd.read_csv(test_file_path)
    except FileNotFoundError:
        print(f"Error: Test file not found at {test_file_path}. Cannot perform final evaluation.")
        exit()
    except Exception as e:
        print(f"Error loading test file {test_file_path}: {e}. Cannot perform final evaluation.")
        exit()

    pre_rect_test = test_df["pre_rect"].values
    ground_truth_labels_test = test_df["labels"].astype(str).str.lower()
    true_is_probe_test = ~ground_truth_labels_test.isin(["n", "z"])

    print(f"Evaluating on test file: {os.path.basename(test_file_path)}")

    # Stage 1: Run simple_probe_finder with best parameters
    best_initial_probes_tuples = ProbeSplitter.simple_probe_finder(
        pre_rect_test,
        window=trial.params["window"],
        threshold=trial.params["threshold"],
        min_probe_length=trial.params["min_probe_length"],
        np_pad=trial.params["np_pad"]
    )

    # Convert initial probe tuples to a boolean array
    best_initial_predicted_is_probe = np.zeros_like(pre_rect_test, dtype=bool)
    for start, end in best_initial_probes_tuples:
        start = max(0, start)
        end = min(len(best_initial_predicted_is_probe), end)
        best_initial_predicted_is_probe[start:end] = True

    # Stage 2: Refine predictions using G-signal detector with best parameters
    best_final_predicted_is_probe = ProbeSplitter.refine_predictions_for_g(
        best_initial_predicted_is_probe,
        pre_rect_test,
        sample_rate=100, # Use the fixed sample rate
        g_window_seconds=trial.params["g_window_seconds"],
        g_std_threshold=trial.params["g_std_threshold"],
        g_ptp_threshold=trial.params["g_ptp_threshold"],
        g_mean_threshold=trial.params["g_mean_threshold"],
        g_dilation_seconds=trial.params["g_dilation_seconds"],
        min_g_length_seconds=trial.params["min_g_length_seconds"],
        initial_probes_tuples=best_initial_probes_tuples # Pass the initial probes list
    )

    # Ensure lengths match for final evaluation
    min_len_test = min(len(true_is_probe_test), len(best_final_predicted_is_probe))
    true_labels_clipped = true_is_probe_test[:min_len_test]
    predicted_labels_clipped = best_final_predicted_is_probe[:min_len_test]

    # Convert boolean arrays to 'P'/'NP' strings for classification_report
    true_labels_str_test = np.where(true_labels_clipped, 'P', 'NP')
    predicted_labels_str_test = np.where(predicted_labels_clipped, 'P', 'NP')

    print(f"Accuracy on test file: {accuracy_score(true_labels_str_test, predicted_labels_str_test):.4f}")
    print(classification_report(true_labels_str_test, predicted_labels_str_test, target_names=["NP", "P"]))

    # Optional: Save test predictions to CSV for visual inspection
    test_df["predicted_labels_two_stage"] = predicted_labels_str_test
    test_df.to_csv("test_output_two_stage_probe_splitter.csv", index=False)
    print("Test output saved to test_output_two_stage_probe_splitter.csv")
