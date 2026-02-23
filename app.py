from flask import Flask, render_template, request, redirect, send_file, session
import mysql.connector
import pandas as pd
import io

app = Flask(__name__)
app.secret_key = "secretkey"

# -------------------- DATABASE CONFIG --------------------
db_config = {
    'host': '192.168.1.22',
    'port': '3306',
    'user': 'avadh',
    'password': 'Avadh!@#123',
    'database': 'test'
}

# ==================== LOGIN ====================
@app.route('/', methods=['GET', 'POST'])
def login():
    error = None

    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password'].strip()

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT Email, PortType, HsCode FROM Users WHERE Email=%s AND Password=%s",
            (email, password)
        )

        users = cursor.fetchall()
        cursor.close()
        conn.close()

        if users:
            session['users'] = users

            # If only one PortType
            if len(users) == 1:
                session['user'] = users[0]['Email']
                session['port_type'] = users[0]['PortType']
                session['hs_code'] = users[0]['HsCode']
                return redirect('/dashboard')

            # If multiple PortTypes
            return render_template('choose_port.html', users=users)

        else:
            error = "Invalid email or password"

    return render_template('login.html', error=error)


# ==================== SELECT PORT ====================
@app.route('/select_port', methods=['POST'])
def select_port():
    index = int(request.form['port_selection'])
    selected_user = session['users'][index]

    session['user'] = selected_user['Email']
    session['port_type'] = selected_user['PortType']
    session['hs_code'] = selected_user['HsCode']

    return redirect('/dashboard')


# ==================== DASHBOARD ====================
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():

    if 'user' not in session:
        return redirect('/')

    user_hs_code = str(session['hs_code'])
    port_type_raw = session['port_type'].lower()

    # ---------- AUTO TABLE DETECTION ----------
    if 'sez' in port_type_raw:
        if 'import' in port_type_raw:
            table_name = 'SEZ_I_Off_Jan26'
            display_type = 'SEZ Import'
        else:
            table_name = 'Sez_E_Off_jan26'
            display_type = 'SEZ Export'
    else:
        if 'import' in port_type_raw:
            table_name = 'Monthly_import_off_1to31th_Jan26'
            display_type = 'Import'
        else:
            table_name = 'Monthly_Export_Offline_Jan26'
            display_type = 'Export'

    # ---------- DOWNLOAD ----------
    if request.method == 'POST':
        hs_code_input = request.form['hs_code'].strip()
        hs_filter = f"{hs_code_input}%" if hs_code_input else f"{user_hs_code}%"

        conn = mysql.connector.connect(**db_config)

        query = f"SELECT * FROM `{table_name}` WHERE `HS Code` LIKE %s"
        df = pd.read_sql(query, conn, params=[hs_filter])

        conn.close()

        if df.empty:
            return f"No data found for HS Code: {hs_filter} in {display_type}"

        output = io.BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)

        return send_file(
            output,
            download_name=f"{display_type}_data.xlsx",
            as_attachment=True
        )

    return render_template(
        'dashboard.html',
        user_port_type=display_type,
        user_hs_code=user_hs_code
    )


# ==================== CHANGE PORT ====================
@app.route('/change_port')
def change_port():
    if 'users' in session:
        return render_template('choose_port.html', users=session['users'])
    return redirect('/')


# ==================== LOGOUT ====================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# ==================== RUN APP ====================
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=False)
    