import os
import json
import requests
import uuid
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError
from dotenv import load_dotenv
from .tasks import run_selenium_task
from .models import MakeResult

# Загружаем переменные окружения
load_dotenv()

# Функция для отправки данных в Make.com (webhook)
def send_to_make(data):
    webhook_url = "https://hook.eu2.make.com/q20tb4ip6m24jxzldaksu955hgcfuejy"
    response = requests.post(webhook_url, json=data)
    return response.status_code

def start_task(request):
    """
    Обрабатывает GET-запрос для запуска задачи.
    Генерирует уникальный task_id, сохраняет его в базе и запускает Celery-задачу.
    Затем отправляет task_id и данные на Make.com.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Метод не поддерживается, используйте GET"}, status=405)

    # Получаем конфиденциальные данные
    username = os.getenv("USERNAMES")
    password = os.getenv("PASSWORD")
    webhook_url = "https://hook.eu2.make.com/q20tb4ip6m24jxzldaksu955hgcfuejy"

    # Генерируем уникальный task_id
    task_id = str(uuid.uuid4())

    # Создаем запись в базе данных до запуска задачи
    try:
        MakeResult.objects.create(
            task_id=task_id,
            status='pending'
        )
        print(f"Task record created with task_id: {task_id}")
    except IntegrityError:
        return JsonResponse({"error": "Task ID уже существует в базе данных"}, status=400)

    # Запускаем Celery-задачу, передавая task_id как аргумент и используя его в качестве идентификатора задачи
    task = run_selenium_task.apply_async(
        args=(webhook_url, username, password, task_id),
        task_id=task_id
    )

    # Формируем данные для отправки в Make.com
    data_to_send = {
        "task_id": task_id,
        "username": username,
        "message": "Task started successfully",
    }

    # Отправляем данные на вебхук Make.com
    status_code = send_to_make(data_to_send)
    if status_code != 200:
        return JsonResponse({"error": "Failed to send data to Make.com"}, status=500)

    return JsonResponse({"task_id": task_id, "status": "Task started"})

@csrf_exempt
def receive_result(request):
    """
    Callback-вьюшка для получения результата от Make.com.
    Ожидается POST-запрос с JSON:
      {
         "task_id": "уникальный_идентификатор",
         "result": { ... }  // итоговый JSON с данными
      }
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            task_id = data.get('task_id')
            result = data.get('result')

            if not task_id or result is None:
                return JsonResponse({'error': 'task_id и result обязательны'}, status=400)

            # Обновляем запись в базе данных по task_id
            obj = MakeResult.objects.get(task_id=task_id)
            obj.status = 'completed'
            obj.result_data = result
            obj.save()

            return JsonResponse({'status': 'Result received'})
        except MakeResult.DoesNotExist:
            return JsonResponse({'error': 'Задача не найдена'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Метод не поддерживается'}, status=405)
