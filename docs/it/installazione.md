# Installazione

## Prerequisiti
- Python   
- Django   
- PostgreSQL
- Liquibase
- Vue3  
- Node.js  

→ Per le versioni consigliate, vedi [Versioni supportate](versioni-supportate.md).


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
---


---
{% include-markdown "signature-core.md" %}
