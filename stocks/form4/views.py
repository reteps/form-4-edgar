from django.shortcuts import render
from parse_files import scrape_all_form_4
# Create your views here.

def index(request):
    task = scrape_all_form_4.delay('../out/out.csv')
    print(f'Celery Task ID: {task.task_id}')
    return render(request, 'form4/index.html', context={'task_id': task.task_id})