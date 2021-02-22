# Scape NC COVID-19 Data

## Overview

This code serves as a proof of concept for automating the process of grabbing COVID-19 infection and death data for North Carolina municipalities from the PowerBI visualization on the wake.gov site (https://covid19.wakegov.com/). There are three parts to the POC:

1. Data request and processing
2. Data persistence 
3. Automation 

Each part is (more or less) independent and can be replaced by any number of alternative programming languages, SaaS platforms, etc.

The POC currently looks like this:

1. COVID-19 infection and death is requested from a PowerBI endpoint via a Python script
2. The requested data is processed and stored in Google Sheets (the sheet is accessible here: https://docs.google.com/spreadsheets/d/1-NFykHBH36Wf35VL7ndAPojXguMhbptJAarxFYVNgrw/edit#gid=21159925)
3. The above two steps are automated by running a cron job. Infection data and death data are each requested once per hour, but separately. Infection data is requested on the hour; death data is requested at the half hour.

### 1. Data request and processing

The file `scrapeWakeCovidData.py` is a Python 3 script that sends a POST request to a PowerBI endpoint, processes the response, then uploads the data to Google Sheets (this last step will be covered in the next section). 

All Python dependencies are held in the file `requirements.txt` and easily pip installable via PyPI.

#### Data request

The script is run with one of two arguments: 

1. infections
2. deaths

which determine the POST data that is sent to the PowerBI endpoint. The POST data is held in the variables `infection_post_data` and `death_post_data` respectively and the endpoint used in the request is in the variable `url`. If rewriting the data request part of this script in another language or using another service, you'll need to reuse these values. 

#### Data processing

The response from the PowerBI endpoint is a JSON blob. It's not meant to be human readable, so processing it took a bit of trial and error. The section of the JSON blob holding the infection or death data is extracted via the `scrape_powerbi_data` method and stored in the variable `data`.

The PowerBI endpoint regularly rejects the Python script's request with a 401 Unauthorized HTTP Status Code. I'm not exactly sure how or why this happens, but scraping the endpoint every hour seems to yield a high enough success rate that we don't need to worry about it too much.

### 2. Data persistence  

The COVID-19 data is stored in Google Sheets. The Python library `gspread` (https://gspread.readthedocs.io/en/latest/) does the heavy lifting. 

#### GSpread setup

The initial steps to configure everything for gspread are pretty minimal. You need to enable an API Access Endpoint in the Google account being used, then you need to create a Service Account. These steps are covered in these two parts of the docs respectively: 

- https://gspread.readthedocs.io/en/latest/oauth2.html#enable-api-access-for-a-project
- https://gspread.readthedocs.io/en/latest/oauth2.html#for-bots-using-service-account

Once that is done, you need to create a new Google Sheet and share it (giving write access) to the email address automatically generated for the Service Account. 

In the script, the Google Sheet is searched for by name and that name is hardcoded in the `sheet_name` variable. The path to the Service Account credentials file is also hardcoded in the `service_account_file` variable. Both of these need to be updated if/when migrating this process to another Google account.

#### Data upload

The data is uploaded to Google Sheets in the `send_data_to_gsheet` method. It should be pretty straightforward in a successful case. All infection or death data is organized by column, and we log the time the request was made and whether or not the request was successful.

When the POST request (from the *Data processing* section) fails, we still log the request in Google Sheets, but the `success` column (#2) is marked as `FALSE` and all data fields are given a value of -1.

### 3. Automation

All automation is handled by the `cron` utility. Two requests are made each hour. On the hour, infection data is requested; on the half hour, death data is requested. The cron jobs look like this:

```
0 * * * * /opt/nc-covid-scrape/ve/nc-covid-scrape/bin/python3 /opt/nc-covid-scrape/scrapeWakeCovidData.py infections
30 * * * * /opt/nc-covid-scrape/ve/nc-covid-scrape/bin/python3 /opt/nc-covid-scrape/scrapeWakeCovidData.py deaths
```

