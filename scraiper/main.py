#!/usr/bin/env python3
"""A web scraper, maybe using AI"""

import argparse
import concurrent.futures
import csv
import enum
import functools
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


def single_scrape(scrape_legislators, url: str) -> typing.Tuple[int, int]:
    try:
        resp = scrape_legislators(url)
        print(resp.data)
        result = resp.data
    except:
        result = ""
    return result


def multi_scrape(
    max_workers: int,
    scrape_legislators,
    urls: typing.List[str],
) -> typing.List[typing.Tuple[int, int]]:
    func = functools.partial(single_scrape, scrape_legislators)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        results = list(pool.map(func, urls))
    return results


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

    toll_road_models_dicts = [model.dict() for model in toll_road_models]
    with psycopg.connect(
        f"dbname={dbname} user={username} host=postgres password={password}"
    ) as conn:
        cursor = conn.cursor()
        query: str = """
INSERT INTO toll_facilities
(State_Or_Province, Facility_Label, Toll_Operator, Facility_type, Road_type, Interstate, Facility_open_date, Revenue_lane_Miles, Revenue, Length_Miles, Lane, Source_Type, Reference, Year)
VALUES  (%(State_Or_Province)s, %(Facility_Label)s, %(Toll_Operator)s, %(Facility_type)s, %(Road_type)s, %(Interstate)s, %(Facility_open_date)s, %(Revenue_lane_Miles)s, %(Revenue)s, %Length_Miles)s, %(Lane)s, %(Source_Type)s, %(Reference)s, %(Year)s)
"""
        cursor.executemany(query, toll_road_models_dicts)


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
            "Operation_Hour": "string",
            "Is_Reversible": "string",
            "Toll_Rate": "url",
            "Vehicle_Type": "string",
        }
    )
    # resp = scrape_legislators("https://www.ilga.gov/house/rep.asp?MemberID=3071")
    # print(resp.data)
    read_csvfile(argparser.args.csv)


if __name__ == "__main__":
    main()
