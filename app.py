# app.py
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
from telegram_scraper import get_telegram_data, analyze_data, validate_telegram_url

st.set_page_config(page_title="محلل بيانات قناة Telegram", layout="wide")

st.title("محلل بيانات قناة Telegram")

col1, col2 = st.columns(2)
with col1:
  start_date = st.date_input(
      "حدد تاريخ البداية",
      value=datetime.now().date() - timedelta(days=365),
  )
with col2:
  end_date = st.date_input(
      "حدد تاريخ النهاية",
      value=datetime.now().date(),
  )

channel_url = st.text_input("أدخل URL قناة Telegram", "https://t.me/s/AjaNews")
max_posts = st.number_input("الحد الأقصى لعدد المنشورات للاستخراج", min_value=1, value=1000)

if st.button("استخراج وتحليل البيانات"):
  if start_date > end_date:
      st.error("تاريخ البداية يجب أن يكون قبل تاريخ النهاية.")
  elif end_date > datetime.now().date():
      st.error("لا يمكن تحديد تاريخ نهاية في المستقبل.")
  elif not validate_telegram_url(channel_url):
      st.error("رابط Telegram غير صالح. يرجى التأكد من أنه يبدأ بـ 'https://t.me/s/' متبوعًا باسم القناة.")
  else:
      progress_bar = st.progress(0)
      status_text = st.empty()

      def update_progress(current, total):
        progress = min(int(current / total * 100), 100) if total > 0 else 0
        progress_bar.progress(progress)
        status_text.text(f"تمت معالجة {current} منشور")

      output_file = "telegram_data.csv"

      with st.spinner("جاري استخراج البيانات من Telegram..."):
          df = get_telegram_data(channel_url, start_date, end_date, output_file, max_posts, update_progress)

      progress_bar.empty()
      status_text.empty()

      if not df.empty:
          st.success(f"تم استخراج {len(df)} منشور بنجاح ضمن النطاق الزمني المحدد!")

          st.subheader("البيانات المستخرجة")
          st.dataframe(df)

          analysis = analyze_data(df)
          if analysis:
              col1, col2 = st.columns(2)

              with col1:
                  st.subheader("إحصائيات عامة")
                  st.write(f"إجمالي المنشورات: {analysis['total_posts']}")
                  st.write(f"نطاق التاريخ: من {analysis['date_range'][0]} إلى {analysis['date_range'][1]}")
                  st.write(f"متوسط طول المنشور: {analysis['avg_post_length']:.2f} حرف")

              with col2:
                  st.subheader("الكلمات الأكثر شيوعًا")
                  st.bar_chart(analysis['most_common_words'])

              st.subheader("المنشورات اليومية")
              chart = alt.Chart(analysis['posts_per_day']).mark_line().encode(
                  x='date:T',
                  y='count:Q',
                  tooltip=['date', 'count']
              ).properties(
                  width=800,
                  height=400
              )
              st.altair_chart(chart, use_container_width=True)

      else:
          st.warning("لم يتم العثور على بيانات ضمن النطاق الزمني المحدد. يرجى التحقق من السجلات للحصول على مزيد من المعلومات.")
          st.info("حاول توسيع نطاق التاريخ أو تحقق من صحة URL قناة Telegram.")

st.sidebar.header("حول التطبيق")
st.sidebar.info(
  "هذا التطبيق يساعدك في استخراج وتحليل البيانات من قنوات Telegram العامة. "
  "أدخل رابط القناة، حدد نطاق التاريخ، واحصل على تحليل مفصل للمنشورات."
)
st.sidebar.header("تعليمات الاستخدام")
st.sidebar.markdown(
  """
  1. أدخل رابط قناة Telegram (يجب أن يبدأ بـ 'https://t.me/s/')
  2. حدد نطاق التاريخ للبيانات التي تريد استخراجها
  3. حدد الحد الأقصى لعدد المنشورات
  4. انقر على زر 'استخراج وتحليل البيانات'
  5. انتظر حتى يتم استخراج البيانات وعرض التحليل
  """
)
