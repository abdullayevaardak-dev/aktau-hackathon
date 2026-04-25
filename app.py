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
                except: default_dob = pd.to_datetime("2000-01-01")
                st.info("💡 У вас уже есть резюме. Вы можете отредактировать его ниже и нажать 'Обновить'.")
            else:
                curr_name, default_dob, curr_desired, curr_exp = "", pd.to_datetime("2000-01-01"), "", ""
                st.warning("У вас еще нет резюме. Заполните данные, чтобы работодатели могли вас найти!")

            with st.container(border=True):
                r_fullname = st.text_input("Ваше ФИО", value=curr_name)
                r_dob = st.date_input("Дата рождения", value=default_dob, min_value=pd.to_datetime("1950-01-01"), max_value=pd.to_datetime("2010-01-01"))
                r_desired = st.text_input("Желаемая должность", value=curr_desired)
                r_exp = st.text_area("Опыт работы и навыки (обязательно укажите стаж цифрами, например '2 года')", value=curr_exp, height=200)
                
                if st.button("💾 Сохранить / Обновить резюме", type="primary", use_container_width=True):
                    if r_fullname and r_desired:
                        c.execute("DELETE FROM resumes_v2 WHERE login=?", (st.session_state.login,))
                        c.execute("INSERT INTO resumes_v2 (login, fullname, dob, desired, experience) VALUES (?, ?, ?, ?, ?)", 
                                  (st.session_state.login, r_fullname, str(r_dob), r_desired, r_exp))
                        conn.commit()
                        st.success("✅ Данные успешно обновлены!")
                        st.rerun()
                    else:
                        st.error("Пожалуйста, заполните ФИО и должность.")

        with tab2:
            st.subheader("Доступные вакансии")
            st.info("🚀 **Хотите узнавать о свежих вакансиях первыми?** Подписывайтесь на наш Telegram-канал: [👉 Перейти в Telegram](https://t.me/aktau_jobs_hack)")
            
            my_res = pd.read_sql_query("SELECT experience FROM resumes_v2 WHERE login=?", conn, params=(st.session_state.login,))
            my_skills = my_res.iloc[0]['experience'] if not my_res.empty else ""
            
            df_vac = pd.read_sql_query("SELECT * FROM vacancies_v2 ORDER BY id DESC", conn)
            
            if df_vac.empty:
                st.info("Пока нет доступных вакансий.")
            else:
                for index, row in df_vac.iterrows():
                    with st.container(border=True):
                        st.markdown(f"### 💼 {row['title']}")
                        st.markdown(f"**💰 Зарплата:** {row['salary']} | **📍 Адрес:** {row['location']}")
                        with st.expander("Подробные условия"):
                            st.write(row['desc'])
                            
                            # --- ВЫВОД РЕЗУЛЬТАТОВ УМНОГО ИИ ---
                            if my_skills:
                                match_pct, recommendation = calculate_smart_match(my_skills, row['desc'])
                                st.progress(match_pct / 100.0)
                                st.markdown(f"🤖 **ИИ-совпадение:** `{match_pct}%`")
                                st.info(f"📋 **Анализ ИИ:** {recommendation}")
                            
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
                v_desc = st.text_area("Описание условий и требований (Например: Опыт от 3 лет...)")
                v_salary = st.text_input("Заработная плата (например: 150 000 тг)")
                v_loc = st.text_input("Адрес работы")
                v_phone = st.text_input("Контактный телефон (WhatsApp)", value="+7", max_chars=12)
                
                if st.button("🚀 Создать вакансию", type="primary"):
                    if not v_phone.startswith("+7") or len(v_phone) < 11:
                        st.error("❌ Ошибка: Пожалуйста, введите корректный номер телефона (начиная с +7)")
                    elif not v_title or not v_desc:
                        st.warning("Пожалуйста, заполните должность и описание!")
                    else:
                        c.execute("INSERT INTO vacancies_v2 (login, title, desc, salary, location, phone) VALUES (?, ?, ?, ?, ?, ?)", 
                                  (st.session_state.login, v_title, v_desc, v_salary, v_loc, v_phone))
                        conn.commit()
                        st.success("✅ Вакансия опубликована!")
                        
                        phone_clean = v_phone.replace("+", "").replace(" ", "").replace("-", "")
                        msg = f"🔥 Новая вакансия: {v_title}\n💰 Зарплата: {v_salary}\n📍 Адрес: {v_loc}\n\n📝 Описание и условия:\n{v_desc}\n\n📞 Телефон: {v_phone}\n💬 WhatsApp: https://wa.me/{phone_clean}"
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
