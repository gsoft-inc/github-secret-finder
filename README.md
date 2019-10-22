# github-secret-finder

Script to monitor commits from Github users and organizations for secrets.

## Setup
```
pip3 install -r requirements.txt
```

## Usage
```
usage: main.py [-h] [--users USERS] [--user USER] [--emails EMAILS]
               [--email EMAIL] [--names NAMES] [--name NAME]
               [--organizations ORGANIZATIONS] [--organization ORGANIZATION]
               --tokens TOKENS [--blacklist BLACKLIST_FILE]
               [--slack-webhook SLACK_WEBHOOK] [--results] [--verbose]

Github Secret Finder

optional arguments:
  -h, --help            show this help message and exit
  --users USERS, -U USERS
                        File containing Github users to monitor.
  --user USER, -u USER  Single Github user to monitor.
  --emails EMAILS, -E EMAILS
                        File containing email addresses to monitor.
  --email EMAIL, -e EMAIL
                        Single email address to monitor.
  --names NAMES, -N NAMES
                        File containing full names to monitor.
  --name NAME, -n NAME  Single full name to monitor.
  --organizations ORGANIZATIONS, -O ORGANIZATIONS
                        File containing organizations to monitor.
  --organization ORGANIZATION, -o ORGANIZATION
                        Single organization to monitor.
  --tokens TOKENS, -t TOKENS
                        Github tokens separated by a comma (,)
  --blacklist BLACKLIST_FILE, -B BLACKLIST_FILE
                        File containing regexes to blacklist file names.
                        Defaults to default-blacklist.json
  --slack-webhook SLACK_WEBHOOK, -w SLACK_WEBHOOK
                        Slack webhook to send messages when secrets are found.
  --results, -r         Shows the previously found results.
  --verbose, -v         Increases output verbosity.
```

