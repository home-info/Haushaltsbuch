import datetime, locale
import streamlit as st
import csv
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.ticker as ticker
import seaborn as sns
import numpy as np
import os, shutil

def SaveClear():
    if not Input_Category == "" or None:
        if not Input_Amount == 0:
            with tab1_status_col:
                st.success(f"Gespeichert: {Input_Date} | {Input_Category} | {Input_Amount:.2f} €")
            dataset = [str(Input_Date), str(Input_Category), float(Input_Amount)]
            with open("src/database.csv", "a", newline='') as db:
                writer = csv.writer(db)
                writer.writerow(dataset)
            db.close()
            st.session_state["DATE_KEY"] = f"{TODAY}"
            st.session_state["CATEGORY_KEY"] = ""
            st.session_state["AMOUNT_KEY"] = 0.00
        else:
            with tab1_status_col:
                st.error("Der Betrag darf nicht Null sein!")
    else:
        with tab1_status_col:
            st.error("Kategorie darf nicht leer sein!")

locale.setlocale(locale.LC_TIME, 'de_DE')
TODAY = datetime.date.today()

plt.style.use('seaborn-v0_8')

with open("src/default/DEFAULT_CATEGORIES", "r") as f:
    CategoryList = sorted([str(line.strip()) for line in f])
f.close()

tab1, tab2, tab3 = st.tabs(["Neue Ausgabe", "Jahresübersicht", "Budget"])

with tab1:
    st.title("Neue Ausgabe")

    tab1_col1, tab1_col2, tab1_col3 = st.columns(3)
    tab1_status_col = st.container()

    with tab1_col1:
        st.session_state.setdefault("DATUM", f"{TODAY}")
        Input_Date = st.text_input("Datum", key="DATUM_KEY")

    with tab1_col2:
        st.session_state.setdefault("KATEGORIE")
        Input_Category = st.selectbox("Kategorie", CategoryList, key="CATEGORY_KEY")

    with tab1_col3:
        st.session_state.setdefault("BETRAG", 0.00)
        Input_Amount = st.number_input(label="Betrag (€)", min_value=0.00, step=0.01, format="%.2f", key="AMOUNT_KEY")

    st.button("Speichern", on_click=SaveClear)

    with tab1_status_col:
        st.empty()

    st.divider()

    DataBase = pd.read_csv('src/database.csv', header=None, names=["Datum", "Kategorie", "Betrag"])
    DataBase = DataBase.sort_values('Datum', ascending=False)
    st.dataframe(DataBase, hide_index=True, column_config={"Betrag": st.column_config.NumberColumn(format="euro")})

with tab2:
    st.title("Jahresübersicht")

    df = pd.read_csv("src/database.csv", header=None, names=["Datum", "Kategorie", "Betrag"])
    df['Datum'] = pd.to_datetime(df['Datum'])
    df['Monat'] = df['Datum'].dt.strftime('%m-%Y')
    df['Betrag'] = df['Betrag'].astype(float)

    pivot = pd.pivot_table(
        df,
        values="Betrag",  # Werte, die aggregiert werden
        index="Monat",  # Monat
        columns="Kategorie",  # Kategorie
        aggfunc="sum",  # Aggregationsfunktion (Summe)
        fill_value=0,  # Fehlende Werte mit 0 füllen
        margins=True,  # Gesamtsummen für Zeilen und Spalten hinzufügen
        margins_name='SUMME',  # Name für die Gesamtsummen-Zeile/-Spalte
    )
    pivot2 = pd.pivot_table(
        df,
        values="Betrag",  # Werte, die aggregiert werden
        index="Kategorie",  # Monat
        columns="Monat",  # Kategorie
        aggfunc="sum",  # Aggregationsfunktion (Summe)
        fill_value=0,  # Fehlende Werte mit 0 füllen
        margins=True,  # Gesamtsummen für Zeilen und Spalten hinzufügen
        margins_name='SUMME',  # Name für die Gesamtsummen-Zeile/-Spalte
    )

    non_margin_columns = [col for col in pivot.columns if col != 'SUMME']
    sorted_columns = pivot[non_margin_columns].sum().sort_values(ascending=False).index
    new_column_order = list(sorted_columns) + ['SUMME']
    pivot = pivot[new_column_order]
    Pivot_Formatted = pivot.style.format('{:,.2f} €')

    tab2_col1, tab2_col2 = st.columns(2, border=True)

    with tab2_col1:
        Pivot_Categories_Sum = pivot2['SUMME'][:-1]
        Pivot_Categories_Sum = Pivot_Categories_Sum.sort_values(ascending=False)
        start_color = np.array([.86, .23, .15])
        end_color = np.array([.94, .74, .25])
        colors = [start_color, end_color]
        n_bins = len(Pivot_Categories_Sum)
        cmap = mcolors.LinearSegmentedColormap.from_list("custom", colors, N=n_bins)
        bar_colors = [cmap(i / (n_bins - 1)) for i in range(n_bins)]
        fig, ax = plt.subplots()
        Pivot_Categories_Sum.plot(kind='bar', ax=ax, color=bar_colors)
        plt.xlabel('')
        plt.xticks(rotation=-45, ha='left', rotation_mode='anchor')
        plt.title("Ausgaben nach Kategorie")
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x:,.0f} €'))
        st.pyplot(fig, use_container_width=True, clear_figure=True)

    with tab2_col2:
        v_08_palette = sns.color_palette("muted", n_colors=8)
        blue_color = v_08_palette[0]  # Erste Farbe (Blau-Äquivalent)
        red_color = v_08_palette[3]  # Vierte Farbe (Rot-Äquivalent)
        Pivot_Month_Sum = pivot['SUMME'][:-1]
        bar_colors = [red_color if value > 800 else blue_color for value in Pivot_Month_Sum]
        fig, ax = plt.subplots()
        Pivot_Month_Sum.plot(kind='bar', ax=ax, color=bar_colors)
        plt.xlabel('')
        plt.xticks(rotation=0)
        plt.title("Ausgaben nach Monat")
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x:,.0f} €'))
        st.pyplot(fig, use_container_width=True)

    st.write(Pivot_Formatted)

# Budget
with tab3:
    balance_sheet = {}
    balance = 0
    CurrentMonth = TODAY.strftime('%m-%Y')

    if not os.path.exists(f'src/overhead/{CurrentMonth}'):
        shutil.copy('src/default/DEFAULT_OVERHEAD', f'src/overhead/{CurrentMonth}')

    if not os.path.exists(f'src/revenues/{CurrentMonth}'):
        shutil.copy('src/default/DEFAULT_REVENUES', f'src/revenues/{CurrentMonth}')

    for entry in sorted(os.listdir('src/overhead')):
        Overhead_FilePath = f'src/overhead/{entry}'
        Overhead_FileName = Overhead_FilePath.rsplit('/', 1)[1]
        if not Overhead_FileName.startswith("."):
            LoopingMonth = Overhead_FileName

            Overhead_Data = pd.read_csv(Overhead_FilePath, header=None, names=['Kostenpunkt', 'Betrag'])
            Overhead_Data = Overhead_Data.sort_values('Betrag', ascending=False)
            Overhead_Sum = Overhead_Data['Betrag'].sum()

            Expenses_Sum = pivot.loc[LoopingMonth]['SUMME']
            Expenses_Data = sorted([(Expenses_Category, pivot.loc[LoopingMonth][Expenses_Category]) for Expenses_Category in pivot.columns[:-1] if pivot.loc[LoopingMonth][Expenses_Category] != 0], key=lambda x: x[1], reverse=True)

            Revenue_Data = pd.read_csv(f'src/revenues/{LoopingMonth}', header=None, names=['Quelle', 'Betrag'])
            Revenue_Data = Revenue_Data.sort_values('Betrag', ascending=False)
            Revenue_Sum = Revenue_Data['Betrag'].sum()

            PreMonthBalance = balance
            budget = Revenue_Sum + PreMonthBalance - Overhead_Sum
            balance = Revenue_Sum + PreMonthBalance - Overhead_Sum - Expenses_Sum

            balance_sheet[LoopingMonth] = {
                'Revenue': float(Revenue_Sum),
                'Revenue_Data': Revenue_Data,
                'Overhead': float(Overhead_Sum * -1),
                'Overhead_Data': Overhead_Data,
                'Expenses': float(Expenses_Sum * -1),
                'Expenses_Data': Expenses_Data,
                'Budget': float(budget),
                'PreMonthBalance': float(PreMonthBalance),
                'Balance': float(balance)
            }

    st.title("Budget")
    for month in reversed(balance_sheet):
        Month_Verbal = datetime.datetime.strptime(month, "%m-%Y").strftime("%B %Y")
        with st.container(border=True):
            st.subheader(Month_Verbal)

            subcol1, subcol2 = st.columns(2, border=True)
            subcol3, subcol4 = st.columns(2, border=True)

            with subcol1:
                monthly_data = {
                    "Position": ["Bilanz aus Vormonat", "Einnahmen", "Fixkosten", "Ausgaben", "BILANZ"],
                    "Betrag": [balance_sheet[month]['PreMonthBalance'], balance_sheet[month]['Revenue'], balance_sheet[month]['Overhead'], balance_sheet[month]['Expenses'], balance_sheet[month]['Balance']]
                }
                monthly_data = pd.DataFrame(monthly_data)

                if balance_sheet[month]['Balance'] >= 0:
                    st.html(
                        # f"<div style='display: flex; justify-content: space-between;'><span><b>Von {balance_sheet[month]['Budget']:,.2f} € noch verfügbar:</b></span> <span style='background-color: #ebf2fb; border-radius: 5px; padding: 2px 5px;'><b>{balance_sheet[month]['Balance']:,.2f} €</b></span></div>")
                        f"<div style='display: flex; justify-content: space-between;'><span><b>Noch verfügbares Budget:</b></span> <span style='background-color: #ebf2fb; border-radius: 5px; padding: 2px 5px;'><b>{balance_sheet[month]['Balance']:,.2f} €</b></span></div>")
                        # st.markdown(f"**Noch :blue-background[{balance_sheet[month]['Balance']:.2f} €] von {balance_sheet[month]['Budget']:.2f} € verfügbar.**")
                    used_budget = (1 - (balance_sheet[month]['Balance'] / balance_sheet[month]['Budget']))
                    st.progress(used_budget, text=f'{used_budget*100:.0f} % vom Budget sind bereits ausgegeben.')
                else:
                    # st.markdown(f"**Noch :grey-background[0.00 €] von {balance_sheet[month]['Budget']:.2f} € verfügbar.**")
                    st.html(f"<div style='display: flex; justify-content: space-between;'><span><b>Noch verfügbares Budget:</b></span> <span style='background-color: #f2f2f4; border-radius: 5px; padding: 2px 5px;'><b>0.00 €</b></span></div>")
                    st.progress(100, text=f'Budget vollständig ausgegeben oder überzogen.')
                st.write(" ")
                st.dataframe(monthly_data, hide_index=True, column_config={"Betrag": st.column_config.NumberColumn(format="euro")})

            with subcol2:
                # st.markdown(f"**Einnahmen: :green-background[{balance_sheet[month]['Revenue']:,.2f} €]**")
                st.html(f"<div style='display: flex; justify-content: space-between;'><span><b>Einnahmen:</b></span> <span style='background-color: #eef9ef; border-radius: 5px; padding: 2px 5px;'><b>{balance_sheet[month]['Revenue']:,.2f} €</b></span></div>")
                st.dataframe(balance_sheet[month]['Revenue_Data'], hide_index=True, column_config={"Betrag": st.column_config.NumberColumn(format="euro")})

            with subcol3:
                st.html(f"<div style='display: flex; justify-content: space-between;'><span><b>Fixkosten:</b></span> <span style='background-color: #fdeceb; border-radius: 5px; padding: 2px 5px;'><b>{balance_sheet[month]['Overhead']:,.2f} €</b></span></div>")
                st.dataframe(balance_sheet[month]['Overhead_Data'], hide_index=True, column_config={"Betrag": st.column_config.NumberColumn(format="euro")})

            with subcol4:
                st.html(f"<div style='display: flex; justify-content: space-between;'><span><b>Ausgaben:</b></span> <span style='background-color: #fdeceb; border-radius: 5px; padding: 2px 5px;'><b>{balance_sheet[month]['Expenses']:,.2f} €</b></span></div>")
                MonthlyExpenses_Category, MonthlyExpenses_CategorySum = zip(*balance_sheet[month]['Expenses_Data'])

                start_color = np.array([.86, .23, .15])
                end_color = np.array([.94, .74, .25])
                colors = [start_color, end_color]
                n_bins = len(MonthlyExpenses_Category)
                cmap = mcolors.LinearSegmentedColormap.from_list("custom", colors, N=n_bins)
                bar_colors = [cmap(i / (n_bins - 1)) for i in range(n_bins)]
                fig, ax = plt.subplots()
                ax.bar(MonthlyExpenses_Category, MonthlyExpenses_CategorySum, color=bar_colors)
                plt.xlabel('')
                plt.xticks(rotation=-45, ha='left', rotation_mode='anchor')
                plt.title(f"Ausgaben im {Month_Verbal}")
                ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x:,.0f} €'))
                st.pyplot(fig, use_container_width=True, clear_figure=True)
