import pygsheets
import os
import numpy as np
from datetime import date,timedelta

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

def get_mock_data():
    """
    Generate mock data for testing

    Outputs:
    dates_formatted: List of strings of the form YYYY,MM,DD for all non-year rows
    data_dict: dictionary with keys=data column descriptors, values=column data values
    info_columns_dict: dictionary with keys=info column descriptors, values=column info strings
    """
    start_date = date(2018,3,22)
    end_date = date(2023,4,9)
    dates_formatted=[str(start_date+timedelta(days=x)).replace('-',',') for x in range((end_date-start_date).days)]
    N=len(dates_formatted)
    data_dict={}
    for key in ['Weight [kg]','Waist [cm]','Body fat [%]','Body fat [kg]','Hydration [%]']:
        data_dict[key]=np.sin(np.linspace(1,N,N)+2*np.pi*np.random.random(1))*N/40+N/2+np.random.random(N)*N/20
    info_columns_dict={}
    for key in ['Activity','Notes']:
        info_columns_dict[key]=[''.join([chr(int(np.random.random(1)*1000)) for _ in range(int(20*np.random.random(1)))]) for _ in range(N)]
    return dates_formatted,data_dict,info_columns_dict

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

def recursive_parse(str_to_parse,data_formula_map_dict,data_dict,days):
    """
    Evaluate a string-input formula to numerical values, recursive calls will be made whenever a ( symbol
    is encountered. Supported formula operations are: +, -, *, /

    Inputs:
    str_to_parse: formula string to evaluate
    data_formula_map_dict: dictionary with keys=data symbol, values=data label/ID in data_dict
    data_dict: dictionary with keys=data label/ID in data_dict, values=data corresponding to the data label
    days: numpy array with day count

    Outputs:
    result: numerical values of the evaluated formula
    iter: count of how many characters that were recursively evaluated (the function call that issued the 
          recursive call should skip ahead this many characters for subsequent evaluation)
    """
    operators={'*','+','-','/'}
    str_to_parse.replace(' ','')
    temp=''
    is_number=False
    to_evaluate=[]
    to_operate=[]
    iter=0
    while iter<len(str_to_parse):
        ch=str_to_parse[iter]
        iter+=1
        if ch=='(':
            rec_result,rec_iter=recursive_parse(str_to_parse[iter:],data_formula_map_dict,data_dict,days)
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
            data_symbol=data_formula_map_dict[ch]
            if data_symbol in data_dict:
                to_evaluate.append(data_dict[data_symbol])
            else:
                to_evaluate.append(days)
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