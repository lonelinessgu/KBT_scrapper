import asyncio, aiohttp
from re import sub as re_sub, search as re_search, I as re_I
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from bs4 import BeautifulSoup

months_dict = {
    1: "yanvarya", 2: "fevralya", 3: "marta", 4: "aprelya", 5: "maya", 6: "iyunya",
    7: "iyulya", 8: "avgusta", 9: "sentyabrya", 10: "oktyabrya", 11: "noyabrya", 12: "dekabrya"
}


def normalize_text(text: str, remove_spaces: bool = False, keep_chars: str = r'a-zA-Zа-яА-Я0-9ёЁ\s') -> str:
    """
    Универсальная очистка текста.
    - Заменяет неразрывные пробелы и zero-width символы на обычный пробел
    - Нормализует множественные пробелы
    - Опционально удаляет всё кроме разрешённых символов
    """
    if not text:
        return ''
    text = re_sub(r'[\xa0\u200b\u200c\u200d\u200e\u200f]', ' ', text)
    text = re_sub(r'\s+', ' ', text).strip()
    if remove_spaces:
        return re_sub(r'\s+', '', text)
    if keep_chars:
        pattern = rf'^[^{keep_chars}]+|[^{keep_chars}]+$'
        text = re_sub(pattern, '', text).strip()
    return text


def mapping(month_value: str) -> str:
    return months_dict[int(month_value)]


async def parse_schedule(session: aiohttp.ClientSession, wrong_form: str) -> Optional[
    Tuple[str, List[List[List[str]]]]]:
    try:
        async with session.get(f"https://raspmoskbt.ru/rasp/{wrong_form}", allow_redirects=False) as response:
            if response.status == 200:
                html_content = await response.text()
                soup = BeautifulSoup(html_content, 'html.parser')

                tbodies = soup.find_all('tbody')
                all_tables_data = []

                for tbody in tbodies:
                    rows = tbody.find_all('tr')
                    table_data = []

                    for row in rows:
                        cells = row.find_all('td')
                        row_data = []

                        for td in cells:
                            mso_normal_elements = td.find_all('p', class_="MsoNormal")
                            cell_texts = []

                            for element in mso_normal_elements:
                                spans = element.find_all('span')
                                row_text = ' '.join(
                                    normalize_text(span.get_text()) for span in spans if normalize_text(span.get_text())
                                )
                                if row_text:
                                    cell_texts.append(row_text)

                            combined_text = ' '.join(cell_texts)
                            row_data.append(normalize_text(combined_text))

                        if row_data:
                            table_data.append(row_data)

                    if table_data:
                        all_tables_data.append(table_data)

                return wrong_form, all_tables_data
            return None
    except Exception as e:
        print(f"Ошибка при обработке {wrong_form}: {e}")
        return None


async def main(decrease: int | None = None, increase: int | None = None) -> list:
    async with aiohttp.ClientSession() as session:
        backtrack = increase if increase is not None and decrease is None else -decrease if decrease is not None and increase is None else 0
        date_today = str(datetime.now().date() + timedelta(days=backtrack)).split("-")
        wrong_form = f"{date_today[2]}{mapping(date_today[1])}{date_today[0]}"
        results = await asyncio.gather(parse_schedule(session=session, wrong_form=wrong_form))
        return [r for r in results if r is not None]


def teacherparcer(results: list, surname: str):
    full_day = results[0][1]
    lessons = {}
    for sublist_index, sublist in enumerate(full_day):
        for item in sublist:
            pair_number = item[0]
            for index, element in enumerate(item):
                if index > 0 and surname in element:
                    if pair_number not in lessons:
                        lessons[pair_number] = []
                    subject_end = element.find(surname)
                    subject_name = normalize_text(element[:subject_end])
                    aud_match = re_search(r'ауд\.?\s*\d+[а-я]?', element, re_I)
                    classroom = normalize_text(aud_match.group(0)) if aud_match else ''
                    group = normalize_text(full_day[sublist_index][0][index])
                    lessons[pair_number].append((group, subject_name, classroom))
    return dict(sorted(lessons.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0))


def studentparcer(results: list, group: str):
    tables = results[0][1]
    schedule = []  # Список кортежей: (номер_пары, описание)

    for table in tables:
        if not table or len(table) < 2:
            continue

        header_row = table[0]
        col_index = None

        for i, header_cell in enumerate(header_row):
            if group in normalize_text(header_cell):
                col_index = i
                break

        if col_index is None:
            continue

        for row in table[1:]:
            if len(row) <= col_index:
                continue

            pair_number = normalize_text(row[0])
            subject_info = normalize_text(row[col_index])

            if subject_info:
                schedule.append((pair_number, subject_info))

    return schedule


def get_all_groups(results: list):
    all_groups = []
    for table in results[0][1]:
        if table and len(table) > 0:
            groups = [normalize_text(group, remove_spaces=True) for group in table[0][1:] if normalize_text(group)]
            if groups:
                all_groups.append(groups)
    return all_groups


def parse(
        decrease: int | None = None,
        increase: int | None = None,
        surname: str | None = None,
        group: str | None = None
):
    results = asyncio.run(main(decrease=decrease, increase=increase))
    if not results:
        raise Exception("Не удалось получить расписание")
    if surname and not group:
        return teacherparcer(results, surname)
    elif group and not surname:
        return studentparcer(results, group)
    else:
        return get_all_groups(results)