from io import BytesIO
import os
import datetime
import subprocess

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
    d = {'data': pd.DataFrame(),
        'start': today,
        'end': today - datetime.timedelta(7),
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
    sdata = REPORT_DATA['data'][(REPORT_DATA['data']['_created_at'] >= REPORT_DATA['start']) &
                                (REPORT_DATA['data']['_created_at'] <= REPORT_DATA['end']) &
                                (REPORT_DATA['data']['report_verified'] == 'Yes')]
    
    if len(REPORT_DATA['additional_reports']) > 0:
        # remove reports already in the selected data
        additional_reports = [r for r in REPORT_DATA['additional_reports'] if r not in sdata.index.values]
        ar = REPORT_DATA['data'][REPORT_DATA['data']['report_id'].isin([additional_reports])]
        print(ar)
        sdata = pd.concat([sdata, ar])

    return sdata

def _generate_word_doc(sdata):
        
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
    return FileResponse(outfile)

@app.get("/datatable")
async def get_data_table(request:Request):

    sdata = _get_report_subset()   
    sdata['_created_at'] = sdata['_created_at'].astype(str)
    sdata = sdata.sort_values('report_id')
    records = sdata[['report_id', '_created_at', 'report_headline']].to_dict(orient='records')
    
    if len(sdata) == 0:
        records = [{'report_id':'--', '_created_at':'--', 'report_headline':'--'}]

    return templates.TemplateResponse("./partials/report_table.html", {'rows': records, 'request': request})

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
    data = await file.read()
    REPORT_DATA['data'], REPORT_DATA['related_reports'] = load_report_data(BytesIO(data))
    response = templates.TemplateResponse("./partials/file_uploaded.html", {'file': file.filename, 'request': request})
    response.headers['HX-Trigger'] = 'file-changed'
    return response

@app.get("/")
async def main(request: Request):
    t = REPORT_DATA['start']
    start = '{}/{}/{}'.format(t.month,t.day,t.year) 
    return templates.TemplateResponse("index.html", {'start': start, 'request': request})
