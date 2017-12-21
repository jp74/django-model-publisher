from django import forms
from django.forms import widgets
from django.utils.translation import ugettext_lazy as _

from publisher.utils import parler_exists


class PublisherNoteForm(forms.Form):
    note = forms.CharField(
        label=_("Note"),
        widget=widgets.Textarea(),
        required=False
    )

class PublisherForm(forms.ModelForm):
    note = forms.CharField(
        label=_("Note"),
        widget=widgets.Textarea(),
        required=False
    )

    def clean(self):
        data = super(PublisherForm, self).clean()
        cleaned_data = self.cleaned_data
        instance = self.instance

        # work out which fields are unique_together
        unique_fields_set = instance.get_unique_together()

        if not unique_fields_set:
            return data

        for unique_fields in unique_fields_set:
            unique_filter = {}
            for unique_field in unique_fields:
                field = instance.get_field(unique_field)

                # Get value from the form or the model
                if field.editable:
                    unique_filter[unique_field] = cleaned_data[unique_field]
                else:
                    unique_filter[unique_field] = getattr(instance, unique_field)

            # try to find if any models already exist in the db;
            # I find all models and then exclude those matching the current model.
            existing_instances = type(instance).objects \
                                               .filter(**unique_filter) \
                                               .exclude(pk=instance.pk)

            if instance.publisher_linked:
                existing_instances = existing_instances.exclude(pk=instance.publisher_linked.pk)

            if existing_instances:
                for unique_field in unique_fields:
                    self._errors[unique_field] = self.error_class(
                        [_('This value must be unique.')])

        return data


if parler_exists:
    from parler.forms import TranslatableModelForm

    class PublisherParlerForm(TranslatableModelForm, PublisherForm):
        pass
