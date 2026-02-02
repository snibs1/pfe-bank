from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'super_secret_key_pfe'

@app.route('/')
def login_page():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if username == "admin" and password == "1234":
        return redirect(url_for('dashboard'))
    else:
        # تأكد أنك داير flash هنا فقط
        flash("Identifiant ou mot de passe incorrect !", "danger")
        return redirect(url_for('login_page'))

# DASHBOARD 
@app.route('/dashboard')
def dashboard():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)