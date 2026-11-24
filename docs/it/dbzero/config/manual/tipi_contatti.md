## 📘 Documentazione Concettuale – Tabella `config.tipi_contatti`

> **Ultimo aggiornamento**: 24 novembre 2026
>
> 👀 **Vedi anche**
>
> * [anagrafiche.contatti](/dbzero/anagrafiche/tabelle/contatti) — i contatti, che portano il tipo
> * [script.fn_tipo_contatto_proposto_id](/dbzero/script/manual/fn_tipo_contatto_proposto_id) — il tipo proposto quando nessuno lo dice
> * [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns)
> * [script.trgfn_audit_data_user_generic](/dbzero/script/funzioni/trgfn_audit_data_user_generic)

---

### 🎯 Scopo Principale

La tabella **`config.tipi_contatti`** definisce le **categorie di contatto** dell'anagrafica dei
soggetti: principale, referente, segreteria, altro. Il reparto o l'ufficio di riferimento non è un
tipo di contatto: lo dice `config.unita_organizzative`.

---

### Colonne e vincoli

* **`codice_interno`** (fino a 10 caratteri): il codice stabile con cui il database e il
  backend riconoscono il tipo. È **unico** (`uq_tipi_contatti_codice_interno`) e **non si
  modifica** dopo la nascita.
* **`codice`** (fino a 15 caratteri): il codice mostrato all'utente.
* **`descrizione`**: obbligatoria.

Il codice si salva in maiuscolo (`trg_tipi_contatti_a15_codice_maiuscolo_ins_upd`).

---

### Il tipo proposto

Quando chi crea un soggetto non dice il tipo del contatto di default, il database scrive il tipo
**proposto**. È il parametro `TIPO_CONTATTO_PROPOSTO`, che contiene un `codice_interno` (in
dotazione `PRINCIPALE`) e ammette gli override per utente, azienda o funzione. Lo legge
[script.fn_tipo_contatto_proposto_id](/dbzero/script/manual/fn_tipo_contatto_proposto_id), che non
ripiega mai sul primo tipo per id. Il registro `config.parameter_fk_surrogate` rifiuta un parametro
che indica un codice assente da questa tabella.

---

### Relazioni

* **FK in ingresso**: `anagrafiche.contatti.tipo_contatto_id` → `config.tipi_contatti(id)`.

---

### Trigger

| Trigger | Quando | Che cosa fa |
| --- | --- | --- |
| `trg_tipi_contatti_a10_lock_columns_upd` | `BEFORE UPDATE OF codice_interno` | rifiuta la modifica del codice interno (`script.trgfn_lock_columns`, `E_CODICE_NON_MODIFICABILE`); la apre solo la porta di manutenzione del migratore |
| `trg_tipi_contatti_a15_codice_maiuscolo_ins_upd` | `BEFORE INSERT OR UPDATE` | il codice in maiuscolo (`script.trgfn_codice_maiuscolo`) |
| `trg_tipi_contatti_audit_data_user_upd` | `BEFORE INSERT OR UPDATE` | i campi di audit `data_*` e `user_*` (`script.trgfn_audit_data_user_generic`) |

---

### Note di migrazione

* In passato la tabella si usava anche come elenco dei reparti; il reparto è passato a
  `config.unita_organizzative`.
* Il codice interno si chiamava `cod_int_tipo_contatto`, e i trigger avevano altri nomi.
* 2026-11-24 — nasce il tipo proposto (decisione D-T5-6 b di Tid): prima le porte prendevano il
  primo tipo per id.
