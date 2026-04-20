"""
Automatic Detection Function using InfraPy
Create class EventDetector to handle configuration for automated detection runs.
Refer to config/config.ini for example configuration file.

Author: Riley Johnson, ISLA 2025/12/18
Modified: Tyler Yoshiyama, ISLA 2026/04/14

Example config classes:

Barebones config class for fixed time period:
evd = EventDetector(
    event_name="TEST",
    network="NTW",
    station="STA*",
    location="",
    channel="CHN",
    nrt_stime=UTCDateTime(START_TIME),
    end_time=UTCDateTime(END_TIME),
)

Barebones config class for real-time processing:
evd = EventDetector(
    event_name="TEST",
    network="NTW",
    station="STA*",
    location="",
    channel="CHN",
    real_time=True,
)
"""
import configparser
import json
import os
import sys
import time
from typing import Optional
import logging
import traceback
from urllib.error import URLError

import numpy as np
import obspy
from obspy import UTCDateTime
from obspy.clients.fdsn import Client
from obspy.clients.seedlink import Client as Client_seedlink

# InfraPy imports
from infrapy.detection import beamforming_new as fkd
from infrapy.utils import config as infraconfig
from infrapy.utils import data_io


class EventDetector:
    """
    This class handles event detection using InfraPy

    Properties:

        event_name: str, name of the event

        network: str, network code for data request

        station: str, station code for data request

        location: str, location code for data request

        channel: str, channel code for data request

        num_elements: int, number of array elements expected.  Default 4.

        wf_client: int, flag to pull data from IRIS (0) or seedlink (1).  Ensure proper network connection
        if using seedlink.  Default 0.  More options may be added in the future.
        NOTE: You must specify a seedlink_ip parameter if using seedlink option.

        root_path: str, root path for the project.  Defaults to current working directory if not given

        results_dir: str, if not given, defaults to "{root_path}/results"

        real_time: bool, flag for static time frame (False) or real-time processing (True).  Defaults to False

        rt_buffer_s: int, buffer time in seconds to account for data source latency during real-time processing.
        Defaults to 120 seconds.  Not required if not using real-time processing.

        nrt_stime: UTCDateTime, start time for non-real-time processing.  Required if real_time is False.

        end_time: UTCDateTime, end time for non-real-time processing.  Required if real_time is False.

        sig_len_secs: int, length of signal window in seconds.  Defaults to 600 seconds.

        overlap_perc: float, fractional overlap between time windows.  Defaults to 0.2 (20% overlap).
        Any value less than 0 or greater than 1.0 will be set to 0.2.

        signal_step_sec: float, signal step in seconds after accounting for overlap.
    """
    def __init__(self,
                 event_name: str,
                 network: str,
                 station: str,
                 location: str,
                 channel: str,
                 num_elements: int = 4,
                 wf_client: int = 0,
                 seedlink_ip: Optional[str] = None,
                 root_path: Optional[str] = None,
                 config_path: Optional[str] = None,
                 real_time: bool = False,
                 rt_buffer_s: int = 120,
                 nrt_stime: Optional[UTCDateTime] = None,
                 end_time: Optional[UTCDateTime] = None,
                 sig_len_secs: int = 600,
                 overlap_perc: float = 0.2,
                 results_dir: Optional[str] = None,
                 inventory_dir: Optional[str] = None,
                 inventory_name: Optional[str] = None
                 ):
        """
        intialize event detector

        :param event_name: name of the event
        :param network: network code for data request
        :param station: station code for data request
        :param location: location code for data request
        :param channel: channel code for data request
        :param num_elements: number of array elements expected.  Default 4.
        :param wf_client: flag to pull data from IRIS (0) or seedlink (1).  Ensure proper network connection
            if using seedlink.  Default 0.  More options may be added in the future.
        :param seedlink_ip: IP address of local seedlink server if using seedlink as data source.  Default None
            NOTE: default value will cause program to quit with error message if using seedlink as source
        :param root_path: root path for the project.  Defaults to current working directory if not given
        :param config_path: path to the Infrapy configuration file.  Defaults to
            "{root_path}/config/config.ini" if not given
        :param real_time: flag for static time frame (False) or real-time processing (True).  Defaults to False
        :param nrt_stime: start time for non-real-time processing.  Required if real_time is False.
        :param end_time: end time for processing.  Required if real_time is False.
        :param sig_len_secs: length of signal window in seconds.  Defaults to 600 seconds.
        :param overlap_perc: fractional overlap between time windows.  Defaults to 0.2 (20% overlap)
        """
        self.event_name = event_name
        self.network = network
        self.station = station
        self.location = location
        self.channel = channel
        self.num_elements = num_elements
        self.wf_client = wf_client
        if not self.wf_client:
            self.client = Client("IRIS")
        elif seedlink_ip is None or not seedlink_ip:
            print("Local seedlink IP address must be provided when using seedlink as data source")
            exit(1)
        else:
            self.client = Client_seedlink(seedlink_ip, port=18000, timeout=180)
            try:
                _ = self.client.get_info()
            except Exception as e:
                print(f"Error connecting to seedlink server at {seedlink_ip}: {e}")
                exit(1)
        self.root_path = root_path if root_path else os.path.join(os.getcwd())
        if config_path is None:
            config_path = os.path.join(self.root_path, 'config')
        if not os.path.exists(config_path):
            print(f"Config file not found, check for file at {config_path}")
            exit(1)
        self.real_time = real_time
        self.rt_buffer_s = rt_buffer_s
        if not self.real_time and nrt_stime is None:
            print("nrt_stime must be provided if real_time is False")
            exit(1)
        self.nrt_stime = nrt_stime
        if not self.real_time and end_time is None:
            print("end_time must be provided if real_time is False")
            exit(1)
        self.end_time = end_time
        self.sig_len_secs = sig_len_secs
        self.overlap_perc = overlap_perc
        self.signal_step_sec = self.sig_len_secs * (1 - self.overlap_perc)
        if not self.real_time:
            dur = self.end_time - self.nrt_stime - sig_len_secs  # type: ignore
            if dur <= 0:
                print("WARNING: Selected time segment is shorter than signal length.  Results may not be reliable.")
            else:
                remainder = dur % self.signal_step_sec  # type: ignore
                if remainder != 0:
                    print("NOTE: Selected time segment will have incomplete last window that will not be processed."
                          f"Extra Time = {remainder} seconds.")
        self.results_dir = results_dir if results_dir else os.path.join(self.root_path, 'results')
        self.inventory_dir = inventory_dir if inventory_dir else config_path
        self.inventory_name = inventory_name if inventory_name else f"{self.station}_inventory.xml"

    @staticmethod
    def create_log(config_path: str, day_key: str) -> str:
        """
            Creates a log file for each day of processings for information and error logging.

            :param config_path: Path to configuration file that contains the output directory.
            :param day_key: Key for the day of processing.
            :return: Path to the created log file.
        """
        day_path = os.path.join(config_path, day_key[:4], day_key[4:6], day_key[6:])
        os.makedirs(day_path, exist_ok=True)
        log_file = os.path.join(day_path, f"data_log_{day_key}.log")
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
        fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        fh = logging.FileHandler(log_file, mode="a")
        fh.setLevel(logging.INFO)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
        sh = logging.StreamHandler()
        sh.setLevel(logging.INFO)
        sh.setFormatter(fmt)
        logger.addHandler(sh)
        return day_path

    @staticmethod
    def load_config(rt_path: str, cfg_path: str, cfg_file: str, run_cfg: configparser.ConfigParser) -> "EventDetector":
        """
        Loads the configuration file for the event detector.

        :param rt_path: Root path for the project
        :param cfg_path: Path to the configuration file
        :param user_config: User-provided configuration parser
        :return: EventDetector object
        """
        try:
            if not os.path.exists(cfg_path):
                print(f"Config not found at {cfg_path}")
                exit(1)

            evd = EventDetector(
                event_name=infraconfig.get_param(run_cfg, "RUN", "event_name", None, "string"),     # type: ignore
                network=infraconfig.get_param(run_cfg, "RUN", "network", None, "string"),           # type: ignore
                station=infraconfig.get_param(run_cfg, "RUN", "station", None, "string"),           # type: ignore
                location=infraconfig.get_param(run_cfg, "RUN", "location", None, "string") or "",   # type: ignore
                channel=infraconfig.get_param(run_cfg, "RUN", "channel", None, "string"),           # type: ignore
                root_path=rt_path,
                config_path=cfg_path,
                num_elements=infraconfig.get_param(run_cfg, "RUN", "num_elements", None, "int"),    # type: ignore
                wf_client=infraconfig.get_param(run_cfg, "RUN", "wf_client", None, "int"),          # type: ignore
                real_time=infraconfig.get_param(run_cfg, "RUN", "real_time", None, "bool"),         # type: ignore
                rt_buffer_s=infraconfig.get_param(run_cfg, "RUN", "rt_buffer_s", None, "int"),      # type: ignore
                nrt_stime=UTCDateTime(infraconfig.get_param(run_cfg, "RUN", "nrt_stime", None, "string")),
                end_time=UTCDateTime(infraconfig.get_param(run_cfg, "RUN", "end_time", None, "string")),
                sig_len_secs=infraconfig.get_param(run_cfg, "RUN", "sig_len_secs", None, "int"),    # type: ignore
                overlap_perc=infraconfig.get_param(run_cfg, "RUN", "overlap_perc", None, "float"),  # type: ignore
                seedlink_ip=infraconfig.get_param(run_cfg, "RUN", "seedlink_ip", None, "string"),   # type: ignore
                results_dir=infraconfig.get_param(run_cfg, "RUN", "results_dir", None, "string"),   # type: ignore
                inventory_dir=infraconfig.get_param(run_cfg, "RUN", "inventory_dir", None, "string"),    # type: ignore
                inventory_name=infraconfig.get_param(run_cfg, "RUN", "inventory_name", None, "string")   # type: ignore
            )
        except Exception as e:
            print(f"Error loading configuration: {e}")
            exit(1)
        return evd


if __name__ == "__main__":
    """
    Main entry point for automated infrasonic detection using InfraPy

    If adding command line parameters, the root path is always first and the config path is second.
    If only one parameter is given, it is assumed to be the root path, and config path will be default.
    Any parameters beyond the first two will be ignored.
    Example: python main.py /path/to/root /path/to/config.ini
    """
    # Set up paths from CLI or use defaults
    root_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.getcwd(), 'sandbox', 'automated_detection')
    cfg_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(root_path, 'config')
    cfg_ini = sys.argv[3] if len(sys.argv) > 3 else 'config.ini'
    # Setup Event Detector and paths
    user_config = configparser.ConfigParser()
    user_config.read(os.path.join(cfg_path, cfg_ini))

    evd = EventDetector.load_config(root_path, cfg_path, cfg_ini, user_config)

    # Beamforming Parameters
    freq_min: float = infraconfig.get_param(user_config, "FK", "freq_min", None, "float")          # type: ignore
    freq_max: float = infraconfig.get_param(user_config, "FK", "freq_max", None, "float")          # type: ignore
    back_az_min: float = infraconfig.get_param(user_config, "FK", "back_az_min", None, "float")    # type: ignore
    back_az_max: float = infraconfig.get_param(user_config, "FK", "back_az_max", None, "float")    # type: ignore
    back_az_step: float = infraconfig.get_param(user_config, "FK", "back_az_step", None, "float")  # type: ignore
    trace_vel_min: float = infraconfig.get_param(user_config, "FK", "trace_vel_min", None,
                                                 "float")    # type: ignore
    trace_vel_max: float = infraconfig.get_param(user_config, "FK", "trace_vel_max", None,
                                                 "float")    # type: ignore
    trace_vel_step: float = infraconfig.get_param(user_config, "FK", "trace_vel_step", None,
                                                  "float")  # type: ignore
    method: str = infraconfig.get_param(user_config, "FK", "method", None, "string")               # type: ignore
    signal_start: UTCDateTime = UTCDateTime(0)
    t = infraconfig.get_param(user_config, "FK", "signal_start", None, "string")
    t = infraconfig.get_param(user_config, "FK", "signal_start", None, "string")
    if t is not None:
        signal_start = UTCDateTime(t)
    signal_end: UTCDateTime = UTCDateTime(0)
    t = infraconfig.get_param(user_config, "FK", "signal_end", None, "string")
    t = infraconfig.get_param(user_config, "FK", "signal_end", None, "string")
    if t is not None:
        signal_end = UTCDateTime(t)
    noise_start: UTCDateTime = UTCDateTime(0)
    t = infraconfig.get_param(user_config, "FK", "noise_start", None, "string")
    if t is not None:
        noise_start = UTCDateTime(t)
    noise_end: UTCDateTime = UTCDateTime(0)
    t = infraconfig.get_param(user_config, "FK", "noise_end", None, "string")
    if t is not None:
        noise_end = UTCDateTime(t)
    window_len: float = infraconfig.get_param(user_config, "FK", "window_len", None, "float")    # type: ignore
    sub_window_len: float = infraconfig.get_param(user_config, "FK", "sub_window_len", None,
                                                  "float")  # type: ignore
    window_step: float = infraconfig.get_param(user_config, "FK", "window_step", None, "float")  # type: ignore
    cpu_cnt: int = infraconfig.get_param(user_config, "FK", "cpu_cnt", None, "int")              # type: ignore

    # Detection parameters
    fd_window_len: float = infraconfig.get_param(user_config, "FD", "window_len", None, "float")     # type: ignore
    p_value: float = infraconfig.get_param(user_config, "FD", "p_value", None, "float")              # type: ignore
    min_duration: float = infraconfig.get_param(user_config, "FD", "min_duration", None, "float")    # type: ignore
    back_az_width: float = infraconfig.get_param(user_config, "FD", "back_az_width", None, "float")  # type: ignore
    fixed_thresh: float = infraconfig.get_param(user_config, "FD", "fixed_thresh", None, "float")    # type: ignore
    thresh_ceil: float = infraconfig.get_param(user_config, "FD", "thresh_ceil", None, "float")      # type: ignore
    return_thresh: bool = infraconfig.get_param(user_config, "FD", "return_thresh", None, "bool")    # type: ignore
    merge_dets: bool = infraconfig.get_param(user_config, "FD", "merge_dets", None, "bool")          # type: ignore

    """
    This section runs an automated infrasonic detection using InfraPy's beamforming and detection modules.
    It will pull data from either IRIS or a local seedlink server, process it in overlapping time windows,
    and save detections and raw data to specified directories.
    """
    # set initial time window
    t1: UTCDateTime = UTCDateTime() - ((2 * evd.sig_len_secs) + evd.rt_buffer_s) \
        if evd.real_time else evd.nrt_stime - evd.signal_step_sec  # type: ignore
    t2 = UTCDateTime() - (evd.sig_len_secs + evd.rt_buffer_s) if evd.real_time else evd.nrt_stime
    current_day = t1.strftime("%Y%m%d")
    det_fpath = evd.create_log(os.path.join(evd.results_dir), current_day)
    # Generate Noise and Get Inventory
    inventory = None
    # Try to load inventory from XML file first
    try:
        inv_file = os.path.join(evd.inventory_dir, evd.inventory_name)
        inventory = obspy.read_inventory(inv_file)
        logging.info(f"Loaded inventory from {inv_file}")
    except Exception as e:
        # If no XML file load from IRIS
        logging.warning(f"could not load from .xml file Exception: {e}")
        logging.error("".join(traceback.format_exception(type(e), e, e.__traceback__)))
        try:
            inventory = Client("IRIS").get_stations(
                network=evd.network,
                station=evd.station,
                location=evd.location,
                channel=evd.channel,
                starttime=t1,
                endtime=t2,
                level="response",
            )
            if inventory is None:
                logging.error("Error fetching inventory: no data returned from client.")
                logging.shutdown()
                sys.exit(1)
        except Exception as e:
            # no inventory means we need to exit
            logging.error(f"Error {e} fetching data from FDSN client. Please check network/station codes and time "
                          "range.")
            logging.error("".join(traceback.format_exception(type(e), e, e.__traceback__)))
            logging.shutdown()
            sys.exit(1)

    # Get Baseline Noise Data
    logging.info("Fetching baseline noise data")
    try:
        n_stream = evd.client.get_waveforms(
            network=evd.network,
            location=evd.location,
            station=evd.station,
            channel=evd.channel,
            starttime=t1,
            endtime=t2,
        )
        if n_stream is None:
            logging.error("Error fetching baseline noise data: no data returned from client.")
            logging.shutdown()
            sys.exit(1)
    except Exception as e:
        logging.error(f"Error fetching base waveforms. Exception: {e}")
        logging.error("".join(traceback.format_exception(type(e), e, e.__traceback__)))
        logging.shutdown()
        sys.exit(1)

    # Load station coordinates into stream
    latlon = []
    for tr in n_stream:
        coords = inventory.get_coordinates(
            f"{evd.network}.{tr.stats.station}.{evd.location}.{evd.channel}", t1
        )
        latlon.append((coords["latitude"], coords["longitude"]))
        logging.info(f"{tr.stats.starttime} {tr.stats.station}")
    logging.info(f"Fetched {len(n_stream)} traces from {evd.network}.{evd.station}.")

    centroid = np.mean([lat for lat, _ in latlon]), np.mean([lon for _, lon in latlon])
    array_lat, array_lon = centroid
    TB_prod = (freq_max - freq_min) * window_len
    back_az_vals = np.arange(back_az_min, back_az_max, back_az_step)
    trc_vel_vals = np.arange(trace_vel_min, trace_vel_max, trace_vel_step)
    n_x, n_t, n_t0, geom = fkd.stream_to_array_data(n_stream, latlon=latlon)  # type: ignore
    slowness = fkd.build_slowness(back_az_vals, trc_vel_vals)
    delays = fkd.compute_delays(geom, slowness)

    # If no fixed threshold compute initial threshold based on noise
    if (not fixed_thresh):
        thresh = fkd.adjust_thresh_noise(
            (n_x, n_t, n_t0, geom),
            window_len,
            sub_window_len,
            evd.signal_step_sec,
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

    # Initialize loop for processing time windows
    logging.info("Beginning automated detection processing")
    while True:
        t_now = UTCDateTime()
        try:
            stop_watch = time.time()
            if (not dets_found):
                noise_start = t1
                noise_end = t1 + evd.signal_step_sec
            t1 = t_now - (evd.sig_len_secs + evd.rt_buffer_s) if (evd.real_time) \
                else evd.nrt_stime + (i * evd.signal_step_sec)                     # type: ignore
            t2 = t_now - evd.rt_buffer_s if (evd.real_time) \
                else evd.nrt_stime + (i * evd.signal_step_sec) + evd.sig_len_secs  # type: ignore
            new_day = t1.strftime("%Y%m%d")
            if new_day != current_day:
                current_day = new_day
                det_fpath = evd.create_log(os.path.join(evd.results_dir), current_day)
            if not evd.real_time and t2 > evd.end_time:                            # type: ignore
                logging.info("End of non-real-time processing reached.  Exiting.")
                exit(0)

            # Get waveforms from IRIS or seedlink
            try:
                g_stream = evd.client.get_waveforms(
                    network=evd.network,
                    location=evd.location,
                    station=evd.station,
                    channel=evd.channel,
                    starttime=t1,
                    endtime=t2,
                )
                if g_stream is None:
                    raise Exception("No waveforms returned from client.")
                logging.info(f"Fetched {len(g_stream)} traces from {evd.network}.{evd.station}.")   # type: ignore
                if (len(g_stream) < evd.num_elements):                                              # type: ignore
                    logging.warning(f"Error fetching waveforms. Received {len(g_stream)} traces, "  # type: ignore
                                    f"expected {evd.num_elements}.")
                    i += 1
                    continue
                str_name = f"{evd.event_name}_{t1.strftime('%Y%m%d_%H%M%S')}"
                logging.info(f"Iteration {i}")

                # Begin beamforming on stream
                strm = g_stream.copy()
                x, t, t0, _ = fkd.stream_to_array_data(strm, latlon=np.array(latlon))
                M, N = x.shape
                logging.info(f"Running {method} beamforming from {t1} to {t2}")
                beam_times, beam_peaks, beam_power = fkd.auto_run_bf(
                    0,
                    t2 - t1,  # type: ignore
                    freq_band=(freq_min, freq_max),
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
                    logging.info("Adjusting threshold based on noise")
                    thresh = prev_thresh if dets_found else new_thresh

                # Run detection
                logging.info(f"Running FD detection from {t1} to {t2}\nNoise Window: {noise_start} to {noise_end}")
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
                logging.info("Detection Complete")

                # Save detections
                if len(det_list) > 0:
                    det_out = os.path.join(det_fpath, f"{str_name}_detections.json")
                    dets_found = True
                    prev_thresh = thresh
                    logging.info(
                        f"Found {len(det_list)} detections, writing to {det_out} ; New Threshold: {prev_thresh}"
                    )
                    str_info = [
                        strm[0].stats.network,                                # type: ignore
                        f"{strm[0].stats.station}-{strm[-1].stats.station}",  # type: ignore
                        strm[0].stats.channel,                                # type: ignore
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

                    # If there is a detection save all raw data
                    dt = np.array(
                        [
                            (tn - np.datetime64(strm[0].stats.starttime))  # type: ignore
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
                    logging.info(f"  Wrote FK results to {rd_out}")
                else:
                    logging.info("No detections found")
                    dets_found = False
                    if (not fixed_thresh):
                        logging.info("Recalculating threshold based on noise")
                        new_thresh = fkd.adjust_thresh_noise(
                            (x, t, t0, geom),
                            window_len,
                            sub_window_len,
                            evd.signal_step_sec,
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
                        logging.info(f"New Threshold: {new_thresh}")
                    else:
                        new_thresh = fixed_thresh
                if evd.real_time:
                    T = time.time() - stop_watch
                    remaining_sleep = evd.signal_step_sec - T
                    logging.info(
                        f"Sleeping for {remaining_sleep} seconds until "
                        f"{t_now + remaining_sleep - 36000} (HST)"
                    )
                    time.sleep(remaining_sleep)
            except URLError as e:
                logging.error(f"Network error fetching data (URLError): {e.reason}")
                if evd.real_time:
                    logging.info(f"Retrying after {evd.signal_step_sec} seconds...")
                    time.sleep(evd.signal_step_sec)
            except Exception as e:
                logging.error(f"Error fetching data. Exception: {e}")
                logging.error("".join(traceback.format_exception(type(e), e, e.__traceback__)))
                if evd.real_time:
                    logging.info(f"Retrying after {evd.signal_step_sec} seconds...")
                    time.sleep(evd.signal_step_sec)
        except Exception as e:
            # Print to output any errors and continue to next time window
            logging.error(f"{t_now}: Error in detection processing: {e}")
            logging.error("".join(traceback.format_exception(type(e), e, e.__traceback__)))
        i += 1  # increment iteration
logging.shutdown()
sys.exit(0)
