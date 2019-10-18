from .github_rate_limited_requester import GithubRateLimitedRequester


class GithubApiClient(object):
    def __init__(self, api_tokens):
        self._requester = GithubRateLimitedRequester(api_tokens)

    def get_commit_patch(self, url):
        content = ""
        response = self._requester.get(url)
        if response.status_code != 200:
            return content

        json_response = response.json()

        if "files" in json_response:
            for f in json_response["files"]:
                if "patch" not in f:
                    continue

                filename = f["filename"]
                status = f["status"]

                prefix = ""
                if status == "renamed":
                    prefix += "--- %s\n" % f["previous_filename"]
                else:
                    prefix += "--- %s\n" % filename
                prefix += "+++ %s\n" % filename
                content += prefix + f["patch"] + "\n"

        return content



