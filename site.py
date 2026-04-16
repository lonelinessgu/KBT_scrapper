import streamlit as st
from functions import parse
from datetime import date

st.title("Скраппер расписания КБТ")

try:
    raw_groups = parse()
    groups = [item for sublist in raw_groups for item in sublist]
except Exception as e:
    st.error(f"Не удалось загрузить список групп: {e}")
    st.stop()

col_empty, col_calendar = st.columns([5.5, 4.5])

with col_calendar:
    selected_date = st.date_input("Дата расписания:", value=date.today())

delta = (selected_date - date.today()).days
parse_kwargs = {}
if delta > 0:
    parse_kwargs['increase'] = delta
elif delta < 0:
    parse_kwargs['decrease'] = -delta

tab_group, tab_teacher = st.tabs(["По группе", "По преподавателю"])

with tab_group:
    selected_group = st.selectbox("Выберите группу:", groups, key="group_select")

    if selected_group:
        try:
            data = parse(group=selected_group, **parse_kwargs)

            if not data:
                st.info("Пар не найдено.")
            else:
                if isinstance(data[0], tuple):
                    lines = [f"{pair}. {text}" for pair, text in data]
                else:
                    lines = data
                st.code("\n".join(lines), language="text")
        except Exception as e:
            st.error(f"Ошибка: {e}")

with tab_teacher:
    teacher_surname = st.text_input("Введите фамилию преподавателя:", key="teacher_input")

    if teacher_surname:
        try:
            data = parse(surname=teacher_surname, **parse_kwargs)

            if not data:
                st.info("Пар не найдено.")
            else:
                lines = []
                for pair_num in sorted(data.keys(), key=lambda x: int(x) if x.isdigit() else 0):
                    lessons = data[pair_num]
                    for group, subject, aud in lessons:
                        line = f"{pair_num}. {subject} | {group} | {aud}"
                        lines.append(line)
                st.code("\n".join(lines), language="text")
        except Exception as e:
            st.error(f"Ошибка: {e}")