#  This file is part of wger Workout Manager <https://github.com/wger-project>.
#
#  wger Workout Manager is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  wger Workout Manager is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Standard Library
import datetime
from decimal import Decimal

# Django
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models
from django.utils.translation import gettext_lazy as _

# wger
from wger.utils.uuid import uuid7


class Sex(models.TextChoices):
    """Biological sex, which the energy equations depend on"""

    FEMALE = 'female', _('Female')
    MALE = 'male', _('Male')


class ActivityLevel(models.TextChoices):
    SEDENTARY = 'sedentary', _('Sedentary')
    LIGHT = 'light', _('Lightly active')
    MODERATE = 'moderate', _('Moderately active')
    VERY = 'very', _('Very active')
    EXTREME = 'extreme', _('Extremely active')


ACTIVITY_FACTORS = {
    ActivityLevel.SEDENTARY: Decimal('1.2'),
    ActivityLevel.LIGHT: Decimal('1.375'),
    ActivityLevel.MODERATE: Decimal('1.55'),
    ActivityLevel.VERY: Decimal('1.725'),
    ActivityLevel.EXTREME: Decimal('1.9'),
}


class EnergyEquation(models.TextChoices):
    MIFFLIN = 'mifflin', _('Mifflin-St Jeor')
    HARRIS_BENEDICT = 'harris_benedict', _('Harris-Benedict (revised)')
    KATCH_MCARDLE = 'katch_mcardle', _('Katch-McArdle (lean mass)')


class NutritionalAnamnesis(models.Model):
    """
    The interview the nutritionist does with the patient: history, habits and
    preferences. Dated, so a later one does not overwrite the first.
    """

    class Meta:
        ordering = ['-date', '-created']

    id = models.UUIDField(default=uuid7, primary_key=True)

    relationship = models.ForeignKey(
        'care.CareRelationship',
        on_delete=models.PROTECT,
        related_name='+',
        editable=False,
    )

    date = models.DateField(default=datetime.date.today)

    goal = models.TextField(blank=True, help_text='Main complaint and goal of the patient')

    medical_history = models.TextField(blank=True, help_text='Diseases, surgeries, exams')

    medications = models.TextField(blank=True, help_text='Medications and supplements')

    allergies = models.TextField(blank=True, help_text='Food allergies and intolerances')

    preferences = models.TextField(blank=True, help_text='Foods liked and disliked')

    eating_habits = models.TextField(blank=True, help_text='Meal times, where and with whom')

    bowel_habits = models.TextField(blank=True)

    sleep = models.TextField(blank=True)

    water = models.TextField(blank=True, help_text='Usual water intake')

    alcohol_smoking = models.TextField(blank=True)

    physical_activity = models.TextField(blank=True)

    notes = models.TextField(blank=True)

    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Anamnesis {self.date}'

    def get_owner_object(self):
        return None


class NutritionalAssessment(models.Model):
    """
    Anthropometry and the energy needs computed from it, taken by the nutritionist

    Sex and age are stored with the assessment, so it keeps its result when
    the profile changes later.
    """

    class Meta:
        ordering = ['-date', '-created']

    id = models.UUIDField(default=uuid7, primary_key=True)

    relationship = models.ForeignKey(
        'care.CareRelationship',
        on_delete=models.PROTECT,
        related_name='+',
        editable=False,
    )

    date = models.DateField(default=datetime.date.today)

    sex = models.CharField(max_length=6, choices=Sex.choices)

    age = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(10), MaxValueValidator(120)],
    )

    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal(20)), MaxValueValidator(Decimal(400))],
        help_text='kg',
    )

    height = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        validators=[MinValueValidator(Decimal(100)), MaxValueValidator(Decimal(250))],
        help_text='cm',
    )

    waist = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal(30)), MaxValueValidator(Decimal(250))],
        help_text='cm',
    )

    hip = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal(30)), MaxValueValidator(Decimal(250))],
        help_text='cm',
    )

    body_fat = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal(2)), MaxValueValidator(Decimal(70))],
        help_text='Body fat in percent, measured e.g. by skinfolds or bioimpedance',
    )

    activity_level = models.CharField(
        max_length=10,
        choices=ActivityLevel.choices,
        default=ActivityLevel.LIGHT,
    )

    equation = models.CharField(
        max_length=15,
        choices=EnergyEquation.choices,
        default=EnergyEquation.MIFFLIN,
    )

    energy_adjustment = models.IntegerField(
        default=0,
        validators=[MinValueValidator(-1500), MaxValueValidator(1500)],
        help_text='kcal added to the total expenditure for the goal, e.g. -500 to lose weight',
    )

    notes = models.TextField(blank=True)

    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Assessment {self.date}'

    def get_owner_object(self):
        return None

    @property
    def bmi(self) -> Decimal:
        meters = self.height / 100
        return (self.weight / (meters * meters)).quantize(Decimal('0.1'))

    @property
    def waist_hip_ratio(self) -> Decimal | None:
        if not self.waist or not self.hip:
            return None
        return (self.waist / self.hip).quantize(Decimal('0.01'))

    @property
    def lean_mass(self) -> Decimal | None:
        if self.body_fat is None:
            return None
        return (self.weight * (100 - self.body_fat) / 100).quantize(Decimal('0.1'))

    @property
    def basal_energy(self) -> int:
        """Basal metabolic rate in kcal per day"""
        w, h, a = float(self.weight), float(self.height), self.age
        male = self.sex == Sex.MALE
        if self.equation == EnergyEquation.KATCH_MCARDLE and self.body_fat is not None:
            value = 370 + 21.6 * w * (100 - float(self.body_fat)) / 100
        elif self.equation == EnergyEquation.HARRIS_BENEDICT:
            if male:
                value = 88.362 + 13.397 * w + 4.799 * h - 5.677 * a
            else:
                value = 447.593 + 9.247 * w + 3.098 * h - 4.330 * a
        else:
            value = 10 * w + 6.25 * h - 5 * a + (5 if male else -161)
        return round(value)

    @property
    def total_energy(self) -> int:
        """Total daily energy expenditure: basal rate times the activity factor"""
        return round(self.basal_energy * float(ACTIVITY_FACTORS[self.activity_level]))

    @property
    def target_energy(self) -> int:
        return self.total_energy + self.energy_adjustment
