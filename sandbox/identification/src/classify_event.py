import cv2
import numpy as np
import sys
import obspy
from obspy.signal.tf_misfit import cwt
import ssqueezepy
import tensorflow as tf
from tensorflow.keras.models import load_model
from scipy.ndimage import zoom
from obspy.geodetics.base import gps2dist_azimuth
import random
from tensorflow.keras.applications import EfficientNetB0
from tensorflow.keras.applications.efficientnet import preprocess_input
from EfficientNetB0 import build_efficientnetb0, finetune_backbone, EfficientNetPreprocessing


def inv_align(st: obspy.Stream, inventory: obspy.Inventory, back_azimuth_deg: float, velocity_ms: float) -> obspy.Stream:
    """
    Aligns traces based on array geometry using m/s velocity.
    Parameters:
    ----------
    st : obspy.Stream
        Input stream with traces to be aligned.
    inventory : obspy.Inventory
        Station metadata for coordinate lookup.
    back_azimuth_deg : float
        Back-azimuth in degrees (0° = North, 90° = East).
    velocity_ms : float
        Wave velocity in m/s for time shift calculation.
    Returns:
    ----------
    obspy.Stream
        New stream with geometrically aligned traces.
    """
    st_out = st.copy()
    ref_tr = st_out[0]
    
    # Get Reference Coordinates
    ref_coords = inventory.get_coordinates(ref_tr.id)
    ref_lat = ref_coords['latitude']
    ref_lon = ref_coords['longitude']
    
    print(f"--- Geometric Alignment (BAZ: {back_azimuth_deg}°, Vel: {velocity_ms} m/s) ---")
    # Calculate time shifts for each trace based on distance and back-azimuth
    for tr in st_out:
        coords = inventory.get_coordinates(tr.id)
        dist_m, az_to_sensor, _ = gps2dist_azimuth(ref_lat, ref_lon, 
                                                   coords['latitude'], 
                                                   coords['longitude'])
        
        angle_diff = np.radians(az_to_sensor - back_azimuth_deg)
        dist_towards_source = dist_m * np.cos(angle_diff)
        time_shift = dist_towards_source / velocity_ms
        tr.stats.starttime += time_shift  
        #print(f"   {tr.id[-4:]}: Dist {dist_m:.1f}m -> Shift {time_shift:.3f}s")

    return st_out


def create_cwt(raw_data: np.array, fs: float,freq_range: tuple, num_freq: int) -> np.ndarray:
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
    cwt_data = cwt(raw_data, 1/fs, 8, freq_range[0], freq_range[1], nf=num_freq)
    h_factor = num_freq / cwt_data.shape[0]
    w_factor = num_freq / cwt_data.shape[1]
    cwt_data = zoom(cwt_data, (h_factor, w_factor))
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


def stack_weighted_traces(aligned_strm, noise_window_sec=60):
    """
    Turns 4 aligned sensors into 1 high-quality Virtual Trace.
    Uses 'Inverse Variance Weighting' to suppress noisy channels
    Parameters
    ----------
    aligned_strm : obspy.Stream
        Input stream where traces are already phase-aligned and trimmed
        to the same length.
    noise_window_sec : float
        Time in seconds from the start of trace for noise estimation
    Returns
    -------
    v_trace : obspy.Trace
        A virtual trace created by weighted stack of traces for improved SNR
    """
    data_matrix = np.stack([tr.data for tr in aligned_strm])
    fs = aligned_strm[0].stats.sampling_rate
    try:
        noise_samples = int(noise_window_sec * fs)
        noise_section = data_matrix[:, :noise_samples]
        variances = np.var(noise_section, axis=1)
        variances[variances == 0] = 1e-9
        raw_weights = 1.0 / variances
        weights = raw_weights / np.sum(raw_weights)
    except Exception:
        # If noise estimation fails, fallback to equal weights
        weights = [.25, .25, .25, .25]
    virtual_data = np.sum(data_matrix * weights[:, np.newaxis], axis=0)
    v_trace = obspy.Trace(data=virtual_data, header=aligned_strm[0].stats.copy())
    v_trace.stats.station = "I59V"
    return obspy.Stream(traces=v_trace)

def apply_mvida_to_stream(aligned_strm):
    """
    Takes an ALIGNED ObsPy Stream (4 traces) and applies MVIDA
    to generate a 'Virtual' Stream (1 Trace)
    Parameters
    ----------
    aligned_strm : obspy.Stream
        Input stream where traces are already phase-aligned and trimmed
        to the same length      
    Returns
    -------
    virtual_strm : obspy.Stream
        A new Stream containing 1 virtual trace derived from the input
    """
    data_matrix = np.stack([tr.data for tr in aligned_strm])
    num_sensors, n_samples = data_matrix.shape
    virtual_strm = obspy.Stream()
    k = random.randint(2, num_sensors - 1)
    indices = random.sample(range(num_sensors), k)
    alphas = np.random.uniform(0.5, 2.5, size=k)
    weighted_sum = np.zeros(n_samples)
    for j, idx in enumerate(indices):
        weighted_sum += alphas[j] * data_matrix[idx]
    virtual_data = weighted_sum / np.sum(alphas)
    v_trace = obspy.Trace(data=virtual_data, header=aligned_strm[0].stats.copy())
    v_trace.stats.station = "VIR"
    virtual_strm.append(v_trace)
    return virtual_strm

def single_stack(strm, inventory, freq_range, center_time, window: float, stack_size: int, overlap: float, back_azimuth, trace_velocity, size) -> np.ndarray:
    """
    Takes a detection stream and generates a single CWT stack for classification.
    Parameters
    ----------
    strm : obspy.Stream
        Input stream containing traces for a single detection, already trimmed to the same time window.
    inventory : obspy.Inventory
        Station metadata for coordinate lookup and response removal.
    center_time : obspy.UTCDateTime
        Center time of the detection window.
    window : float
        Total window length in seconds for the stack.
    stack_size : int
        Number of frames in the stack (e.g., 6).
    overlap : float
        Fractional overlap between frames (e.g., 0.5 for 50% overlap).
    back_azimuth : float
        Back-azimuth in degrees for geometric alignment.
    trace_velocity : float
        Wave velocity in m/s for geometric alignment.
    Returns
    -------
    data_stack : np.ndarray
        A 3D numpy array of shape (num_freq, num_freq, stack_size) representing the CWT stack for classification.
    """
    fft_size = int(20*window)
    # Preprocess Stream
    for tr in strm:
        tr.attach_response(inventory)
        tr.remove_sensitivity()
    strm.detrend()
    strm.taper(max_percentage=0.05, type="blackmanharris")
    strm.filter("bandpass", freqmin=freq_range[0], freqmax=freq_range[1], corners=4, zerophase=True)
    t_strm = inv_align(strm, inventory, back_azimuth, trace_velocity)
    strm = t_strm.copy()
    final_start = center_time - (window / 2)
    final_end = center_time + (window / 2)
    strm.trim(starttime=final_start, endtime=final_end, pad=True)
    single_strm = stack_weighted_traces(strm)
    current_strm = obspy.Stream(traces=single_strm)

    frame_length = window / (stack_size-(stack_size-1)*overlap)
    frame_step = frame_length / (stack_size * (1 - overlap))
    for i in range(stack_size):
        # Split data stack into multiple frames to capture temporal evolution
        t_start = final_start + (i * frame_step)
        t_end = t_start + frame_length
        strm_window = current_strm.copy()
        strm_window.trim(starttime=t_start, endtime=t_end, pad=True, fill_value=0.0)
        if len(strm_window[0].data) > fft_size:
            data = strm_window[0].data
            strm_window[0].data = data[:fft_size]
        elif len(strm_window[0].data) < fft_size:
            data = strm_window[0].data
            pad_width = fft_size - len(data)
            strm_window[0].data = np.pad(data, (0, pad_width), 'constant')
        # Create CWT representation for the current frame
        raw_cwt = []
        for tr in strm_window:
            cwt_complex = create_cwt(raw_data=tr.data, fs=20, freq_range=freq_range, num_freq=fft_size)
            cwt_mag = np.abs(cwt_complex)
            cwt_log = np.log1p(cwt_mag)
            cwt_norm = (cwt_log - cwt_log.min()) / (cwt_log.max() - cwt_log.min() + 1e-10)
            raw_cwt.append(cwt_norm)
    data_stack = np.array(raw_cwt).transpose(1, 2, 0)

    data_stack = cv2.resize(data_stack, (size, size), interpolation=cv2.INTER_AREA)
    if data_stack.ndim == 2:
        data_stack = np.expand_dims(data_stack, axis=-1)

    # Validate the data stack
    if np.isnan(data_stack).any():
        print("WARNING: NaN values detected in single_stack!")
        data_stack = np.nan_to_num(data_stack, nan=0.0)
    if np.isinf(data_stack).any():
        print("WARNING: Inf values detected in single_stack!")
        data_stack = np.nan_to_num(data_stack, posinf=1.0, neginf=-1.0)
    return data_stack

def mvida_stack(strm, inventory, freq_range, center_time, window: float, stack_size: int, overlap: float, back_azimuth, trace_velocity) -> np.ndarray:
    """
    Takes a detection stream and generates a single CWT stack for classification.
    Parameters
    ----------
    strm : obspy.Stream
        Input stream containing traces for a single detection, already trimmed to the same time window.
    inventory : obspy.Inventory
        Station metadata for coordinate lookup and response removal.
    center_time : obspy.UTCDateTime
        Center time of the detection window.
    window : float
        Total window length in seconds for the stack.
    stack_size : int
        Number of frames in the stack (e.g., 6).
    overlap : float
        Fractional overlap between frames (e.g., 0.5 for 50% overlap).
    back_azimuth : float
        Back-azimuth in degrees for geometric alignment.
    trace_velocity : float
        Wave velocity in m/s for geometric alignment.
    Returns
    -------
    data_stack : np.ndarray
        A 3D numpy array of shape (num_freq, num_freq, stack_size) representing the CWT stack for classification.
    """
    fft_size = int(20*window)
    # Preprocess Stream
    for tr in strm:
        tr.attach_response(inventory)
        tr.remove_sensitivity()
    strm.detrend()
    strm.taper(max_percentage=0.05, type="blackmanharris")
    strm.filter("bandpass", freqmin=freq_range[0], freqmax=freq_range[1], corners=4, zerophase=True)
    t_strm = inv_align(strm, inventory, back_azimuth, trace_velocity)
    strm = t_strm.copy()
    final_start = center_time - (window / 2)
    final_end = center_time + (window / 2)
    strm.trim(starttime=final_start, endtime=final_end, pad=False)
    single_strm = apply_mvida_to_stream(strm)
    current_strm = obspy.Stream(traces=single_strm)

    frame_length = window / (stack_size-(stack_size-1)*overlap)
    frame_step = frame_length / (stack_size * (1 - overlap))
    for i in range(stack_size):
        # Split data stack into multiple frames to capture temporal evolution
        t_start = final_start + (i * frame_step)
        t_end = t_start + frame_length
        strm_window = current_strm.copy()
        strm_window.trim(starttime=t_start, endtime=t_end, pad=True, fill_value=0.0)
        if len(strm_window[0].data) > fft_size:
            data = strm_window[0].data
            strm_window[0].data = data[:fft_size]
        elif len(strm_window[0].data) < fft_size:
            data = strm_window[0].data
            pad_width = fft_size - len(data)
            strm_window[0].data = np.pad(data, (0, pad_width), 'constant')
        # Create CWT representation for the current frame
        raw_cwt = []
        for tr in strm_window:
            cwt_complex = create_cwt(raw_data=tr.data, fs=20, freq_range=freq_range, num_freq=fft_size)
            cwt_mag = np.abs(cwt_complex)
            cwt_log = np.log1p(cwt_mag)
            cwt_norm = (cwt_log - cwt_log.min()) / (cwt_log.max() - cwt_log.min() + 1e-10)
            raw_cwt.append(cwt_norm)
    data_stack = np.array(raw_cwt).transpose(1, 2, 0)
    
    # Validate the data stack
    if np.isnan(data_stack).any():
        print("WARNING: NaN values detected in mvida_stack!")
        data_stack = np.nan_to_num(data_stack, nan=0.0)
    if np.isinf(data_stack).any():
        print("WARNING: Inf values detected in mvida_stack!")
        data_stack = np.nan_to_num(data_stack, posinf=1.0, neginf=-1.0)
    return data_stack

def predict_entry(single_stack, model_path, model=None, class_names=None):
    """
    Predict class from a single CWT stack.

    Parameters
    ----------
    single_stack : np.ndarray
        CWT image stack with shape (1, H, W, 1) or (H, W, 1)
    model_path : str
        Path to the saved model file
    model : keras.Model, optional
        Pre-loaded model to avoid repeated loading (recommended for multiple predictions)
    class_names : list[str], optional
        Optional list of class names matching the model output order.

    Returns
    -------
    class_name : str
        Predicted class name
    """
    if model is None:
        model = load_model(model_path)

    if single_stack.ndim == 3:
        single_stack = np.expand_dims(single_stack, axis=0)

    pred = model.predict(single_stack, verbose=0)

    if pred.ndim == 1 or pred.shape[-1] == 1:
        prob = float(pred[0] if pred.ndim == 1 else pred[0, 0])
        class_idx = 1 if prob > 0.5 else 0
        default_names = ["Sonic Boom", "Surf"]
        class_names = class_names or default_names
        confidence = prob if class_idx == 1 else 1.0 - prob
    else:
        class_idx = int(np.argmax(pred[0]))
        confidence = float(pred[0, class_idx])
        if class_names is None:
            if pred.shape[-1] == 3:
                class_names = ["surf", "transient", "thunder"]
            else:
                class_names = [f"class_{i}" for i in range(pred.shape[-1])]

    class_name = class_names[class_idx]
    print(f"Predicted Class: {class_name} with confidence {confidence:.4f} (raw scores: {pred[0]})")
    return class_name
