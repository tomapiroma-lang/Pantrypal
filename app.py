import os
import requests
import json
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from groq import Groq

# ფორმების შემოტანა გამოყოფილი forms.py ფაილიდან
from forms import LoginForm, RegisterForm

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = 'your-very-secret-key-12345'

# Flask-Login კონფიგურაცია
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# დროებითი მომხმარებლის კლასი სესიების სამართავად (ტესტირებისთვის)
class User(UserMixin):
    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    # აბრუნებს იმიტირებულ მომხმარებელს, რათა ავტორიზაციამ იმუშაოს ბაზის გარეშეც
    return User(user_id, "გიორგი", "user@pantrypal.ge")


# --- სამხმელი ფუნქციები ---

def get_recipe_image(recipe_name):
    """Unsplash API-დან სურათის მოთხოვნა რეცეპტის სახელით"""
    try:
        # Unsplash API (ბიუჯეტი: 50 requests per hour without API key, 5000 with key)
        url = "https://api.unsplash.com/search/photos"
        params = {
            "query": recipe_name,
            "per_page": 1,
            "orientation": "landscape"
        }
        headers = {
            "Accept-Version": "v1"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('results'):
                return data['results'][0]['urls']['regular']
    except:
        pass
    
    # თუ ვერ მოიძებნა, დაბრუნებ placeholder
    return None


# --- ზოგადი მარშრუტები (ROUTES) ---

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('ingredients'))
    return redirect(url_for('login'))


@app.route('/security')
def security():
    return render_template('security.html')


# --- ავტორიზაციის მარშრუტები ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User(1, "გიორგი", form.email.data)
        login_user(user, remember=form.remember.data)
        flash('წარმატებით შეხვედით სისტემაში!', 'success')
        return redirect(url_for('ingredients'))
    return render_template('signin.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        flash('რეგისტრაცია წარმატებით დასრულდა!', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html', form=form)

@app.route('/logout')
@login_required
def logout():
    session.pop('pantry_list', None)  # სისტემიდან გასვლისას ვშლით დროებით კალათას
    logout_user()
    flash('თქვენ გამოხვედით სისტემიდან.', 'info')
    return redirect(url_for('login'))

@app.route('/favorites')
@login_required
def favorites():
    return "<h1>შენი ფავორიტი რეცეპტები (მალე დაემატება)</h1>"


# --- მაღაზიის მარშრუტი (Shop) ---

@app.route('/shop', methods=['GET', 'POST'])
@login_required
def shop():
    recipes = None
    search_query = None
    
    # თუ მომხმარებელმა დააწკაპუნა ძებნა
    if request.method == 'POST' and 'search_recipes_shop' in request.form:
        search_query = request.form.get('search_query', '').strip()
        
        if search_query:
            try:
                client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
                
                prompt = f"""
                მომხმარებელი ძებნის: {search_query}
                
                შესთავაზე 4-5 რეცეპტი, რომელიც შეიძლება გაკეთდეს ამ ინგრედიენტით ან მასთან დაკავშირებული.
                
                პასუხი დააფორმატე ზუსტად JSON ფორმატში (არა ```json ბლოკი, პირდაპირ JSON):
                [
                  {{
                    "name": "რეცეპტის სახელი",
                    "category": "კატეგორია (მეტი/გვერდი/სალადი და ა.შ)",
                    "ingredients": "ინგრედიენტები (ფრჩხელი სიის სახით)",
                    "instructions": "დეტალური მოამზადების ინსტრუქციები",
                    "cookTime": "მოამზადების დრო (მინ)",
                    "servings": "რამდენი ადამიანისთვის",
                    "difficulty": "სირთულე (მარტივი/საშუალო/ჩალი)"
                  }}
                ]
                
                მხოლოდ JSON, არა სხვა ტექსტი.
                """
                
                completion = client.chat.completions.create(
                    model="llama3-8b-8192",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=2000
                )
                
                response_text = completion.choices[0].message.content.strip()
                # ცადეთ JSON პარსირება
                import json
                recipes = json.loads(response_text)
                
                # თითოეული რეცეპტისთვის სურათის ძებნა
                for recipe in recipes:
                    if 'error' not in recipe:
                        image_url = get_recipe_image(recipe.get('name', ''))
                        recipe['image'] = image_url
                
            except json.JSONDecodeError:
                recipes = [{"error": "JSON პარსირება ვერ მოხერხდა"}]
            except Exception as e:
                recipes = [{"error": f"შეცდომა: {str(e)}"}]
    
    return render_template('shop.html', recipes=recipes, search_query=search_query)


# --- ინგრედიენტების მართვა და GROQ AI მარშრუტები (JINJA2-ზე) ---

@app.route('/ingredients', methods=['GET', 'POST'])
@login_required
def ingredients():
    ai_response = None
    
    # თუ მომხმარებელმა დააჭირა "მოძებნე რეცეპტები" ღილაკს
    if request.method == 'POST' and 'search_recipes' in request.form:
        pantry_list = session.get('pantry_list', [])
        
        if pantry_list:
            ingredients_string = ", ".join(pantry_list)
            try:
                # Groq კლიენტის ინიციალიზაცია (აუცილებელია GROQ_API_KEY გარემოს ცვლადში)
                client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
                
                prompt = f"""
                შენ ხარ პროფესიონალი შეფ-მზარეული და PantryPal აპლიკაციის ასისტენტი. 
                მომხმარებელს აქვს მხოლოდ ეს ინგრედიენტები: {ingredients_string}.
                შესთავაზე 2 ან 3 მარტივი და გემრიელი რეცეპტი, რომლის მომზადებაც შეიძლება ძირითადად ამ პროდუქტებით.
                
                პასუხი დააფორმატე სუფთა HTML-ში (გამოიყენე მხოლოდ <h3>, <p>, <ul>, <li> თეგები, არ გამოიყენო ```html ბლოკები).
                მოამზადე პასუხი ქართულ ენაზე, მეგობრული ტონით.
                """
                
                completion = client.chat.completions.create(
                    model="llama3-8b-8192",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=1000
                )
                ai_response = completion.choices[0].message.content
            except Exception as e:
                ai_response = f"<p style='color:red;'>სამწუხაროდ, Groq AI-სთან დაკავშირება ვერ მოხერხდა. ({str(e)})</p>"

    return render_template('ingredients.html', recipes=ai_response)


@app.route('/ingredients/add', methods=['POST'])
@login_required
def add_ingredient():
    item = request.form.get('ingredient_name', '').strip()
    if item:
        if 'pantry_list' not in session:
            session['pantry_list'] = []
        
        current_list = session['pantry_list']
        # დუბლიკატების შემოწმება
        if item not in current_list:
            current_list.append(item)
            session['pantry_list'] = current_list
            session.modified = True
            
    return redirect(url_for('ingredients'))


@app.route('/ingredients/remove', methods=['POST'])
@login_required
def remove_ingredient():
    item_to_remove = request.form.get('remove_item')
    if 'pantry_list' in session and item_to_remove:
        current_list = session['pantry_list']
        if item_to_remove in current_list:
            current_list.remove(item_to_remove)
            session['pantry_list'] = current_list
            session.modified = True
            
    return redirect(url_for('ingredients'))


@app.route('/ingredients/clear', methods=['POST'])
@login_required
def clear_ingredients():
    session.pop('pantry_list', None)
    return redirect(url_for('ingredients'))


if __name__ == '__main__':
    app.run(debug=True)