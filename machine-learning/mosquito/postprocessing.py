# %%
import numpy as np
import pandas as pd
from data_augmentation import Probe
from scipy.special import softmax
from collections import defaultdict
from scipy.signal import savgol_filter
import torch
import math
from scipy.stats import norm

EPS = 1e-9

'''
u_t(j,d) is defined as:
prod_{Tau = t-d+1}^t b_j(o_Tau)
i.e the cumprob of probability of each observation given the state is J
'''

# evaluate current u_t(j, d). extends to t - d < 0 and t > n_samples - 1.
# note: for t > n_samples - 1, "log_obsprob[t, j]" is not stored and its value is 0.
def _curr_u(n_samples, u, t, j, d):
    if t - d >= 0 and t < n_samples:
        return u[t, j, d]
    elif t - d < 0:
        return u[t, j, t]
    # elif d >= t - (n_samples - 1):
    #     return u[n_samples - 1, j, (n_samples - 1) + d - t]
    # else:
    #     return 0.0

def _core_u_only(log_obsprob, n_states, n_durations):
        n_samples = log_obsprob.shape[0]
        u = np.empty((n_samples, n_states, n_durations))
        for t in range(n_samples):
            for j in range(n_states):
                for d in range(n_durations):
                    if t < 1 or d < 1:
                        u[t, j, d] = log_obsprob[t, j]
                    else:
                        u[t, j, d] = u[t - 1, j, d - 1] + log_obsprob[t, j]
        return u


            

def HSMM_viterbi(probabilities, starting_probs, transition_matrix, durations):
    log_duration = np.log(durations+EPS)
    log_startprob = np.log(starting_probs+EPS)
    log_transmat = np.log(transition_matrix+EPS)
    log_probs = np.log(probabilities+EPS)
    print(durations.shape)
    n_durations = durations.shape[1]

    u = _core_u_only(log_probs, n_states, n_durations)

    n_states, t_iter = probabilities.shape
    delta = np.empty((t_iter, n_states))
    psi = np.empty((t_iter, n_states, 2), dtype=np.int32)
    buffer0 = np.empty(n_states)
    buffer1 = np.empty(n_durations)
    buffer1_state = np.empty(n_durations, dtype=np.int32)
    state_sequence = np.empty(t_iter, dtype=np.int32)

    # forward pass
    for t in range(t_iter):
        for j in range(n_states):
            for d in range(n_durations):
                if t - d == 0:   # beginning
                    buffer1[d] = log_startprob[j] + log_duration[j, d] + _curr_u(t_iter, u, t, j, d)
                    buffer1_state[d] = -1   # place-holder only
                elif t - d > 0:   # ongoing
                    for i in range(n_states):
                        if i != j:
                            buffer0[i] = delta[t - d - 1, i] + log_transmat[i, j] + _curr_u(t_iter, u, t, j, d)
                        else:
                            buffer0[i] = -math.inf
                    buffer1[d] = buffer0.max() + log_duration[j, d]
                    buffer1_state[d] = buffer0.argmax()
                else:   # this should not be chosen
                    buffer1[d] = -math.inf
            delta[t, j] = buffer1.max()
            j_dur = buffer1.argmax()
            psi[t, j, 0] = j_dur   # psi[:, j, 0] is the duration of j
            psi[t, j, 1] = buffer1_state[j_dur]   # psi[:, j, 1] is the state leading to j
        # getting the last state and maximum log-likelihood

        state_logl = delta[t_iter - 1].max()
        back_state = delta[t_iter - 1].argmax()
        back_dur = psi[t_iter - 1, back_state, 0]
        # backward pass
        back_t = t_iter - 1
        for t in range(t_iter - 1, -1, -1):
            if back_dur < 0:
                back_state = psi[back_t, back_state, 1]
                back_dur = psi[t, back_state, 0]
                back_t = t
            state_sequence[t] = back_state
            back_dur -= 1
    return state_sequence, state_logl

def barcode_deleter(self, probe):
    probe = np.array(probe)
    sample_rate = 100 #Hz
    # These should be made configurable in GUI if we decide to
    # use this method.
    min_lengths = { # sec
        "J" : 5,
        "K" : 0.5,
        "L" : 30,
        "M" : 30,
        "N" : 5,
        "Z" : 0.1
    }
    # idea: remove states that are not long enough
    #       and replace them by their neighbors
    #       that are long enough
    state_times = [(state, len(list(vals))) for state, vals in groupby(probe)]
    clean_probe = []
    position = 0
    last_state_end = 0
    last_state = None
    for i in range(len(state_times)):
        state, time = state_times[i]
        # If this state was long enough
        if min_lengths[state] * sample_rate <= time:
            # We need to figure out how to fill in space between
            if last_state == state or not last_state:
                # Just make it all that state
                clean_probe += [state] * (position - last_state_end)
            else:
                # Replace region between the long enough states
                # by extending those states in proportion to the
                # amount of those states in the between region
                between_states = probe[last_state_end:position]
                # We add 1 below to prevent divide by 0
                last_state_count = (between_states == last_state).sum() + 1
                next_state_count = (between_states == state).sum() + 1
                last_state_proportion = last_state_count / \
                                        (last_state_count + next_state_count)
                last_state_length = int(np.floor(last_state_proportion * len(between_states)))
                clean_probe += [last_state] * last_state_length
                clean_probe += [state] * (len(between_states) - last_state_length)

            # Add on the current state and update the last state
            clean_probe += [state] * time
            position += time
            last_state = state
            last_state_end = position
                
        # If this state was not long enough
        else:
            # Increment the position and continue
            position += time

    # Extend to end if necessary
    if len(clean_probe) < len(probe):
        if len(clean_probe) == 0:
            # in case the labeling was a mess, just give up and write NP
            clean_probe = ['NP']
        clean_probe += [clean_probe[-1]] * (len(probe) - len(clean_probe))
    return clean_probe



def find_path_viterbi(probabilities, starting_probs, transition_matrix, lambdas, alpha):
    # setup
    N, T = probabilities.shape
    vitberi = np.full((N, T), -np.inf)
    backpointer = np.zeros((N, T), dtype=int)

    # adjust for log and to add dwell time
    log_prob = np.log(probabilities + EPS)
    log_starting_probs = np.log(starting_probs + EPS)

    stay_probs = np.exp(-lambdas)
    mod_trans_mat = (1 - stay_probs[:, None]) * transition_matrix
    np.fill_diagonal(mod_trans_mat, stay_probs)
    # p(i -> i) = e^(-lambda_i)
    # p(i -> j) = A[i,j] * (1-e^(-lambda_i))
    log_transition_matrix = np.log(mod_trans_mat + EPS)
    # initialize
    for s in range(N):
        vitberi[s, 0] = log_starting_probs[s] + log_prob[s, 0]
        backpointer[s, 0] = 0


    # recursion
    for t in range(1, T):
        for s in range(N):
            consider = [vitberi[s_prime, t-1] + log_transition_matrix[s_prime, s] + (alpha)*log_prob[s, t] for s_prime in range(N)]
            best_s_prime = np.argmax(consider)
            vitberi[s, t] = consider[best_s_prime]
            backpointer[s, t] = best_s_prime

    # termination
    best_path_pointer = np.argmax(vitberi[:, -1])
    best_path = [best_path_pointer]
    for t in reversed(range(T-1)):
        best_path_pointer = backpointer[best_path_pointer, t]
        best_path.append(best_path_pointer)

    return best_path[::-1]

possible_paths = {
('K', 'L', 'W'),
('K', 'L', 'M', 'L', 'W'),
('K', 'L', 'M', 'N', 'W'),
('K', 'L', 'M', 'L', 'M', 'W'),
('J', 'K', 'L', 'M', 'W'),
('J', 'K', 'L', 'M', 'L', 'W'),
('J', 'K', 'L', 'M', 'L', 'M', 'W'),
('J', 'K', 'L', 'M', 'L', 'M', 'N', 'W'),
('K', 'L', 'M', 'W'),
('K', 'L', 'M', 'L', 'M', 'N', 'W'),
('J', 'K', 'L', 'W'),
('J', 'K', 'L', 'M', 'N', 'W'),
}

class LogProbWindowSum:
    def __init__(self, log_probs: np.ndarray):
        """
        log_probs: np.ndarray of shape (K, T)
        """
        self.log_probs = log_probs
        # Precompute cumulative sum along time axis for each K
        # We pad with a leading zero for easier indexing
        self.cumsum = np.cumsum(log_probs, axis=1)
        self.cumsum = np.pad(self.cumsum, ((0, 0), (1, 0)), mode='constant', constant_values=0)

    def query(self, k: int, start_idx: int, end_idx: int) -> float:
        """
        Returns the sum of log_probs[k, start_idx:end_idx], i.e., log_probs[k, start_idx] + ... + log_probs[k, end_idx-1]
        Assumes: 0 <= k < K and 0 <= start_idx <= end_idx <= T
        """
        return self.cumsum[k, end_idx] - self.cumsum[k, start_idx]

def best_dwell_path(path, log_duration, log_startprob, log_transmat, log_probs, max_min):
    K, T = log_probs.shape
    D = log_duration.shape[1]
    S = len(path)


    window_sum = LogProbWindowSum(log_probs)
    decoding_mat = {n:i for i, n in enumerate(log_transmat.index)}

    dp = np.full((S+1, T+1), -np.inf)
    backpointer = np.full((S+1, T+1), np.nan)
    dp[0, 0] = 0
    for s in range(1,S+1):
        state = path[s-1]
        state_idx = decoding_mat[state]
        min_duration, max_duration = max_min[state_idx]
        min_duration, max_duration = int(min_duration), int(max_duration)
        print(s, state_idx, max_duration, S)
        for t in range(1,T+1):
            for d in range(min_duration+1, min(t+1, max_duration)):
                candidate_score = dp[s-1, t-d] + window_sum.query(state_idx, t-d, t) + log_duration[state_idx, d]
                if candidate_score > dp[s, t]:
                    dp[s, t] = candidate_score
                    backpointer[s, t] = t-d
    best_score = dp[S][T]

    segmentation = []
    t = T
    for s in range(S, 0, -1):
        start = backpointer[s,t]
        segmentation.append((path[s - 1], start, t))
        t = int(start)

    return best_score, segmentation[::-1]



def path_decode(probabilities, starting_probs, transition_matrix, durations, max_min):
    log_duration = np.log(durations+EPS)
    log_startprob = np.log(starting_probs+EPS)
    log_transmat = np.log(transition_matrix+EPS)
    log_probs = np.log(probabilities+EPS)

    best_path = None
    best_recording = None
    best_score = -math.inf
    for path in possible_paths:
        score, recording = best_dwell_path(path, log_duration, log_startprob, log_transmat, log_probs, max_min)
        print(path, score, recording)
        if score > best_score:
            best_score = score
            best_recording = recording
            best_path = path
    
    return best_score, best_path, best_recording


def prep_viterbi(train_data, build_durations=False, N=None):
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
    
    durations_dict = dict()
    means = dict()
    stds = dict()
    if build_durations:
        for key,durations in lens.items():
            mean_duration = np.mean(durations)
            std_duration = np.std(durations, ddof=1)  # sample standard deviation
            probabilities = np.zeros(N) # N is max duration
            for i in range(N):
                cdf_upper = norm.cdf(i + 1, loc=mean_duration, scale=std_duration)
                cdf_lower = norm.cdf(i, loc=mean_duration, scale=std_duration)
                probabilities[i] = cdf_upper - cdf_lower
            probabilities /= probabilities.sum()
            durations_dict[key] = probabilities
            means[key] = mean_duration
            stds[key] = std_duration
        durations_array = np.array([durations_dict[key] for key in transition_matrix_without_NP.columns])
        max_mins = [(max(0, means[key]-4*stds[key]), min(means[key]+4*stds[key], N)) for key in transition_matrix_without_NP.columns]
        mean_sd = [(means[key], stds[key]) for key in transition_matrix_without_NP.columns]
    if not build_durations:
        return transition_matrix_without_NP_normed, starting_probs, lambda_list, None
    else:
        return transition_matrix_without_NP_normed, starting_probs, durations_array, max_mins, mean_sd


class PostProcessor:
    def __init__(self, train_data, inv_label_map):
        self.transition_matrix_without_NP_normed, self.starting_probs, self.durations, self.mm = prep_viterbi(train_data=train_data)
        # note that durations is either a lambda list or a durations array
        self.inv_label_map = inv_label_map

    def postprocess_viterbi(self, logit, alpha=0.8):
        probs = softmax(logit, axis=0)
        best_path = find_path_viterbi(probs, self.starting_probs, self.transition_matrix_without_NP_normed.values, self.durations, alpha=alpha)
        best_path_labeled = [self.inv_label_map[s] for s in best_path]
        return best_path_labeled
    
    def HSMM(self, logit):
        probs = softmax(logit, axis=0)
        best_path = HSMM_viterbi(probs, self.starting_probs, self.transition_matrix_without_NP_normed.values, self.durations)
        best_path_labeled = [self.inv_label_map[s] for s in best_path]
        return best_path_labeled
    
    def postprocess_smooth(self, logits, window_size=301, poly_order=3):
        smooth_logit = torch.tensor(savgol_filter(logits.numpy(), window_size, poly_order, axis=1))
        preds = smooth_logit.argmax(dim=0).view(-1).tolist()
        pred_labels = [self.inv_label_map[p] for p in preds]
        return pred_labels
    

# if __name__ == "__main__":
#     transition_matrix_without_NP_normed, starting_probs, durations_array, mm, ms = prep_viterbi(train_data, build_durations=True, N=probs.shape[1])
#     path_decode(probs, starting_probs, transition_matrix_without_NP_normed, durations_array, mm)