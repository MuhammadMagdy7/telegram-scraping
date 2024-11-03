# telegram_scraper.py
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import logging
import re
import pandas as pd
import csv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_telegram_url(url):
  pattern = r'^https://t\.me/s/[a-zA-Z0-9_]+$'
  return re.match(pattern, url) is not None

def scrape_telegram(url, start_date, end_date, max_posts=1000, progress_callback=None):
    logger.info(f"بدء الاستخراج من URL: {url}")
    logger.info(f"تاريخ البداية: {start_date}, تاريخ النهاية: {end_date}")
    
    data = []
    total_scraped = 0
    current_url = url
    
    while total_scraped < max_posts:
        try:
            logger.info(f"جاري جلب الصفحة: {current_url}")
            response = requests.get(current_url, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            messages = soup.select('.tgme_widget_message_wrap')
            
            if not messages:
                logger.info("لم يتم العثور على المزيد من الرسائل. إيقاف الاستخراج.")
                break
            
            for message in messages:
                text = message.select_one('.tgme_widget_message_text')
                date = message.select_one('.tgme_widget_message_date time')
                
                if text and date:
                    text_content = text.get_text(strip=True)
                    date_str = date['datetime']
                    post_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    
                    if start_date <= post_date.date() <= end_date:
                        data.append({'text': text_content, 'date': post_date})
                        total_scraped += 1
                        if progress_callback:
                            progress_callback(total_scraped, max_posts)
                    elif post_date.date() < start_date:
                        logger.info(f"تم الوصول إلى تاريخ قبل تاريخ البداية: {post_date.date()}. إيقاف الاستخراج.")
                        return data
                else:
                    logger.warning("نص أو تاريخ مفقود لرسالة")
            
            logger.info(f"تم استخراج {len(data)} رسالة حتى الآن.")
            
            if total_scraped >= max_posts:
                logger.info(f"تم الوصول إلى الحد الأقصى للمنشورات ({max_posts}). إيقاف الاستخراج.")
                break
            
            # البحث عن رابط "تحميل المزيد"
            load_more = soup.select_one('a.tme_messages_more')
            if load_more and 'href' in load_more.attrs:
                current_url = 'https://t.me' + load_more['href']
            else:
                logger.info("لم يتم العثور على رابط 'تحميل المزيد'. إيقاف الاستخراج.")
                break
            
            time.sleep(5)  # تأخير للاحترام
            
        except requests.exceptions.RequestException as e:
            logger.error(f"خطأ في جلب الصفحة: {e}")
            break
    
    return data


def save_to_csv(data, filename):
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=['text', 'date'])
            writer.writeheader()
            for row in data:
                writer.writerow(row)
        logger.info(f"تم حفظ البيانات بنجاح في {filename}")
    except Exception as e:
        logger.error(f"خطأ في حفظ البيانات: {e}")

def get_telegram_data(url, start_date, end_date, output_file, max_posts=1000, progress_callback=None):
    data = scrape_telegram(url, start_date, end_date, max_posts, progress_callback)
    if data:
        save_to_csv(data, output_file)
        return pd.DataFrame(data)
    return pd.DataFrame()

def analyze_data(df):
  if df.empty:
      return None
  
  # قائمة الكلمات الشائعة التي نريد استبعادها
  arabic_stop_words = set([
      'في', 'من', 'على', 'إلى', 'عن', 'مع', 'هذا', 'هذه', 'تم', 'قال',
      'كان', 'كانت', 'أن', 'التي', 'الذي', 'هو', 'هي', 'قد', 'ما', 'لا',
      'إن', 'نحو', 'لدى', 'عند', 'حيث', 'لقد', 'أو', 'و', 'ثم', 'أم','عبر',
      'كل', 'بعد', 'قبل', 'حتى', 'إذا', 'كما', 'لكن', 'انه', 'انها', 'منذ',
      'مثل', 'حول', 'ضمن', 'فقط', 'بين', 'أيضا', 'به', 'بها', 'منها', 'عنها',
      'وقد', 'فيه', 'فيها', 'تلك', 'ذلك', 'عليه', 'عليها', 'اول', 'ضد', 'بعض',
      'اي', 'وفي', 'وقال', 'وكان', 'المقبل', 'الماضي', 'اليوم', 'ألف', 'الف',
      'بن', 'بإن', 'به', 'لها', 'له', 'تكون', 'وأن', 'صلى', 'عليه', 'وسلم',
      'تحت', 'جدا', 'ذات', 'ضمن', 'حاليا', 'بشكل', 'أبو', 'بكر', 'حسب'
  ])

  def clean_text(text):
      # إزالة علامات الترقيم والأرقام
      text = re.sub(r'[^\w\s]', ' ', text)
      text = re.sub(r'\d+', ' ', text)
      # تقسيم النص إلى كلمات
      words = text.split()
      # إزالة الكلمات القصيرة والكلمات الشائعة
      words = [word for word in words 
              if len(word) > 2  # استبعاد الكلمات القصيرة
              and word not in arabic_stop_words  # استبعاد الكلمات الشائعة
              and not any(char.isdigit() for char in word)]  # استبعاد النصوص التي تحتوي على أرقام
      return words

  total_posts = len(df)
  date_range = (df['date'].min(), df['date'].max())
  
  # تحليل الكلمات الأكثر شيوعاً بعد التنقية
  all_words = []
  for text in df['text']:
      all_words.extend(clean_text(text))
  
  word_counts = pd.Series(all_words).value_counts()
  most_common_words = word_counts.head(20)  # أخذ أعلى 20 كلمة
  
  # إضافة التحليلات الأخرى
  posts_per_day = df.groupby(df['date'].dt.date).size().reset_index(name='count')
  posts_per_day.columns = ['date', 'count']
  
  avg_post_length = df['text'].str.len().mean()
  
  return {
      'total_posts': total_posts,
      'date_range': date_range,
      'most_common_words': most_common_words,
      'posts_per_day': posts_per_day,
      'avg_post_length': avg_post_length
  }