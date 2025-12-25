import numpy as np
import matplotlib.pyplot as plt
"""
Gramian Angular Fields is a technique that allows encoding of a signal into a 2D image which then can be used by a CNN for classification. 
This can also be applied to frequency representations such as spectrograms or power spectral densities.
"""


def min_max_normalize(signal:np.array):
    """
    scale to [-1, 1]
    """
    min_value = np.min(signal)
    max_value = np.max(signal)

    return (2 * (signal-min_value)/(max_value-min_value)) - 1

def create_gaf(signal: np.array, summation: bool = True):
    """Convert a signal into a Gramian Angular Field, a two dimenions matrix representation of the signal.

    Parameters
    ----------
    signal : np.array
        1D array signal values. Can be time series or frequency series.
    summation : bool, optional
        Used to dermine if the GAF is based on summation (True) or difference (False) of angles. 

    Returns:
    ----------
    gaf : 2darray
        2d np.array of corresponding gramian angular field

    """
    normalized_signal = min_max_normalize(signal=signal)
    polar_signal = np.arccos(normalized_signal)
    print(polar_signal, polar_signal.shape)

    if summation == False:
        gaf = np.sin(polar_signal[:, None] - polar_signal[None, :])
        return gaf
    else:
        gaf = np.cos(polar_signal[:, None] + polar_signal[None, :])
        return gaf
