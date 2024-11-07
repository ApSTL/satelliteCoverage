import requests
import pandas as pd
from bs4 import BeautifulSoup

# Define the URL
url = "https://celestrak.org/NORAD/elements/table.php?GROUP=iridium&FORMAT=tle&SHOW-OPS"

# Send a request to the URL
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

# Find all tables on the page
tables = pd.read_html(str(soup))

# Select the second table (index 1) and store it in a DataFrame
if len(tables) > 1:  # Check if there is more than one table
    df = tables[1]
else:
     print("Only one table found on the page.")
     
# Save to CSV or other format
df.to_csv("Celestrak Constellation Details/CelesTrak_Iridium.csv", index=False)
