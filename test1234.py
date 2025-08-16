#todo:
#add return-to-list button from formula
#split code into separate scripts
#verify recursive parsing with example data that's easier to check

import pygsheets
import os
import numpy as np
from PyQt6.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QSizePolicy, QLineEdit, QLabel, QComboBox, QTabWidget, QRadioButton
from PyQt6.QtCore import QRectF, Qt, QPointF, QPoint
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QPalette, QIcon
from PyQt6.QtWidgets import QGraphicsEllipseItem
from pyqtgraph import PlotWidget, mkPen,mkBrush, InfiniteLine, SignalProxy, CircleROI, ScatterPlotItem, ViewBox, PlotCurveItem, ScatterPlotItem, ColorMap

def get_data(service_account_file='client_secret.json',key_file='key.txt',date_column_index=1):
    """
    Assumes:
     Dates on the form DD/MM
     Years are indicated by blank rows with only the year, e.g. 2022, mentioned in the date column
     That the bottom entry of the date column starts with a year
    """
    os.chdir(os.path.dirname(__file__))
    #authorize
    gc=pygsheets.authorize(service_account_file=service_account_file)
    #open google spreadsheet
    with open(key_file) as f:
        key=f.read()
    worksheet=gc.open_by_key(key)[0]
    date_column=worksheet.get_col(date_column_index)[1:]
    N=len(date_column)
    y_data_columns_id=[('Weight [kg]',2),('Waist [cm]',3),('Body fat [%]',4),('Body fat [kg]',5),('Hydration [%]',6)]
    info_columns_id=[('Activity',7),('Notes',8)]
    y_data_dict={}
    y_data_columns=[]
    for key,i in y_data_columns_id:
        y_data_dict[key]=[]
        y_data_columns.append(worksheet.get_col(i)[1:])
    info_columns_dict={}
    info_columns=[]
    for key,i in info_columns_id:
        info_columns_dict[key]=[]
        info_columns.append(worksheet.get_col(i)[1:])
    dates_formatted=[]
    year_rows=[]
    valid_count=0
    for i,date in enumerate(date_column[::-1]):
        if date=='':
            continue
        try:
            day,month=date.split('/')
            dates_formatted.append(f"{currentYear},{('0'+month)[-2:]},{('0'+day)[-2:]}")
            for ii,(_,_list) in enumerate(y_data_dict.items()):
                y_value=y_data_columns[ii][N-1-i].replace(' ','.')
                if y_value=='' or float(y_value)==0:
                    y_value=np.nan
                else:
                    y_value=float(y_value)
                _list.append(y_value)
            for ii,(_,_list) in enumerate(info_columns_dict.items()):
                _list.append(info_columns[ii][N-1-i])
        except:
            currentYear=date
            year_rows.append((valid_count,date))
        valid_count+=1
    for key,_list in y_data_dict.items():
        y_data_dict[key]=np.array(_list)
    return dates_formatted,y_data_dict,info_columns_dict,year_rows

dates_formatted,y_data_dict,info_columns_dict,year_rows=get_data(service_account_file='client_secret.json',key_file='key.txt')
moving_average_dict={key:None for key in y_data_dict.keys()}

def movingAvg(data,window):
    movAvgData=[]
    halfWindow=window//2
    Ndata=len(data)
    for i in range(Ndata):
        startIndex=np.max([0,i-halfWindow])
        if np.isnan(data[i]):
            movAvgData.append(np.nan)
        else:
            if startIndex==0:
                endIndex=np.max([1,i*2])
            else:
                endIndex=np.min([Ndata-1,startIndex+window])
            dataSlice=data[startIndex:endIndex]
            dataSlide_finite=[d for d in dataSlice if np.isfinite(d)]
            try:
                movAvgData.append(np.mean(dataSlide_finite))
            except:
                movAvgData.append(np.nan)
    return np.array(movAvgData)

class chronological_plotter(QWidget):
    def __init__(self,styles={"font-family":"Times New Roman"}):
        crosshair_color="#ff00ff"
        self.right_y_color="k"
        self.right_moving_average_color="r"
        self.left_y_color="b"
        self.left_moving_average_color="g"
        super().__init__()
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
        for label in y_data_dict.keys():
            self.left_y_data_picker.addItem(label)
            self.right_y_data_picker.addItem(label)
        self.left_y_data_picker.addItem('')
        self.right_y_data_picker.addItem('')
        picker_layout=QHBoxLayout()
        picker_layout.setSpacing(2)
        picker_layout.addStretch(1)
        picker_layout.addWidget(QLabel('Left y-axis:'))
        picker_layout.addWidget(self.left_y_data_picker)
        picker_layout.addStretch(1)
        picker_layout.addWidget(QLabel('Right y-axis:'))
        picker_layout.addWidget(self.right_y_data_picker)
        picker_layout.addStretch(1)
        
        topTicks=[] 
        yCounter=1
        for i,dStr in enumerate(dates_formatted):
            y,m,d=dStr.split(',')
            if m+d=='0101':
                yCounter+=1
                self.left_y_axis_graph.addItem(InfiniteLine(pos=i,angle=90,pen=pen2))
        topTicks=year_rows
        self.figure.getAxis('top').setTicks([topTicks,[]])
        self.figure.getAxis('right').setTicks('')
        self.figure.setBackground(self.palette().color(QPalette.ColorRole.Window))
        
        left_layout=QVBoxLayout()
        left_layout.addWidget(self.figure)
        left_layout.addLayout(picker_layout)
        mainGraphLayout=QHBoxLayout()
        mainGraphLayout.addLayout(left_layout,stretch=4)
        mainGraphLayout.addWidget(self.infoLabel,stretch=1)
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
        self.right_y_data_picker.setCurrentIndex(len(y_data_dict))
        self.startIndex=0
        self.endIndex=len(dates_formatted)
    def update_views(self):
        self.right_y_axis_graph.setGeometry(self.left_y_axis_graph.sceneBoundingRect())
        self.right_y_axis_graph.linkedViewChanged(self.left_y_axis_graph, self.right_y_axis_graph.XAxis)
    def updateMovAg(self,movAvgWindow):
        self.moving_avg_window=movAvgWindow
        for key in moving_average_dict.keys():
            moving_average_dict[key]=movingAvg(y_data_dict[key],self.moving_avg_window)
        for _,y_dict in self.left_right_dict.items():
            if y_dict['y_data_label']:
                if y_dict['moving_average_plot']:
                    y_dict['viewbox'].removeItem(y_dict['moving_average_plot'])
                    self.legend.removeItem(y_dict['moving_average_plot'])
                movAvg=moving_average_dict[y_dict['y_data_label']]
                y_dict['moving_average_plot']=PlotCurveItem(movAvg,pen=mkPen(color=y_dict['moving_average_color'],width=2))
                y_dict['viewbox'].addItem(y_dict['moving_average_plot'])
                self.legend.addItem(y_dict['moving_average_plot'],name=f"{self.moving_avg_window}-day avg.")
    def update_crosshair(self, e):
        pos = e[0]
        if self.figure.sceneBoundingRect().contains(pos):
            mousePoint = self.figure.getPlotItem().vb.mapSceneToView(pos)
            mPx=mousePoint.x()
            if mPx<0:
                mPx=0
            elif mPx>self.xMax:
                mPx=self.xMax
            for data_picker in [self.left_y_data_picker,self.right_y_data_picker]:
                y_dict=self.left_right_dict[data_picker]
                if y_dict['y_data_label']:
                    y_dict['crosshair_vertical_line'].setPos(mPx)
                    y_dict['crosshair_data_point'].clear()
                    xIndex=round(mPx)
                    y_value=y_data_dict[y_dict['y_data_label']][xIndex]
                    if not np.isnan(y_value):
                        y_dict['crosshair_data_point'].addPoints([mPx], [y_value])
            y_str=''
            for label,y_data in y_data_dict.items():
                y_metric,y_unit=label.split(' [')
                y_metric_moving_avg=moving_average_dict[label][xIndex]
                if not np.isnan(y_data[xIndex]):
                    y_str+=f"{y_metric}: {np.round(y_data[xIndex],decimals=1)} (Avg. {np.round(y_metric_moving_avg,decimals=1)}) {y_unit.strip(']')}\n"
                else:
                    y_str+=f"{y_metric}:\n"
            info_str=''
            for label,info in info_columns_dict.items():
                info_str+=f"\n{label}:\n{info[xIndex]}\n"
            self.infoLabel.setText(f"{dates_formatted[xIndex]}\n{y_str}{info_str}")

    def updateStart(self,startStr):
        self.startIndex=dates_formatted.index(startStr)
        self.figure.setXRange(self.startIndex,self.endIndex,padding=0.002)
    def updateEnd(self,endStr):
        self.endIndex=dates_formatted.index(endStr)
        self.figure.setXRange(self.startIndex,self.endIndex,padding=0.002)
    def change_y_data(self,text):
        y_dict=self.left_right_dict[self.sender()]
        if y_dict['y_data_plot']:
            y_dict['viewbox'].removeItem(y_dict['y_data_plot'])
            self.legend.removeItem(y_dict['y_data_plot'])
        if text!='':
            y_dict['y_data_label']=text
            y_dict['y_data_plot']=PlotCurveItem(y_data_dict[y_dict['y_data_label']],pen=y_dict['y_color'])
            self.legend.addItem(y_dict['y_data_plot'],name='Data')
            y_dict['viewbox'].addItem(y_dict['y_data_plot'])
            self.updateMovAg(self.moving_avg_window)
            self.figure.getAxis(y_dict['axis']).setTicks(None)
            self.figure.getAxis(y_dict['axis']).setLabel(text,**self.styles)
            y_dict['viewbox'].setYRange(np.nanmin(y_data_dict[y_dict['y_data_label']])*.95,np.nanmax(y_data_dict[y_dict['y_data_label']])*1.05)
        else:
            if y_dict['moving_average_plot']:
                y_dict['viewbox'].removeItem(y_dict['moving_average_plot'])
                self.legend.removeItem(y_dict['moving_average_plot'])
            y_dict['y_data_label']=None
            y_dict['y_data_plot']=None
            y_dict['moving_average_plot']=None
            self.figure.getAxis(y_dict['axis']).setLabel('',**self.styles)
            self.figure.getAxis(y_dict['axis']).setTicks('')

class dataCOMP(QWidget):
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
        for i,label in enumerate(list(y_data_dict.keys())+['Days',self.x_formula_str]):
            if label!=self.x_formula_str:
                self.data_formula_map_dict[chr(65+i)]=label
                formula_info_str+=f"{chr(65+i)}: {label}\n"
            for picker in [self.y_data_picker,self.x_data_picker]:
                picker.addItem(label)
        self.x_data_picker.setCurrentIndex(1)
        self.y_data_picker.setCurrentIndex(1)
        formula_info_str=formula_info_str[:-1]
        # picker_layout=QHBoxLayout()
        # picker_layout.setSpacing(2)
        # picker_layout.addStretch(1)
        # picker_layout.addWidget(QLabel('y-axis:'))
        # picker_layout.addWidget(self.y_data_picker)
        # picker_layout.addStretch(1)
        # picker_layout.addWidget(QLabel('x-axis:'))
        # picker_layout.addWidget(self.x_data_picker)
        # picker_layout.addStretch(1)
        self.x_formula=QLineEdit()
        self.y_formula=QLineEdit()
        picker_layout=QGridLayout()
        picker_layout.addWidget(QLabel('x-axis:'),0,0)
        picker_layout.addWidget(self.x_formula,0,1)
        picker_layout.addWidget(self.x_data_picker,0,1)
        picker_layout.addWidget(QLabel('y-axis:'),1,0)
        picker_layout.addWidget(self.y_formula,1,1)
        picker_layout.addWidget(self.y_data_picker,1,1)

        self.moving_average_indicator=QRadioButton('Moving average')
        self.data_indicator=QRadioButton('Data')
        radio_button_layout=QVBoxLayout()
        radio_button_layout.addWidget(self.data_indicator)
        radio_button_layout.addWidget(self.moving_average_indicator)
        # picker_layout.addLayout(radio_button_layout)
        picker_layout.addLayout(radio_button_layout,0,2,0,2)
        bottom_layout=QHBoxLayout()
        bottom_layout.addWidget(QLabel(formula_info_str))
        bottom_layout.addLayout(picker_layout)

        layout=QVBoxLayout()
        layout.addWidget(self.figure)
        layout.addLayout(bottom_layout)
        self.setLayout(layout)

        self.moving_average_indicator.clicked.connect(self.change_data_dict)
        self.data_indicator.clicked.connect(self.change_data_dict)
        self.moving_average_indicator.click()
        self.y_data_picker.currentTextChanged.connect(self.change_data)
        self.x_data_picker.currentTextChanged.connect(self.change_data)
        self.x_data_picker.setCurrentIndex(0)
        self.y_data_picker.setCurrentIndex(0)
        self.y_formula.returnPressed.connect(self.enter_formula)
        self.x_formula.returnPressed.connect(self.enter_formula)
    def enter_formula(self):
        formula=self.sender().text()
        if self.sender()==self.y_formula:
            self.y_formula_str=formula
            self.y_data_picker.setItemText(self.y_data_picker.count()-1,formula)
            self.y_data_picker.show()
        else:
            self.x_formula_str=formula
            self.x_data_picker.setItemText(self.y_data_picker.count()-1,formula)
            self.x_data_picker.show()
        self.plot_data()
    def change_data_dict(self):
        if self.sender()==self.moving_average_indicator:
            self.scatter_dict['data_dict']=moving_average_dict
        else:
            self.scatter_dict['data_dict']=y_data_dict
        self.plot_data()
    def change_data(self,text):
        if self.sender()==self.y_data_picker:
            self.scatter_dict['y_label']=text
        if self.sender()==self.x_data_picker:
            self.scatter_dict['x_label']=text
        if text==self.x_formula_str or text==self.y_formula_str:
            if self.sender()==self.y_data_picker:
                self.y_data_picker.hide()
            else:
                self.x_data_picker.hide()
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
            # temp=''
            # is_number=False
            # to_evaluate=[]
            # to_operate=[]
            # for ch in data_label:
            #     if ch.isnumeric():
            #         temp+=ch
            #         is_number=True
            #     elif ch in operators:
            #         if is_number:
            #             to_evaluate.append(float(temp))
            #             is_number=False
            #         temp=''
            #         to_operate.append(ch)
            #     else:
            #         data_symbol=self.data_formula_map_dict[ch]
            #         if data_symbol in self.scatter_dict['data_dict']:
            #             to_evaluate.append(self.scatter_dict['data_dict'][data_symbol])
            #         else:
            #             to_evaluate.append(self.days)
            # to_add_subtract=[to_evaluate[0]]
            # add_subtract_operators=[]
            # # last_operator=''
            # for i,operator in enumerate(to_operate,start=1):
            #     if operator=='*':
            #         # if last_operator in {'*','/'}:
            #         to_add_subtract[-1]=to_add_subtract[-1]*to_evaluate[i]
            #         # else:
            #         #     to_add_subtract.append(to_evaluate[i-1]*to_evaluate[i])
            #     elif operator=='/':
            #         # if last_operator in {'*','/'}:
            #         to_add_subtract[-1]=to_add_subtract[-1]/to_evaluate[i]
            #         # else:
            #         #     to_add_subtract.append(to_evaluate[i-1]/to_evaluate[i])
            #     else:
            #         to_add_subtract.append(to_evaluate[i])
            #         add_subtract_operators.append(operator)
            # full_data_set=to_add_subtract[0]
            # for operator,operand in zip(add_subtract_operators,to_add_subtract[1:]):
            #     if operator=='-':
            #         full_data_set-=operand
            #     else:
            #         full_data_set+=operand

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
class mainWindow(QWidget):
    def __init__(self,styles={"font-family":"Times New Roman"}):
        super().__init__()
        self.setWindowTitle('Body-metric log visualizer')
        self.setWindowIcon(QIcon('scale.png'))
        ctrlLayout=QHBoxLayout()
        self.startLineEdit=QLineEdit()
        self.endLineEdit=QLineEdit()
        self.movAvgWindowLineEdit=QLineEdit()
        self.movAvgWindowLineEdit.setText('7')
        ctrlLayout.addWidget(QLabel('From, Year,Month,Day:'))
        ctrlLayout.addWidget(self.startLineEdit)
        ctrlLayout.addWidget(QLabel('Until, Year,Month,Day:'))
        ctrlLayout.addWidget(self.endLineEdit)
        ctrlLayout.addWidget(QLabel('Avg. window:'))
        ctrlLayout.addWidget(self.movAvgWindowLineEdit)
        self.history_plot_widget=chronological_plotter(styles)
        layout=QVBoxLayout()
        tabWidget=QTabWidget()
        # tabWidget.addTab(self.history_plot_widget,'History')
        self.data_comparison_plot=dataCOMP()
        tabWidget.addTab(self.data_comparison_plot,'Comparison')

        for i in range(tabWidget.count()):
            tab_page = tabWidget.widget(i)   # or the QWidget you created earlier
            pal = tab_page.palette()
            pal.setColor(QPalette.ColorRole.Window, self.history_plot_widget.palette().color(QPalette.ColorRole.Window))
            tab_page.setAutoFillBackground(True)   # important so palette is used
            tab_page.setPalette(pal)
            tab_page.update()

        
        layout.addWidget(tabWidget)
        layout.addLayout(ctrlLayout)
        self.setLayout(layout)

        self.startLineEdit.returnPressed.connect(self.updateStart)
        self.endLineEdit.returnPressed.connect(self.updateEnd)
        self.movAvgWindowLineEdit.returnPressed.connect(self.updateMovAg)
        self.startLineEdit.setText(dates_formatted[0])
        self.endLineEdit.setText(dates_formatted[-1])    
        self.startLineEdit.returnPressed.emit()
        self.endLineEdit.returnPressed.emit()
    def updateStart(self):
        startStr=self.startLineEdit.text()
        self.history_plot_widget.updateStart(startStr)
        self.data_comparison_plot.set_start_index(startStr)
    def updateEnd(self):
        endStr=self.endLineEdit.text()
        self.history_plot_widget.updateEnd(endStr)
        self.data_comparison_plot.set_end_index(endStr)
    def updateMovAg(self):
        self.history_plot_widget.updateMovAg(int(self.movAvgWindowLineEdit.text()))
        self.data_comparison_plot.plot_data()


if __name__=='__main__':
    app=QApplication([])
    app.setFont(QFont('Times New Roman'))
    # gui=chronological_plotter()
    gui=mainWindow()
    gui.show()
    app.exec()