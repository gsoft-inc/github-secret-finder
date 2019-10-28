import argparse
import logging
import operator

from github import GithubApiClient, GithubSearchClient, GithubApi


def get_users_from_contributors(api: GithubApi, repo):
    if not repo.is_fork:
        for contributor, contribution_count in api.get_repository_contributors(repo.get_contributors_url()):
            yield contributor, contribution_count


def get_users_from_commits(api: GithubApi, repo):
    for commit_with_user in api.get_repository_commit_users(repo):
        for user in [commit_with_user.committer, commit_with_user.author]:
            yield user, 1


def get_sorted_user_informations(api: GithubApi, orgs):
    emails = {}
    names = {}
    logins = {}

    for org in orgs:
        for repo in api.get_organization_repositories(org):
            for source in [get_users_from_contributors, get_users_from_commits]:
                for user, count in source(api, repo):
                    update_counts(emails, user.email, count, is_email_blacklisted)
                    update_counts(names, user.name, count, is_name_blacklisted)
                    update_counts(logins, user.login, count, is_login_blacklisted)

    sorted_emails = list(x[0] for x in sorted(emails.items(), key=operator.itemgetter(1), reverse=True))
    sorted_names = list(x[0] for x in sorted(names.items(), key=operator.itemgetter(1), reverse=True))
    sorted_logins = list(x[0] for x in sorted(logins.items(), key=operator.itemgetter(1), reverse=True))
    return sorted_emails, sorted_names, sorted_logins


def is_email_blacklisted(email):
    return "@" not in email or email.endswith("@users.noreply.github.com") or email.endswith("@github.com")


def is_login_blacklisted(login):
    return not login or login in ["unknown", "web-flow"]


def is_name_blacklisted(name):
    return not name or name in ["web-flow"]


def update_counts(counts, value, count=1, is_blacklisted=None):
    if not value or (is_blacklisted and is_blacklisted(value)):
        return

    value = value.lower()
    if value not in counts:
        counts[value] = 0
    counts[value] += count


def search_additionnal_user_informations(api, logins, emails, names, on_new_login, on_new_email, on_new_name):
    emails_operation = "emails"
    logins_operation = "logins"
    names_operation = "names"

    for x in emails:
        on_new_email(x, "")
    for x in logins:
        on_new_login(x, "")
    for x in names:
        on_new_name(x, "")

    operations = [logins_operation, emails_operation, names_operation]
    inputs = {emails_operation: emails, logins_operation: logins, names_operation: names}
    results = {emails_operation: set(), logins_operation: set(), names_operation: set()}
    query_suffixes = {emails_operation: "-email", logins_operation: "", names_operation: "-name"}

    while True:
        operation = next((o for o in operations if len(inputs[o]) > 0), None)
        if operation is None:
            break

        value = inputs[operation].pop(0)
        results[operation].add(value)

        user_type_selector = {"author": lambda x: x.author, "committer": lambda x: x.committer}

        for prefix, selector in user_type_selector.items():
            query = "%s%s:\"%s\"" % (prefix, query_suffixes[operation], value)
            for commit_with_user in api.search_users_from_commits(query):
                user = selector(commit_with_user)
                login = user.login.lower() if user.login else None
                email = user.email.lower() if user.email else None
                name = user.name.lower() if user.name else None

                if not is_login_blacklisted(login) and login not in results[logins_operation] and login not in inputs[logins_operation]:
                    inputs[logins_operation].append(login)
                    on_new_login(login, query)

                if not is_name_blacklisted(name) and name not in results[names_operation] and name not in inputs[names_operation]:
                    inputs[names_operation].append(name)
                    on_new_name(name, query)

                if not is_email_blacklisted(email) and email not in results[emails_operation] and email not in inputs[emails_operation]:
                    inputs[emails_operation].append(email)
                    on_new_email(email, query)


def main():
    parser = argparse.ArgumentParser(description='Github User OSINT Tool')
    parser.add_argument('--organization', '-o', action="store", dest='organization', help="Single organization to monitor.")
    parser.add_argument('--organizations', '-O', action='store', dest='organizations', help='File containing organizations to monitor.')
    parser.add_argument('--tokens', '-t', action="store", dest='tokens', help="Github tokens separated by a comma (,)", required=True)
    parser.add_argument('--cached', '-c', action="store_true", dest='cached', default=False, help="Only use cached values.")
    parser.add_argument('--verbose', '-V', action="store_true", dest='verbose', default=False, help="Increases output verbosity.")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger("sqlitedict").setLevel(logging.ERROR)
        logging.getLogger().setLevel(logging.INFO)

    tokens = [t.strip() for t in args.tokens.split(",")]
    api = GithubApi(GithubApiClient(tokens), GithubSearchClient(tokens), "github-secret-finder.sqlite", True)

    if args.organizations:
        with open(args.organizations) as f:
            organizations = [l for l in [l.strip() for l in f.readlines()] if l]
    else:
        organizations = [args.organization]

    emails, names, logins = get_sorted_user_informations(api, organizations)

    api = GithubApi(GithubApiClient(tokens), GithubSearchClient(tokens), "github-secret-finder.sqlite", False)
    search_additionnal_user_informations(api,
                                         logins,
                                         emails,
                                         names,
                                         lambda x, q: print("New login: %s (%s)" % (x, q)),
                                         lambda x, q: print("New email: %s (%s)" % (x, q)),
                                         lambda x, q: print("New name: %s (%s)" % (x, q)))


if __name__ == "__main__":
    main()

