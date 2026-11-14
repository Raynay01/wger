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
import uuid
from dataclasses import dataclass

# Django
from django.contrib.auth.models import User
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models
from django.utils.translation import gettext_lazy as _

# wger
from wger.care.disciplines import Discipline
from wger.care.prescription import (
    PrescriptionMixin,
    PrescriptionStatus,
)


class TrainingGoal(models.TextChoices):
    HYPERTROPHY = 'hypertrophy', _('Hypertrophy')
    STRENGTH = 'strength', _('Strength')
    FAT_LOSS = 'fat_loss', _('Fat loss')
    ENDURANCE = 'endurance', _('Endurance')
    PERFORMANCE = 'performance', _('Sports performance')
    HEALTH = 'health', _('Health and fitness')


class BlockFocus(models.TextChoices):
    ADAPTATION = 'adaptation', _('Adaptation')
    HYPERTROPHY = 'hypertrophy', _('Hypertrophy')
    STRENGTH = 'strength', _('Strength')
    POWER = 'power', _('Power')
    ENDURANCE = 'endurance', _('Endurance')
    DELOAD = 'deload', _('Deload')
    PEAK = 'peak', _('Peak')
    TRANSITION = 'transition', _('Transition')


@dataclass
class ScheduledBlock:
    block: 'TrainingBlock'
    start: datetime.date
    end: datetime.date


class TrainingPlan(PrescriptionMixin, models.Model):
    """
    A periodization (macrocycle): consecutive blocks (mesocycles) with a focus,
    a length in weeks and optionally the routine trained in them
    """

    discipline = Discipline.TRAINING

    class Meta:
        ordering = ['-start']

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    user = models.ForeignKey(User, on_delete=models.CASCADE, editable=False)

    name = models.CharField(verbose_name=_('Name'), max_length=100)

    goal = models.CharField(
        max_length=15,
        choices=TrainingGoal.choices,
        default=TrainingGoal.HYPERTROPHY,
    )

    start = models.DateField(default=datetime.date.today)

    description = models.TextField(blank=True)

    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def get_owner_object(self):
        return self

    def schedule(self) -> list[ScheduledBlock]:
        """The blocks with their calendar days, one after the other from the start"""
        out = []
        day = self.start
        for block in self.blocks.all():
            end = day + datetime.timedelta(weeks=block.weeks) - datetime.timedelta(days=1)
            out.append(ScheduledBlock(block, day, end))
            day = end + datetime.timedelta(days=1)
        return out

    @property
    def end(self) -> datetime.date | None:
        schedule = self.schedule()
        return schedule[-1].end if schedule else None

    def build_snapshot(self) -> dict:
        return {
            'name': self.name,
            'goal': self.goal,
            'start': self.start,
            'description': self.description,
            'blocks': [
                {
                    'name': b.name,
                    'focus': b.focus,
                    'weeks': b.weeks,
                    'routine': b.routine_id,
                    'intensity': b.intensity,
                    'volume': b.volume,
                    'weekly_sets': b.weekly_sets,
                    'notes': b.notes,
                    'order': b.order,
                }
                for b in self.blocks.all()
            ],
        }

    def copy_content_to(self, target) -> None:
        for block in self.blocks.all():
            block.pk = None
            block._state.adding = True
            block.plan = target
            block.save()


class TrainingBlock(models.Model):
    """
    A mesocycle of a training plan
    """

    class Meta:
        ordering = ['order', 'id']

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    plan = models.ForeignKey(TrainingPlan, on_delete=models.CASCADE, related_name='blocks')

    order = models.PositiveIntegerField(default=1)

    name = models.CharField(max_length=100, blank=True)

    focus = models.CharField(max_length=12, choices=BlockFocus.choices)

    weeks = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(26)],
    )

    routine = models.ForeignKey(
        'manager.Routine',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )
    """Any version of the routine; the current published one of its lineage is shown"""

    intensity = models.CharField(max_length=100, blank=True, help_text='e.g. 70-80% 1RM, RIR 2-3')

    volume = models.CharField(max_length=100, blank=True, help_text='e.g. 12-16 sets per muscle')

    weekly_sets = models.JSONField(default=list, blank=True)
    """Target sets per week per muscle: ``[{'muscle': id, 'sets': n}]``"""

    notes = models.TextField(blank=True)

    def __str__(self):
        return self.name or self.focus

    def get_owner_object(self):
        return self.plan

    def current_routine(self):
        """The published version of the routine's lineage, else the linked one"""
        routine = self.routine
        if routine is None or routine.lineage_id is None:
            return routine
        return (
            type(routine)
            .objects.filter(lineage_id=routine.lineage_id, status=PrescriptionStatus.PUBLISHED)
            .first()
            or routine
        )
