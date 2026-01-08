## 📘 Documentazione Concettuale – Tabella `config.unita_organizzative`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.contatti](/dbzero/anagrafiche/tabelle/contatti)
> * [config.tipi_contatti](/dbzero/config/tabelle/tipi_contatti)
>
> Approfondimenti funzioni:
>
> * [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns)
> * [script.trgfn_audit_data_user_generic](/dbzero/script/funzioni/trgfn_audit_data_user_generic)

---

### 🎯 Scopo Principale

(latest review 07-01-26)
La tabella **`config.unita_organizzative`** definisce il catalogo dei reparti/uffici
utilizzabili nell'anagrafica (es. Amministrazione, Tecnico, Commerciale).
Nasce per separare in modo netto il concetto di **unita organizzativa** dai
**tipi di contatto**, riducendo ambiguita semantiche.

---

### 🔍 Campi principali

* `codice` e `codice_interno`: identificativi stabili e univoci.
* `descrizione`: etichetta leggibile del reparto/ufficio.
* `parent_id`: riferimento gerarchico ad altra unita (opzionale).
* `attivo`: dismissione logica senza cancellazione.
* audit standard: `data_insert`, `user_insert`, `data_update`, `user_update`.

---

### ✅ Regole

* `codice_interno` e' immutabile (trigger di lock).
* `parent_id` non puo puntare a se stesso.
* `attivo` permette di disabilitare un reparto senza rimuovere le associazioni.

---

### 🧭 Nota di refactor

In molte installazioni, **`config.tipi_contatti`** e' stato usato di fatto
come elenco dei reparti. Il refactor introduce `config.unita_organizzative`
come fonte corretta e separata; l'adeguamento delle tabelle applicative
avverra in step successivi.

---

{% include-markdown "signature-core.md" %}
