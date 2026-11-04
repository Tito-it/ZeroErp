## 📘 Documentazione Concettuale – Funzione `dbops.fn_seed_automazione_overlap`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automazione_overlap](/dbzero/dbops/tabelle/automazione_overlap) — il registro che la funzione riscrive
>
> Approfondimento funzioni:
>
> * [dbops.fn_apply_automazione_overlap](/dbzero/dbops/funzioni/fn_apply_automazione_overlap) — chi legge il registro e crea i vincoli
> * [dbops.fn_resolve_scope](/dbzero/dbops/funzioni/fn_resolve_scope) — l'ambito degli schemi da guardare
> * [dbops.fn_table_in_scope](/dbzero/dbops/funzioni/fn_table_in_scope) — le esclusioni per tabella dell'ambito
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — l'automazione OVERLAP fra le altre

---

### 🎯 Scopo Principale

Rileva dallo schema le tabelle con un periodo di validità e scrive per ognuna una riga in
`dbops.automazione_overlap`, attiva se gli indizi strutturali dicono che la tabella è versionata.
⚠️ Oggi non la chiama nessuno: il registro si scrive a mano, con changeSet di `80_data`, e
questa funzione, lanciata, lo riscriverebbe.

---

### Quali tabelle guarda

Le tabelle ordinarie degli schemi dell'ambito (`p_schemas`, o l'ambito risolto se è vuoto), lo
schema `storico` escluso, che hanno la coppia `valido_dal` / `valido_al` oppure
`valid_from` / `valid_to`. Una tabella con **solo** una colonna range nativa, senza la coppia di
date, non viene vista. Se la tabella ha anche una colonna range `validita`, la riga la porta in
`range_col`.

---

### Come decide che una tabella è versionata

Cerca gli indizi in quest'ordine, e si ferma al primo:

1. **un vincolo `EXCLUDE`** già presente: la chiave si legge dalle colonne messe in uguaglianza,
   e il nome del vincolo finisce nella riga;
2. **un indice GiST** sull'intervallo delle date: la chiave si dovrebbe leggere dalle colonne
   dell'indice. ⚠️ Oggi questo ramo non estrae mai la chiave (le espressioni regolari che lo
   leggono non riconoscono la definizione dell'indice), e la riga resta spenta con la nota
   `gist_index_keys_not_parsed`;
3. **un vincolo `UNIQUE` o una chiave primaria** che contiene la data d'inizio: la chiave sono le
   altre colonne del vincolo.

Se nessun indizio dà una chiave, per tre tabelle note (`vendite.contratti`,
`catalogo.articoli_componenti`, `catalogo.unita_misura_conversioni`) la funzione assegna una
chiave scritta nel suo corpo e accende la riga. Le altre restano spente, con la nota del motivo.

---

### ⛔ Riscrive le righe che esistono

La scrittura è un upsert sulla tabella: se la riga c'è già, la funzione ne **sovrascrive** chiave,
date, estremi, nome del vincolo, `active`, `exec_mode`, `note` e `range_col` con quello che ha
rilevato. Restano solo `key_expressions` e `where_predicate`, che la funzione non conosce.

Sul registro di oggi, curato a mano, vuol dire spegnere o allargare righe scritte apposta: una riga
con chiavi su espressione, o con un vincolo parziale, perde il suo `constraint_name` e la sua
chiave curata. Per questo la funzione non è fra i passi di nessun giro.

---

### Codici errore

La funzione non solleva codici suoi.

---

### Note di migrazione

* 2026-01-19 — nasce con il registro, come passo di popolamento.
* 2026-04-12 — rileva la colonna range nativa `validita`.
* 2026-06-02 — il registro passa a righe scritte da changeSet, con vincoli parziali ed espressioni
  di chiave che la funzione non sa rilevare. Nessun changeSet, job o test la chiama.

---

{% include-markdown "signature-core.md" %}
