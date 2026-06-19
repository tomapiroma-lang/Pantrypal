import json
import re
import requests
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import UserMixin, login_user, logout_user, current_user, login_required

from forms import LoginForm, RegisterForm

main_bp = Blueprint('main', __name__)


class User(UserMixin):
    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email


def split_into_steps(text):
    """თუ Groq-მა instructions ერთიანი ტექსტის სახით დაგვიბრუნა (და არა მასივად),
    ვცდილობთ მისი ბუნებრივი დაყოფა ცალკეულ ნაბიჯებად, რომ თემპლეითში სწორად
    გამოვა <li>-ების სახით."""
    if not isinstance(text, str):
        return text

    # 1. ჯერ ვცადოთ ახალი ხაზებით დაყოფილი ნაბიჯები
    lines = [line.strip(" -•\t") for line in text.split('\n') if line.strip()]
    if len(lines) > 1:
        return lines

    # 2. ვცადოთ ნუმერირებული ნაბიჯები, მაგ. "1. ...", "2) ..."
    numbered = re.split(r'\d+[\.\)]\s*', text)
    numbered = [s.strip() for s in numbered if s.strip()]
    if len(numbered) > 1:
        return numbered

    # 3. ბოლო ვარიანტი - წინადადებების მიხედვით დაყოფა
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences if sentences else [text]


def get_recipe_image(recipe_name):
    """Unsplash API-დან სურათის მოთხოვნა რეცეპტის სახელით"""
    access_key = current_app.config.get('UNSPLASH_ACCESS_KEY')
    if not access_key:
        # თუ Unsplash-ის გასაღები არ არის კონფიგურირებული, საჯარისოდ ვაბრუნებთ None-ს
        # (requests-ის გაშვება ამის გარეშე ყოველთვის 401-ით ჩავარდება)
        current_app.logger.warning("UNSPLASH_ACCESS_KEY არ არის დაყენებული - ფოტოები არ დაემატება")
        return None

    try:
        url = "https://api.unsplash.com/search/photos"
        params = {
            "query": recipe_name,
            "per_page": 1,
            "orientation": "landscape"
        }
        headers = {
            "Authorization": f"Client-ID {access_key}",
            "Accept-Version": "v1"
        }

        response = requests.get(url, params=params, headers=headers, timeout=5)

        if response.status_code == 200:
            data = response.json()
            if data.get('results'):
                return data['results'][0]['urls']['regular']
        else:
            current_app.logger.warning(
                f"Unsplash API შეცდომა ({response.status_code}) '{recipe_name}'-სთვის: {response.text[:200]}"
            )
    except Exception as e:
        current_app.logger.warning(f"Unsplash მოთხოვნა ჩავარდა '{recipe_name}'-სთვის: {e}")

    return None


# --- ზოგადი მარშრუტები (ROUTES) ---

@main_bp.route('/', endpoint='index')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.ingredients'))
    return redirect(url_for('main.landing'))


@main_bp.route('/landing', endpoint='landing')
def landing():
    return render_template('landing.html')


@main_bp.route('/security', endpoint='security')
def security():
    return render_template('security.html')


# --- ავტორიზაციის მარშრუტები ---

@main_bp.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User(1, "გიორგი", form.email.data)
        login_user(user, remember=form.remember.data)
        flash('წარმატებით შეხვედით სისტემაში!', 'success')
        return redirect(url_for('main.ingredients'))
    return render_template('signin.html', form=form)


@main_bp.route('/register', methods=['GET', 'POST'], endpoint='register')
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        flash('რეგისტრაცია წარმატებით დასრულდა!', 'success')
        return redirect(url_for('main.login'))
    return render_template('signup.html', form=form)


@main_bp.route('/logout', endpoint='logout')
@login_required
def logout():
    session.pop('pantry_list', None)  # სისტემიდან გასვლისას ვშლით დროებით კალათას
    logout_user()
    flash('თქვენ გამოხვედით სისტემიდან.', 'info')
    return redirect(url_for('main.login'))


@main_bp.route('/favorites', endpoint='favorites')
@login_required
def favorites():
    return "<h1>შენი ფავორიტი რეცეპტები (მალე დაემატება)</h1>"


# --- მაღაზიის მარშრუტი (Shop) ---

@main_bp.route('/shop', methods=['GET', 'POST'], endpoint='shop')
@login_required
def shop():
    recipes = None
    search_query = None

    if request.method == 'POST' and 'search_recipes_shop' in request.form:
        search_query = request.form.get('search_query', '').strip()

        if search_query:
            try:
                prompt = f"""
                მომხმარებელი ძებნის: {search_query}

                შესთავაზე 4-5 რეცეპტი, რომელიც შეიძლება გაკეთდეს ამ ინგრედიენტით ან მასთან დაკავშირებული.

                პასუხი დააფორმატე მკაცრად JSON სახით, ყოველგვარი Markdown თეგების (როგორიცაა ```json) და ყოველგვარი შესავალი/დასკვნითი ტექსტის გარეშე. პირდაპირ დაიწყე მასივით [.

                სტრუქტურა:
                [
                  {{
                    "name": "რეცეპტის სახელი",
                    "category": "კატეგორია (მთავარი/გვერდითი/სალათი და ა.შ)",
                    "ingredients": ["ინგრედიენტი 1", "ინგრედიენტი 2"],
                    "instructions": ["ნაბიჯი 1", "ნაბიჯი 2"],
                    "cookTime": "მომზადების დრო (მინ)",
                    "servings": "რამდენი ადამიანისთვის",
                    "difficulty": "სირთულე (მარტივი/საშუალო/რთული)"
                  }}
                ]
                """

                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {current_app.config['GROQ_API_KEY']}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": current_app.config['GROQ_MODEL'],
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2, 
                    "max_tokens": 3000
                }

                response = requests.post(url, headers=headers, json=payload, timeout=15)
                
                if response.status_code == 200:
                    response_data = response.json()
                    response_text = response_data['choices'][0]['message']['content'].strip()

                    cleaned_text = re.sub(r'```json\s*|```', '', response_text).strip()

                    start_idx = cleaned_text.find('[')
                    end_idx = cleaned_text.rfind(']')

                    if start_idx == -1 or end_idx == -1 or end_idx < start_idx:
                        current_app.logger.error(f"ვერ მოიძებნა მასივის საზღვრები. ნედლი პასუხი: {response_text}")
                        raise json.JSONDecodeError(
                            "JSON მასივი ვერ მოიძებნა პასუხში", cleaned_text, 0
                        )

                    json_str = cleaned_text[start_idx:end_idx + 1]

                    try:
                        recipes = json.loads(json_str)
                    except json.JSONDecodeError:
                        cleaned = re.sub(r',\s*([\]}])', r'\1', json_str)
                        recipes = json.loads(cleaned)

                    for recipe in recipes:
                        if 'error' not in recipe:
                            image_url = get_recipe_image(recipe.get('name', ''))
                            recipe['image'] = image_url
                            
                            if isinstance(recipe.get('ingredients'), str):
                                recipe['ingredients'] = [i.strip() for i in recipe['ingredients'].split(',')]

                            if isinstance(recipe.get('instructions'), str):
                                recipe['instructions'] = split_into_steps(recipe['instructions'])
                else:
                    recipes = [{"error": f"Groq API შეცდომა: {response.status_code}"}]

            except json.JSONDecodeError as e:
                current_app.logger.error(f"Groq JSON parse failed: {e}\nRaw response: {response_text!r}")
                recipes = [{"error": "JSON პარსირება ვერ მოხერხდა. სცადეთ ხელახლა."}]
            except Exception as e:
                recipes = [{"error": f"შეცდომა: {str(e)}"}]

    return render_template('shop.html', recipes=recipes, search_query=search_query)


# --- ინგრედიენტების მართვა და GROQ AI მარშრუტები (JINJA2-ზე) ---

@main_bp.route('/ingredients', methods=['GET', 'POST'], endpoint='ingredients')
@login_required
def ingredients():
    ai_response = None

    if request.method == 'POST' and 'search_recipes' in request.form:
        pantry_list = session.get('pantry_list', [])

        if pantry_list:
            ingredients_string = ", ".join(pantry_list)
            try:
                prompt = f"""
                შენ ხარ გამოცდილი ქართველი შეფ-მზარეული და PantryPal აპლიკაციის ასისტენტი.
                მომხმარებელს მაცივარში აქვს მხოლოდ ეს პროდუქტები: {ingredients_string}.

                შესთავაზე 2 ან 3 ნამდვილი, ცნობილი და გემრიელი კერძი (არა გამოგონილი ან ზოგადი
                სახელები), რომელთა მომზადებაც შესაძლებელია ძირითადად ამ ინგრედიენტებით
                (დასაშვებია ჩამატო 1-2 საბაზისო პროდუქტი, მაგალითად მარილი, წიწაკა, ზეთი,
                წყალი, თუ ისინი არ არის ჩამოთვლილში).

                თითო რეცეპტი უნდა იყოს განსხვავებული და კონკრეტული — არ გაიმეორო იგივე
                ნაბიჯები სხვადასხვა რეცეპტში. ინსტრუქცია დაწერე ბუნებრივი, გამართული და
                კარგად ნაცნობი ქართული სამზარეულოს ტერმინოლოგიით, არა სიტყვასიტყვითი
                თარგმანის სტილით.

                პასუხი დააფორმატე სუფთა HTML-ში (გამოიყენე მხოლოდ <h3>, <p>, <ul>, <li>
                თეგები, არ გამოიყენო ```html ბლოკები). თითო რეცეპტს დაუსვი სათაური <h3>-ში
                კერძის ნამდვილი სახელით, შემდეგ ინგრედიენტების სია <ul>-ში და ბოლოს
                მომზადების ინსტრუქცია <p>-ში, მეგობრული და ბუნებრივი ტონით.
                """

                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {current_app.config['GROQ_API_KEY']}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": current_app.config['GROQ_MODEL'],
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.6,
                    "max_tokens": 1500
                }

                response = requests.post(url, headers=headers, json=payload, timeout=10)
                
                if response.status_code == 200:
                    response_data = response.json()
                    ai_response = response_data['choices'][0]['message']['content']
                else:
                    ai_response = f"<p style='color:red;'>Groq API შეცდომა: {response.status_code}</p>"

            except Exception as e:
                ai_response = f"<p style='color:red;'>სამწუხაროდ, Groq AI-სთან დაკავშირება ვერ მოხერხდა. ({str(e)})</p>"

    return render_template('ingredients.html', recipes=ai_response)


@main_bp.route('/ingredients/add', methods=['POST'], endpoint='add_ingredient')
@login_required
def add_ingredient():
    item = request.form.get('ingredient_name', '').strip()
    if item:
        if 'pantry_list' not in session:
            session['pantry_list'] = []

        current_list = session['pantry_list']
        if item not in current_list:
            current_list.append(item)
            session['pantry_list'] = current_list
            session.modified = True

    return redirect(url_for('main.ingredients'))


@main_bp.route('/ingredients/remove', methods=['POST'], endpoint='remove_ingredient')
@login_required
def remove_ingredient():
    item_to_remove = request.form.get('remove_item')
    if 'pantry_list' in session and item_to_remove:
        current_list = session['pantry_list']
        if item_to_remove in current_list:
            current_list.remove(item_to_remove)
            session['pantry_list'] = current_list
            session.modified = True

    return redirect(url_for('main.ingredients'))


@main_bp.route('/ingredients/clear', methods=['POST'], endpoint='clear_ingredients')
@login_required
def clear_ingredients():
    session.pop('pantry_list', None)
    return redirect(url_for('main.ingredients'))