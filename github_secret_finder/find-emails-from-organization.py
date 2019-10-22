import argparse
import logging
import operator

from github import GithubApiClient, GithubSearchClient


def get_organization_contributors(api, orgs):
    contributors = {}
    counts = {}

    for org in orgs:
        for repo in api.get_organization_repositories(org):
            for contributor, contribution_count in api.get_repository_contributors(repo.contributors_url):
                if contributor.login not in contributors:
                    contributors[contributor.login] = contributor
                    counts[contributor.login] = 1
                else:
                    counts[contributor.login] += 1

    for contributor_login, count in sorted(counts.items(), key=operator.itemgetter(1), reverse=True):
        yield contributors[contributor_login]


def get_user_emails(search, user):
    emails = {}

    for f, value in [(search.search_commit_emails_by_username, user.login), (search.search_commit_emails_by_full_name, user.name)]:
        if not value:
            continue
        for email, count in f(value).items():
            if email not in emails:
                emails[email] = count
            else:
                emails[email] += count

    return emails


def main():
    parser = argparse.ArgumentParser(description='Github Secret Finder')
    parser.add_argument('--organization', '-o', action="store", dest='organization', help="Single organization to monitor.")
    parser.add_argument('--organizations', '-O', action='store', dest='organizations', help='File containing organizations to monitor.')
    parser.add_argument('--tokens', '-t', action="store", dest='tokens', help="Github tokens separated by a comma (,)", required=True)
    parser.add_argument('--verbose', '-V', action="store_true", dest='verbose', default=False, help="Increases output verbosity.")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger("sqlitedict").setLevel(logging.ERROR)
        logging.getLogger().setLevel(logging.INFO)

    tokens = [t.strip() for t in args.tokens.split(",")]
    api = GithubApiClient(tokens)
    search = GithubSearchClient(tokens)

    if args.organizations:
        with open(args.organizations) as f:
            organizations = [l for l in [l.strip() for l in f.readlines()] if l]
    else:
        organizations = [args.organization]

    for contributor in get_organization_contributors(api, organizations):
        print("===================")
        print(contributor.name)
        for email, count in sorted(get_user_emails(search, contributor).items(), key=operator.itemgetter(1), reverse=True):
            print("%s (%d)" % (email, count))


if __name__ == "__main__":
    main()

