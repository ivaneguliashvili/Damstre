git clone https://github.com/YOUR_USERNAME/damstsre.git
cd damstsre
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
