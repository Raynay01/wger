{% load i18n %}{% blocktranslate %}Hello!{% endblocktranslate %}

{% blocktranslate %}{{ professional }} ({{ profession }}, {{ organization }}) invited you to be followed in {{ discipline }} on {{ app }}.{% endblocktranslate %}

{% if link %}{% blocktranslate %}To accept, open this link and log in with your Google account:{% endblocktranslate %}

{{ link }}
{% else %}{% blocktranslate %}To accept, log in to {{ app }} with the Google account of {{ email }} and open your invitations.{% endblocktranslate %}
{% endif %}
{% blocktranslate %}When you accept, this professional can prescribe and follow your {{ discipline }}. Data of other areas is only shared if you allow it, and you can end the follow-up at any time.{% endblocktranslate %}

{% blocktranslate %}If you don't know this professional, just ignore this email.{% endblocktranslate %}

— {{ app }}
