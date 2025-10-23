import os
import requests
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime, time, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from playwright.async_api import async_playwright, TimeoutError
from asgiref.sync import sync_to_async
from openai import AsyncOpenAI, APIError 

from establishments.models import Establishment
from promotions.models import Promotion, Media


OPENROUTER_API_KEY = "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"
# AI_MODEL_NAME = "openai/gpt-oss-20b:free" # Старая модель
AI_MODEL_NAME = "mistralai/mistral-7b-instruct:free" # <-- Пробуем другую модель
ai_client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)

def parse_date(date_string):
    if not date_string: return None
    date_part = date_string.split(',')[0].strip()
    formats = ['%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%d', '%m/%d/%Y']
    for fmt in formats:
        try: return datetime.strptime(date_part, fmt)
        except ValueError: continue
    return None
@sync_to_async
def fetch_profile_data_sync(username, output_folder):
    profile_url = f"https://www.instagram.com/{username}/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    data = {"Username": username, "FullName": "Не найдено", "Biography": "Не найдено", "Followers": "Не найдено", "PostsCount": "Не найдено"}
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
                    if 'Followers' in part or 'подписчиков' in part: data["Followers"] = part.strip()
                    elif 'Posts' in part or 'публикаций' in part: data["PostsCount"] = part.strip()
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
             data["Biography"] = meta_desc['content'].split('-')[0].strip()
        description_path = os.path.join(output_folder, 'Описание.txt')
        with open(description_path, 'w', encoding='utf-8') as f:
            f.write(f"Имя пользователя: {data['Username']}\nПолное имя: {data['FullName']}\n")
            f.write(f"Подписчики: {data['Followers']}\nКол-во постов: {data['PostsCount']}\n\nОписание профиля:\n{data['Biography']}\n")
        print(f"Файл 'Описание.txt' успешно создан.")
    except requests.exceptions.RequestException as e:
        print(f"Не удалось получить данные с Instagram напрямую: {e}")

async def find_and_save_promotions(page, content_type, date_range, establishment, base_folder):
    print(f"\nНачинаю работать с разделом: {content_type.upper()}")
    start_date, end_date = date_range
    try: await page.locator(f'button:has-text("{content_type}")').click()
    except Exception: return 0
    if content_type == 'stories': await page.wait_for_timeout(8000)
    else: await page.wait_for_timeout(5000)
    item_selector = "li.profile-media-list__item"
    while True:
        all_items = await page.locator(item_selector).all()
        if not all_items: break
        last_item = all_items[-1]
        date_element = last_item.locator("p.media-content__meta-time")
        if start_date and await date_element.count() > 0:
            date_title = await date_element.get_attribute('title')
            last_item_date = parse_date(date_title)
            if last_item_date and last_item_date < start_date: break
        await last_item.scroll_into_view_if_needed()
        await page.wait_for_timeout(2500)
        if await page.locator(item_selector).count() == len(all_items): break
    all_items = await page.locator(item_selector).all()
    print(f"Всего найдено {len(all_items)}. Начинаю фильтрацию по дате ({start_date.strftime('%d.%m')} - {end_date.strftime('%d.%m')}) и анализ ИИ ({AI_MODEL_NAME}).")
    promotions_found_counter = 0
    for i, item in enumerate(all_items):
        date_element = item.locator("p.media-content__meta-time")
        if await date_element.count() == 0: continue
        date_title = await date_element.get_attribute('title')
        item_date = parse_date(date_title)
        if not item_date or not (start_date <= item_date <= end_date): continue
        print(f"  + {content_type.capitalize()} от {item_date.strftime('%d.%m.%Y')} ПОДХОДИТ по дате.")
        text_element = item.locator("p.media-content__caption")
        if await text_element.count() == 0: text_element = item.locator(".media-content__text")
        post_text = await text_element.inner_text() if await text_element.count() > 0 else ""
        if not post_text.strip():
            print(f"    - Текст отсутствует. Пропускаю.")
            continue
        print(f"    ? Анализирую текст с помощью ИИ: '{post_text[:70].strip()}...'")
        is_promotion = False
        try:
            prompt = (f"Текст из Instagram: {post_text}\n\n"
                      f"Вопрос: Этот текст описывает акцию, скидку, распродажу, розыгрыш или спецпредложение? "
                      f"Ответь только 'да' или 'нет'.")
            completion = await ai_client.chat.completions.create(
                model=AI_MODEL_NAME, messages=[{"role": "user", "content": prompt}],
                max_tokens=10, 
                temperature=0.1
            )

            print(f"    DEBUG AI Response Object: {completion}")
            
            ai_response = completion.choices[0].message.content.strip().lower() if completion.choices else ""
            
            print(f"    > Ответ ИИ: '{ai_response}'")
            if 'да' in ai_response: is_promotion = True
            
        except APIError as e:
            print(f"    ! Ошибка API OpenRouter: {e}. Пропускаю пост.")
            continue
        except Exception as e:
            print(f"    ! Общая ошибка при вызове ИИ: {e}. Пропускаю пост.")
            continue
        if not is_promotion:
            print(f"    - ИИ считает, что это НЕ акция. Пропускаю.")
            continue
        print(f"    АКЦИЯ ПОДТВЕРЖДЕНА ИИ!")
        button = item.locator("a.button__download")
        if await button.count() == 0: continue
        create_promo_task = sync_to_async(Promotion.objects.create, thread_sensitive=True)
        new_promo = await create_promo_task(establishment=establishment, raw_text=post_text, status='moderation')
        promotions_found_counter += 1
        download_url = await button.get_attribute('href')
        if download_url:
            download_task = sync_to_async(requests.get, thread_sensitive=True)
            try:
                if download_url.startswith('/get'): download_url = f"https://media.storiesig.info{download_url}"
                response = await download_task(download_url)
                response.raise_for_status()
                is_video = await item.locator(".tags__item--video").count() > 0
                default_ext = ".mp4" if is_video else ".jpg"
                folder_name = 'Stories' if content_type == 'stories' else 'Posts'
                file_name = f"promo_{new_promo.id}_{i+1}{default_ext}"
                relative_path = os.path.join(str(establishment.city.country.name), str(establishment.city.name), establishment.instagram_url.strip('/').split('/')[-1], datetime.now().strftime('%Y-%m-%d'), folder_name, file_name)
                full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'wb') as f: f.write(response.content)
                create_media_task = sync_to_async(Media.objects.create, thread_sensitive=True)
                await create_media_task(promotion=new_promo, file_path=relative_path, file_type='video' if is_video else 'image')
                print(f"      - Медиафайл ({folder_name}) сохранен.")
            except requests.exceptions.RequestException as e: print(f"      Не смог скачать файл: {e}")
    return promotions_found_counter

class Command(BaseCommand):
    help = 'Запускает парсинг аккаунтов Instagram для сбора акций за последние 7 дней'
    def add_arguments(self, parser):
        parser.add_argument('account_id', nargs='?', type=int, help='ID конкретного заведения для парсинга')
    def handle(self, *args, **kwargs):
        self.today = datetime.now()
        self.end_date = datetime.combine(self.today, time.max)
        self.start_date = self.end_date - timedelta(days=7)
        account_id = kwargs.get('account_id')
        asyncio.run(self.async_handle(account_id))
    async def async_handle(self, account_id):
        if account_id:
            query = Establishment.objects.select_related('city__country').filter(pk=account_id)
        else:
            query = Establishment.objects.select_related('city__country').all()
        get_establishments = sync_to_async(list, thread_sensitive=True)
        establishments = await get_establishments(query)
        if not establishments:
            self.stdout.write(self.style.WARNING('Не найдено заведений для парсинга.'))
            return
        self.stdout.write(f"Начинаем парсинг с {self.start_date.strftime('%Y-%m-%d')} по {self.end_date.strftime('%Y-%m-%d')}...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            try:
                await page.goto("https://storiesig.info/en/")
                for establishment in establishments:
                    username = establishment.instagram_url.strip('/').split('/')[-1]
                    self.stdout.write(self.style.MIGRATE_HEADING(f"\n--- Работаю с профилем: {username} ---"))
                    base_folder = os.path.join(settings.MEDIA_ROOT, str(establishment.city.country.name), str(establishment.city.name), username, self.today.strftime('%Y-%m-%d')) # Папка для Описания
                    os.makedirs(base_folder, exist_ok=True)
                    await fetch_profile_data_sync(username, base_folder)
                    self.stdout.write("Шаг 2: Ищу профиль на StoriesIG...")
                    await page.locator("input.search.search-form__input").fill(username)
                    try:
                        async with context.expect_page(timeout=5000) as new_page_info:
                            await page.locator("button.search-form__button").click()
                        new_page = await new_page_info.value
                        await new_page.close()
                    except TimeoutError:
                        await page.locator("button.search-form__button").click()
                    try:
                        await page.wait_for_selector("div.search-result", timeout=30000)
                        self.stdout.write("Профиль найден, начинаю поиск акций.")
                    except TimeoutError:
                        self.stdout.write(self.style.ERROR(f"Не удалось найти профиль {username}."))
                        await page.goto("https://storiesig.info/en/")
                        continue
                    posts_promo_count = await find_and_save_promotions(page, 'posts', (self.start_date, self.end_date), establishment, base_folder)
                    stories_promo_count = await find_and_save_promotions(page, 'stories', (self.start_date, self.end_date), establishment, base_folder)
                    message = f"Готово для {username}. Найдено акций: {posts_promo_count} (посты), {stories_promo_count} (сторис)."
                    self.stdout.write(self.style.SUCCESS(message))
                    await page.goto("https://storiesig.info/en/")
            finally:
                await browser.close()
                self.stdout.write(self.style.SUCCESS('\nПарсинг всех заведений успешно завершен!'))