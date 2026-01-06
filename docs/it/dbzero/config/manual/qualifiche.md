## 📘 Documentazione Concettuale – Tabella `config.qualifiche`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane)
> * [config.unita_organizzative](/dbzero/config/tabelle/unita_organizzative)
>
> Approfondimenti funzioni:
>
> * [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns)
> * [script.trgfn_audit_data_user_generic](/dbzero/script/funzioni/trgfn_audit_data_user_generic)

---

### 🎯 Scopo Principale

La tabella **`config.qualifiche`** definisce il catalogo delle mansioni/posizioni
assegnabili alle risorse (es. Amministratore, Dipendente, Consulente).
Serve per distinguere la funzione operativa della persona all'interno
dell'organizzazione.

---

### 🔍 Campi principali

* `codice` e `codice_interno`: identificativi stabili e univoci.
* `descrizione`: etichetta leggibile della qualifica.
* `attivo`: dismissione logica senza cancellazione.
* `meta`: JSONB per estensioni future.
* audit standard: `data_insert`, `user_insert`, `data_update`, `user_update`.

---

### ✅ Regole

* `codice_interno` e' immutabile (trigger di lock).
* `attivo` permette di disabilitare una qualifica senza rimuovere le associazioni.

---

{% include-markdown "signature-core.md" %}
