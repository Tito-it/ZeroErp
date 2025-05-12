# Installazione

## Prerequisiti
- Python 3.x  
- **Django (ultima versione stabile,  5.2)**  
- PostgreSQL 17+  
- **Node.js 18.x+** 

## Setup ambiente
```bash
git clone git@github.com:Tito-it/ZeroErp.git
cd ZeroErp


```
## Crea e attiva virtualenv
python -m venv .venv
source .venv/bin/activate

## Installa le dipendenze Python (incluso Django)
pip install -r requirements.txt


##  Vue3 + Vite
cd frontend
npm install
npm run dev


## Avvia la doc locale
cd ..
mkdocs serve