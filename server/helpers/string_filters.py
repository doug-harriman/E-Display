#!/usr/bin/python
# Filters strings based on list of substitutions in a file.

from __future__ import annotations
import os
import json
import re

from pydantic import BaseModel

# TODO: Add default string-filters.txt file with only:
# "[\(\[<].*?[\)\]>]", ""
# Do this after UI is done.


class StringFilter(BaseModel):
    """
    Simple string filtering object.

    Example:
    String to filter: "Hello world!"
    Filter: "world","universe"
    Result after filtering: "Hello universe!"

    >> filter = StringFilter("world", "universe")
    >> result = filter.filter("Hello world!")

    result = "Hello universe!"

    """

    regexp: str = ""
    replacement: str = ""

    def apply(self, text: str) -> str:
        """
        Filter a string based on a regular expression and replacement string.

        Example:
            Filter: "world","universe"
            String to filter: "Hello world!"
            Result after filtering: "Hello universe!"

        Args:
            text (str): String to filter.

        Returns:
            str: Filtered string.
        """

        # Assume no changes made.
        res = text

        if self.replacement is not None:
            # Have a replacement string, os use re.sub()
            res = re.sub(self.regexp, self.replacement, text)
        else:
            # Looking to remove the matched string, so use re.match()
            if re.match(self.regexp, text):
                res = ""

        return res


class StringFilterManager:
    def __init__(self) -> None:
        self._filename: str = "string-filters.json"
        self._filters = []

    def __str__(self) -> str:
        s = ""
        for filter in self._filters:
            s += f"{filter}\n"

        return s

    @property
    def filename(self) -> str:
        return self._filename

    def json(self, value: str = None) -> str:
        """
        Get a JSON representation of the filters.
        """

        s = "[\n"
        for filter in self._filters:
            s += f"    {filter.json()},\n"
        s = s[:-2]
        s += "\n]\n"

        return s

    def save(self, filename: str = None) -> None:
        """
        Saves the filters to a file as JSON.

        Args:
            filename (str, optional): File name. Defaults to 'string-filters.json'.
        """

        if filename is None:
            filename = self._filename

        if not isinstance(filename, str):
            raise TypeError(f"Filename must be a string, got: {type(filename)}")

        if filename is None:
            self._filename = filename

        with open(filename, "w") as f:
            f.write(self.json())

    def load(self, filename: str = None) -> None:
        """
        Read the filters from a JSON file.

        Args:
            filename (str, optional): File name. Defaults to "string-filters.json".
        """
        import json

        if filename is None:
            filename = self._filename

        if not isinstance(filename, str):
            raise TypeError(f"Filename must be a string, got: {type(filename)}")

        if not os.path.exists(filename):
            raise FileExistsError(f"File does not exist: {filename}")

        if filename is not None:
            self._filename = filename

        with open(filename, "r") as fp:
            try:
                data = json.load(fp)
            except:  # noqa: E722
                # Error loading data.
                return

        for filter in data:
            self += StringFilter(**filter)

    @property
    def filters(self) -> list:
        """
        Get the list of filters.
        """
        return self._filters

    def clear(self) -> None:
        """
        Clear the list of filters.
        """

        self._filters = []

    def add(self, filter: StringFilter) -> None:
        """
        Add a filter to the list of filters.
        Filter is verified before adding.

        Args:
            filter (StringFilter): Filter to add.
        """

        # Validate filter.
        if not isinstance(filter, StringFilter):
            raise ValueError("Filter must be a StringFilter object.")

        # Disallow duplicates
        if filter in self._filters:
            return

        self._filters.append(filter)

    def remove(self, filter: StringFilter) -> None:
        """
        Removes a filter from the list of filters.

        Args:
            filter (StringFilter): Filter to remove.
        """

        if not isinstance(filter, StringFilter):
            raise ValueError(f"Filter must be a StringFilter object: {type(filter)}")

        self._filters.remove(filter)

    def replace(self, filter_old: StringFilter, filter_new: StringFilter) -> None:
        """
        Replace an existing filter with a new filter.

        Args:
            filter_old (StringFilter): Filter to be replaced.
            filter_new (StringFilter): New filter to replace with.

        Raises:
            ValueError: If filter_old is not found.
        """

        if not isinstance(filter_old, StringFilter):
            raise ValueError(
                f"Filter must be a StringFilter object: {type(filter_old)}"
            )

        if not isinstance(filter_new, StringFilter):
            raise ValueError(
                f"Filter must be a StringFilter object: {type(filter_new)}"
            )

        if filter_old not in self._filters:
            raise ValueError(f"Filter not found: {filter_old}")

        idx = self._filters.index(filter_old)
        self._filters[idx] = filter_new

    def __iadd__(self, filter: StringFilter) -> StringFilterManager:
        """
        Add a filter to the list of filters.
        Filter is verified before adding.

        Args:
            filter (StringFilter): Filter to add.

        Returns:
            StringFilterManager: This object.
        """

        self.add(filter)

        return self

    def __isub__(self, filter: StringFilter) -> StringFilterManager:
        """
        Removes a filter from the list of filters.

        Args:
            filter (StringFilter): Filter to remove.

        Returns:
            StringFilterManager: This object.
        """

        self.remove(filter)

        return self

    def apply(self, string: str) -> str:
        """
        Filter a string based on all loaded list of StringFilter objects.

        Args:
            string (str): String to filter.

        Returns:
            str: Filtered string.
        """

        # Validate filters.
        if len(self._filters) == 0:
            raise ValueError("No filters loaded.")

        # Apply filters.
        for filter in self.filters:
            string = filter.apply(string)

        # Eliminate multiple spaces.
        string = " ".join(string.split())
        string = string.strip()

        return string


if __name__ == "__main__":
    s1 = "2023 CONCACAF Gold Cup, Group A: U.S. Men vs. Saint Kits"
    # Filters:
    # "CONCACAF Gold Cup,",""
    # "202\d",""
    # "Group A:",""

    fm = StringFilterManager()
    f = StringFilter(regexp="CONCACAF Gold Cup,", replacement="")
    print(f)
    fm += f
    f = StringFilter(regexp="202\d", replacement="")
    fm += f

    print(f"'{s1}'")
    s2 = fm.apply(s1)
    print(f"'{s2}'")

    # Remove one of the filtes
    print(fm)
    fm -= f
    print(fm)

    fm.save()
