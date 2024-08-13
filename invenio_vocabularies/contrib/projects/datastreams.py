# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 CERN.
#
# Invenio-Vocabularies is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Projects datastreams, transformers, writers and readers."""

# TODO: Delete this file.

from invenio_i18n import lazy_gettext as _


VOCABULARIES_DATASTREAM_READERS = {}
"""Projects datastream readers."""

VOCABULARIES_DATASTREAM_TRANSFORMERS = {}
"""Projects datastream transformers."""

VOCABULARIES_DATASTREAM_WRITERS = {}
"""Projects datastream writers."""

DATASTREAM_CONFIG = {
    "readers": [
        {
            "type": "zip",
            "args": {
                "regex": "\\.xml$",
            },
        },
        {
            "type": "xml",
            "args": {
                "root_element": "project",
            },
        },
    ],
    "transformers": [
    ],
    "writers": [
    ],
}
"""Data Stream configuration.

An origin is required for the reader.
"""
