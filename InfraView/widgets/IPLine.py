from PyQt5.QtCore import QLine


class IPLine(QLine):
    """
    class for Line
    """
    my_zValue = 20

    def __init__(self):
        """
        initialize
        """
        super().__init__()
        self.setZValue(self.my_zValue)
