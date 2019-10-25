from typing import Iterable, TypeVar, Callable, Dict
from .models import BaseGithubCommit
from .github_rate_limited_requester import GithubRateLimitedRequester
import logging

TCommit = TypeVar('TCommit', bound=BaseGithubCommit)


class GithubSearchClient(object):
    def __init__(self, api_tokens):
        self._requester = GithubRateLimitedRequester(api_tokens)

    def search_commits(self, query, parser: Callable[[Dict], TCommit]) -> Iterable[TCommit]:
        for item in self._query_commits(query):
            yield parser(item)

    def search_other_emails_and_names_by_login(self, login):
        emails, names, logins = self._search_for_other_emails_names_and_logins(login, "")
        return emails, names

    def search_other_emails_and_logins_by_name(self, name):
        # If the query returns more than 5000 results, assume that it's too generic and don't return anything.
        emails, names, logins = self._search_for_other_emails_names_and_logins(name, "-name", 5000)
        return emails, logins

    def search_other_names_and_logins_by_email(self, email):
        emails, names, logins = self._search_for_other_emails_names_and_logins(email, "-email")
        return names, logins

    def _search_for_other_emails_names_and_logins(self, value, query_suffix, max_results=-1):
        emails = {}
        names = {}
        logins = {}

        for query_type in ["author", "committer"]:
            query = "%s%s:\"%s\"" % (query_type, query_suffix, value)
            logging.info(query)
            for item in self._query_commits(query, max_results):
                infos = item["commit"][query_type]
                email = infos["email"].lower()
                if "@" in email and not email.endswith("@users.noreply.github.com") and not email.endswith("@github.com"):
                    self._update_counts(emails, email)

                name = infos["name"].lower()
                if name and name != "unknown":
                    self._update_counts(names, name)

                login_info = item[query_type]
                if login_info:
                    self._update_counts(logins, login_info["login"].lower())

        return emails, names, logins

    def _query_commits(self, query, max_results=-1):
        return self._requester.paginated_get("https://api.github.com/search/commits?sort=committer-date&order=desc&q=" + query.replace(" ", "+"), lambda x: x["items"], max_results)

    @staticmethod
    def _update_counts(counts_dict, key):
        if not key:
            return

        if key not in counts_dict:
            counts_dict[key] = 1
        else:
            counts_dict[key] += 1
