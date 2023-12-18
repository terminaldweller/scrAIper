#!/usr/bin/env python3
"""A web scraper, maybe using AI"""

import argparse
import concurrent.futures
import csv
import enum
import functools
import hashlib
import json
import logging
import os
import sys
import time
import typing
import urllib.parse

import openai
import psycopg

# import psycopg_pool
import pydantic
import requests

# from scrapeghost import SchemaScraper
import tabula


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
        parser.add_argument(
            "--headers",
            type=str,
            help="a file containing the headers for the GET requests",
            default="",
        )
        parser.add_argument("--apikey", type=str, help="the api key", default="")
        self.args = parser.parse_args()


class FacilityType(enum.Enum):
    """Facility Type"""

    OTHER = "Other"
    BRIDGE = "Bridge"
    TUNNEL = "Tunnel"
    ROAD = "Road"


class TollRateModel(pydantic.BaseModel):
    """The toll rate model."""

    State_Or_Province: str = ""
    Facility_Label: str = ""
    Toll_Operator: str = ""
    Facility_type: FacilityType = FacilityType.OTHER
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

    @pydantic.validator("State_Or_Province", pre=True)
    def ignore_facility_label(cls, value: str) -> str:
        try:
            return value
        except (ValueError, TypeError):
            return ""

    @pydantic.validator("Interstate", pre=True)
    def ignore_interstate(cls, value: str) -> bool:
        try:
            if value.lower() == "yes":
                return True
            elif value.lower() == "no":
                return False
            return False
        except (ValueError, TypeError):
            return False

    @pydantic.validator("Revenue", pre=True)
    def ignore_revenue(cls, value: str) -> float:
        try:
            return float(value.replace(",", ""))
        except (ValueError, TypeError):
            return 0.0

    @pydantic.validator("Year", pre=True)
    def ignore_year(cls, value: str) -> int:
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0

    @pydantic.validator("Lane", pre=True)
    def ignore_lane(cls, value: str) -> float:
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0


def get_proxies() -> typing.Dict:
    """Get the proxy env vars."""
    http_proxy: typing.Optional[str] = ""
    if "HTTP_PROXY" in os.environ and os.environ["HTTP_PROXY"] != "":
        http_proxy = os.environ["HTTP_PROXY"]

    https_proxy: typing.Optional[str] = ""
    if "HTTPS_PROXY" in os.environ and os.environ["HTTPS_PROXY"] != "":
        https_proxy = os.environ["HTTPS_PROXY"]

    no_proxy: typing.Optional[str] = ""
    if "NO_PROXY" in os.environ and os.environ["NO_PROXY"] != "":
        no_proxy = os.environ["NO_PROXY"]

    return {"http": http_proxy, "https": https_proxy, "no_proxy": no_proxy}


def single_scrape(scrape_legislators, url: str) -> typing.Tuple[int, int]:
    """Scrape one url."""
    try:
        resp = scrape_legislators(url)
        print(resp.data)
        result = resp.data
    except Exception:  # pylint: disable=broad-except
        result = ""
    return result


def get_user_agent() -> str:
    """Returns a random user agent."""
    user_agent: str = ""
    if "MAGNI_USER_AGENT" in os.environ and os.environ["MAGNI_USER_AGENT"]:
        user_agent = os.environ["MAGNI_USER_AGENT"]
    else:
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"

    return user_agent


def get_headers() -> typing.Dict[str, str]:
    """Sets the ncessary headers."""
    headers: typing.Dict = {}

    if argparser.args.headers != "":
        with open(argparser.args.headers, "r", encoding="utf-8") as headers_file:
            headers = json.load(headers_file)
    else:
        headers = {
            "User-Agent": get_user_agent(),
        }

    return headers


def single_get(url: str) -> None:
    """Get one pdf file.""" ""
    try:
        backoff: int = 15
        backoff_multiplier: int = 2
        while True:
            response = requests.get(
                url,
                allow_redirects=True,
                timeout=10,
                proxies=get_proxies(),
                headers=get_headers(),
            )
            if response.ok:
                with open(f"/pdfs/{get_pdf_hash(url)}.pdf", "wb") as file:
                    file.write(response.content)
                break
            time.sleep(backoff)
            backoff = backoff * backoff_multiplier
    except Exception as e:  # pylint: disable=broad-except
        logging.fatal("was not able to get %s. error: %s", url, e)


def multi_get(urls: typing.List[str]) -> None:
    """Get multiple pdf files concurrently.""" ""
    with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
        response_list = list(pool.map(single_get, urls))
        for response in response_list:
            logging.debug("GET: %s", response)


def multi_scrape(
    max_workers: int,
    scrape_legislators,
    urls: typing.List[str],
) -> typing.List[typing.Tuple[int, int]]:
    """Scrape multiple urls concurrently."""
    func = functools.partial(single_scrape, scrape_legislators)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        results = list(pool.map(func, urls))
    return results


def read_csvfile(path: str, cursor) -> None:
    """Reads in the CSV file and returns the data"""
    toll_road_models: typing.List[TollRateModel] = []
    epoch_time = int(time.time())

    with open(path, encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file, delimiter="|")
        next(reader)
        for row in reader:
            toll_rate_model = TollRateModel(**row)
            toll_road_models.append(toll_rate_model)

    create_main_table_query = """
CREATE TABLE IF NOT EXISTS toll_facility_history (
	event_time bigint NOT NULL PRIMARY KEY
);
"""
    cursor.execute(create_main_table_query)
    create_table_query = f"""
CREATE TABLE IF NOT EXISTS toll_facilities_{epoch_time} (
    id SERIAL PRIMARY KEY,
    state_or_province VARCHAR(255) NOT NULL,
    facility_label VARCHAR(255) NOT NULL,
    toll_operator VARCHAR(255) NOT NULL,
    facility_type VARCHAR(255) NOT NULL,
    road_type VARCHAR(255) NOT NULL,
    interstate boolean NOT NULL,
    facility_open_date VARCHAR(255) NOT NULL,
    revenue_lane_miles float NOT NULL,
    revenue float NOT NULL,
    length_miles float NOT NULL,
    lane float NOT NULL,
    source_type VARCHAR(255) NOT NULL,
    reference VARCHAR(255) NOT NULL,
    year integer NOT NULL
);
    """
    cursor.execute(create_table_query)
    update_main_query = f"""
INSERT INTO toll_facility_history (event_time) VALUES ({epoch_time});
    """
    cursor.execute(update_main_query)
    toll_road_models_dicts = [model.dict() for model in toll_road_models]
    query: str = f"""
INSERT INTO toll_facilities_{epoch_time}
(State_Or_Province, Facility_Label, Toll_Operator, Facility_type, Road_type, Interstate, Facility_open_date, Revenue_lane_Miles, Revenue, Length_Miles, Lane, Source_Type, Reference, Year)
VALUES  (%(State_Or_Province)s, %(Facility_Label)s, %(Toll_Operator)s, %(Facility_type)s, %(Road_type)s, %(Interstate)s, %(Facility_open_date)s, %(Revenue_lane_Miles)s, %(Revenue)s, %(Length_Miles)s, %(Lane)s, %(Source_Type)s, %(Reference)s, %(Year)s)
"""
    cursor.executemany(query, toll_road_models_dicts)


# def scrape_all(cursor) -> None:
#     """Scrapes all the data from the given urls"""
#     query = """
# select distinct Reference from public.toll_facilities;
#     """
#     cursor.execute(query)


def get_pdf_hash(url: str) -> str:
    """Returns the md5 hash of the pdf"""
    return hashlib.md5(url.encode("utf-8"), usedforsecurity=False).hexdigest()


argparser = Argparser()


def main() -> None:
    """The entrypoint"""
    openai.api_key = os.environ["OPENAI_API_KEY"]
    if openai.api_key == "":
        logging.critical(
            "no openai api key set in the environment variable OPENAI_API_KEY. exiting ..."
        )
        sys.exit(1)
    # scrape_legislators = SchemaScraper(
    #     schema={
    #         "name": "string",
    #         "Operation_Hour": "string",
    #         "Is_Reversible": "string",
    #         "Toll_Rate": "url",
    #         "Vehicle_Type": "string",
    #     }
    # )

    dbname = os.environ["POSTGRES_DB"]
    username = os.environ["POSTGRES_USER"]
    password = os.environ["POSTGRES_PASSWORD"]
    with psycopg.connect(
        f"dbname={dbname} user={username} host=postgres password={password}"
    ) as conn:
        with conn.cursor() as cursor:
            query = """
SELECT DISTINCT Reference FROM public.toll_facilities;
            """
            cursor.execute(query)
            res = cursor.fetchall()
            # print(res)
            urls = [
                url[0]
                for url in res
                if all(
                    [
                        urllib.parse.urlparse(url[0]).scheme,
                        urllib.parse.urlparse(url[0]).netloc,
                    ]
                )
            ]
            for url in urls:
                print(url)

            if not os.path.exists("/pdfs"):
                os.makedirs("/pdfs")
            multi_get(urls)
            # resp = scrape_legislators("https://www.ilga.gov/house/rep.asp?MemberID=3071")
            # print(resp.data)
            if argparser.args.csv:
                read_csvfile(argparser.args.csv, cursor)

            # print(
            #     get_pdf_hash(
            #         """
            #         https://floridasturnpike.com/wp-content/uploads/2022/12/FY_2022_Floridas_Turnpike_Enterprise_ACFR.pdf
            #         """
            #     )
            # )
            # dfs = tabula.read_pdf(
            #     """
            #     https://floridasturnpike.com/wp-content/uploads/2022/12/FY_2022_Floridas_Turnpike_Enterprise_ACFR.pdf
            #     """,
            #     pages="all",
            # )
            # print(dfs)


if __name__ == "__main__":
    main()
