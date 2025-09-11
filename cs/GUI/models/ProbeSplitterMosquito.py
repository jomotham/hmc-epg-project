import numpy as np

class SimpleProbeSplitter:
    def simple_probe_finder(recording, window = 500, threshold = 0.1,
                        min_probe_length = 1500, np_pad = 500):
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
