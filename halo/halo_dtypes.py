import datetime
import pandas as pd 

dtypes = {
    '_record_id' : str, 
    '_created_at': datetime.datetime, 
    'report_id': str, 
    'region_and_country': str, 
    'incident_date': datetime.datetime,
    'primary_incident_type': str, 
    'incident_type_two': str, 
    'weapons_type': str,
    'us_origin_equipment': str, 
    'location': str,
    'report_headline': str, 
    'report_summary': str,
    'reporter_name': str, 
    'report_text': str, 
    'source': str, 
    'report_date': datetime.datetime, 
    'report_url': str,
    'related_reports': str, 
    'multimedia_available': str, 
    'photos': str, 
    'photos_captions': str,
    'videos': str, 
    'report_url_link': str, 
    'calc_country': str, 
    'calc_region': str, 
    'source_name': str,
    'report_verified': str,
}

converters = {
    'incident_date': pd.to_datetime, 
    'report_date': pd.to_datetime, 
    '_created_at': pd.to_datetime,
}