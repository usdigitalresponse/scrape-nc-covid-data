"""
This is a script to scrape COVID19 data from the PowerBI visualization for Wake County NC:
	- https://covid19.wakegov.com/
	- https://app.powerbigov.us/view?r=eyJrIjoiNTIwNTg4NzktNjEzOC00NmVhLTg0OWMtNDEzNGEyM2I4MzhlIiwidCI6ImM1YTQxMmQxLTNhYmYtNDNhNC04YzViLTRhNTNhNmNjMGYyZiJ9

This script:
- scrapes infection and death data from all Wake counties 
- appends the results to a Google Sheet

Create the cron job to run this script every four hours:
	0 * * * * /path/to/python3 scrapeWakeCovidData.py infections
	30 * * * * /path/to/python3 scrapeWakeCovidData.py deaths 
"""

import sys
import requests
import json
import gspread
from datetime import datetime
from time import sleep

url = 'https://wabi-us-gov-virginia-api.analysis.usgovcloudapi.net/public/reports/querydata?synchronous=true'
infection_post_data = "{\"version\":\"1.0.0\",\"queries\":[{\"Query\":{\"Commands\":[{\"SemanticQueryDataShapeCommand\":{\"Query\":{\"Version\":2,\"From\":[{\"Name\":\"c1\",\"Entity\":\"COVID19 Cases\",\"Type\":0}],\"Select\":[{\"Column\":{\"Expression\":{\"SourceRef\":{\"Source\":\"c1\"}},\"Property\":\"City (groups)\"},\"Name\":\"COVID19 Cases.City (groups)\"},{\"Measure\":{\"Expression\":{\"SourceRef\":{\"Source\":\"c1\"}},\"Property\":\"Confirmed Cases\"},\"Name\":\"COVID19 Cases.Confirmed Cases\"}],\"OrderBy\":[{\"Direction\":1,\"Expression\":{\"Column\":{\"Expression\":{\"SourceRef\":{\"Source\":\"c1\"}},\"Property\":\"City (groups)\"}}}]},\"Binding\":{\"Primary\":{\"Groupings\":[{\"Projections\":[0,1]}]},\"DataReduction\":{\"DataVolume\":4,\"Primary\":{\"Window\":{\"Count\":1000}}},\"Version\":1}}}]},\"QueryId\":\"\",\"ApplicationContext\":{\"DatasetId\":\"13d0297e-cd45-4c40-886a-9ac95733bf66\",\"Sources\":[{\"ReportId\":\"41cc676d-758a-4e98-bb6d-2611acfdbdf8\"}]}}],\"cancelQueries\":[],\"modelId\":428118}"

death_post_data = "{\"version\":\"1.0.0\",\"queries\":[{\"Query\":{\"Commands\":[{\"SemanticQueryDataShapeCommand\":{\"Query\":{\"Version\":2,\"From\":[{\"Name\":\"c1\",\"Entity\":\"COVID19 Cases\",\"Type\":0}],\"Select\":[{\"Column\":{\"Expression\":{\"SourceRef\":{\"Source\":\"c1\"}},\"Property\":\"City (groups)\"},\"Name\":\"COVID19 Cases.City (groups)\"},{\"Measure\":{\"Expression\":{\"SourceRef\":{\"Source\":\"c1\"}},\"Property\":\"Total Deaths\"},\"Name\":\"COVID19 Cases.Total Deaths\"}],\"OrderBy\":[{\"Direction\":1,\"Expression\":{\"Column\":{\"Expression\":{\"SourceRef\":{\"Source\":\"c1\"}},\"Property\":\"City (groups)\"}}}]},\"Binding\":{\"Primary\":{\"Groupings\":[{\"Projections\":[0,1]}]},\"DataReduction\":{\"DataVolume\":4,\"Primary\":{\"Window\":{\"Count\":1000}}},\"Version\":1}}}]},\"CacheKey\":\"{\\\"Commands\\\":[{\\\"SemanticQueryDataShapeCommand\\\":{\\\"Query\\\":{\\\"Version\\\":2,\\\"From\\\":[{\\\"Name\\\":\\\"c1\\\",\\\"Entity\\\":\\\"COVID19 Cases\\\",\\\"Type\\\":0}],\\\"Select\\\":[{\\\"Column\\\":{\\\"Expression\\\":{\\\"SourceRef\\\":{\\\"Source\\\":\\\"c1\\\"}},\\\"Property\\\":\\\"City (groups)\\\"},\\\"Name\\\":\\\"COVID19 Cases.City (groups)\\\"},{\\\"Measure\\\":{\\\"Expression\\\":{\\\"SourceRef\\\":{\\\"Source\\\":\\\"c1\\\"}},\\\"Property\\\":\\\"Total Deaths\\\"},\\\"Name\\\":\\\"COVID19 Cases.Total Deaths\\\"}],\\\"OrderBy\\\":[{\\\"Direction\\\":1,\\\"Expression\\\":{\\\"Column\\\":{\\\"Expression\\\":{\\\"SourceRef\\\":{\\\"Source\\\":\\\"c1\\\"}},\\\"Property\\\":\\\"City (groups)\\\"}}}]},\\\"Binding\\\":{\\\"Primary\\\":{\\\"Groupings\\\":[{\\\"Projections\\\":[0,1]}]},\\\"DataReduction\\\":{\\\"DataVolume\\\":4,\\\"Primary\\\":{\\\"Window\\\":{\\\"Count\\\":1000}}},\\\"Version\\\":1}}}]}\",\"QueryId\":\"\",\"ApplicationContext\":{\"DatasetId\":\"13d0297e-cd45-4c40-886a-9ac95733bf66\",\"Sources\":[{\"ReportId\":\"41cc676d-758a-4e98-bb6d-2611acfdbdf8\"}]}}],\"cancelQueries\":[],\"modelId\":428118}"

sheet_name = 'Wake county municipality COVID19'
service_account_file = '/opt/nc-covid-scrape/usdr-nc-covid-7afc8b3be71c.json'

def scrape_powerbi_data(url, post_data):
    try:
        r = requests.post(url,data=post_data)
        data_status_code = r.status_code
        j = json.loads(r.text)
        data_timestamp = ''
        #data_title = j['results'][0]['result']['data']['descriptor']['Select'][1]['Name']
        data = j['results'][0]['result']['data']['dsr']['DS'][0]['PH'][0]['DM0']
    except json.decoder.JSONDecodeError:
        data = []
        data_timestamp = ''

    return [data, data_timestamp, data_status_code]

def send_data_to_gsheet(sheet, data, data_timestamp, data_status_code):
    city_data_list = [ item['C'] for item in data]

    sheet_header = sheet.get('A1:1')[0]

    scrape_data = [
                ['timestamp', str(datetime.now())],
                ['success', bool(data_status_code == 200)],
                ['data_timestamp', data_timestamp]
               ]

    data_row = [-1] * len(sheet_header)
    #for column, value in scrape_data + city_data_list:
    for item in scrape_data + city_data_list:
        try:
            # column = town 
            # value = infections/deaths
            column = item[0]
            value = item[1]

            index = sheet_header.index(column)
            data_row[index] = value
        except ValueError:  # if the town doesn't exist in the current sheet
            sheet_header.append(column)
            data_row.append(value)
        except IndexError:  # if only a town is provided; no value
            index = sheet_header.index(column)
            data_row[index] = -1

    # write data to gsheets
    sheet.append_row(data_row)
    # replace header
    sheet.insert_row(sheet_header, index=1)
    sheet.delete_row(index=2)
    sheet.format(range_name='A1:1', cell_format={'textFormat': {'bold': True}})

def help():
    print('\nScrape COVID19 data from Wake county PowerBI visualization' + \
          '\nUsage: \n\tpython3 scrapeWakeCovidData.py [infections|deaths]')
    #sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        help()
    report = sys.argv[1]

    if report == 'infections':
        data = scrape_powerbi_data(url, infection_post_data)
        gc = gspread.service_account(filename=service_account_file)
        sheet = gc.open(sheet_name).worksheet('Scrape Infections')
        send_data_to_gsheet(sheet, *data)
    elif report == 'deaths':
        data = scrape_powerbi_data(url, death_post_data)
        gc = gspread.service_account(filename=service_account_file)
        sheet = gc.open(sheet_name).worksheet('Scrape Deaths')
        send_data_to_gsheet(sheet, *data)
    else:
        help()


