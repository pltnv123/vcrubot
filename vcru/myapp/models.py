from django.db import models

class MakeResult(models.Model):
    task_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, default='pending')  # Возможные значения: pending, completed, error
    result_data = models.JSONField(null=True, blank=True)  # Сохраняем полученный JSON с данными
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Task {self.task_id} - {self.status}"
