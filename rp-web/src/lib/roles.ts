import 'server-only';

import { api } from './api';
import type { Organization, Paginated, Registration } from './types';

/** Whether the user works as a professional (has an organization or a council registration) */
export async function professionalContext() {
  const [organizations, registrations] = await Promise.all([
    api<Paginated<Organization>>('organization/'),
    api<Paginated<Registration>>('professional-registration/'),
  ]);
  return {
    organizations: organizations.results,
    registrations: registrations.results,
    isProfessional: organizations.count > 0 || registrations.count > 0,
  };
}
