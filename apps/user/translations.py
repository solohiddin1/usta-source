from modeltranslation.translator import TranslationOptions, register
from modeltranslation.admin import TranslationAdmin
from .models import Region, Store


class CustomAdmin(TranslationAdmin):
    class Media:
        js = (
            'https://ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js',
            'https://ajax.googleapis.com/ajax/libs/jqueryui/1.10.2/jquery-ui.min.js',
            'modeltranslation/js/tabbed_translation_fields.js',
        )
        css = {
            'screen': ('modeltranslation/css/tabbed_translation_fields.css',),
        }


@register(Region)
class RegionTranslationOptions(TranslationOptions):
    fields = ['name']


@register(Store)
class StoreTranslationOptions(TranslationOptions):
    fields = ['name']
