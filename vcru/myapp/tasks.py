import os
import random
import pyperclip
import keyboard
import json
from PIL import Image
from celery import shared_task
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pyautogui
import requests
import time
import logging

from .models import MakeResult

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

# Пути для загрузки изображений (НЕ ИЗМЕНЯТЬ)
file_path1 = r"C:\ТИПО Д\prjct\vcrubot\vcru\downloaded_image_from_webhook_1.png"
file_path2 = r"C:\ТИПО Д\prjct\vcrubot\vcru\downloaded_image_from_webhook_2.png"

def get_webhook_data_long_polling(webhook_url, timeout=600):
    """
    Отправляет HTTP-запрос с long polling к вебхуку.
    Если сервер возвращает "Accepted", продолжает считывание данных, пока не будет получен валидный JSON.
    """
    try:
        response = requests.get(webhook_url, timeout=timeout, stream=True)
        response.encoding = 'utf-8'
        if response.status_code != 200:
            print(f"Ошибка: статус {response.status_code}")
            return None
        accumulated = ""
        for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
            if chunk:
                accumulated += chunk
                if accumulated.strip().lower() != "accepted":
                    try:
                        data = json.loads(accumulated)
                        print(f"Данные успешно получены: {data}")
                        return data
                    except json.JSONDecodeError:
                        continue
        print("Соединение завершено, но не получен валидный JSON.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Ошибка запроса: {e}")
        return None

def download_image_from_webhook_1(image_url):
    if not image_url:
        print("URL изображения 1 не найден.")
        return False
    try:
        if os.path.exists(file_path1):
            os.remove(file_path1)
        response = requests.get(image_url, stream=True)
        if response.status_code == 200:
            with open(file_path1, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print(f"Изображение 1 загружено: {file_path1}")
            try:
                with Image.open(file_path1) as img:
                    img.verify()
                return True
            except Exception as img_error:
                print(f"Ошибка верификации изображения 1: {img_error}")
                return False
        else:
            print(f"Ошибка загрузки изображения 1: {response.status_code}")
            return False
    except Exception as e:
        print(f"Ошибка загрузки: {e}")
        return False

def download_image_from_webhook_2(image_url):
    if not image_url:
        print("URL изображения 2 не найден.")
        return False
    try:
        if os.path.exists(file_path2):
            os.remove(file_path2)
        response = requests.get(image_url, stream=True)
        if response.status_code == 200:
            with open(file_path2, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print(f"Изображение 2 загружено: {file_path2}")
            try:
                with Image.open(file_path2) as img:
                    img.verify()
                return True
            except Exception as img_error:
                print(f"Ошибка верификации изображения 2: {img_error}")
                return False
        else:
            print(f"Ошибка загрузки изображения 2: {response.status_code}")
            return False
    except Exception as e:
        print(f"Ошибка загрузки : {e}")
        return False

@shared_task(bind=True)
def run_selenium_task(self, webhook_url, username, password, task_id):
    """
    Выполняет Selenium-задачу, ожидает результат в MakeResult по task_id, затем использует полученные данные.
    """
    driver = None
    try:
        logging.info("Начало выполнения Selenium задачи.")
        if not all([webhook_url, username, password, task_id]):
            raise ValueError("Один из параметров отсутствует.")
        logging.info(f"Используем task_id: {task_id}")

        # Ожидание результата от Make.com (до 10 минут)
        max_wait = 600
        interval = 10
        elapsed = 0
        make_result = None
        while elapsed < max_wait:
            try:
                make_result = MakeResult.objects.get(task_id=task_id)
                if make_result.status == 'completed' and make_result.result_data:
                    break
            except MakeResult.DoesNotExist:
                pass
            time.sleep(interval)
            elapsed += interval

        if not make_result or make_result.status != 'completed':
            raise Exception("Не получен результат от Make.com в отведенное время.")

        data = make_result.result_data
        glav_title = data.get("glav_title", "Без заголовка")
        image_url1 = data.get("picture1")
        image_url2 = data.get("picture2")
        logging.info(f"Получены данные: glav_title={glav_title}, image_url1={image_url1}, image_url2={image_url2}")

        if image_url1:
            if not download_image_from_webhook_1(image_url1):
                logging.info("Не удалось загрузить изображение 1. Продолжаем без него.")
        if image_url2:
            if not download_image_from_webhook_2(image_url2):
                logging.info("Не удалось загрузить изображение 2. Продолжаем без него.")

        # Запуск Selenium
        service = Service(ChromeDriverManager().install())
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36")
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            "source": """
            Object.defineProperty(navigator, 'webdriver', {
              get: () => undefined
            });
            """
        })

        def move_mouse_randomly():
            screen_width, screen_height = pyautogui.size()
            x = random.randint(0, screen_width)
            y = random.randint(0, screen_height)
            duration = random.uniform(0.1, 0.5)
            pyautogui.moveTo(x, y, duration)

        def random_delay(min_time=1, max_time=3):
            time.sleep(random.uniform(min_time, max_time))

        try:
            driver.get("https://vc.ru/")
            time.sleep(2)

            # Вход в систему
            move_mouse_randomly()
            login_button_step1 = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div[2]/div/div[2]/div[4]/a[2]/button'))
            )
            login_button_step1.click()
            random_delay()

            move_mouse_randomly()
            login_button_step2 = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div[5]/div/div[2]/div/div[2]/button[3]'))
            )
            login_button_step2.click()
            random_delay()
            username_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="app"]/div[5]/div/div[2]/div/div[2]/form/div[1]/label/div/input'))
            )
            username_field.send_keys(username)

            move_mouse_randomly()
            password_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="app"]/div[5]/div/div[2]/div/div[2]/form/div[2]/label/div/input'))
            )
            password_field.send_keys(password)

            move_mouse_randomly()
            submit_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div[5]/div/div[2]/div/div[2]/form/button'))
            )
            submit_button.click()
            time.sleep(15)

            # Создание поста

            move_mouse_randomly()
            create_post_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div[2]/div/div[2]/div[4]/a/button'))
            )

            move_mouse_randomly()
            create_post_button.click()
            time.sleep(3)
            random_delay()

            keyboard.press_and_release('enter')
            print("Добавление картинки")
            ####КАРТИНКА

            if os.path.exists(file_path1):
                panel_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div.ce-toolbar.opened > div > span > i"))
                )
                panel_button.click()
                time.sleep(3)
                upload_image_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR,
                                                "#app > div.modal-fullpage > div > div > div > div.editor__body > div > div > div > div.ce-toolbar.opened > div > div.ce-popover.ce-toolbox.opened > div.ce-popover__content > div > li:nth-child(5) > span.ce-toolbox__item-title"))
                )
                upload_image_button.click()
                time.sleep(2)
                random_delay()
                pyperclip.copy(file_path1)
                keyboard.press_and_release('ctrl+v')
                random_delay()
                keyboard.press_and_release('enter')
                time.sleep(3)
                random_delay()
                print("Фото загружено.")

                time.sleep(3)
                random_delay()

            # Вставляем главный заголовок (название поста) в верхнее поле редактора

            move_mouse_randomly()
            content_field = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH,
                                                '//*[@id="app"]/div[5]/div/div[2]/div/div[2]/div/div/div/div[1]/div/div[3]/div/div/div/p'))
            )
            move_mouse_randomly()
            content_field.send_keys(glav_title)

            print("Главный заголовок вставлен, Enter")

            time.sleep(0.5)
            keyboard.press_and_release('tab')
            time.sleep(0.5)
            keyboard.press_and_release('tab')

            ##### content_field.click() #####
            print("ПЕРЕШЛИ НА СТРОКУ ВВОДА ТЕКСТА")
            #### pyperclip.copy(glav_title) #####

            move_mouse_randomly()
            random_delay()  #

            time.sleep(2)

            first_header = True  # Флаг для отслеживания первого заголовка

            for zag in data["zaglvk"]:
                random_delay()

                move_mouse_randomly()
                if first_header:
                    keyboard.press_and_release('tab')  # Нажимаем TAB при первом заголовке
                    random_delay()
                    move_mouse_randomly()
                    first_header = False  # Сбрасываем флаг, чтобы дальше кликать
                else:
                    header_panel = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "div.ce-toolbar.opened > div > span > i"))
                    )
                    header_panel.click()
                    random_delay()
                    move_mouse_randomly()

                header_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR,
                                                "#app > div.modal-fullpage > div > div > div > div.editor__body > div > div > div > div.ce-toolbar.opened > div > div.ce-popover.ce-toolbox.opened > div.ce-popover__content > div > li:nth-child(3) > span.ce-toolbox__item-title"))
                )
                header_button.click()
                random_delay()
                move_mouse_randomly()
                # Печатаем заголовок по символу
                keyboard.write(zag["title"], delay=0.15)
                random_delay()
                keyboard.press_and_release('enter')
                random_delay()

                # --- Подзаголовки ---
                for sub in zag["subtitles"]:
                    random_delay()
                    move_mouse_randomly()
                    sub_panel = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "div.ce-toolbar.opened > div > span > i"))
                    )
                    move_mouse_randomly()
                    sub_panel.click()
                    random_delay()
                    sub_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR,
                                                    "#app > div.modal-fullpage > div > div > div > div.editor__body > div > div > div > div.ce-toolbar.opened > div > div.ce-popover.ce-toolbox.opened > div.ce-popover__content > div > li:nth-child(4) > span.ce-toolbox__item-title"))
                    )
                    move_mouse_randomly()
                    sub_button.click()
                    random_delay()

                    # Печатаем подзаголовок по символу
                    keyboard.write(sub["subtitle"], delay=0.15)
                    random_delay()
                    keyboard.press_and_release('enter')
                    random_delay()

                    # --- Основной текст ---
                    first_text = True
                    for text in sub["texts"]:
                        random_delay()
                        move_mouse_randomly()
                        if first_text:
                            text_panel = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.ce-toolbar.opened > div > span > i"))
                            )
                            move_mouse_randomly()
                            text_panel.click()
                            random_delay()
                            text_button = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR,
                                                            "#app > div.modal-fullpage > div > div > div > div.editor__body > div > div > div > div.ce-toolbar.opened > div > div.ce-popover.ce-toolbox.opened > div.ce-popover__content > div > li:nth-child(2) > span.ce-toolbox__item-title"))
                            )
                            move_mouse_randomly()
                            text_button.click()
                            random_delay()
                            # Набираем первый абзац текста по символу
                            keyboard.write(text, delay=0.15)
                            random_delay()
                            keyboard.press_and_release('enter')
                            random_delay()
                            move_mouse_randomly()
                            first_text = False
                        else:
                            # Набираем последующие абзацы текста по символу
                            keyboard.write(text, delay=0.15)
                            random_delay()
                            keyboard.press_and_release('enter')
                            random_delay()
                            move_mouse_randomly()

            keyboard.press_and_release('enter')

            # --- СДЕЛАЮ ПОТОМ ДОБАВЛЕНИЕ ВТОРОГО ИЗОБРАЖЕНИЯ ---
            if os.path.exists(file_path2):
                panel_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div.ce-toolbar.opened > div > span > i"))
                )
                panel_button.click()
                time.sleep(3)
                upload_image_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR,
                                                "#app > div.modal-fullpage > div > div > div > div.editor__body > div > div > div > div.ce-toolbar.opened > div > div.ce-popover.ce-toolbox.opened > div.ce-popover__content > div > li:nth-child(5) > span.ce-toolbox__item-title"))
                )
                upload_image_button.click()
                time.sleep(5)
                pyperclip.copy(file_path2)
                keyboard.press_and_release('ctrl+v')
                time.sleep(2)
                keyboard.press_and_release('enter')
                time.sleep(5)
                print("Фото загружено.")

                time.sleep(5)

                keyboard.press_and_release('tab')
                time.sleep(1)

                keyboard.press_and_release('enter')
                time.sleep(1)
                keyboard.press_and_release('enter')

            print("enter")
            print("Пост опубликован!")
            time.sleep(150)
            response = requests.post(webhook_url, json={"status": "done"})
            print(f"Webhook ответ: {response.status_code}")
            return "Пост успешно опубликован!"


        finally:
            if driver:
                driver.quit()
                logging.info("WebDriver завершён.")


    except Exception as e:
        print(f"Ошибка: {e}")
        return str(e)
