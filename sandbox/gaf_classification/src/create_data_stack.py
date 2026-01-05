import numpy as np
from scipy import signal
from scipy.signal import resample
from pyts.image import GramianAngularField
import matplotlib.pyplot as plt
import obspy
from obspy.clients.fdsn import Client
import json
import pickle
from obspy.signal.tf_misfit import cwt
import cv2

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
    gaf = GramianAngularField(image_size=size, method='summation' if summation else 'difference')
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


path = "sandbox/gaf_classification/"
cl = Client("IRIS")
with open(path+'training/json/merged_detections.json', 'r') as f:
    detections = json.load(f)
with open(path+'training/json/merged_noise.json', 'r') as f:
    noise = json.load(f)

all_entries = detections + noise
np.random.shuffle(all_entries)  #Shuffles signal/noise so event dates are mixed up

X_data = []
Y_labels = []
window = 6.4
stack_size = 3
frame_step = window / (stack_size+1)

for num, entry in enumerate(all_entries):
    center_time = obspy.UTCDateTime(entry['Time (UTC)']+'Z')
    s_time = center_time - window/2
    e_time = center_time + window/2
    strm_g = cl.get_waveforms(network="IM", station="I59*", location="", channel="BDF", starttime=s_time, endtime=e_time)
    strm = strm_g.copy()
    # Preprocess Stream
    strm.detrend("demean")
    strm.detrend("linear")
    strm.taper(max_percentage=0.05, type="hann")
    strm.filter("bandpass", freqmin=1.0, freqmax=8.0, corners=4, zerophase=True)
   
    global_max = max([abs(tr.data).max() for tr in strm])
    if global_max > 0:
        for tr in strm:
            tr.data = tr.data / global_max

    num_versions = 10  # Data is limited so we augment using MVIDA to add in jitter
    v = 0
    while v < num_versions:
        if num > 196:
            # Testing and Validation data should not be augmented.
            v = num_versions-1
            current_strm = strm.copy()
        if v == 0:
            current_strm = strm.copy()
        else:
            current_strm = apply_mvida_to_stream(strm, strength=0.02)

        frame = window / stack_size
        gaf_sequence = []
        for i in range(stack_size):
            # Because we are using this data for ConvLTSM we split the window into multiple frames to see how it changes over time/space
            t_start = s_time + (i * frame_step)
            t_end = t_start + (frame_step * 2)
            strm_window = current_strm.copy()
            strm_window.trim(starttime=t_start, endtime=t_end, pad=True, fill_value=0.0)
            csd = extract_csd(str=strm_window, nfft=128, cent_index=0)
            gaf_data = create_gaf(csd_data=csd, summation=True, size = 64)
            
            raw_cwt = []
            for tr in strm_window:
                # Obspy CWT returns (32, len(tr.data))
                cwt_mag = create_cwt(raw_data=tr.data, freq_range=(1,8), num_freq=64)
                
                # Resize Time-axis (Length) to 32 to match GAF Width
                # From (32, 64) -> (32, 32)
                cwt_resized = cv2.resize(np.abs(cwt_mag), (64, 64))
                
                # Normalize CWT per channel (0 to 1) so it matches GAF scale
                cwt_max = cwt_resized.max()
                if cwt_max > 0:
                    cwt_resized = cwt_resized / cwt_max  
                raw_cwt.append(cwt_resized)
            cwt_gaf = np.concatenate((raw_cwt, gaf_data), axis=0)
            gaf_sequence.append(cwt_gaf)
        X_data.append(np.array(gaf_sequence))
        Y_labels.append([entry['Class'], entry.get('Back Azimuth'), entry.get('Trace Vel. (m/s)')])
        v += 1
    print(f"Processed entry {num+1}/{len(all_entries)}. Dataset size: {len(X_data)}")

with open('sandbox\\gaf_classification\\training\\numpy\\all_entries.pkl', 'wb') as f:
    pickle.dump(all_entries, f)

X_train = np.array(X_data)
Y_train = np.array(Y_labels)

np.save('X_train_cwt_5D.npy', X_train.astype('float32'))
np.save('Y_train_cwt_labels.npy', Y_train.astype('float32'))

print("Serialization Complete.")
print(f"Final Data Shape: {X_train.shape}")