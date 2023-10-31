#!/usr/bin/env python3
"""A web scraper, maybe using AI"""

import argparse
import csv
import enum
import logging
import os
import sys
import typing

import openai
import psycopg
import psycopg_pool
import pydantic
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


class Toll_Facilitie_Model(pydantic.BaseModel):
    Country: str = "United States"
    IBTAA_Facility: str = ""
    IBTTA_TollOperator: str = ""
    Facility_Type: str = ""
    Interstate: bool = False
    FacilityOpenDate: str = ""
    IBTTA_Center_Miles: float = 0.0
    Ort: bool = False
    Cash: bool = False
    ETC: bool = False
    AET: bool = False
    AET_Some: bool = False
    ETL: bool = False
    HOT: bool = False
    Is_Static: bool = False
    Peak_Period: bool = False
    Real_Time: bool = False


class Facility_Type(enum.Enum):
    """Facility Type"""

    Other = "Other"
    Bridge = "Bridge"
    Tunnel = "Tunnel"
    Road = "Road"


class Toll_Rate_Model(pydantic.BaseModel):
    State_Or_Province: str = ""
    Facility_Label: str = ""
    Toll_Operator: str = ""
    Facility_type: Facility_Type = Facility_Type.Other
    Road_type: str = ""
    Interstate: bool = False
    Facility_open_date: str = ""
    Revenue_lane_Miles: float = 0.0
    Revenue: float = 0.0
    Length_Miles: float = 0.0
    Lane: float = 0.0
    Source_Type: str = ""
    Reference: str = ""
    Year: int = 0

    @pydantic.validator("Revenue", pre=True)
    def remove_commas(cls, value: str) -> float:
        """Removes commas from the value"""
        return float(value.replace(",", ""))


def read_csvfile(path: str) -> None:
    """Reads in the CSV file and returns the data"""
    toll_road_models: typing.List[Toll_Rate_Model] = []

    with open(path, encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file, delimiter="|")
        next(reader)
        for row in reader:
            toll_rate_model = Toll_Rate_Model(**row)
            toll_road_models.append(toll_rate_model)

    dbname = os.environ["POSTGRES_DB"]
    username = os.environ["POSTGRES_USER"]
    password = os.environ["POSTGRES_PASSWORD"]
    with psycopg.connect(
        f"dbname={dbname} user={username} host=postgres password={password}"
    ) as conn:
        cursor = conn.cursor()
        cursor.executemany("INSERT INTO toll_facilities VALUES (%s)", toll_road_models)
        # cursor.execute("INSERT INTO toll_facilities VALUES (%s)", toll_road_models)
        # result = cursor.fetchall()


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
    # resp = scrape_legislators("https://www.ilga.gov/house/rep.asp?MemberID=3071")
    # print(resp.data)
    read_csvfile(argparser.args.csv)


if __name__ == "__main__":
    main()
