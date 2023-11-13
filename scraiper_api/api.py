#!/usr/bin/python
# _*_ coding=utf-8 _*_
"""API server for scraiper."""

import logging
import os
import typing
import uvicorn

import fastapi
import requests  # type:ignore

MODULE_DESCRIPTION = """
the API server component of scraiper.</br>
"""
TAGS_METADATA = [
    {
        "name": "/api/v1/tolls",
        "description": "get toll info",
    },
    {"name": "/api/v1/health", "description": "The health endpoint."},
]


def log_error(err: str) -> None:
    """Logs the errors."""
    logging.exception(err)


def is_a_good_response(resp: requests.Response) -> bool:
    """Checks whether the get we sent got a 200 response."""
    content_type = resp.headers["Content-Type"].lower()
    return resp.status_code == 200 and content_type is not None


def simple_get(url: str) -> bytes:
    """Issues a simple get request."""
    content = bytes()
    try:
        with contextlib.closing(requests.get(url, stream=True)) as resp:
            if is_a_good_response(resp):
                content = resp.content
    except requests.exceptions.RequestException as e:
        log_error(f"Error during requests to {0} : {1}".format(url, str(e)))

    return content


def get_with_params(url: str, params: dict) -> typing.Optional[dict]:
    """Issues a get request with params."""
    try:
        with contextlib.closing(requests.get(url, params=params, stream=True)) as resp:
            if is_a_good_response(resp):
                return resp.json()
            return None
    except requests.exceptions.RequestException as e:
        log_error(f"Error during requests to {0} : {1}".format(url, str(e)))
        return None


app = fastapi.FastAPI(
    title="scraiper_api",
    description=MODULE_DESCRIPTION,
    contact={
        "name": "farzad sadeghi",
        "url": "https://behnoush.com",
        "email": "devi@terminaldweller.com",
    },
    license_info={
        "name": "",
        "url": "",
    },
    openapi_tags=TAGS_METADATA,
)


# https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html
@app.middleware("http")
async def add_secure_headers(request: fastapi.Request, call_next) -> fastapi.Response:
    """Adds security headers proposed by OWASP."""
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = "default-src-https"
    response.headers["Strict-Transport-Security"] = "max-age=63072000"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Access-Control-Allow-Methods"] = "GET,OPTIONS"
    return response


@app.get("/api/v1/tolls", tags=["/api/v1/tolls"])
def tolls_endpoint(
    url: str, feat: str = "", audio: bool = False, summarize: bool = False
):
    """The tolls info endpoint."""
    pass


@app.get("/api/v1/health", tags=["/api/v1/health"])
def health_ep():
    """The health endpoint."""
    return {"Content-Type": "application/json", "isOK": True}


@app.get("/api/v1/robots.txt")
def robots_ep():
    """The robots endpoint."""
    return {
        "Content-Type": "apllication/json",
        "User-Agents": "*",
        "Disallow": "/",
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
