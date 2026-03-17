## 📘 Documentazione Concettuale – Tabella `config.area_model_overrides`

> 👀 **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni)
>
Tabelle correlate:
>
[config.aree_funzionali](/dbzero/config/tabelle/aree_funzionali)

---

La tabella **`config.area_model_overrides`** è una **tabella tecnica di mapping** che consente di riassegnare un model Django a un'area funzionale diversa dal suo schema DB.

---

### 🎯 Scopo Principale

* Gestire le **eccezioni** al mapping automatico area = schema.
* Consentire che un model appartenga a un'area diversa senza spostarlo fisicamente di schema.

---

### Colonne chiave

| Colonna | Scopo |
|---------|-------|
| `app_label` | Label app Django (es. `anagrafiche`) |
| `model_name` | Nome model Django (es. `clienti`) |
| `area_id` | Area a cui riassegnare il model |

Il vincolo UNIQUE su `(app_label, model_name)` garantisce un solo override per model.

---

### Quando usarla

Questa tabella è pensata per **eccezioni rare**. Il caso standard è area = schema (risoluzione automatica). Esempio d'uso: un model in schema `config` che per logica di business appartiene all'area `vendite`.

---

> **"Tabella di eccezione: il 99% dei model non ne ha bisogno. Usare solo quando il mapping automatico schema→area non è sufficiente."**
