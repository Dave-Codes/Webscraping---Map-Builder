# Code for ETL operations on USDA-FS geospatial data

# Imports

import pandas as pd 
import numpy as np 
from bs4 import BeautifulSoup
from datetime import datetime
import requests
import sqlite3

url = 'https://data.fs.usda.gov/geodata/edw/datasets.php'
csv_path = './us_forest_service.csv'
db_name = 'Forest_Service.db'
table_name = 'Geometries'
table_attribs = ['Feature Class', 'Description','ESRI GDB', 'Shapefile']
log_file_path = './code_log.txt'



def log_progress(message):
    ''' This function logs the mentioned message of a given stage of the
    code execution to a log file. Function returns nothing'''
    timestamp_format = '%Y-%h-%d-%H-%M-%S'
    now = datetime.now()
    timestamp = now.strftime(timestamp_format)
    with open(log_file_path, "a") as f:
        f.write(timestamp + ' : ' + message + '\n')

def get_soup(url):
    html_page = requests.get(url).text
    html_soup = BeautifulSoup(html_page, 'html.parser')
    return html_soup

def make_clickable(val):
    # target _blank to open new window
    return '<a target="_blank" href="{}">{}</a>'.format(val, val)

def extract(url, table_attribs):
    ''' This function aims to extract the required
    information from the website and save it to a data frame. The
    function returns the data frame for further processing. '''

    soup = get_soup(url)
    df = pd.DataFrame(columns=table_attribs)

    table = soup.find('table', {'class':'fcTable'})
    trs = table.find_all('tr')
    trs = trs[1:]

    for tr in trs:

        tds = tr.find_all('td')
        description = tr.find('td',{'class':'abstractCopy'}).get_text(strip=True)
        links = tr.find_all('a', href=True)
        gdb_link = links[0]['href']
        shapefile_link = links[1]['href']

        "prepend https://data.fs.usda.gov/geodata/edw/"

        for td in tds:

            for p in td.find_all('p'):

                for strong in p.find_all('strong'):
                    feature_class = strong.get_text(strip=True)
                    data_dict = {
                                    table_attribs[0]:feature_class,
                                    table_attribs[1] : description,
                                    table_attribs[2] : gdb_link,
                                    table_attribs[3] : shapefile_link
                    }
                    df.loc[len(df)] = data_dict
    df['Description'] = df['Description'].str.split('.')\
                                        .str.get(0)\
                                        .str.replace("…[see more]", ' ', regex=False)\
                                        + '.'
    #df.style.format({'ESRI GDB': make_clickable})
    df['ESRI GDB'] = df['ESRI GDB'].apply(lambda x: '<a href="https://data.fs.usda.gov/geodata/edw/{}">ESRI Geodatabase</a>'.format(x))
    df['Shapefile'] = df['Shapefile'].apply(lambda x: '<a href="https://data.fs.usda.gov/geodata/edw/{}">Shapefile</a>'.format(x))

    return df



def transform(df, csv_path):
    ''' This function accesses the CSV file for exchange rate
    information, and adds three columns to the data frame, each
    containing the transformed version of Market Cap column to
    respective currencies'''

    ex_rates = pd.read_csv("./exchange_rate.csv")

    ex_rates_dict = ex_rates.set_index('Currency').to_dict()['Rate']

    for k, v in ex_rates_dict.items():
        df[str('MC_' + k + '_Billion')] = round(df['MC_USD_Billion'] * float(v), 2)

    return df

def load_to_csv(df, output_path):
    ''' This function saves the final data frame as a CSV file in
    the provided path. Function returns nothing.'''
    
    df.to_csv(output_path)



def load_to_db(df, sql_connection, table_name):
    ''' This function saves the final data frame to a database
    table with the provided name. Function returns nothing.'''

    df.to_sql(table_name, sql_connection, if_exists='replace', index=False)





def run_queries(query_statements, sql_connection):
    ''' This function runs the query on the database table and
    prints the output on the terminal. Function returns nothing. '''

    for query in query_statements:
        query_output = pd.read_sql(query, sql_connection)
        print(query)
        print(query_output)





#log_progress("Preliminaries complete. Initiating ETL process")

df = extract(url, table_attribs)

#load_to_csv(df, csv_path)
#log_progress("Data saved to CSV file")

conn = sqlite3.connect(db_name)
#log_progress("SQL Connection initiated")

#load_to_db(df, conn, table_name)
#log_progress("Data loaded to Database as a table, Executing queries")

query_statement = [f"SELECT * FROM Geometries LIMIT 5"]
#run_queries(query_statement, conn)
#log_progress("Process Complete")

'''print("Extracted DF: \n", banks_df)
log_progress("Data extraction complete. Initiating Transformation process")

banks_df = transform(banks_df, csv_path)
print("Transformed DF: \n", banks_df)
log_progress("Data transformation complete. Initiating Loading process")

load_to_csv(banks_df, csv_path)


conn = sqlite3.connect(db_name)
log_progress("SQL Connection initiated")

load_to_db(banks_df, conn, table_name)
log_progress("Data loaded to Database as a table, Executing queries")

query_statements = [f'SELECT * FROM Largest_banks',f'SELECT AVG(MC_GBP_Billion) FROM Largest_banks',f'SELECT Name from Largest_banks LIMIT 5']
run_queries(query_statements, conn)
log_progress("Process Complete")

conn.close()
log_progress("Server Connection closed")'''