#!/usr/bin/env python3

#
# Licensed under the Apache 2.0 and MITnoAttr License.
#
# Copyright 2023 Fabian Lober. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with the License.

from typing import Any, Literal
import json
import os
import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.event_handler.exceptions import NotFoundError, ServiceError
import uuid

__author__ = "Fabian Lober"
__email__ = "fabian@lober.io"
__copyright__ = "Copyright 2023 Fabian Lober. All Rights Reserved."
__credits__: list[str] = ["Fabian Lober"]
__version__ = "1.0"


BOOKS_TABLE_NAME: str | None = os.getenv(key="BOOKS_TABLE_NAME")
AWS_REGION: str | None = os.getenv(key="REGION")

tracer = Tracer()
logger = Logger()
app = APIGatewayRestResolver()

SESSION1 = boto3.session.Session()

DYNAMOCLIENT = SESSION1.resource(
    service_name="dynamodb",
    region_name="eu-central-1",
)


@tracer.capture_method(capture_response=True)
def get_books_from_db() -> dict:
    books: list = []

    logger.info("Get all books from DB")

    try:
        table = DYNAMOCLIENT.Table(BOOKS_TABLE_NAME)

        response = table.scan(Limit=500)
        # response = table.scan()

        for item in response["Items"]:
            books.append(item)

    except Exception as err:
        logger.error("Error: %s", repr(err))
        raise

    return books


@tracer.capture_method(capture_response=True)
def put_book_to_db(book_id: str, book_title: str, book_desc: str) -> None:
    response = None

    logger.info("Put book with id: %s" % book_id)
    logger.append_keys(book_id=book_id)

    try:
        table = DYNAMOCLIENT.Table(BOOKS_TABLE_NAME)

        response = table.put_item(
            Item={
                "book_id": book_id,
                "book_title": book_title,
                "book_desc": book_desc,
            }
        )

    except Exception as err:
        logger.error("Error: %s", repr(err))
        raise

    return response


def delete_book_by_id_from_db(book_id: str) -> None:
    try:
        table = DYNAMOCLIENT.Table(BOOKS_TABLE_NAME)

        table.delete_item(Key={"book_id": book_id})

    except Exception as err:
        logger.error("Error: %s", repr(err))
        raise


@tracer.capture_method(capture_response=True)
def get_book_by_id_from_db(book_id: str) -> dict:
    book: dict = {}

    logger.info("Get book with id: %s" % book_id)
    logger.append_keys(book_id=book_id)

    try:
        table = DYNAMOCLIENT.Table(BOOKS_TABLE_NAME)

        response = table.get_item(Key={"book_id": book_id})

        if "Item" in response:
            for field in response["Item"]:
                book[field] = response["Item"][field]

    except Exception as err:
        logger.error("Error: %s", repr(err))
        raise

    return book


@tracer.capture_method(capture_response=True)
def update_book_in_db(book_id: str, book_title: str, book_desc: str) -> None:
    logger.info("Update book with id: %s" % book_id)
    logger.append_keys(book_id=book_id)

    try:
        table = DYNAMOCLIENT.Table(BOOKS_TABLE_NAME)

        response = table.update_item(
            Key={"book_id": book_id},
            UpdateExpression="set book_title = :title, book_desc = :desc",
            ExpressionAttributeValues={
                ":title": book_title,
                ":desc": book_desc,
            },
        )

    except Exception as err:
        logger.error("Error: %s", repr(err))
        raise


@app.post(rule="/fn/books")
@tracer.capture_method
def post_book() -> tuple[Any, Literal[202, 404, 500]]:
    response_status_code: int = 202
    response_body: dict = {}

    logger.info("Create new book")

    try:
        book_id: str = str(uuid.uuid4())
        book_title: str = app.current_event.json_body["book_title"]
        book_desc: str = app.current_event.json_body["book_desc"]

        response_body["book_id"] = book_id

        put_book_to_db(book_id=book_id, book_title=book_title, book_desc=book_desc)

        logger.info(f"Created new book with ID {book_id} successfully")
        logger.append_keys(book_id=book_id)

    except Exception as err:
        logger.error("ERROR - Unexpected error: %s" % err)

        raise ServiceError(status_code=500, msg="Unexpected System Error")

    return (
        json.loads(json.dumps(response_body)),
        response_status_code,
    )


@app.put("/fn/books/<book_id>")
@tracer.capture_method
def update_book(book_id) -> dict[str, Any]:
    response_status_code: int = 202
    response_body: dict = {}

    logger.info("Update book with id: %s" % book_id)
    logger.append_keys(book_id=book_id)

    try:
        book_title: str = app.current_event.json_body["book_title"]
        book_desc: str = app.current_event.json_body["book_desc"]

        put_book_to_db(book_id=book_id, book_title=book_title, book_desc=book_desc)

    except Exception as err:
        logger.error("ERROR - Unexpected error: %s" % err)

        raise ServiceError(status_code=500, msg="Unexpected System Error")

    return (
        json.loads(json.dumps(response_body)),
        response_status_code,
    )


@app.delete("/fn/books/<book_id>")
@tracer.capture_method
def delete_book(book_id) -> dict[str, Any]:
    response_status_code: int = 204
    response_body: dict = {}

    logger.info("Delete book with id: %s" % book_id)
    logger.append_keys(book_id=book_id)

    try:
        delete_book_by_id_from_db(book_id=book_id)

    except Exception as err:
        logger.error("ERROR - Unexpected error: %s" % err)

        raise ServiceError(status_code=500, msg="Unexpected System Error")

    return (
        json.loads(json.dumps(response_body)),
        response_status_code,
    )


@app.get("/fn/books/<book_id>")
@tracer.capture_method
def get_book(book_id) -> dict[str, Any]:
    response_status_code: int = 200
    response_body: dict = {}

    logger.info("Get book with id: %s" % book_id)
    logger.append_keys(book_id=book_id)

    try:
        response_body = get_book_by_id_from_db(book_id=book_id)

        if not response_body:
            raise NotFoundError(msg=f"Book not found")

    except NotFoundError as err:
        raise

    except Exception as err:
        logger.error("ERROR - Unexpected error: %s" % err)

        raise ServiceError(status_code=500, msg="Unexpected System Error")

    return (
        json.loads(json.dumps(response_body)),
        response_status_code,
    )


@app.get("/fn/books")
@tracer.capture_method
def get_books() -> dict[str, Any]:
    response_status_code: int = 200
    response_body: dict = {}

    logger.info("Get all books")

    try:
        response_body["books"] = get_books_from_db()

    except Exception as err:
        logger.error("ERROR - Unexpected error: %s" % err)

        raise ServiceError(status_code=500, msg="Unexpected System Error")

    return (
        json.loads(json.dumps(response_body)),
        response_status_code,
    )


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    return app.resolve(event, context)
