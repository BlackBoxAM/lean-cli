# QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
# Lean CLI v1.0. Copyright 2021 QuantConnect Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from flask import Flask, request
from flask.typing import ResponseReturnValue

from lean.models.api import QCAccount


class AccountServer:
    """The AccountServer class contains the logic to serve the account/* API endpoints."""

    def register_routes(self, app: Flask) -> None:
        """Registers the routes this class serves on a Flask instance.

        :param app: the Flask instance to register the routes on
        """
        app.add_url_rule("/account/read", view_func=self._read, methods=["POST"])

    def _read(self) -> ResponseReturnValue:
        organization_id = request.json.get("organizationId", None)
        if organization_id is None:
            organization_id = "fake-organization-id"

        return QCAccount(organizationId=organization_id, creditBalance=1000).dict(exclude_none=True)
