import os
import configparser
import obspy
from obspy.core.util import AttribDict
from obspy.clients.fdsn import Client
from obspy.clients.seedlink import Client as Client_seedlink
import numpy as np
import time
import json
# InfraPy imports
from infrapy.utils import data_io
from infrapy.detection import beamforming_new as fkd
from infrapy.utils import config as infraconfig
# User defined variables
user_config = configparser.ConfigParser()
user_config.read("../config/example.ini")
wf_client = 1  # Flag to pull data from IRIS (0) or seedlink (1) NOTE: If 1 ensure WiFi is ISLA_CF_5g
real_time = 1  # Flag to for static time frame (0) or real-time processing (1)
LOCAL_SEEDLINK = "192.168.112.200"
nrt_stime = obspy.UTCDateTime("2025-12-10T18:30:00.000000Z")
nrt_etime = obspy.UTCDateTime("2025-12-10T19:30:00.000000Z")


def cfg(param_section: str, param_name: str, dtype: str = "float", cli_val=None):
    """
    Helper to pull params from InfraPy user config

    :param param_section: Section in config file
    :param param_name: Parameter name
    :param dtype: Data type of parameter (float, int, bool, str)
    :param cli_val: Value from command line interface
    :return: Parameter value
    """
    return infraconfig.get_param(user_config, param_section, param_name, cli_val, dtype)


if __name__ == "__main__":
    """
    Main entry point for automated infrasonic detection using InfraPy
    """
    # Beamforming Parameters
    freq_min = cfg("FK", "freq_min", "float")
    freq_max = cfg("FK", "freq_max", "float")
    back_az_min = cfg("FK", "back_az_min", "float")
    back_az_max = cfg("FK", "back_az_max", "float")
    back_az_step = cfg("FK", "back_az_step", "float")
    trace_vel_min = cfg("FK", "trace_vel_min", "float")
    trace_vel_max = cfg("FK", "trace_vel_max", "float")
    trace_vel_step = cfg("FK", "trace_vel_step", "float")
    method = infraconfig.get_param(user_config, "FK", "method", None, "string")
    signal_start = infraconfig.get_param(user_config, "FK", "signal_start", None, "string")
    signal_end = infraconfig.get_param(user_config, "FK", "signal_end", None, "string")
    noise_start = infraconfig.get_param(user_config, "FK", "noise_start", None, "string")
    noise_end = infraconfig.get_param(user_config, "FK", "noise_end", None, "string")
    window_len = cfg("FK", "window_len", "float")
    sub_window_len = cfg("FK", "sub_window_len", "float")
    window_step = cfg("FK", "window_step", "float")
    cpu_cnt = infraconfig.get_param(user_config, "FK", "cpu_cnt", None, "int")

    # Detection parameters
    fd_window_len = cfg("FD", "window_len", "float")
    p_value = cfg("FD", "p_value", "float")
    min_duration = cfg("FD", "min_duration", "float")
    back_az_width = cfg("FD", "back_az_width", "float")
    fixed_thresh = cfg("FD", "fixed_thresh", "float")
    thresh_ceil = cfg("FD", "thresh_ceil", "float")
    return_thresh = (
        infraconfig.get_param(user_config, "FD", "return_thresh", None, "bool") or False
    )
    # NOTE: Merge detections currently needs to be improved. Should investigate how they associate nearby detections
    # (time window, etc).
    merge_dets = (
        infraconfig.get_param(user_config, "FD", "merge_dets", None, "bool") or True
    )
    """
    This section runs an automated infrasonic detection using InfraPy's beamforming and detection modules.
    It will pull data from either IRIS or a local seedlink server, process it in overlapping time windows,
    and save detections and raw data to specified directories. Please update them to match the intended directories.
    """
    i = 0
    # Currently using while loop for simplicity, ideally would be updated with a start/stop callback to interrupt
    while i < 600:
        stop_watch = time.time()
        # Adding event params
        EVENT_CONFIG = {
            "name": "auto_infrapy_test",
            "network": "IM",
            "station": "I59*",
            "location": "",
            "channel": "BDF",
            "start_time": (
                obspy.UTCDateTime() - 720 if (real_time) else nrt_stime
            ),
            "end_time": (
                obspy.UTCDateTime() - 120 if (real_time) else nrt_etime
            ),
        }

        # Set parameters from the event config
        name = EVENT_CONFIG["name"]
        network = EVENT_CONFIG["network"]
        station = EVENT_CONFIG["station"]
        location = EVENT_CONFIG["location"]
        channel = EVENT_CONFIG["channel"]
        if not i:
            t1 = EVENT_CONFIG["start_time"] - 480
        else:
            t1 = EVENT_CONFIG["start_time"]
        t2 = EVENT_CONFIG["end_time"]

        # Get waveforms from IRIS or seedlink
        if i == 0:
            try:
                client = Client("IRIS")
                inventory = client.get_stations(
                    network=network,
                    station=station,
                    location=location,
                    channel=channel,
                    starttime=t1,
                    endtime=t2,
                    level="response",
                )
            except Exception as e:
                print(
                    f"Error fetching data from FDSN client. Please check network/station codes and time range. "
                    f"Exception: {e}"
                )
                break

        # Set up seedlink and take in stream
        seed = Client_seedlink(LOCAL_SEEDLINK, port=18000, timeout=180)
        try:
            if wf_client:
                g_stream = seed.get_waveforms(
                    network=network,
                    location=location,
                    station=station,
                    channel=channel,
                    starttime=t1,
                    endtime=t2,
                )
                if len(g_stream) > 0:
                    print("Data Found on seedlink")
                else:
                    print(
                        "Error fetching data from Seedlink. WiFi is correct, possibly an issue with retrieving data"
                        "from CTBTO."
                    )
            else:
                g_stream = client.get_waveforms(
                    network=network,
                    location=location,
                    station=station,
                    channel=channel,
                    starttime=t1,
                    endtime=t2,
                )
                if len(g_stream) > 0:
                    print("Data Found on IRIS")
        except Exception as e:
            print(f"Error fetching data. Exception: {e}")

        # Add coordinates to stream using inv fetched from IRIS
        latlon = []
        for tr in g_stream:
            coords = inventory.get_coordinates(
                f"{network}.{tr.stats.station}.{location}.{channel}", t1
            )
            tr.stats.coordinates = AttribDict(
                {
                    "latitude": coords["latitude"],
                    "elevation": coords["elevation"],
                    "longitude": coords["longitude"],
                }
            )
            latlon.append((coords["latitude"], coords["longitude"]))
            print(tr.stats.starttime, tr.stats.station)
        print(f"Fetched {len(g_stream)} traces from {network}.{station}.")

        # Get the centroid of the array. Standard coords are fine bc array isn't big enough for geodeisic shifting
        # to occur.
        centroid = np.mean([lat for lat, lon in latlon]), np.mean(
            [lon for lat, lon in latlon]
        )
        array_lat, array_lon = centroid

        strm = g_stream.copy()
        print(f"Run iteration {i}")

        # Noise is calculated based on the previous stream. If the previous stream has detections it will use the most
        # current stream that does not have any detections.
        if not i:
            # i==0 is a special case in which the previous 8 minutes of signal is the baseline noise.
            prev_start_time = t1
            dets = 0
            noise_start = t1
            noise_end = t1 + 480
            strm = strm.trim(t1 + 480, t2)
            n_strm = g_stream.trim(t1, t1 + 480)
        else:
            if not dets:
                noise_start = prev_start_time
                noise_end = prev_start_time + 480
            else:
                pass

        print(f"Noise window: {noise_start} to {noise_end}")
        # Compute noise and signal indices in seconds relative to stream start (t1).
        noise_len = noise_end - noise_start
        subset_start = t1 if (i) else t1 + 480
        str_name = name + "_" + t1.strftime("%Y%m%d_%H%M%S")
        print(f"Running Detection {subset_start} to {t2}")
        print(f"Processing stream: {str_name}")

        # Setup bf inputs based on config file
        back_az_vals = np.arange(back_az_min, back_az_max, back_az_step)
        trc_vel_vals = np.arange(trace_vel_min, trace_vel_max, trace_vel_step)

        # Run beamforming
        print(f"Running {method} beamforming")

        x, t, t0, geom = fkd.stream_to_array_data(strm, latlon=latlon)
        M, N = x.shape

        slowness = fkd.build_slowness(back_az_vals, trc_vel_vals)
        delays = fkd.compute_delays(geom, slowness)

        # Beamforming returns beam_power as a 3D array. Need to look into what actually is returned and best way to
        # access this data
        beam_times, beam_peaks, beam_power = fkd.auto_run_bf(
            (subset_start - t1),
            (t2 - subset_start),
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
        # Run detection
        print("Running FD detection")
        # Compute noise _fstat for detection auto threshold ; IPBeamformingWidget.py lines 1402 -> 1449
        TB_prod = (freq_max - freq_min) * window_len
        if fixed_thresh:
            thresh = fixed_thresh
        else:
            # If detections were found thresh will be the same as previous valid fstat threshold. If not recompute
            # with the previous timeslot
            if not i:
                n_x, n_t, n_t0, n_geom = fkd.stream_to_array_data(n_strm, latlon=latlon)
                n_delays = fkd.compute_delays(n_geom, slowness)
                thresh = fkd.adjust_thresh_noise(
                    (n_x, n_t, n_t0, n_geom),
                    window_len,
                    sub_window_len,
                    noise_len,
                    window_step,
                    freq_min,
                    freq_max,
                    method,
                    back_az_vals,
                    trc_vel_vals,
                    n_delays,
                    p_value,
                    TB_prod,
                )
                prev_thresh = 0
                new_thresh = 0
            elif dets:
                thresh = prev_thresh
            else:
                thresh = new_thresh

        min_seq = int(max(2, min_duration / (window_step)))
        det_results = fkd.run_fd(
            beam_times,
            beam_peaks,
            window_len,
            TB_prod,
            len(strm),
            p_value,
            min_seq,
            back_az_width,
            thresh,
            thresh_ceil,
            return_thresh,
            merge_dets,
        )
        dets = det_results[0] if return_thresh else det_results

        det_list = []
        for det_info in dets:
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
            det_fpath = "../results/" + t1.strftime("%Y/%m/%d/")
            try:
                if not os.path.isdir(det_fpath):
                    print("Making New Folder")
                    os.makedirs(det_fpath, exist_ok=True)
                else:
                    pass
            except Exception as e:
                print(f"Error making folder, please investigate issues: {e}")
                det_fpath = "../results/bin/"
            det_out = det_fpath + str_name + "_detections.json"
            dets = 1
            prev_thresh = thresh
            print(
                f"  Found {len(det_list)} detections, writing to {det_out}\nNew Threshold: {prev_thresh}"
            )
            str_info = [
                strm[0].stats.network,
                fstrm[0].stats.station + "-" + strm[-1].stats.station,
                strm[0].stats.channel,
            ]
            data_io.detection_list_to_json(det_out, det_list, str_info)
            with open(det_out, "r") as f:
                dets_data = json.load(f)
            for det in dets_data:
                det["Name"] = str_name
                det["Latitude"] = array_lat
                det["Longitude"] = array_lon
                det["Signal"] = f"{subset_start} to {t2}"
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
                subset_start,
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
            print("No detections found.")
            dets = 0
            prev_start_time = subset_start
            new_thresh = fkd.adjust_thresh_noise(
                (x, t, t0, geom),
                window_len,
                sub_window_len,
                noise_len,
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
        if real_time:
            T = time.time() - stop_watch
            print(
                f"Sleeping for {510 - T} seconds until {obspy.UTCDateTime() + (510 - T) - 36000} (HST)"
            )
            time.sleep(510 - T)
        i += 1
