## 📘 Documentazione Concettuale – Funzione `script.fn_area_di_oggetto()`

> 👀 **Vedi anche**
>
> **Le eccezioni che legge:** [config.area_model_overrides](/dbzero/config/tabelle/area_model_overrides) · [config.aree_funzionali](/dbzero/config/tabelle/aree_funzionali)
>
> **Chi la chiama:** [script.fn_guard_livello](/dbzero/script/funzioni/fn_guard_livello)

---

### 🎯 Scopo Principale
(scritta il 25-09-2026)

Risponde a una domanda: **a quale area funzionale appartiene questo oggetto?**
L'oggetto si nomina con due pezzi, `app_label` e `model_name` (per esempio
`('magazzino', 'causali')`).

La regola:

1. se l'oggetto ha un'eccezione in `area_model_overrides`, l'area è quella;
2. altrimenti l'area è il primo pezzo del nome (area = schema).

Restituisce la chiave dell'area (`schema_db`). Non blocca niente: un'area che
non esiste la restituisce com'è, e chi decide il livello non concede niente su
un'area sconosciuta.

---

### Una sede sola

La stessa regola oggi la scrive anche il backend, in Python
(`PermissionResolver.get_area_schema_db`), con la stessa query. La sede è
questa funzione: il backend è chiamato a usarla invece di rifarla
(brief-db-pannello-config-verbo-generico §6). Finché non lo fa, le copie sono
due, e il brief lo dichiara.

Presidio: `db/pgtap/script/test-fn-guard-livello-v1.sql` (test 1-3 e 11).

{% include-markdown "signature-core.md" %}
