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
import datetime

# Django
from django.contrib.auth.models import User
from django.urls import (
    NoReverseMatch,
    reverse,
)

# Third Party
from rest_framework import status
from rest_framework.test import APITestCase

# wger
from wger.care.prescription import start_prescription
from wger.care.tests.helpers import CareScenarioMixin
from wger.core.tests.base_testcase import BaseTestCase
from wger.manager.models import Routine
from wger.measurements.models import Category
from wger.physio.models import (
    PainRecord,
    PhysioProtocol,
)
from wger.urls import router


# Catalogs every user reads: exercises, foods, units, languages, licenses, trophies
PUBLIC = {
    'language',
    'license',
    'setting-repetition-unit',
    'setting-weight-unit',
    'exercise',
    'exerciseinfo',
    'exercise-translation',
    'exercisealias',
    'exercisecategory',
    'exercisecomment',
    'exerciseimage',
    'video',
    'equipment',
    'muscle',
    'deletion-log',
    'api-ingredient',
    'api-ingredientinfo',
    'api-ingredient-sync',
    'ingredientimage',
    'ingredientweightunit',
    'trophy',
}


class IsolationTestCase(CareScenarioMixin, BaseTestCase, APITestCase):
    """
    A user without any follow-up gets nothing but the public catalogs from
    every list of the API, while others have data everywhere
    """

    def setUp(self):
        super().setUp()
        self.build_team()
        routine = Routine(name='Força', start=datetime.date(2026, 3, 9))
        start_prescription(routine, self.training_rel, self.trainer)
        routine.end = routine.start + datetime.timedelta(days=27)
        routine.save()
        routine.publish()
        protocol = PhysioProtocol(name='Joelho')
        start_prescription(protocol, self.physio_rel, self.physio)
        protocol.save()
        protocol.publish()
        PainRecord.objects.create(
            user=self.patient,
            protocol=protocol,
            moment='after',
            value=4,
            datetime=routine.start,
        )
        self.stranger = User.objects.create_user('estranho', 'estranho@example.com', 'x')

    def list_urls(self):
        for _prefix, _viewset, basename in router.registry:
            try:
                yield basename, reverse(f'{basename}-list')
            except NoReverseMatch:
                continue

    def test_stranger_sees_only_public_catalogs(self):
        self.client.force_authenticate(self.stranger)
        checked = 0
        for basename, url in self.list_urls():
            response = self.client.get(url, {'limit': 1})
            if response.status_code != status.HTTP_200_OK:
                continue
            data = response.data
            count = (
                data.get('count', len(data.get('results', [])))
                if isinstance(data, dict)
                else len(data)
            )
            checked += 1
            if basename in PUBLIC:
                continue
            self.assertEqual(
                count,
                self.allowed(basename),
                f'{url} shows data of other users to a stranger',
            )
        self.assertGreater(checked, 50)

    def allowed(self, basename: str) -> int:
        """What a stranger may see in a non-public list: own rows and public templates"""
        if basename == 'measurement-category':
            return Category.objects.filter(user=self.stranger).count()
        if basename in ('routine', 'public-templates'):
            return Routine.objects.filter(is_template=True, is_public=True).count()
        return 0

    def test_the_scenario_has_data(self):
        """The patient sees their own data, so an empty list above means isolation"""
        self.client.force_authenticate(self.patient)
        for name in ('routine-list', 'pain-record-list', 'care-relationship-list'):
            response = self.client.get(reverse(name))
            self.assertGreater(response.data['count'], 0, name)
