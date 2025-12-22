from typing import Optional, Tuple

from obspy.core.inventory import Inventory


class IPInfrasoundArray(object):
    """
    class for infrasound array
    """
    def __init__(self, inventory: Optional[Inventory] = None, a_name: str = ""):
        """
        initialize

        :param inventory: obspy inventory object for the array
        :param a_name: name of the array
        """
        self._array_name = a_name
        self._inv = inventory

    def set_name(self, name: str):
        """
        set the array's name

        :param name: name of the array
        """
        # set the arrays name
        self._array_name = name

    def name(self) -> str:
        """
        :return: the array's name
        """
        # return the arrays name
        return self._array_name

    def set_inventory(self, inventory: Inventory):
        """
        set the array's inventory

        :param inventory: obspy inventory object for the array
        """
        self._inv = inventory

    def station_center(self) -> Tuple[float, float]:
        """
        :return: the lat, lon center of the stations in the array
        """
        center_lat = 0.
        center_lon = 0.

        count = 0   # The number of stations in the array

        if self._inv is None:
            raise ValueError("Inventory is not set for the array; no stations to calculate center.")
        for network in self._inv:
            for station in network:
                center_lat += station.latitude
                center_lon += station.longitude

                count += 1

        center_lat = center_lat / count
        center_lon = center_lon / count

        return center_lat, center_lon

    def avg_elevation(self) -> Optional[float]:
        """
        :return: the average elevation of the stations in the array or None if no stations
        """
        avg_elevation = 0.

        count = 0   # The number of stations in the array

        if self._inv is None:
            raise ValueError("Inventory is not set for the array; no stations to calculate average elevation.")
        for network in self._inv:
            for station in network:
                avg_elevation += station.elevation

                count += 1

        if count == 0:
            return None

        return avg_elevation / count
