import os
import random
import pyperclip
import keyboard
import requests
import json
import time
from PIL import Image
from celery import shared_task
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Путь для загрузки изображений (НЕ ИЗМЕНЯТЬ)
file_path2 = r"C:\ТИПО Д\prjct\vcrubot\vcru\downloaded_image_from_webhook.png"


# Функция для получения данных из webhook
def get_webhook_data(webhook_url):
    for attempt in range(5):
        try:
            response = requests.get(webhook_url)
            response.encoding = 'utf-8'
            print(f"Ответ от webhook: {response.text}")
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"JSON получен: {data}")
                    # Извлекаем основной заголовок из ключа "glav_title"
                    main_title = data.get("glav_title", "Нет заголовка")
                    # Извлекаем заголовок первого элемента массива "zaglvk" для дополнительного использования
                    zaglvk_title = data["zaglvk"][0]["title"] if "zaglvk" in data and data["zaglvk"] else "Нет заголовка"
                    image_url = data.get("picture", "")
                    return {
                        "glav_title": main_title,       # Основной заголовок
                        "zaglvk_title": zaglvk_title,     # Заголовок из первого элемента массива zaglvk
                        "zaglvk": data.get("zaglvk", []),
                        "picture": image_url
                    }
                except json.JSONDecodeError as e:
                    print(f"Ошибка парсинга JSON: {e}")
                    return None
            else:
                print(f"Ошибка: {response.status_code}, повторная попытка...")
                time.sleep(2)
        except requests.exceptions.RequestException as e:
            print(f"Ошибка запроса: {e}")
            time.sleep(2)
    raise Exception("Не удалось получить данные из webhook после 5 попыток.")


# Функция для загрузки изображения
def download_image_from_webhook(image_url):
    if not image_url:
        print("URL изображения не найден.")
        return False
    try:
        if os.path.exists(file_path2):
            os.remove(file_path2)
        response = requests.get(image_url, stream=True)
        if response.status_code == 200:
            with open(file_path2, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print(f"Изображение загружено: {file_path2}")
            try:
                with Image.open(file_path2) as img:
                    img.verify()
                return True
            except Exception as img_error:
                print(f"Ошибка верификации изображения: {img_error}")
                return False
        else:
            print(f"Ошибка загрузки изображения: {response.status_code}")
            return False
    except Exception as e:
        print(f"Ошибка загрузки: {e}")
        return False





@shared_task(bind=True)
def run_selenium_task(self, webhook_url, username, password):
    driver = None
    try:
        data = get_webhook_data(webhook_url)
        if data is None:
            raise Exception("Ошибка получения данных из webhook.")

        # Используем основной заголовок для вставки в редактор
        glav_title = data["glav_title"]
        image_url = data.get("picture")
        if image_url:
            if not download_image_from_webhook(image_url):
                print("Не удалось загрузить изображение. Продолжаем без него.")

        # Установка ChromeDriver
        service = Service(ChromeDriverManager().install())

        # Настройка опций Chrome
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")  # Убираем флаг автоматизации
        options.add_experimental_option("excludeSwitches",
                                        ["enable-automation"])  # Убираем уведомление об управлении браузером
        options.add_experimental_option("useAutomationExtension", False)  # Отключаем стандартное расширение Selenium
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36")  # Устанавливаем реальный User-Agent

        # Запуск браузера
        driver = webdriver.Chrome(service=service, options=options)

        # Убираем navigator.webdriver
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            "source": """
            Object.defineProperty(navigator, 'webdriver', {
              get: () => undefined
            });
            """
        })

        # Функция для имитации задержек
        def random_delay(min_time=1, max_time=3):
            time.sleep(random.uniform(min_time, max_time))
        try:
            driver.get("https://vc.ru/")
            time.sleep(2)

            # Вход в систему
            login_button_step1 = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div[2]/div/div[2]/div[4]/a[2]/button'))
            )
            login_button_step1.click()
            time.sleep(2)
            login_button_step2 = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div[5]/div/div[2]/div/div[2]/button[3]'))
            )
            login_button_step2.click()
            time.sleep(2)
            username_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="app"]/div[5]/div/div[2]/div/div[2]/form/div[1]/label/div/input'))
            )
            username_field.send_keys(username)
            password_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="app"]/div[5]/div/div[2]/div/div[2]/form/div[2]/label/div/input'))
            )
            password_field.send_keys(password)
            submit_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div[5]/div/div[2]/div/div[2]/form/button'))
            )
            submit_button.click()
            time.sleep(15)

            # Создание поста
            create_post_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div[2]/div/div[2]/div[4]/a/button'))
            )
            create_post_button.click()
            time.sleep(5)
            time.sleep(2)

            keyboard.press_and_release('enter')
            print("Добавление картинки")
            ####КАРТИНКА

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


            # Вставляем главный заголовок (название поста) в верхнее поле редактора
            content_field = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH,
                                                '//*[@id="app"]/div[5]/div/div[2]/div/div[2]/div/div/div/div[1]/div/div[3]/div/div/div/p'))
            )
            content_field.send_keys(glav_title)


            print("Главный заголовок вставлен, Enter")

            time.sleep(0.5)
            keyboard.press_and_release('tab')
            time.sleep(0.5)
            keyboard.press_and_release('tab')

            ##### content_field.click() #####
            print("ПЕРЕШЛИ НА СТРОКУ ВВОДА ТЕКСТА")
            #### pyperclip.copy(glav_title) #####

            time.sleep(1)
            # keyboard.press_and_release('ctrl+v')
            # # time.sleep(2)
            # keyboard.press_and_release('enter')


            time.sleep(2)


            # Обработка каждого заголовка из data["zaglvk"]
            #

            # ПЕРВАЯ ИТЕРАЦИЯ TAB И СРАБОТАЕТ !!!!!!!!!!!!
            first_header = True  # Флаг для отслеживания первого заголовка

            for zag in data["zaglvk"]:
                time.sleep(1)

                if first_header:
                    keyboard.press_and_release('tab')  # Нажимаем TAB при первом заголовке
                    time.sleep(2)
                    first_header = False  # Сбрасываем флаг, чтобы дальше кликать
                else:
                    header_panel = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "div.ce-toolbar.opened > div > span > i"))
                    )
                    header_panel.click()
                    time.sleep(2)

                header_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR,
                                                "#app > div.modal-fullpage > div > div > div > div.editor__body > div > div > div > div.ce-toolbar.opened > div > div.ce-popover.ce-toolbox.opened > div.ce-popover__content > div > li:nth-child(3) > span.ce-toolbox__item-title"))
                )
                header_button.click()
                time.sleep(2)

                # Печатаем заголовок по символу
                keyboard.write(zag["title"], delay=0.15)
                time.sleep(2)
                keyboard.press_and_release('enter')
                time.sleep(2)
                # --- Подзаголовки ---
                for sub in zag["subtitles"]:
                    time.sleep(1)
                    sub_panel = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "div.ce-toolbar.opened > div > span > i"))
                    )
                    sub_panel.click()
                    time.sleep(2)
                    sub_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR,
                                                    "#app > div.modal-fullpage > div > div > div > div.editor__body > div > div > div > div.ce-toolbar.opened > div > div.ce-popover.ce-toolbox.opened > div.ce-popover__content > div > li:nth-child(4) > span.ce-toolbox__item-title"))
                    )
                    sub_button.click()
                    time.sleep(2)
                    # Печатаем подзаголовок по символу
                    keyboard.write(sub["subtitle"], delay=0.15)
                    time.sleep(2)
                    keyboard.press_and_release('enter')
                    time.sleep(2)

                    # --- Основной текст ---
                    first_text = True
                    for text in sub["texts"]:
                        time.sleep(1)
                        if first_text:
                            text_panel = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.ce-toolbar.opened > div > span > i"))
                            )
                            text_panel.click()
                            time.sleep(2)
                            text_button = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR,
                                                            "#app > div.modal-fullpage > div > div > div > div.editor__body > div > div > div > div.ce-toolbar.opened > div > div.ce-popover.ce-toolbox.opened > div.ce-popover__content > div > li:nth-child(2) > span.ce-toolbox__item-title"))
                            )
                            text_button.click()
                            time.sleep(2)
                            # Набираем первый абзац текста по символу
                            keyboard.write(text, delay=0.15)
                            time.sleep(2)
                            keyboard.press_and_release('enter')
                            time.sleep(2)
                            first_text = False
                        else:
                            # Набираем последующие абзацы текста по символу
                            keyboard.write(text, delay=0.15)
                            time.sleep(2)
                            keyboard.press_and_release('enter')
                            time.sleep(2)

            keyboard.press_and_release('enter')

            # --- СДЕЛАЮ ПОТОМ ДОБАВЛЕНИЕ ВТОРОГО ИЗОБРАЖЕНИЯ ---
            # if os.path.exists(file_path2):
            #     panel_button = WebDriverWait(driver, 10).until(
            #         EC.element_to_be_clickable((By.CSS_SELECTOR, "div.ce-toolbar.opened > div > span > i"))
            #     )
            #     panel_button.click()
            #     time.sleep(3)
            #     upload_image_button = WebDriverWait(driver, 10).until(
            #         EC.element_to_be_clickable((By.CSS_SELECTOR,
            #                                     "#app > div.modal-fullpage > div > div > div > div.editor__body > div > div > div > div.ce-toolbar.opened > div > div.ce-popover.ce-toolbox.opened > div.ce-popover__content > div > li:nth-child(5) > span.ce-toolbox__item-title"))
            #     )
            #     upload_image_button.click()
            #     time.sleep(5)
            #     pyperclip.copy(file_path2)
            #     keyboard.press_and_release('ctrl+v')
            #     time.sleep(2)
            #     keyboard.press_and_release('enter')
            #     time.sleep(5)
            #     print("Фото загружено.")
            #
            #     time.sleep(5)
            #     keyboard.press_and_release('tab')
            #     time.sleep(1)
            #     keyboard.press_and_release('enter')
            #     time.sleep(1)
            #     keyboard.press_and_release('enter')
            #


            print("enter")
            print("Пост опубликован!")
            time.sleep(300)
            response = requests.post(webhook_url, json={"status": "done"})
            print(f"Webhook ответ: {response.status_code}")
            return "Пост успешно опубликован!"

        finally:
            if driver:
                driver.quit()

    except Exception as e:
        print(f"Ошибка: {e}")
        return str(e)