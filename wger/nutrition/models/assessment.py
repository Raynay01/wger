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
import math
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


class SkinfoldProtocol(models.TextChoices):
    JACKSON_POLLOCK_3 = 'jp3', _('Jackson-Pollock, 3 skinfolds')
    JACKSON_POLLOCK_7 = 'jp7', _('Jackson-Pollock, 7 skinfolds')
    DURNIN_WOMERSLEY = 'durnin', _('Durnin-Womersley, 4 skinfolds')


SKINFOLD_SITES = (
    'chest',
    'midaxillary',
    'triceps',
    'subscapular',
    'abdomen',
    'suprailiac',
    'thigh',
    'biceps',
)


def skinfold_sites(protocol: str, sex: str) -> tuple[str, ...]:
    """The sites a protocol measures"""
    if protocol == SkinfoldProtocol.JACKSON_POLLOCK_3:
        if sex == Sex.MALE:
            return ('chest', 'abdomen', 'thigh')
        return ('triceps', 'suprailiac', 'thigh')
    if protocol == SkinfoldProtocol.JACKSON_POLLOCK_7:
        return ('chest', 'midaxillary', 'triceps', 'subscapular', 'abdomen', 'suprailiac', 'thigh')
    if protocol == SkinfoldProtocol.DURNIN_WOMERSLEY:
        return ('biceps', 'triceps', 'subscapular', 'suprailiac')
    return ()


# Durnin & Womersley (1974): density = c - m * log10(sum), by sex and age band
DURNIN_COEFFICIENTS = {
    Sex.MALE: ((20, 1.1620, 0.0630), (30, 1.1631, 0.0632), (40, 1.1422, 0.0544),
               (50, 1.1620, 0.0700), (None, 1.1715, 0.0779)),
    Sex.FEMALE: ((20, 1.1549, 0.0678), (30, 1.1599, 0.0717), (40, 1.1423, 0.0632),
                 (50, 1.1333, 0.0612), (None, 1.1339, 0.0645)),
}  # fmt: skip


def body_density(protocol: str, sex: str, age: int, total: float) -> float:
    """Body density from the sum of the skinfolds in mm"""
    male = sex == Sex.MALE
    if protocol == SkinfoldProtocol.JACKSON_POLLOCK_3:
        if male:
            return 1.10938 - 0.0008267 * total + 0.0000016 * total**2 - 0.0002574 * age
        return 1.0994921 - 0.0009929 * total + 0.0000023 * total**2 - 0.0001392 * age
    if protocol == SkinfoldProtocol.JACKSON_POLLOCK_7:
        if male:
            return 1.112 - 0.00043499 * total + 0.00000055 * total**2 - 0.00028826 * age
        return 1.097 - 0.00046971 * total + 0.00000056 * total**2 - 0.00012828 * age
    for limit, c, m in DURNIN_COEFFICIENTS[Sex.MALE if male else Sex.FEMALE]:
        if limit is None or age < limit:
            return c - m * math.log10(total)
    raise ValueError(protocol)


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

    skinfold_protocol = models.CharField(
        max_length=6,
        choices=SkinfoldProtocol.choices,
        blank=True,
        help_text='When set, the body fat is computed from the skinfolds',
    )

    skinfolds = models.JSONField(
        default=dict,
        blank=True,
        help_text='Skinfolds in mm by site, e.g. {"triceps": 18}',
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

    protein_per_kg = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.5')), MaxValueValidator(Decimal(4))],
        help_text='Protein target in g per kg of body weight',
    )

    fat_percent = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(10), MaxValueValidator(70)],
        help_text='Share of the target energy from fat, in percent',
    )

    notes = models.TextField(blank=True)

    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Assessment {self.date}'

    def save(self, *args, **kwargs):
        computed = self.skinfold_body_fat
        if computed is not None:
            self.body_fat = computed
        super().save(*args, **kwargs)

    @property
    def skinfold_sum(self) -> Decimal | None:
        sites = skinfold_sites(self.skinfold_protocol, self.sex)
        if not sites or any(self.skinfolds.get(site) is None for site in sites):
            return None
        return sum((Decimal(str(self.skinfolds[site])) for site in sites), Decimal(0))

    @property
    def skinfold_body_fat(self) -> Decimal | None:
        """Body fat in percent by the protocol and Siri's equation"""
        total = self.skinfold_sum
        if total is None or total <= 0:
            return None
        density = body_density(self.skinfold_protocol, self.sex, self.age, float(total))
        return Decimal(495 / density - 450).quantize(Decimal('0.1'))

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

    @property
    def macros(self) -> dict | None:
        """Protein from g/kg, fat from its share of the energy, carbohydrates the rest"""
        if self.protein_per_kg is None or self.fat_percent is None:
            return None
        protein = round(float(self.weight * self.protein_per_kg))
        fat = round(self.target_energy * self.fat_percent / 100 / 9)
        carbohydrates = max(0, round((self.target_energy - protein * 4 - fat * 9) / 4))
        return {'protein': protein, 'carbohydrates': carbohydrates, 'fat': fat}
