## 📘 Documentazione Concettuale – Trigger Function `script.trgfn_righe_guard_pending()`

> 👀 **Vedi anche**
>
> `stato_approvazione_prezzo` (colonna, non tabella) — enum PENDING/APPROVED/REJECTED
> [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe) — tabella utente
> [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe) — tabella utente
> [vendite.offerte_commerciali_eccezioni](/dbzero/vendite/tabelle/offerte_commerciali_eccezioni) — tabella utente
> [script.trgfn_componenti_guard_pending](/dbzero/script/funzioni/trgfn_componenti_guard_pending) — guard gemello per le tabelle `*_componenti`
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

Trigger function **BEFORE UPDATE** generica per le tabelle **RIGA-LEVEL** del
sotto-sistema approvazione prezzo (`preventivi_righe`, `contratti_righe`,
`offerte_commerciali_eccezioni`). Blocca le modifiche ai **campi struttura** di una
riga quando la sua richiesta di approvazione prezzo è in stato `PENDING`.

---

### 🎯 Scopo Principale

(rev 2026-06-01 — estrazione)

Quando una riga ha `stato_approvazione_prezzo = 'PENDING'` (richiesta L3 in attesa
di esito), l'approvatore deve decidere sulla **riga esatta** proposta: cambi di
prezzo/quantità/articolo tra richiesta ed esito romperebbero la catena decisionale.

Questa funzione è la **generalizzazione** delle due guard domain-specific
`vendite.trgfn_preventivi_righe_guard_pending` (20260422-07) e
`vendite.trgfn_contratti_righe_guard_pending` (20260518-02), che contenevano
logica equivalente, ed estende lo stesso comportamento al nuovo consumer
`offerte_commerciali_eccezioni`. È il gemello riga-level di
[`script.trgfn_componenti_guard_pending`](/dbzero/script/funzioni/trgfn_componenti_guard_pending).

---

### Strategia ALLOWLIST (non denylist)

A differenza del guard componenti — dove i campi struttura sono **identici** tra
tutte le tabelle `*_componenti` e quindi enumerabili staticamente — le tabelle
riga-level hanno strutture **diverse** (es. `contratti_righe` ha
`tipo_erogazione`/`periodicita`/…; `preventivi_righe` ha
`descrizione`/`sconto_percentuale`/`iva_id`). Un'enumerazione statica non
generalizza.

La funzione adotta quindi un confronto ad **allowlist via `to_jsonb`**: rimuove dai
record `OLD` e `NEW` i soli campi ammessi in PENDING e confronta il resto.
Qualsiasi residuo diverso → raise. Vantaggio: **robusto all'aggiunta di nuove
colonne** (nessuna denylist da manutenere).

```text
to_jsonb(OLD) - allowlist   IS DISTINCT FROM   to_jsonb(NEW) - allowlist   → raise
```

### Campi modificabili in PENDING (allowlist)

`stato_approvazione_prezzo`, `pratica_approvazione_prezzo_id`, `meta`,
`data_update`, `user_update`, `tx_id`.

Tutto il resto (incluse colonne di sistema immutabili come `id`, `data_insert`,
`user_insert`) è considerato struttura e bloccato.

### TG_ARGV[0] — colonna FK padre (solo contesto errore)

La colonna FK padre varia per tabella ed è usata **solo** per arricchire il payload
dell'errore (non incide sul confronto, che è interamente jsonb):

| Tabella | TG_ARGV[0] |
|---|---|
| `preventivi_righe` | `'preventivo_id'` |
| `contratti_righe` | `'contratto_id'` |
| `offerte_commerciali_eccezioni` | `'offerta_id'` |

---

### Transizioni ammesse / tentativi misti

- **Ammesse**: `PENDING → APPROVED`, `PENDING → REJECTED`, `PENDING → NULL` (reset
  richiesta) e l'aggancio/sgancio della pratica — sono cambi su colonne allowlisted.
- **Bloccato il tentativo misto**: se l'UPDATE cambia **sia** lo stato approvazione
  **sia** un campo struttura (es. "approva E riduci il prezzo"), scatta il raise: la
  decisione deve essere atomica e preservare la riga originale.

---

### Codici errore

| Codice | Quando |
|---|---|
| `E_RIGA_PREZZO_PENDENTE` (id 390) | UPDATE su un campo struttura quando `OLD.stato_approvazione_prezzo = 'PENDING'` |

Context payload JSONB: `riga_id`, `<col_fk_padre>` (valore), `campi_modificati`
(array dei campi struttura cambiati), `hint`.

---

### Quando NON scatta

- **`OLD.stato_approvazione_prezzo != 'PENDING'`**: early return immediato (nessun
  overhead su UPDATE normali — la gran parte dei casi in produzione).
- **INSERT** / **DELETE**: scope `BEFORE UPDATE`.
- **UPDATE di soli campi allowlisted su riga PENDING**: pass-through.

---

### Note operative

- **Equivalenza comportamentale** con le due guard dedicate sostituite: le uniche
  colonne extra-bloccate rispetto alle vecchie denylist (`id`, `data_insert`,
  `user_insert`) sono immutabili in UPDATE → nessuna regressione.
- **Ordine `_a10_`**: il trigger guard_pending mantiene la posizione lessicografica
  precedente (prima di audit/tx_id), preservando la catena trigger.
- **Migrazione**: il changeset `20260601-03` ha ripuntato i tre trigger
  `*_a10_guard_pending_upd` a questa funzione e droppato le due funzioni dedicate
  ora inutilizzate.
