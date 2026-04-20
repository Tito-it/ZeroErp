## 📘 Documentazione Concettuale – Trigger Function `script.trgfn_canale_origine_immutable()`

> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
>
> Guide:
>
> [Architettura Multi-Face Auth](/guide/architettura-multi-face-auth) §6.4 — Tracciabilita' canale
> [Linee Guida Trigger](/linee-guida-trigger) — convenzioni naming e fasi

La trigger function **`script.trgfn_canale_origine_immutable()`** garantisce
che la colonna `canale_origine` di una tabella transazionale non possa essere
modificata dopo l'INSERT. E' una funzione generica (non hardcoded su una
tabella specifica): viene riusata da piu' tabelle (`anagrafiche.billing_account`,
`vendite.ordini`, `vendite.fatture`) tramite `CREATE TRIGGER ... UPDATE OF
canale_origine ... EXECUTE FUNCTION script.trgfn_canale_origine_immutable()`.

---

### 🎯 Scopo Principale

(latest review 20-04-2026)

* **Immutabilita' semantica del canale** — il `canale_origine` traccia l'origine
  del record (ADMIN / PORTALE / SHOP). Una modifica retroattiva sarebbe una
  riscrittura della storia del dato e invaliderebbe decisioni RLS gia' prese
  sul record (es. shop customer che "all'improvviso" vede un ordine
  originariamente portale).
* **Difesa al livello giusto** — applicare la regola nel DB (trigger) garantisce
  che sia rispettata anche da script di manutenzione, migrazioni ad-hoc,
  accessi diretti via psql. Il service layer non e' unica linea di difesa.
* **Genericita'** — unica funzione riusata su N tabelle, invece di N funzioni
  duplicate. Il trigger viene applicato con `UPDATE OF canale_origine`:
  scatta **solo se** la colonna e' esplicitamente nel SET dell'UPDATE,
  evitando overhead su UPDATE che toccano altre colonne.

---

### Logica

1. Confronta `NEW.canale_origine` con `OLD.canale_origine` usando
   `IS DISTINCT FROM` (gestione NULL-safe).
2. Se uguali (no-op o UPDATE con stesso valore): `RETURN NEW`, operazione
   accettata senza errore.
3. Se diversi: chiama `script.fn_log_and_raise_error` con codice
   `E_CANALE_ORIGINE_IMMUTABILE` (id 385). Il raise interrompe la transazione.

Context di errore riportato nel payload JSONB:

* `op` — operazione (`TG_OP`, normalmente `UPDATE`)
* `schema` — `TG_TABLE_SCHEMA` (es. `anagrafiche`, `vendite`)
* `tabella` — `TG_TABLE_NAME` (es. `billing_account`, `ordini`, `fatture`)
* `old_canale` — valore precedente
* `new_canale` — valore tentato

Il messaggio descrittivo include schema/tabella/old/new per debug.

---

### Applicazione

Trigger creati dalla migration `20260420-04`:

* `trg_billing_account_a10_canale_origine_immutable_upd` su
  `anagrafiche.billing_account`
* `trg_vendite_ordini_a10_canale_origine_immutable_upd` su
  `vendite.ordini` (schema prefisso per evitare collisione con
  `acquisti.ordini`)
* `trg_vendite_fatture_a10_canale_origine_immutable_upd` su
  `vendite.fatture`

Tutti:

* Timing: **BEFORE UPDATE OF canale_origine**
* Fase: **_a10_** (guard/block)
* Scope: **FOR EACH ROW**

---

### Codice errore sollevato

**`E_CANALE_ORIGINE_IMMUTABILE`** (id 385) — `config.messaggi_errore` CSV.

Messaggio: "Canale origine su `<schema>.<tabella>`: la colonna
canale_origine e' immutabile post-INSERT."

Causa: un UPDATE ha cercato di modificare `canale_origine` su un record
esistente. Soluzione documentata: non modificare la colonna; se serve
cambiare canale, annullare il record e crearne uno nuovo.

---

### Quando NON si applica

* INSERT: il trigger non scatta (solo UPDATE). Il valore di
  `canale_origine` viene settato all'INSERT e resta valido.
* UPDATE che non tocca `canale_origine`: `UPDATE OF canale_origine` non
  scatena il trigger. Performance OK per UPDATE frequenti su altre
  colonne.
* UPDATE con stesso valore (`canale_origine = canale_origine`): il trigger
  scatta ma `IS DISTINCT FROM` ritorna false → `RETURN NEW` senza errore.
  Idempotenza.
* DELETE: non scatta.

---

### Note implementative

* `LANGUAGE plpgsql` — necessario per il RAISE tramite
  `fn_log_and_raise_error`.
* Non `STABLE` / `IMMUTABLE` — non ha senso etichettare una trigger function.
* Riutilizzata via `EXECUTE FUNCTION`: non e' una "trigger-generator", e'
  la stessa fn su N tabelle. Il context (schema/tabella) e' sempre
  disponibile via `TG_TABLE_*`.
