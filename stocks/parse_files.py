import edgar
import requests
from lxml import html
import pandas
import ujson as json
import sys
import random
import asyncio
import threading
import importlib.util
import time
import os
import xmltodict
import uuid
# import tqdm if possible
import tqdm
from asgiref.sync import sync_to_async
import xml
import django
from aiohttp import ClientSession, TCPConnector
from timeit import default_timer as timer
base = 'https://www.sec.gov'
limit = 10
import re
from itertools import islice
import math
import binascii
from collections import OrderedDict

TRANSACTION_CODES = [
    ('P', 'PURCHASE'),
    ('P-B', 'PURCHASE - 10b5-1'),
    ('S', 'SOLD'),
    ('S-B', 'SOLD - 10b5-1'),
    ('S-T', 'SOLD - TAX'),
    ('S-M', 'SOLD - MARGIN CALL'),
    ('A', 'ACQUIRED'),
    ('A-B', 'ACQUIRED - 10b5-1'),
    ('A-P', 'ACQUIRED - PURCHASE PLAN'),
    ('A-I', 'ACQUIRED - COMPENSATION'),
    ('A-D', 'ACQUIRED - DIVIDEND')
]

def test(phrases, s):
    for phrase in phrases:
        if phrase in s:
            return True
    return False

def get_informative_code(text, code):
    text = text.lower()
    if test(['10b5-1'], text):
        code = code.split('-')[0] + '-B'
    elif code.startswith('S') and test(['tax'], text):
        code = 'S-T'
    elif code.startswith('A') and test(['purchase plan'],text):
        code = 'A-P'
    elif code.startswith('S') and test(['margin loan'],text):
        code = 'S-M'
    elif code.startswith('A') and test(['dividend'],text):
        code = 'A-D'
    elif code.startswith('A') and test(['performance', 'incentive', 'prsu', 'compensation plan'],text):
        code = 'A-I'
    return code

def create_django_models(data, index_url, filing_url):
    try:
        company, _ = Company.objects.get_or_create(
            cik=data['company']['issuerCik'],
            symbol=data['company']['issuerTradingSymbol'].upper().split('.')[0].split(',')[0],
            name=data['company']['issuerName']
        )
    except django.db.utils.IntegrityError:
        company = Company.objects.get(cik=data['company']['issuerCik'])
    filing, _ = Filing.objects.get_or_create(
        company=company,
        date_filed=data['date_filed'],
        index_url=index_url,
        filing_url=filing_url
    )
    for raw_f in data['filers']:
        try:
            filer, _ = Filer.objects.get_or_create(
                cik=raw_f['cik'],
                name=raw_f['name'],
                is_director=raw_f.get('isDirector', False),
                is_officer=raw_f.get('isOfficer', False),
                is_ten_percent_owner=raw_f.get('isTenPercentOwner', False),
                is_other=raw_f.get('isOther', False),
                officer_title=raw_f.get('officerTitle'),
                other_text=raw_f.get('otherText'),
            )
        except django.db.utils.IntegrityError: # Usually because the officer_title or other_text has changed.
            filer = Filer.objects.get(cik=raw_f['cik'])
        filing.filers.add(filer)
    for raw_t in data['transactions']:
        transaction, _ = Transaction.objects.get_or_create(
            filing=filing,
            date=raw_t['date'],
            amount=raw_t['amount'],
            price=raw_t['price'],
            added_stock=raw_t['addedStock'],
            code=raw_t['code'],
            amount_after=raw_t['amountAfter']
        )
        for price_note in raw_t['priceFootnotes']:
            FilingNote.objects.get_or_create(
                on_field='P',
                transaction=transaction,
                text=price_note
            )
        for amount_note in raw_t['amountFootnotes']:
            FilingNote.objects.get_or_create(
                on_field='A',
                transaction=transaction,
                text=amount_note
            )
def extract_relevant(data):
    data_o = data.get('ownershipDocument')

    # If there are no possible non derivatives, ignore
    non_deriv_table = data_o.get('nonDerivativeTable')
    if non_deriv_table is None:
        return None
    non_deriv = non_deriv_table.get('nonDerivativeTransaction')
    if non_deriv is None:
        return None
    if isinstance(non_deriv, OrderedDict):
        non_deriv = [non_deriv]
    final = {}
    issuer = data_o['issuer']
    # FUND LLC CAPITAL PARTNERS, LIMITED PARTNERSHIP TRUST ADVISORS L.L.C
    owner_blacklist = ['fund','llc','capital','partner','partnership','trust','advisor','l.l.c', 'ltd.','asset','holdings','inc.']
    if isinstance(data_o['reportingOwner'], OrderedDict):
        data_o['reportingOwner'] = [data_o['reportingOwner']]
    
    all_owners = []
    for i, o in enumerate(data_o['reportingOwner']):
        owner_details = {}
        owner_details['cik'] = o['reportingOwnerId']['rptOwnerCik']
        owner_details['name'] = o['reportingOwnerId']['rptOwnerName']
        for key in o['reportingOwnerRelationship']:
            val = o['reportingOwnerRelationship'][key]
            if key.startswith('is'):
                owner_details[key] = bool(val)
            else:
                owner_details[key] = val
        all_owners.append(owner_details)
        # valid_owners = []
        # for possible_owner in data_o['reportingOwner']:
        #     owner_name = possible_owner['reportingOwnerId']['rptOwnerName'].lower()
        #     valid = True
        #     for term in owner_blacklist:
        #         if term in owner_name:
        #             valid = False
        #             break
        #     if valid:
        #         valid_owners.append(possible_owner)
        
        # if len(valid_owners) == 0:
        #     # print(json.dumps(data_o['reportingOwner'], indent=2))
        #     print('No valid owners.')
        #     data_o['reportingOwner'] = data_o['reportingOwner'][0]
        # elif len(valid_owners) > 1:
        #     # print(json.dumps(valid_owners, indent=2))
        #     print('Multiple valid owners.')
        #     data_o['reportingOwner'] = valid_owners[0]
        # else:
        #     print(valid_owners[0]['reportingOwnerId']['rptOwnerName'])
        #     data_o['reportingOwner'] = valid_owners[0]

    t_list = []
    valid_codes = ['A', 'P', 'S']
    for transaction in non_deriv:
        code = transaction['transactionCoding']['transactionCode']
        # Skip transactions not purchases, sales, grants
        if code not in valid_codes:
            continue
        date = transaction['transactionDate']['value']
        if ':' in date:
            date = '-'.join(date.split('-')[:-1])

        did_buy = transaction['transactionAmounts']['transactionAcquiredDisposedCode']['value'] == 'A'
        amount = float(transaction['transactionAmounts']['transactionShares']['value'])
        price = transaction['transactionAmounts']['transactionPricePerShare'].get('value', 0)
        price_per_share_footnotes = []
        if transaction['transactionAmounts']['transactionPricePerShare'].get('footnoteId'):
            actual_footnote = transaction['transactionAmounts']['transactionPricePerShare']['footnoteId']
            if isinstance(actual_footnote, OrderedDict):
                actual_footnote = [actual_footnote]
            actual_footnote = [f['@id'] for f in actual_footnote]
            all_footnote = data_o['footnotes']['footnote']
            if isinstance(all_footnote, OrderedDict):
                all_footnote = [all_footnote]
            for possible_footnote in all_footnote:
                if possible_footnote['@id'] in actual_footnote:
                    price_per_share_footnotes.append(possible_footnote['#text'])
        transaction_share_footnotes = []
        if transaction['transactionAmounts']['transactionShares'].get('footnoteId'):
            actual_footnote = transaction['transactionAmounts']['transactionShares']['footnoteId']
            if isinstance(actual_footnote, OrderedDict):
                actual_footnote = [actual_footnote]
            actual_footnote = [f['@id'] for f in actual_footnote]
            all_footnote = data_o['footnotes']['footnote']
            if isinstance(all_footnote, OrderedDict):
                all_footnote = [all_footnote]
            for possible_footnote in all_footnote:
                if possible_footnote['@id'] in actual_footnote:
                    transaction_share_footnotes.append(possible_footnote['#text'])
        
        post_amount = float(transaction['postTransactionAmounts']['sharesOwnedFollowingTransaction']['value'])

        # mark 10b5-1 plans
        combined = ('\n'.join(price_per_share_footnotes) + '\n'.join(transaction_share_footnotes))

        code = get_informative_code(combined, code) 
        t_list.append({
            'date': date,
            'amount': amount,
            'price': float(price),
            'code': code,
            'addedStock': did_buy,
            'priceFootnotes': price_per_share_footnotes,
            'amountFootnotes': transaction_share_footnotes,
            'amountAfter': post_amount,
        })
    if len(t_list) == 0:
        return None
    final_dict = {
        'company': issuer,
        'filers': all_owners,
        'transactions': t_list
    }
    return final_dict
def attemptXML(file_contents):
    xml_regex = re.compile('<XML>(.*)</XML>', flags=re.DOTALL) # [/s/S]*
    xml_doc = re.search(xml_regex, file_contents)
    if not xml_doc:
        return None
    return xml_doc.group(1).strip()
def batch(iterable, n):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]

async def wait_for_download_async(inputs, batch_num):


    """Asynchronously download links into files using rate limit."""
    async def get_xml_link(link, session):
        index_link = base + '/Archives/' + link

        # Get Form 4 Link
        async with session.get(index_link) as response:
            new_link, filing_date = form_4(await response.read())
            if new_link is None or filing_date is None:
                print('ERROR', index_link)
                print(new_link, filing_date)
                raise ValueError()
        # Download Form 4
        async with session.get(base + new_link) as resp2:

            file_contents = await resp2.read()
            if new_link.endswith('txt'):
                file_contents = attemptXML(file_contents.decode('utf-8'))
            if file_contents is None:
                raise IndexError()
            try:
                form_4_details = extract_relevant(xmltodict.parse(file_contents))
            except (KeyError, IndexError, xml.parsers.expat.ExpatError) as e:
                print('Abnormal Details...', index_link, base+new_link)
                print(e)
                return 0
            if form_4_details is not None:
                form_4_details['date_filed']=filing_date
                await sync_to_async(create_django_models, thread_sensitive=True)(form_4_details, index_link, base + new_link)
                return 1
            return 0
    client = ClientSession(connector=TCPConnector(limit=10), headers={'Connection': 'keep-alive'})
    async with client:
        total = 0
        for group_of_5 in tqdm.tqdm(batch(inputs, 5), total=len(inputs)//5, unit_scale=5, desc=f"Batch {batch_num+1}"):
            start = time.monotonic()
            tasks = [get_xml_link(link, client) for link in group_of_5]
            total += sum(await asyncio.gather(*tasks))
            runtime = time.monotonic() - start
            if runtime < 1:
                await asyncio.sleep(1 - runtime)
def form_4(data):
    # data = requests.get(base+index).content
    html_tree = html.fromstring(data)
    lines = html_tree.xpath('/html/body/div[4]/div[2]/div/table/tr[.//td[text() = "4"]]//td[3]//a')
    results =  {l.xpath('./text()')[0].split('.')[1]: l.attrib['href'] for l in lines}
    try:
        date = html_tree.xpath('/html/body/div[4]/div[1]/div[2]/div[1]/div[2]/text()')[0]
    except IndexError:
        return ((None, None))
    if len(results) == 0:
        full_doc = html_tree.xpath('/html/body/div[4]/div[2]/div/table/tr[.//td[text() = "Complete submission text file"]]//td[3]//a')[0]
        return (full_doc.attrib['href'], date)
    # print(results)
    return (results.get('xml', None), date)

if __name__ == '__main__':
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stocks.settings")
    django.setup()
    from form4.models import *

    data_frame = pandas.read_csv('../out/form_4.tsv', sep='|')

    s = timer()
    loop = asyncio.get_event_loop()
    # 188

    start_batch = 1709
    for i, b in enumerate(batch(data_frame['INDEX'], 1000)):
        if i+1 < start_batch:
            continue
        while True:
            try:
                results = loop.run_until_complete(wait_for_download_async(b, i))
                break
            except ValueError:
                print("hit rate limit.")
                exit()
    loop.close()
