from flask import Flask, render_template, request, redirect, send_file, session
import mysql.connector
import pandas as pd
import io

app = Flask(__name__)
app.secret_key = "supersecretkey123"

# -------------------- DATABASE CONFIG --------------------


db_config = {
    'host': '122.180.251.28',
    'port': '3306',
    'user': 'avadh',
    'password': 'Avadh!@#123',
    'database': 'test'
}

# -------------------- LOGIN PAGE --------------------
@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password'].strip()

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT DISTINCT Email, Password, HsCode, PortType FROM Users WHERE Email=%s AND Password=%s",
            (email, password)
        )
        users = cursor.fetchall()
        cursor.close()
        conn.close()

        if users:
            session['users'] = users
            if len(users) == 1:
                session['user'] = users[0]['Email']
                session['port_type'] = users[0]['PortType']
                session['hs_code'] = users[0]['HsCode']
                return redirect('/dashboard')
            else:
                return render_template('choose_port.html', users=users)
        else:
            error = "Invalid Email or Password"

    return render_template('login.html', error=error)


# -------------------- SELECT PORT --------------------
@app.route('/select_port', methods=['POST'])
def select_port():
    index = int(request.form['port_selection'])
    selected_user = session['users'][index]

    session['user'] = selected_user['Email']
    session['port_type'] = selected_user['PortType']
    session['hs_code'] = selected_user['HsCode']

    return redirect('/dashboard')


# -------------------- DASHBOARD PAGE --------------------
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session:
        return redirect('/')

    user_hs_code = str(session['hs_code'])
    port_type = session['port_type'].strip().lower().replace(" ", "_")  # normalize

    # -------- STRICT TABLE MAPPING --------
    table_mapping = {
        "import": "Monthly_import_off_1to31th_Jan26",
        "export": "Monthly_Export_Offline_Jan26",
        "sez_import": "SEZ_I_Off_Jan26",
        "sez_export": "Sez_E_Off_jan26"
    }

    if port_type not in table_mapping:
        return f"Access Denied: Invalid PortType ({port_type})"

    table_name = table_mapping[port_type]

    if request.method == 'POST':
        hs_code_input = request.form['hs_code'].strip()

        # -------------------- STRICT HS CODE RLS --------------------
        if hs_code_input:
            if not hs_code_input.startswith(user_hs_code):
                return "Unauthorized HS Code Access"
            hs_filter = f"{hs_code_input}%"
        else:
            hs_filter = f"{user_hs_code}%"
        # ----------------------------------------------------------

        conn = mysql.connector.connect(**db_config)
        query = f"SELECT * FROM `{table_name}` WHERE `HS Code` LIKE %s"
        df = pd.read_sql(query, conn, params=[hs_filter])
        conn.close()

        if df.empty:
            return f"No data found for HS Code: {hs_filter}"

        output = io.BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)

        return send_file(
            output,
            download_name=f"{port_type}_data.xlsx",
            as_attachment=True
        )

    return render_template(
        'dashboard.html',
        user_port_type=port_type,
        user_hs_code=user_hs_code
    )


# -------------------- CHANGE PORT --------------------
@app.route('/change_port')
def change_port():
    if 'users' not in session:
        return redirect('/')

    return render_template('choose_port.html', users=session['users'])


# -------------------- LOGOUT --------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# ==================== RUN APP ====================
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=False)
