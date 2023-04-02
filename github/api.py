# GitHub/api.py

import asyncio
import aiohttp
import json
import os
from base64 import b64decode


class GitHubAPI:
    def __init__(self, token):
        self.token = token
        self.headers = {'Authorization': f'token {self.token}'}


    async def fetch(self, url):
        print(url)
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"Error: {response.status}")
                    return None

    async def fetch_file_content(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    print(f"Error: {response.status}")
                    return None

    async def fetch_repository_files(self, repo_url):
        # Fetch the default branch for the repository
        default_branch = await self.fetch_default_branch(repo_url)

        # Replace the base URL to use the GitHub API
        api_url = repo_url.replace("https://github.com", f"https://api.github.com/repos")

        # Append the contents and branch endpoint to the URL
        contents_url = f"{api_url}/contents?ref={default_branch}"

        contents = await self.fetch(contents_url)
        if contents:
            files = []
            for item in contents:
                if item['type'] == 'file':
                    files.append({
                        'name': item['name'],
                        'path': item['path'],
                        'url': item['html_url'],
                        'last_updated': item['git_url']  # This contains the last updated information
                    })
            return files
        else:
            print(f"Error fetching contents for {repo_url}")
            return None

    async def search_github_repositories(self, query, sort='updated', order='asc', per_page=10, num_pages=1):

        base_url = 'https://api.github.com/search/repositories'
        all_repos = []

        for page in range(1, num_pages + 1):
            params = {
                'q': query,
                'sort': sort,
                'order': order,
                'per_page': per_page,
                'page': page
            }
            url = f"{base_url}?q={params['q']}&sort={params['sort']}&order={params['order']}&per_page={params['per_page']}&page={params['page']}"
            data = await self.fetch(url)
            if data:
                all_repos.extend([filter_repo_data(repo) for repo in data['items']])
            else:
                break

        return all_repos

    async def fetch_default_branch(self, repo_url):
        api_url = repo_url.replace("https://github.com", "https://api.github.com/repos")
        repo_data = await self.fetch(api_url)
        if repo_data:
            return repo_data.get("default_branch", "master")
        return "master"

    async def fetch_readme(self, repo_url):
        readme_filenames = ['readme', 'README', 'Readme']

        # Extract the repo owner and name from the repo_url
        repo_parts = repo_url.split('/')
        repo_owner = repo_parts[-2]
        repo_name = repo_parts[-1]

        # Fetch the default branch for the repository
        default_branch = await self.fetch_default_branch(repo_url)

        for readme_filename in readme_filenames:
            # Use the raw.githubusercontent.com URL format for fetching raw files
            readme_url = f"https://raw.githubusercontent.com/{repo_owner}/{repo_name}/{default_branch}/{readme_filename}.md"
            async with aiohttp.ClientSession() as session:
                async with session.get(readme_url, headers=self.headers) as response:
                    if response.status == 200:
                        return await response.text()
                    elif response.status == 404:
                        continue
                    else:
                        print(f"Error fetching readme for {repo_url}: {response.status}")
                        return None

        print(f"Readme not found for {repo_url}")
        return None


def filter_repo_data(repo):
    return {
        'id': repo['id'],
        'name': repo['name'],
        'full_name': repo['full_name'],
        'html_url': repo['html_url'],
        'description': repo['description'],
        'updated_at': repo['updated_at'],
        'language': repo['language'],
    }


async def fetch_crypto_repositories():
    with open(os.path.join(os.path.dirname(__file__), '..', 'tokens.json')) as f:
        tokens_data = json.load(f)

    GITHUB_TOKEN = tokens_data['tokens'][0]

    queries = [
        "cryptocurrency",
        "smart contract",
        "proof-of-work",
        "full node",
        "full-node",
        "smart-contract"
    ]

    api = GitHubAPI(GITHUB_TOKEN)
    repositories = []
    for query in queries:
        search_task = api.search_github_repositories(query)
        repos = await search_task
        repositories.extend(repos)

    # Remove duplicates by checking the 'id' field of the repositories
    unique_repos = {repo['id']: repo for repo in repositories}.values()
    print(len(unique_repos))

    # Fetch repository files and readme, and save them in the JSON file
    repo_data = []
    for repo in unique_repos:
        repo_files_task = api.fetch_repository_files(repo['html_url'])
        repo_readme_task = api.fetch_readme(repo['html_url'])

        repo_files = await repo_files_task
        repo_readme = await repo_readme_task

        repo['files'] = repo_files
        repo['readme'] = repo_readme
        repo_data.append(repo)

    with open('data/crypto_repos.json', 'w') as f:
        json.dump(repo_data, f, indent=4)


def main():
    os.makedirs("data", exist_ok=True)  # This line creates the 'data' directory if it doesn't exist
    asyncio.run(fetch_crypto_repositories())


if __name__ == "__main__":
    main()
