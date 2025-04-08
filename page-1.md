# Definizione codice interni non modificabili 

### 🗂️ **Analisi della richiesta:**

* Avere un **codice interno fisso e immutabile** per identificare certe entità (es: servizi) nel database e nel codice sorgente.
* Evitare che tale codice fisso venga modificato dall’utente attraverso il software.
* Avere anche un **codice utente personalizzabile**, per uso del gestore del sistema (anche multilingua).

***

### ✅ **Soluzione consigliata con Django:**

Il modo migliore e più pulito per farlo è avere nel tuo modello Django due campi separati:

1. **`internal_code`** (Codice Interno, non modificabile, usato solo nel codice e mai esposto agli utenti finali).
2. **`user_code`** (Codice personalizzabile dall’utente o gestore del sistema).

L'`internal_code` diventa un identificatore univoco fisso nel codice, il `user_code` invece può cambiare nel tempo.

***

### 🔧 **Esempio pratico modello Django:**

```python
pythonCopiaModificafrom django.db import models

class Servizio(models.Model):
    internal_code = models.CharField(
        max_length=10, 
        unique=True, 
        editable=False  # Non modificabile nell'interfaccia Django Admin e form
    )
    user_code = models.CharField(max_length=10, unique=True)
    descrizione = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.user_code} - {self.descrizione}"
```

**Nota Importante:**

* `editable=False` garantisce che non venga modificato dall'interfaccia Django (né Admin, né Form).
* Può comunque essere assegnato o modificato solo dal codice stesso (ad esempio tramite migrazioni Django o tramite script di inizializzazione dati).

***

### 🚩 **Come assegnare e gestire il codice interno:**

Il codice interno fisso deve essere gestito da:

* **Migrazioni Django:**\
  Generi migrazioni specifiche per popolare i dati iniziali del database.

```python
pythonCopiaModifica# migration Django esempio:
from django.db import migrations

def crea_servizi(apps, schema_editor):
    Servizio = apps.get_model('tua_app', 'Servizio')
    servizi = [
        {'internal_code': 'ENE', 'user_code': 'Energia', 'descrizione': 'Fornitura Energia'},
        {'internal_code': 'ACQ', 'user_code': 'Acqua', 'descrizione': 'Fornitura Idrica'},
        {'internal_code': 'GAS', 'user_code': 'Gas', 'descrizione': 'Fornitura Gas'},
    ]
    for servizio in servizi:
        Servizio.objects.update_or_create(
            internal_code=servizio['internal_code'],
            defaults={'user_code': servizio['user_code'], 'descrizione': servizio['descrizione']}
        )

class Migration(migrations.Migration):
    dependencies = [
        ('tua_app', '0001_initial'),
    ]
    operations = [
        migrations.RunPython(crea_servizi),
    ]
```

* **Fixtures Django:**\
  Puoi popolare i dati iniziali con un fixture JSON o YAML.

***

### 📌 **Esempio d’uso nel codice:**

```python
pythonCopiaModifica# recupera servizio con internal_code fisso 'ENE'
energia_servizio = Servizio.objects.get(internal_code='ENE')

# Uso nelle query e nelle logiche interne, indipendente dal user_code
fatture_energia = Fattura.objects.filter(servizio=energia_servizio)
```
