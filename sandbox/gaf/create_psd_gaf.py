import numpy as np
from scipy import signal
import matplotlib.pyplot as plt
import obspy
from obspy.clients.fdsn import Client
import pandas as pd
from typing import List, Tuple

# "Signal": "2025-12-17T19:58:29.538474Z to 2025-12-17T20:08:29.538474Z",
# "Noise": "2025-12-17T19:50:29.538474Z to 2025-12-17T19:58:29.538474Z",



def min_max_normalize(signal: np.array):
    # scale to [-1, 1]
    min_value = np.min(signal)
    max_value = np.max(signal)
    return (2 * (signal - min_value) / (max_value - min_value)) - 1

def GAF(signal: np.array, summation: bool = True):
    normalized_signal = min_max_normalize(signal=signal)
    normalized_signal = np.clip(normalized_signal, -1.0 + 1e-6, 1.0 - 1e-6)  # avoid arccos edge artifacts
    polar_signal = np.arccos(normalized_signal)

    if summation:
        return np.cos(polar_signal[:, None] + polar_signal[None, :])
    return np.sin(polar_signal[:, None] - polar_signal[None, :])

def plot_gaf(gaf, title: str = 'Gramian Angular Field'):
    plt.figure(figsize=(4, 4))
    plt.imshow(gaf, cmap='rainbow', origin='upper')
    plt.title(title)
    plt.colorbar()
    plt.show()


def latlon_to_xy(ref_lat: float, ref_lon: float, lats: List[float], lons: List[float]) -> List[Tuple[float, float]]:
    """Approximate local ENU offsets (meters) from lat/lon pairs."""
    # Simple equirectangular approximation, adequate for small arrays (< ~50 km)
    lat_rad = np.deg2rad(ref_lat)
    m_per_deg_lat = 111320.0
    m_per_deg_lon = 111320.0 * np.cos(lat_rad)
    xs = (np.array(lons) - ref_lon) * m_per_deg_lon
    ys = (np.array(lats) - ref_lat) * m_per_deg_lat
    return list(zip(xs, ys))


def delaysum_bf(data_list: List[np.ndarray], coords_xy: List[Tuple[float, float]], baz_deg: float, celerity: float, fs: float, method: str = "mean") -> np.ndarray:
    """Delay-and-sum beamformer given back-azimuth and celerity."""
    baz_rad = np.deg2rad(baz_deg)
    sx, sy = np.sin(baz_rad) / celerity, np.cos(baz_rad) / celerity
    delays = [sx * x + sy * y for x, y in coords_xy]  # seconds

    t = np.arange(len(data_list[0])) / fs
    shifted = []
    for d, dt in zip(data_list, delays):
        shifted.append(np.interp(t, t + dt, d, left=0.0, right=0.0))

    stacked = np.vstack(shifted)
    if method == "median":
        return np.median(stacked, axis=0)
    return stacked.mean(axis=0)






# Trim all traces to common window and sort
def prep_stream(st: obspy.Stream):
    st.sort(keys=["station", "channel"])
    t0 = max(tr.stats.starttime for tr in st)
    t1 = min(tr.stats.endtime for tr in st)
    st.trim(t0, t1, pad=True, fill_value=0.0)
    st.detrend("demean").detrend("linear")
    return st

# Build coordinate list and data arrays
def collect_array_data(st: obspy.Stream):
    data_list, coords = [], []
    if len(st) == 0:
        return data_list, coords, None
    ref_latlon = None
    for tr in st:
        key = (tr.stats.network, tr.stats.station, tr.stats.channel)
        if key not in sta_coords:
            continue
        lat, lon = sta_coords[key]
        if ref_latlon is None:
            ref_latlon = (lat, lon)
        data_list.append(tr.data)
        coords.append((lat, lon))
    if ref_latlon is None:
        return [], [], None
    xs_ys = latlon_to_xy(ref_latlon[0], ref_latlon[1], [c[0] for c in coords], [c[1] for c in coords])
    return data_list, xs_ys, st[0].stats.sampling_rate








det_time = obspy.UTCDateTime('2025-12-16T21:47:03.000000Z')
start = det_time - 8
end = det_time + 8
n_start = obspy.UTCDateTime('2025-12-17T19:50:29.538474Z')
n_end = n_start + 16
# Beamform using known back-azimuth and assumed celerity
baz_deg = -84.08  # set from detection
celerity = 371.57  # m/s

cl = Client("IRIS")

# Fetch signal and noise streams (all array channels)
strm = cl.get_waveforms(network="IM", station="I59*", location="", channel="BDF", starttime=start, endtime=end)
n_strm = cl.get_waveforms(network="IM", station="I59*", location="", channel="BDF", starttime=n_start, endtime=n_end)
strm = prep_stream(strm)
n_strm = prep_stream(n_strm)

# Pull station coordinates from metadata
inv = cl.get_stations(network="IM", station="I59*", channel="BDF", starttime=start, endtime=end, level="channel")
sta_coords = {}
for net in inv:
    for sta in net:
        lat, lon = sta.latitude, sta.longitude
        for ch in sta:
            sta_coords[(net.code, sta.code, ch.code)] = (lat, lon)


data_sig, coords_sig, fs = collect_array_data(strm)
data_noise, coords_noise, _ = collect_array_data(n_strm)

# Apply bandpass consistently before beamforming
bp_kwargs = dict(freqmin=1.0, freqmax=8.0, corners=4, zerophase=True)
for tr in strm:
    tr.filter("bandpass", **bp_kwargs)
for tr in n_strm:
    tr.filter("bandpass", **bp_kwargs)
    fs = strm[0].stats.sampling_rate


if len(data_sig) >= 2:
    sig_beam = delaysum_bf(data_sig, coords_sig, baz_deg, celerity, fs, method="mean")
    noise_beam = delaysum_bf(data_noise, coords_noise, baz_deg, celerity, fs, method="mean")
else:
    sig_beam = data_sig[0]
    noise_beam = data_noise[0]

plt.plot(sig_beam)
plt.title('Beamformed Signal Trace')

window = "hann"          # matches InfraView defaults
# Use the same nperseg for signal/noise to keep frequency bins aligned
nperseg = min(1024, len(sig_beam), len(noise_beam))
if nperseg < 8:
    raise ValueError("Not enough samples for Welch PSD")
noverlap = nperseg // 2

f, pxx = signal.welch(sig_beam, fs=fs, window=window, nperseg=nperseg, noverlap=noverlap)
n_f, n_pxx = signal.welch(noise_beam, fs=fs, window=window, nperseg=nperseg, noverlap=noverlap)
pxx_db = 10.0 * np.log10(pxx)
n_pxx_db = 10.0 * np.log10(n_pxx)
# Plot PSD (log frequency, dB amplitude)
plt.figure(figsize=(10, 6))
plt.semilogx(f, pxx_db)
plt.semilogx(n_f, n_pxx_db, color='orange')
plt.title("Power Spectral Density (PSD)")
plt.xlabel("Frequency [Hz]")
plt.ylabel("Power/Frequency [dB/Hz]")
plt.xlim(.1, 8)
plt.grid(True, which="both")
plt.show()

# Build GAFs from log-compressed, smoothed, downsampled PSDs for stability
def prep_for_gaf(pxx_linear: np.array, smooth: int = 5, target_len: int = 256):
    pxx_db_local = 10.0 * np.log10(pxx_linear)
    # median smooth to knock down spikes
    if smooth > 1:
        pxx_db_local = pd.Series(pxx_db_local).rolling(window=smooth, center=True, min_periods=1).median().to_numpy()
    # downsample to fixed length
    if len(pxx_db_local) > target_len:
        idx = np.linspace(0, len(pxx_db_local) - 1, target_len).astype(int)
        pxx_db_local = pxx_db_local[idx]
    return pxx_db_local

def prep_band(series: np.ndarray, freqs: np.ndarray, band: Tuple[float, float]) -> np.ndarray:
    mask = (freqs >= band[0]) & (freqs <= band[1])
    return series[mask]

# Configurable knobs for CNN-friendly inputs
freq_band = (1.0, 8.0)   # focus band
smooth_win = 3       # median window for PSD smoothing
target_len = 256         # fixed length fed to GAF/CNN

pxx_band = prep_band(pxx, f, freq_band)
n_pxx_band = prep_band(n_pxx, n_f, freq_band)

sig_series = prep_for_gaf(pxx_band, smooth=smooth_win, target_len=target_len)
noise_series = prep_for_gaf(n_pxx_band, smooth=smooth_win, target_len=target_len)

# PSD ratio (signal / noise) to boost contrast
eps = 1e-12
ratio_series = prep_for_gaf((pxx_band / (n_pxx_band + eps)), smooth=smooth_win, target_len=target_len)

sig_gasf = GAF(signal=sig_series, summation=True)
plot_gaf(sig_gasf, title='Signal GASF')
sig_gadf = GAF(signal=sig_series, summation=False)
plot_gaf(sig_gadf, title='Signal GADF')

noise_gasf = GAF(signal=noise_series, summation=True)
plot_gaf(noise_gasf, title='Noise GASF')
noise_gadf = GAF(signal=noise_series, summation=False)
plot_gaf(noise_gadf, title='Noise GADF')

ratio_gasf = GAF(signal=ratio_series, summation=True)
plot_gaf(ratio_gasf, title='PSD Ratio GASF')
ratio_gadf = GAF(signal=ratio_series, summation=False)
plot_gaf(ratio_gadf, title='PSD Ratio GADF')