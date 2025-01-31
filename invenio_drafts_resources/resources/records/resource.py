# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 CERN.
# Copyright (C) 2020 Northwestern University.
#
# Invenio-Drafts-Resources is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Invenio Drafts Resources module to create REST APIs."""

import marshmallow as ma
from flask import g
from flask_resources import resource_requestctx, response_handler, route
from flask_resources.parsers.decorators import request_parser
from invenio_records_resources.resources import \
    RecordResource as RecordResourceBase
from invenio_records_resources.resources.records.resource import \
    request_data, request_headers, request_search_args, request_view_args
from invenio_records_resources.resources.records.utils import es_preference

from .errors import RedirectException


class RecordResource(RecordResourceBase):
    """Draft-aware RecordResource."""

    def create_blueprint(self, **options):
        """Create the blueprint."""
        # We avoid passing url_prefix to the blueprint because we need to
        # install URLs under both /records and /user/records. Instead we
        # add the prefix manually to each route (which is anyway what Flask
        # does in the end)
        options["url_prefix"] = ""
        return super().create_blueprint(**options)

    def create_url_rules(self):
        """Create the URL rules for the record resource."""
        routes = self.config.routes

        def p(route):
            """Prefix a route with the URL prefix."""
            return f"{self.config.url_prefix}{route}"

        def s(route):
            """Suffix a route with the URL prefix."""
            return f"{route}{self.config.url_prefix}"

        return [
            route("GET", p(routes["list"]), self.search),
            route("POST", p(routes["list"]), self.create),
            route("GET", p(routes["item"]), self.read),
            route("PUT", p(routes["item"]), self.update),
            route("DELETE", p(routes["item"]), self.delete),
            route("GET", p(routes["item-versions"]), self.search_versions),
            route("POST", p(routes["item-versions"]), self.new_version),
            route("GET", p(routes["item-latest"]), self.read_latest),
            route("GET", p(routes["item-draft"]), self.read_draft),
            route("POST", p(routes["item-draft"]), self.edit),
            route("PUT", p(routes["item-draft"]), self.update_draft),
            route("DELETE", p(routes["item-draft"]), self.delete_draft),
            route("POST", p(routes["item-publish"]), self.publish),
            route("GET", s(routes["user-prefix"]), self.search_user_records),
        ]

    @request_search_args
    @request_view_args
    @response_handler(many=True)
    def search_user_records(self):
        """Perform a search over the record's versions.

        GET /user/records
        """
        hits = self.service.search_drafts(
            identity=g.identity,
            params=resource_requestctx.args,
            es_preference=es_preference()
        )
        return hits.to_dict(), 200

    @request_search_args
    @request_view_args
    @response_handler(many=True)
    def search_versions(self):
        """Perform a search over the record's versions.

        GET /records/:pid_value/versions
        """
        hits = self.service.search_versions(
            resource_requestctx.view_args["pid_value"],
            identity=g.identity,
            params=resource_requestctx.args,
            es_preference=es_preference()
        )
        return hits.to_dict(), 200

    @request_view_args
    @response_handler()
    def new_version(self):
        """Create a new version.

        POST /records/:pid_value/versions
        """
        item = self.service.new_version(
            resource_requestctx.view_args["pid_value"],
            g.identity,
        )
        return item.to_dict(), 201

    @request_view_args
    @response_handler()
    def edit(self):
        """Edit a record.

        POST /records/:pid_value/draft
        """
        item = self.service.edit(
            resource_requestctx.view_args["pid_value"],
            g.identity,
        )
        return item.to_dict(), 201

    @request_view_args
    @response_handler()
    def publish(self):
        """Publish the draft."""
        item = self.service.publish(
            resource_requestctx.view_args["pid_value"],
            g.identity,
        )
        return item.to_dict(), 202

    @request_view_args
    def read_latest(self):
        """Redirect to latest record.

        GET /records/:pid_value/versions/latest
        """
        item = self.service.read_latest(
            resource_requestctx.view_args["pid_value"],
            g.identity,
        )
        raise RedirectException(item["links"]["self"])

    @request_view_args
    @response_handler()
    def read_draft(self):
        """Edit a draft.

        GET /records/:pid_value/draft
        """
        item = self.service.read_draft(
            resource_requestctx.view_args["pid_value"],
            g.identity,
        )
        return item.to_dict(), 200

    @request_headers
    @request_view_args
    @request_data
    @response_handler()
    def update_draft(self):
        """Update a draft.

        PUT /records/:pid_value/draft
        """
        item = self.service.update_draft(
            resource_requestctx.view_args["pid_value"],
            g.identity,
            resource_requestctx.data or {},
            revision_id=resource_requestctx.headers.get("if_match"),
        )
        return item.to_dict(), 200

    @request_headers
    @request_view_args
    def delete_draft(self):
        """Delete a draft.

        DELETE /records/:pid_value/draft
        """
        self.service.delete_draft(
            resource_requestctx.view_args["pid_value"],
            g.identity,
            revision_id=resource_requestctx.headers.get("if_match"),
        )
        return "", 204
