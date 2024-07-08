import re
import os, sys

import pandas as pd
from halo.halo_dtypes import dtypes, converters


REGIONS = ('North America', 
           'Central America', 
           'South America', 
           'Europe',
           'Central Asia',  
           'East Asia/Pacific',  
           'Middle East', 
           'North Africa/Maghreb', 
           'West Africa', 
           'Central Africa',
           'East Africa',
           'Southern Africa',
           )

def load_report_data(fname):

 
    sdata = pd.read_excel(fname, 
                          sheet_name='data', 
                          usecols=dtypes.keys(),
                          converters=converters)

    sdata._created_at = sdata._created_at.dt.tz_localize(None)

    related_report_lookup = sdata[['_record_id','report_id']]
    related_report_lookup = related_report_lookup.set_index('_record_id')

    return sdata, related_report_lookup

class Report:

    def __init__(self, report_data, related_reports_lookup):

        self.reports = report_data
        self.reports['incident_type_two'] = self.reports['incident_type_two'].fillna('None')
        self.reports['weapons_type'] = self.reports['weapons_type'].str.replace(',', ', ')
        self.reports['report_url'] = self.reports['report_url'].str.strip()
        
        self.related_reports_lookup = related_reports_lookup
        self.report_items = []
        top_matter = """
---
toc: true
---

"""
        self.report_items.append(top_matter)

    def __timestamp_to_date(self, ts):
        year = int(ts.year)
        month = int(ts.month)
        day =  int(ts.day)
        date_str = f'{year}-{month:02}-{day:02}'
        return date_str

    def _get_related_reports(self, record_ids):
        
        record_ids = str(record_ids)
        if record_ids == 'nan':
            related_reports = 'None'
        else:
            record_ids = record_ids.split(',')
            related_reports = list(self.related_reports_lookup.loc[record_ids]['report_id'].values)
            related_reports = ', '.join(related_reports)

        return related_reports

    def _clean_url(self, url):

        if type(url) is not str:
            raise TypeError

        if url == 'Unavailable':
            return url 
        
        if url.startswith(('Una', 'Co')):
            url = url.replace('http', '<http')
        else:
            url = '<' + url

        if url.endswith(('(log-in required)', '(login required)')):
            url = url.replace(' (log-in required)', '> (log-in required)')
        else:
            url = url + '>'

        return url


    def create_article(self, article_data):
        """
        """

        article_dict = article_data.to_dict()
        article_dict['incident_date'] = self.__timestamp_to_date(article_dict['incident_date'])
        article_dict['source_date'] = self.__timestamp_to_date(article_dict['report_date'])
        article_dict['related_reports'] = self._get_related_reports(article_dict['related_reports'])

        try:
            article_dict['report_url'] = self._clean_url(article_dict['report_url'])
        except TypeError:
            raise ValueError('report_url not found for report_id = {}'.format(article_dict['report_id']))
            

        p = """
### {report_headline}

{report_summary}

*Report ID: {report_id}*  
*Region: {calc_region}*  
*Country: {calc_country}*   
*Incident Date: {incident_date}*   
*Primary Incident Type: {primary_incident_type}*   
*Secondary Incident Type: {incident_type_two}*   
*Weapons Type(s): {weapons_type}*   
*US Origin: {us_origin_equipment}*   
*Location: {location}*  
*Report URL: {report_url}*  
*Source: {source_name}*   
*Source Date: {source_date}*   
*Multimedia Available: {multimedia_available}*   
*Related Reports: {related_reports}*    

""".format(**article_dict)
        
        return p 


    def create_report(self):

        for region in REGIONS:
            region_data = self.reports[self.reports.calc_region == region]
            region_data = region_data.sort_values('report_id') 
            self.report_items.append('-----\n\n')
            self.report_items.append(f'## {region.upper()}\n')

            for _, article_data in region_data.iterrows():

                p = self.create_article(article_data)
                self.report_items.append(p)

    def save(self, fname):
        with open(fname, 'w+') as fid:
            fid.write(''.join(self.report_items))

