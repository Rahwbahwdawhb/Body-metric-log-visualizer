import pygsheets
import os
import numpy as np
from PyQt6.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QSizePolicy, QLineEdit, QLabel, QComboBox, QTabWidget
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

class visualizerGUI(QWidget):
    def __init__(self,styles={"font-family":"Times New Roman"}):
        crosshair_color="#ff00ff"
        self.right_y_color="k"
        self.right_moving_average_color="r"
        self.left_y_color="b"
        self.left_moving_average_color="g"
        super().__init__()
        # self.setWindowTitle('Body-metric log visualizer')
        # self.setWindowIcon(QIcon('scale.png'))
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
        info_layout=QVBoxLayout()
        info_layout.addWidget(self.infoLabel)
        info_layout.addWidget(self.left_y_data_picker)
        info_layout.addWidget(self.right_y_data_picker)
        
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
        mainGraphLayout=QHBoxLayout()
        mainGraphLayout.addWidget(self.figure,stretch=4)
        mainGraphLayout.addLayout(info_layout,stretch=1)
        layout=QVBoxLayout()
        layout.addLayout(mainGraphLayout)
        # ctrlLayout=QHBoxLayout()
        # self.startLineEdit=QLineEdit()
        # self.endLineEdit=QLineEdit()
        # self.movAvgWindowLineEdit=QLineEdit()
        # self.movAvgWindowLineEdit.setText('7')
        # ctrlLayout.addWidget(QLabel('From, Year,Month,Day:'))
        # ctrlLayout.addWidget(self.startLineEdit)
        # ctrlLayout.addWidget(QLabel('Until, Year,Month,Day:'))
        # ctrlLayout.addWidget(self.endLineEdit)
        # ctrlLayout.addWidget(QLabel('Avg. window:'))
        # ctrlLayout.addWidget(self.movAvgWindowLineEdit)
        # layout.addLayout(ctrlLayout)
        self.setLayout(layout)

        # Add crosshair line
        self.dataPointCircle_asScatterPlot=ScatterPlotItem(size=5,pen=crosshair_color,brush=crosshair_color)
        self.crosshair_v = InfiniteLine(angle=90, movable=False,pen=crosshair_color)
        self.figure.addItem(self.crosshair_v, ignoreBounds=True)
        self.figure.addItem(self.dataPointCircle_asScatterPlot)
        self.proxy = SignalProxy(self.figure.scene().sigMouseMoved, rateLimit=60, slot=self.update_crosshair)

        self.left_right_dict={self.left_y_data_picker:{'axis':'left',
                                                       'viewbox':self.left_y_axis_graph,
                                                       'y_color':self.left_y_color,
                                                       'moving_average_color':self.left_moving_average_color,
                                                       'y_data_label':None,
                                                       'y_data_plot':None,
                                                       'moving_average_color':self.left_moving_average_color,
                                                       'moving_average_plot':None},
                              self.right_y_data_picker:{'axis':'right',
                                                       'viewbox':self.right_y_axis_graph,
                                                       'y_color':self.right_y_color,
                                                       'moving_average_color':self.right_moving_average_color,
                                                       'y_data_label':None,
                                                       'y_data_plot':None,
                                                       'moving_average_color':self.right_moving_average_color,
                                                       'moving_average_plot':None}}
        self.left_y_data_picker.currentTextChanged.connect(self.change_y_data)
        self.right_y_data_picker.currentTextChanged.connect(self.change_y_data)
        self.left_y_data_picker.setCurrentIndex(1)
        self.right_y_data_picker.setCurrentIndex(len(y_data_dict))
        self.startIndex=0
        self.endIndex=len(dates_formatted)
        # self.startLineEdit.returnPressed.connect(self.updateStart)
        # self.endLineEdit.returnPressed.connect(self.updateEnd)
        # self.movAvgWindowLineEdit.returnPressed.connect(self.updateMovAg)
        # self.startLineEdit.setText(dates_formatted[0])
        # self.endLineEdit.setText(dates_formatted[-1])    
        # self.startLineEdit.returnPressed.emit()
        # self.endLineEdit.returnPressed.emit()
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

            self.crosshair_v.setPos(mPx)            
            xIndex=round(mPx)
            self.dataPointCircle_asScatterPlot.clear()
            self.dataPointCircle_asScatterPlot.addPoints([mPx], [y_data_dict[self.left_right_dict[self.left_y_data_picker]['y_data_label']][xIndex]])
            y_str=''
            for label,y_data in y_data_dict.items():
                y_metric,y_unit=label.split(' [')
                # y_metric_moving_avg=movingAvg(y_data,self.moving_avg_window)[xIndex]
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
        # startStr=self.startLineEdit.text()
        self.startIndex=dates_formatted.index(startStr)
        self.figure.setXRange(self.startIndex,self.endIndex,padding=0.002)
    def updateEnd(self,endStr):
        # endStr=self.endLineEdit.text()
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
            self.figure.getAxis(y_dict['axis']).setLabel(y_dict['axis'],'',**self.styles)
            self.figure.getAxis(y_dict['axis']).setTicks('')

class dataCOMP(QWidget):
    def __init__(self,styles={"font-family":"Times New Roman"}):
        super().__init__()
        self.figure=PlotWidget()
        self.figure.setBackground(self.palette().color(QPalette.ColorRole.Window))
        self.legend=self.figure.addLegend(labelTextColor=(0,0,0))
        self.styles=styles

        # x=y_data_dict['Weight [kg]']
        # x=y_data_dict['Body fat [kg]']
        # y=y_data_dict['Waist [cm]']
        x=moving_average_dict['Body fat [kg]']
        y=moving_average_dict['Weight [kg]']
        # y=moving_average_dict['Waist [cm]']

        # Define a continuous gradient
        cmap = ColorMap(
        pos=np.linspace(0, 1, 2),       # gradient positions
        color=[( 0, 0, 255, 100),        # RGBA at pos 0
            (255, 0, 0, 255)]        # at pos 1
            )

        # Map normalized t-values to colors
        t = np.linspace(0, 1, len(x))
        colors = cmap.mapToQColor(t)  # PyQtGraph does the interpolation

        scatter = ScatterPlotItem(x=x, y=y, pen=None, brush=colors, size=10)
        self.figure.plotItem.vb.addItem(scatter)
        # self.figure.plot(y_data_dict['Weight [kg]'],y_data_dict['Body fat [kg]'],pen=None, symbol='o', symbolBrush='r')
        layout=QVBoxLayout()
        layout.addWidget(self.figure)
        self.setLayout(layout)

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
        self.history_plot_widget=visualizerGUI(styles)
        layout=QVBoxLayout()
        tabWidget=QTabWidget()
        tabWidget.addTab(self.history_plot_widget,'History')
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
    def updateEnd(self):
        endStr=self.endLineEdit.text()
        self.history_plot_widget.updateEnd(endStr)
    def updateMovAg(self):
        self.history_plot_widget.updateMovAg(int(self.movAvgWindowLineEdit.text()))


if __name__=='__main__':
    app=QApplication([])
    app.setFont(QFont('Times New Roman'))
    # gui=visualizerGUI()
    gui=mainWindow()
    gui.show()
    app.exec()