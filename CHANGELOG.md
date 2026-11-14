# Changelog for the next release

> [!IMPORTANT]
> This release comes with some breaking changes for self-hoster. Please read carefully.

## New features

### Double progression
Progression requirements can now reference the top of the prescribed range via the new rules `max_repetitions` and `max_weight`, and the new `all_sets` flag requires every prescribed set to qualify. Together they enable classic double progression schemes ("work from 8 to 12 reps at a fixed weight, add weight only once all sets reach 12"), e.g. `{"rules": ["max_repetitions"], "all_sets": true}`.

### Professionals, patients and multidisciplinary follow-up (RP Performance)
Trainers, physiotherapists and nutritionists work in organizations
(`/api/v2/organization/`, `/api/v2/membership/`) and register their council
number (`/api/v2/professional-registration/`, CREF, CREFITO or CRN). They invite
patients per discipline (`/api/v2/care-relationship/`); the patient accepts with
an explicit consent, which is recorded (`/api/v2/consent/`).

* The app shows the modules of the patient's professionals only
  (`/api/v2/care/modules/`), and `/api/v2/care/my-day/` returns the training,
  meals, logged totals, water and physio exercises of a calendar day.
* Nutrition plans, routines and the new physio protocols can be written by a
  professional for a patient (`care_relationship` on create). They start as a
  draft the patient does not see; `publish` freezes the version, `new-version`
  creates an editable copy and the previous version stays readable as
  superseded. Only the author edits a prescription, so a nutritionist cannot
  change a routine and vice versa. Plans and routines without author behave as
  before.
* Patients share read-only summaries with each professional
  (`/api/v2/access-grant/`, read via `care-relationship/{id}/shared/`), every
  read is logged. Professionals leave notes for each other
  (`/api/v2/multidisciplinary-note/`).
* Nutrition: meal and meal item `instructions`, substitution options approved by
  the nutritionist (`/api/v2/substitution-option/`), meal adherence per day
  (`/api/v2/meal-adherence/`), water logs (`/api/v2/water-log/`) and a
  `goal_water_ml` per plan.
* Training: `tempo`, target `rpe` and `range_of_motion` on slot entries (also in
  the routine `structure`), `rpe` on workout logs.
* Invitation links: `care-relationship/{id}/accept/` with the invitation
  `token` works for any email address of the patient.
* Invitation emails: creating an invitation sends nothing; the professional
  sends it with `care-relationship/{id}/send-email/` (at most every ten
  minutes, `invitation_sent_at` tells when). The link points to `WEB_APP_URL`,
  the app is named after `WEB_APP_NAME`.
* Google login: set `GOOGLE_CLIENT_ID` (and `GOOGLE_CLIENT_SECRET`) to enable
  it; web clients send Google's ID token to the headless provider token
  endpoint.
* New web app in `rp-web/` (Next.js) for patients and professionals, see its
  README.
* Data subject rights (LGPD): `/api/v2/care/my-data/` exports all personal
  data of the user as JSON, including who read what they shared.
  `/api/v2/data-request/` records a deletion request, which ends the
  follow-ups at once; the platform admin deletes the account in the Django
  admin, which refuses while professionals hold clinical records about the
  person. Requests stay as evidence after the deletion.
* The set descriptions ("3 Sets", "RiR", "rest") are translatable again.
* `import-taco-products` imports the TACO (Tabela Brasileira de Composição de
  Alimentos, NEPA/UNICAMP): 590 Brazilian foods in Portuguese, with category,
  fiber and sodium, rounded as printed. The pinned CSV is verified by checksum,
  a second run updates instead of duplicating. Foods the table gives no values
  for are skipped, not guessed. It also adds about 700 household measures
  (colher de sopa, concha, xícara, ...) with the grams of the POF/IBGE table,
  through a hand-curated TACO to POF mapping kept in the repository; measures
  that whole grams would change by more than 5% are left out.
* `/api/v2/care/my-day/` gives the household measure and the grams of each
  prescribed meal item.
* Agenda: professionals schedule consultations, sessions and assessments
  (`/api/v2/appointment/`), both sides can cancel. `/api/v2/care/calendar/`
  gives the patient's days (training or rest, food plan, physio protocols,
  appointments) in the patient's timezone. Prescriptions created without a
  start date start on the patient's calendar day instead of the server's.
* Nutritionists add foods to the shared database or correct an existing one
  (`/api/v2/professional-food/`). The food is public like any other, marked
  as "Cadastro profissional" with the organization as author; a correction
  copies the values and household measures of the original, which stays
  untouched. Only the organization changes its foods, and only while no
  published plan or diary uses them.
* Physiotherapy: protocols with exercises (`/api/v2/physio-protocol/`,
  `/api/v2/protocol-exercise/`), pain records on the 0-10 scale with alerts for
  the physiotherapist (`/api/v2/pain-record/`, `pain-record/alerts/`), exercise
  records and functional assessments (`/api/v2/functional-assessment/`).

### Others
* `/api/v2/measurement/` accepts a `metric_type` instead of a `category` id when
  writing, and can be filtered by `metric_type` and `external_id`. Integrations
  such as scale apps no longer have to look up their category first or keep
  track of the ids of the entries they wrote.
* Exercise contributions always have an author: if none is given, the username
  is used. Everyone who edits an exercise or translation is credited as an
  author, images and videos keep the author of the file.
* The routine date sequences (`date-sequence-gym`, `date-sequence-display`) have
  a new `text_repr_short` per set: repetitions and weight only, without sets,
  RiR and rest, e.g. for notifications.
* Measurements have a new generic `device` source for data written by a wearable
  or sensor app on behalf of the user. Put vendor and model in `extra_data`. It
  is deduplicated on `external_id` and checked against the metric limits like
  every other source.
* Workout logs have an optional `notes` field, so individual sets can get a note
  (e.g. form cues or how the set felt) in addition to the notes of the session.
* Cloudflare Turnstile can be used as captcha on the registration and password
  reset forms, as an alternative to Google reCAPTCHA. The `CAPTCHA_PROVIDER`
  setting selects reCAPTCHA, Turnstile or no captcha, see the settings page in
  the docs.

### Bug fixes

* All 1RM estimates (calculated "1RM" and "1RM total" measurements, personal
  record trophies, routine statistics) now share one calculation. The reps in
  reserve of a set now also raise the estimate of the calculated measurements,
  existing curves change accordingly on their next recalculation. Personal
  records compare sets logged in lb and kg correctly and are no longer awarded
  for sets not counted in repetitions or not weighed in kg or lb. Personal
  record trophies already awarded for such sets are deleted by a migration.
* Counted messages for token expiry, confirmation links, inactive-member reminders,
  and workout-session limits now use locale-aware plural forms.
* Deleting a routine, day, slot, or slot entry now preserves completed workout
  sessions and logs, including performed and target values. Only the references
  to deleted routine structure are cleared. Explicit session deletion and account
  deletion continue to remove the corresponding history. Apply the usual database
  migrations when upgrading; previously deleted history cannot be restored by
  this change.
* Sets with "Until Failure" or "Max Reps" but no repetitions value keep their
  unit in the routine API and show it in the set text.
* The exercise and ingredient syncs no longer hang forever when the remote
  server stops answering. Requests to it now time out, see
  `WGER_REQUEST_TIMEOUT`.
* Gallery and exercise images with more than about 89 megapixels are now
  rejected on upload.

## New settings
*(for self-hoster)*

* `CAPTCHA_PROVIDER` (`none`, `recaptcha` or `turnstile`) replaces `USE_RECAPTCHA`.
  `USE_RECAPTCHA=True` keeps working for now, but `manage.py check` warns about
  it. Turnstile needs `TURNSTILE_SITE_KEY` and `TURNSTILE_SECRET_KEY`.
* `WGER_REQUEST_TIMEOUT` (default `60`): seconds to wait for an answer from a
  remote server, e.g. `WGER_INSTANCE` during the exercise and ingredient syncs,
  before giving up.
* `AWS_DEFAULT_ACL` (default empty): ACL for files uploaded to S3, e.g.
  `public-read` for buckets whose files aren't public by default.

## Breaking API changes
*(only relevant if you have your own scripts or interact with the REST API)*

* Creating exercises via `POST /api/v2/exercise/` now requires the `add_exercise`
  permission. Regular users should use `/api/v2/exercise-submission/`, which
  creates the exercise together with at least one translation.

## Upgrade steps

  ```bash
  docker compose pull 
  docker compose down powersync
  docker compose up -d web
  docker compose up -d powersync
  ```
