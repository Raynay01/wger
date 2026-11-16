{% load i18n %}{% blocktranslate %}Hello!{% endblocktranslate %}

{{ text }}
{% if link %}
{{ link }}
{% endif %}
{% blocktranslate %}You can turn these emails off in the app, under Notices.{% endblocktranslate %}

— {{ app }}
