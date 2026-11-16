/*
 This file is part of wger Workout Manager.

 wger Workout Manager is free software: you can redistribute it and/or modify
 it under the terms of the GNU Affero General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 wger Workout Manager is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU Affero General Public License
 */

/*
 * Fetches the reCAPTCHA v3 token when the form is submitted
 * (django_recaptcha/includes/js_v3.html)
 */
(function () {
    const config = document.currentScript.dataset;
    grecaptcha.ready(function () {
        const element = document.querySelector(
            `.g-recaptcha[data-widget-uuid="${config.widgetUuid}"]`
        );
        element.form.addEventListener('submit', function (event) {
            event.preventDefault();
            const options = config.action ? { action: config.action } : {};
            grecaptcha.execute(config.publicKey, options).then(function (token) {
                element.value = token;
                element.form.submit();
            });
        });
    });
})();
