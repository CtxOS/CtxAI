import os
import sys

import requests


def main():
    token = os.getenv("GITHUB_TOKEN")
    pr_number = os.getenv("PR_NUMBER")
    repo = os.getenv("REPOSITORY")

    if not all([token, pr_number, repo]):
        print("Missing required environment variables.")
        sys.exit(1)

    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/labels"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # We want to add the 'approved' label
    data = {"labels": ["approved"]}

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200 or response.status_code == 201:
        print(f"Successfully added 'approved' label to PR #{pr_number}")
    else:
        print(f"Failed to add label: {response.status_code}")
        print(response.text)
        sys.exit(1)


if __name__ == "__main__":
    main()
