#!/usr/bin/env python3

import argparse
import os
from secret_finder import SecretFinder
from scheduling import QueryScheduler
import logging
from slack import SlackFindingSender
from contextlib import contextmanager
import shutil


def create_list_from_args(file_name, single_value = None):
    if single_value:
        return [single_value]

    if file_name:
        with open(file_name, "r") as f:
            return [l.strip() for l in f.readlines() if l and not l.isspace()]

    return []


def print_result(result):
    width = shutil.get_terminal_size((80, 20)).columns
    prefix = result.commit.html_url + " - "
    secret_width = width - len(prefix)
    if secret_width < 20:
        secret_width = 20
    print("%s%s" % (prefix, result.secret.to_terminal_string(secret_width)))


def create_slack_finding_sender(args, db_file):
    if not args.cache_only and args.slack_webhook:
        return SlackFindingSender(args.slack_webhook, db_file)
    else:
        return contextmanager(lambda: iter([None]))()


def main():
    directory = os.path.dirname(os.path.realpath(__file__))
    default_blacklist = os.path.join(directory, "default-blacklist.json")
    database_file_name = os.path.join(directory, "github-secret-finder.sqlite")

    parser = argparse.ArgumentParser(description='Github Secret Finder')
    parser.add_argument('--users', '-U', action='store', dest='users', help='File containing Github users to monitor.')
    parser.add_argument('--user', '-u', action="store", dest='user', help="Single Github user to monitor.")
    parser.add_argument('--emails', '-E', action='store', dest='emails', help='File containing email addresses to monitor.')
    parser.add_argument('--email', '-e', action="store", dest='email', help="Single email address to monitor.")
    parser.add_argument('--names', '-N', action='store', dest='names', help='File containing full names to monitor.')
    parser.add_argument('--name', '-n', action="store", dest='name', help="Single full name to monitor.")
    parser.add_argument('--organizations', '-O', action='store', dest='organizations', help='File containing organizations to monitor.')
    parser.add_argument('--organization', '-o', action="store", dest='organization', help="Single organization to monitor.")
    parser.add_argument('--ignore-forks', action="store_true", dest='ignore_forks', default=False, help="Ignores the forked repositories when monitoring an organization.")
    parser.add_argument('--tokens', '-t', action="store", dest='tokens', help="Github tokens separated by a comma (,)", required=True)
    parser.add_argument('--blacklist', '-B', action='store', dest='blacklist_file', default=default_blacklist, help='File containing regexes to blacklist file names. Defaults to default-blacklist.json')
    parser.add_argument('--slack-webhook', '-w', action="store", dest='slack_webhook', default=None, help="Slack webhook to send messages when secrets are found.")
    parser.add_argument('--results', '-r', action="store_true", dest='cache_only', default=False, help="Shows the previously found results.")
    parser.add_argument('--verbose', '-v', action="store_true", dest='verbose', default=False, help="Increases output verbosity.")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger("sqlitedict").setLevel(logging.ERROR)
        logging.getLogger().setLevel(logging.INFO)

    emails = create_list_from_args(args.emails, args.email)
    names = create_list_from_args(args.names, args.name)
    users = create_list_from_args(args.users, args.user)
    organizations = create_list_from_args(args.organizations, args.organization)

    tokens = [t.strip() for t in args.tokens.split(",")]

    with create_slack_finding_sender(args, database_file_name):
        with SecretFinder(tokens, database_file_name, args.blacklist_file, args.cache_only, args.ignore_forks) as finder:
            scheduler = QueryScheduler(finder.find_by_username, finder.find_by_email, finder.find_by_name, finder.find_by_organization, print_result, database_file_name, args.cache_only)
            scheduler.execute(users, emails, names, organizations)


if __name__ == "__main__":
    main()

