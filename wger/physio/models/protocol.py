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
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# wger
from wger.care.disciplines import Discipline
from wger.care.prescription import PrescriptionMixin
from wger.exercises.models import Exercise
from wger.utils.uuid import uuid7


class PainMoment(models.TextChoices):
    BEFORE = 'before', _('Before the exercises')
    DURING = 'during', _('During the exercises')
    AFTER = 'after', _('After the exercises')
    NEXT_DAY = 'next_day', _('On the next day')
    OTHER = 'other', _('Other')


class ExerciseLocation(models.TextChoices):
    HOME = 'home', _('Home')
    GYM = 'gym', _('Gym')
    CLINIC = 'clinic', _('Clinic')


class PhysioProtocol(PrescriptionMixin, models.Model):
    """
    A therapeutic exercise protocol, prescribed by a physiotherapist
    """

    class Meta:
        ordering = ['-start']

    discipline = Discipline.PHYSIO

    id = models.UUIDField(default=uuid7, primary_key=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE, editable=False)

    name = models.CharField(verbose_name=_('Name'), max_length=100)

    description = models.TextField(verbose_name=_('Description'), blank=True)

    start = models.DateField(default=datetime.date.today)

    end = models.DateField(null=True, blank=True)

    pain_before = models.BooleanField(default=True)

    pain_during = models.BooleanField(default=False)

    pain_after = models.BooleanField(default=True)

    pain_next_day = models.BooleanField(default=False)

    pain_alert_threshold = models.PositiveSmallIntegerField(
        default=7,
        validators=[MaxValueValidator(10)],
        help_text='Pain from this value on alerts the physiotherapist',
    )

    pain_alert_increase = models.PositiveSmallIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text='An increase from before to after the exercises by this much alerts',
    )

    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def get_owner_object(self):
        return self

    @property
    def pain_moments(self) -> list[str]:
        flags = {
            PainMoment.BEFORE: self.pain_before,
            PainMoment.DURING: self.pain_during,
            PainMoment.AFTER: self.pain_after,
            PainMoment.NEXT_DAY: self.pain_next_day,
        }
        return [moment.value for moment, enabled in flags.items() if enabled]

    def build_snapshot(self) -> dict:
        return {
            'name': self.name,
            'description': self.description,
            'start': self.start,
            'end': self.end,
            'pain_moments': self.pain_moments,
            'pain_alert_threshold': self.pain_alert_threshold,
            'pain_alert_increase': self.pain_alert_increase,
            'exercises': [
                {
                    'exercise': e.exercise_id,
                    'name': e.name,
                    'sets': e.sets,
                    'repetitions': e.repetitions,
                    'duration_seconds': e.duration_seconds,
                    'load': e.load,
                    'frequency_per_week': e.frequency_per_week,
                    'location': e.location,
                    'instructions': e.instructions,
                    'video_url': e.video_url,
                    'order': e.order,
                }
                for e in self.exercises.all()
            ],
        }

    def copy_content_to(self, target) -> None:
        for entry in self.exercises.all():
            entry.pk = None
            entry._state.adding = True
            entry.protocol = target
            entry.save()


class ProtocolExercise(models.Model):
    """
    An exercise of a protocol with its dosage
    """

    class Meta:
        ordering = ['order']

    id = models.UUIDField(default=uuid7, primary_key=True)

    protocol = models.ForeignKey(
        PhysioProtocol,
        on_delete=models.CASCADE,
        related_name='exercises',
    )

    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text='Exercise of the library, if any',
    )

    name = models.CharField(max_length=100)

    sets = models.PositiveSmallIntegerField(null=True, blank=True)

    repetitions = models.PositiveSmallIntegerField(null=True, blank=True)

    duration_seconds = models.PositiveIntegerField(null=True, blank=True)

    load = models.CharField(max_length=50, blank=True, help_text='e.g. red elastic band')

    frequency_per_week = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MaxValueValidator(21)],
    )

    location = models.CharField(
        max_length=10,
        choices=ExerciseLocation.choices,
        default=ExerciseLocation.HOME,
    )

    instructions = models.TextField(blank=True)

    video_url = models.URLField(blank=True)

    order = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.name

    def get_owner_object(self):
        return self.protocol


class PainRecord(models.Model):
    """
    Pain on the numeric rating scale, 0 (no pain) to 10 (worst imaginable)
    """

    class Meta:
        ordering = ['-datetime']

    id = models.UUIDField(default=uuid7, primary_key=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE, editable=False)

    protocol = models.ForeignKey(
        PhysioProtocol,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pain_records',
    )

    protocol_exercise = models.ForeignKey(
        ProtocolExercise,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pain_records',
    )

    datetime = models.DateTimeField(default=timezone.now)

    moment = models.CharField(max_length=10, choices=PainMoment.choices)

    value = models.PositiveSmallIntegerField(validators=[MaxValueValidator(10)])

    body_region = models.CharField(max_length=50, blank=True)

    notes = models.CharField(max_length=500, blank=True)

    def __str__(self):
        return f'{self.value}/10 {self.moment}'

    def get_owner_object(self):
        return self


class ExerciseRecord(models.Model):
    """
    A protocol exercise the patient did
    """

    class Meta:
        ordering = ['-datetime']

    id = models.UUIDField(default=uuid7, primary_key=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE, editable=False)

    protocol_exercise = models.ForeignKey(
        ProtocolExercise,
        on_delete=models.CASCADE,
        related_name='records',
    )

    datetime = models.DateTimeField(default=timezone.now)

    sets = models.PositiveSmallIntegerField(null=True, blank=True)

    repetitions = models.PositiveSmallIntegerField(null=True, blank=True)

    duration_seconds = models.PositiveIntegerField(null=True, blank=True)

    notes = models.CharField(max_length=500, blank=True)

    def __str__(self):
        return f'{self.protocol_exercise_id} at {self.datetime}'

    def get_owner_object(self):
        return self


class AssessmentKind(models.TextChoices):
    RANGE_OF_MOTION = 'rom', _('Range of motion')
    STRENGTH = 'strength', _('Strength')
    FUNCTIONAL_TEST = 'functional_test', _('Functional test')
    QUESTIONNAIRE = 'questionnaire', _('Questionnaire')
    BALANCE = 'balance', _('Balance')
    OTHER = 'other', _('Other')


class Side(models.TextChoices):
    NONE = '', _('Not applicable')
    LEFT = 'left', _('Left')
    RIGHT = 'right', _('Right')


class FunctionalAssessment(models.Model):
    """
    A measurement taken by the physiotherapist, e.g. knee flexion in degrees,
    a Timed Up and Go time or the score of a questionnaire
    """

    class Meta:
        ordering = ['-date']

    id = models.UUIDField(default=uuid7, primary_key=True)

    relationship = models.ForeignKey(
        'care.CareRelationship',
        on_delete=models.PROTECT,
        related_name='+',
        editable=False,
    )

    kind = models.CharField(max_length=20, choices=AssessmentKind.choices)

    name = models.CharField(max_length=100, help_text='e.g. Knee flexion, TUG, LEFS')

    side = models.CharField(max_length=5, choices=Side.choices, blank=True, default=Side.NONE)

    value = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)

    unit = models.CharField(max_length=20, blank=True, help_text='e.g. °, s, points, kg')

    data = models.JSONField(default=dict, blank=True, help_text='Answers or details')

    date = models.DateField(default=datetime.date.today)

    notes = models.TextField(blank=True)

    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} {self.value} {self.unit}'

    def get_owner_object(self):
        return None
