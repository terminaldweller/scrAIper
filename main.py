#!/usr/bin/env python3
"""A web scraper, maybe using AI"""

import argparse
import csv
import logging
import os
import sys
import typing

import psycopg
import psycopg_pool
import openai
from scrapeghost import SchemaScraper


class Argparser:  # pylint: disable=too-few-public-methods
    """Argparser class."""

    def __init__(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--csv", type=str, help="path to the csv file", default="")
        parser.add_argument(
            "--maxworkers",
            type=int,
            help="maxworkers to pass to ThreadPoolExecutor",
            default=32,
        )
        parser.add_argument("--apikey", type=str, help="the api key", default="")
        self.args = parser.parse_args()


def read_csvfile(
    path: str,
) -> typing.Tuple[typing.List[str], typing.List[str]]:
    """Reads in the CSV file and returns the data"""
    a: typing.List[str] = []
    b: typing.List[str] = []

    with open(path, encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            a.append(row["A"])
            b.append(row["B"])

    return a, b


def main() -> None:
    """The entrypoint"""
    argparser = Argparser()
    openai.api_key = os.environ["OPENAI_API_KEY"]
    if openai.api_key == "":
        logging.critical(
            "no openai api key set in the environment variable OPENAI_API_KEY. exiting ..."
        )
        sys.exit(1)
    scrape_legislators = SchemaScraper(
        schema={
            "name": "string",
            "url": "url",
            "district": "string",
            "party": "string",
            "photo_url": "url",
            "offices": [{"name": "string", "address": "string", "phone": "string"}],
        }
    )
    resp = scrape_legislators("https://www.ilga.gov/house/rep.asp?MemberID=3071")
    print(resp.data)


if __name__ == "__main__":
    main()
