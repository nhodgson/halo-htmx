import datetime
import pandas as pd

from halo.halo_dtypes import dtypes, converters
from salw_report import Report

sdata = pd.read_excel('/Users/sarah/Desktop/Copy_of_salw_project_data.xlsx', 
                    sheet_name='data', 
                    usecols=dtypes.keys(),
                    converters=converters)

sdata._created_at = sdata._created_at.dt.tz_localize(None)

start_date =  datetime.datetime(2022, 12, 1)
end_date =  datetime.datetime(2022, 12, 15)

related_report_lookup = sdata[['_record_id','report_id']]
related_report_lookup = related_report_lookup.set_index('_record_id')

sdata = sdata[(sdata._created_at >= start_date) &
              (sdata._created_at <= end_date) &
              (sdata.report_verified == 'Yes')]

r = Report(sdata, related_report_lookup)
r.create_report()
r.save('../data/salw_test_04082022.md')

# pandoc -o salw_27072022.docx -f markdown -t docx salw_test_27072022.md --reference-doc=custom-reference.docx