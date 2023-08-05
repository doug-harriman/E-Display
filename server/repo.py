# Git Repository tools.

# Copied from Simplexity FW-Tools repo at SHA 47f5c61
# https://bitbucket.org/simplexity-ondemand/fw-tools/commits/47f5c6185cc1d4f29e3fa16502d4c4b69d7d21b2
# Deprecated from that repo.

import re
import warnings
import sh
import json
import datetime
import pandas as pd
from collections import OrderedDict
import logging

# Future Features:
# - Repo figures out if it's BitBucket or GitHub.
# - Capture repo name & use that on dashboard.
# - Make the 'metrics-' string a property of the repo & use that everywhere.
# - Command line arg processor.
# - Abstract metrics into their own file so they're more easily modified.
# - Set up as proper Python module so easier to install dependencies.


class Commit:
    """
    Commit data for an existing commit, immutable.
    """

    def __init__(
        self,
        repo,
        sha: str = None,
        timestamp=None,
        subject: str = None,
        author: str = None,
        author_email: str = None,
    ):
        self._sha = sha
        self._repo = repo

        if isinstance(timestamp, str):
            self._timestamp = datetime.datetime.strptime(
                timestamp, "%Y-%m-%d %H:%M:%S %z"
            )
        if isinstance(timestamp, datetime.datetime):
            self._timestamp = timestamp

        self._subject = subject
        self._author = author
        self._author_email = author_email
        self._metrics = {}

        # Capture metric data if it exists for this commit.
        # Check for tags on this Commit.  If a metric tag, read the data.
        for tag in self.tags:
            if "metrics-" in tag:
                data = self._repo.git.tag("-l", "--format=%(contents)", tag)
                data = data.strip()
                self._metrics = json.loads(data)

    def __str__(self) -> str:
        """
        String representation of Commit.

        Returns:
            str: String representation of commit.
        """

        s = f"{self._sha[:6]} ({self._timestamp.strftime('%d-%b-%Y %H:%M:%S')}) {self._subject}"

        return s

    def __repr__(self) -> str:
        return f"Commit({self._sha[:6]})"

    @property
    def sha(self) -> str:
        """
        Returns commit SHA string.
        """

        return self._sha

    @property
    def subject(self) -> str:
        """
        Subject line of commit.

        Returns:
            str: Commit subject line.
        """

        return self._subject

    @property
    def author(self) -> str:
        """
        Author of commit.

        Returns:
            str: Author name per 'git log --format=%aN'
        """

        return self._author

    @property
    def author_email(self) -> str:
        """
        Email of author of commit.

        Returns:
            str: Author's email  per 'git log --format=%aE'
        """

        return self._author_email

    @property
    def tags(self) -> list:
        """
        Tags associated with this commit.

        Returns:
            str: Tags associated with commit.
        """

        tags = self._repo.git.tag("--points-at", self.sha)
        tags = tags.splitlines()

        return tags

    @property
    def timestamp(self) -> datetime.datetime:
        """
        Time stamp of commit.

        Returns:
            datetime.datetime: Time stamp.
        """
        return self._timestamp

    @property
    def pr(self) -> int:
        """
        Pull request number of commit.
        None is returned if this commit is not associated
        with a pull request.

        Returns:
            int: Pull request number of commit.
        """

        pr = re.search("\(pull request #(\d+)\)", self.subject)
        if pr is None:
            return None

        pr = int(pr.group(1))

        return pr

    @property
    def url(self) -> str:
        """
        URL of remote HTTP server page for this commit.

        Returns:
            str: URL for commit.
        """

        return f"{self._repo.url_base}/commits/{self.sha}"

    @property
    def url_pr(self) -> str:
        """
        URL of remote HTTP server page for pull request for this commit.
        Returns None if no Pull Request associated with commit.

        Returns:
            str: URL of Pull Request or None.
        """

        if self.pr is None:
            return None

        return f"{self._repo.url_base}/pull-requests/{self.pr}"

    def checkout(self) -> None:
        """
        Checks out commit in repository.

        Returns: None
        """
        self._repo.checkout(self._sha)

    def log(self) -> str:
        res = self._repo.git.log("-n1", self._sha)
        return res

    def metrics_calc(self):
        """
        Calculates and stores all metrics registered on the commit's repo.

        The repository checked out to this commit, then the metric functions
        are run.
        """

        # Make sure this commit is the current commit
        self.checkout()

        # Clean the repo except this file.
        # self._repo.git.clean('-dxf', f'-e {__file__}')

        # Run each of the metric calc functions
        metrics = {}
        for metric in self._repo.metrics:
            metric.calc(sha=self.sha[:6])
            if metric.metrics is not None:
                metrics = {**metrics, **metric.metrics}

        self._metrics = metrics

    @property
    def metrics(self) -> dict:
        return self._metrics

    def metrics_tag(self, build: str = None):
        """
        Tags this commit in the repository with a JSON representation
        of the metric values for this commit.

        Args:
            build (str): Build identifier string. Placed within tag.  Default=None

        Returns:
            _type_: _description_
        """

        # Make sure this commit is the current commit
        self.checkout()

        # If we don't have any metric, try to generate it.
        # If still none, then warn and skip.
        if self.metrics is None:
            self.metrics_calc()
        if self.metrics is None:
            warnings.warn(f"No metric data for {self}, skipping.")
            return

        # Generate metrics tag string
        tagstr = "metrics-"
        if build is not None:
            tagstr += build
            tagstr += "-"
        tagstr += self.timestamp.strftime("%Y-%m-%d-%H-%M")
        tagstr += "-"
        tagstr += self.sha[:8]

        # Check for existing tag
        # If tag exists, we want to overwrite it.
        # That requires deleting and writing a new tag.
        log = logging.getLogger(__name__)
        if tagstr in self.tags:
            log.warning(f"Tag exists: {tagstr}, deleting & replacing")

            # Delete locally
            self._repo.git.tag("-d", tagstr)

            # Delete on origin (if was already pushed)
            # git push --delete origin tagname
            try:
                self._repo.git.push("--delete", "origin", tagstr)
            except:
                pass

        # Tag the repo.
        data = json.dumps(self.metrics)
        self._repo.git.tag("-a", tagstr, "-m", data)

        # Push this tag.
        self._repo.git.push("origin", tagstr)


class Repo:
    def __init__(self, dir: str = None, default_branch: str = None):
        # Default directory
        if dir is None:
            dir = "."  # os.getcwd()
        self._dir = dir
        self._git = sh.git.bake("--no-pager", _cwd=dir)

        # Get repo to default branch if provided
        self._default_branch = default_branch
        if default_branch is not None:
            self.checkout(default_branch)

        # List of metrics to run upon request.
        self._metrics = []
        self._metadata_cols = ["Time Stamp", "SHA", "Pull Request", "Author"]

        # URL to repo
        self._url_base = None

        # Log format string.
        self._log_format = '--format={"sha":"%H","timestamp":"%ai","subject":"%s","author":"%aN","author_email":"%aE"}'

    def __str__(self) -> str:
        """
        Stringifier for Repo object.

        Returns:
            str: string representation of Repo.
        """

        return f"Repo({self.dir})"

    def __repr__(self) -> str:
        return self.__str__()

    @property
    def dir(self) -> str:
        """
        Directory for the repository.

        Returns:
            str: Path of directory.
        """

        return self._dir

    @property
    def git(self) -> sh.Command:
        """
        Returns sh.Command object for git command pointing at Repo.

        Returns:
            sh.Command: git command object.
        """

        return self._git

    @property
    def url_base(self) -> str:
        """
        Returns base URL to remote HTTP server.

        Returns:
            str: base URL
        """

        # URL
        # https://bitbucket.org/simplexity-ondemand/barista-fw/src/main/
        # git remote -v
        # origin  git@bitbucket.org:simplexity-ondemand/barista-fw.git (fetch)
        # origin  git@bitbucket.org:simplexity-ondemand/barista-fw.git (push)

        if self._url_base is not None:
            return self._url_base

        url = self.git.remote("-v").splitlines()[0]
        url = url[url.find("@") + 1 :]
        url = url[: url.find(".git")]
        url = url.replace(":", "/")
        url = "https://" + url
        self._url_base = url

        return self._url_base

    @property
    def branch(self) -> str:
        """
        Name of currently active branch.

        Returns:
            str: Branch name
        """

        br = self.git.branch("--show-current").strip()
        return br

    @property
    def url(self) -> str:
        """
        Returns URL to host HTTP server default branch.

        Returns:
            str: URL to default branch.
        """

        url = f"{self.url_base}/src/{self._default_branch}/"
        return url

    def url_pull_request(self, pr: int = None) -> str:
        """
        Returns URL to pull request on server.
        If no PR number is provided, the base PR URL is returned.

        Args:
            pr (int, optional): Pull request number. Defaults to None.

        Returns:
            str: URL
        """

        url = f"{self.url_base}/pull-requests/"

        if pr is not None:
            url = f"{url}{pr}"

        return url

    def url_commit(self, sha: str = None) -> str:
        """
        Returns URL to commit on server.
        If no commit SHA is provided, the base commit URL is returned.

        Args:
            sha (str, optional): SHA. Defaults to None.

        Returns:
            str: URL
        """

        url = f"{self.url_base}/commits/"

        if sha is not None:
            url = f"{url}{sha}"

        return url

    @property
    def current(self) -> Commit:
        """
        Commit object for current commit.

        Returns:
            Commit: Commit object for current commit.
        """

        commit = self._git.log("-n1", self._log_format).strip()
        commit = json.loads(commit)
        commit = Commit(self, **commit)
        return commit

    def commit_by_sha(self, sha: str) -> Commit:
        """
        Returns the Commit object specified by the given SHA.

        Args:
            sha (str): SHA of commit to find.

        Returns:
            Commit: Commit object with given SHA or None if not found.
        """

        try:
            commit = self._git.log("-n1", self._log_format, sha).strip()
            commit = json.loads(commit)
            commit = Commit(self, **commit)
        except:  # noqa: E722
            commit = None

        return commit

    def pullrequests(self) -> dict:
        """
        Generate dictionary of commits keyed by pull request number.

        Returns:
            dict: Dictionary of commits keyed by pull request number.
        """

        # git log --grep "pull request" --format="%h  %ai %s %d" --tags
        # Commits is now a list of dictionaries of commit info for commits with 'pull request' in the subject.
        commits = self._git.log("--grep", "pull request", self._log_format)
        commits = commits.splitlines()
        commits = [json.loads(commit) for commit in commits]

        ids = [
            int(re.search("\(pull request #(\d+)\)", commit["subject"]).group(1))
            for commit in commits
        ]

        commits = [Commit(self, **commit) for commit in commits]

        return dict(zip(ids, commits))

    def tags(self, tag_re: str = "*") -> list:
        """
        Generates list of commits identified by given tag regular expression.
        If no regular expression string provided, returns all tagged commits.

        Args:
            tag_re (str, optional): Tag regex filter string. Defaults to None.

        Returns:
            list: List of commits with matching tags.
        """

        # List of tags
        tags = self._git.log("--no-walk", f"--tags={tag_re}", self._log_format)
        commits = tags.splitlines()

        # Get commit info associated with each tag.
        commits = [json.loads(commit) for commit in commits]

        return [Commit(self, **commit) for commit in commits]

    def releases(self, tag_re: str = "release-*") -> dict:
        """
        Generates dictionary of commits keyed by commit date string.
        Commits can be filtered by a tag regexp.

        Args:
            tag_re (str): Tag string regular expression to match.  Default='release-*'.

        Returns:
            dict: Dictionary of commits keyed by release commit date.
        """

        # List of commits with tag string.
        commits = self.tags(tag_re=tag_re)

        # Dates for keys
        dates = [commit.timestamp.strftime("%Y-%m-%d-%H-%M") for commit in commits]

        return OrderedDict(zip(dates, commits))

    def metric_commits(self, tag_re: str = "metrics-*") -> dict:
        """
        Generates a ditionary of commits keyed by commit date string.
        Commits are those tagged by the given string.
        This is a convenience function.

        Args:
            tag_re (str, optional): String to use for filtering tags . Defaults to 'metrics-*'.

        Returns:
            dict: Dictionary of commits with metric data keyed by date.
        """

        return self.releases(tag_re=tag_re)

    def checkout(self, sha: str = None) -> None:
        """
        Checks out the commit specified by the given SHA.
        If no SHA provided, will check out to default_branch.

        Args:
            sha (str): SHA to check out.
        """

        if sha is None:
            if self._default_branch is not None:
                self._git.checkout(self._default_branch)

        try:
            self._git.checkout("--force", sha)
        except sh.ErrorReturnCode_2:
            print("Checkout failed, repository has changes.")

    def remote_status(self) -> str:
        """
        Returns status of this repository relative to remote.

        Returns:
            str: Ahead/behind commit status relative to remote.
        """

        # Fetch the latest stuff from remote.
        self.git.fetch()

        # Get status of local branch relative to remote.
        res = self.git.status("-sb", _tty_out=False)

        # Find status line for current branch
        status = None
        for line in res.splitlines():
            if self.branch in line:
                status = line
                break

        if status is None:
            raise RuntimeError("Could not find status line for current branch.")

        idx1 = status.find("[")
        idx2 = status.find("]")
        status = status[idx1 + 1 : idx2]

        if idx1 == -1:
            # Up to date
            status = "up to date"

        return status

    @property
    def remote_current(self) -> Commit:
        """
        Remote current Commit object.

        Returns:
            Commit: Commit object for latest commit on current branch on remote.
        """

        # Fetch the latest stuff from remote.
        self.git.fetch()
        remote = "origin/" + self.branch

        # Get Commit object for that SHA
        try:
            commit = self._git.log("-n1", remote, self._log_format).strip()
            commit = json.loads(commit)
            commit = Commit(self, **commit)
        except:  # noqa: E722
            commit = None

        return commit

        return commit

    def metric_add(self, metric):
        self._metrics.append(metric)

    @property
    def metrics(self) -> list:
        """
        List of Metric objects associated with this Repo.

        Returns:
            list: Metric objects associated with Repo
        """

        return self._metrics

    def metrics_to_dataframe(self) -> pd.DataFrame:
        """
        Returns Pandas DataFrame with all metric data in Repo.

        Returns:
            pd.DataFrame: DataFrame of metric data.
        """

        df = pd.DataFrame()

        # List of metric tags
        commits = self.metric_commits()
        commits = list(commits.values())

        # Convert those to DataFrame
        metrics = [commit.metrics for commit in commits]
        df = pd.DataFrame(metrics)
        cols = list(df.columns)

        # Add in commit metadata
        df["SHA"] = [commit.sha[:6] for commit in commits]
        df["Time Stamp"] = [commit.timestamp for commit in commits]
        df["Pull Request"] = [commit.pr for commit in commits]
        df["Author"] = [commit.author for commit in commits]

        # Order columns nicely
        cols = self._metadata_cols + cols
        df = df[cols]

        return df

    def metrics_to_csv(self, filename: str = "metrics.csv") -> None:
        """
        Writes Repo metric data to CSV file.
        Convenience function using Pandas DataFrame to_csv() method.

        Args:
            filename (str, optional): CSV file name. Defaults to 'metrics.csv'.

        Returns:
            pd.DataFrame: DataFrame of metric data.
        """

        df = self.metrics_to_dataframe()
        df.to_csv(filename, index=False)

        return df
