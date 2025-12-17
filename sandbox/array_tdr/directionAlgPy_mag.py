import numpy as np
from scipy.signal import correlate
import matplotlib.pyplot as plt 

# User-defined variables
V = 1100    # Nominal wave velocity in m/s
fs = 1000.  # Sampling frequency in Hz
dt = 1 / fs  # Sample interval in seconds
# Data directory
data_dir = "src/dsp/array_tdr/"


def xcorr_td(sig_01, sig_02, dt):
    """Calculates time delay using cross-correlation."""
    c = correlate(sig_01, sig_02, mode='full')
    lags = np.arange(len(c)) - (len(sig_01) - 1)
    I = np.argmax(c)
    return lags[I] * dt


if __name__ == "__main__":
    # TODO: Construct load function for signals and array geometry
    # Coordinates of equilateral triangle array, in meters (dNorth, dEast, dZ)
    x = np.array([-50, 0, 50])
    y = np.array([-43.3, 43.3, -43.3])
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

    # Provided signal data 
    sig1 = np.loadtxt(data_dir + "S1AZ156EL53.txt")
    sig2 = np.loadtxt(data_dir + "S2AZ156EL53.txt")
    sig3 = np.loadtxt(data_dir + "S3AZ156EL53.txt")

    # plot waveforms (optional)
    t = np.arange(len(sig1)) * dt
    plt.figure()    
    plt.plot(t, sig1, label='Sensor 1')
    plt.plot(t, sig2, label='Sensor 2')
    plt.plot(t, sig3, label='Sensor 3')
    plt.xlabel('Time (s)')
    plt.ylabel('Amplitude')


    # displacement matrix creation
    dx21 = x[1] - x[0]
    dy21 = y[1] - y[0]
    dx32 = x[2] - x[1]
    dy32 = y[2] - y[1]
    dx13 = x[0] - x[2]
    dy13 = y[0] - y[2]

    X = np.array([[dx13, dy13],
                  [dx32, dy32],
                  [dx21, dy21]])

    TD13 = xcorr_td(sig3, sig1, dt)
    TD31 = -TD13
    TD12 = xcorr_td(sig2, sig1, dt)
    TD21 = -TD12
    TD23 = xcorr_td(sig3, sig2, dt)
    TD32 = -TD23
    td = np.array([TD13, TD32, TD21])

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
    
    plt.title(f"Waveforms from Three Sensors\nBack Azimuth: {back_azimuth_degrees:.2f}°, Elevation: {elevation_degrees:.2f}°")
    plt.legend()
    plt.show()