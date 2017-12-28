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


if parler_exists:
    from parler.forms import TranslatableModelForm

    class PublisherParlerForm(TranslatableModelForm, PublisherForm):
        pass
