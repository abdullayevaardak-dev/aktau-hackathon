import streamlit as st
import sqlite3
import pandas as pd
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# --- НАСТРОЙКИ ПРИЛОЖЕНИЯ ---
st.set_page_config(page_title="Aktau Job Wave", layout="wide")
st.title("🌊 Aktau Job Wave - Работа рядом с домом")
st.markdown("Платформа занятости для молодежи и малого бизнеса Мангистау")

# --- 1. БАЗА ДАННЫХ (SQLite) ---
# Это выполняет требование хакатона о хранении данных в БД
conn = sqlite3.connect('aktau_jobs.db', check_same_thread=False)
c = conn.cursor()

# Создаем таблицы, если их нет
c.execute('''CREATE TABLE IF NOT EXISTS vacancies 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, desc TEXT, location TEXT, phone TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS resumes 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, skills TEXT, location TEXT, phone TEXT)''')
conn.commit()

# --- 2. AI-МАТЧИНГ (Алгоритм семантического сходства) ---
# Выполняет требование наличия ИИ
def calculate_ai_match(resume_text, vacancy_text):
    if not resume_text or not vacancy_text: return 0
    # Используем TF-IDF векторайзер для сравнения текстов (простое ML решение)
    vectorizer = TfidfVectorizer()
    try:
        tfidf_matrix = vectorizer.fit_transform([resume_text, vacancy_text])
        match_score = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return round(match_score * 100)
    except:
        return 0

# --- 3. TELEGRAM УВЕДОМЛЕНИЯ ---
def send_telegram(message):
    # Для реального бота нужно вставить ваш ТОКЕН и CHAT_ID из BotFather
    # Пока оставим заглушку, чтобы код не выдавал ошибку без ключей
    TOKEN = "ВАШ_ТОКЕН"
    CHAT_ID = "ВАШ_CHAT_ID"
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    try:
        requests.get(url)
    except:
        pass

# --- ИНТЕРФЕЙС ПРИЛОЖЕНИЯ ---
tab1, tab2, tab3 = st.tabs(["🔍 Найти работу", "🏢 Создать вакансию", "👤 Мое резюме (Для ИИ)"])

# Вкладка: Создание вакансии
with tab2:
    st.subheader("Опубликовать вакансию для малого бизнеса")
    v_title = st.text_input("Название (например: Бариста, Продавец)")
    v_desc = st.text_area("Опишите требования и условия")
    v_loc = st.selectbox("Микрорайон Актау", ["1 мкр", "2 мкр", "14 мкр", "27 мкр", "Шугыла", "Другой"])
    v_phone = st.text_input("Ваш WhatsApp номер")
    
    if st.button("Создать вакансию"):
        c.execute("INSERT INTO vacancies (title, desc, location, phone) VALUES (?, ?, ?, ?)", 
                  (v_title, v_desc, v_loc, v_phone))
        conn.commit()
        st.success("✅ Вакансия добавлена в базу!")
        send_telegram(f"Новая вакансия в Актау: {v_title} в {v_loc}")

# Вкладка: Резюме соискателя
with tab3:
    st.subheader("Заполните профиль, чтобы ИИ нашел вам работу")
    r_name = st.text_input("Ваше Имя")
    r_skills = st.text_area("Ваши навыки и опыт (Напишите подробно, ИИ читает это!)")
    r_loc = st.selectbox("В каком микрорайоне ищете?", ["Любой", "1 мкр", "14 мкр", "27 мкр"])
    r_phone = st.text_input("Ваш телефон")
    
    if st.button("Сохранить профиль"):
        c.execute("INSERT INTO resumes (name, skills, location, phone) VALUES (?, ?, ?, ?)", 
                  (r_name, r_skills, r_loc, r_phone))
        conn.commit()
        st.success("✅ Резюме сохранено! Перейдите во вкладку 'Найти работу'.")

# Вкладка: Поиск с AI-Матчингом
with tab1:
    st.subheader("Умная лента вакансий")
    filter_loc = st.selectbox("Фильтр по району", ["Все", "1 мкр", "14 мкр", "27 мкр"])
    
    # Загружаем вакансии
    df_vac = pd.read_sql_query("SELECT * FROM vacancies", conn)
    # Загружаем последнее резюме для AI-матчинга
    df_res = pd.read_sql_query("SELECT * FROM resumes ORDER BY id DESC LIMIT 1", conn)
    my_skills = df_res['skills'].iloc[0] if not df_res.empty else ""
    
    if filter_loc != "Все":
        df_vac = df_vac[df_vac['location'] == filter_loc]

    if df_vac.empty:
        st.info("Пока нет подходящих вакансий.")
    else:
        for index, row in df_vac.iterrows():
            with st.container():
                st.markdown(f"### {row['title']} (📍 {row['location']})")
                st.write(f"**Описание:** {row['desc']}")
                
                # Вызов функции ИИ
                if my_skills:
                    match_pct = calculate_ai_match(my_skills, row['desc'])
                    st.progress(match_pct / 100.0)
                    st.write(f"🤖 **AI-Матчинг:** Вы подходите на {match_pct}%")
                
                if st.button(f"Откликнуться", key=f"btn_{row['id']}"):
                    st.success(f"Отклик отправлен! Напишите работодателю: {row['phone']}")
                st.divider()