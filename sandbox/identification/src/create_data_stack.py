import librosa
import numpy as np
from scipy.signal import hilbert
import os
import numpy as np
import pywt
from scipy import signal
from pyts.image import GramianAngularField, MarkovTransitionField, RecurrencePlot
import matplotlib.pyplot as plt
import obspy
from obspy.clients.fdsn import Client
import json
import cv2
import random
import ssqueezepy
from obspy import Stream
from scipy.ndimage import zoom
from obspy.geodetics import gps2dist_azimuth
from sklearn.model_selection import train_test_split
from scipy.signal import hilbert
import emd
from scipy.signal import stft
from obspy.signal.tf_misfit import cwt
#from scipy.signal import cwt, ricker

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

def apply_jitter_to_stream(strm: obspy.Stream, strength: float) -> obspy.Stream:
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


def inv_align(st, inventory, back_azimuth_deg, velocity_ms):
    """
    Aligns traces based on array geometry using m/s velocity.
    """
    st_out = st.copy()
    ref_tr = st_out[0]
    
    # Get Reference Coordinates
    ref_coords = inventory.get_coordinates(ref_tr.id)
    ref_lat = ref_coords['latitude']
    ref_lon = ref_coords['longitude']
    
    print(f"--- Geometric Alignment (BAZ: {back_azimuth_deg}°, Vel: {velocity_ms} m/s) ---")
    
    for tr in st_out:
        # Get Sensor Coordinates
        coords = inventory.get_coordinates(tr.id)
        
        # Calculate distance (meters) and azimuth (degrees)
        # gps2dist_azimuth returns: (distance_in_meters, azimuth, back_azimuth)
        dist_m, az_to_sensor, _ = gps2dist_azimuth(ref_lat, ref_lon, 
                                                   coords['latitude'], 
                                                   coords['longitude'])
        
        # Project sensor position onto the wave vector
        # Angle between "direction of wave" and "direction to sensor"
        # We subtract BAZ from Azimuth to find the angle difference
        angle_diff = np.radians(az_to_sensor - back_azimuth_deg)
        
        # Calculate distance *towards* the source relative to reference
        # (+ means closer to source, - means further away)
        dist_towards_source = dist_m * np.cos(angle_diff)
        
        # Time Shift = Distance (m) / Velocity (m/s)
        time_shift = dist_towards_source / velocity_ms
        
        # APPLY SHIFT
        # If sensor is closer (positive dist), signal arrives EARLY.
        # To align it with the later Reference, we must ADD time to its start.
        tr.stats.starttime += time_shift
        
        print(f"   {tr.id[-4:]}: Dist {dist_m:.1f}m -> Shift {time_shift:.3f}s")

    return st_out

def apply_mvida_to_stream(aligned_strm):
    """
    Takes an ALIGNED ObsPy Stream (4 traces) and applies MVIDA
    to generate a 'Virtual' Stream (4 traces).
    
    Parameters
    ----------
    aligned_strm : obspy.Stream
        Input stream where traces are already phase-aligned and trimmed
        to the same length.
        
    Returns
    -------
    virtual_strm : obspy.Stream
        A new Stream containing 4 virtual traces derived from the input.
    """
    # 1. Extract data into a matrix for easy math
    # Shape: (4, N_samples)
    data_matrix = np.stack([tr.data for tr in aligned_strm])
    num_sensors, n_samples = data_matrix.shape
    
    # Prepare the output stream
    virtual_strm = obspy.Stream()
    
    # We generate 4 virtual channels to match the input dimensions
    k = random.randint(2, num_sensors - 1)
    indices = random.sample(range(num_sensors), k)
    
    # ---------------------------------------------------------
    # B. WEIGHTING: Generate random alphas (1.0 to 3.5)
    # ---------------------------------------------------------
    alphas = np.random.uniform(1.0, 3.5, size=k)
    
    # ---------------------------------------------------------
    # C. LINEAR COMBINATION (The MVIDA Formula)
    #    x_v = sum(alpha * x_i) / sum(alpha)
    # ---------------------------------------------------------
    weighted_sum = np.zeros(n_samples)
    for j, idx in enumerate(indices):
        weighted_sum += alphas[j] * data_matrix[idx]
        
    virtual_data = weighted_sum / np.sum(alphas)
    
    # ---------------------------------------------------------
    # D. REPACKAGING: Create a new Trace object
    # ---------------------------------------------------------
    # Copy metadata from the first trace (sampling rate, etc.)
    v_trace = obspy.Trace(data=virtual_data, header=aligned_strm[0].stats.copy())
    
    # Mark this as a virtual channel in the metadata
    v_trace.stats.station = f"VIR"
    
    virtual_strm.append(v_trace)
        
    return virtual_strm

def create_sstcwt(raw_data: np.array, fs, freq_range: tuple, num_freq: int) -> np.ndarray:
    Tx, _, ssq_freqs, _ = ssqueezepy.ssq_cwt(raw_data, fs=fs)
    sst_mag = np.abs(Tx)
    idx = np.where((ssq_freqs >= freq_range[0]) & (ssq_freqs <= freq_range[1]))[0]
    if len(idx) > 0:
        sst_mag = sst_mag[idx, :]
    #h_factor = num_freq / sst_mag.shape[0]
    #w_factor = num_freq / sst_mag.shape[1]
    #sstcwt_data = zoom(sst_mag, (h_factor, w_factor))
    return sst_mag



def extract_psd(str: obspy.Stream, nfft: int) -> np.ndarray:
    """Convert a signal into a Power Spectral Density matrix, a two dimensional matrix representation of the signal in frequency domain.
    Parameters
    ----------
    str : obspy.Stream
        1D array signal values. Can be time series or frequency series.
    nfft : int
        Number of FFT points.
    preprocess : bool
        Whether to preprocess the signal with a bandpass filter before computing PSD.
    cent_index : int
        Index of the center frequency in the PSD matrix to extract around.
    Returns:
    ----------
    psd_matrix : 2darray
        2d np.array of corresponding power spectral density matrix
    """
    psd_list = []
    pxx = []
    for tr in str:
        _, pxx_temp = signal.welch(tr.data, fs=tr.stats.sampling_rate, nperseg=len(tr.data), nfft=nfft)
        pxx.append(pxx_temp)
    # Since we are aligning the waveforms, we do not care about the phase offset (it will be ~zero)
    """for i in pxx:
        phase = np.angle(i)
        psd_list.append(phase)"""
    for i in pxx:
        mag = np.abs(i)
        psd_list.append(mag)
    psd_matrix = np.array(psd_list)
    return psd_matrix


def generate_high_quality_trace(aligned_strm, noise_window_sec=5.0):
    """
    Turns 4 aligned sensors into 1 high-quality Virtual Trace.
    Uses 'Inverse Variance Weighting' to suppress noisy channels.
    """
    data_matrix = np.stack([tr.data for tr in aligned_strm])
    n_sensors, n_pts = data_matrix.shape
    fs = aligned_strm[0].stats.sampling_rate
    
    """# 2. Calculate Weights based on Noise Level
    # We look at the first 'noise_window_sec' seconds to estimate noise power.
    # (Assumes the explosion is in the middle, not the start)
    noise_samples = int(noise_window_sec * fs/2)
    noise_section = data_matrix[:, :noise_samples]
    
    # Variance = Average Power of the noise
    variances = np.var(noise_section, axis=1)
    
    # SAFETY: Avoid division by zero if a trace is perfectly flat
    variances[variances == 0] = 1e-9
    
    # Weight = 1 / Variance (Quiet sensors get big weights)
    raw_weights = 1.0 / variances
    
    # Normalize weights so they sum to 1.0 (Preserves true amplitude)
    weights = raw_weights / np.sum(raw_weights)
    
    print("--- Smart Stack Weights ---")
    for i, w in enumerate(weights):
        print(f"   {aligned_strm[i].id}: {w:.2f} (Noise Var: {variances[i]:.2e})")"""
    weights = np.array([.25, .25, .25, .25])
    virtual_data = np.sum(data_matrix * weights[:, np.newaxis], axis=0)

    v_trace = obspy.Trace(data=virtual_data, header=aligned_strm[0].stats.copy())
    v_trace.stats.station = "I59V"

    return obspy.Stream(traces=v_trace)


def create_texture_analysis(cwt_image: np.ndarray) -> np.ndarray:
    """
    Applies directional Gabor filters to highlight Booms (Vertical) vs Surf (Horizontal).
    
    Parameters
    ----------
    cwt_image : np.ndarray
        The 2D CWT spectrogram (normalized 0.0 to 1.0).
        
    Returns
    -------
    composite_image : np.ndarray
        Shape (H, W, 2). Channel 0 is Boom-enhanced, Channel 1 is Surf-enhanced.
    """
    
    # 1. Define the Boom Filter (Vertical Orientation -> Theta = 0)
    # ksize: (21, 21) - Size of the filter
    # sigma: 4.0 - Spread of the Gaussian envelope
    # theta: 0 - Vertical orientation (detects vertical lines)
    # lambd: 10.0 - Wavelength of the sinusoidal factor (tune this to match boom width)
    # gamma: 0.5 - Spatial aspect ratio
    kernel_boom = cv2.getGaborKernel((21, 21), 4.0, 0, 10.0, 0.5, 0, ktype=cv2.CV_32F)
    
    # 2. Define the Surf Filter (Horizontal Orientation -> Theta = np.pi/2)
    kernel_surf = cv2.getGaborKernel((21, 21), 4.0, np.pi/2, 10.0, 0.5, 0, ktype=cv2.CV_32F)
    
    # 3. Apply Filters (Use CV_32F to keep decimal precision!)
    boom_feature = cv2.filter2D(cwt_image.astype(np.float32), cv2.CV_32F, kernel_boom)
    surf_feature = cv2.filter2D(cwt_image.astype(np.float32), cv2.CV_32F, kernel_surf)
    
    # 4. Stack them into a 2-channel image
    # Shape becomes (Height, Width, 2)
    texture_data = np.stack([boom_feature, surf_feature], axis=-1)
    
    return texture_data

def create_mtf(raw_data: np.array, fs, freq_range, num_freq: int = 256) -> np.ndarray:
    """Convert a signal into a Markov Transition Field, a two dimenions matrix representation of the signal.

    Parameters
    ----------
    raw_data : np.array
        2D array raw signal values. Can be time series or frequency series.
    num_freq : int
        Size of the MTF image (size x size).
    Returns:
    ----------
    mtf : 2darray
        2d np.array of corresponding markov transition field

    """
    env = np.abs(hilbert(raw_data))

    dither = np.random.normal(0, 1e-9, env.shape)
    env = env + dither
    mtf = MarkovTransitionField(n_bins=8)
    mtf_data = mtf.fit_transform(env)
    return mtf_data

def create_welch_gaf(raw_data, n_fft):
    """
    Creates a Gramian Angular Field from normalized 1D data.
    
    Parameters
    ----------
    raw_data : np.ndarray
        1D normalized signal (shape: (n_samples,))
    n_fft : int
        Image size for GAF (output: n_fft x n_fft)
    
    Returns
    -------
    gaf_image : np.ndarray
        Shape (n_fft, n_fft) GAF image
    """
    # GramianAngularField expects 2D input: (n_samples, n_features)
    # Reshape 1D raw_data to (1, n_features) to represent single sample
    raw_data_2d = raw_data.reshape(1, -1)
    
    gaf = GramianAngularField(image_size=n_fft, sample_range=(0, 1), method='difference')
    gaf_image = gaf.fit_transform(raw_data_2d)
    
    # gaf_image shape: (1, n_fft, n_fft), extract the single sample
    return gaf_image.transpose(1, 2, 0)


def create_cwt_image(raw_data, fs, freq_range, target_size):
    """
    Computes a normalized CWT spectrogram image.
    
    Parameters
    ----------
    raw_data : np.array
        1D time-domain signal
    fs : float
        Sampling frequency
    freq_range : tuple
        (min_freq, max_freq) for CWT
    target_size : int
        Output will be (target_size, target_size)
        
    Returns
    -------
    cwt_image : np.ndarray
        Shape (target_size, target_size, 1) normalized CWT image
    """
    cwt_data, _ = pywt.cwt(raw_data, np.arange(1, target_size+1), 'mexh')
    cwt_mag = np.abs(cwt_data)
    cwt_image = cv2.resize(cwt_mag, (target_size, target_size), interpolation=cv2.INTER_CUBIC)
    # Log transform and normalize to [0, 1]
    cwt_log = np.log1p(cwt_image)
    cwt_norm = (cwt_log - np.min(cwt_log)) / (np.max(cwt_log) - np.min(cwt_log) + 1e-9)
    return cwt_norm

def create_recurrence_plot(raw_data, eps=0.1, steps=10):
    """
    Creates a recurrence plot from 1D data.
    
    Parameters
    ----------
    raw_data : np.ndarray
        1D signal (shape: (n_samples,))
    eps : float
        Threshold for recurrence
    steps : int
        Number of steps for quantization
        
    Returns
    -------
    rp_image : np.ndarray
        Shape (n_samples, n_samples) recurrence plot
    """
    n_samples = len(raw_data)
    rp = np.zeros((n_samples, n_samples))
    
    # Compute pairwise distances and apply threshold
    for i in range(n_samples):
        for j in range(n_samples):
            distance = abs(raw_data[i] - raw_data[j])
            if distance < eps:
                rp[i, j] = 1.0 - (distance / eps)
            else:
                rp[i, j] = 0.0
    
    return rp
from scipy.signal import spectrogram

def create_log_mel_spectrogram(raw_data, fs, target_size=256, n_mels=128, fmin=0.5, fmax=None):
    """
    Creates a log-Mel spectrogram from a raw time-domain waveform.
    Optimized for infrasound identification where transients appear as
    broadband impulses and surf appears as narrowband repetitive energy.

    Parameters
    ----------
    raw_data : np.ndarray
        1D raw time-domain waveform
    fs : float
        Sampling frequency (Hz)
    target_size : int
        Output image dimensions (target_size x target_size)
    n_mels : int
        Number of Mel frequency bands
    fmin : float
        Minimum frequency for Mel filterbank (Hz)
    fmax : float
        Maximum frequency for Mel filterbank (Hz). Defaults to fs/2.

    Returns
    -------
    mel_img : np.ndarray
        Shape (target_size, target_size) normalized log-Mel spectrogram
    """
    if fmax is None:
        fmax = fs / 2.0

    # Longer FFT window for low-frequency infrasound resolution
    n_fft = min(len(raw_data), 256)
    hop_length = max(1, n_fft // 4)

    S = librosa.feature.melspectrogram(
        y=raw_data.astype(np.float32),
        sr=fs,
        n_fft=n_fft,
        hop_length=hop_length,
        n_mels=n_mels,
        fmin=fmin,
        fmax=fmax
    )
    S_db = librosa.power_to_db(S, ref=np.max)

    # Normalize to [0, 1]
    S_norm = (S_db - S_db.min()) / (S_db.max() - S_db.min() + 1e-9)

    # Resize to target and flip so low freq is at bottom
    S_resized = cv2.resize(S_norm, (target_size, target_size), interpolation=cv2.INTER_LINEAR)
    return np.flipud(S_resized)


def create_raw_waveform_gaf(raw_data, target_size=256):
    """
    Creates a Gramian Angular Field directly from the raw time-domain waveform.
    Encodes temporal correlations as angular relationships — preserves waveform
    shape, distinguishing sharp N-wave transients from stochastic surf.

    Parameters
    ----------
    raw_data : np.ndarray
        1D raw time-domain waveform
    target_size : int
        Output GAF image size (target_size x target_size)

    Returns
    -------
    gaf_image : np.ndarray
        Shape (target_size, target_size) normalized GAF image
    """
    # Normalize to [0, 1] for GAF computation
    norm_data = (raw_data - np.min(raw_data)) / (np.max(raw_data) - np.min(raw_data) + 1e-9)
    gaf = GramianAngularField(image_size=target_size, sample_range=(0, 1), method='difference')
    gaf_image = gaf.fit_transform(norm_data.reshape(1, -1))
    return gaf_image[0]  # Shape: (target_size, target_size)


def create_envelope_spectrogram(raw_data, fs, target_size=256):
    """
    Spectrogram of the signal envelope (amplitude modulation).
    Captures temporal energy patterns: transients have sharp single peaks,
    surf has periodic modulation from repeating wave groups.

    Parameters
    ----------
    raw_data : np.ndarray
        1D raw time-domain waveform
    fs : float
        Sampling frequency (Hz)
    target_size : int
        Output image dimensions (target_size x target_size)

    Returns
    -------
    env_img : np.ndarray
        Shape (target_size, target_size) normalized envelope spectrogram
    """
    envelope = np.abs(hilbert(raw_data))

    nperseg = min(len(envelope), 64)
    noverlap = max(0, nperseg - 2)

    f, t, Sxx = spectrogram(envelope, fs=fs, nperseg=nperseg, noverlap=noverlap)
    Sxx_log = 10 * np.log10(Sxx + 1e-10)

    img = (Sxx_log - Sxx_log.min()) / (Sxx_log.max() - Sxx_log.min() + 1e-10)
    img_resized = cv2.resize(img, (target_size, target_size), interpolation=cv2.INTER_LINEAR)
    return np.flipud(img_resized)


def create_freq_band_ratio_image(raw_data, fs, target_size=256, split_freq=2.0):
    """
    Creates a time-resolved frequency band energy ratio image.
    Computes the ratio of low-band to high-band energy over sliding windows.
    Surf concentrates energy in low frequencies (0.1-2 Hz); transients
    distribute energy more evenly across the band.

    Parameters
    ----------
    raw_data : np.ndarray
        1D raw time-domain waveform
    fs : float
        Sampling frequency (Hz)
    target_size : int
        Output image dimensions (target_size x target_size)
    split_freq : float
        Frequency (Hz) dividing low and high bands

    Returns
    -------
    ratio_img : np.ndarray
        Shape (target_size, target_size) normalized band ratio image
    """
    nperseg = min(len(raw_data), 64)
    noverlap = max(0, nperseg - 2)

    f, t, Sxx = spectrogram(raw_data, fs=fs, nperseg=nperseg, noverlap=noverlap)

    low_mask = f <= split_freq
    high_mask = f > split_freq

    low_energy = Sxx[low_mask, :].sum(axis=0) if low_mask.any() else np.zeros(Sxx.shape[1])
    high_energy = Sxx[high_mask, :].sum(axis=0) if high_mask.any() else np.ones(Sxx.shape[1])

    # Ratio per time bin (log scale for better dynamic range)
    ratio = np.log1p(low_energy) / (np.log1p(high_energy) + 1e-9)

    # Tile into a 2D image (ratio varies along time axis, constant along freq axis)
    ratio_2d = np.tile(ratio, (target_size, 1))
    ratio_norm = (ratio_2d - ratio_2d.min()) / (ratio_2d.max() - ratio_2d.min() + 1e-9)
    ratio_resized = cv2.resize(ratio_norm, (target_size, target_size), interpolation=cv2.INTER_LINEAR)
    return ratio_resized


def generate_boom_spectrogram(raw_waveform_512, sr=20, target_size=(256, 256)):
    """
    Generates a Wideband Spectrogram optimized for transient detection.
    Input: raw_waveform_512 (Array of 512 samples)
    Output: Single channel image (256, 256)
    """
    
    # --- 1. The Physics Tuning (Wideband) ---
    # nperseg=32: Short window (~0.3s). Capture the specific moment of the snap.
    # nfft=512: Zero-padding. Forces the math to output 257 frequency rows (Height).
    # noverlap=30: 94% overlap. Creates a dense, smooth time axis.
    f, t, Sxx = spectrogram(
        raw_waveform_512, 
        fs=sr, 
        nperseg=32, 
        nfft=512,      
        noverlap=30    
    )
    
    # --- 2. Log Scale (Decibels) ---
    # Essential. Booms are exponentially louder than surf. 
    # This reveals the "shape" of the sound, not just the peak volume.
    Sxx_log = 10 * np.log10(Sxx + 1e-10)
    
    # --- 3. Normalize [0, 1] ---
    img = (Sxx_log - Sxx_log.min()) / (Sxx_log.max() - Sxx_log.min() + 1e-10)
    
    # --- 4. Resize to Target (256x256) ---
    # We use Linear interpolation to keep the vertical lines (the boom) smooth.
    img_resized = cv2.resize(img, target_size, interpolation=cv2.INTER_LINEAR)
    
    # --- 5. Flip Vertically ---
    # Spectrograms output low-freq at index 0 (top). 
    # We flip so Low Freq is at the Bottom (standard visual format).
    img_final = np.flipud(img_resized)
    
    return img_final

def create_cwt(raw_data: np.array, fs: float, freq_range: tuple, num_freq: int) -> np.ndarray:
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
    cwt_raw = cwt(raw_data, 1/fs, 8, freq_range[0], freq_range[1], nf=num_freq)
    #cwt_log = np.log1p(np.abs(cwt_raw))
    #cwt_norm = (cwt_log - np.min(cwt_log)) / (np.max(cwt_log) - np.min(cwt_log) + 1e-9)
    #h_factor = num_freq / cwt_raw.shape[0]
    #w_factor = num_freq / cwt_raw.shape[1]
    #cwt_data = zoom(cwt_raw, (h_factor, w_factor))
    return cwt_raw

def create_multichannel_features(raw_data, fs, freq_range, target_size, 
                                  include_cwt=False, include_cepstral=False, include_welch=False,
                                  include_mel_spec=False, include_raw_gaf=False, include_envelope=False,
                                  include_band_ratio=False):
    """
    Creates a multi-channel image combining different representations.
    
    All channels are aligned to (target_size, target_size).
    
    Parameters
    ----------
    raw_data : np.array
        1D time-domain signal
    fs : float
        Sampling frequency
    freq_range : tuple
        (min_freq, max_freq) for frequency-domain analyses
    target_size : int
        Output spatial dimensions (target_size x target_size)
    include_cwt : bool
        Include CWT spectrogram channel
    include_cepstral : bool
        Include Cepstral GAF channel
    include_welch : bool
        Include Recurrence Plot channel
    include_mel_spec : bool
        Include Log-Mel Spectrogram channel (recommended for infrasound)
    include_raw_gaf : bool
        Include GAF of raw waveform channel (captures waveform shape)
    include_envelope : bool
        Include Envelope Spectrogram channel (amplitude modulation patterns)
    include_band_ratio : bool
        Include Frequency Band Ratio channel (low vs high energy distribution)
        
    Returns
    -------
    multichannel : np.ndarray
        Shape (target_size, target_size, num_channels)
    """
    channels = []
    
    if include_mel_spec:
        mel_img = create_log_mel_spectrogram(raw_data, fs, target_size=target_size, fmin=freq_range[0], fmax=freq_range[1])
        channels.append(mel_img[:, :, np.newaxis])

    if include_raw_gaf:
        gaf_img = create_raw_waveform_gaf(raw_data, target_size=target_size)
        channels.append(gaf_img[:, :, np.newaxis])

    if include_envelope:
        env_img = create_envelope_spectrogram(raw_data, fs, target_size=target_size)
        channels.append(env_img[:, :, np.newaxis])

    if include_band_ratio:
        ratio_img = create_freq_band_ratio_image(raw_data, fs, target_size=target_size, split_freq=freq_range[0] + (freq_range[1] - freq_range[0]) / 2)
        channels.append(ratio_img[:, :, np.newaxis])

    if include_cwt:
        cwt_img = create_cwt(raw_data, fs, freq_range, target_size)
        channels.append(np.array([cwt_img]).transpose(1, 2, 0))
    
    if include_cepstral:
        norm_data = (raw_data - np.min(raw_data)) / (np.max(raw_data) - np.min(raw_data))
        cep_img = create_welch_gaf(norm_data, n_fft=target_size)
        channels.append(cep_img)

    if include_welch:
        rp_transformer = RecurrencePlot(dimension=1, time_delay=1)
        rp_img = rp_transformer.fit_transform(raw_data.reshape(1, -1))[0]
        channels.append(np.array([rp_img]).transpose(1, 2, 0))

    multichannel = np.concatenate(channels, axis=-1)
    
    return multichannel

"""
Code Starts Here
"""

def create_train_stack(all_entries, fname, pname, inv, window=12.8, target_size=64, stack_size=1, overlap=0, do_mvida=True):
    cl = Client("IRIS")
    X_data = []
    Y_labels = []
    questionable_entries = []
    expected_channels = None
    fft_size = int(window * 20)
    frame_length = window / (stack_size-(stack_size-1)*overlap)
    frame_step = frame_length / (stack_size * (1 - overlap))
    for num, entry in enumerate(all_entries):
        while True:
            print(f"Processed entry {entry['Class']} {num+1}/{len(all_entries)}.")
            try:
                buffer = 20.
                center_time = obspy.UTCDateTime(entry['Time (UTC)']+'Z')
                s_time = center_time - (window/2) - buffer
                e_time = center_time + (window/2) + buffer
                strm_g = cl.get_waveforms(network="IM", station="I59*", location="", channel="BDF", starttime=s_time, endtime=e_time)
                strm = strm_g.copy()
                for tr in strm:
                    #tr.attach_response(inv)
                    #tr.remove_sensitivity()
                    tr.data = tr.data[:int((window+(2*buffer))*20)]
                t_strm = inv_align(strm, inv, entry['Back Azimuth'], entry['Trace Vel. (m/s)'])
                strm = t_strm.copy()
                strm.detrend()
                strm.taper(max_percentage=0.05, type="blackmanharris")
                strm.filter("bandpass", freqmin=0.8, freqmax=8.0, corners=4, zerophase=True)
                #for tr in strm:
                #    tr.data = wavelet_denoise(tr.data, wavelet='db4', level=2, threshold_mode='soft')
                if do_mvida:
                    if entry['Class'] == 'transient':
                        num_versions = 20
                    elif entry['Class'] == 'thunder':
                        num_versions = 20  # Data is limited so we augment using MVIDA
                    else:  # surf
                        num_versions = 12  # Data is limited so we augment using MVIDA
                else:
                    num_versions = 1
                v = 0
                while v < num_versions:
                    """if num > 99:
                        # Testing and Validation data should not be augmented.
                        v = num_versions-1
                        current_strm = strm.copy()
                        single_strm = generate_high_quality_trace(current_strm)"""
                    if v == 0:
                        current_strm = strm.copy()
                        single_strm = generate_high_quality_trace(current_strm)
                    else:
                        ref_sensor = strm[0]
                        comp_sensors = strm[1:]

                        random.shuffle(comp_sensors)
                        strm_list = obspy.Stream(ref_sensor) + comp_sensors
                        shuffled_strm = obspy.Stream(traces=strm_list)
                        single_strm = apply_mvida_to_stream(shuffled_strm)

                    if isinstance(single_strm, obspy.Stream):
                        current_strm = single_strm.copy()
                    else:
                        current_strm = obspy.Stream(traces=[single_strm])

                    peak_strm = current_strm.slice(starttime=center_time - (window/2), endtime=center_time + ((window/2)))
                    pasc_max = np.abs(peak_strm[0].data)
                    peak_index = peak_strm[0].times("utcdatetime")[np.argmax(pasc_max)]
                    peak_time = obspy.UTCDateTime(round(peak_index.timestamp))
                    final_start = peak_time - (window / 2)
                    final_end = peak_time + (window / 2)

                    current_strm.trim(starttime=final_start, endtime=final_end, pad=False)
                    
                    for i in range(stack_size):
                        # Because we are using this data for ConvLTSM we split the window into multiple frames to see how it changes over time/space
                        t_start = final_start + (i * frame_step)
                        t_end = t_start + frame_length
                        strm_window = current_strm.copy()
                        strm_window.trim(starttime=t_start, endtime=t_end, pad=True)
                        if len(strm_window) == 0:
                            raise ValueError("Windowing produced an empty stream")

                        # Ensure all traces in the window are exactly fft_size samples.
                        for tr in strm_window:
                            data = tr.data
                            if len(data) > fft_size:
                                tr.data = data[:fft_size]
                            elif len(data) < fft_size:
                                pad_width = fft_size - len(data)
                                tr.data = np.pad(data, (0, pad_width), mode='constant')

                        """
                            strm_window[0].data = np.pad(data, (0, pad_width), 'constant')
                        # Create 2-channel image: CWT + Cepstral GAF
                        target_size = fft_size  # e.g., 128 for fft_size=512
                        multichannel_img = create_multichannel_features(
                            raw_data=strm_window[0].data,
                            fs=strm_window[0].stats.sampling_rate,
                            freq_range=(.8, 8.0),
                            target_size=target_size,
                            include_cwt=True,
                            include_cepstral=False,
                            include_welch=False
                        )  # Shape: (target_size, target_size, 2)
                        
                    X_data.append(multichannel_img)"""
                        raw_cwt = []
                        for tr in strm_window:
                            cwt_complex = create_cwt(raw_data=tr.data, fs=20, freq_range=(.8, 8.0), num_freq=fft_size)
                            cwt_mag = np.abs(cwt_complex)
                            """if v == 0:
                                if np.max(cwt_mag) < .01 and entry['Class'] == 'transient':
                                    print("Magnitude Warning: ", np.max(cwt_mag), entry['Class'], num+1)
                                    questionable_entries.append([entry['Class'], entry['Back Azimuth'], np.max(cwt_mag)])
                                elif np.max(cwt_mag) > .01 and entry['Class'] == 'surf':
                                    print("Magnitude Warning: ", np.max(cwt_mag), entry['Class'], num+1)
                                    questionable_entries.append([entry['Class'], entry['Back Azimuth'], np.max(cwt_mag)])"""
                            cwt_log = np.log1p(cwt_mag)
                            cwt_norm = (cwt_log - cwt_log.min()) / (cwt_log.max() - cwt_log.min() + 1e-10)
                            raw_cwt.append(cwt_norm)
                        #cwt_gaf = np.concatenate((raw_cwt, gaf_data), axis=0)
                        #cwt_gaf = np.concatenate(raw_cwt, axis=0)
                        #gaf_sequence.append(mtf)
                    if(1):
                        sample = np.asarray(raw_cwt, dtype=np.float32).transpose(1, 2, 0)

                        # Keep channel count consistent across all samples.
                        if expected_channels is None:
                            expected_channels = sample.shape[-1]
                        elif sample.shape[-1] != expected_channels:
                            if sample.shape[-1] > expected_channels:
                                sample = sample[:, :, :expected_channels]
                            else:
                                pad_ch = expected_channels - sample.shape[-1]
                                sample = np.pad(sample, ((0, 0), (0, 0), (0, pad_ch)), mode='constant')

                        if target_size is not None and (sample.shape[0] != target_size or sample.shape[1] != target_size):
                            sample = cv2.resize(sample, (target_size, target_size), interpolation=cv2.INTER_LINEAR)
                            if sample.ndim == 2:
                                sample = np.expand_dims(sample, axis=-1)

                    X_data.append(sample)  # Shape: (target_size, target_size, channels)
                    Y_labels.append(entry['Class'])
                    v += 1
                print(f"Dataset size: {len(X_data)}")
                break
            except Exception as e:
                print(f"Error processing entry {num+1}: {e}. Retrying...")
                continue
    X_train = np.array(X_data)  # Shape: (samples, height, width, channels)
    Y_train = np.array(Y_labels)
    print(f"Sample shape: {X_train[0].shape}")
    print(f"First label: {Y_train[0]}")

    np.save(os.path.join(pname, f'X_{fname}.npy'), X_train)
    np.save(os.path.join(pname, f'Y_{fname}.npy'), Y_train)

    print("Serialization Complete.")
    print(f"Final X Data Shape: {X_train.shape}")
    print(f"Final Y Data Shape: {Y_train.shape}")

    print("Questionable Entries (Class, Back Azimuth, Max CWT Mag): ")
    for entry in questionable_entries:
        print(entry)

if __name__ == "__main__":
    path = os.getcwd() + '/sandbox/identification/'
    rel_path = os.path.join(path, 'training', 'numpy')
    cl = Client("IRIS")
    with open(path+'training/json/merged_detections.json', 'r') as f:
        detections = json.load(f)
    inv = obspy.read_inventory(path+'training/I59US_station.xml')
    all_entries = detections
    np.random.shuffle(all_entries)
    labels_for_splitting = [x['Class'] for x in all_entries]
    # Split data into train, test, val sets (70%, 15%, 15%)
    train_entries, testval_entries = train_test_split(
        all_entries,
        test_size=0.3,          
        random_state=42,
        shuffle=True,
        stratify=labels_for_splitting 
    )
    labels_testval = [x['Class'] for x in testval_entries]
    test_entries, val_entries = train_test_split(
        testval_entries,
        test_size=0.5,
        random_state=42,
        shuffle=True,
        stratify=labels_testval
    )
    
    create_train_stack(train_entries, 'train', rel_path, inv, window=38.4, target_size=384, stack_size=1, overlap=0, do_mvida=True)
    create_train_stack(test_entries, 'test', rel_path, inv, window=38.4, target_size=384, stack_size=1, overlap=0, do_mvida=False)
    create_train_stack(val_entries, 'val', rel_path, inv, window=38.4, target_size=384, stack_size=1, overlap=0, do_mvida=True)