# %%
import numpy as np
import pandas as pd
from data_augmentation import Probe
from scipy.special import softmax
from collections import defaultdict
from scipy.signal import savgol_filter
import torch
import math
import matplotlib.pyplot as plt
from model_eval import *
from transition_matrix import transition_matrix_dict
# n_samples : total points, T
# n_states : number of hidden states, N
# n_durations : max length in a duration

def prep_lens():
    transition_matrix_df = pd.DataFrame(transition_matrix_dict)
    data_path = r"c:\Users\milok\clasp_transitions"
    data = DataImport(data_path)
    train_data, test_data, test_names = data.get_train_test()
    probes = [Probe().init_df(p) for p in train_data+test_data]
    lens = defaultdict(list)
    for probe in probes:
        for state_df, state_name in zip(probe.state_dfs, probe.state_names):
            lens[state_name].append(len(state_df))
    return lens

from scipy.stats import norm
def discrete_kde_distribution(lengths, bandwidth=None):
    lengths = np.asarray(lengths)
    
    x_min = lengths.min()
    x_max = lengths.max()
    x_values = np.arange(x_min, x_max + 1, 1)  # all integer points in [x_min, x_max]
    
    pdf_unnormalized = np.zeros_like(x_values, dtype=float)
    
    # Sum contributions from each data point using a Gaussian kernel
    for i, x in enumerate(x_values):
        # norm.pdf(x, loc=mu, scale=bandwidth) for each observed length
        if bandwidth is None:
            bandwidth = (x_max - x_min) / 10
            print(bandwidth)
        pdf_unnormalized[i] = np.sum(norm.pdf(x, loc=lengths, scale=bandwidth))
    
    # Normalize so that the sum of probabilities is 1
    pmf = pdf_unnormalized / np.sum(pdf_unnormalized)
    
    return x_values, pmf, bandwidth

def plot_pmf(lengths, bandwidth=None, title="Discrete KDE Distribution"):
    x_values, pmf, bandwidth = discrete_kde_distribution(lengths, bandwidth)
    plt.figure(figsize=(8, 4))
    plt.bar(x_values, pmf, width=0.8, align='center', alpha=0.7)
    plt.xlabel("Duration")
    plt.ylabel("Probability")
    plt.title(title)
    plt.show()
    plt.hist(lengths, bins=50)
    plt.show()
    return bandwidth

def plot_all_smoothed_data():
    bands = {"J": None,
            "K": None,
            "L": None,
            "M": None,
            "N": None,
            "W": None, }
    new_bands = dict()
    lens = prep_lens()
    for key,val in lens.items():
        new_bands[key] = plot_pmf(val, bandwidth=bands[key], title=key)
    return new_bands

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

def compute_u(n_samples, n_states, n_durations, log_obsprob):
    u = np.zeros((n_samples, n_states, n_durations))
    for t in range(n_samples):
        for j in range(n_states):
            for d in range(n_durations):
                if d == 0:
                    u[t, j, d] = log_obsprob[t, j]
                elif t - d + 1 >= 0:
                    u[t, j, d] = np.sum(log_obsprob[t - d + 1:t + 1, j])
                else:
                    u[t, j, d] = np.sum(log_obsprob[:t + 1, j])
    return u

# log_duration[j,d]
# state j, duration d
def log_duration(j,d):
    return log_durations[j](d)

def HSMM_viterbi(probabilities, starting_probs, transition_matrix, n_durations):
    n_states, t_iter = probabilities.shape
    delta = np.empty((t_iter, n_states))
    psi = np.empty((t_iter, n_states, 2), dtype=np.int32)
    buffer0 = np.empty(n_states)
    buffer1 = np.empty(n_durations)
    buffer1_state = np.empty(n_durations, dtype=np.int32)
    state_sequence = np.empty(t_iter, dtype=np.int32)

    log_obsprob = np.log(probabilities + EPS)
    log_startprob = np.log(starting_probs + EPS)

    mod_trans_mat = transition_matrix.copy()
    np.fill_diagonal(mod_trans_mat, 0)
    log_transmat = np.log(mod_trans_mat + EPS)

    u = compute_u(t_iter, n_states, n_durations, log_obsprob)

    # forward pass
    for t in range(t_iter):
        for j in range(n_states):
            for d in range(n_durations):
                if t - d == 0:   # beginning
                    buffer1[d] = log_startprob[j] + log_duration(j, d) + _curr_u(t_iter, u, t, j, d)
                    buffer1_state[d] = -1   # place-holder only
                elif t - d > 0:   # ongoing
                    for i in range(n_states):
                        if i != j:
                            buffer0[i] = delta[t - d - 1, i] + log_transmat[i, j] + _curr_u(t_iter, u, t, j, d)
                        else:
                            buffer0[i] = -math.inf
                    buffer1[d] = buffer0.max() + log_duration(j, d)
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

if __name__ == "__main__":
    plot_all_smoothed_data()