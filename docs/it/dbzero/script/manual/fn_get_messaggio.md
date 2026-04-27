## 📘 Documentazione Concettuale – Funzione `script.fn_get_messaggio`

> 👀 **Vedi anche**

> Approfondimenti tabelle:   
>
[config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)  


La funzione **`script.fn_get_messaggio(p_codice text, p_valore text DEFAULT NULL, p_lingua text DEFAULT NULL) RETURNS text`** recupera e formatta un messaggio dall’archivio centralizzato, con supporto per placeholder e internazionalizzazione.

---
### 🎯 Scopo Principale
* **Centralizzare i testi**
  Conservare tutti i messaggi (errori, avvisi, info) in tabella, evitando hard‑coding in trigger, procedure o sorgenti SQL.
* **Internazionalizzazione avanzata con fallback**
  Selezionare dinamicamente la lingua di output in base a:

  1. parametro `p_lingua`
  2. GUC `myapp.user_language` (impostata dal middleware BE per-request)
  3. default `'it'`

  Post **23-04-2026** (migration `20260423-02-01`) e' attivo il
  **fallback lingua IT**: se la lingua risolta `lingua_eff` non ha
  riga per il codice richiesto, la funzione ricade su `lingua='it'`
  invece di ritornare il placeholder. Solo se nemmeno `'it'` ha
  riga viene restituito il placeholder legacy
  `[MESSAGGIO NON DEFINITO: <codice>]`. Questo permette il rollout
  incrementale delle traduzioni EN senza dover tradurre tutti i
  codici in un solo colpo.
* **Placeholder dinamici**
  Utilizzare `format()` per sostituire i placeholder `%s` nel template con i valori runtime, abilitando messaggi parametrizzati.

---

### Parametri di Input

| Nome       | Tipo   | Default |Descrizione                                           |
| ---------- | ------ | ------- |----------------------------------------------------- |
| `p_codice` | `text` | —       | Codice del messaggio (`codice` in `config.messaggi_errore`). |
| `p_valore` | `text` | `NULL`  | Valore da sostituire al placeholder `%s`; se `NULL`, nessuna         sostituzione viene applicata.|
| `p_lingua` | `text` | `NULL`  | Lingua desiderata (es. `it`, `en`); se `NULL`, usa `myapp.user_language` o fallback a `it`. |

---

### Comportamento Interno

1. **Determinazione lingua effettiva**

   ```plpgsql
   lingua_eff := coalesce(
     p_lingua,
     current_setting('myapp.user_language', true),
     'it'
   );
   ```
2. **Recupero del template con fallback lingua** (post 23-04-2026)

   Single-query che preferisce la lingua richiesta ma ricade su `'it'`
   se manca: ordering booleano + LIMIT 1 garantisce che la riga con
   `lingua = lingua_eff` vinca, altrimenti passa quella `'it'`.

   ```plpgsql
   SELECT messaggio
     INTO tmpl
     FROM config.messaggi_errore
    WHERE codice = p_codice
      AND lingua IN (lingua_eff, 'it')
    ORDER BY (lingua = lingua_eff) DESC
    LIMIT 1;
   ```

   Quando `lingua_eff = 'it'` la IN degenera a singolo valore, la
   ORDER BY e' idempotente e il LIMIT 1 restituisce il match esatto
   (comportamento legacy).

3. **Messaggio non definito** (nessuna lingua disponibile, nemmeno `'it'`)

   * Se `tmpl IS NULL`, restituisce:

     ```text
     [MESSAGGIO NON DEFINITO: <p_codice>]
     ```
4. **Sostituzione placeholder**

   * Se `p_valore IS NOT NULL`, restituisce:

     ```plpgsql
     format(tmpl, p_valore)
     ```
   * Altrimenti restituisce `tmpl` originale.

---

### Valore di Ritorno

* **`text`**
  Messaggio finale, con eventuale sostituzione di `%s` applicata.

---

### Volatilita'

**`STABLE`** (post 23-04-2026). La fn legge da `config.messaggi_errore`
quindi il risultato cambia tra query diverse se la tabella viene
modificata, ma resta costante all'interno di una singola query. La
versione pre-23-04-2026 era marcata `IMMUTABLE` per errore — bug
latente: il planner poteva cachare risultati stantii dopo UPDATE dei
seed. Corretto nella stessa migration che ha introdotto il fallback
lingua.

---

### Vantaggi Operativi

* **Manutenzione semplificata**
  Modifiche ai messaggi avvengono unicamente in tabella, senza interventi su sorgenti PL/pgSQL.
* **Coerenza e uniformità**
  Un solo punto di definizione e recupero per tutti i testi applicativi.
* **Internazionalizzazione flessibile**
  Supporto per lingua utente tramite GUC e fallback gerarchico.
* **Messaggi parametrizzati**
  Placeholder `%s` sostituiti dinamicamente, per contesti runtime variabili.
* **Best practice**
  Separazione tra codici di business e contenuti testuali, migliorando qualità e riusabilità.

---

> **“Centralizzare e parametrizzare i messaggi in tabella con supporto multilingua e placeholder `%s` è una best practice per mantenere il codice pulito, manutenibile e traducibile.”**