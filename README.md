# NEXOVA POS

NEXOVA POS is a Django restaurant point-of-sale application. Each installation has its own database; do not share the development `db.sqlite3` database between computers.

## Run on a new computer

Requirements: Python 3.10+ and pip.

```bash
git clone <your-repository-url>
cd nexova-pos
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/`, log in with the superuser credentials, then open **Users** in the POS header to create cashier accounts. Create sections, tables, categories, and menu items in **Management** before expecting tables to appear on the POS screen.

## Share on the same Wi-Fi network

On the host computer, allow its LAN address and start Django on all interfaces. Replace `192.168.1.20` with the host computer's actual local IP address:

```bash
export DJANGO_DEBUG=true
export DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.20
python manage.py runserver 0.0.0.0:8000
```

Other devices on that Wi-Fi can then use `http://192.168.1.20:8000/`.

## PWA

The app is installable as a PWA when served from `localhost` or HTTPS. It is not an offline POS: creating orders and bills needs a live Django server and database. For another computer, run its own server or deploy one shared server; copying only frontend files cannot run Django.

For production, set a unique `DJANGO_SECRET_KEY`, set `DJANGO_DEBUG=false`, configure `DJANGO_ALLOWED_HOSTS`, use HTTPS, and move from SQLite to a managed database such as PostgreSQL.
