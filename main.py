#todo:
#verify recursive parsing with example data that's easier to check
#same vertical size of self.x_picker_show, self.y_formula and self.x_data_picker
#stop lower outline of self.y_formula from vanishing when hovering above it
#display formula instructions when hovering over some icon that appears when clicking formula
#fix bug that selects text in a different widget when choosing formula

import numpy as np
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QGridLayout, QLineEdit, QLabel, QComboBox, QTabWidget, QRadioButton, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPalette, QIcon
from pyqtgraph import mkPen, InfiniteLine, SignalProxy, ScatterPlotItem, ViewBox, PlotCurveItem, ScatterPlotItem, ColorMap

from frontend_utils import stack_in_layout, get_prepared_plot_widget, QLabel_applied_stylesheet
from backend import get_data, get_mock_data, moving_average, recursive_parse

class chronological_plotter(QWidget):
    """
    GUI-object for displaying data as a time series (days on the bottom x-axis and year-ticks on the top x-axis)
    """
    def __init__(self,dates_formatted,data_dict,moving_average_dict,info_columns_dict,styles={"font-family":"Times New Roman"}):
        super().__init__()
        self.dates_formatted=dates_formatted
        self.days=np.linspace(0,len(self.dates_formatted)-1,len(self.dates_formatted))
        self.data_dict=data_dict
        self.moving_average_dict=moving_average_dict
        self.info_columns_dict=info_columns_dict

        crosshair_color="#ff00ff"
        self.right_y_color="k"
        self.right_moving_average_color="r"
        self.left_y_color="b"
        self.left_moving_average_color="g"
        self.figure=get_prepared_plot_widget(self.palette().color(QPalette.ColorRole.Window))
        self.legend=self.figure.addLegend(labelTextColor=(0,0,0))
        self.styles=styles
        self.right_y_axis_graph=ViewBox()
        self.left_y_axis_graph=self.figure.plotItem.vb
        self.figure.plotItem.scene().addItem(self.right_y_axis_graph)
        self.figure.plotItem.getAxis('right').linkToView(self.right_y_axis_graph)
        self.right_y_axis_graph.setXLink(self.figure.plotItem)
        
        self.xMax=len(self.dates_formatted)-1
        self.moving_avg_window=7
        self.left_y_axis_graph.sigResized.connect(self.update_views)

        self.figure.setLabel('bottom','Days elapsed [#]',**self.styles)
        
        self.infoLabel=QLabel()
        self.infoLabel.setWordWrap(True)
        self.infoLabel.setAlignment(Qt.AlignmentFlag.AlignTop)
        pen2=mkPen(color=(0,0,0),style=Qt.PenStyle.DashLine)
        
        self.left_y_data_picker=QComboBox()
        self.right_y_data_picker=QComboBox()
        for label in self.data_dict.keys():
            self.left_y_data_picker.addItem(label)
            self.right_y_data_picker.addItem(label)
        self.left_y_data_picker.addItem('')
        self.right_y_data_picker.addItem('')
        self.dots_rb=QRadioButton('Dots')
        self.dots_rb.clicked.connect(self.change_plot_type)
        self.lines_rb=QRadioButton('Lines')
        self.lines_rb.clicked.connect(self.change_plot_type)
        dots_lines_layout=stack_in_layout([self.dots_rb,self.lines_rb])
        picker_layout=stack_in_layout([('stretch',1),QLabel('Left y-axis:'),self.left_y_data_picker,('stretch',1),
                                       QLabel('Right y-axis:'),self.right_y_data_picker,('stretch',1),
                                       QLabel('Show data as: '),dots_lines_layout,('stretch',1)],'h')
        picker_layout.setSpacing(2)
        year_rows=[]
        for i,dStr in enumerate(self.dates_formatted):
            y,m,d=dStr.split(',')
            if m+d=='0101':
                year_rows.append((i,y))
                self.left_y_axis_graph.addItem(InfiniteLine(pos=i,angle=90,pen=pen2))
        self.figure.getAxis('top').setTicks([year_rows,[]])

        left_layout=stack_in_layout([self.figure,picker_layout])
        mainGraphLayout=stack_in_layout([(left_layout,4),(self.infoLabel,1)],'h')
        layout=QVBoxLayout()
        layout.addLayout(mainGraphLayout)
        self.setLayout(layout)

        # Add crosshair line
        self.dataPointCircle_left=ScatterPlotItem(size=5,pen=crosshair_color,brush=crosshair_color)
        self.dataPointCircle_left.setZValue(1000)
        self.crosshair_v_left = InfiniteLine(angle=90, movable=False,pen=crosshair_color)
        self.left_y_axis_graph.addItem(self.crosshair_v_left, ignoreBounds=True)
        self.left_y_axis_graph.addItem(self.dataPointCircle_left)        
        self.dataPointCircle_right=ScatterPlotItem(size=5,pen=crosshair_color,brush=crosshair_color)
        self.dataPointCircle_right.setZValue(1000)
        self.crosshair_v_right = InfiniteLine(angle=90, movable=False,pen=crosshair_color)
        self.right_y_axis_graph.addItem(self.crosshair_v_right, ignoreBounds=True)
        self.right_y_axis_graph.addItem(self.dataPointCircle_right)
        self.proxy = SignalProxy(self.figure.scene().sigMouseMoved, rateLimit=60, slot=self.update_crosshair)
        
        self.left_right_dict={self.left_y_data_picker:{'axis':'left',
                                                       'viewbox':self.left_y_axis_graph,
                                                       'y_color':self.left_y_color,
                                                       'moving_average_color':self.left_moving_average_color,
                                                       'y_data_label':None,
                                                       'y_data_plot':None,
                                                       'moving_average_color':self.left_moving_average_color,
                                                       'moving_average_plot':None,
                                                       'crosshair_data_point':self.dataPointCircle_left,
                                                       'crosshair_vertical_line':self.crosshair_v_left},
                              self.right_y_data_picker:{'axis':'right',
                                                       'viewbox':self.right_y_axis_graph,
                                                       'y_color':self.right_y_color,
                                                       'moving_average_color':self.right_moving_average_color,
                                                       'y_data_label':None,
                                                       'y_data_plot':None,
                                                       'moving_average_color':self.right_moving_average_color,
                                                       'moving_average_plot':None,
                                                       'crosshair_data_point':self.dataPointCircle_right,
                                                       'crosshair_vertical_line':self.crosshair_v_right}}
        self.lines_rb.click()
        self.left_y_data_picker.currentTextChanged.connect(self.change_y_data)
        self.right_y_data_picker.currentTextChanged.connect(self.change_y_data)
        #the 1st added item is set to current, change to update moving averages and then change back
        self.left_y_data_picker.setCurrentIndex(1)
        self.left_y_data_picker.setCurrentIndex(0)
        self.right_y_data_picker.setCurrentIndex(len(self.data_dict))
        self.start_index=0
        self.end_index=len(self.dates_formatted)
    def update_views(self):
        """
        Function for updating the scaling of the right y-axis, required for proper appearance
        """
        self.right_y_axis_graph.setGeometry(self.left_y_axis_graph.sceneBoundingRect())
        self.right_y_axis_graph.linkedViewChanged(self.left_y_axis_graph, self.right_y_axis_graph.XAxis)
    def update_moving_average(self,moving_average_window):
        self.moving_avg_window=moving_average_window
        for key in self.moving_average_dict.keys():
            self.moving_average_dict[key]=moving_average(self.data_dict[key],self.moving_avg_window)
        for _,y_dict in self.left_right_dict.items():
            if y_dict['y_data_label']:
                if y_dict['moving_average_plot']:
                    y_dict['viewbox'].removeItem(y_dict['moving_average_plot'])
                    self.legend.removeItem(y_dict['moving_average_plot'])
                moving_average_values=self.moving_average_dict[y_dict['y_data_label']]
                y_dict['moving_average_plot']=self.plot_type(self.days,moving_average_values,pen=mkPen(color=y_dict['moving_average_color'],width=2),brush=y_dict['moving_average_color'])
                y_dict['viewbox'].addItem(y_dict['moving_average_plot'])
                self.legend.addItem(y_dict['moving_average_plot'],name=f"{self.moving_avg_window}-day avg.")
    def update_crosshair(self, e):
        pos = e[0]
        if self.figure.sceneBoundingRect().contains(pos):
            cursor_position = self.figure.getPlotItem().vb.mapSceneToView(pos)
            x_position=cursor_position.x()
            if x_position<0:
                x_position=0
            elif x_position>self.xMax:
                x_position=self.xMax
            for data_picker in [self.left_y_data_picker,self.right_y_data_picker]:
                y_dict=self.left_right_dict[data_picker]
                if y_dict['y_data_label']:
                    y_dict['crosshair_vertical_line'].setPos(x_position)
                    y_dict['crosshair_data_point'].clear()
                    x_index=round(x_position)
                    y_value=self.data_dict[y_dict['y_data_label']][x_index]
                    if not np.isnan(y_value):
                        y_dict['crosshair_data_point'].addPoints([x_position], [y_value])
            y_str=''
            if 'x_index' in locals():
                for label,y_data in self.data_dict.items():
                    y_metric,y_unit=label.split(' [')
                    y_metric_moving_avg=self.moving_average_dict[label][x_index]
                    if not np.isnan(y_data[x_index]):
                        y_str+=f"{y_metric}: {np.round(y_data[x_index],decimals=1)} (Avg. {np.round(y_metric_moving_avg,decimals=1)}) {y_unit.strip(']')}\n"
                    else:
                        y_str+=f"{y_metric}:\n"
            info_str=''
            for label,info in self.info_columns_dict.items():
                info_str+=f"\n{label}:\n{info[x_index]}\n"
            self.infoLabel.setText(f"{self.dates_formatted[x_index]}\n{y_str}{info_str}")
    def update_start(self,startStr):
        self.start_index=self.dates_formatted.index(startStr)
        self.figure.setXRange(self.start_index,self.end_index,padding=0.002)
    def update_end(self,endStr):
        self.end_index=self.dates_formatted.index(endStr)
        self.figure.setXRange(self.start_index,self.end_index,padding=0.002)
    def change_plot_type(self):
        if self.sender()==self.dots_rb:
            self.plot_type=ScatterPlotItem
        else:
            self.plot_type=PlotCurveItem
        for _,y_dict in self.left_right_dict.items():
            if y_dict['y_data_label']:
                self.change_y_data(y_dict['y_data_label'],y_dict)
    def change_y_data(self,text,y_dict=None):
        if not y_dict:
            y_dict=self.left_right_dict[self.sender()]
        if y_dict['y_data_plot']:
            y_dict['viewbox'].removeItem(y_dict['y_data_plot'])
            self.legend.removeItem(y_dict['y_data_plot'])
        if text!='':
            y_dict['crosshair_vertical_line'].show()
            y_dict['crosshair_data_point'].show()
            y_dict['y_data_label']=text
            y_dict['y_data_plot']=self.plot_type(self.days,self.data_dict[y_dict['y_data_label']],pen=mkPen(color=y_dict['y_color']),brush=y_dict['y_color'])
            self.legend.addItem(y_dict['y_data_plot'],name='Data')
            y_dict['viewbox'].addItem(y_dict['y_data_plot'])
            self.update_moving_average(self.moving_avg_window)
            self.figure.getAxis(y_dict['axis']).setTicks(None)
            self.figure.getAxis(y_dict['axis']).setLabel(text,**self.styles)
            y_dict['viewbox'].setYRange(np.nanmin(self.data_dict[y_dict['y_data_label']])*.95,np.nanmax(self.data_dict[y_dict['y_data_label']])*1.05)
        else:
            if y_dict['moving_average_plot']:
                y_dict['viewbox'].removeItem(y_dict['moving_average_plot'])
                self.legend.removeItem(y_dict['moving_average_plot'])
            y_dict['y_data_label']=None
            y_dict['y_data_plot']=None
            y_dict['moving_average_plot']=None
            y_dict['crosshair_vertical_line'].hide()
            y_dict['crosshair_data_point'].hide()
            self.figure.getAxis(y_dict['axis']).setLabel('',**self.styles)
            self.figure.getAxis(y_dict['axis']).setTicks('')

class data_analysis_plotter(QWidget):
    """
    GUI-object for displaying a scatter plot with user-defined data on the x- and y-axes
    """
    def __init__(self,dates_formatted,data_dict,moving_average_dict,styles={"font-family":"Times New Roman"}):
        super().__init__()
        self.dates_formatted=dates_formatted
        self.data_dict=data_dict
        self.moving_average_dict=moving_average_dict

        self.figure=get_prepared_plot_widget(self.palette().color(QPalette.ColorRole.Window))
        self.styles=styles
        self.days=np.linspace(1,len(self.dates_formatted),len(self.dates_formatted))
        self.scatter_dict={'x_label':None,'x_data':None,'y_label':None,'y_data':None,
                           'data_plot_dict':None,'start_index':0,'end_index':len(self.dates_formatted)}
        self.x_formula_str='Formula'
        self.y_formula_str='Formula'
        # Define a continuous gradient
        self.cmap = ColorMap(
        pos=np.linspace(0, 1, 2),       # gradient positions
        color=[( 0, 0, 255, 100),        # RGBA at pos 0
            (255, 0, 0, 255)]        # at pos 1
            )

        self.y_data_picker=QComboBox()
        self.x_data_picker=QComboBox()
        self.data_formula_map_dict={}
        formula_info_str=''
        for i,label in enumerate(list(self.data_dict.keys())+['Days',self.x_formula_str]):
            if label!=self.x_formula_str:
                self.data_formula_map_dict[chr(65+i)]=label
                formula_info_str+=f"{chr(65+i)}: {label}\n"
            for picker in [self.y_data_picker,self.x_data_picker]:
                picker.addItem(label)
        self.x_data_picker.setCurrentIndex(1)
        self.y_data_picker.setCurrentIndex(1)
        formula_info_str=formula_info_str[:-1]
        self.x_formula=QLineEdit()
        self.x_picker_show=QPushButton('List')
        self.x_picker_show.hide()
        self.y_formula=QLineEdit()
        self.y_picker_show=QPushButton('List')
        self.y_picker_show.hide()
        picker_layout=QGridLayout()
        picker_layout.addWidget(QLabel('x-axis:'),0,0)
        picker_layout.addLayout(stack_in_layout([self.x_formula,self.x_picker_show],'h'),0,1)
        picker_layout.addWidget(self.x_data_picker,0,1)
        picker_layout.addWidget(QLabel('y-axis:'),1,0)
        picker_layout.addLayout(stack_in_layout([self.y_formula,self.y_picker_show],'h'),1,1)
        picker_layout.addWidget(self.y_data_picker,1,1)

        self.moving_average_indicator=QRadioButton('Moving average')
        self.data_indicator=QRadioButton('Data')
        data_ma_layout=stack_in_layout([QLabel_applied_stylesheet('Data set',"text-decoration: underline;"),self.data_indicator,self.moving_average_indicator])
        data_ma_widget=QWidget()
        data_ma_widget.setLayout(data_ma_layout)
        self.dots_rb=QRadioButton('Dots')
        self.dots_rb.clicked.connect(self.change_plot_type)
        self.lines_rb=QRadioButton('Lines')
        self.lines_rb.clicked.connect(self.change_plot_type)
        dots_lines_layout=stack_in_layout([QLabel_applied_stylesheet('Show data as',"text-decoration: underline;"),self.dots_rb,self.lines_rb])
        dots_lines_widget=QWidget()
        dots_lines_widget.setLayout(dots_lines_layout)
        bottom_layout=stack_in_layout([data_ma_widget,dots_lines_widget,stack_in_layout([('stretch',3),picker_layout,('stretch',1)])],'h')
        layout=stack_in_layout([self.figure,bottom_layout])
        self.setLayout(layout)

        self.moving_average_indicator.clicked.connect(self.change_data_plot_dict)
        self.data_indicator.clicked.connect(self.change_data_plot_dict)
        self.moving_average_indicator.click()
        self.x_data_picker.activated.connect(self.change_data)
        self.y_data_picker.activated.connect(self.change_data)
        self.x_data_picker.activated.emit(0)        
        self.y_data_picker.activated.emit(0)
        self.y_formula.returnPressed.connect(self.enter_formula)
        self.x_formula.returnPressed.connect(self.enter_formula)
        self.y_picker_show.pressed.connect(self.show_picker)
        self.x_picker_show.pressed.connect(self.show_picker)
        self.dots_rb.click()
    def show_picker(self):
        if self.sender()==self.y_picker_show:
            self.y_data_picker.show()
            self.y_picker_show.hide()
        else:
            self.x_data_picker.show()
            self.x_picker_show.hide()
    def enter_formula(self):
        formula=self.sender().text()
        if self.sender()==self.y_formula:
            self.y_formula_str=formula
            picker=self.y_data_picker
        else:
            self.x_formula_str=formula
            picker=self.x_data_picker
        picker.setItemText(self.y_data_picker.count()-1,formula)
        picker.activated.emit(self.y_data_picker.count()-1)
        self.plot_data()
    def change_data_plot_dict(self):
        if self.sender()==self.moving_average_indicator:
            self.scatter_dict['data_plot_dict']=self.moving_average_dict
        else:
            self.scatter_dict['data_plot_dict']=self.data_dict
        self.plot_data()
    def change_data(self):
        text=self.sender().currentText()
        if self.sender()==self.y_data_picker:
            self.scatter_dict['y_label']=text
        if self.sender()==self.x_data_picker:
            self.scatter_dict['x_label']=text
        if text==self.x_formula_str or text==self.y_formula_str:
            if self.sender()==self.y_data_picker:
                self.y_data_picker.hide()
                self.y_picker_show.show()
            else:
                self.x_data_picker.hide()
                self.x_picker_show.show()
        else:
            self.plot_data()
    def set_start_index(self,startStr):
        self.scatter_dict['start_index']=self.dates_formatted.index(startStr)
        self.plot_data()
    def set_end_index(self,endStr):
        self.scatter_dict['end_index']=self.dates_formatted.index(endStr)
        self.plot_data()
    def get_data(self,xy_label):
        data_label=self.scatter_dict[xy_label]
        evaluate_formula=False
        match data_label:
            case self.x_formula_str:
                evaluate_formula=True
                self.x_formula_str=data_label
            case self.y_formula_str:
                evaluate_formula=True
                self.y_formula_str=data_label
            case 'Days':
                full_data_set=self.days
            case _:
                full_data_set=self.scatter_dict['data_plot_dict'][data_label]
        if evaluate_formula:
            full_data_set,_=recursive_parse(data_label,self.data_formula_map_dict,self.scatter_dict['data_plot_dict'],self.days)
        return full_data_set[self.scatter_dict['start_index']:self.scatter_dict['end_index']+1]
    def change_plot_type(self):
        if self.sender()==self.dots_rb:
            self.scatter_dict['plot_type']='dots'
        else:
            self.scatter_dict['plot_type']='lines'
        self.plot_data()
    def plot_data(self):
        try:
            self.figure.plotItem.vb.removeItem(self.plot)
        except:
            pass
        if self.scatter_dict['x_label'] is not None and self.scatter_dict['y_label'] is not None:
            x_data=self.get_data('x_label')
            if self.scatter_dict['plot_type']=='dots':
                self.colors = self.cmap.mapToQColor(np.linspace(0, 1, len(x_data)))
                self.plot = ScatterPlotItem(x=x_data, y=self.get_data('y_label'), pen=None, brush=self.colors, size=10)
            else:
                self.plot = PlotCurveItem(x=x_data, y=self.get_data('y_label'), pen='b', size=2)
            self.figure.plotItem.vb.addItem(self.plot)
class main_window(QWidget):
    def __init__(self,dates_formatted,data_dict,moving_average_dict,info_columns_dict,styles={"font-family":"Times New Roman"}):
        super().__init__()
        self.setWindowTitle('Body-metric log visualizer')
        self.setWindowIcon(QIcon('scale.png'))
        self.start_line_edit=QLineEdit()
        self.end_line_edit=QLineEdit()
        self.moving_avgerage_window_line_edit=QLineEdit()
        self.moving_avgerage_window_line_edit.setText('7')
        ctrlLayout=stack_in_layout([QLabel('From, Year,Month,Day:'),self.start_line_edit,
                                    QLabel('Until, Year,Month,Day:'),self.end_line_edit,
                                    QLabel('Avg. window:'),self.moving_avgerage_window_line_edit],'h')
        self.history_plot_widget=chronological_plotter(dates_formatted,data_dict,moving_average_dict,info_columns_dict,styles)
        tab_widget=QTabWidget()
        tab_widget.addTab(self.history_plot_widget,'History')
        self.data_comparison_plot=data_analysis_plotter(dates_formatted,data_dict,moving_average_dict,styles)
        tab_widget.addTab(self.data_comparison_plot,'Comparison')

        for i in range(tab_widget.count()):
            tab_page = tab_widget.widget(i)
            pal = tab_page.palette()
            pal.setColor(QPalette.ColorRole.Window, self.history_plot_widget.palette().color(QPalette.ColorRole.Window))
            tab_page.setAutoFillBackground(True)   # important so palette is used
            tab_page.setPalette(pal)
            tab_page.update()

        layout=stack_in_layout([tab_widget,ctrlLayout])
        self.setLayout(layout)

        self.start_line_edit.returnPressed.connect(self.update_start)
        self.end_line_edit.returnPressed.connect(self.update_end)
        self.moving_avgerage_window_line_edit.returnPressed.connect(self.update_moving_average)
        self.start_line_edit.setText(dates_formatted[0])
        self.end_line_edit.setText(dates_formatted[-1])    
        self.start_line_edit.returnPressed.emit()
        self.end_line_edit.returnPressed.emit()
    def update_start(self):
        startStr=self.start_line_edit.text()
        self.history_plot_widget.update_start(startStr)
        self.data_comparison_plot.set_start_index(startStr)
    def update_end(self):
        endStr=self.end_line_edit.text()
        self.history_plot_widget.update_end(endStr)
        self.data_comparison_plot.set_end_index(endStr)
    def update_moving_average(self):
        self.history_plot_widget.update_moving_average(int(self.moving_avgerage_window_line_edit.text()))
        self.data_comparison_plot.plot_data()

if __name__=='__main__':
    mock_bool=False
    if mock_bool:
        dates_formatted,data_dict,info_columns_dict=get_mock_data()
    else:
        dates_formatted,data_dict,info_columns_dict=get_data()
    moving_average_dict={key:None for key in data_dict.keys()}

    app=QApplication([])
    app.setFont(QFont('Times New Roman'))
    gui=main_window(dates_formatted,data_dict,moving_average_dict,info_columns_dict)
    gui.show()
    app.exec()