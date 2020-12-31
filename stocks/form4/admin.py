from django.contrib import admin
from form4.models import Filing, Transaction, FilingNote, Filer, Company
from django.urls import resolve
import nested_admin

# Register your models here.

class FilingNoteInline(nested_admin.NestedTabularInline):
    model = FilingNote
    can_delete = False
    extra = 0
class TransactionInline(nested_admin.NestedTabularInline):
    model = Transaction
    can_delete = False
    extra = 0
    fields = ('date', 'amount', 'amount_after', 'price', 'added_stock', 'code')

    inlines = [FilingNoteInline]
class FilingInline(admin.TabularInline):
    model = Filing.filers.through
    show_change_link = True
    can_delete = False
    extra = 0

class CompanyFilingInline(admin.TabularInline):
    model = Filing
    extra = 0
    can_delete = False
@admin.register(Filing)
class FilingAdmin(nested_admin.NestedModelAdmin):
    # list_filter = ('',)
    inlines = [TransactionInline]
    def get_company_symbol(self, obj):
        return obj.company.symbol
    get_company_symbol.admin_order_field = 'company__symbol'
    get_company_symbol.short_description = 'Company Symbol'
    list_display = ('id', 'date_filed', 'get_company_symbol', 'num_transactions', 'filers_display')
    readonly = ('filers',)

    exclude = ('filers',)
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_filter = ('code',)
    list_display = ('date', 'amount', 'amount_after', 'price', 'percent_change', 'filers_display')
    inlines = [FilingNoteInline]
@admin.register(FilingNote)
class FilingNoteAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'text')
@admin.register(Filer)
class FilerAdmin(admin.ModelAdmin):
    # inlines = [FilingInline]
    pass
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    sort_order = []
    list_display = ('name', 'symbol','cik', 'num_filings')
    inlines = [CompanyFilingInline]