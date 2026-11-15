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
import pathlib
import re
import uuid
from collections import defaultdict

# Django
from django.db import connection
from django.test import TestCase

# Third Party
import yaml

# wger
from wger.care.prescription import start_prescription
from wger.care.tests.helpers import CareScenarioMixin
from wger.core.tests.base_testcase import BaseTestCase
from wger.manager.models import Routine
from wger.nutrition.models import (
    Ingredient,
    Meal,
    MealItem,
    NutritionPlan,
)


SYNC_RULES = (
    pathlib.Path(__file__).resolve().parents[3] / 'extras' / 'powersync' / 'sync_rules.yaml'
)

TARGET = re.compile(r'SELECT\s+(?:\*\s+FROM\s+(\w+)|(\w+)\.\*)', re.IGNORECASE)


def _id(value):
    """SQLite returns UUID keys as text, Postgres as UUID"""
    if isinstance(value, str):
        return uuid.UUID(value)
    return value


def run_sync_rules(user_id: int, path: pathlib.Path = SYNC_RULES) -> dict[str, set]:
    """
    The ids each query of the sync rules returns for a user, per table

    The queries run on the test database: ``auth.user_id()`` becomes the id,
    the ``with:`` sets become subqueries, and the Postgres-only copy of the
    ingredients is read from the ingredient table it mirrors.
    """
    streams = yaml.safe_load(path.read_text(encoding='utf-8'))['streams']
    rows = defaultdict(set)
    for stream in streams.values():
        sets = stream.get('with', {})
        for query in stream['queries']:
            sql = query.replace('auth.user_id()', f"'{user_id}'")
            for name, body in sets.items():
                body = body.replace('auth.user_id()', f"'{user_id}'")
                sql = re.sub(rf'\bIN\s+{name}\b', f'IN ({body})', sql)
            sql = sql.replace('nutrition_synced_ingredient', 'nutrition_ingredient')
            table = next(group for group in TARGET.search(sql).groups() if group)
            with connection.cursor() as cursor:
                cursor.execute(sql)
                columns = [column[0] for column in cursor.description]
                for row in cursor.fetchall():
                    rows[table].add(_id(dict(zip(columns, row))['id']))
    return rows


class SyncRulesTestCase(CareScenarioMixin, BaseTestCase, TestCase):
    """
    The patient's device receives their own and published prescriptions,
    never the drafts of their professionals
    """

    def setUp(self):
        super().setUp()
        self.build_team()
        self.ingredients = list(Ingredient.objects.all()[:2])

    def routine(self, publish: bool) -> Routine:
        routine = Routine(name='Força', start=datetime.date(2026, 3, 9))
        start_prescription(routine, self.training_rel, self.trainer)
        routine.end = routine.start + datetime.timedelta(days=27)
        routine.save()
        if publish:
            routine.publish()
        return routine

    def plan(self, publish: bool, ingredient: Ingredient) -> tuple:
        plan = NutritionPlan(description='Hipertrofia')
        start_prescription(plan, self.nutrition_rel, self.nutritionist)
        plan.save()
        meal = Meal.objects.create(plan=plan, name='Almoço', order=1)
        item = MealItem.objects.create(meal=meal, ingredient=ingredient, amount=100, order=1)
        if publish:
            plan.publish()
        return plan, meal, item

    def test_drafts_stay_on_the_server(self):
        own = Routine.objects.create(
            user=self.patient,
            name='Meu treino',
            start=datetime.date(2026, 3, 9),
            end=datetime.date(2026, 4, 9),
        )
        published = self.routine(publish=True)
        draft = self.routine(publish=False)
        plan, meal, item = self.plan(publish=True, ingredient=self.ingredients[0])
        draft_plan, draft_meal, draft_item = self.plan(
            publish=False, ingredient=self.ingredients[1]
        )

        rows = run_sync_rules(self.patient.id)

        self.assertEqual(rows['manager_routine'], {own.id, published.id})
        self.assertNotIn(draft.id, rows['manager_routine'])
        self.assertIn(plan.id, rows['nutrition_nutritionplan'])
        self.assertNotIn(draft_plan.id, rows['nutrition_nutritionplan'])
        self.assertIn(meal.id, rows['nutrition_meal'])
        self.assertNotIn(draft_meal.id, rows['nutrition_meal'])
        self.assertIn(item.id, rows['nutrition_mealitem'])
        self.assertNotIn(draft_item.id, rows['nutrition_mealitem'])
        # Foods only a draft uses stay unknown too
        self.assertIn(self.ingredients[0].id, rows['nutrition_ingredient'])
        self.assertNotIn(self.ingredients[1].id, rows['nutrition_ingredient'])

    def test_published_versions_stay_after_a_new_draft(self):
        """The superseded version keeps syncing, the new draft does not"""
        published = self.routine(publish=True)
        draft = published.new_version()
        rows = run_sync_rules(self.patient.id)
        self.assertIn(published.id, rows['manager_routine'])
        self.assertNotIn(draft.id, rows['manager_routine'])

    def test_other_users_get_nothing(self):
        self.routine(publish=True)
        self.plan(publish=True, ingredient=self.ingredients[0])
        rows = run_sync_rules(self.trainer.id)
        self.assertEqual(rows['manager_routine'], set())
        self.assertEqual(rows['nutrition_nutritionplan'], set())
