# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2024 CERN.
# Copyright (C) 2024 California Institute of Technology.
#
# Invenio-Vocabularies is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Affiliations datastreams, transformers, writers and readers."""
import io

import requests
from flask import current_app
from invenio_i18n import lazy_gettext as _

from ...datastreams.errors import ReaderError, WriterError
from ...datastreams.readers import BaseReader
from ...datastreams.transformers import BaseTransformer
from ...datastreams.writers import ServiceWriter
from ..common.ror.datastreams import RORTransformer


class AffiliationsServiceWriter(ServiceWriter):
    """Affiliations service writer."""

    def __init__(self, *args, **kwargs):
        """Constructor."""
        service_or_name = kwargs.pop("service_or_name", "affiliations")
        super().__init__(service_or_name=service_or_name, *args, **kwargs)

    def _entry_id(self, entry):
        """Get the id from an entry."""
        return entry["id"]


class AffiliationsRORTransformer(RORTransformer):
    """Affiliations ROR Transformer."""

    def __init__(
        self, *args, vocab_schemes=None, funder_fundref_doi_prefix=None, **kwargs
    ):
        """Constructor."""
        if vocab_schemes is None:
            vocab_schemes = current_app.config.get("VOCABULARIES_AFFILIATION_SCHEMES")
        super().__init__(
            *args,
            vocab_schemes=vocab_schemes,
            funder_fundref_doi_prefix=funder_fundref_doi_prefix,
            **kwargs,
        )


class OpenAIREOrganizationHTTPReader(BaseReader):
    """OpenAIRE Organization HTTP Reader returning an in-memory binary stream of the latest OpenAIRE Graph Dataset Organization tar file."""

    def _iter(self, fp, *args, **kwargs):
        raise NotImplementedError(
            "OpenAIREOrganizationHTTPReader downloads one file and therefore does not iterate through items"
        )

    def read(self, item=None, *args, **kwargs):
        """Reads the latest OpenAIRE Graph Dataset organization tar file from Zenodo and yields an in-memory binary stream of it."""
        if item:
            raise NotImplementedError(
                "OpenAIREOrganizationHTTPReader does not support being chained after another reader"
            )

        # OpenAIRE Graph Dataset
        api_url = "https://zenodo.org/api/records/3516917"

        # Call the signposting `linkset+json` endpoint for the Concept DOI (i.e. latest version) of the OpenAIRE Graph Dataset.
        # See: https://github.com/inveniosoftware/rfcs/blob/master/rfcs/rdm-0071-signposting.md#provide-an-applicationlinksetjson-endpoint
        headers = {"Accept": "application/linkset+json"}
        api_resp = requests.get(api_url, headers=headers)
        api_resp.raise_for_status()

        # Extract the Landing page Link Set Object located as the first (index 0) item.
        landing_page_linkset = api_resp.json()["linkset"][0]

        # Extract the URL of the only organization tar file linked to the record.
        landing_page_organization_tar_items = [
            item
            for item in landing_page_linkset["item"]
            if item["type"] == "application/x-tar"
            and item["href"].endswith("/organization.tar")
        ]
        if len(landing_page_organization_tar_items) != 1:
            raise ReaderError(
                f"Expected 1 organization tar item but got {len(landing_page_organization_tar_items)}"
            )
        file_url = landing_page_organization_tar_items[0]["href"]

        # Download the organization tar file and fully load the response bytes content in memory.
        # The bytes content are then wrapped by a BytesIO to be file-like object (as required by `tarfile.open`).
        # Using directly `file_resp.raw` is not possible since `tarfile.open` requires the file-like object to be seekable.
        file_resp = requests.get(file_url)
        file_resp.raise_for_status()
        yield io.BytesIO(file_resp.content)


class OpenAIREOrganizationTransformer(BaseTransformer):
    """OpenAIRE Organization Transformer."""

    def apply(self, stream_entry, **kwargs):
        """Applies the transformation to the stream entry."""
        record = stream_entry.entry
        organization = {}

        for pid in record["pid"]:
            if pid["scheme"] == "ROR":
                organization["id"] = pid["value"].removeprefix('https://ror.org/')
            elif pid["scheme"] == "PIC":
                organization["identifiers"] = {
                    "scheme": "pic",
                    "identifier": pid["value"]
                }

        organization["openaire_id"] = record["id"]

        stream_entry.entry = organization
        return stream_entry


class OpenAIREAffiliationsServiceWriter(ServiceWriter):
    """OpenAIRE Affiliations service writer."""

    def __init__(self, *args, **kwargs):
        """Constructor."""
        service_or_name = kwargs.pop("service_or_name", "affiliations")
        # Here we only update and we do not insert, since OpenAIRE data is used to augment existing affiliations
        # (with PIC identifiers) and is not used to create new affiliations.
        super().__init__(service_or_name=service_or_name, insert=False, *args, **kwargs)

    def _entry_id(self, entry):
        """Get the id from an entry."""
        return entry["id"]

    def write(self, stream_entry, *args, **kwargs):
        entry = stream_entry.entry

        if not entry["openaire_id"].startswith("openorgs____::"):
            raise WriterError([f"Not valid OpenAIRE OpenOrgs id for : {entry}"])
        del entry["openaire_id"]

        if "id" not in entry:
            raise WriterError([f"No id for : {entry}"])

        if "identifiers" not in entry:
            raise WriterError([f"No alternative identifiers for : {entry}"])

        return super().write(stream_entry, *args, **kwargs)

    def write_many(self, stream_entries, *args, **kwargs):
        return super().write_many(stream_entries, *args, **kwargs)


VOCABULARIES_DATASTREAM_READERS = {
    "openaire-organization-http": OpenAIREOrganizationHTTPReader,
}
"""Affiliations datastream readers."""

VOCABULARIES_DATASTREAM_WRITERS = {
    "affiliations-service": AffiliationsServiceWriter,
    "openaire-affiliations-service": OpenAIREAffiliationsServiceWriter,
}
"""Affiliations datastream writers."""

VOCABULARIES_DATASTREAM_TRANSFORMERS = {
    "ror-affiliations": AffiliationsRORTransformer,
    "openaire-organization": OpenAIREOrganizationTransformer
}
"""Affiliations datastream transformers."""


DATASTREAM_CONFIG = {
    "readers": [
        {
            "type": "zip",
            "args": {
                "regex": "_schema_v2\\.json$",
            },
        },
        {"type": "json"},
    ],
    "transformers": [
        {
            "type": "ror-affiliations",
        },
    ],
    "writers": [
        {
            "type": "async",
            "args": {
                "writer": {
                    "type": "affiliations-service",
                }
            },
        }
    ],
}
"""Data Stream configuration.

An origin is required for the reader.
"""

DATASTREAM_CONFIG_OPENAIRE = {
    "readers": [
        {"type": "openaire-organization-http"},
        {
            "type": "tar",
            "args": {
                "regex": "\\.json.gz$",
                "mode": "r",
            },
        },
        {"type": "gzip"},
        {"type": "jsonl"},
    ],
    "transformers": [
        {
            "type": "openaire-organization",
        },
    ],
    "writers": [
        {
            "type": "async",
            "args": {
                "writer": {
                    "type": "openaire-affiliations-service",
                }
            },
        }
    ],
}
"""Data Stream configuration."""
