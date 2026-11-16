# This file is part of wger Workout Manager.
#
# wger Workout Manager is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# wger Workout Manager is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Workout Manager.  If not, see <http://www.gnu.org/licenses/>.

# Standard Library
import pathlib
import re

# Django
from django.test import SimpleTestCase


ROOT = pathlib.Path(__file__).resolve().parents[2]

SCRIPT_TAG = re.compile(r'<script\b([^>]*)>', re.IGNORECASE)
EVENT_HANDLER = re.compile(r'<[a-z][^>]*\son[a-z]+\s*=', re.IGNORECASE | re.DOTALL)
JAVASCRIPT_URL = re.compile(r'(href|src|action)\s*=\s*["\']\s*javascript:', re.IGNORECASE)

# Data blocks, the browser does not run them
DATA_TYPES = ('application/json', 'application/ld+json', 'text/template')


def templates():
    for path in sorted(ROOT.glob('*/templates/**/*')):
        if path.suffix in ('.html', '.tpl', '.js') and path.is_file():
            yield path, path.read_text()


class TemplateScriptPolicyTestCase(SimpleTestCase):
    """
    The templates run no script the content security policy blocks: every
    inline script carries the request's nonce, and there are no inline event
    handlers or javascript: links
    """

    def test_inline_scripts_carry_the_nonce(self):
        missing = []
        for path, text in templates():
            for match in SCRIPT_TAG.finditer(text):
                attributes = match.group(1)
                if 'src=' in attributes or any(t in attributes for t in DATA_TYPES):
                    continue
                if 'nonce="{{ csp_nonce }}"' not in attributes:
                    line = text.count('\n', 0, match.start()) + 1
                    missing.append(f'{path.relative_to(ROOT)}:{line}')
        self.assertEqual(missing, [])

    def test_no_inline_event_handlers(self):
        found = [
            str(path.relative_to(ROOT))
            for path, text in templates()
            if EVENT_HANDLER.search(text) or JAVASCRIPT_URL.search(text)
        ]
        self.assertEqual(found, [])
