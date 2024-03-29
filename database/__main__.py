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

import os

from dotenv import load_dotenv
from .models import migrate

load_dotenv()


if __name__ == "__main__":
    """
    This code creates the necessary tables in the database.
    To apply this migration, run: python3 -m database
    """

    ENVIRONMENT = os.getenv('ENVIRONMENT', 'LOCAL')

    import asyncio
    asyncio.get_event_loop().run_until_complete(migrate(ENVIRONMENT))
