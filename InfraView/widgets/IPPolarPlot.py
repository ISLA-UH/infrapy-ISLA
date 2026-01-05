import numpy as np

import pyqtgraph as pg

from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot

# class IPSlownessSettingsWidget(QGroupBox):

#     def __init__(self, parent):
#         super().__init__(parent)
#         self.setTitle("Slowness Plot")
#         self.beamformingWidget = parent

#         self.buildUI()

#     def buildUI(self):

#         colormap_label = QLabel("Color Map: ")
#         self.colormap_cb = QComboBox()

#         available_maps = pg.colormap.listMaps(source='matplotlib')
#         self.colormap_cb.addItems(available_maps)
#         self.colormap_cb.setCurrentText('jet')

#         #TODO:  Hardwire resolution?  Currently not displayed
#         resolution_label = QLabel("Resolution:")
#         self.resolution_spin = QSpinBox()
#         self.resolution_spin.setRange(10,1000)
#         self.resolution_spin.setMaximumWidth(70)
#         self.resolution_spin.setValue(300)
#         self.resolution_spin.setToolTip("Number of points (horizontal and vertical) that make up the slowness image.
#                                          \nIf you want to 'smooth' the plot, reduce the size of the trace velocity
#                                          step \nsize and the azimuth step size in the beamformer settings.")

#         form1_layout = QFormLayout()
#         form1_layout.addRow(colormap_label, self.colormap_cb)

#         self.setLayout(form1_layout)

#     def settings(self):
#         '''returns the current settings'''
#         settings = {'cmap': self.colormap_cb.currentText()}

#         return settings


class IPSlownessImageItem(pg.ImageItem):
    """
    class for slowness image item
    """
    sig_info_changed = pyqtSignal(str, str)

    def __init__(self, parent):
        """
        initialize

        :param parent: parent image item
        """
        super().__init__()

        self.parent = parent
        self.resolution: int = 0
        self.hr: float = 1.
        self.pps: float = 1.
        self.tracev_range: tuple = ()

    def set_params(self, resolution: int, tracev_range: tuple, pps: float):
        """
        set parameters

        :param resolution: image resolution
        :param tracev_range: trace velocity range
        :param pps: points per slowness unit
        """
        self.resolution = resolution
        self.hr = resolution / 2.
        self.pps = pps
        self.tracev_range = tracev_range

    def hoverEvent(self, event):
        """
        handle hover event

        :param event: hover event
        """
        if not event.isExit():
            pos = event.pos()

            x = (pos.x() - self.hr) / self.pps
            y = (pos.y() - self.hr) / self.pps

            slow = np.sqrt(x**2 + y**2)
            vel = 1./slow

            az = np.degrees(np.arctan2(x, y))

            if vel > self.tracev_range[0] and vel < self.tracev_range[1]:
                info_str1 = 'Velocity: {:3.2f} m/s'.format(vel)
                info_str2 = 'Azimuth: {:3.2f} deg.'.format(az)
                self.sig_info_changed.emit(info_str1, info_str2)


class IPSlownessPlot(pg.PlotItem):
    """
    class for slowness plot
    """
    def __init__(self, parent):
        """
        initialize

        :param parent: parent plot item
        """
        super().__init__()

        self.parent = parent

        self.resolution = 0
        self.hr = 1.
        self.image_item = IPSlownessImageItem(self)
        self.image_item.sig_info_changed.connect(self.update_info_labels)
        self.tracev_range: tuple = ()

        self.addItem(self.image_item)

        self.showAxis('top')
        self.showAxis('right')

        self.vb.setAspectLocked(lock=True, ratio=1)

        # initialize circles
        self.i_circle = pg.QtWidgets.QGraphicsEllipseItem(0, 0, 0, 0)
        self.i_circle.setPen(pg.mkPen(width=3, color='k'))
        self.addItem(self.i_circle)

        self.o_circle = pg.QtWidgets.QGraphicsEllipseItem(0, 0, 0, 0)
        self.o_circle.setPen(pg.mkPen(width=3, color='k'))
        self.addItem(self.o_circle)

        self.info_label1 = pg.LabelItem(text="")
        self.info_label1.setParentItem(self.vb)
        self.info_label1.anchor(itemPos=(0, 0), parentPos=(0, 0))

        self.info_label2 = pg.LabelItem(text="")
        self.info_label2.setParentItem(self.vb)
        self.info_label2.anchor(itemPos=(1, 0), parentPos=(1, 0))
        self.radial_list = []

        ax = self.getAxis('bottom')
        ax.setTicks([])
        ax = self.getAxis('top')
        ax.setTicks([])
        ax = self.getAxis('right')
        ax.setTicks([])
        ax = self.getAxis('left')
        ax.setTicks([])

        cmap = pg.colormap.get('jet', source='matplotlib')
        self.image_item.setColorMap(cmap)

    def update_theme(self, t: str):
        """
        update theme

        :param t: theme type.  Options are 'light' and 'dark'
        """
        if t == 'light':
            self.setBackground((255, 255, 255))
        elif t == 'dark':
            self.setBackground((50, 50, 50))

    def set_image(self, image, resolution: int, tracev_range: tuple):
        """
        set slowness image

        :param image: image data
        :param resolution: image resolution
        :param tracev_range: trace velocity range
        """
        self.resolution = resolution
        self.hr = self.resolution / 2.
        self.tracev_range = tracev_range

        self.pps = self.resolution / (2. / self.tracev_range[0])  # points per 1/vel unit (points per slowness)

        self.setXRange(0, resolution)
        self.setYRange(0, resolution)

        self.image_item.setImage(image)
        self.image_item.set_params(self.resolution, self.tracev_range, self.pps)

        self.draw_radials()
        self.draw_circles()

        self.setAutoVisible(y=True, x=True)
        self.getViewBox().autoRange()

    def update_info_labels(self, info_str1: str, info_str2: str):
        """
        update info labels

        :param info_str1: first info string
        :param info_str2: second info string
        """
        self.info_label1.setText(info_str1)
        self.info_label2.setText(info_str2)

    def draw_radials(self):
        """
        draw radial lines
        """
        count = 8

        angles = np.arange(0, 360, 360. / count)

        # clear old radials
        for rline in self.radial_list:
            self.removeItem(rline)

        for angle in angles:
            r_line = pg.InfiniteLine(pos=(self.hr, self.hr), angle=angle, pen=pg.mkPen((100, 100, 100), width=1,
                                                                                       style=Qt.DotLine))
            self.radial_list.append(r_line)
            self.addItem(r_line)

    def draw_circles(self):
        """
        draw inner and outer circles
        """
        # outer circle
        self.o_circle.setRect(0, 0, self.resolution, self.resolution)

        # inner circle
        lx = (1 / self.tracev_range[0] - 1 / self.tracev_range[1]) * self.pps   # lower x coord
        w = 2. * self.pps / self.tracev_range[1]                               # circle width
        self.i_circle.setRect(lx, lx, w, w)

        # circle_count = 5
        # for r in range(1, circle_count+1):
        #     circle = pg.QtWidgets.QGraphicsEllipseItem(-r / (min_trace_vel*circle_count),
        #                                                -r / (min_trace_vel*circle_count),
        #                                                r * 2 / (min_trace_vel*circle_count),
        #                                                r * 2 / (min_trace_vel*circle_count))
        #     circle.setPen(pg.mkPen(0.75, width=2))
        #     circle.setZValue(10)
        #     self.addItem(circle)

    @pyqtSlot(str)
    def set_colormap(self, map_name: str):
        """
        set colormap

        :param map_name: colormap name
        """
        cmap = pg.colormap.get(map_name, source='matplotlib')
        self.image_item.setColorMap(cmap)

    def clear_slowness(self):
        """
        clear slowness
        """
        self.image_item.clear()
        self.resolution = 0
        self.hr = 1.
        self.tracev_range = ()
