from modeltranslation.translator import TranslationOptions, register
from modeltranslation.admin import TranslationAdmin, TranslationStackedInline
from .models import Category, Product, SubCategory, Instruction


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


class StackedAdmin(TranslationStackedInline):
    class Media:
        js = (
            'https://ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js',
            'https://ajax.googleapis.com/ajax/libs/jqueryui/1.10.2/jquery-ui.min.js',
            'modeltranslation/js/tabbed_translation_fields.js',
        )
        css = {
            'screen': ('modeltranslation/css/tabbed_translation_fields.css',),
        }


@register(Category)
class CategoryTranslationOptions(TranslationOptions):
    fields = ['name']


@register(SubCategory)
class SubCategoryTranslationOptions(TranslationOptions):
    fields = ['name']


@register(Product)
class ProductTranslationOptions(TranslationOptions):
    fields = ['name', 'description']
