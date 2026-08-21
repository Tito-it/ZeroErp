## 📘 Documentazione Concettuale – Funzione `anagrafiche.trgfn_soggetti_gen_codice()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
> • [config.sistema_codici](/dbzero/config/tabelle/sistema_codici)
>
Approfondimento funzioni:
> • [script.fn_generate_codice](/dbzero/script/funzioni/fn_generate_codice)
> • [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Assegna il **codice interno** di `anagrafiche.soggetti` quando chi scrive non lo
fornisce. Non calcola niente da sé: delega a `script.fn_generate_codice('soggetto')`,
che legge prefisso, separatore e lunghezza da `config.sistema_codici` e consuma la
sequenza dedicata. È il pattern comune a tutte le anagrafiche con codice generato.

---

### Aggancio

Trigger `trg_soggetti_a10_gen_codice_ins_upd` — fase `_a10_`, `BEFORE INSERT OR UPDATE`
su `anagrafiche.soggetti`.

---

### Regole applicate

1. Se `NEW.codice` è `NULL` **oppure** stringa vuota dopo `btrim`, viene valorizzato
   con `script.fn_generate_codice('soggetto')`.
2. Se `NEW.codice` è già valorizzato, **non viene toccato**: un codice fornito
   dall'applicazione o da un import vince sempre sulla generazione.

La configurazione vive in `config.sistema_codici` alla riga `codice_interno = 'soggetto'`
(prefisso `SGT`, separatore `-`, numero a 7 cifre).

---

### ⚠️ Note e trappole

* **La chiave di configurazione è `'soggetto'`, non il nome della tabella.** Rinominare
  quella riga in `config.sistema_codici` senza toccare la funzione fa fallire ogni
  inserimento con `E_SEQUENZA_NON_CONFIGURATA`: il legame è per stringa, non per FK.
* **`usa_sequenza = false` non è un errore: è un `NULL`.** In quel caso
  `fn_generate_codice` **restituisce `NULL`** senza sollevare niente, e la riga prosegue
  senza codice. ⚠️ E qui è più insidioso che altrove: su `anagrafiche.soggetti` la colonna `codice` è **nullable**, quindi non c'è nessun vincolo a fermare la riga. Il soggetto viene creato **senza codice, in silenzio**, e il difetto si scopre a valle.
* **In `UPDATE` la generazione è di fatto inerte, ma solo grazie al lock.** Sulla stessa
  tabella agisce `trg_soggetti_a10_lock_columns_upd`
  (`script.trgfn_lock_columns('codice', 'CODICE_NON_MODIFICABILE')`), e i trigger `BEFORE ROW`
  scattano in **ordine alfabetico**: `gen_codice` gira *prima* di `lock_columns`. Chi svuota
  `codice` in un `UPDATE` ottiene quindi un codice nuovo, che il lock intercetta subito dopo
  come modifica e rifiuta.
  ⚠️ Con `SET LOCAL zeroerp.allow_lock_columns_override = 'on'` il lock si spegne e questa
  rete sparisce: in manutenzione, svuotare `codice` **cambia davvero l'identità della riga**
  e consuma un valore di sequenza.

---

### Codici errore

| Codice | Sollevato da | Quando |
|--------|--------------|--------|
| `E_SEQUENZA_NON_CONFIGURATA` | `script.fn_generate_codice` | Nessuna riga `codice_interno = 'soggetto'` in `config.sistema_codici` |
| `CODICE_NON_MODIFICABILE` | `script.trgfn_lock_columns` | Tentativo di cambiare `codice` in `UPDATE` |

La funzione **non solleva errori propri**: ogni errore viene dalle funzioni che invoca.

---

{% include-markdown "signature-core.md" %}
