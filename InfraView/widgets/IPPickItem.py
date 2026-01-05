from infrapy.propagation.likelihoods import InfrasoundDetection


class IPPickItem(InfrasoundDetection):
    """
    class for Pick Items
    """
    _associatedPickLine = None    # reference to the pick line associated with this pick

    def __init__(self, name: str = ""):
        """
        initialize

        :param name: name of the pick item.  Default empty string
        """
        super().__init__()

        self.set_name(name)

    def getAssociatedPickLine(self):
        """
        :return: reference to the pick line associated with this pick
        """
        return self._associatedPickLine

    def setAssociatedPickLine(self, pickline):
        """
        set reference to the pick line associated with this pick

        :param pickline: reference to the pick line
        """
        self._associatedPickLine = pickline

    def to_InfrasoundDetection(self) -> InfrasoundDetection:
        """
        :return: InfrasoundDetection object
        """
        return InfrasoundDetection(lat_loc=self.latitude, lon_loc=self.longitude, time=self.peakF_UTCtime,
                                   azimuth=self.back_azimuth, f_stat=self.peakF_value, array_d=self.array_dim)
