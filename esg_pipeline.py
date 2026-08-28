import os
import sys
import pandas as pd
from google.cloud import bigquery
from dotenv import load_dotenv
import requests

load_dotenv()

def get_salesforce_url():
    try: 
        consumer_key = os.environ['SF_CONSUMER_KEY']
        consumer_secret = os.environ['SF_CONSUMER_SECRET']
        refresh_token = os.environ['SF_REFRESH_TOKEN']

        token_url = 'https://login.salesforce.com/services/oauth2/token'
        payload = {
            'grant_type': 'refresh_token',
            'client_id': consumer_key,
            'client_secret': consumer_secret,
            'refresh_token': refresh_token
        }

        response = requests.post(token_url, data = payload)
        response.raise_for_status()
        if response.status_code == 200:
            data = response.json()

            print(f"Instance URL: {data.get('instance_url')}")
            print(f"Access Token: {data.get('access_token')}")

            return data['access_token'], data['instance_url']
        
    except Exception as e:
        print(f'Salesforce retrieval failed: {e}')
    
def extract_emission_records(access_token, instance_url):

    try:
        query = ('SELECT Name, Business_Unit__c,CO2_Tons__c,Reporting_Period__c,Scope__c,Source__c FROM Emissions_Record__c')

        url = f"{instance_url}/services/data/v60.0/query"
        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.get(url, headers = headers, params = {"q": query})
        response.raise_for_status()
        if response.status_code == 200:
            result = response.json()
            records = result.get('records',[])

            if not records:
                print('\nNo records available in the pull')
                return pd.DataFrame()
            for r in records:
                r.pop('attributes', None)
            df = pd.DataFrame(records)
            print(f'Extracted {len(df)} records from salesforce')
            print('Updated Dataframe\n')
            print(df)
            return df
    
    except Exception as e:
        print(f'Data Extraction failed: {e}')
    
def transform_records(df):
    try:
        if df.empty:
            print('No data available in dataframe')

        df = df.rename(columns={
            'Name': 'salesforce_id',
            'Business_Unit__c': 'business_unit',
            'CO2_Tons__c': 'co2_tons',
            'Reporting_Period__c': 'reporting_period',
            'Scope__c': 'scope',
            'Source__c': 'source'
        })

        df['co2_tons'] = pd.to_numeric(df['co2_tons'], errors = 'coerce')
        before = len(df)
        df = df.dropna(subset = ['co2_tons'])
        dropped = before - len(df)
        if dropped:
            print(f'Length of dataframe changed from {before} to {dropped} after dropping invalid values')
        print('\nColumn names updated')
        print('Fetching cleaned Dataframe....\n')
        print(df)
        return df
    
    except Exception as e:
        print(f'Column rename failed: {e}')

def load_to_bigquery(df, project_id, dataset, table):
    try:
        if df.empty:
            print('No data available in dataframe')
        
        client = bigquery.Client(project = project_id)      #connects with the project
        table_id = f'{project_id}.{dataset}.{table}'

        job_config = bigquery.LoadJobConfig(
            write_disposition = 'WRITE_TRUNCATE',
            autodetect = True
        )

        load_job = client.load_table_from_dataframe(df, table_id, job_config = job_config)
        load_job.result()

        table_ref = client.get_table(table_id)
        print(f'Loaded {table_ref.num_rows} rows in {table_id}')

    except Exception as e:
        print(f'BigQuery Dataload failed: {e}')

def main():
    try:
        project_id = os.environ['GCP_PROJECT_ID']
        dataset = os.environ['BQ_DATASET']
        table = os.environ['BQ_TABLE']
    except Exception as e:
        print(f'Variable Fetch failed: {e}')
        sys.exit(1)

    print('ESG Pipeline Started....')

    print('Retrieving Salesforce Credentials....')
    access_token, instance_url = get_salesforce_url()
    print('Successfully retireved salesforce credentials')

    print('Extracting Records from Salesforce...')
    cleaned_df = extract_emission_records(access_token, instance_url)
    print('Successfully retrieved records from Salesforce')

    print('Transforming Column names to bigquery standards....')
    transform_records(cleaned_df)
    print('returned dataframe with changed column names')

    print('Loading Data to big query....')
    load_to_bigquery(cleaned_df, project_id, dataset, table)
    print('Dataload successful')
    print('Pipeline Execution Success')    

if __name__ == '__main__':
    main()
