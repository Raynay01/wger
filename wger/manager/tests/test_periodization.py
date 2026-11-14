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
from django.urls import reverse

# Third Party
from rest_framework import status
from rest_framework.test import APITestCase

# wger
from wger.care.export import export_user_data
from wger.care.prescription import start_prescription
from wger.care.tests.helpers import CareScenarioMixin
from wger.core.tests.base_testcase import BaseTestCase
from wger.exercises.models import (
    Exercise,
    Muscle,
)
from wger.manager.models import (
    Day,
    RepetitionsConfig,
    Routine,
    SetsConfig,
    Slot,
    SlotEntry,
    TrainingPlan,
    WeightConfig,
    WorkoutLog,
)


class PeriodizationTestCase(CareScenarioMixin, BaseTestCase, APITestCase):
    """
    Training plans (macrocycles) with consecutive blocks (mesocycles)
    """

    start = datetime.date(2026, 3, 2)

    def setUp(self):
        super().setUp()
        self.build_team()
        self.routine = Routine(name='Hipertrofia A/B', start=self.start)
        start_prescription(self.routine, self.training_rel, self.trainer)
        self.routine.end = self.start + datetime.timedelta(days=60)
        self.routine.save()
        self.routine.publish()

    def create_plan(self) -> dict:
        self.client.force_authenticate(self.trainer)
        response = self.client.post(
            reverse('training-plan-list'),
            {
                'name': 'Temporada 2026',
                'goal': 'hypertrophy',
                'start': self.start.isoformat(),
                'care_relationship': str(self.training_rel.pk),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return response.data

    def add_block(self, plan_id, **data) -> dict:
        self.client.force_authenticate(self.trainer)
        response = self.client.post(reverse('training-block-list'), {'plan': plan_id, **data})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return response.data

    def publish(self, plan_id):
        self.client.force_authenticate(self.trainer)
        response = self.client.post(reverse('training-plan-publish', kwargs={'pk': plan_id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data

    def patient_plans(self):
        self.client.force_authenticate(self.patient)
        return self.client.get(reverse('training-plan-list')).data['results']

    def test_blocks_follow_each_other(self):
        """Each block starts the day after the previous one ends"""
        plan = self.create_plan()
        self.add_block(plan['id'], order=1, focus='hypertrophy', weeks=4, routine=self.routine.pk)
        self.add_block(plan['id'], order=2, focus='deload', weeks=1, intensity='RIR 4')
        self.add_block(plan['id'], order=3, focus='strength', weeks=3)

        self.assertEqual(self.patient_plans(), [])
        published = self.publish(plan['id'])

        blocks = published['blocks']
        self.assertEqual(
            [(b['focus'], b['start'], b['end']) for b in blocks],
            [
                ('hypertrophy', datetime.date(2026, 3, 2), datetime.date(2026, 3, 29)),
                ('deload', datetime.date(2026, 3, 30), datetime.date(2026, 4, 5)),
                ('strength', datetime.date(2026, 4, 6), datetime.date(2026, 4, 26)),
            ],
        )
        self.assertEqual(published['end'], '2026-04-26')
        self.assertEqual(blocks[0]['current_routine_name'], 'Hipertrofia A/B')
        self.assertEqual([p['id'] for p in self.patient_plans()], [plan['id']])

    def test_routine_of_another_person(self):
        """A block only links routines of the plan's patient"""
        other = Routine.objects.create(
            user=self.trainer,
            name='Minha',
            start=self.start,
            end=self.start + datetime.timedelta(days=30),
        )
        plan = self.create_plan()
        response = self.client.post(
            reverse('training-block-list'),
            {'plan': plan['id'], 'focus': 'strength', 'weeks': 2, 'routine': other.pk},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('routine', response.data)

    def test_only_the_author_writes(self):
        """Other professionals cannot add blocks; published blocks are frozen"""
        plan = self.create_plan()
        block = self.add_block(plan['id'], focus='adaptation', weeks=2)

        self.client.force_authenticate(self.physio)
        response = self.client.post(
            reverse('training-block-list'),
            {'plan': plan['id'], 'focus': 'power', 'weeks': 1},
        )
        self.assertIn(response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

        self.publish(plan['id'])
        self.client.force_authenticate(self.trainer)
        response = self.client.patch(
            reverse('training-block-detail', kwargs={'pk': block['id']}),
            {'weeks': 6},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_new_version(self):
        """A new version copies the blocks, the published one keeps its own"""
        plan = self.create_plan()
        self.add_block(plan['id'], focus='hypertrophy', weeks=4, routine=self.routine.pk)
        self.publish(plan['id'])

        response = self.client.post(reverse('training-plan-new-version', kwargs={'pk': plan['id']}))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        draft = response.data
        self.assertEqual(draft['version'], 2)
        self.assertEqual([b['weeks'] for b in draft['blocks']], [4])

        response = self.client.patch(
            reverse('training-block-detail', kwargs={'pk': draft['blocks'][0]['id']}),
            {'weeks': 6},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        first = TrainingPlan.objects.get(pk=plan['id'])
        self.assertEqual([b.weeks for b in first.blocks.all()], [4])

    def test_current_routine(self):
        """A block shows the published version of its routine's lineage"""
        plan = self.create_plan()
        self.add_block(plan['id'], focus='hypertrophy', weeks=4, routine=self.routine.pk)
        second = self.routine.new_version()
        second.name = 'Hipertrofia A/B v2'
        second.save()
        second.publish()

        self.client.force_authenticate(self.trainer)
        response = self.client.get(reverse('training-plan-detail', kwargs={'pk': plan['id']}))
        block = response.data['blocks'][0]
        self.assertEqual(block['routine'], self.routine.pk)
        self.assertEqual(block['current_routine'], second.pk)
        self.assertEqual(block['current_routine_name'], 'Hipertrofia A/B v2')

    def test_calendar_phase(self):
        """The calendar shows the block and its week, also on the boundary days"""
        plan = self.create_plan()
        self.add_block(plan['id'], name='Base', focus='hypertrophy', weeks=4)
        self.add_block(plan['id'], order=2, focus='deload', weeks=1)
        self.publish(plan['id'])

        self.client.force_authenticate(self.patient)
        response = self.client.get(
            reverse('care-calendar'),
            {'start': '2026-03-01', 'end': '2026-04-06'},
        )
        phases = {d['date'].isoformat(): d['phase'] for d in response.data['days']}
        self.assertIsNone(phases['2026-03-01'])
        self.assertEqual(
            phases['2026-03-02'],
            {
                'plan': 'Temporada 2026',
                'block': 'Base',
                'focus': 'hypertrophy',
                'week': 1,
                'weeks': 4,
            },
        )
        self.assertEqual(phases['2026-03-29']['week'], 4)
        self.assertEqual(phases['2026-03-30']['focus'], 'deload')
        self.assertEqual(phases['2026-04-05']['focus'], 'deload')
        self.assertIsNone(phases['2026-04-06'])

    def test_export(self):
        """The patient's export contains the plan and its blocks"""
        plan = self.create_plan()
        self.add_block(plan['id'], focus='strength', weeks=3)
        self.publish(plan['id'])

        exported = export_user_data(self.patient)['manager']
        self.assertEqual([p['name'] for p in exported['TrainingPlan']], ['Temporada 2026'])
        self.assertEqual([b['weeks'] for b in exported['TrainingBlock']], [3])

    def test_planned_versus_done(self):
        """Per week: sessions, sets and load of the routine against the patient's logs"""
        day = Day.objects.create(routine=self.routine, order=1, name='A')
        Day.objects.create(routine=self.routine, order=2, name='Descanso', is_rest=True)
        squat, plank = Exercise.objects.all()[:2]
        entry = SlotEntry.objects.create(
            slot=Slot.objects.create(day=day, order=1),
            exercise=squat,
            order=1,
        )
        SetsConfig.objects.create(slot_entry=entry, iteration=1, value=3)
        RepetitionsConfig.objects.create(slot_entry=entry, iteration=1, value=10)
        WeightConfig.objects.create(slot_entry=entry, iteration=1, value=50)

        plan = self.create_plan()
        self.add_block(plan['id'], order=1, focus='hypertrophy', weeks=1, routine=self.routine.pk)
        self.add_block(plan['id'], order=2, focus='deload', weeks=1)
        self.publish(plan['id'])

        profile = self.patient.userprofile
        profile.time_zone = 'America/Sao_Paulo'
        profile.save()

        def log(when, exercise=squat, **data):
            WorkoutLog.objects.create(
                user=self.patient,
                exercise=exercise,
                date=datetime.datetime.fromisoformat(when),
                **data,
            )

        # 23:30 in Sao Paulo on the first day of the block, already the next day in UTC
        for _ in range(3):
            log('2026-03-03T02:30:00+00:00', repetitions=10, weight=50, rir=2)
        log('2026-03-04T12:00:00+00:00', repetitions=10, weight=100, weight_unit_id=2)
        log('2026-03-04T12:10:00+00:00', exercise=plank, repetitions=60, repetitions_unit_id=3)
        log('2026-03-09T12:00:00+00:00', repetitions=5, weight=40)
        log('2026-03-02T02:00:00+00:00', repetitions=5, weight=40)

        self.client.force_authenticate(self.patient)
        response = self.client.get(reverse('training-plan-progress', kwargs={'pk': plan['id']}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        first, second = response.data['blocks']

        # Training every other day: 2, 4, 6 and 8 March, 3 x 10 x 50 kg each
        self.assertEqual(first['planned_sessions'], 4)
        self.assertEqual(first['planned_sets'], 12)
        self.assertEqual(first['planned_load'], 6000)
        # 3 x 10 x 50 kg plus 10 x 100 lb; the plank counts as a set without load
        self.assertEqual(first['done_sessions'], 2)
        self.assertEqual(first['done_sets'], 5)
        self.assertEqual(first['done_load'], 1954)
        self.assertEqual(first['average_rir'], '2.0')
        self.assertEqual(first['weeks'][0]['week'], 1)
        self.assertEqual(first['weeks'][0]['done_sets'], 5)

        self.assertEqual(second['start'], '2026-03-09')
        self.assertEqual(second['planned_sessions'], 0)
        self.assertEqual(second['done_sessions'], 1)
        self.assertEqual(second['done_load'], 200)

        self.client.force_authenticate(self.physio)
        response = self.client.get(reverse('training-plan-progress', kwargs={'pk': plan['id']}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_sets_per_muscle(self):
        """Weekly targets per muscle against the sets of the routine and of the logs"""
        chest, back, legs = Muscle.objects.all()[:3]
        squat, plank = Exercise.objects.all()[:2]
        squat.muscles.set([chest, back])
        plank.muscles.set([back])
        squat.muscles_secondary.set([legs])
        day = Day.objects.create(routine=self.routine, order=1, name='A')
        Day.objects.create(routine=self.routine, order=2, name='Descanso', is_rest=True)
        entry = SlotEntry.objects.create(
            slot=Slot.objects.create(day=day, order=1),
            exercise=squat,
            order=1,
        )
        SetsConfig.objects.create(slot_entry=entry, iteration=1, value=3)

        plan = self.create_plan()
        url = reverse('training-block-list')
        targets = [
            {'muscle': chest.pk, 'sets': 10},
            {'muscle': back.pk, 'sets': 8},
            {'muscle': legs.pk, 'sets': 6},
        ]
        data = {'plan': plan['id'], 'focus': 'hypertrophy', 'weeks': 2, 'routine': self.routine.pk}
        response = self.client.post(url, {**data, 'weekly_sets': targets}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['weekly_sets'], targets)
        self.publish(plan['id'])

        for when, exercise in [
            ('2026-03-02T12:00:00+00:00', squat),
            ('2026-03-02T12:05:00+00:00', squat),
            ('2026-03-04T12:00:00+00:00', plank),
            ('2026-03-09T12:00:00+00:00', squat),
        ]:
            WorkoutLog.objects.create(
                user=self.patient,
                exercise=exercise,
                date=datetime.datetime.fromisoformat(when),
                repetitions=10,
            )

        self.client.force_authenticate(self.patient)
        response = self.client.get(reverse('training-plan-progress', kwargs={'pk': plan['id']}))
        (block,) = response.data['blocks']
        # Sessions on 2, 4, 6, 8, 10, 12 and 14 March, 3 sets of squats each
        self.assertEqual(
            block['muscles'],
            [
                {
                    'muscle': chest.pk,
                    'planned_sets': 21,
                    'done_sets': 3,
                    'name': chest.name,
                    'weekly_sets': 10,
                },
                {
                    'muscle': back.pk,
                    'planned_sets': 21,
                    'done_sets': 4,
                    'name': back.name,
                    'weekly_sets': 8,
                },
                {
                    'muscle': legs.pk,
                    'planned_sets': 0,
                    'done_sets': 0,
                    'name': legs.name,
                    'weekly_sets': 6,
                },
            ],
        )
        first, second = block['weeks']
        self.assertEqual(
            [(m['planned_sets'], m['done_sets']) for m in first['muscles']],
            [(12, 2), (12, 3), (0, 0)],
        )
        self.assertEqual(
            [(m['planned_sets'], m['done_sets']) for m in second['muscles']],
            [(9, 1), (9, 1), (0, 0)],
        )

    def test_sets_per_muscle_validation(self):
        """A target needs a known muscle, once per block, and 1 to 60 sets"""
        plan = self.create_plan()
        muscle = Muscle.objects.first()
        data = {'plan': plan['id'], 'focus': 'strength', 'weeks': 3}
        for weekly_sets in [
            [{'muscle': muscle.pk, 'sets': 10}, {'muscle': muscle.pk, 'sets': 4}],
            [{'muscle': Muscle.objects.order_by('-pk').first().pk + 1, 'sets': 10}],
            [{'muscle': muscle.pk, 'sets': 0}],
            [{'muscle': muscle.pk, 'sets': 61}],
        ]:
            response = self.client.post(
                reverse('training-block-list'),
                {**data, 'weekly_sets': weekly_sets},
                format='json',
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, weekly_sets)
            self.assertIn('weekly_sets', response.data)
