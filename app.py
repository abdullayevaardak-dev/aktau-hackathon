import streamlit as st
import sqlite3
import pandas as pd
import requests
import re # <-- Добавили библиотеку для умного поиска по тексту
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# --- НАСТРОЙКИ ПРИЛОЖЕНИЯ ---
st.set_page_config(page_title="Aktau Job Wave", layout="wide", page_icon="🌊")

# --- ПАМЯТЬ СЕССИИ ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.login = ""
    st.session_state.role = ""

# --- БАЗА ДАННЫХ (ВЕРСИЯ 2) ---
conn = sqlite3.connect('aktau_jobs_v2.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users_v2 (id INTEGER PRIMARY KEY AUTOINCREMENT, login TEXT, password TEXT, role TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS vacancies_v2 (id INTEGER PRIMARY KEY AUTOINCREMENT, login TEXT, title TEXT, desc TEXT, salary TEXT, location TEXT, phone TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS resumes_v2 (id INTEGER PRIMARY KEY AUTOINCREMENT, login TEXT, fullname TEXT, dob TEXT, desired TEXT, experience TEXT)''')
conn.commit()

# --- TELEGRAM БОТ ---
def send_telegram(message):
    TOKEN = "ВАШ_ТОКЕН" # <-- ВАЖНО: Вставьте ваш токен!
    CHAT_ID = "ВАШ_CHAT_ID" # <-- ВАЖНО: Вставьте ваш канал!
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    try: requests.get(url)
    except: pass

# --- УМНЫЙ ИИ-МАТЧИНГ С РЕКОМЕНДАЦИЯМИ ---
def calculate_smart_match(resume_text, vacancy_text):
    if not resume_text or not vacancy_text: return 0, "Недостаточно данных для анализа."
    
    # 1. Базовое совпадение по ключевым словам (TF-IDF)
    vectorizer = TfidfVectorizer()
    try:
        tfidf_matrix = vectorizer.fit_transform([resume_text, vacancy_text])
        base_score = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0] * 100
    except:
        base_score = 0
        
    # 2. Умный поиск опыта работы (ищем цифры перед словами год/лет/г)
    req_exp_matches = re.findall(r'(\d+)\s*(?:год|лет|г)', vacancy_text.lower())
    user_exp_matches = re.findall(r'(\d+)\s*(?:год|лет|г)', resume_text.lower())
    
    # Берем максимальную цифру (если написано "опыт от 2 до 5 лет", возьмет 5)
    req_exp = max([int(m) for m in req_exp_matches]) if req_exp_matches else 0
    user_exp = max([int(m) for m in user_exp_matches]) if user_exp_matches else 0
    
    bonus = 0
    recs = []
    
    # 3. Логика ИИ-рекомендаций
    if req_exp > 0:
        if user_exp >= req_exp:
            bonus += 25  # Даем огромный бонус за совпадение опыта!
            recs.append(f"✅ Ваш опыт ({user_exp} г.) полностью покрывает требования работодателя ({req_exp} г.).")
        elif user_exp > 0:
            recs.append(f"⚠️ Работодатель ищет опыт от {req_exp} лет, а у вас {user_exp}. Сделайте акцент на ваших навыках при отклике!")
        else:
            recs.append(f"⚠️ В вакансии указан опыт {req_exp} лет, но ИИ не нашел цифр в вашем резюме. Обязательно укажите стаж цифрами (например: '3 года')!")
    else:
        if user_exp > 0:
            bonus += 15
            recs.append("💡 Плюс: работодатель не указал жестких требований к опыту, а у вас он есть. Это выделит вас среди новичков.")
            
    if base_score < 20 and req_exp == 0:
        recs.append("💡 Совет: добавьте в свое резюме слова и навыки из описания этой вакансии, чтобы ИИ лучше вас замечал.")
        
    final_score = min(round(base_score + bonus), 100) # Процент не может быть больше 100
    
    if not recs:
        recs.append("💡 Ваши профили подходят друг другу. Можно смело откликаться!")
        
    return final_score, " ".join(recs)

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

    # --- ТИЗЕР ВАКАНСИЙ НА ГЛАВНОЙ ---
    st.divider()
    st.subheader("🔥 Свежие вакансии на платформе")
    
    df_recent_vacs = pd.read_sql_query("SELECT * FROM vacancies_v2 ORDER BY id DESC LIMIT 3", conn)
    
    if df_recent_vacs.empty:
        st.info("Скоро здесь появятся первые вакансии! Будьте в числе первых работодателей.")
    else:
        cols = st.columns(len(df_recent_vacs))
        for i, (index, row) in enumerate(df_recent_vacs.iterrows()):
            with cols[i]:
                with st.container(border=True):
                    st.markdown(f"#### 💼 {row['title']}")
                    st.markdown(f"**💰 {row['salary']}**")
                    st.caption(f"📍 {row['location']}")
                    
        st.info("👉 **Войдите или зарегистрируйтесь**, чтобы увидеть описание, контакты работодателя и откликнуться!")

# ==========================================
# ЭКРАН 2: ЛИЧНЫЙ КАБИНЕТ
# ==========================================
else:
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
            st.subheader("Ваша анкета")
            c.execute("SELECT fullname, dob, desired, experience FROM resumes_v2 WHERE login=?", (st.session_state.login,))
            existing_res = c.fetchone()
            
            if existing_res:
                curr_name, curr_dob, curr_desired, curr_exp = existing_res
                try: default_dob = pd.to_datetime(curr_dob)
                except: default_dob = pd.to_datetime("20
