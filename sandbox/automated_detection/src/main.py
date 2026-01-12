import configparser
import json
import os
import sys
import time

import numpy as np
import obspy
from obspy import UTCDateTime
from obspy.clients.fdsn import Client
from obspy.clients.seedlink import Client as Client_seedlink

import logging
import traceback
# InfraPy imports
from infrapy.detection import beamforming_new as fkd
from infrapy.utils import config as infraconfig
from infrapy.utils import data_io


# User defined variables
USER_CONFIG = configparser.ConfigParser()
root_path = os.path.join(os.getcwd())
config_path = os.path.join(root_path, 'config', 'example.ini')
if not os.path.exists(config_path):
    print(f"Config file not found, check for file at {config_path}")
    exit(1)
USER_CONFIG.read(config_path)
wf_client = 0  # Flag to pull data from IRIS (0) or seedlink (1) NOTE: If 1 ensure WiFi is ISLA_CF_5g
if wf_client:
    LOCAL_SEEDLINK = "192.168.112.200"
    client = Client_seedlink(LOCAL_SEEDLINK, port=18000, timeout=180)
else:
    client = Client("IRIS")

real_time = False  # Flag to for static time frame (False) or real-time processing (True)
nrt_stime = obspy.UTCDateTime("2025-10-31T11:58:00.000000Z")
end_time = obspy.UTCDateTime("2026-01-07T19:30:00.000000Z")
sig_len_secs = 600  # Seconds
overlap_perc = 0.2  # Fractional overlap between time windows
logging.basicConfig(
    filename=os.path.join(root_path, 'results', 'bin', "error.log"),
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.ERROR
)

# Define Event Parameters
EVENT_CONFIG = {
    "name": "auto_infrapy_test",
    "network": "IM",
    "station": "I59*",
    "location": "",
    "channel": "BDF",
    "start_time": (
        obspy.UTCDateTime() - ((2 * sig_len_secs) + 120) if (real_time) else nrt_stime -
            (sig_len_secs * (1 - overlap_perc))
    ),
    "end_time": (
        obspy.UTCDateTime() - (sig_len_secs + 120) if (real_time) else nrt_stime
    ),
}
EVENT_NAME = EVENT_CONFIG["name"]
NETWORK = EVENT_CONFIG["network"]
STATION = EVENT_CONFIG["station"]
LOCATION = EVENT_CONFIG["location"]
CHANNEL = EVENT_CONFIG["channel"]
t1 = EVENT_CONFIG["start_time"]
t2 = EVENT_CONFIG["end_time"]


if __name__ == "__main__":
    """
    Main entry point for automated infrasonic detection using InfraPy
    """
    # Beamforming Parameters
    freq_min: float = infraconfig.get_param(USER_CONFIG, "FK", "freq_min", None, "float")              # type: ignore
    freq_max: float = infraconfig.get_param(USER_CONFIG, "FK", "freq_max", None, "float")              # type: ignore
    back_az_min: float = infraconfig.get_param(USER_CONFIG, "FK", "back_az_min", None, "float")        # type: ignore
    back_az_max: float = infraconfig.get_param(USER_CONFIG, "FK", "back_az_max", None, "float")        # type: ignore
    back_az_step: float = infraconfig.get_param(USER_CONFIG, "FK", "back_az_step", None, "float")      # type: ignore
    trace_vel_min: float = infraconfig.get_param(USER_CONFIG, "FK", "trace_vel_min", None, "float")    # type: ignore
    trace_vel_max: float = infraconfig.get_param(USER_CONFIG, "FK", "trace_vel_max", None, "float")    # type: ignore
    trace_vel_step: float = infraconfig.get_param(USER_CONFIG, "FK", "trace_vel_step", None, "float")  # type: ignore
    method: str = infraconfig.get_param(USER_CONFIG, "FK", "method", None, "string")                   # type: ignore
    signal_start: UTCDateTime = UTCDateTime(0)
    t = infraconfig.get_param(USER_CONFIG, "FK", "signal_start", None, "string")                       # type: ignore
    if t is not None:
        signal_start = obspy.UTCDateTime(t)
    signal_end: UTCDateTime = UTCDateTime(0)
    t = infraconfig.get_param(USER_CONFIG, "FK", "signal_end", None, "string")                         # type: ignore
    if t is not None:
        signal_end = obspy.UTCDateTime(t)
    noise_start: UTCDateTime = UTCDateTime(0)
    t = infraconfig.get_param(USER_CONFIG, "FK", "noise_start", None, "string")                        # type: ignore
    if t is not None:
        noise_start = obspy.UTCDateTime(t)
    noise_end: UTCDateTime = UTCDateTime(0)
    t = infraconfig.get_param(USER_CONFIG, "FK", "noise_end", None, "string")                          # type: ignore
    if t is not None:
        noise_end = obspy.UTCDateTime(t)
    window_len: float = infraconfig.get_param(USER_CONFIG, "FK", "window_len", None, "float")          # type: ignore
    sub_window_len: float = infraconfig.get_param(USER_CONFIG, "FK", "sub_window_len", None, "float")  # type: ignore
    window_step: float = infraconfig.get_param(USER_CONFIG, "FK", "window_step", None, "float")        # type: ignore
    cpu_cnt: int = infraconfig.get_param(USER_CONFIG, "FK", "cpu_cnt", None, "int")                    # type: ignore

    # Detection parameters
    fd_window_len: float = infraconfig.get_param(USER_CONFIG, "FD", "window_len", None, "float")       # type: ignore
    p_value: float = infraconfig.get_param(USER_CONFIG, "FD", "p_value", None, "float")                # type: ignore
    min_duration: float = infraconfig.get_param(USER_CONFIG, "FD", "min_duration", None, "float")      # type: ignore
    back_az_width: float = infraconfig.get_param(USER_CONFIG, "FD", "back_az_width", None, "float")    # type: ignore
    fixed_thresh: float = infraconfig.get_param(USER_CONFIG, "FD", "fixed_thresh", None, "float")      # type: ignore
    thresh_ceil: float = infraconfig.get_param(USER_CONFIG, "FD", "thresh_ceil", None, "float")        # type: ignore
    return_thresh: bool = infraconfig.get_param(USER_CONFIG, "FD", "return_thresh", None, "bool")      # type: ignore
    # NOTE: Merge detections currently needs to be improved. Should investigate how they associate nearby detections
    # (time window, etc).
    merge_dets: bool = infraconfig.get_param(USER_CONFIG, "FD", "merge_dets", None, "bool")            # type: ignore

    """
    This section runs an automated infrasonic detection using InfraPy's beamforming and detection modules.
    It will pull data from either IRIS or a local seedlink server, process it in overlapping time windows,
    and save detections and raw data to specified directories. Please update them to match the intended directories.
    """
    # Generate Noise and Get Inventory
    inventory = None
    # Try to load inventory from XML file first
    try:
        inv_file = os.path.join(root_path, 'config', 'I59US_station.xml')
        inventory = obspy.read_inventory(inv_file)
        print(f"Loaded inventory from {inv_file}")
    except Exception as e:
        # If no XML file load from IRIS
        print(f"could not load from .xml file Exception: {e}")
        logging.error("".join(traceback.format_exception(type(e), e, e.__traceback__)))
        try:
            inventory = client.get_stations(
                network=NETWORK,
                station=STATION,
                location=LOCATION,
                channel=CHANNEL,
                starttime=t1,
                endtime=t2,
                level="response",
            )
        except Exception as e:
            # no inventory means we need to exit
            print(f"Error {e} fetching data from FDSN client. Please check network/station codes and time range.")
            logging.error("".join(traceback.format_exception(type(e), e, e.__traceback__)))
            logging.shutdown()
            sys.exit(1)

    # Get Baseline Noise Data
    print("Fetching baseline noise data")
    try:
        n_stream = client.get_waveforms(
            network=NETWORK,
            location=LOCATION,
            station=STATION,
            channel=CHANNEL,
            starttime=t1,
            endtime=t2,
        )
    except Exception as e:
        print(f"Error fetching base waveforms. Exception: {e}")
        logging.error("".join(traceback.format_exception(type(e), e, e.__traceback__)))
        logging.shutdown()
        sys.exit(1)

    # Load station coordinates into stream
    latlon = []
    for tr in n_stream:
        coords = inventory.get_coordinates(
            f"{NETWORK}.{tr.stats.station}.{LOCATION}.{CHANNEL}", t1
        )
        latlon.append((coords["latitude"], coords["longitude"]))
        print(tr.stats.starttime, tr.stats.station)
    print(f"Fetched {len(n_stream)} traces from {NETWORK}.{STATION}.")
    # Calculate array geometry and dependencies
    # array_lat = [np.mean(lc[0] for lc in latlon)]
    # array_lon = [np.mean(lc[1] for lc in latlon)]
    centroid = np.mean([lat for lat, lon in latlon]), np.mean([lon for lat, lon in latlon])
    array_lat, array_lon = centroid
    TB_prod = (freq_max - freq_min) * window_len
    back_az_vals = np.arange(back_az_min, back_az_max, back_az_step)
    trc_vel_vals = np.arange(trace_vel_min, trace_vel_max, trace_vel_step)
    n_x, n_t, n_t0, geom = fkd.stream_to_array_data(n_stream, latlon=latlon)
    slowness = fkd.build_slowness(back_az_vals, trc_vel_vals)
    delays = fkd.compute_delays(geom, slowness)

    # If no fixed threshold compute initial threshold based on noise
    if (not fixed_thresh):
        thresh = fkd.adjust_thresh_noise(
            (n_x, n_t, n_t0, geom),
            window_len,
            sub_window_len,
            (sig_len_secs * (1 - overlap_perc)),
            window_step,
            freq_min,
            freq_max,
            method,
            back_az_vals,
            trc_vel_vals,
            delays,
            p_value,
            TB_prod,
        )
    else:
        thresh = fixed_thresh
    prev_thresh = 0
    new_thresh = 0
    dets_found = False
    i = 0
    stop_time = t1

    # Initialize loop for processing time windows
    print("Beginning automated detection processing")
    while True:
        try:
            stop_watch = time.time()
            if (not dets_found):
                noise_start = t1
                noise_end = t1 + (sig_len_secs * (1 - overlap_perc))
            t1 = obspy.UTCDateTime() - (sig_len_secs + 120) if (real_time) else nrt_stime + \
                (i * (sig_len_secs * (1 - overlap_perc)))
            t2 = obspy.UTCDateTime() - 120 if (real_time) else nrt_stime + \
                (i * (sig_len_secs * (1 - overlap_perc))) + sig_len_secs
            stop_time = t2

            # Get waveforms from IRIS or seedlink
            try:
                g_stream = client.get_waveforms(
                    network=NETWORK,
                    location=LOCATION,
                    station=STATION,
                    channel=CHANNEL,
                    starttime=t1,
                    endtime=t2,
                )
                print(f"Fetched {len(g_stream)} traces from {NETWORK}.{STATION}.")
                if (not len(g_stream)):
                    print("Error fetching waveforms. Moving onto next iteration")
                    i += 1
                    continue
                str_name = f"{EVENT_NAME}_{t1.strftime('%Y%m%d_%H%M%S')}"
                print(f"Iteration {i}")

                # Begin beamforming on stream
                strm = g_stream.copy()
                x, t, t0, _ = fkd.stream_to_array_data(strm, latlon=latlon)
                M, N = x.shape
                print(f"Running {method} beamforming from {t1} to {t2}")
                beam_times, beam_peaks, beam_power = fkd.auto_run_bf(
                    0,
                    t2 - t1,
                    freq_band=[freq_min, freq_max],
                    window_len=window_len,
                    sub_window_len=sub_window_len,
                    window_step=window_step,
                    method=method,
                    back_az_vals=back_az_vals,
                    trc_vel_vals=trc_vel_vals,
                    array_data=(x, t, t0, geom),
                    delays=delays,
                )

                # Determine threshold; if not fixed adjust threshold based on previous detections
                if fixed_thresh:
                    thresh = fixed_thresh
                else:
                    # If detections were found thresh will be the same as previous valid fstat thresh. If not recompute
                    print("Adjusting threshold based on noise")
                    if dets_found:
                        thresh = prev_thresh
                    else:
                        thresh = new_thresh

                # Run detection
                print(f"Running FD detection from {t1} to {t2}\nNoise Window: {noise_start} to {noise_end}")
                min_seq = int(max(2, min_duration / (window_step)))
                det_results = fkd.run_fd(
                    beam_times,
                    beam_peaks,
                    window_len,
                    int(TB_prod),
                    len(strm),
                    p_value,
                    min_seq,
                    back_az_width,
                    thresh,
                    thresh_ceil,
                    return_thresh,
                    merge_dets,
                )
                det_list = []
                for det_info in det_results[0]:
                    det = data_io.define_detection(
                        det_info,
                        [array_lat, array_lon],
                        len(strm),
                        [freq_min, freq_max],
                        note="Automated run",
                        method=method,
                    )
                    det_list.append(det)
                print("Detection Complete")

                # Save detections
                if len(det_list) > 0:
                    det_fpath = os.path.join(root_path, 'results', t1.strftime("%Y/%m/%d/"))
                    try:
                        if not os.path.isdir(det_fpath):
                            print("Making New Folder")
                            os.makedirs(det_fpath, exist_ok=True)
                    except Exception as e:
                        logging.error("".join(traceback.format_exception(type(e), e, e.__traceback__)))
                        print(f"Error making folder, please investigate issues: {e}")
                        det_fpath = os.path.join(root_path, 'results', 'bin')
                    det_out = os.path.join(det_fpath, f"{str_name}_detections.json")
                    dets_found = True
                    prev_thresh = thresh
                    print(
                        f"Found {len(det_list)} detections, writing to {det_out} ; New Threshold: {prev_thresh}"
                    )
                    str_info = [
                        strm[0].stats.network,
                        f"{strm[0].stats.station}-{strm[-1].stats.station}",
                        strm[0].stats.channel,
                    ]
                    data_io.detection_list_to_json(det_out, det_list, str_info)
                    with open(det_out, "r") as f:
                        dets_data = json.load(f)
                    for det in dets_data:
                        det["Name"] = str_name
                        det["Latitude"] = array_lat
                        det["Longitude"] = array_lon
                        det["Signal"] = f"{t1} to {t2}"
                        det["Noise"] = f"{noise_start} to {noise_end}"
                        det["F-Stat Threshold"] = thresh

                    with open(det_out, "w") as f:
                        json.dump(dets_data, f, indent=4)

                    # If there is a detection save off all raw data
                    dt = np.array(
                        [
                            (tn - np.datetime64(strm[0].stats.starttime))
                            .astype("m8[ms]")
                            .astype(float)
                            * 1.0e-3
                            for tn in beam_times
                        ]
                    )
                    raw_data = np.hstack((np.atleast_2d(dt).T, beam_peaks))
                    rd_header = data_io.fk_header(
                        strm,
                        latlon,
                        freq_min,
                        freq_max,
                        back_az_min,
                        back_az_max,
                        back_az_step,
                        trace_vel_min,
                        trace_vel_max,
                        trace_vel_step,
                        method,
                        t1,
                        t2,
                        noise_start,
                        noise_end,
                        window_len,
                        sub_window_len,
                        window_step,
                    )

                    rd_out = os.path.join(det_fpath, f"{str_name}_raw_data.txt")
                    np.savetxt(rd_out, raw_data, header=rd_header)
                    print(f"  Wrote FK results to {rd_out}")
                else:
                    print("No detections found")
                    dets_found = False
                    if (not fixed_thresh):
                        print("Recalculating threshold based on noise")
                        new_thresh = fkd.adjust_thresh_noise(
                            (x, t, t0, geom),
                            window_len,
                            sub_window_len,
                            (sig_len_secs * (1 - overlap_perc)),
                            window_step,
                            freq_min,
                            freq_max,
                            method,
                            back_az_vals,
                            trc_vel_vals,
                            delays,
                            p_value,
                            TB_prod,
                        )
                        print(f"New Threshold: {new_thresh}")
                    else:
                        new_thresh = fixed_thresh
                if real_time:
                    T = time.time() - stop_watch
                    print(
                        f"Sleeping for {(sig_len_secs * (1 - overlap_perc)) - T} seconds until "
                        f"{obspy.UTCDateTime() + ((sig_len_secs * (1 - overlap_perc)) - T) - 36000} (HST)"
                    )
                    time.sleep((sig_len_secs * (1 - overlap_perc)) - T)
            except Exception as e:
                print(f"Error fetching data. Exception: {e}")
                logging.error("".join(traceback.format_exception(type(e), e, e.__traceback__)))
        except Exception as e:
            # Print to output any errors and continue to next time window
            print(f"{obspy.UTCDateTime()}: Error in detection processing: {e}")
            logging.error("".join(traceback.format_exception(type(e), e, e.__traceback__)))
        i += 1  # increment iteration
logging.shutdown()
sys.exit(0)
