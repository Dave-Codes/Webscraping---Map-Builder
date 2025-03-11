import os
import requests
import zipfile
import io
import pandas as pd
from bs4 import BeautifulSoup
from urllib.request import urlopen
from webscrape import extract, get_soup

url = 'https://data.fs.usda.gov/geodata/edw/datasets.php'

gdb_directory_path = 'gdb_directory'
if not os.path.exists(gdb_directory_path):
    os.makedirs(gdb_directory_path)


def extract_links(url):
    ''' This function aims to extract the required
    information from the website and save it to a data frame. The
    function returns the data frame for further processing. '''

    soup = get_soup(url)
    
    url_prefix = "https://data.fs.usda.gov/geodata/edw/"

    table = soup.find('table', {'class':'fcTable'})
    trs = table.find_all('tr')
    trs = trs[1:]
    gdb_links = []
    shapefile_links = []

    for tr in trs:
        links = tr.find_all('a', href=True)
        gdb_links.append(url_prefix + links[0]['href'])
        shapefile_links.append(url_prefix + links[1]['href'])

    return gdb_links, shapefile_links



def download_and_extract_zip(url, extract_to=gdb_directory_path):
    """Downloads a zip file from a URL and extracts it to a specified directory.

    Args:
        url: The URL of the zip file.
        extract_to: The directory to extract the contents to (default is current directory).
    """
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
            zip_file.extractall(extract_to)
        print(f"Successfully extracted to {extract_to}")
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
    except zipfile.BadZipFile as e:
         print(f"Zip file error: {e}. The URL might not point to a valid zip file.")
    except Exception as e:
        print(f"An error occurred: {e}")

extract_links(url)
gdb_links, shapefile_links = extract_links(url)

for link in gdb_links:
    download_and_extract_zip(link)

for link in shapefile_links:
    download_and_extract_zip(link)