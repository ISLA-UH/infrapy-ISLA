from typing import Optional
from numpy import dtype
from obspy.core.stream import Stream
from obspy.core import read as obsRead
from obspy import UTCDateTime


def ip_read(pathname_or_url: Optional[str] = None, format: Optional[str] = None, headonly: bool = False,
            starttime: Optional[UTCDateTime] = None, endtime: Optional[UTCDateTime] = None,
            nearest_sample: bool = True, dtype: Optional[dtype] = None, apply_calib: bool = False,
            check_compression: bool = True, **kwargs) -> 'IPStream':
    """
    read data from the given IP

    :param pathname_or_url: Path or URL to the IP data
    :param format: Data format
    :param headonly: If True, only read the trace headers
    :param starttime: Start time for reading data
    :param endtime: End time for reading data
    :param nearest_sample: If True, align to the nearest sample
    :param dtype: Data type for the traces
    :param apply_calib: If True, apply calibration to the data
    :param check_compression: If True, check for compressed data
    :param kwargs: Additional keyword arguments for obspy read function
    :return: An IPStream object containing the read data
    """
    stream = obsRead(pathname_or_url, format=format, headonly=headonly, starttime=starttime,
                     endtime=endtime, nearest_sample=nearest_sample, dtype=dtype, apply_calib=apply_calib,
                     check_compression=check_compression, **kwargs)

    stream.__class__ = IPStream
    stream.promote()

    return stream


class IPStream(Stream):
    """
    class for stream from IP
    """
    __filtered = []

    def __init__(self, traces: Optional[list] = None):
        """
        initialize

        :param traces: list of traces
        """
        super().__init__(traces)
        self.promote()

    def promote(self):
        """
        reset filtered traces
        """
        self.resetFiteredTraces()

    def getFiltered(self) -> list:
        """
        :return: filtered traces
        """
        return self.__filtered

    def resetFiteredTraces(self):
        """
        reset filtered traces
        """
        self.__filtered.clear()
        for trace in self.traces:
            self.__filtered.append(trace.copy())

        return
