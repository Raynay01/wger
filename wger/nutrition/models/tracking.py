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
from wger.utils.uuid import uuid7

# Local
from .meal import Meal


class AdherenceStatus(models.TextChoices):
    FULL = 'full', _('Followed')
    PARTIAL = 'partial', _('Partially followed')
    SKIPPED = 'skipped', _('Not followed')


class MealAdherence(models.Model):
    """
    Whether the user followed a prescribed meal on a calendar day
    """

    class Meta:
        ordering = ['-date']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'meal', 'date'],
                name='unique_meal_adherence_per_day',
            ),
        ]

    id = models.UUIDField(default=uuid7, primary_key=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE, editable=False)

    meal = models.ForeignKey(Meal, on_delete=models.CASCADE, related_name='adherence')

    date = models.DateField()

    status = models.CharField(max_length=10, choices=AdherenceStatus.choices)

    notes = models.CharField(max_length=500, blank=True)

    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.date} {self.meal_id} {self.status}'

    def get_owner_object(self):
        return self


class WaterLog(models.Model):
    """
    Water the user drank
    """

    class Meta:
        ordering = ['-datetime']

    id = models.UUIDField(default=uuid7, primary_key=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE, editable=False)

    datetime = models.DateTimeField(default=timezone.now)

    amount_ml = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5000)],
    )

    def __str__(self):
        return f'{self.amount_ml} ml'

    def get_owner_object(self):
        return self
