import os
from django.http import JsonResponse
from dotenv import load_dotenv
from .tasks import run_selenium_task

# Загружаем переменные окружения из файла .env
load_dotenv()

def start_task(request):
    # Получаем конфиденциальные данные из переменных окружения
    webhook_url = "https://hook.eu2.make.com/q20tb4ip6m24jxzldaksu955hgcfuejy"
    username = os.getenv("USERNAMES")
    # username = "dotasymphony@gmail.com"
    password = os.getenv("PASSWORD")
    # password = "Z12345678z+"

    task = run_selenium_task.delay(webhook_url, username, password)

    return JsonResponse({"task_id": task.id, "status": "Task started"})
