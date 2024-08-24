from io import BytesIO
import os, sys
import datetime
import subprocess
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler(sys.stdout)
log_formatter = logging.basicConfig(format="{levelname}:{name}:{message}", style="{")
stream_handler.setFormatter(log_formatter)
logger.addHandler(stream_handler)

from halo.salw_report import load_report_data, Report 

from typing import Annotated

from fastapi import FastAPI, Request, UploadFile, Form, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse

import pandas as pd

CWD = os.path.dirname(os.path.realpath(__file__))
                      
def initialise_report_data():

    today = datetime.datetime.today()
    d = {'raw_data': None,
         'data': None,
         'start': today - datetime.timedelta(7),
         'end': today,
         'related_reports': [],
         'additional_reports': []}
    
    return d

REPORT_DATA = initialise_report_data()

app = FastAPI()
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(CWD, 'static')) ,
    name="static",
)

templates = Jinja2Templates(directory=os.path.join(CWD, 'templates'))

def to_datetime(d):
    d = [int(x) for x in d.split('/')]
    return datetime.datetime(d[2], d[0], d[1])

def _get_report_subset():
    logger.info('Subset requested')
    logger.info('Start date: {}'.format(REPORT_DATA['start']))
    logger.info('End date: {}'.format(REPORT_DATA['end']))
    
    sdata = REPORT_DATA['data'][(REPORT_DATA['data']['_created_at'] >= REPORT_DATA['start']) &
                                (REPORT_DATA['data']['_created_at'] <= REPORT_DATA['end']) &
                                (REPORT_DATA['data']['report_verified'] == 'Yes')]
    
    logger.info('Number of reports found: {}'.format(len(sdata)))

    if len(REPORT_DATA['additional_reports']) > 0:
        # remove reports already in the selected data
        additional_reports = [r for r in REPORT_DATA['additional_reports'] if r not in sdata.index.values]
        ar = REPORT_DATA['data'][REPORT_DATA['data']['report_id'].isin([additional_reports])]
        sdata = pd.concat([sdata, ar])

    return sdata

def _generate_word_doc(sdata):

    logger.info('Generating .docx')

    sdata = sdata.reset_index()
    r = Report(sdata, REPORT_DATA['related_reports'])
    r.create_report()
    markdown_file = os.path.join(CWD,'tmp', 'salw_report.md')
    output_file = os.path.join(CWD, 'tmp', 'salw_report.docx')
    r.save(markdown_file)
    template_file = os.path.join(CWD, 'tmp', 'custom-reference.docx')    
    proc = ['pandoc', '-o', output_file, '-f', 
            'markdown', '-t', 'docx', markdown_file, 
            '--reference-doc={}'.format(template_file)]

    c = subprocess.run(proc)

    return output_file

@app.get("/downloadreport")
async def download(request:Request):
    sdata = _get_report_subset()
    outfile = _generate_word_doc(sdata)
    return FileResponse(outfile, 
                        media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        filename='salw_report.docx')

@app.get("/datatable")
async def get_data_table(request:Request):

    if REPORT_DATA['data'] is None:
        logger.info('Creating dataframe from raw bytes')
        REPORT_DATA['data'], REPORT_DATA['related_reports'] = load_report_data(BytesIO(REPORT_DATA['raw_data']))

    sdata = _get_report_subset()   
    sdata['_created_at'] = sdata['_created_at'].astype(str)
    sdata = sdata.sort_values('report_id')
    records = sdata[['report_id', '_created_at', 'report_headline']].to_dict(orient='records')
    
    if len(sdata) == 0:
        records = [{'report_id':'--', '_created_at':'--', 'report_headline':'--'}]
        n_reports = 0
    else:
        n_reports = len(records)
    
    start = '{}/{}/{}'.format(REPORT_DATA['start'].day, REPORT_DATA['start'].month, REPORT_DATA['start'].year)
    end = '{}/{}/{}'.format(REPORT_DATA['end'].day, REPORT_DATA['end'].month, REPORT_DATA['end'].year)
        
    return templates.TemplateResponse("./partials/report_table.html", {'rows': records,
                                                                       'n_reports': n_reports, 
                                                                       'start': start, 
                                                                       'end': end,
                                                                       'request': request})

@app.post("/reportoptions/additionalreports")
async def date(additionalReports: Annotated[str, Form()], request:Request):
    ars = [r.strip() for r in additionalReports.split(',')]
    reports = REPORT_DATA['related_reports']['report_id'].to_list()
    isin = [r for r in ars if r in reports]
    msg = 'All reports OK!'
    REPORT_DATA['additional_reports'] = isin
    if (not isin) or (not all(isin)):
        msg = 'Error finding additional reports found, please check Report IDs'
    else:
        msg = 'All reports OK!'

    return templates.TemplateResponse('./partials/additional_reports.html', {'msg': msg, 
                                                                             'additional_reports': additionalReports,
                                                                             'request':request})

@app.post("/reportoptions")
async def date(start: Annotated[str, Form()], end: Annotated[str, Form()], request:Request):
    REPORT_DATA['start'] = to_datetime(start)
    REPORT_DATA['end'] = to_datetime(end)
    response = Response()
    response.headers['HX-Trigger'] = 'file-changed'
    return response

@app.post("/uploadfile")
async def create_upload_file(file: UploadFile, request:Request):
    REPORT_DATA['raw_data'] = await file.read()
    response = templates.TemplateResponse("./partials/file_uploaded.html", {'file': file.filename, 'request': request})
    response.headers['HX-Trigger'] = 'file-changed'
    return response

@app.get("/")
async def main(request: Request):
    REPORT_DATA = initialise_report_data()
    t = REPORT_DATA['start']
    start = '{}/{}/{}'.format(t.month,t.day,t.year) 
    return templates.TemplateResponse("index.html", {'start': start, 'request': request})
