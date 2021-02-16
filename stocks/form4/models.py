from django.db import models
from django.db.models.functions import Lower
import math
from django.db.models import F
from django.db.models.functions import Cast
from parse_files import TRANSACTION_CODES
# Create your models here.
ON_FIELDS = [
    ('P', 'price'),
    ('A', 'amount')
]

class Filing(models.Model):
    company = models.ForeignKey('Company', on_delete=models.CASCADE)
    date_filed = models.DateField()
    filers = models.ManyToManyField('Filer')
    index_url = models.URLField(max_length=250)
    filing_url = models.URLField(max_length=250)
    @property
    def num_transactions(self):
        return self.transaction_set.all().count()
    # num_transactions.short_description = 'Number of Transactions'
    def filers_display(self):
        return ' / '.join([f.name for f in self.filers.all()])
    filers_display.short_description = 'Filed By'
    def __str__(self):
        return f' {self.filers_display()} - {self.date_filed} - {self.company.symbol}'
    class Meta:
        ordering = ('date_filed',)

# class StockPriceOnDay(models.Model):
#     company = models.ForeignKey('Company', on_delete=models.CASCADE)
#     date = models.DateField()
#     price = models.FloatField()
class Transaction(models.Model):
    filing = models.ForeignKey('Filing', on_delete=models.CASCADE)
    date = models.DateField()
    amount = models.FloatField()
    price = models.FloatField()
    added_stock = models.BooleanField()
    code = models.CharField(max_length=3, choices=TRANSACTION_CODES)
    amount_after = models.FloatField()
    # price_history = models.ManyToManyField('StockPriceOnDay')
    def filers_display(self):
        return self.filing.filers_display()
    @property
    def amount_before(self):
        multiplier = float(self.added_stock) * 2 - 1
        amount_before = self.amount_after - (multiplier * self.amount)
        return amount_before
    def percent_change(self):
        amount_before = self.amount_before
        if amount_before == 0:
            return 'NEW'
        percentage =  round((self.amount_after / self.amount_before - 1) * 100, 3)
        return f'{percentage}%'
    percent_change.admin_order_field = F('amount_after') / (F('amount_after') - F('amount') * (F('added_stock') * 2 - 1)) - 1
    filers_display.short_description = 'Made by'
    def __str__(self):
        # added_stock_str = next((v[1] for v in TRANSACTION_CODES if v[0] == self.code), None)
        return f'{self.date}: {self.code} {self.amount} @ {self.price}'
    class Meta:
        ordering = ('date',)
class FilingNote(models.Model):
    transaction = models.ForeignKey('Transaction', on_delete=models.CASCADE)
    text = models.TextField()
    on_field = models.CharField(max_length=1, choices=ON_FIELDS)
    def __str__(self):
        return f'{self.text[:100]}...'
class Company(models.Model):
    name = models.CharField(max_length=200)
    cik = models.CharField(max_length=20, unique=True)
    symbol = models.CharField(max_length=10)
    def num_filings(self):
        return self.filing_set.all().count()
    def __str__(self):
        return f'{self.name} ({self.symbol}) - {self.cik}'
    class Meta:
        ordering = ('symbol',)
class Filer(models.Model):
    name = models.CharField(max_length=200)
    cik = models.CharField(max_length=20, unique=True)
    is_director = models.BooleanField()
    is_officer = models.BooleanField()
    is_ten_percent_owner = models.BooleanField()
    is_other = models.BooleanField()
    officer_title = models.CharField(max_length=200, null=True)
    other_text = models.CharField(max_length=200, null=True)
    def role_display(self):
        roles = []
        if self.is_director:
            roles.append('Director')
        if self.is_ten_percent_owner:
            roles.append('Ten percent owner')
        if self.is_officer:
            roles.append('Officer')
        if self.is_other:
            roles.append('Other')
        if self.other_text is not None:
            roles.append(self.other_text)
        if self.officer_title is not None:
            roles.append(self.officer_title)
        return ', '.join(roles)
    def __str__(self):
        return f'{self.name} - {self.role_display()} ({self.cik})'
    class Meta:
        ordering = ('name',)