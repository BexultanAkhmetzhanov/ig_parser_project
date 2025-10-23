import os
import requests
import json
from bs4 import BeautifulSoup
from datetime import datetime
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from playwright.sync_api import sync_playwright, TimeoutError

def parse_date(date_string):
    date_part = date_string.split(',')[0].strip()
    formats = ['%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%d', '%m/%d/%Y']
    for fmt in formats:
        try:
            return datetime.strptime(date_part, fmt)
        except ValueError:
            continue
    return None

def fetch_profile_data(username, output_folder):
    profile_url = f"https://www.instagram.com/{username}/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    data = {
        "Username": username,
        "FullName": "Не найдено",
        "Biography": "Не найдено",
        "Followers": "Не найдено",
        "Following": "Не найдено",
        "PostsCount": "Не найдено",
    }
    
    try:
        response = requests.get(profile_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        og_description = soup.find('meta', property='og:description')
        if og_description and og_description.get('content'):
            desc = og_description['content']
            data["FullName"] = desc.split('•')[0].strip()
            
            if 'Followers' in desc or 'подписчиков' in desc:
                parts = desc.split(',')
                for part in parts:
                    if 'Followers' in part or 'подписчиков' in part:
                         data["Followers"] = part.strip()
                    elif 'Posts' in part or 'публикаций' in part:
                         data["PostsCount"] = part.strip()
            
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
             data["Biography"] = meta_desc['content'].split('-')[0].strip()

        description_path = os.path.join(output_folder, 'Описание.txt')
        with open(description_path, 'w', encoding='utf-8') as f:
            f.write(f"Имя пользователя: {data['Username']}\n")
            f.write(f"Полное имя: {data['FullName']}\n")
            f.write(f"Подписчики: {data['Followers']}\n")
            f.write(f"Подписки: {data['Following']}\n")
            f.write(f"Кол-во постов: {data['PostsCount']}\n")
            f.write(f"\nОписание профиля:\n{data['Biography']}\n")
            
        print(f"Файл 'Описание.txt' успешно создан.")
        
    except requests.exceptions.RequestException as e:
        print(f"Не удалось получить данные с Instagram напрямую: {e}")
        description_path = os.path.join(output_folder, 'Описание.txt')
        with open(description_path, 'w', encoding='utf-8') as f:
            f.write("Не удалось получить полное описание профиля (Подписчики/Биография) из-за блокировки Instagram.\n")


def download_media(page, content_type, date_range, folder):
    print(f"\nНачинаю работать с разделом: {content_type.upper()}")
    start_date, end_date = date_range

    try:
        page.locator(f'button:has-text("{content_type}")').click()
    except Exception:
        print(f"Не нашел вкладку '{content_type}'.")
        return 0

    if content_type == 'stories':
        page.wait_for_timeout(8000)
    else:
        page.wait_for_timeout(3000)

    item_selector = "li.profile-media-list__item"
    
    while True:
        all_items = page.locator(item_selector).all()
        count_before = len(all_items)
        
        if count_before == 0:
            break
        
        last_item = all_items[-1]
        date_element = last_item.locator("p.media-content__meta-time")
        if start_date and date_element.count() > 0:
            date_title = date_element.get_attribute('title')
            last_item_date = parse_date(date_title)
            
            if last_item_date:
                print(f"Найдено {count_before} постов. Последний пост от {last_item_date.strftime('%d.%m.%Y')}.")
                if last_item_date < start_date:
                    print("  - Этот пост старше начальной даты. Останавливаю прокрутку.")
                    break
            else:
                 print(f"Найдено {count_before} постов. Прокручиваю дальше (не удалось прочитать дату).")
        else:
             print(f"Найдено {count_before} постов. Прокручиваю дальше...")

        last_item.scroll_into_view_if_needed()
        page.wait_for_timeout(2500)
        
        count_after = page.locator(item_selector).count()
        if count_after == count_before:
            print("Больше ничего не загрузилось, заканчиваю скролл.")
            break
            
    all_items = page.locator(item_selector).all()
    print(f"Всего найдено {len(all_items)}. Начинаю фильтрацию и скачивание.")
    
    download_counter = 0
    for i, item in enumerate(all_items):
        date_element = item.locator("p.media-content__meta-time")
        
        if date_element.count() > 0:
            date_title = date_element.get_attribute('title')
            item_date = parse_date(date_title)
            
            if item_date:
                date_str = item_date.strftime('%d.%m.%Y')
                
                if start_date and item_date < start_date:
                    print(f"  - Пропускаю пост от {date_str} (слишком старый)")
                    continue
                if end_date and item_date > end_date:
                    print(f"  - Пропускаю пост от {date_str} (слишком новый)")
                    continue
                
                print(f"  + Пост от {date_str} ПОДХОДИТ по дате.")
            else:
                print(f"  - Не смог прочитать дату поста ({date_title}). Пропускаю, чтобы не качать лишнее.")
                continue

        is_video = item.locator(".tags__item--video").count() > 0
        button = item.locator("a.button__download")
        if button.count() == 0: continue

        download_url = button.get_attribute('href')
        if download_url:
            download_counter += 1
            print(f"    Качаю файл #{download_counter}...")
            try:
                if download_url.startswith('/get'):
                    download_url = f"https://media.storiesig.info{download_url}"
                
                response = requests.get(download_url)
                response.raise_for_status()

                default_ext = ".mp4" if is_video else ".jpg"
                file_name = f"media_{i+1}{default_ext}"
                if 'content-disposition' in response.headers:
                    disposition = response.headers['content-disposition']
                    for part in disposition.split(';'):
                        if 'filename=' in part:
                            file_name = part.split('=')[1].strip('"')
                            break
                
                file_path = os.path.join(folder, file_name)
                with open(file_path, 'wb') as f:
                    f.write(response.content)
            except requests.exceptions.RequestException as e:
                print(f"      Не смог скачать файл: {e}")
    
    return download_counter

class ScrapeInstagramView(APIView):
    def post(self, request, *args, **kwargs):
        profile_url = request.data.get('url')
        start_date_str = request.data.get('startDate')
        end_date_str = request.data.get('endDate')

        if not profile_url:
            return Response({"error": "Нужно вставить ссылку на профиль."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else None
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None
        except ValueError:
            return Response({"error": "Неверный формат даты. Используйте ГГГГ-ММ-ДД."}, status=status.HTTP_400_BAD_REQUEST)

        username = profile_url.strip('/').split('/')[-1]

        print(f"\nНачинаю новый поиск для {username}")
        
        try:
            with sync_playwright() as p:
                base_folder = os.path.join(settings.BASE_DIR, 'downloads', username)
                posts_folder = os.path.join(base_folder, 'Posts')
                stories_folder = os.path.join(base_folder, 'Stories')
                os.makedirs(posts_folder, exist_ok=True)
                os.makedirs(stories_folder, exist_ok=True)
                
                print("Шаг 1: Получаю описание профиля с Instagram...")
                fetch_profile_data(username, base_folder)

                browser = p.chromium.launch(headless=False)
                context = browser.new_context()
                page = context.new_page()

                page.goto("https://storiesig.info/en/")
                page.locator("input.search.search-form__input").fill(username)
                page.locator("button.search-form__button").click()

                try:
                    with context.expect_page(timeout=10000) as new_page_info:
                        new_page_info.value.close()
                except TimeoutError:
                    pass
                
                page.wait_for_selector("div.search-result", timeout=30000)
                print("Шаг 2: Профиль найден, начинаю скачивание медиа.")

                posts_count = download_media(page, 'posts', (start_date, end_date), posts_folder)
                stories_count = download_media(page, 'stories', (start_date, end_date), stories_folder)
                
                browser.close()
                
                message = f"Готово. Скачано постов: {posts_count}, сторис: {stories_count}. Описание сохранено."
                print(message)
            
            return Response({"message": message}, status=status.HTTP_200_OK)

        except Exception as e:
            error = f"Что-то пошло не так: {e}"
            print(error)
            return Response({"error": error}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)