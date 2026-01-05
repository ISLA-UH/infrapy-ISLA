from scipy import signal
import numpy as np
import pyqtgraph as pg
from obspy import Trace


class IPSpectrogram(pg.ImageItem):
    """
    class for Spectrogram display
    """
    def __init__(self):
        """
        initialize
        """
        super().__init__()

    def setData(self, trace: Trace):
        """
        ingest obspy trace, get the data and calculate the spectrogram

        :param trace: obspy trace
        """
        f, t, Sxx = signal.spectrogram(trace.data, trace.stats['sampling_rate'])
