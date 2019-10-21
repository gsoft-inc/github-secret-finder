#!/usr/bin/env python3

import argparse
import os
from secret_finder import SecretFinder
from scheduling import QueryScheduler
import logging


def create_list_from_args(file_name, single_value = None):
    if single_value:
        return [single_value]

    if file_name:
        with open(file_name, "r") as f:
            return [l.strip() for l in f.readlines() if l and not l.isspace()]

    return []


def print_result(result):
    url = result["html_url"]
    secret = result["secret"]

    s = ""
    if secret.verified:
        s += "[VERIFIED] "
    s += "%s - %s" % (url, str(secret))
    print(s)


def main():
    directory = os.path.dirname(os.path.realpath(__file__))
    default_blacklist = os.path.join(directory, "default-blacklist.json")

    parser = argparse.ArgumentParser(description='Github Secret Finder')
    parser.add_argument('--users', '-U', action='store', dest='users', help='File containing Github users to monitor.')
    parser.add_argument('--user', '-u', action="store", dest='user', help="Single Github user to monitor.")
    parser.add_argument('--emails', '-E', action='store', dest='emails', help='File containing email addresses to monitor.')
    parser.add_argument('--email', '-e', action="store", dest='email', help="Single email address to monitor.")
    parser.add_argument('--names', '-N', action='store', dest='names', help='File containing full names to monitor.')
    parser.add_argument('--name', '-n', action="store", dest='name', help="Single full name to monitor.")
    parser.add_argument('--tokens', '-t', action="store", dest='tokens', help="Github tokens separated by a comma (,)", required=True)
    parser.add_argument('--blacklist', '-B', action='store', dest='blacklist_file', default=default_blacklist, help='File containing regexes to blacklist file names. Defaults to default-blacklist.json')
    parser.add_argument('--verbose', '-V', action="store_true", dest='verbose', default=False, help="Increases output verbosity.")
    parser.add_argument('--results', '-r', action="store_true", dest='cache_only', default=False, help="Shows the previously found results.")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger("sqlitedict").setLevel(logging.ERROR)
        logging.getLogger().setLevel(logging.INFO)

    emails = create_list_from_args(args.emails, args.email)
    names = create_list_from_args(args.names, args.name)
    users = create_list_from_args(args.users, args.user)

    tokens = [t.strip() for t in args.tokens.split(",")]

    database_file_name = "./github-secret-finder.sqlite"
    with SecretFinder(tokens, database_file_name, args.blacklist_file, args.cache_only) as finder:
        scheduler = QueryScheduler(finder.find_by_username, finder.find_by_email, finder.find_by_name, print_result, database_file_name, args.cache_only)
        scheduler.execute(users, emails, names)


if __name__ == "__main__":
    main()

