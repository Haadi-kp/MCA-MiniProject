from flask import Flask, render_template, request, redirect, session, flash, jsonify
import os
from datetime import timedelta  # used for setting session timeout
import pandas as pd
import plotly
import plotly.express as px
import json
import warnings
import pymysql
import support

warnings.filterwarnings("ignore")

# Database connection setup
db = pymysql.connect(
    host="localhost",
    user="root",
    password="",
    database="personal_finance_management_system"
)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)

# Helper function to execute queries (based on your previous support.execute_query logic)
def execute_query(query_type, query):
    try:
        cursor = db.cursor()
        cursor.execute(query)
        if query_type == "search":
            result = cursor.fetchall()
            cursor.close()
            return result
        elif query_type == "insert":
            db.commit()
            cursor.close()
    except Exception as e:
        print(f"An error occurred: {e}")
        db.rollback()


@app.route('/')
def login():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=15)
    if 'user_id' in session:  # if logged-in
        flash("Already a user is logged-in!")
        return redirect('/home')
    else:  # if not logged-in
        return render_template("login.html")


@app.route('/login_validation', methods=['POST'])
def login_validation():
    if 'user_id' not in session:  # if user not logged-in
        email = request.form.get('email')
        passwd = request.form.get('password')
        query = """SELECT * FROM user_login WHERE email LIKE '{}' AND password LIKE '{}'""".format(email, passwd)
        users = execute_query("search", query)
        if len(users) > 0:  # if user details matched in db
            session['user_id'] = users[0][0]
            return redirect('/home')
        else:  # if user details not matched in db
            flash("Invalid email and password!")
            return redirect('/')
    else:  # if user already logged-in
        flash("Already a user is logged-in!")
        return redirect('/home')


@app.route('/reset', methods=['POST'])
def reset():
    if 'user_id' not in session:
        email = request.form.get('femail')
        pswd = request.form.get('pswd')
        userdata = execute_query('search', """select * from user_login where email LIKE '{}'""".format(email))
        if len(userdata) > 0:
            try:
                query = """update user_login set password = '{}' where email = '{}'""".format(pswd, email)
                execute_query('insert', query)
                flash("Password has been changed!!")
                return redirect('/')
            except:
                flash("Something went wrong!!")
                return redirect('/')
        else:
            flash("Invalid email address!!")
            return redirect('/')
    else:
        return redirect('/home')


@app.route('/register')
def register():
    if 'user_id' in session:  # if user is logged-in
        flash("Already a user is logged-in!")
        return redirect('/home')
    else:  # if not logged-in
        return render_template("register.html")


@app.route('/registration', methods=['POST'])
def registration():
    if 'user_id' not in session:  # if not logged-in
        name = request.form.get('name')
        email = request.form.get('email')
        passwd = request.form.get('password')
        if len(name) > 5 and len(email) > 10 and len(passwd) > 5:  # if input details satisfy length condition
            try:
                query = """INSERT INTO user_login(username, email, password) VALUES('{}','{}','{}')""".format(name,
                                                                                                              email,
                                                                                                              passwd)
                execute_query('insert', query)

                user = execute_query('search',
                                     """SELECT * from user_login where email LIKE '{}'""".format(email))
                session['user_id'] = user[0][0]  # set session on successful registration
                flash("Successfully Registered!!")
                return redirect('/home')
            except:
                flash("Email id already exists, use another email!!")
                return redirect('/register')
        else:  # if input condition length not satisfy
            flash("Not enough data to register, try again!!")
            return redirect('/register')
    else:  # if already logged-in
        flash("Already a user is logged-in!")
        return redirect('/home')


@app.route('/contact')
def contact():
    return render_template("contact.html")


@app.route('/feedback', methods=['POST'])
def feedback():
    name = request.form.get("name")
    email = request.form.get("email")
    phone = request.form.get("phone")
    sub = request.form.get("sub")
    message = request.form.get("message")
    flash("Thanks for reaching out to us. We will contact you soon.")
    return redirect('/')


@app.route('/home')
def home():
    if 'user_id' in session:  # if user is logged-in
        query = """select * from user_login where user_id = {} """.format(session['user_id'])
        userdata = execute_query("search", query)

        table_query = """select * from user_expenses where user_id = {} order by pdate desc""".format(
            session['user_id'])
        table_data = execute_query("search", table_query)
        df = pd.DataFrame(table_data, columns=['#', 'User_Id', 'Date', 'Expense', 'Amount', 'Note'])

        df = support.generate_df(df)
        try:
            earning, spend, invest, saving = support.top_tiles(df)
        except:
            earning, spend, invest, saving = 0, 0, 0, 0

        try:
            bar, pie, line, stack_bar = support.generate_Graph(df)
        except:
            bar, pie, line, stack_bar = None, None, None, None
        try:
            monthly_data = support.get_monthly_data(df, res=None)
        except:
            monthly_data = []
        try:
            card_data = support.sort_summary(df)
        except:
            card_data = []

        try:
            goals = support.expense_goal(df)
        except:
            goals = []
        try:
            size = 240
            pie1 = support.makePieChart(df, 'Earning', 'Month_name', size=size)
            pie2 = support.makePieChart(df, 'Spend', 'Day_name', size=size)
            pie3 = support.makePieChart(df, 'Investment', 'Year', size=size)
            pie4 = support.makePieChart(df, 'Saving', 'Note', size=size)
            pie5 = support.makePieChart(df, 'Saving', 'Day_name', size=size)
            pie6 = support.makePieChart(df, 'Investment', 'Note', size=size)
        except:
            pie1, pie2, pie3, pie4, pie5, pie6 = None, None, None, None, None, None
        return render_template('home.html',
                               user_name=userdata[0][1],
                               df_size=df.shape[0],
                               df=jsonify(df.to_json()),
                               earning=earning,
                               spend=spend,
                               invest=invest,
                               saving=saving,
                               monthly_data=monthly_data,
                               card_data=card_data,
                               goals=goals,
                               table_data=table_data[:4],
                               bar=bar,
                               line=line,
                               stack_bar=stack_bar,
                               pie1=pie1,
                               pie2=pie2,
                               pie3=pie3,
                               pie4=pie4,
                               pie5=pie5,
                               pie6=pie6,
                               )
    else:  # if not logged-in
        return redirect('/')


@app.route('/home/add_expense', methods=['POST'])
def add_expense():
    if 'user_id' in session:
        user_id = session['user_id']
        if request.method == 'POST':
            date = request.form.get('e_date')
            expense = request.form.get('e_type')
            amount = request.form.get('amount')
            notes = request.form.get('notes')
            try:
                query = """insert into user_expenses (user_id, pdate, expense, amount, pdescription) values 
                ({}, '{}','{}',{},'{}')""".format(user_id, date, expense, amount, notes)
                execute_query('insert', query)
                flash("Saved!!")
            except:
                flash("Something went wrong.")
                return redirect("/home")
            return redirect('/home')
    else:
        return redirect('/')

@app.route('/home/add_income', methods=['POST'])
def add_income():
    if 'user_id' in session:
        user_id = session['user_id']
        if request.method == 'POST':
            date = request.form.get('i_date')
            income = request.form.get('income')
            details = request.form.get('details')
            try:
                query = """INSERT INTO income (user_id, income, details, date) VALUES 
                ('{}', {}, '{}', '{}')""".format(user_id, income, details, date)
                execute_query('insert', query)
                flash("Income Added Successfully!")
            except Exception as e:
                flash(f"Something went wrong: {e}")
                return redirect("/home")
            return redirect('/home')
    else:
        return redirect('/')



@app.route('/analysis')
def analysis():
    if 'user_id' in session:  # if already logged-in
        user_id = session['user_id']
        
        # Retrieve user data
        query = f"SELECT * FROM user_login WHERE user_id = {user_id}"
        userdata = execute_query('search', query)
        
        # Retrieve user expenses data
        query2 = f"SELECT pdate, expense, pdescription, amount FROM user_expenses WHERE user_id = {user_id}"
        data = execute_query('search', query2)
        
        # Create DataFrame
        df = pd.DataFrame(data, columns=['Date', 'Expense', 'Note', 'Amount(₹)'])
        df = support.generate_df(df)

        # Convert Timestamps to strings
        df['Date'] = df['Date'].astype(str)

        if df.shape[0] > 0:
            try:
                # Generate graphs
                bar, pie, line, stack_bar = support.generate_Graph(df)
            except Exception as e:
                print(f"Error generating graphs: {e}")
                bar, pie, line, stack_bar = None, None, None, None
            
            try:
                # Get monthly data
                monthly_data = support.get_monthly_data(df, res=None)
            except Exception as e:
                print(f"Error getting monthly data: {e}")
                monthly_data = []
            
            try:
                # Sort and summarize data
                card_data = support.sort_summary(df)
            except Exception as e:
                print(f"Error sorting summary: {e}")
                card_data = []
            
            try:
                # Get expense goals
                goals = support.expense_goal(df)
            except Exception as e:
                print(f"Error getting goals: {e}")
                goals = []

            try:
                # Generate pie charts
                size = 240
                pie1 = support.makePieChart(df, 'Earning', 'Month_name', size=size)
                pie2 = support.makePieChart(df, 'Spend', 'Day_name', size=size)
                pie3 = support.makePieChart(df, 'Investment', 'Year', size=size)
                pie4 = support.makePieChart(df, 'Saving', 'Note', size=size)
                pie5 = support.makePieChart(df, 'Saving', 'Day_name', size=size)
                pie6 = support.makePieChart(df, 'Investment', 'Note', size=size)
            except Exception as e:
                print(f"Error generating pie charts: {e}")
                pie1, pie2, pie3, pie4, pie5, pie6 = None, None, None, None, None, None

            return render_template('analysis.html',
                                   df_size=df.shape[0],
                                   df=json.dumps(df.to_dict(orient='records')),  # Convert DataFrame to JSON
                                   monthly_data=monthly_data,
                                   card_data=card_data,
                                   goals=goals,
                                   bar=bar,
                                   line=line,
                                   stack_bar=stack_bar,
                                   pie1=pie1,
                                   pie2=pie2,
                                   pie3=pie3,
                                   pie4=pie4,
                                   pie5=pie5,
                                   pie6=pie6)
        else:
            flash("Not enough data to analyze.")
            return redirect('/home')
    else:
        return redirect('/')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("Logged out successfully!!")
    return redirect('/')


if __name__ == "__main__":
    app.run(debug=True)
