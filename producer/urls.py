"""
Copyright [2009-2019] EMBL-European Bioinformatics Institute
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
     http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
from aiohttp import web
from aiohttp_swagger import setup_swagger

from .views.index import index


def setup_routes(app):
    app.add_routes([web.get('/', index)])

    # setup swagger documentation
    setup_swagger(app, swagger_url="api/doc", title="RNAcentral references", description="")
