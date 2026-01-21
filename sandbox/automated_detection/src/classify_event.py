import numpy as np
from scipy import signal
from pyts.image import GramianAngularField
import matplotlib.pyplot as plt
import obspy
from obspy.signal.tf_misfit import cwt
import cv2
import pywt
import ssqueezepy
import tensorflow as tf
from tensorflow.keras.models import load_model
from scipy.ndimage import zoom

def wavelet_denoise(signal: np.ndarray, wavelet: str = 'db4', level: int = None, 
                    threshold_mode: str = 'soft') -> np.ndarray:
    """
    Apply wavelet denoising to a signal.
    
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
    # Level not given default to highest level (anything past 6 may remove too much signal)
    if level is None:
        level = pywt.dwt_max_level(len(signal), wavelet)
        level = min(level, 6)
    # Decomp signal and create threshold coeffs
    coeffs = pywt.wavedec(signal, wavelet, level=level)
    sigma = np.median(np.abs(coeffs[-1])) / 0.6745
    threshold = sigma * np.sqrt(2 * np.log(len(signal)))
    denoised_coeffs = [coeffs[0]]

    # Apply wavelet denoising
    for detail in coeffs[1:]:
        denoised_coeffs.append(pywt.threshold(detail, threshold, mode=threshold_mode))
    denoised = pywt.waverec(denoised_coeffs, wavelet)
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
    """Converts a signal into its Synchrosqueeze Continuous Wavelet Transform representation.

    Parameters
    ----------
    raw_data : np.array
        2D array raw signal values. Can be time series or frequency series.
    fs : float
        Sampling frequency of the raw data.
    freq_range : tuple
        Frequency range for the CWT.
    num_freq : int
        Number of frequency bins for the CWT (Must match GAF image size).
    Returns:
    ----------
    cwt_data : 2darray
        2d np.array of corresponding continuous wavelet transform representation of the signal.

    """
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
        0-3 ssCWT Signal GAFs
        4-6 CSD Phase GAFs
        7-9 CSD Magnitude GAFs
    Returns:
    ----------
    None -> Just plots the GAF stack
    """
    titles = [
        "ssCWT S1", "ssCWT S2", "ssCWT S3", "ssCWT S4",
        "CSD Phase (1-2)", "CSD Phase (1-3)", "CSD Phase (1-4)",
        "CSD Mag (1-2)", "CSD Mag (1-3)", "CSD Mag (1-4)"
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

def single_stack(strm, center_time, window: float, stack_size: int, overlap: float) -> np.ndarray:
    s_time = center_time - window/2
    frame_length = window / (stack_size-(stack_size-1)*overlap)
    frame_step = frame_length / (stack_size * (1 - overlap))
    # Preprocess Stream
    strm.detrend()
    strm.taper(max_percentage=0.05, type="hann")
    strm.filter("bandpass", freqmin=1.0, freqmax=8.0, corners=4, zerophase=True)
    for tr in strm:
        tr.data = wavelet_denoise(tr.data, wavelet='db4', level=4, threshold_mode='soft')
    global_max = max([abs(tr.data).max() for tr in strm])
    if global_max > 0:
        for tr in strm:
            tr.data = tr.data / global_max
    gaf_sequence = []
    for i in range(stack_size):
        # BC we are using this data for ConvLTSM we split the window into multiple frames to see how it changes over time/space
        t_start = s_time + (i * frame_step)
        t_end = t_start + frame_length
        strm_window = strm.copy()
        strm_window.trim(starttime=t_start, endtime=t_end, pad=True, fill_value=0.0)
        csd = extract_csd(str=strm_window, nfft=128, cent_index=0)
        gaf_data = create_gaf(csd_data=csd, summation=False, size=64)
        raw_cwt = []
        for tr in strm_window:
            cwt_mag = create_sstcwt(raw_data=tr.data, fs=20, freq_range=(1,8), num_freq=64)        
            """cwt_resized = cv2.resize(np.abs(cwt_mag), (64, 64))
            # Normalize CWT per channel (0 to 1) so it matches GAF scale"""
            cwt_max = cwt_mag.max()
            if cwt_max > 0:
                cwt_mag = cwt_mag / cwt_max  
            raw_cwt.append(cwt_mag)
        cwt_gaf = np.concatenate((raw_cwt, gaf_data), axis=0)
        gaf_sequence.append(cwt_gaf)
    data_stack = np.array(gaf_sequence)
    print(f"Created stack with shape: {data_stack.shape}")
    return data_stack

def predict_entry(single_stack, model_path):
    model = load_model(model_path)
    preds = model.predict(single_stack)
    # Handle output shape robustly
    if isinstance(preds, list):
        preds = preds[0]
    y_pred_class = (preds.flatten()[0] > 0.5).astype(int)
    class_labels = {0: "Sonic Boom", 1: "Surf"}
    class_name = class_labels[y_pred_class]
    return class_name