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


def get_user_informations(search, user):
    email_counts = {}
    login_counts = {}
    name_counts = {}

    searched_logins = set()
    searched_emails = set()
    searched_names = set()
    emails_to_search = set()
    logins_to_search = set()
    names_to_search = set()

    if user.login:
        logins_to_search.add(user.login.lower())
    if user.name:
        names_to_search.add(user.name.lower())

    operations = [
        (search.search_other_emails_and_names_by_login, lambda x: (x[0], x[1], None), logins_to_search, searched_logins),
        (search.search_other_emails_and_logins_by_name, lambda x: (x[0], None, x[1]), names_to_search, searched_names),
        (search.search_other_names_and_logins_by_email, lambda x: (None, x[0], x[1]), emails_to_search, searched_emails)
    ]

    while any(len(x[2]) != 0 for x in operations):
        for f, x, to_search, searched in operations:
            if len(to_search) == 0:
                continue

            value = to_search.pop()
            if not value:
                continue
            searched.add(value)

            emails, names, logins = x(f(value))
            for source, counts, s, ts in [
                (emails, email_counts, searched_emails, emails_to_search),
                (names, name_counts, searched_names, names_to_search),
                (logins, login_counts, searched_logins, logins_to_search)]:
                if not source:
                    continue
                for item, count in source.items():
                    increment_counts(counts, item, count)
                    if item not in s:
                        ts.add(item)

    return email_counts, name_counts, login_counts


def increment_counts(counts_dict, key, count):
    if not key:
        return

    if key not in counts_dict:
        counts_dict[key] = count
    else:
        counts_dict[key] += count


def main():
    parser = argparse.ArgumentParser(description='Github User OSINT Tool')
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
        emails, names, logins = get_user_informations(search, contributor)

        print("Possible emails: " + ", ".join("%s (%d)" % (x, count) for x, count in sorted(emails.items(), key=operator.itemgetter(1), reverse=True)))
        print("Possible names: " + ", ".join("%s (%d)" % (x, count) for x, count in sorted(names.items(), key=operator.itemgetter(1), reverse=True)))
        print("Possible logins: " + ", ".join("%s (%d)" % (x, count) for x, count in sorted(logins.items(), key=operator.itemgetter(1), reverse=True)))


if __name__ == "__main__":
    main()

