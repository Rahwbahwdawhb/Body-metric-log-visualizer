#todo:
#split code into separate scripts
#verify recursive parsing with example data that's easier to check
#same vertical size of self.x_picker_show, self.y_formula and self.x_data_picker
#stop lower outline of self.y_formula from vanishing when hovering above it
#option to display data as lines or dots for both views
#display formula instructions when hovering over some icon that appears when clicking formula

import pygsheets
import os
import numpy as np
from PyQt6.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QLayout, QLineEdit, QLabel, QComboBox, QTabWidget, QRadioButton, QPushButton
from PyQt6.QtCore import QRectF, Qt, QPointF, QPoint
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QPalette, QIcon
from PyQt6.QtWidgets import QGraphicsEllipseItem
from pyqtgraph import PlotWidget, mkPen,mkBrush, InfiniteLine, SignalProxy, CircleROI, ScatterPlotItem, ViewBox, PlotCurveItem, ScatterPlotItem, ColorMap

def get_data(service_account_file='key.json',spreadsheet_id_file='spreadsheet_id.txt'):
    """
    Parse Google spreadsheet data
    Inputs:
    service_account_file: Google Service Account key of .json-format 
    spreadsheet_id_file: .txt-file containing the spreadsheet ID

    See readMe.txt for details.

    Outputs:
    dates_formatted: List of strings of the form YYYY,MM,DD for all non-year rows
    data_dict: dictionary with keys=data column descriptors, values=column data values
    info_columns_dict: dictionary with keys=info column descriptors, values=column info strings

    Assumes the spread sheet data to be of the form:
    Column 1: Dates of the format DD/MM, e.g. 1/7 (1st of June), 21/8 (21st of August), 1/12 (1st of December), 23/12 (23rd of December)
              Years are indicated in this column as a single entry, e.g. 2024, all other columns of such rows should be empty
              The most recent dates should be at the top of the spreadsheet
    Column 2: Weight, in units of kg
    Column 3: Waist circumference in units of cm
    Column 4: Body fat in units of %
    Column 5: Body fat in units of kg
    Column 6: Hydration in units of %
    Column 7: Activity (Text input)
    Column 8: Notes (Text input)
    """
    os.chdir(os.path.dirname(__file__))
    #authorize
    gc=pygsheets.authorize(service_account_file=service_account_file)
    #open google spreadsheet
    with open(spreadsheet_id_file) as f:
        key=f.read()
    worksheet=gc.open_by_key(key)[0]
    date_column=worksheet.get_col(1)[1:]
    N=len(date_column)
    data_columns_id=[('Weight [kg]',2),('Waist [cm]',3),('Body fat [%]',4),('Body fat [kg]',5),('Hydration [%]',6)]
    info_columns_id=[('Activity',7),('Notes',8)]
    data_dict={}
    data_columns=[]
    for key,i in data_columns_id:
        data_dict[key]=[]
        data_columns.append(worksheet.get_col(i)[1:])
    info_columns_dict={}
    info_columns=[]
    for key,i in info_columns_id:
        info_columns_dict[key]=[]
        info_columns.append(worksheet.get_col(i)[1:])
    dates_formatted=[]
    valid_count=0
    for i,date in enumerate(date_column[::-1]):
        if date=='':
            continue
        try:
            day,month=date.split('/')
            dates_formatted.append(f"{currentYear},{('0'+month)[-2:]},{('0'+day)[-2:]}")
            for ii,(_,_list) in enumerate(data_dict.items()):
                y_value=data_columns[ii][N-1-i].replace(' ','.')
                if y_value=='' or float(y_value)==0:
                    y_value=np.nan
                else:
                    y_value=float(y_value)
                _list.append(y_value)
            for ii,(_,_list) in enumerate(info_columns_dict.items()):
                _list.append(info_columns[ii][N-1-i])
        except:
            currentYear=date
        valid_count+=1
    for key,_list in data_dict.items():
        data_dict[key]=np.array(_list)
    return dates_formatted,data_dict,info_columns_dict

dates_formatted,data_dict,info_columns_dict=get_data()
moving_average_dict={key:None for key in data_dict.keys()}

def moving_average(data,window):
    """
    Moving average calculation

    Inputs:
    data: iterable containing data values
    window: size of moving average window
    
    Output: numpy array with moving average values
    """
    moving_average_data=[]
    half_window=window//2
    N=len(data)
    for i in range(N):
        start_index=np.max([0,i-half_window])
        if np.isnan(data[i]):
            moving_average_data.append(np.nan)
        else:
            if start_index==0:
                end_index=np.max([1,i*2])
            else:
                end_index=np.min([N-1,start_index+window])
            data_slice=data[start_index:end_index]
            data_slice_finite=[d for d in data_slice if np.isfinite(d)]
            try:
                moving_average_data.append(np.mean(data_slice_finite))
            except:
                moving_average_data.append(np.nan)
    return np.array(moving_average_data)

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

class chronological_plotter(QWidget):
    """
    GUI-object for displaying data as a time series (days on the bottom x-axis and year-ticks on the top x-axis)
    """
    def __init__(self,styles={"font-family":"Times New Roman"}):
        super().__init__()
        crosshair_color="#ff00ff"
        self.right_y_color="k"
        self.right_moving_average_color="r"
        self.left_y_color="b"
        self.left_moving_average_color="g"
        self.figure=PlotWidget()
        self.legend=self.figure.addLegend(labelTextColor=(0,0,0))
        self.styles=styles
        self.right_y_axis_graph=ViewBox()
        self.left_y_axis_graph=self.figure.plotItem.vb
        self.figure.plotItem.scene().addItem(self.right_y_axis_graph)
        self.figure.plotItem.getAxis('right').linkToView(self.right_y_axis_graph)
        self.right_y_axis_graph.setXLink(self.figure.plotItem)
        
        self.xMax=len(dates_formatted)-1
        self.moving_avg_window=7
        self.left_y_axis_graph.sigResized.connect(self.update_views)

        self.figure.setLabel('bottom','Days elapsed [#]',**self.styles)
        self.figure.getAxis('left').setTextPen('k')
        self.figure.getAxis('bottom').setTextPen('k')
        self.figure.getAxis('left').setPen('k')
        self.figure.getAxis('bottom').setPen('k')
        self.figure.setLabel('top','')
        self.figure.setLabel('right','')
        self.figure.getAxis('top').setPen('k')
        self.figure.getAxis('top').setTextPen('k')
        self.figure.getAxis('right').setPen('k')
        
        self.infoLabel=QLabel()
        self.infoLabel.setWordWrap(True)
        self.infoLabel.setAlignment(Qt.AlignmentFlag.AlignTop)
        pen2=mkPen(color=(0,0,0),style=Qt.PenStyle.DashLine)
        
        self.left_y_data_picker=QComboBox()
        self.right_y_data_picker=QComboBox()
        for label in data_dict.keys():
            self.left_y_data_picker.addItem(label)
            self.right_y_data_picker.addItem(label)
        self.left_y_data_picker.addItem('')
        self.right_y_data_picker.addItem('')
        picker_layout=stack_in_layout([('stretch',1),QLabel('Left y-axis:'),self.left_y_data_picker,('stretch',1),
                                       QLabel('Right y-axis:'),self.right_y_data_picker,('stretch',1)],'h')
        picker_layout.setSpacing(2)
        year_rows=[]
        for i,dStr in enumerate(dates_formatted):
            y,m,d=dStr.split(',')
            if m+d=='0101':
                year_rows.append((i,y))
                self.left_y_axis_graph.addItem(InfiniteLine(pos=i,angle=90,pen=pen2))
        self.figure.getAxis('top').setTicks([year_rows,[]])
        self.figure.getAxis('right').setTicks('')
        self.figure.setBackground(self.palette().color(QPalette.ColorRole.Window))

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
        self.left_y_data_picker.currentTextChanged.connect(self.change_y_data)
        self.right_y_data_picker.currentTextChanged.connect(self.change_y_data)
        #the 1st added item is set to current, change to update moving averages and then change back
        self.left_y_data_picker.setCurrentIndex(1)
        self.left_y_data_picker.setCurrentIndex(0)
        self.right_y_data_picker.setCurrentIndex(len(data_dict))
        self.start_index=0
        self.end_index=len(dates_formatted)
    def update_views(self):
        """
        Function for updating the scaling of the right y-axis, required for proper appearance
        """
        self.right_y_axis_graph.setGeometry(self.left_y_axis_graph.sceneBoundingRect())
        self.right_y_axis_graph.linkedViewChanged(self.left_y_axis_graph, self.right_y_axis_graph.XAxis)
    def update_moving_average(self,moving_average_window):
        self.moving_avg_window=moving_average_window
        for key in moving_average_dict.keys():
            moving_average_dict[key]=moving_average(data_dict[key],self.moving_avg_window)
        for _,y_dict in self.left_right_dict.items():
            if y_dict['y_data_label']:
                if y_dict['moving_average_plot']:
                    y_dict['viewbox'].removeItem(y_dict['moving_average_plot'])
                    self.legend.removeItem(y_dict['moving_average_plot'])
                moving_average_values=moving_average_dict[y_dict['y_data_label']]
                y_dict['moving_average_plot']=PlotCurveItem(moving_average_values,pen=mkPen(color=y_dict['moving_average_color'],width=2))
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
                    y_value=data_dict[y_dict['y_data_label']][x_index]
                    if not np.isnan(y_value):
                        y_dict['crosshair_data_point'].addPoints([x_position], [y_value])
            y_str=''
            if 'x_index' in locals():
                for label,y_data in data_dict.items():
                    y_metric,y_unit=label.split(' [')
                    y_metric_moving_avg=moving_average_dict[label][x_index]
                    if not np.isnan(y_data[x_index]):
                        y_str+=f"{y_metric}: {np.round(y_data[x_index],decimals=1)} (Avg. {np.round(y_metric_moving_avg,decimals=1)}) {y_unit.strip(']')}\n"
                    else:
                        y_str+=f"{y_metric}:\n"
            info_str=''
            for label,info in info_columns_dict.items():
                info_str+=f"\n{label}:\n{info[x_index]}\n"
            self.infoLabel.setText(f"{dates_formatted[x_index]}\n{y_str}{info_str}")
    def update_start(self,startStr):
        self.start_index=dates_formatted.index(startStr)
        self.figure.setXRange(self.start_index,self.end_index,padding=0.002)
    def update_end(self,endStr):
        self.end_index=dates_formatted.index(endStr)
        self.figure.setXRange(self.start_index,self.end_index,padding=0.002)
    def change_y_data(self,text):
        y_dict=self.left_right_dict[self.sender()]
        if y_dict['y_data_plot']:
            y_dict['viewbox'].removeItem(y_dict['y_data_plot'])
            self.legend.removeItem(y_dict['y_data_plot'])
        if text!='':
            y_dict['crosshair_vertical_line'].show()
            y_dict['crosshair_data_point'].show()
            y_dict['y_data_label']=text
            y_dict['y_data_plot']=PlotCurveItem(data_dict[y_dict['y_data_label']],pen=y_dict['y_color'])
            self.legend.addItem(y_dict['y_data_plot'],name='Data')
            y_dict['viewbox'].addItem(y_dict['y_data_plot'])
            self.update_moving_average(self.moving_avg_window)
            self.figure.getAxis(y_dict['axis']).setTicks(None)
            self.figure.getAxis(y_dict['axis']).setLabel(text,**self.styles)
            y_dict['viewbox'].setYRange(np.nanmin(data_dict[y_dict['y_data_label']])*.95,np.nanmax(data_dict[y_dict['y_data_label']])*1.05)
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
    def __init__(self,styles={"font-family":"Times New Roman"}):
        super().__init__()
        self.figure=PlotWidget()
        self.figure.setBackground(self.palette().color(QPalette.ColorRole.Window))
        self.legend=self.figure.addLegend(labelTextColor=(0,0,0))
        self.styles=styles
        self.days=np.linspace(1,len(dates_formatted),len(dates_formatted))
        self.scatter_dict={'x_label':None,'x_data':None,'y_label':None,'y_data':None,
                           'data_dict':None,'start_index':0,'end_index':len(dates_formatted)}
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
        for i,label in enumerate(list(data_dict.keys())+['Days',self.x_formula_str]):
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
        radio_button_layout=stack_in_layout([self.data_indicator,self.moving_average_indicator])
        picker_layout.addLayout(radio_button_layout,0,2,0,2)
        bottom_layout=stack_in_layout([QLabel(formula_info_str),picker_layout],'h')
        layout=stack_in_layout([self.figure,bottom_layout])
        self.setLayout(layout)

        self.moving_average_indicator.clicked.connect(self.change_data_dict)
        self.data_indicator.clicked.connect(self.change_data_dict)
        self.moving_average_indicator.click()
        self.x_data_picker.activated.connect(self.change_data)
        self.y_data_picker.activated.connect(self.change_data)
        self.x_data_picker.activated.emit(0)        
        self.y_data_picker.activated.emit(0)
        self.y_formula.returnPressed.connect(self.enter_formula)
        self.x_formula.returnPressed.connect(self.enter_formula)
        self.y_picker_show.pressed.connect(self.show_picker)
        self.x_picker_show.pressed.connect(self.show_picker)
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
    def change_data_dict(self):
        if self.sender()==self.moving_average_indicator:
            self.scatter_dict['data_dict']=moving_average_dict
        else:
            self.scatter_dict['data_dict']=data_dict
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
        self.scatter_dict['start_index']=dates_formatted.index(startStr)
        self.plot_data()
    def set_end_index(self,endStr):
        self.scatter_dict['end_index']=dates_formatted.index(endStr)
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
                full_data_set=self.scatter_dict['data_dict'][data_label]
        if evaluate_formula:
            operators={'*','+','-','/'}
            data_label.replace(' ','')
            def recursive_parse(str_to_parse):
                temp=''
                is_number=False
                to_evaluate=[]
                to_operate=[]
                iter=0
                while iter<len(str_to_parse):
                    ch=str_to_parse[iter]
                    iter+=1
                    if ch=='(':
                        rec_result,rec_iter=recursive_parse(str_to_parse[iter:])
                        to_evaluate.append(rec_result)
                        iter+=rec_iter
                    elif ch==')':
                        break
                    elif ch.isnumeric():
                        temp+=ch
                        is_number=True
                    elif ch in operators:
                        if is_number:
                            to_evaluate.append(float(temp))
                            is_number=False
                        temp=''
                        to_operate.append(ch)
                    else:
                        data_symbol=self.data_formula_map_dict[ch]
                        if data_symbol in self.scatter_dict['data_dict']:
                            to_evaluate.append(self.scatter_dict['data_dict'][data_symbol])
                        else:
                            to_evaluate.append(self.days)
                if temp!='':
                    to_evaluate.append(float(temp))
                to_add_subtract=[to_evaluate[0]]
                add_subtract_operators=[]
                for i,operator in enumerate(to_operate,start=1):
                    if operator=='*':
                        to_add_subtract[-1]=to_add_subtract[-1]*to_evaluate[i]
                    elif operator=='/':
                        to_add_subtract[-1]=to_add_subtract[-1]/to_evaluate[i]
                    else:
                        to_add_subtract.append(to_evaluate[i])
                        add_subtract_operators.append(operator)
                result=to_add_subtract[0]
                for operator,operand in zip(add_subtract_operators,to_add_subtract[1:]):
                    if operator=='-':
                        result-=operand
                    else:
                        result+=operand
                return result,iter
            full_data_set,_=recursive_parse(data_label)
        return full_data_set[self.scatter_dict['start_index']:self.scatter_dict['end_index']+1]
    def plot_data(self):
        try:
            self.figure.plotItem.vb.removeItem(self.scatter)
        except:
            pass
        if self.scatter_dict['x_label'] is not None and self.scatter_dict['y_label'] is not None:
            x_data=self.get_data('x_label')
            self.colors = self.cmap.mapToQColor(np.linspace(0, 1, len(x_data)))
            self.scatter = ScatterPlotItem(x=x_data, y=self.get_data('y_label'), pen=None, brush=self.colors, size=10)
            self.figure.plotItem.vb.addItem(self.scatter)
class main_window(QWidget):
    def __init__(self,styles={"font-family":"Times New Roman"}):
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
        self.history_plot_widget=chronological_plotter(styles)
        tab_widget=QTabWidget()
        tab_widget.addTab(self.history_plot_widget,'History')
        self.data_comparison_plot=data_analysis_plotter()
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
    app=QApplication([])
    app.setFont(QFont('Times New Roman'))
    gui=main_window()
    gui.show()
    app.exec()