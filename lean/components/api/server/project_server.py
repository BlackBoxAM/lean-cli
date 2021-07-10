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

import shutil
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, g
from flask.typing import ResponseReturnValue

from lean.components.config.lean_config_manager import LeanConfigManager
from lean.components.config.project_config_manager import ProjectConfigManager
from lean.components.util.project_manager import ProjectManager
from lean.constants import PROJECT_CONFIG_FILE_NAME, FAKE_ORGANIZATION
from lean.models.api import QCProject, QCLanguage, QCLiveResults, QCCollaborator, QCParameter, QCCreatedProject


class ProjectServer:
    """The ProjectServer class contains the logic to serve the projects/* API endpoints."""

    def __init__(self,
                 project_manager: ProjectManager,
                 project_config_manager: ProjectConfigManager,
                 lean_config_manager: LeanConfigManager) -> None:
        """Creates a new ProjectServer instance.

        :param project_manager: the ProjectManager to use
        :param project_config_manager: the ProjectConfigManager to get project configuration from
        :param lean_config_manager: the LeanConfigManager to get the CLI root directory from
        """
        self._project_manager = project_manager
        self._project_config_manager = project_config_manager
        self._lean_config_manager = lean_config_manager

    def register_routes(self, app: Flask) -> None:
        """Registers the routes this class serves on a Flask instance.

        :param app: the Flask instance to register the routes on
        """
        app.add_url_rule("/projects/read", view_func=self._projects_read, methods=["GET", "POST"])
        app.add_url_rule("/projects/update", view_func=self._projects_update, methods=["GET", "POST"])
        app.add_url_rule("/projects/create", view_func=self._projects_create, methods=["GET", "POST"])
        app.add_url_rule("/projects/delete", view_func=self._projects_delete, methods=["GET", "POST"])

    def _projects_read(self) -> ResponseReturnValue:
        project_id = g.input.get("projectId", None)
        if project_id is not None:
            projects = [self._create_project(self._project_manager.find_project_by_id(int(project_id)))]
        else:
            cli_root = self._lean_config_manager.get_cli_root_directory()
            projects = [self._create_project(p.parent) for p in cli_root.rglob(PROJECT_CONFIG_FILE_NAME)]

        return {"projects": [p.dict(exclude_none=True) for p in projects]}

    def _projects_update(self) -> ResponseReturnValue:
        project_id = int(g.input["projectId"])

        project_dir = self._project_manager.find_project_by_id(project_id)
        project_config = self._project_config_manager.get_project_config(project_dir)

        if "description" in g.input:
            project_config.set("description", g.input["description"])

        if "parameters" in g.input:
            project_config.set("parameters", {})
        elif "parameters[0][key]" in g.input:
            parameters = {}

            index = 0
            while f"parameters[{index}][key]" in g.input:
                parameters[g.input[f"parameters[{index}][key]"]] = g.input[f"parameters[{index}][value]"]
                index += 1

            project_config.set("parameters", parameters)

        if "name" in g.input:
            new_dir = self._lean_config_manager.get_cli_root_directory() / g.input["name"].lstrip("/")
            if new_dir.is_dir():
                raise RuntimeError(f"There already exists a project named '{g.input['name']}'")
            shutil.move(project_dir, new_dir)

        return {}

    def _projects_create(self) -> ResponseReturnValue:
        name = g.input["name"].lstrip("/")
        language = "python" if g.input["language"] == "Py" else "csharp"

        from lean.commands.create_project import create_project
        create_project.callback(name, language)

        project_dir = self._lean_config_manager.get_cli_root_directory() / name
        now = datetime.now()

        created_project = QCCreatedProject(projectId=self._project_config_manager.get_local_id(project_dir),
                                           name=name,
                                           modified=now,
                                           created=now)

        return {"projects": [created_project.dict(exclude_none=True)]}

    def _projects_delete(self) -> ResponseReturnValue:
        project_id = int(g.input["projectId"])

        project_dir = self._project_manager.find_project_by_id(project_id)
        shutil.rmtree(project_dir)

        return {}

    def _create_project(self, project_dir: Path) -> QCProject:
        project_id = self._project_config_manager.get_local_id(project_dir)
        project_config = self._project_config_manager.get_project_config(project_dir)

        relative_dir = project_dir.relative_to(self._lean_config_manager.get_cli_root_directory())
        project_language = project_config.get("language", "Python")

        stats = [f.stat() for f in self._project_manager.get_files_to_sync(project_dir)]
        if len(stats) == 0:
            stats = [project_dir.stat()]

        modified_time = datetime.fromtimestamp(max(s.st_mtime_ns for s in stats) / 1e9).astimezone(tz=timezone.utc)
        created_time = datetime.fromtimestamp(min(s.st_ctime_ns for s in stats) / 1e9).astimezone(tz=timezone.utc)

        project_parameters = [QCParameter(key=k, value=v) for k, v in project_config.get("parameters", {}).items()]

        return QCProject(projectId=project_id,
                         organizationId=FAKE_ORGANIZATION.id,
                         name=relative_dir.as_posix(),
                         description=project_config.get("description", ""),
                         modified=modified_time,
                         created=created_time,
                         language=next(v for k, v in QCLanguage.__members__.items() if k == project_language),
                         collaborators=[QCCollaborator(id=0,
                                                       uid=FAKE_ORGANIZATION.members[0].id,
                                                       blivecontrol=True,
                                                       epermission="write",
                                                       profileimage="https://cdn.quantconnect.com/i/tu/qc-logo.svg",
                                                       name=FAKE_ORGANIZATION.members[0].name,
                                                       owner=True)],
                         leanVersionId=-1,
                         leanPinnedToMaster=True,
                         parameters=project_parameters,
                         liveResults=QCLiveResults(eStatus="Undefined"),
                         libraries=[])
