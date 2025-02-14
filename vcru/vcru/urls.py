from django.contrib import admin
from django.urls import path
from myapp.views import start_task  # импорт функции

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', start_task),  # Этот путь теперь будет обрабатывать корневой URL
    path('start_task/', start_task, name='start_task'),
]