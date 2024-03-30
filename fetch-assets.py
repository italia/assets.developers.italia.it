#!/usr/bin/env python3
import hashlib
import os
import re
import sys
from urllib.parse import urlparse

import requests
import yaml

API_BASE_URL = "https://api.developers.italia.it/v1"


def absolute_url(url, repo):
    repo = re.sub('.git$', '', repo.lower())

    if not url or url.lower().startswith(("http://", "https://")):
        return url

    repo_url = urlparse(repo)
    hostname = repo_url.hostname.lower()

    if hostname == "github.com":
        return "https://raw.githubusercontent.com" + os.path.join(
            repo_url.path, "HEAD", url
        )
    elif hostname == "bitbucket.org":
        return "https://bitbucket.org" + os.path.join(repo_url.path, "raw/HEAD", url)
    else:
        # GitLab
        return f"{repo_url.scheme}://{repo_url.hostname}" + os.path.join(
            repo_url.path, "-/raw/HEAD", url
        )


def get_software():
    page = True
    page_after = ""

    while page:
        res = requests.get(f"{API_BASE_URL}/software?{page_after}")
        res.raise_for_status()

        body = res.json()

        page_after = body["links"]["next"]
        if page_after:
            # Remove the '?'
            page_after = page_after[1:]

        page = bool(page_after)

        for item in body.get("data", []):
            yield item

def download_file(url, filename):
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    try:
        with requests.get(url, stream=True) as response:
            response.raise_for_status()

            with open(filename, 'wb') as file:
                for chunk in response.iter_content(chunk_size=64*1024): 
                    if chunk:
                        file.write(chunk)

    except requests.RequestException as e:
        print(f"Error downloading {url}", e)

if __name__ == "__main__":
    for software in get_software():
        try:
            publiccode = yaml.safe_load(software["publiccodeYml"])
        except (yaml.YAMLError, ValueError) as e:
            print(f"Error parsing YAML ({API_BASE_URL}/software/{software["id"]}): {e}", file=sys.stderr)
            continue

        logo = publiccode.get("logo", None)
        if logo:
            logo = absolute_url(logo, publiccode["url"])

            hash = hashlib.sha1(logo.encode("utf-8")).hexdigest()
            _, ext = os.path.splitext(logo)

            download_file(logo, f"{hash[:2]}/{hash[2:]}{ext}")
