from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLayout
from pyqtgraph import PlotWidget
def stack_in_layout(QItems_list,layout_type='v'):
    """
    Stack QWidgets and/or QLayouts into a QHBoxLayout or QVBoxLayout, the stacking follows the order of QItems_list

    Inputs:
    QItems_list: iterable containing QWidgets or QLayouts to be stacked
    layout_type: 'v' to stack into a QVBoxLayout, any other value will stack into a QHBoxLayout

    Output: the stacked QHBoxLayout or QVBoxLayout
    """
    if layout_type=='v':
        layout=QVBoxLayout()
    else:
        layout=QHBoxLayout()
    for QItem in QItems_list:
        if isinstance(QItem,QWidget):
            layout.addWidget(QItem)
        elif isinstance(QItem,QLayout):
            layout.addLayout(QItem)
        elif isinstance(QItem,tuple):
            if QItem[0]=='stretch':
                layout.addStretch(QItem[1])
            elif isinstance(QItem[0],QLayout) and isinstance(QItem[1],int):
                layout.addLayout(QItem[0],stretch=QItem[1])
            elif isinstance(QItem[0],QWidget) and isinstance(QItem[1],int):
                layout.addWidget(QItem[0],stretch=QItem[1])
    return layout

def get_prepared_plot_widget(palette=None):
    figure=PlotWidget()
    figure.getAxis('left').setTextPen('k')
    figure.getAxis('bottom').setTextPen('k')
    figure.getAxis('left').setPen('k')
    figure.getAxis('bottom').setPen('k')
    figure.setLabel('top','')
    figure.setLabel('right','')
    figure.getAxis('top').setPen('k')
    figure.getAxis('top').setTextPen('k')
    figure.getAxis('right').setPen('k')
    figure.getAxis('top').setTicks('')
    figure.getAxis('right').setTicks('')
    if palette:
        figure.setBackground(palette)
    return figure