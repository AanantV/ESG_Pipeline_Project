import os
import sys
import requests
import pandas as pd
#from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()

def get_salesforce_access_token():
    consumer_key = os.environ['SF_CONSUMER_KEY']
    consumer_secret = os.environ['SF_CONSUMER_SECRET']
    refresh_token = os.environ['SF_REFRESH_TOKEN']

    token_url = "https://login.salesforce.com/services/oauth2/token"

    payload = {
        'grant_type': 'refresh_token',
        'client_id': consumer_key,
        'client_secret': consumer_secret,
        'refresh_token': refresh_token,
    }

    response = requests.post(token_url, data = payload)

    try:
        response.raise_for_status()
        if response.status_code == 200:
            data = response.json()
            print("Access token: " + data.get('access_token'))
            print("Instance URL: " + data.get('instance_url'))
            return data['access_token'], data['instance_url']
        

    except Exception as e:
        print(f'Request Access Failed: {e}')

def extract_emissions_records(access_token, instance_url):
    query = ('SELECT Name,Business_Unit__c, Reporting_Period__c, Scope__c, Source__c, CO2_Tons__c FROM Emissions_Record__c ')
    url = f'{instance_url}/services/data/v60.0/query'

    headers = {'Authorization': f'Bearer {access_token}'}

    response = requests.get(url, headers = headers, params = {'q': query})
    response.raise_for_status()
    result = response.json()

    print(result)
    
token,url = get_salesforce_access_token()
extract_emissions_records(token, url)
    