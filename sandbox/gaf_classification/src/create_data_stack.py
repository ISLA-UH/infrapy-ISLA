import os
import numpy as np
import pywt
from scipy import signal
from pyts.image import GramianAngularField
import matplotlib.pyplot as plt
import obspy
from obspy.clients.fdsn import Client
import json
from obspy.signal.tf_misfit import cwt
import cv2
import random
import ssqueezepy
from obspy import Stream
from scipy.ndimage import zoom
def wavelet_denoise(signal: np.ndarray, wavelet: str = 'db4', level: int = None, 
                    threshold_mode: str = 'soft') -> np.ndarray:
    """
    Apply wavelet denoising to a signal. Much faster than CEEMDAN.
    
    Parameters
    ----------
    signal : np.ndarray
        Input signal
    wavelet : str
        Wavelet type ('db4', 'sym4', 'coif3')
    level : int
        Decomposition level. If None, automatically determined.
    threshold_mode : str
        soft
    
    Returns
    -------
    denoised : np.ndarray
        Denoised signal
    """
    # Determine decomposition level if not specified
    if level is None:
        level = pywt.dwt_max_level(len(signal), wavelet)
        level = min(level, 6)  # Cap at 6 levels
    
    # Wavelet decomposition
    coeffs = pywt.wavedec(signal, wavelet, level=level)
    
    # Estimate noise from finest detail coefficients (MAD estimator)
    sigma = np.median(np.abs(coeffs[-1])) / 0.6745
    
    # Universal threshold
    threshold = sigma * np.sqrt(2 * np.log(len(signal)))
    
    # Apply threshold to detail coefficients (keep approximation unchanged)
    denoised_coeffs = [coeffs[0]]  # Keep approximation
    for detail in coeffs[1:]:
        denoised_coeffs.append(pywt.threshold(detail, threshold, mode=threshold_mode))
    
    # Reconstruct
    denoised = pywt.waverec(denoised_coeffs, wavelet)
    
    # Handle length mismatch due to padding
    return denoised[:len(signal)]

def extract_csd(str: obspy.Stream, nfft: int, cent_index: int) -> np.ndarray:
    
    """Convert a signal into a Cross Spectral Density matrix, a two dimensional matrix representation of the signal in frequency domain.
    Parameters
    ----------
    str : obspy.Stream
        1D array signal values. Can be time series or frequency series.
    freq_range : tuple
        Frequency range to extract CSD from (min_freq, max_freq)
    nfft : int
        Number of FFT points.
    preprocess : bool
        Whether to preprocess the signal with a bandpass filter before computing CSD.
    cent_index : int
        Index of the center frequency in the CSD matrix to extract around.
    Returns:
    ----------
    csd_matrix : 2darray
        2d np.array of corresponding cross spectral density matrix
    """
    ref_sensor = str[cent_index]
    csd_list = []
    pxy = []
    for tr in str:
        if tr == ref_sensor:
            continue
        else:
            _, pxy_temp = signal.csd(ref_sensor.data, tr.data, fs=ref_sensor.stats.sampling_rate, nperseg=len(ref_sensor.data), nfft=nfft)
            pxy.append(pxy_temp)
    for i in pxy:
        phase = np.angle(i)
        csd_list.append(phase)
    for i in pxy:
        mag = np.abs(i)
        csd_list.append(mag)

    csd_matrix = np.array(csd_list)
    return csd_matrix

def apply_mvida_to_stream(strm: obspy.Stream, strength: float) -> obspy.Stream:
    """Adds jitter to a instram based on the covariance of the original stream.
        ----------
        strm : obspy.Stream
            Obspy infrasound stream to apply augmentation to
        strength : float
            Strength of the jitter to apply.
        Returns:
        ----------
        strm_aug : obspy.Stream
            Augmented Obspy infrasound stream with jitter applied.
        """
    strm_aug = strm.copy()
    data_list = [tr.data for tr in strm_aug]
    
    min_len = min(len(d) for d in data_list)
    data_list = [d[:min_len] for d in data_list]
    data_array = np.array(data_list)
    
    cov = np.cov(data_array) 
    
    jitter = np.random.multivariate_normal(
        np.zeros(len(strm_aug)), 
        cov * strength, 
        size=min_len
    ).T 
    
    # Inject jitter back into traces (truncate trace data to min_len)
    for i, tr in enumerate(strm_aug):
        tr.data = tr.data[:min_len] + jitter[i]
        
    return strm_aug

def create_gaf(csd_data: np.array, summation: bool = True, size: int = 64) -> np.ndarray:
    """Convert a signal into a Gramian Angular Field, a two dimenions matrix representation of the signal.

    Parameters
    ----------
    raw_data : np.array
        2D array raw signal values. Can be time series or frequency series.
    csd_data : np.array
        2D array of cross spectral density matrix.
    summation : bool, optional
        Used to dermine if the GAF is based on summation (True) or difference (False) of angles.
    Returns:
    ----------
    gaf : 2darray
        2d np.array of corresponding gramian angular field

    """
    """
    if len(raw_data[0]) != 64:
        raw_data = resample(raw_data, 64, axis=1)
    if len(csd_data[0]) != 64:
    
        csd_data = resample(csd_data, 64, axis=1)"""
    gaf = GramianAngularField(image_size=size, sample_range=(0, 1), method='summation' if summation else 'difference')
    csd_gafs = gaf.fit_transform(csd_data)
    return csd_gafs

def create_cwt(raw_data: np.array, freq_range: tuple, num_freq: int) -> np.ndarray:
    """Converts a signal into its Continuous Wavelet Transform representation.

    Parameters
    ----------
    raw_data : np.array
        2D array raw signal values. Can be time series or frequency series.
    freq_range : tuple
        Frequency range for the CWT.
    num_freq : int
        Number of frequency bins for the CWT (Must match GAF image size).
    Returns:
    ----------
    cwt_data : 2darray
        2d np.array of corresponding continuous wavelet transform representation of the signal.

    """
    cwt_data = cwt(raw_data, 1/len(raw_data), 8, freq_range[0], freq_range[1], nf=num_freq)
    return cwt_data

def create_sstcwt(raw_data: np.array, fs, freq_range: tuple, num_freq: int) -> np.ndarray:
    wavelet = 'morlet'
    Tx, _, ssq_freqs, _ = ssqueezepy.ssq_cwt(raw_data, wavelet=wavelet, fs=fs)
    sst_mag = np.abs(Tx)
    idx = np.where((ssq_freqs >= freq_range[0]) & (ssq_freqs <= freq_range[1]))[0]
    if len(idx) > 0:
        sst_mag = sst_mag[idx, :]
    h_factor = num_freq / sst_mag.shape[0]
    w_factor = num_freq / sst_mag.shape[1]
    sstcwt_data = zoom(sst_mag, (h_factor, w_factor))
    return sstcwt_data

def plot_gaf_stack(gaf_stack: np.ndarray) -> None:
    """
    Plots the 10-channel GAF stack to visually inspectin GAF is as expected.
    Parameters
    ----------
    gaf_stack : np.ndarray
        np array with shapes of (10, hieght, width)
        0-3 Raw Signal GAFs
        4-6 CSD Phase GAFs
        7-9 CSD Magnitude GAFs
    Returns:
    ----------
    None -> Just plots the GAF stack
    """
    titles = [
        "Raw S1", "Raw S2", "Raw S3", "Raw S4", # 0-3
        "CSD Phase (1-2)", "CSD Phase (1-3)", "CSD Phase (1-4)", # 4-6
        "CSD Mag (1-2)", "CSD Mag (1-3)", "CSD Mag (1-4)" # 7-9
    ]
    fig, axes = plt.subplots(2, 5, figsize=(20, 8))
    axes = axes.flatten()

    for i in range(10):
        cmap = 'rainbow'
        axes[i].imshow(gaf_stack[i], cmap=cmap, origin='lower')
        axes[i].set_title(titles[i])
        axes[i].axis('off')    
    plt.tight_layout()
    plt.show()



"""
Code Starts Here
"""


path = os.getcwd() + '/sandbox/gaf_classification/'
cl = Client("IRIS")
with open(path+'training/json/merged_detections.json', 'r') as f:
    detections = json.load(f)

all_entries = detections
np.random.shuffle(all_entries)  #Shuffles signal/noise so event dates are mixed up

X_data = []
Y_labels = []
window = 12.8
stack_size = 6
overlap = .25
frame_length = window / (stack_size-(stack_size-1)*overlap)
frame_step = frame_length / (stack_size * (1 - overlap))

for num, entry in enumerate(all_entries):
    while True:
        try:
            center_time = obspy.UTCDateTime(entry['Time (UTC)']+'Z')
            s_time = center_time - window/2
            e_time = center_time + window/2
            strm_g = cl.get_waveforms(network="IM", station="I59*", location="", channel="BDF", starttime=s_time, endtime=e_time)
            strm = strm_g.copy()
            # Preprocess Stream
            strm.detrend()
            strm.taper(max_percentage=0.05, type="hann")
            strm.filter("bandpass", freqmin=1.0, freqmax=8.0, corners=4, zerophase=True)
            #  Wavelet 
            for tr in strm:
                tr.data = wavelet_denoise(tr.data, wavelet='db4', level=4, threshold_mode='soft')
        
            global_max = max([abs(tr.data).max() for tr in strm])
            if global_max > 0:
                for tr in strm:
                    tr.data = tr.data / global_max

            num_versions = 25  # Data is limited so we augment using MVIDA to add in jitter
            v = 0
            while v < num_versions:
                """if num > 139:
                    # Testing and Validation data should not be augmented.
                    v = num_versions-1
                    current_strm = strm.copy()"""
                if v == 0:
                    current_strm = strm.copy()
                else:
                    ref_sensor = strm[0]
                    comp_sensors = strm[1:]

                    random.shuffle(comp_sensors)
                    strm_list = Stream(ref_sensor) + comp_sensors
                    shuffled_strm = obspy.Stream(traces=strm_list)
                    current_strm = apply_mvida_to_stream(shuffled_strm, strength=0)

                gaf_sequence = []
                for i in range(stack_size):
                    # Because we are using this data for ConvLTSM we split the window into multiple frames to see how it changes over time/space
                    t_start = s_time + (i * frame_step)
                    t_end = t_start + frame_length
                    strm_window = current_strm.copy()
                    strm_window.trim(starttime=t_start, endtime=t_end, pad=True, fill_value=0.0)
                    csd = extract_csd(str=strm_window, nfft=128, cent_index=0)
                    gaf_data = create_gaf(csd_data=csd, summation=False, size=64)
                    
                    raw_cwt = []
                    for tr in strm_window:
                        cwt_mag = create_sstcwt(raw_data=tr.data, fs=tr.stats.sampling_rate, freq_range=(1.0, 8.0), num_freq=64)
                        
                        #cwt_resized = cv2.resize(np.abs(cwt_mag), (64, 64))
                        
                        # Normalize CWT per channel (0 to 1) so it matches GAF scale
                        cwt_max = cwt_mag.max()
                        if cwt_max > 0:
                            cwt_mag = cwt_mag / cwt_max  
                        raw_cwt.append(cwt_mag)
                    cwt_gaf = np.concatenate((raw_cwt, gaf_data), axis=0)
                    gaf_sequence.append(cwt_gaf)
                X_data.append(np.array(gaf_sequence))
                Y_labels.append(entry['Class'])
                v += 1
            print(f"Processed entry {num+1}/{len(all_entries)}. Dataset size: {len(X_data)}")
            break
        except Exception as e:
            print(f"Error processing entry {num+1}: {e}. Retrying...")
            continue
        """
        with open('sandbox\\gaf_classification\\training\\numpy\\all_entries.pkl', 'wb') as f:
            pickle.dump(all_entries, f)
        """
X_train = np.array(X_data)
Y_train = np.array(Y_labels)

np.save('X_train_cwt_5D.npy', X_train)
np.save('Y_train_cwt_labels.npy', Y_train)

print("Serialization Complete.")
print(f"Final X Data Shape: {X_train.shape}")
print(f"Final Y Data Shape: {Y_train.shape}")
