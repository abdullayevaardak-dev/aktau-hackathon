import streamlit as st
import sqlite3
import pandas as pd
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# --- НАСТРОЙКИ ПРИЛОЖЕНИЯ ---
st.set_page_config(page_title="Aktau Job Wave", layout="wide", page_icon="🌊")
st.title("🌊 Aktau Job Wave")
st.markdown("### Платформа занятости для молодежи и малого бизнеса Мангистау")
st.divider()

# --- БАЗА ДАННЫХ ---
conn = sqlite3.connect('aktau_jobs.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS vacancies 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, desc TEXT, location TEXT, phone TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS resumes 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, skills TEXT, location TEXT, phone TEXT)''')
conn.commit()

# --- ИИ-МАТЧИНГ ---
def calculate_ai_match(resume_text, vacancy_text):
    if not resume_text or not vacancy_text: return 0
    vectorizer = TfidfVectorizer()
    try:
        tfidf_matrix = vectorizer.fit_transform([resume_text, vacancy_text])
        return round(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0] * 100)
    except: return 0

# --- TELEGRAM БОТ ---
def send_telegram(message):
    TOKEN = "8353625063:AAGvAYdYZ-oeo3H3OR_fo5VJA6DhJbLYWds" # <-- ВАЖНО: Вставьте сюда ваш токен снова!
    CHAT_ID = "@aktau_jobs_hack" # <-- ВАЖНО: Вставьте сюда ваш канал (@...) снова!
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    try: requests.get(url)
    except: pass

# --- ИНТЕРФЕЙС (4 ВКЛАДКИ) ---
tab1, tab2, tab3, tab4 = st.tabs(["🔍 Вакансии", "👥 База резюме", "🏢 Разместить вакансию", "👤 Оставить резюме"])

# --- ВКЛАДКА 1: ВАКАНСИИ (Для соискателя) ---
with tab1:
    col1, col2 = st.columns([3, 1])
    with col1: st.subheader("Свежие вакансии")
    with col2: filter_loc = st.selectbox("📍 Район:", ["Все", "1 мкр", "14 мкр", "27 мкр", "Шугыла"])

    df_vac = pd.read_sql_query("SELECT * FROM vacancies ORDER BY id DESC", conn)
    df_res = pd.read_sql_query("SELECT * FROM resumes ORDER BY id DESC LIMIT 1", conn)
    my_skills = df_res['skills'].iloc[0] if not df_res.empty else ""

    if filter_loc != "Все": df_vac = df_vac[df_vac['location'] == filter_loc]

    if df_vac.empty: st.info("Пока нет вакансий в этом районе.")
    for index, row in df_vac.iterrows():
        # Красивая рамка для карточки
        with st.container(border=True):
            st.markdown(f"### 💼 {row['title']}")
            st.caption(f"📍 **Локация:** {row['location']}")
            
            with st.expander("Показать подробное описание и контакты"):
                st.write(row['desc'])
                if my_skills:
                    match_pct = calculate_ai_match(my_skills, row['desc'])
                    st.progress(match_pct / 100.0)
                    st.markdown(f"🤖 **AI-совпадение с вашим резюме:** `{match_pct}%`")
                
                phone_clean = row['phone'].replace("+", "").replace(" ", "").replace("-", "")
                st.markdown(f"[💬 Написать работодателю в WhatsApp](https://wa.me/{phone_clean})")
# Кнопка удаления
                if st.button("❌ Удалить эту вакансию", key=f"del_vac_{row['id']}"):
                    c.execute("DELETE FROM vacancies WHERE id=?", (row['id'],))
                    conn.commit()
                    st.rerun()
# --- ВКЛАДКА 2: БАЗА РЕЗЮМЕ (Для бизнеса) ---
with tab2:
    st.subheader("Таланты Актау (База соискателей)")
    df_res_all = pd.read_sql_query("SELECT * FROM resumes ORDER BY id DESC", conn)
    
    if df_res_all.empty: st.info("Пока нет резюме.")
    for index, row in df_res_all.iterrows():
        with st.container(border=True):
            st.markdown(f"#### 👤 {row['name']}")
            st.caption(f"📍 **Желаемый район:** {row['location']}")
            with st.expander("Навыки и опыт"):
                st.write(row['skills'])
                phone_clean_res = row['phone'].replace("+", "").replace(" ", "").replace("-", "")
                st.markdown(f"[💬 Пригласить на работу (WhatsApp)](https://wa.me/{phone_clean_res})")

# --- ВКЛАДКА 3: СОЗДАТЬ ВАКАНСИЮ ---
with tab3:
    with st.container(border=True):
        st.subheader("Опубликовать вакансию")
        v_title = st.text_input("Должность (например: Бариста)")
        v_desc = st.text_area("Требования")
        v_loc = st.selectbox("Микрорайон", ["1 мкр", "14 мкр", "27 мкр", "Шугыла", "Другой"])
        v_phone = st.text_input("WhatsApp номер (например: 77012345678)")
        if st.button("🚀 Создать вакансию", use_container_width=True):
            c.execute("INSERT INTO vacancies (title, desc, location, phone) VALUES (?, ?, ?, ?)", (v_title, v_desc, v_loc, v_phone))
            conn.commit()
            st.success("Вакансия опубликована!")
            # Отправка в Телеграм
            phone_clean = v_phone.replace("+", "").replace(" ", "").replace("-", "")
msg = f"🔥 Новая вакансия: {v_title}\n📍 Район: {v_loc}\n📞 Телефон: {v_phone}\n💬 WhatsApp: https://wa.me/{phone_clean}"

# --- ВКЛАДКА 4: СОЗДАТЬ РЕЗЮМЕ ---
with tab4:
    with st.container(border=True):
        st.subheader("Заполнить профиль (CV)")
        r_name = st.text_input("Ваше Имя и Фамилия")
        r_skills = st.text_area("Ваши навыки (подробно для ИИ)")
        r_loc = st.selectbox("Где ищете работу?", ["Любой", "1 мкр", "14 мкр", "27 мкр"])
        r_phone = st.text_input("Ваш WhatsApp")
        if st.button("💾 Сохранить резюме", use_container_width=True):
            c.execute("INSERT INTO resumes (name, skills, location, phone) VALUES (?, ?, ?, ?)", (r_name, r_skills, r_loc, r_phone))
            conn.commit()
            st.success("Резюме добавлено в базу!")
