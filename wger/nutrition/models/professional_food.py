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
import uuid

# Django
from django.contrib.auth.models import User
from django.db import models

# Local
from .ingredient import Ingredient


class ProfessionalFood(models.Model):
    """
    A food a professional added to the shared food database, e.g. a corrected
    TACO food or a product of a local brand. The ingredient itself is public,
    this keeps who added it and lets their organization maintain it.
    """

    class Meta:
        ordering = ['-created']

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    ingredient = models.OneToOneField(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='professional_food',
    )

    organization = models.ForeignKey(
        'care.Organization',
        on_delete=models.PROTECT,
        related_name='foods',
    )

    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+')

    based_on = models.ForeignKey(
        Ingredient,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text='The food this one corrects, if any',
    )

    created = models.DateTimeField(auto_now_add=True)

    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.ingredient.name} ({self.organization})'

    def get_owner_object(self):
        return None
