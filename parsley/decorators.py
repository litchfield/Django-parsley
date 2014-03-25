import re

from django import forms
from widgets import ParsleyChoiceFieldRendererMixin

FIELD_TYPES = [
    (forms.URLField, "url"),
    (forms.EmailField, "email"),
    (forms.IntegerField, "digits"),
    (forms.DecimalField, "number"),
    (forms.FloatField, "number"),
]


FIELD_ATTRS = [
    ("min_length", "minlength"),
    ("max_length", "maxlength"),
    ("min_value", "min"),
    ("max_value", "max"),
]


def update_widget_attrs(field, prefix='data'):
    attrs = field.widget.attrs

    if field.required:
        if getattr(field.widget, 'renderer', False):
            # Use a mixin, to try and support non-standard renderers if possible
            renderer = field.widget.renderer
            class ParsleyChoiceFieldRenderer(ParsleyChoiceFieldRendererMixin, renderer):
                parsley_namespace = prefix
            field.widget.renderer = ParsleyChoiceFieldRenderer
        else:
            attrs["{prefix}-required".format(prefix=prefix)] = "true"
            error_message = field.error_messages.get('required', None)
            if error_message:
                attrs["{prefix}-required-message".format(prefix=prefix)] = error_message

    if isinstance(field, forms.RegexField):
        attrs.update({"{prefix}-regexp".format(prefix=prefix): field.regex.pattern})

        error_message = field.error_messages.get('invalid', None)
        if error_message:
            attrs["{prefix}-regexp-message".format(prefix=prefix)] = error_message

        if field.regex.flags & re.IGNORECASE:
            attrs.update({"{prefix}-regexp-flag".format(prefix=prefix): "i"})

    if isinstance(field, forms.MultiValueField):
        for subfield in field.fields:
            update_widget_attrs(subfield)

    # Set {prefix}-* attributes for parsley based on Django field attributes
    for attr, data_attr, in FIELD_ATTRS:
        if getattr(field, attr, None):
            attrs["{prefix}-{0}".format(data_attr, prefix=prefix)] = getattr(field, attr)

            error_message = field.error_messages.get(attr, None)
            if error_message:
                attrs["{prefix}-{0}-message".format(data_attr, prefix=prefix)] = error_message

    # Set {prefix}-type attribute based on Django field instance type
    for klass, field_type in FIELD_TYPES:
        if isinstance(field, klass):
            attrs["{prefix}-type".format(prefix=prefix)] = field_type

            error_message = field.error_messages.get('invalid', None)
            if error_message:
                attrs["{prefix}-type-{0}-message".format(field_type, prefix=prefix)] = error_message


def parsleyfy_bind(form):
    prefix = getattr(getattr(form, 'Meta', None), 'parsley_namespace', 'data-parsley')
    for _, field in form.fields.items():
        update_widget_attrs(field, prefix)
    extras = getattr(getattr(form, 'Meta', None), 'parsley_extras', {})
    for field_name, data in extras.items():
        for key, value in data.items():
            if field_name not in form.fields:
                continue
            attrs = form.fields[field_name].widget.attrs
            if key == 'equalto':
                # Use HTML id for {prefix}-equalto
                value = '#' + form[value].id_for_label
            if isinstance(value, bool):
                value = "true" if value else "false"
            attrs["{prefix}-%s".format(prefix=prefix) % key] = value

def parsleyfy(klass):
    "A decorator to add {prefix}-* attributes to your form.fields"
    old_init = klass.__init__

    def new_init(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        parsleyfy_bind(self)
    klass.__init__ = new_init

    return klass
