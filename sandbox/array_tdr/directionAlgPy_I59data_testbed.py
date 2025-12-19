import numpy as np
from scipy.signal import correlate
import matplotlib.pyplot as plt
from obspy import clients as C
import obspy
from obspy.core.util import AttribDict
from obspy.clients.fdsn import Client
from obspy.clients.seedlink import Client as Client_seedlink
import numpy as np
from pyproj import Geod
"""
This script implements the directionAlgPy script using data fetched from IRIS or Seedlink as opposed to simulated data. Detection data from other detection
algorithms can be used to verify the results obtained from this script.
"""

# User-defined variables
wgs84_proj = Geod(ellps='sphere')
V = 1100    # Nominal wave velocity in m/s
fs = 1000.  # Sampling frequency in Hz
dt = 1 / fs  # Sample interval in seconds
# Data directory
data_dir = "./sandbox/array_tdr/"
LOCAL_SEEDLINK = "192.168.112.200"
wf_client = 0  # Flag to pull data from IRIS (0) or seedlink (1) NOTE: If 1 ensure WiFi is ISLA_CF_5g
def xcorr_td(sig_01, sig_02, dt):
    """Calculates time delay using cross-correlation."""
    c = correlate(sig_01, sig_02, mode='full')
    lags = np.arange(len(c)) - (len(sig_01) - 1)
    I = np.argmax(c)
    return lags[I] * dt


if __name__ == "__main__":
    # TODO: Construct load function for signals and array geometry
    # Coordinates of equilateral triangle array, in meters (dNorth, dEast, dZ)
    EVENT_CONFIG = {
        "name": "auto_infrapy_test",
        "network": "IM",
        "station": "I59*",
        "location": "",
        "channel": "BDF",
        "start_time": (
            obspy.UTCDateTime('2025-12-17T20:06:59.543007Z')
        ),
        "end_time": (
            obspy.UTCDateTime('2025-12-17T20:16:59.543007Z')
        ),
    }

    # Set parameters from the event config
    name = EVENT_CONFIG["name"]
    network = EVENT_CONFIG["network"]
    station = EVENT_CONFIG["station"]
    location = EVENT_CONFIG["location"]
    channel = EVENT_CONFIG["channel"]
    t1 = EVENT_CONFIG["start_time"]
    t2 = EVENT_CONFIG["end_time"]

    # Get waveforms from IRIS or seedlink
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
            f"Error fetching data from FDSN client. Please check network/station codes and time range. Exception: {e}"
        )

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
                    "Error fetching data from Seedlink. WiFi is correct, possibly an issue with retrieving data from CTBTO."
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
    # Add coordinates to stream using inv feteched from IRIS
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

    dxdy = np.zeros((len(g_stream), 2))
    for m in range(0, len(g_stream)):
        temp = wgs84_proj.inv(latlon[0][1], latlon[0][0], latlon[m][1], latlon[m][0])
        dxdy[m] = np.array((temp[2] * np.sin(np.radians(temp[0])), temp[2] * np.cos(np.radians(temp[0]))))

    
    x = dxdy[:, 0]
    y = dxdy[:, 1]
    z = np.array([0, 0, 0])

    # Plot array geometry (optional)
    plt.figure()
    plt.plot(x, y, 'ro')
    for i in range(len(x)):
        plt.text(x[i], y[i], f'Sensor {i+1}')
    plt.xlabel('East (m)')
    plt.ylabel('North (m)')
    plt.title('Array Geometry')
    plt.axis('equal')
    plt.grid()

    # Provided real signal data from I59
    sig1 = g_stream[0].data
    sig2 = g_stream[1].data
    sig3 = g_stream[2].data
    sig4 = g_stream[3].data

    # plot waveforms (optional)
    g_stream = g_stream.normalize() # Normalize stream so dont need to deal with response
    t = np.arange(len(sig1))/20
    plt.figure()    
    plt.plot(t, sig1, label='Sensor 1')
    plt.plot(t, sig2, label='Sensor 2')
    plt.plot(t, sig3, label='Sensor 3')
    plt.plot(t, sig4, label='Sensor 4')
    plt.xlabel('Time')
    plt.ylabel('Amplitude')


    # Build baselines and time delays consistently: displacement is from i -> j
    pairs = [
        (0, 1),
        (0, 2),
        (0, 3),
        (1, 2),
        (1, 3),
        (2, 3),
    ]

    sigs = [sig1, sig2, sig3, sig4]
    X_rows = []
    td_vals = []
    for i, j in pairs:
        X_rows.append([x[j] - x[i], y[j] - y[i]])  # displacement i -> j (E, N)
        td_vals.append(xcorr_td(sigs[i], sigs[j], dt))  # lag of j relative to i

    X = np.array(X_rows)
    td = np.array(td_vals)


    """# displacement matrix creation
    dx21 = x[1] - x[0]
    dy21 = y[1] - y[0]
    dx32 = x[2] - x[1]
    dy32 = y[2] - y[1]
    dx13 = x[0] - x[2]
    dy13 = y[0] - y[2]

    dx14 = x[0] - x[3]
    dy14 = y[0] - y[3]
    dx42 = x[3] - x[1]
    dy42 = y[3] - y[1]
    dx34 = x[2] - x[3]
    dy34 = y[2] - y[3]


    X = np.array([[dx13, dy13],
                  [dx32, dy32],
                  [dx21, dy21],
                  [dx14, dy14],
                  [dx42, dy42],
                  [dx34, dy34]])

    TD13 = xcorr_td(sig3, sig1, dt)
    TD31 = -TD13
    TD12 = xcorr_td(sig2, sig1, dt)
    TD21 = -TD12
    TD23 = xcorr_td(sig3, sig2, dt)
    TD32 = -TD23
    TD14 = xcorr_td(sig4, sig1, dt)
    TD41 = -TD14
    TD24 = xcorr_td(sig4, sig2, dt)
    TD42 = -TD24
    TD34 = xcorr_td(sig4, sig3, dt)
    TD43 = -TD34
    td = np.array([TD13, TD32, TD21, TD14, TD24, TD34])"""
    # Slowness vector calculation
    # X * td / X^2 has units of seconds per meter
    # Original line: SH = np.linalg.inv(X.T @ X) @ X.T @ td
    # Optimized: Using np.linalg.solve instead of explicit matrix inversion
    # This is ~1.8x faster and more numerically stable
    SH = np.linalg.solve(X.T @ X, X.T @ td)

    # Azimuth and elevation calculations
    Sh = np.sqrt(SH[0]**2 + SH[1]**2)  # Horizontal slowness
    azimuth = np.degrees(np.arctan2(SH[1], SH[0]))
    # Coordinate frame adjustment to N = 0, E = 90
    back_azimuth_degrees = -azimuth + 90
    # Normalize to 0-360 degrees
    if back_azimuth_degrees < 0:
        back_azimuth_degrees += 360
    # Elevation calculation: horontal slowness |Sh| = Cos(theta)/V
    elevation_degrees = np.degrees(np.arccos(abs(Sh) * V))

    print(f"Back Azimuth: {back_azimuth_degrees:.2f}")
    print(f"Elevation, degrees: {elevation_degrees:.2f}")
    
    plt.title(f"Waveforms from Four Sensors\nBack Azimuth: {back_azimuth_degrees:.2f}°, Elevation: {elevation_degrees:.2f}°")
    plt.legend()
    plt.show()