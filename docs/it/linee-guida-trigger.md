# 🔧 Linee guida Trigger (PostgreSQL + Liquibase)

## 🎯 Scopo

Definire **convenzioni univoche** per:

* naming dei trigger e delle funzioni trigger,
* quando usare `UPDATE OF ...`,
* ordine di esecuzione (priorità),
* pattern degli eventi (`_ins/_upd/_dlt`).

---

## 🏷️ Convenzioni di naming

### Prefisso

* Tutti i trigger iniziano con **`trg_`**.

### Fasi / priorità

Usiamo suffissi alfabetici per imporre l’**ordine di esecuzione** (i trigger sono eseguiti in ordine lessicografico):

* **`_a10_`** → **trigger di verifica/blocco** (validazioni, guard-rails). Se falliscono, chiamano la nostra funzione di errore/log e **impediscono** l’operazione.
* **`_z90_`** → **trigger finali** (effetti collaterali “terminali”), es. duplicazione su schema storico, audit finali.

Se servono step intermedi (facoltativo in futuro): riserviamo `_mXX_` (es. `_m50_`).

### Eventi (segmento finale)

* `_ins` = `INSERT`
* `_upd` = `UPDATE` (vedi sotto quando usare `OF colonna`)
* `_dlt` = `DELETE`
* Combinali se serve: `_ins_upd`, `_upd_dlt`, `_ins_upd_dlt`.

### Pattern completo consigliato

```
trg_<fase>_<schema_opzionale>_<tabella>_<descrizione_breve>_<eventi>
```

* **fase**: `a10` o `z90`
* **descrizione_breve**: snake_case, verbo + oggetto, es. `only_allowed_tipi`
* **eventi**: `_ins`, `_upd`, `_dlt`, o combinati

---

## ⚙️ Scelta tra `UPDATE` vs `UPDATE OF colonna`

* Se la logica riguarda **solo una o poche colonne specifiche**, usa **`UPDATE OF colonna1[, colonna2]`** → **più efficiente** (il trigger non scatta se non cambiano quelle colonne).
* Se la logica dipende dal **record intero** o da **più colonne** in combinazione, usa `UPDATE` **senza `OF`**.

**Standard Zero ERP**

* Validazioni su singola colonna → `UPDATE OF colonna`.
* Trigger di storico/audit che reagiscono a qualsiasi modifica → `UPDATE` senza `OF`.

---

## ✅ Best practice riassunte

* **`_a10`**: prima linea di difesa (check & block).
* **`_z90`**: azioni finali “a valle” (es. storico).
* **`OF colonna`** quando possibile per performance.
* Nomi **brevi e descrittivi**.
* Usare la funzione progetto per errori: `script.fn_log_and_raise_error(...)`.

---

## 📋 Checklist rapida (da usare nei PR)

* [ ] Nome con prefisso `trg_` e fase corretta (`_a10_` / `_z90_`).
* [ ] Eventi coerenti (`_ins/_upd/_dlt`); usare `UPDATE OF colonna` quando possibile.
* [ ] In `_a10_` usata `script.fn_log_and_raise_error(...)`.
* [ ] Ordine lessicografico rispettato (niente prefissi “casuali”).
* [ ] Commenti/descrizioni chiari in SQL o Liquibase.
