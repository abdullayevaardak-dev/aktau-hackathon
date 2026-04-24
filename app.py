import streamlit as st
import sqlite3
import pandas as pd
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# --- НАСТРОЙКИ ПРИЛОЖЕНИЯ ---
st.set_page_config(page_title="Aktau Job Wave", layout="wide", page_icon="🌊")

# --- ПАМЯТЬ СЕССИИ (ДЛЯ АВТОРИЗАЦИИ И РОЛЕЙ) ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.login = ""
    st.session_state.role = ""

# --- БАЗА ДАННЫХ (ВЕРСИЯ 2) ---
conn = sqlite3.connect('aktau_jobs_v2.db', check_same_thread=False)
c = conn.cursor()
# Таблица пользователей
c.execute('''CREATE TABLE IF NOT EXISTS users_v2 (id INTEGER PRIMARY KEY AUTOINCREMENT, login TEXT, password TEXT, role TEXT)''')
# Таблица вакансий (добавили зарплату)
c.execute('''CREATE TABLE IF NOT EXISTS vacancies_v2 (id INTEGER PRIMARY KEY AUTOINCREMENT, login TEXT, title TEXT, desc TEXT, salary TEXT, location TEXT, phone TEXT)''')
# Таблица резюме (добавили ФИО, дату рождения, желаемую должность)
c.execute('''CREATE TABLE IF NOT EXISTS resumes_v2 (id INTEGER PRIMARY KEY AUTOINCREMENT, login TEXT, fullname TEXT, dob TEXT, desired TEXT, experience TEXT)''')
conn.commit()

# --- TELEGRAM БОТ ---
def send_telegram(message):
    TOKEN = "8353625063:AAGvAYdYZ-oeo3H3OR_fo5VJA6DhJbLYWds" # <-- ВАЖНО: Вставьте ваш токен!
    CHAT_ID = "@aktau_jobs_hack" # <-- ВАЖНО: Вставьте ваш канал!
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    try: requests.get(url)
    except: pass

# --- ИИ-МАТЧИНГ ---
def calculate_ai_match(resume_text, vacancy_text):
    if not resume_text or not vacancy_text: return 0
    vectorizer = TfidfVectorizer()
    try:
        tfidf_matrix = vectorizer.fit_transform([resume_text, vacancy_text])
        return round(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0] * 100)
    except: return 0


# ==========================================
# ЭКРАН 1: АВТОРИЗАЦИЯ И РЕГИСТРАЦИЯ
# ==========================================
if not st.session_state.logged_in:
    st.title("🌊 Добро пожаловать в Aktau Job Wave")
    st.markdown("### Платформа для быстрого поиска работы и сотрудников в Мангистау")
    st.divider()

    col1, col2 = st.columns(2)
    
    with col1:
        with st.container(border=True):
            st.subheader("👋 Впервые здесь? Регистрация")
            reg_role = st.radio("Кто вы?", ["Я ищу работу (Соискатель)", "Я ищу сотрудников (Работодатель)"])
            reg_login = st.text_input("Ваш номер телефона или Email", key="reg_log")
            reg_pass = st.text_input("Придумайте пароль", type="password", key="reg_pass")
            
            if st.button("Создать аккаунт", type="primary", use_container_width=True):
                c.execute("SELECT * FROM users_v2 WHERE login=?", (reg_login,))
                if c.fetchone():
                    st.error("❌ Аккаунт с таким номером/email уже существует!")
                elif reg_login and reg_pass:
                    role_db = "seeker" if "Соискатель" in reg_role else "employer"
                    c.execute("INSERT INTO users_v2 (login, password, role) VALUES (?, ?, ?)", (reg_login, reg_pass, role_db))
                    conn.commit()
                    st.success("✅ Аккаунт успешно создан! Теперь войдите в систему справа.")
                else:
                    st.warning("Пожалуйста, заполните все поля.")

    with col2:
        with st.container(border=True):
            st.subheader("🔑 Уже есть аккаунт? Вход")
            log_login = st.text_input("Ваш номер телефона или Email", key="login_log")
            log_pass = st.text_input("Ваш пароль", type="password", key="login_pass")
            
            if st.button("Войти на платформу", use_container_width=True):
                c.execute("SELECT * FROM users_v2 WHERE login=? AND password=?", (log_login, log_pass))
                user = c.fetchone()
                if user:
                    st.session_state.logged_in = True
                    st.session_state.login = user[1]
                    st.session_state.role = user[3]
                    st.rerun()
                else:
                    st.error("❌ Неверный логин или пароль")

# ==========================================
# ЭКРАН 2: ЛИЧНЫЙ КАБИНЕТ (ПОСЛЕ ВХОДА)
# ==========================================
else:
    # Верхняя панель (Header)
    col_head1, col_head2 = st.columns([4, 1])
    with col_head1:
        if st.session_state.role == "seeker":
            st.title("👤 Кабинет Соискателя")
        else:
            st.title("🏢 Кабинет Работодателя")
    with col_head2:
        st.write(f"Вы вошли как: `{st.session_state.login}`")
        if st.button("🚪 Выйти"):
            st.session_state.logged_in = False
            st.session_state.login = ""
            st.session_state.role = ""
            st.rerun()
    st.divider()

    # ----------------------------------------
    # ИНТЕРФЕЙС СОИСКАТЕЛЯ
    # ----------------------------------------
    if st.session_state.role == "seeker":
        tab1, tab2 = st.tabs(["📄 Мое резюме", "🔍 Найти работу"])
        
        with tab1:
            st.subheader("Заполните вашу анкету")
            with st.container(border=True):
                r_fullname = st.text_input("Ваше ФИО")
                r_dob = st.date_input("Дата рождения", min_value=pd.to_datetime("1950-01-01"), max_value=pd.to_datetime("2010-01-01"))
                r_desired = st.text_input("Желаемая должность (например: Менеджер, Бариста)")
                r_exp = st.text_area("Опыт работы и навыки (расскажите подробнее)")
                
                if st.button("💾 Сохранить / Обновить резюме", type="primary"):
                    # Удаляем старое резюме этого пользователя, чтобы было только одно актуальное
                    c.execute("DELETE FROM resumes_v2 WHERE login=?", (st.session_state.login,))
                    c.execute("INSERT INTO resumes_v2 (login, fullname, dob, desired, experience) VALUES (?, ?, ?, ?, ?)", 
                              (st.session_state.login, r_fullname, str(r_dob), r_desired, r_exp))
                    conn.commit()
                    st.success("✅ Ваше резюме успешно сохранено в базе!")

            st.markdown("### Ваша текущая анкета в базе:")
            my_res = pd.read_sql_query("SELECT * FROM resumes_v2 WHERE login=?", conn, params=(st.session_state.login,))
            if not my_res.empty:
                st.info(f"**ФИО:** {my_res.iloc[0]['fullname']} | **Ищет работу:** {my_res.iloc[0]['desired']}")

        with tab2:
            st.subheader("Доступные вакансии")
            df_vac = pd.read_sql_query("SELECT * FROM vacancies_v2 ORDER BY id DESC", conn)
            
            my_skills = my_res.iloc[0]['experience'] if not my_res.empty else ""
            
            if df_vac.empty:
                st.info("Пока нет доступных вакансий.")
            else:
                for index, row in df_vac.iterrows():
                    with st.container(border=True):
                        st.markdown(f"### 💼 {row['title']}")
                        st.markdown(f"**💰 Зарплата:** {row['salary']} | **📍 Адрес:** {row['location']}")
                        with st.expander("Подробные условия"):
                            st.write(row['desc'])
                            if my_skills:
                                match_pct = calculate_ai_match(my_skills, row['desc'])
                                st.progress(match_pct / 100.0)
                                st.markdown(f"🤖 **AI-совпадение с вашим опытом:** `{match_pct}%`")
                            
                            phone_clean = row['phone'].replace("+", "").replace(" ", "").replace("-", "")
                            st.markdown(f"[💬 Откликнуться в WhatsApp](https://wa.me/{phone_clean})")

    # ----------------------------------------
    # ИНТЕРФЕЙС РАБОТОДАТЕЛЯ
    # ----------------------------------------
    elif st.session_state.role == "employer":
        tab1, tab2 = st.tabs(["🏢 Мои вакансии (Создать)", "👥 База талантов (Поиск)"])
        
        with tab1:
            st.subheader("Опубликовать новую вакансию")
            with st.container(border=True):
                v_title = st.text_input("Должность")
                v_desc = st.text_area("Описание условий и требований")
                v_salary = st.text_input("Заработная плата (например: 150 000 тг)")
                v_loc = st.text_input("Адрес работы")
                v_phone = st.text_input("Контактный телефон (WhatsApp)")
                
                if st.button("🚀 Создать вакансию", type="primary"):
                    c.execute("INSERT INTO vacancies_v2 (login, title, desc, salary, location, phone) VALUES (?, ?, ?, ?, ?, ?)", 
                              (st.session_state.login, v_title, v_desc, v_salary, v_loc, v_phone))
                    conn.commit()
                    st.success("✅ Вакансия опубликована!")
                    # Отправка в Телеграм
                    phone_clean = v_phone.replace("+", "").replace(" ", "").replace("-", "")
                    msg = f"🔥 Новая вакансия: {v_title}\n💰 Зарплата: {v_salary}\n📍 Адрес: {v_loc}\n📞 Телефон: {v_phone}\n💬 WhatsApp: https://wa.me/{phone_clean}"
                    send_telegram(msg)

            st.markdown("### Управление моими вакансиями:")
            my_vacs = pd.read_sql_query("SELECT * FROM vacancies_v2 WHERE login=?", conn, params=(st.session_state.login,))
            if my_vacs.empty:
                st.info("У вас пока нет опубликованных вакансий.")
            else:
                for index, row in my_vacs.iterrows():
                    with st.container(border=True):
                        st.markdown(f"**{row['title']}** — {row['salary']}")
                        if st.button("❌ Удалить", key=f"del_vac_{row['id']}"):
                            c.execute("DELETE FROM vacancies_v2 WHERE id=?", (row['id'],))
                            conn.commit()
                            st.rerun()

        with tab2:
            st.subheader("Резюме соискателей Актау")
            df_res = pd.read_sql_query("SELECT * FROM resumes_v2 ORDER BY id DESC", conn)
            if df_res.empty:
                st.info("Пока нет опубликованных резюме.")
            else:
                for index, row in df_res.iterrows():
                    with st.container(border=True):
                        st.markdown(f"#### 👤 {row['fullname']}")
                        st.caption(f"**Желаемая должность:** {row['desired']} | **Возраст (г.р.):** {row['dob']}")
                        with st.expander("Опыт работы и навыки"):
                            st.write(row['experience'])
                            st.markdown(f"**Связаться:** Пользователь зарегистрирован под логином `{row['login']}`")
