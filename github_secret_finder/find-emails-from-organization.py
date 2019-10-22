import argparse
import logging
from github import GithubApiClient, GithubSearchClient


def get_organization_contributors(api, org):
    contributors = {}
    for repo in api.get_organization_repositories(org):
        for contributor in api.get_repository_contributors(repo.contributors_url):
            if contributor.login not in contributors:
                contributors[contributor.login] = contributor
                yield contributor


def get_user_emails(search, user):
    emails = set()
    for email in search.search_commit_emails(user):
        if email not in emails:
            emails.add(email)
            yield email


def main():
    parser = argparse.ArgumentParser(description='Github Secret Finder')
    parser.add_argument('--organization', '-o', action="store", dest='organization', help="Single organization to monitor.")
    parser.add_argument('--tokens', '-t', action="store", dest='tokens', help="Github tokens separated by a comma (,)", required=True)
    parser.add_argument('--verbose', '-V', action="store_true", dest='verbose', default=False, help="Increases output verbosity.")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger("sqlitedict").setLevel(logging.ERROR)
        logging.getLogger().setLevel(logging.INFO)

    tokens = [t.strip() for t in args.tokens.split(",")]
    api = GithubApiClient(tokens)
    search = GithubSearchClient(tokens)

    for contributor in get_organization_contributors(api, "gsoft-inc"):
        print("===================")
        print(contributor.name)
        for email in get_user_emails(search, contributor.login):
            print(email)


if __name__ == "__main__":
    main()

