import argparse
import logging
from enum import Enum
from github import GithubApiClient, GithubSearchClient, GithubApi
from github.models import GithubUser


class UserSourceType(Enum):
    Organization = 1,
    Search = 2


class UserRelation(object):
    def __init__(self, user: GithubUser, user_source: UserSourceType):
        self.user = user
        self.relations = set()
        self.parents = set()
        self.user_source = user_source

    def add_relation(self, relation):
        if not any(r.user == relation.user for r in self.relations):
            self.relations.add(relation)

        if not any(p.user == relation.user for p in relation.parents):
            relation.parents.add(self)


def get_users_from_contributors(api: GithubApi, repo):
    if not repo.is_fork:
        for contributor, contribution_count in api.get_repository_contributors(repo.get_contributors_url()):
            yield contributor, contribution_count


def get_users_from_commits(api: GithubApi, repo):
    for commit_with_user in api.get_repository_commit_users(repo):
        for user in [commit_with_user.committer, commit_with_user.author]:
            yield user, 1


def is_email_blacklisted(email):
    return not email or email == "noreply@github.com" or "@" not in email


def is_login_blacklisted(login):
    return not login or login in ["unknown", "web-flow"]


def is_name_blacklisted(name):
    return not name or name in ["web-flow", "github", "unknown", "first last"] or not " " in name  # The name probably won't be generic enough if there is no space in it.


def get_users_from_organizations(api: GithubApi, organizations):
    user_relations = {}
    for org in organizations:
        logging.info("Fetching repositories from %s" % org)
        for repo in api.get_organization_repositories(org):
            for source, log_string in [(get_users_from_contributors, "Fetching contributors"), (get_users_from_commits, "Fetching commit users")]:
                logging.info("%s from %s" % (log_string, repo.name))
                for user, count in source(api, repo):
                    new_relation = UserRelation(user, UserSourceType.Organization)
                    for value, is_blacklisted in [(user.login, is_login_blacklisted),
                                                  (user.email, is_email_blacklisted),
                                                  (user.name, is_name_blacklisted)]:
                        if not value or (is_blacklisted and is_blacklisted(value)):
                            continue
                        if value in user_relations:
                            user_relations[value].add_relation(new_relation)
                        else:
                            user_relations[value] = new_relation
    return user_relations


def get_user_informations_hierarchy(api, organizations):
    emails_operation = "emails"
    logins_operation = "logins"
    names_operation = "names"

    user_relations = get_users_from_organizations(api, organizations)

    emails = list(set(r.user.email for r in user_relations.values() if r.user.email))
    logins = list(set(r.user.login for r in user_relations.values() if r.user.login))
    names = list(set(r.user.name for r in user_relations.values() if r.user.name))

    operations = [logins_operation, emails_operation, names_operation]
    inputs = {emails_operation: emails, logins_operation: logins, names_operation: names}
    results = {emails_operation: set(), logins_operation: set(), names_operation: set()}
    query_suffixes = {emails_operation: "-email", logins_operation: "", names_operation: "-name"}

    while True:
        operation = next((o for o in operations if len(inputs[o]) > 0), None)
        if operation is None:
            break

        # Start with the most specific queries.
        value = max(inputs[operation], key=len)
        inputs[operation].remove(value)

        if value not in user_relations:
            continue
        results[operation].add(value)

        user_type_selector = {"author": lambda x: x.author, "committer": lambda x: x.committer}

        for prefix, selector in user_type_selector.items():
            query = "%s%s:\"%s\"" % (prefix, query_suffixes[operation], value)
            logging.info(query)
            for commit_with_user in api.search_users_from_commits(query):
                user = selector(commit_with_user)
                login = user.login.lower() if user.login else None
                email = user.email.lower() if user.email else None
                name = user.name.lower() if user.name else None

                new_relation = UserRelation(user, UserSourceType.Search)
                user_relations[value].add_relation(new_relation)

                if not is_login_blacklisted(login) and login not in results[logins_operation] and login not in inputs[logins_operation]:
                    inputs[logins_operation].append(login)
                    user_relations[login] = new_relation

                if not is_name_blacklisted(name) and name not in results[names_operation] and name not in inputs[names_operation]:
                    inputs[names_operation].append(name)
                    user_relations[name] = new_relation

                if not is_email_blacklisted(email) and email not in results[emails_operation] and email not in inputs[emails_operation]:
                    inputs[emails_operation].append(email)
                    user_relations[email] = new_relation

    returned_relations = set()
    for r in user_relations.values():
        if len(r.parents) > 0 or r in returned_relations:
            continue
        returned_relations.add(r)
        yield r


def flatten_relations(relation: UserRelation):
    names = set()
    logins = set()
    emails = set()

    user = relation.user
    for value, col, is_blacklisted in [(user.name, names, is_name_blacklisted),
                                       (user.login, logins, is_login_blacklisted),
                                       (user.email, emails, is_email_blacklisted)]:
        if value and not is_blacklisted(value):
            col.add((relation.user_source, value))

    for r in relation.relations:
        relation_logins, relation_emails, relation_names = flatten_relations(r)
        logins.update(relation_logins)
        emails.update(relation_emails)
        names.update(relation_names)

    return logins, emails, names


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
    api = GithubApi(GithubApiClient(tokens), GithubSearchClient(tokens), "github-secret-finder.sqlite", args.cached)

    if args.organizations:
        with open(args.organizations) as f:
            organizations = [l for l in [l.strip() for l in f.readlines()] if l]
    else:
        organizations = [args.organization]

    for relation in get_user_informations_hierarchy(api, organizations):
        print("============================")
        logins, emails, names = flatten_relations(relation)
        displayed_logins = set()
        displayed_names = set()
        displayed_emails = set()

        for source_type in [UserSourceType.Organization, UserSourceType.Search]:
            for values, description, displayed in [(logins, "Logins", displayed_logins),
                                                   (names, "Names", displayed_names),
                                                   (emails, "Emails", displayed_emails)]:
                values = [x[1] for x in values if x[0] == source_type and x[1] not in displayed]
                displayed.update(values)
                if len(values) > 0:
                    print("%s (%s): %s" % (description, source_type.name, ", ".join(values)))


if __name__ == "__main__":
    main()
