# Code for ETL operations on Country-GDP data

# Importing the required libraries

import pandas as pd 
import numpy as np 
from bs4 import BeautifulSoup
from datetime import datetime
import requests
import sqlite3





def log_progress(message):
    ''' This function logs the mentioned message of a given stage of the
    code execution to a log file. Function returns nothing'''
    timestamp_format = '%Y-%h-%d-%H-%M-%S'
    now = datetime.now()
    timestamp = now.strftime(timestamp_format)
    with open(log_file_path, "a") as f:
        f.write(timestamp + ' : ' + message + '\n')

def extract(url, table_attribs):
    ''' This function aims to extract the required
    information from the website and save it to a data frame. The
    function returns the data frame for further processing. '''

    html_page = requests.get(url).text
    data = BeautifulSoup(html_page, 'html.parser')
    df = pd.DataFrame(columns=table_attribs)

    tables = data.find_all('tbody')
    rows = tables[0].find_all('tr')

    for row in rows:

        col = row.find_all('td')
        
        if len(col) != 0:

            data_dict = {
                
                "Name": col[1].text[:-1],
                "MC_USD_Billion": float(col[2].contents[0][:-1])

            }

            df.loc[len(df)] = data_dict

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
    
    df.to_csv(csv_path)



def load_to_db(df, sql_connection, table_name):
    ''' This function saves the final data frame to a database
    table with the provided name. Function returns nothing.'''

    df.to_sql(table_name, conn, if_exists='replace', index=False)





def run_queries(query_statements, sql_connection):
    ''' This function runs the query on the database table and
    prints the output on the terminal. Function returns nothing. '''

    for query in query_statements:
        query_output = pd.read_sql(query, sql_connection)
        print(query)
        print(query_output)



''' Here, you define the required entities and call the relevant
functions in the correct order to complete the project. Note that this
portion is not inside any function.'''

url = 'https://web.archive.org/web/20230908091635/https://en.wikipedia.org/wiki/List_of_largest_banks'
csv_path = './Largest_banks_data.csv'
db_name = 'Banks.db'
table_name = 'Largest_banks'
table_attribs = ['Name','MC_USD_Billion']
log_file_path = './code_log.txt'

log_progress("Preliminaries complete. Initiating ETL process")

banks_df = extract(url, table_attribs)
print("Extracted DF: \n", banks_df)
log_progress("Data extraction complete. Initiating Transformation process")

banks_df = transform(banks_df, csv_path)
print("Transformed DF: \n", banks_df)
log_progress("Data transformation complete. Initiating Loading process")

load_to_csv(banks_df, csv_path)
log_progress("Data saved to CSV file")

conn = sqlite3.connect(db_name)
log_progress("SQL Connection initiated")

load_to_db(banks_df, conn, table_name)
log_progress("Data loaded to Database as a table, Executing queries")

query_statements = [f'SELECT * FROM Largest_banks',f'SELECT AVG(MC_GBP_Billion) FROM Largest_banks',f'SELECT Name from Largest_banks LIMIT 5']
run_queries(query_statements, conn)
log_progress("Process Complete")

conn.close()
log_progress("Server Connection closed")