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
import pickle
from num2words import num2words
from passlib.hash import bcrypt
import re
from github import Github


# Function to verify login credentials
def check_credentials(username, password):
    try:
        users = pd.read_csv("src/users.csv")
        user_row = users[users["username"] == username]
        if not user_row.empty:
            stored_password = user_row.iloc[0]["password"]
            return bcrypt.verify(password, stored_password)
        return False
    except FileNotFoundError:
        st.error("Benutzerdatenbank nicht gefunden!")
        return False


# Initialize session state for authentication
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""


# Login page
def login_page():
    st.title("Login")
    with st.form(key="login_form"):
        username = st.text_input("Benutzername")
        password = st.text_input("Passwort", type="password")
        submit = st.form_submit_button("Einloggen")

        if submit:
            if check_credentials(username, password):
                st.session_state["authenticated"] = True
                st.rerun()  # Refresh to show main app
            else:
                st.error("Benutzername oder Passwort falsch!")


# Logout function
def logout():
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""
    st.rerun()


# Main app content (your original code, wrapped in authentication check)
def main_app():
    # === GitHub Setup ===
    GITHUB_TOKEN = st.secrets["GitHubToken"]
    REPO_NAME = "home-info/haushaltsbuch"
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)

    monatsname = {
        "01": "Januar",
        "02": "Februar",
        "03": "März",
        "04": "April",
        "05": "Mai",
        "06": "Juni",
        "07": "Juli",
        "08": "August",
        "09": "September",
        "10": "Oktober",
        "11": "November",
        "12": "Dezember"
    }

    def ersetze_monate(match):
        monat = match.group(1)
        return monatsname.get(monat, monat) + " "
    
    plt.style.use('seaborn-v0_8')

    with open("src/default/DEFAULT_CATEGORIES", "r") as f:
        CategoryList = sorted([str(line.strip()) for line in f])
    f.close()

    tab1, tab2, tab3, tab4 = st.tabs(["Neue Ausgabe", "Jahresübersicht", "Budget", "Sparziele"])

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
                with open("src/database.csv", "rb") as local_file:
                    new_file = local_file.read()
                contents = repo.get_contents('src/database.csv')
                repo.update_file(contents.path, "Overwrite with new file", new_file, contents.sha)

                st.session_state["DATE_KEY"] = f"{TODAY}"
                st.session_state["CATEGORY_KEY"] = ""
                st.session_state["AMOUNT_KEY"] = 0.00
            else:
                with tab1_status_col:
                    st.error("Der Betrag darf nicht Null sein!")
        else:
            with tab1_status_col:
                st.error("Kategorie darf nicht leer sein!")


    with tab1:
        TODAY = datetime.date.today()
        st.title("Neue Ausgabe")

        with st.container(border=True):
            tab1_col1, tab1_col2, tab1_col3 = st.columns(3)
            tab1_status_col = st.container()
            with tab1_col1:
                st.session_state.setdefault("DATUM_KEY", f"{TODAY}")
                Input_Date = st.text_input("Datum", key="DATUM_KEY")

            with tab1_col2:
                st.session_state.setdefault("CATEGORY_KEY", "")
                Input_Category = st.selectbox("Kategorie", CategoryList, key="CATEGORY_KEY")

            with tab1_col3:
                st.session_state.setdefault("AMOUNT_KEY", 0.00)
                Input_Amount = st.number_input(label="Betrag (€)", min_value=0.00, step=0.01, format="%.2f",
                                               key="AMOUNT_KEY")

            st.button("Speichern", on_click=SaveClear)

            with tab1_status_col:
                st.empty()

        DataBase = pd.read_csv('src/database.csv', header=None, names=["Datum", "Kategorie", "Betrag"])
        DataBase = DataBase.sort_values('Datum', ascending=False)
        st.dataframe(DataBase, hide_index=True, column_config={"Betrag": st.column_config.NumberColumn(format="euro")})

        #Add logout button
        st.button("Ausloggen", on_click=logout)

    with tab2:
        st.title("Jahresübersicht")
        df = pd.read_csv("src/database.csv", header=None, names=["Datum", "Kategorie", "Betrag"])
        df['Datum'] = pd.to_datetime(df['Datum'])
        df['Monat'] = df['Datum'].dt.strftime('%m-%Y')
        df['Betrag'] = df['Betrag'].astype(float)

        pivot = pd.pivot_table(
            df,
            values="Betrag",
            index="Monat",
            columns="Kategorie",
            aggfunc="sum",
            fill_value=0,
            margins=True,
            margins_name='SUMME',
        )
        pivot2 = pd.pivot_table(
            df,
            values="Betrag",
            index="Kategorie",
            columns="Monat",
            aggfunc="sum",
            fill_value=0,
            margins=True,
            margins_name='SUMME',
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
            blue_color = v_08_palette[0]
            red_color = v_08_palette[3]
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

    with tab3:
        balance_sheet = {}
        balance = 0
        CurrentMonth = TODAY.strftime('%m-%Y')

        if not os.path.exists(f'src/overhead/{CurrentMonth}'):
            with open('src/default/DEFAULT_OVERHEAD', 'rb') as f:
                new_file = f.read()
            repo.create_file(f'src/overhead/{CurrentMonth}', 'new file', new_file)

        if not os.path.exists(f'src/revenues/{CurrentMonth}'):
            # shutil.copy('src/default/DEFAULT_REVENUES', f'src/revenues/{CurrentMonth}')
            with open('src/default/DEFAULT_REVENUES', 'rb') as f:
                new_file = f.read()
            repo.create_file(f'src/revenues/{CurrentMonth}', 'new file', new_file)

        for entry in sorted(os.listdir('src/overhead')):
            Overhead_FilePath = f'src/overhead/{entry}'
            Overhead_FileName = Overhead_FilePath.rsplit('/', 1)[1]
            if not Overhead_FileName.startswith("."):
                LoopingMonth = Overhead_FileName

                Overhead_Data = pd.read_csv(Overhead_FilePath, header=None, names=['Kostenpunkt', 'Betrag'])
                Overhead_Data = Overhead_Data.sort_values('Betrag', ascending=False)
                Overhead_Sum = Overhead_Data['Betrag'].sum()

                try:
                    Expenses_Sum = pivot.loc[LoopingMonth]['SUMME']
                    Expenses_Data = sorted(
                        [(Expenses_Category, pivot.loc[LoopingMonth][Expenses_Category]) for Expenses_Category in
                         pivot.columns[:-1] if pivot.loc[LoopingMonth][Expenses_Category] != 0], key=lambda x: x[1],
                        reverse=True)
                except:
                    Expenses_Sum = 0
                    Expenses_Data = [("", 0)]

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
            Month_Verbal = re.sub(r'\b(0[1-9]|1[0-2])-', ersetze_monate, month)

            with st.container(border=True):
                st.subheader(Month_Verbal)

                subcol1, subcol2 = st.columns(2, border=True)
                subcol3, subcol4 = st.columns(2, border=True)

                with subcol1:
                    monthly_data = {
                        "Position": ["Bilanz aus Vormonat", "Einnahmen", "Fixkosten", "Ausgaben", "BILANZ"],
                        "Betrag": [balance_sheet[month]['PreMonthBalance'], balance_sheet[month]['Revenue'],
                                   balance_sheet[month]['Overhead'], balance_sheet[month]['Expenses'],
                                   balance_sheet[month]['Balance']]
                    }
                    monthly_data = pd.DataFrame(monthly_data)

                    if balance_sheet[month]['Balance'] >= 0:
                        st.html(f"<div style='display: flex; justify-content: space-between;'><span><b>Noch verfügbares Budget:</b></span> <span style='color: black !important; background-color: #b2ebb8; border-radius: 5px; padding: 2px 5px;'><b>{balance_sheet[month]['Balance']:,.2f} €</b></span></div>")
                        used_budget = (1 - (balance_sheet[month]['Balance'] / balance_sheet[month]['Budget']))
                        st.progress(used_budget, text=f'{used_budget * 100:.0f} % vom Budget sind bereits ausgegeben.')
                    else:
                        st.html(f"<div style='display: flex; justify-content: space-between;'><span><b>Noch verfügbares Budget:</b></span> <span style='color: black !important; background-color: #f2f2f4; border-radius: 5px; padding: 2px 5px;'><b>0.00 €</b></span></div>")  # f2f2f4
                        st.progress(100, text=f'Budget vollständig ausgegeben oder überzogen.')
                    st.write(" ")
                    st.dataframe(monthly_data, hide_index=True,
                                 column_config={"Betrag": st.column_config.NumberColumn(format="euro")})

                with subcol2:
                    st.html(f"<div style='display: flex; justify-content: space-between;'><span><b>Einnahmen:</b></span> <span style='color: black !important; background-color: #b2ebb8; border-radius: 5px; padding: 2px 5px;'><b>{balance_sheet[month]['Revenue']:,.2f} €</b></span></div>")  # eef9ef
                    st.dataframe(balance_sheet[month]['Revenue_Data'], hide_index=True,
                                 column_config={"Betrag": st.column_config.NumberColumn(format="euro")})

                with subcol3:
                    st.html(f"<div style='display: flex; justify-content: space-between;'><span><b>Fixkosten:</b></span> <span style='color: black !important; background-color: #fac1be; border-radius: 5px; padding: 2px 5px;'><b>{balance_sheet[month]['Overhead']:,.2f} €</b></span></div>")  # fdeceb
                    st.dataframe(balance_sheet[month]['Overhead_Data'], hide_index=True,
                                 column_config={"Betrag": st.column_config.NumberColumn(format="euro")})

                with subcol4:
                    st.html(f"<div style='display: flex; justify-content: space-between;'><span><b>Ausgaben:</b></span> <span style='color: black !important; background-color: #fac1be; border-radius: 5px; padding: 2px 5px;'><b>{balance_sheet[month]['Expenses']:,.2f} €</b></span></div>")  # fdeceb
                    try:
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
                    except:
                        pass

    with tab4:
        st.title("Sparziele")

        with open("src/savings/kontostand", "r") as f:
            Kontostand_Ist = float(f.read())
        f.close()

        kontostand_container = st.container(border=True)

        Target_Index = 0
        Kontostand_Soll = 0

        with open('src/savings/SavingTargets.pkl', 'rb') as f:
            st.session_state.SavingsDict = pickle.load(f)
        f.close()

        for target in sorted(st.session_state.SavingsDict):
            if st.session_state.SavingsDict[target]['status'] == False:
                Target_Index += 1
                Target_PayIn_Sum = st.session_state.SavingsDict[target]['einzahlungen']['Betrag'].sum()
                Kontostand_Soll += Target_PayIn_Sum
                Target_PayOut_Sum = st.session_state.SavingsDict[target]['auszahlungen']['Betrag'].sum()
                Kontostand_Soll -= Target_PayOut_Sum

                with st.expander(label=f":{num2words(Target_Index)}:&nbsp;&nbsp;&nbsp;**{st.session_state.SavingsDict[target]['name']}**"):
                    st.html(f"<div style='margin-bottom: 0px; display: flex; justify-content: space-between;'><span><h1>{st.session_state.SavingsDict[target]['name']}</h1></span><span style='text-align: right'><h1>{Target_PayIn_Sum:,.2f}&nbsp;€ von {st.session_state.SavingsDict[target]['ziel_summe']:,.2f}&nbsp;€</h1></span></div>")

                    progress = Target_PayIn_Sum / st.session_state.SavingsDict[target]['ziel_summe']
                    st.html(f"<div style='margin-bottom: -25px; display: flex; justify-content: space-between;'><span>Sparziel zu {progress * 100:.0f}&nbsp;%&nbsp;erreicht</span><span style='text-align: right'>Noch {st.session_state.SavingsDict[target]['ziel_summe'] - Target_PayIn_Sum:,.2f}&nbsp;€</span></div>")
                    if progress > 1:
                        st.progress(100)
                    elif progress < 0:
                        st.progress(0)
                    else:
                        st.progress(progress)

                    target_col1, target_col2 = st.columns(2)
                    with target_col1:
                        st.html(f"<div style='margin-bottom: -30px; display: flex; justify-content: space-between;'><span><h3>Einzahlungen:</h3></span><span style='text-align: right'><h3>{Target_PayIn_Sum:,.2f} €</h3></span></div>")

                        editor = st.data_editor(
                                st.session_state.SavingsDict[target]['einzahlungen'],
                                hide_index=True,
                                num_rows="dynamic",
                                column_config={"Betrag": st.column_config.NumberColumn(format="%.2f €", step=0.01)},
                                key=f"editor_einzahlung_{target}",
                                use_container_width=True
                            )
                        st.session_state.SavingsDict[target]['einzahlungen'] = editor
                        st.write(st.session_state.SavingsDict[target]['einzahlungen'])
            #
            # if st.button('Änderungen speichern', key=f"button_{termin}"):
            #     with open('src/savings/SavingTargets.pkl', 'wb') as f:
            #         new_data = st.session_state.SavingsDict
            #         pickle.dump(new_data, f)
            #     f.close()






        # with kontostand_container:
        #     st.subheader("Kontostand")
        #     kontostand_container_col1, kontostand_container_col2 = st.columns([5, 1])
        #     with kontostand_container_col1:
        #         st.html(
        #             f"<div style='margin-bottom: -15px; display: flex; justify-content: space-between;'><span><b>Aktueller Kontostand:</b></span></div>")
        #         Kontostand_Ist_Input = st.number_input(label="Aktueller Kontostand (€)", format="%.2f",
        #                                                value=Kontostand_Ist, label_visibility='collapsed')
        #     with kontostand_container_col2:
        #         st.html(
        #             f"<div style='margin-bottom: -15px; display: flex; justify-content: space-between;'><span><b>&nbsp;</b></span></div>")
        #         if st.button("Speichern", key="kontostand-speichern"):
        #             Kontostand_Ist = Kontostand_Ist_Input
        #             with open('src/savings/kontostand', 'w') as f:
        #                 f.write(str(Kontostand_Ist))
        #             f.close()
        #             with open('src/savings/kontostand', "rb") as local_file:
        #                 new_file = local_file.read()
        #             local_file.close()
        #             contents = repo.get_contents('src/savings/kontostand')
        #             repo.update_file(contents.path, "Overwrite with new file", new_file, contents.sha)
        #             st.rerun()
        #
        #     Kontostand_Differenz = Kontostand_Ist - Kontostand_Soll
        #
        #     with kontostand_container_col1:
        #         if Kontostand_Differenz == 0:
        #             st.html(
        #                 f"<div style='display: flex; justify-content: space-between;'><span>Kontostand Soll:&nbsp;&nbsp;&nbsp;<b>{Kontostand_Soll:,.2f}&nbsp;€</b></span> <span style='color: black !important; background-color: #f2f2f4; border-radius: 5px; padding: 2px 5px;'><b>± 0.00&nbsp;€</b></span></div>")  # f2f2f4
        #         if Kontostand_Differenz > 0:
        #             st.html(
        #                 f"<div style='display: flex; justify-content: space-between;'><span>Kontostand Soll:&nbsp;&nbsp;&nbsp;<b>{Kontostand_Soll:,.2f}&nbsp;€</b></span> <span style='color: black !important; background-color: #b2ebb8; border-radius: 5px; padding: 2px 5px;'><b>+ {Kontostand_Differenz:,.2f}&nbsp;€</b></span></div>")
        #         if Kontostand_Differenz < 0:
        #             st.html(
        #                 f"<div style='display: flex; justify-content: space-between;'><span>Kontostand Soll:&nbsp;&nbsp;&nbsp;<b>{Kontostand_Soll:,.2f}&nbsp;€</b></span> <span style='color: black !important; background-color: #fac1be; border-radius: 5px; padding: 2px 5px;'><b>– {Kontostand_Differenz * -1:,.2f}&nbsp;€</b></span></div>")

# Display login page or main app based on authentication status
if not st.session_state["authenticated"]:
    login_page()
else:
    main_app()