from sqlitedict import SqliteDict
from .github_search_client import GithubSearchClient
import hashlib


class CachedGithubSearchClient(object):
    def __init__(self, client: GithubSearchClient, db_file: str, db_table_prefix: str):
        self._db_table_prefix = db_table_prefix
        self._db_file = db_file
        self._client = client

    def search_commits(self, query):
        existing_commits = {}

        h = hashlib.sha1()
        h.update(query.encode("utf-8"))
        table_name = "%s_%s" % (self._db_table_prefix, h.hexdigest())

        with SqliteDict(self._db_file, tablename=table_name) as db:
            for commit, x in db.iteritems():
                existing_commits[commit] = x

            for commit, url, html_url in self._client.search_commits(query):
                if commit in existing_commits:
                    break

                existing_commits[commit] = (url, html_url)
                db[commit] = (url, html_url)

            db.commit()

            for commit, x in existing_commits.items():
                url, html_url = x
                yield commit, url, html_url


