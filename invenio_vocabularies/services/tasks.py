# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 CERN.
#
# Invenio-Vocabularies is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Celery tasks."""

from celery import shared_task
from flask import current_app

from ..datastreams.factories import DataStreamFactory
from ..factories import get_vocabulary_config


@shared_task(ignore_result=True)
def process_datastream(config):
    """Process a datastream from config."""
    ds = DataStreamFactory.create(
        readers_config=config["readers"],
        transformers_config=config.get("transformers"),
        writers_config=config["writers"],
    )

    for result in ds.process():
        if result.errors:
            for err in result.errors:
                current_app.logger.error(err)


@shared_task(bind=True)
def process_funders(self):
    """Process the funders datastream."""
    vc = get_vocabulary_config("funders")
    config = vc.get_config()

    for w_conf in config["writers"]:
        w_conf["args"]["update"] = True

    ds = DataStreamFactory.create(
        readers_config=config["readers"],
        transformers_config=config.get("transformers"),
        writers_config=config["writers"],
    )

    for result in ds.process():
        if result.errors:
            for err in result.errors:
                current_app.logger.error(err)
