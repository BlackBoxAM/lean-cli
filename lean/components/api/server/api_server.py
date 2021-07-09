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

import json
import traceback

import waitress
from flask import Flask, Response, request
from flask.typing import ResponseReturnValue

from lean.components.api.server.account_server import AccountServer
from lean.components.util.logger import Logger


class APIServer:
    """The APIServer class manages the local API server."""

    def __init__(self, logger: Logger, account_server: AccountServer) -> None:
        """Creates a new APIServer instance.

        :param logger: the logger to print debug messages with
        :param account_server: the server serving the account/* endpoints
        """
        self._logger = logger

        self._app = Flask(__name__)
        self._app.before_request(self._before_request)
        self._app.after_request(self._after_request)
        self._app.register_error_handler(Exception, self._error_handler)

        account_server.register_routes(self._app)

    def start(self, port: int) -> None:
        """Starts the local API server.

        This method is blocking and doesn't return until the server is stopped with Ctrl+C.

        :param port: the local port to run on
        """
        self._logger.info(f"The local API server is running on http://localhost:{port}/ (press Ctrl+C to quit)")
        waitress.serve(self._app, host="127.0.0.1", port=port)

    def _before_request(self) -> None:
        body = request.data.decode("utf-8")
        body = f" with body:\n{body}" if body != "" else ""

        self._logger.debug(f"<-- {request.method} {request.url}{body}")

    def _after_request(self, response: Response) -> Response:
        for header in ["Access-Control-Allow-Origin", "Access-Control-Allow-Headers", "Access-Control-Allow-Methods"]:
            response.headers[header] = "*"

        if response.is_json and "success" not in response.json:
            data = response.json
            data["success"] = True
            response.data = json.dumps(data)

        return response

    def _error_handler(self, exception: Exception) -> ResponseReturnValue:
        self._logger.debug(traceback.format_exc().strip())

        return {
            "errors": [str(exception)],
            "success": False
        }
