import os
import json
import subprocess
import dns.resolver
import pandas as pd
from datetime import datetime, timedelta
from functools import cache
from os.path import dirname, join, abspath
from urllib.parse import urlparse
from tld import get_fld

COUNTRIES = ['DE', 'FR', 'ES', 'IT', 'NL']
CONSENT_MODES = ['Accept', 'Reject']
MEASUREMENT_MODES = ['tracking', 'social']
NOTEBOOKS_DIR = dirname(abspath(__file__))

# precomputed parsed HAR URLs and metadatas
REQS_PICKLE = join(NOTEBOOKS_DIR, 'parsed_har_urls.pkl')

# precomputed domain categories from Tracker Radar data
# cloned on 20 October 2024. Commmit hash: e158d637d52
# last updated on Wed Sep 18 17:45:01 2024 +0200
# The file only contains the domains that are present in the study data
# if the data changes, this file should be recreated
TRACKER_RADAR_CATEGORIES_JSON = join(NOTEBOOKS_DIR, 'tracker-radar-categories.json')

CNAME_CACHE_JSON = join(NOTEBOOKS_DIR, 'cname_cache.json')

# Domain -> Entity mapping
# Downloaded on 13 October 2024
# from https://raw.githubusercontent.com/duckduckgo/tracker-radar/refs/heads/main/build-data/generated/domain_map.json
ENTITY_MAP_FILE = join(NOTEBOOKS_DIR, 'domain_map.json')

UBO_TEMP_REQS_JSON_FILE = join(NOTEBOOKS_DIR, 'ublock/requests_temp.json')
NODE_UBO_SCRIPT_PATH = join(NOTEBOOKS_DIR, "ublock/ublock.js")


def load_json_file(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)


def write_json_file(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)


def extract_urls(stack):
    urls = []
    if 'callFrames' in stack:
        for frame in stack['callFrames']:
            if 'url' in frame:
                urls.append(frame['url'])
    if 'parent' in stack:
        urls.extend(extract_urls(stack['parent']))
    return urls


def extract_initiator_domains(request):
    """Extract the initiator type and urls from a request."""
    if '_initiator' not in request or 'stack' not in request['_initiator']:
        return '', []
    initiator_type = request['_initiator']['type']
    # Extract distinct URLs from the callFrames
    urls = extract_urls(request['_initiator']['stack'])
    return initiator_type, list(set(urls))


def extract_param_names(request):
    """Extract parameter names from a request."""
    return [param['name'] for param in request.get('queryString', [])]


def extract_post_data(request):
    """Extract POST data from a request."""
    post_data = request.get('postData', {})
    mime_type = post_data.get('mimeType', '')
    text = post_data.get('text', '')
    return mime_type, text

def check_cookie_expiration(cookie):
    """Check if a cookie is expired or will expire in more than 2 months."""
    if 'expires' in cookie:
        expiration_date = datetime.strptime(cookie['expires'], "%Y-%m-%dT%H:%M:%S.%fZ")
        # TODO: use the data collection date instead of the current date
        two_months_later = datetime.now() + timedelta(days=60)
        return expiration_date > two_months_later
    return False


UBO_BATCH_SIZE = 20000

def run_ubo_core_script(json_reqs):
    """Run the uBO core Node script on a list of request dicts and return a boolean list."""
    with open(UBO_TEMP_REQS_JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(json_reqs, f, ensure_ascii=False)

    env = {**os.environ, 'NO_COLOR': '1', 'FORCE_COLOR': '0'}
    proc = subprocess.run(
        ['node', NODE_UBO_SCRIPT_PATH, UBO_TEMP_REQS_JSON_FILE],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env
    )
    if proc.returncode != 0:
        print(f"🚩 uBlock script exited with code {proc.returncode}: {proc.stderr.decode()[:500]}")
        return None

    # Each console.log produces one line: "0", "1", or "2"
    lines = [l.strip() for l in proc.stdout.decode("utf-8").splitlines() if l.strip()]
    results = []
    for line in lines:
        if line in ('0', '1', '2'):
            # 0: not blocked, 1: blocked, 2: unblocked (allowed to avoid breakage)
            results.append(line != '0')
        else:
            print(f"🚩 Unexpected uBlock output (first 200 chars): {line[:200]}")
            return None

    if len(results) != len(json_reqs):
        print(f"🚩 uBlock returned {len(results)} results for {len(json_reqs)} requests")
        return None
    return results


def assign_tracker_labels(df_reqs, in_column, out_column):
    """Label trackers using uBlock Origin's core (npm) script, processing in batches."""
    json_reqs = [
        {
            'url': row[in_column],
            'originURL': "https://" + row['site_hostname'],
            'type': row['resource_type'],
        }
        for row in df_reqs.to_dict('records')
    ]

    total = len(json_reqs)
    print(f"Running uBlock for {out_column}: {total} requests in batches of {UBO_BATCH_SIZE}")
    all_results = []
    for i in range(0, total, UBO_BATCH_SIZE):
        batch = json_reqs[i:i + UBO_BATCH_SIZE]
        batch_results = run_ubo_core_script(batch)
        if batch_results is None:
            df_reqs[out_column] = None
            return df_reqs
        all_results.extend(batch_results)
        print(f"  Batch {i // UBO_BATCH_SIZE + 1}: {len(batch)} requests → {sum(batch_results)} blocked")

    df_reqs[out_column] = all_results
    return df_reqs


def label_trackers(df_reqs):
    """Label trackers using uBlock Origin's core (npm) script."""
    return assign_tracker_labels(df_reqs, 'url', 'is_tracker')


def label_cname_trackers(df_reqs):
    """Label trackers using the cname_url column."""
    return assign_tracker_labels(df_reqs, 'cname_url', 'is_cname_tracker')



def is_tracking_cookie(request, site_hostname):
    """Check if a cookie is tracking."""
    cookies = request.get('cookies', [])
    if not cookies:
        return False
    site_domain = get_fld(site_hostname, fix_protocol=True, fail_silently=True)
    return any(
        get_fld(cookie.get('domain', ''), fix_protocol=True, fail_silently=True) != site_domain and
        cookie.get('sameSite', '').lower() == 'none' and
        cookie.get('partitionKey', '') == '' and
        check_cookie_expiration(cookie)
        for cookie in cookies
    )


IGNORED_HOSTNAMES = [
    'translate-pa.googleapis.com',
    'translate.googleapis.com'
]


IGNORED_URLS = [
    'https://fonts.gstatic.com/s/i/productlogos/translate/v14/24px.svg'
]


def is_bg_traffic(url):
    if (urlparse(url).hostname in IGNORED_HOSTNAMES) or (url in IGNORED_URLS):
        return True
    return False


GTM_JS_PRELUDE = "\n// Copyright 2012 Google Inc. All rights reserved.\n \n (function(w,g){w[g]=w[g]||{};\n w[g].e=function(s){return eval(s);};})(window,'google_tag_manager');"


def extract_req_details_from_har(har_file_path, site_hostname):
    """Extract request and response related details from a HAR file."""
    urls = []
    first_page_ref_seen = False

    with open(har_file_path, 'r', encoding='utf-8') as f:
        har_data = json.load(f)

    # Extract all URLs from the HAR file
    assert 'log' in har_data and 'entries' in har_data['log']
    for entry in har_data['log']['entries']:
        if not first_page_ref_seen and "pageref" not in entry:
            # print(entry['request'].get('url'))
            continue
        elif "pageref" in entry:
            first_page_ref_seen = True
        if 'request' in entry and 'url' in entry['request']:
            request = entry['request']
            request_url = request['url']
            resource_type = entry.get('_resourceType', '')
            if is_bg_traffic(request_url):
                continue
            initiator_type, initiator_urls = extract_initiator_domains(entry)
            param_names = extract_param_names(request)
            post_mime_type, post_data = extract_post_data(request)
            tracking_cookie_flag = is_tracking_cookie(request, site_hostname)

            if 'response' in entry:
                # server and via headers
                headers = {header['name'].lower(): header['value'] for header in entry['response'].get('headers', [])}
                server_header = headers.get('server', '')
                via_header = headers.get('via', '')
                content_size = entry['response'].get('content', {}).get('size', 0)
                content_mime_type = entry['response'].get('content', {}).get('mimeType', '')
                has_gtm_signature = GTM_JS_PRELUDE in entry['response'].get('content', {}).get('text', '')
                # content_first_1k = entry['response'].get('content', {}).get('text', '')[:1024]
                # check if the response content includes the lines:
            else:
                server_header = ''
                via_header = ''
                content_size = 0
                content_mime_type = ''

            urls.append(
                (request_url, initiator_type, initiator_urls,
                param_names, post_mime_type, post_data,
                tracking_cookie_flag, resource_type, server_header, via_header,
                content_size, content_mime_type, has_gtm_signature)
                )

    return urls


def parse_har_files_to_dataframe(base_dir, test=False, use_cache=False):
    """Parse HAR files in the given directory and return a DataFrame."""
    if use_cache and os.path.exists(REQS_PICKLE):
        return pd.read_pickle(REQS_PICKLE)

    data = []

    # Walk through the directory structure
    for root, __, file_names in os.walk(base_dir):
        # Check if the directory matches the expected pattern (e.g., Final_social_it_accept)
        folder_name = os.path.basename(root)
        # Parse the folder name to extract country, measurement mode, and consent mode
        try:
            _, exp_mode, country, consent_mode = folder_name.split('_')
            country = country.upper()
            # make the first letter of consent_mode uppercase
            consent_mode = consent_mode.capitalize()
        except ValueError:
            continue
        if country not in COUNTRIES or exp_mode not in MEASUREMENT_MODES or consent_mode not in CONSENT_MODES:
            continue

        # Process each HAR file in the folder
        for file_name in file_names:
            if not file_name.endswith('.har'):
                continue
            har_file_path = join(root, file_name)
            # print(f'Processing {har_file_path}')
            # Extract website domain from the HAR file name (before .har)
            site_hostname = file_name.replace('.har', '')
            try:
                reqs_details = extract_req_details_from_har(har_file_path, site_hostname)
            except Exception as e:
                print(f'🚩 Error processing HAR file {har_file_path}: {e}')
                # raise e
                continue

            # Add each URL along with metadata to the data list
            # for url, initiator_type, initiator_urls, param_names, post_mime_type, post_data in reqs_details:
            for req_details in reqs_details:
                data.append([site_hostname, exp_mode, country, consent_mode, *req_details])

            if test:
                break
    # Convert the collected data into a pandas DataFrame
    df = pd.DataFrame(data, columns=[
        'site_hostname',
        'exp_mode',
        'country',
        'consent_mode',
        'url', 'initiator_type', 'initiator_urls',
        'param_names', 'post_mime_type', 'post_data',
        'cookies', 'resource_type', 'server', 'via',
        'size', 'mime_type', 'has_gtm_signature']
    )
    df = add_analysis_columns(df)
    # pickle the df for future use
    df.to_pickle(REQS_PICKLE)
    return df


def extract_domain_categories_from_tracker_radar_data(tracker_radar_dir, domain_list=None):
    """Extract domain categories from the Tracker Radar data.

    We should clone the repo to the folder containing the study (pharmacy) repo
        `git clone git@github.com:duckduckgo/tracker-radar.git`

    """
    domain_categories = {}
    seen_domains = set()  # to avoid processing the same domain multiple times
    for subdir, _, files in os.walk(tracker_radar_dir):
        for file_name in files:
            if not file_name.endswith('.json'):
                continue
            file_path = join(subdir, file_name)
            domain_name = file_name.rsplit('.json', 1)[0]
            # Check if the domain (file name) is in the domain list if provided
            if domain_list and (domain_name not in domain_list):
                continue
            # Skip if the domain has already been processed
            if domain_name in seen_domains:
                continue
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "categories" in data:
                        domain_categories[domain_name] = data["categories"]
                        seen_domains.add(domain_name)
            except json.JSONDecodeError as jse:
                print(f"🚩 Error reading Tracker Radar JSON file: {file_path} - {jse}")
            except Exception as e:
                print(f"🚩 Unexpected error processing file {file_path}: {e}")
    return domain_categories


def add_domain_categories(df):
    if os.path.exists(TRACKER_RADAR_CATEGORIES_JSON):
        print("Loading domain categories from JSON file")
        domain_categories = load_json_file(TRACKER_RADAR_CATEGORIES_JSON)
    else:
        domain_list = df['req_domain'].unique().tolist()
        tracker_radar_dir = join(dirname(dirname(NOTEBOOKS_DIR)), 'tracker-radar', 'domains')
        if not os.path.exists(tracker_radar_dir):
            print("Tracker Radar directory not found. Skipping domain categorization.")
            df['categories'] = ''
            return df
        domain_categories = extract_domain_categories_from_tracker_radar_data(tracker_radar_dir, domain_list)
        write_json_file(TRACKER_RADAR_CATEGORIES_JSON, domain_categories)

    df['categories'] = df['req_domain'].apply(lambda x: domain_categories.get(x, []))
    return df


@cache  # Cache the results to avoid repeated DNS queries
def get_cname_dns(hostname):
    """Get the CNAME record for a hostname."""
    try:
        # Perform a DNS query for the CNAME record
        answers = dns.resolver.resolve(hostname, 'CNAME')
        # Extract and return the canonical name
        for rdata in answers:
            return str(rdata.target).rstrip('.')
    except Exception as e:
        # print(f"Error {e}: {hostname}")
        return ""


def get_cached_cname(cname_cache_file):
    if os.path.exists(cname_cache_file):
        with open(cname_cache_file, 'r') as f:
            return json.load(f)
    return {}


def get_cname(hostname, cname_cache):
    if hostname in cname_cache:
        # print(f"CNAME cache hit for {hostname}, {cname_cache[hostname]}")
        return cname_cache[hostname]
    cname = get_cname_dns(hostname)
    cname_cache[hostname] = cname
    return cname


def add_analysis_columns(df):
    """Add additional columns to the dataframe for analysis."""
    entity_map = load_entity_map()
    df['req_domain'] = df['url'].apply(lambda x: get_fld(x, fail_silently=True))
    # convert None to '' in req_domain. Only 4 localhost URLs have None as req_domain
    # this makes sorting possible
    df['req_domain'] = df['req_domain'].apply(lambda x: '' if x is None else x)
    df = add_domain_categories(df)
    df['req_hostname'] = df['url'].apply(lambda x: urlparse(x).hostname)
    # get the CNAME for the request hostname
    cname_cache = get_cached_cname(CNAME_CACHE_JSON)  # we cache the CNAME results to avoid repeated DNS queries
    print(f"Loaded CNAME cache with {len(cname_cache)} entries.")
    df['cname'] = df.req_hostname.map(lambda x: get_cname(x, cname_cache))
    write_json_file(CNAME_CACHE_JSON, cname_cache)
    df['cname_domain'] = df.cname.apply(lambda x: get_fld(x, fix_protocol=True) if x else '')
    df['cname_entity'] = df['cname_domain'].apply(lambda x: entity_map.get(x, {}).get('displayName', ''))
    # take the url, and replace the hostname with the cname (use list comp to avoid apply returning DataFrame in edge cases)
    def _cname_url_row(url, hostname, cname):
        if not cname or (isinstance(cname, float) and pd.isna(cname)):
            return ''
        return str(url).replace(str(hostname), str(cname))
    df['cname_url'] = [_cname_url_row(u, h, c) for u, h, c in zip(df['url'], df['req_hostname'], df['cname'])]
    # End of CNAME
    df['entity'] = df['req_domain'].apply(lambda x: entity_map.get(x, {}).get('displayName', ''))
    df['site_domain'] = df['site_hostname'].apply(lambda x: get_fld(x, fix_protocol=True))
    # TODO: Rename: third_party -> is_third_party
    df['third_party'] = df['req_domain'] != df['site_domain']
    # extract registrable domains from initiator URLs
    df['initiator_domains_str'] = df['initiator_urls'].apply(
        lambda x: ",".join(
            sorted(set(filter(None, [get_fld(i, fix_protocol=True, fail_silently=True) for i in x]))))
    )
    df = label_trackers(df)
    df = label_cname_trackers(df)
    return df


def load_entity_map(entity_map_file=ENTITY_MAP_FILE):
    """Load the entity map file into a dictionary."""
    with open(entity_map_file, 'r') as f:
        entity_map = json.load(f)
    return entity_map
