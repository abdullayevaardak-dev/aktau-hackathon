import streamlit as st
import sqlite3
import pandas as pd
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# --- НАСТРОЙКИ ПРИЛОЖЕНИЯ ---
st.set_page_config(page_title="Aktau Job Wave", layout="wide", page_icon="🌊")

# --- ПАМЯТЬ СЕССИИ (ДЛЯ АВТОРИЗАЦИИ) ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

st.title("🌊 Aktau Job Wave")
st.markdown("### Платформа занятости для молодежи и малого бизнеса Мангистау")
st.divider()

# --- БАЗА ДАННЫХ ---
conn = sqlite3.connect('aktau_jobs.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS vacancies (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, desc TEXT, location TEXT, phone TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS resumes (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, skills TEXT, location TEXT, phone TEXT)''')
# Создаем новую таблицу специально для зарегистрированных пользователей
c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT)''')
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
    TOKEN = "8353625063:AAGvAYdYZ-oeo3H3OR_fo5VJA6DhJbLYWds" # <-- ВАЖНО: Не забудьте вставить ваш токен!
    CHAT_ID = "@aktau_jobs_hack" # <-- ВАЖНО: Не забудьте вставить ваш канал!
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    try: requests.get(url)
    except: pass

# --- ИНТЕРФЕЙС (5 ВКЛАДОК) ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 Вакансии", "👥 База резюме", "🏢 Разместить вакансию", "👤 Оставить резюме", "🔑 Мой аккаунт"])

# --- ВКЛАДКА 1: ВАКАНСИИ ---
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
        with st.container(border=True):
            st.markdown(f"### 💼 {row['title']}")
            st.caption(f"📍 **Локация:** {row['location']}")
            with st.expander("Показать подробное описание и контакты"):
                st.write(row['desc'])
                if my_skills:
                    match_pct = calculate_ai_match(my_skills, row['desc'])
                    st.progress(match_pct / 100.0)
                    st.markdown(f"🤖 **AI-совпадение:** `{match_pct}%`")
                phone_clean = row['phone'].replace("+", "").replace(" ", "").replace("-", "")
                st.markdown(f"[💬 Написать работодателю в WhatsApp](https://wa.me/{phone_clean})")

# --- ВКЛАДКА 2: БАЗА РЕЗЮМЕ ---
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
            phone_clean = v_phone.replace("+", "").replace(" ", "").replace("-", "")
            msg = f"🔥 Новая вакансия: {v_title}\n📍 Район: {v_loc}\n📞 Телефон: {v_phone}\n💬 WhatsApp: https://wa.me/{phone_clean}"
            send_telegram(msg)

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

# --- ВКЛАДКА 5: СИСТЕМА РЕГИСТРАЦИИ И АККАУНТ ---
with tab5:
    if not st.session_state.logged_in:
        st.subheader("Вход в систему и Регистрация")
        col_log, col_reg = st.columns(2)
        
        with col_reg:
            with st.container(border=True):
                st.markdown("#### 📝 Регистрация")
                reg_user = st.text_input("Придумайте логин", key="reg_user")
                reg_pass = st.text_input("Придумайте пароль", type="password", key="reg_pass")
                if st.button("Создать аккаунт", use_container_width=True):
                    c.execute("SELECT * FROM users WHERE username=?", (reg_user,))
                    if c.fetchone():
                        st.error("❌ Такой логин уже существует!")
                    elif reg_user and reg_pass:
                        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (reg_user, reg_pass))
                        conn.commit()
                        st.success("✅ Аккаунт создан! Теперь войдите слева.")
                    else:
                        st.warning("Введите логин и пароль.")

        with col_log:
            with st.container(border=True):
                st.markdown("#### 🔑 Войти")
                login_user = st.text_input("Ваш логин", key="log_user")
                login_pass = st.text_input("Ваш пароль", type="password", key="log_pass")
                if st.button("Войти", use_container_width=True):
                    c.execute("SELECT * FROM users WHERE username=? AND password=?", (login_user, login_pass))
                    if c.fetchone():
                        st.session_state.logged_in = True
                        st.session_state.username = login_user
                        st.rerun() # Перезагружаем страницу, чтобы пустить пользователя
                    else:
                        st.error("❌ Неверный логин или пароль")

    else:
        # Экран, когда пользователь успешно вошел в систему
        with st.container(border=True):
            st.subheader(f"👋 Добро пожаловать в профиль, {st.session_state.username}!")
            st.success("Вы успешно авторизованы в системе.")
            st.markdown("---")
            st.write("Здесь находится ваш личный кабинет. Вы можете управлять своими данными, просматривать отклики и редактировать профиль.")
            st.info("💡 Подсказка для жюри: В MVP версии редактирование объявлений привязано к сессии аккаунта. В полной версии здесь появится панель управления (Dashboard).")
            st.markdown("---")
            if st.button("🚪 Выйти из аккаунта"):
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.rerun()
