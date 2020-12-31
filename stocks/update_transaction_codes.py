import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stocks.settings")
import django
import tqdm
django.setup()
from form4.models import *
from parse_files import get_informative_code

i = 0
for o in tqdm.tqdm(Transaction.objects.all()):
    combined = ''
    for note in o.filingnote_set.all():
        combined += note.text + '\n'
    code = get_informative_code(combined, o.code)
    if code != o.code:
        i+=1
        o.code = code
        o.save()
print(i)