## 📘 Documentazione Concettuale – Trigger Function `script.trgfn_componenti_guard_pending()`

> 👀 **Vedi anche**
>
> [config.stato_approvazione_prezzo](/dbzero/config/tabelle/stati_approvazione_prezzo) — enum PENDING/APPROVED/REJECTED
> [vendite.contratti_righe_componenti](/dbzero/vendite/tabelle/contratti_righe_componenti) — prima tabella utente
> [vendite.offerte_commerciali_eccezioni_componenti](/dbzero/vendite/tabelle/offerte_commerciali_eccezioni_componenti) — seconda tabella utente
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

Trigger function **BEFORE UPDATE** generica per tabelle `*_componenti` BoM CASO A.
Blocca le modifiche ai **campi struttura** di un componente quando la sua
richiesta di approvazione prezzo è in stato `PENDING`.

---

### 🎯 Scopo Principale

Quando un componente ha `stato_approvazione_prezzo = 'PENDING'` (richiesta L3 in
attesa di esito), è necessario garantire che i dati su cui si basa la richiesta di
approvazione non vengano modificati fino alla risoluzione.

Questa funzione è la **generalizzazione** di 5 guard domain-specific
(`trgfn_preventivi_righe_componenti_guard_pending`, ecc.) che contenevano logica
identica con il solo nome della colonna FK padre diverso.

---

### TG_ARGV[0] — Parametrizzazione colonna FK padre

La colonna FK padre varia per tabella:

| Tabella | TG_ARGV[0] |
|---|---|
| `contratti_righe_componenti` | `'riga_contratto_id'` |
| `offerte_commerciali_eccezioni_componenti` | `'eccezione_offerta_id'` |
| (future tabelle) | nome colonna FK padre |

La funzione usa `EXECUTE format(...)` per confrontare dinamicamente la colonna
FK nel `OLD`/`NEW` record, evitando la necessità di cloni domain-specific.

---

### Campi bloccati in PENDING (denylist)

| Categoria | Campi |
|---|---|
| FK padre | `<col_fk_padre>` (dinamico da TG_ARGV[0]) |
| Identificatori BoM | `articolo_componente_id`, `componente_id` |
| Quantità | `coeff_qta_snapshot`, `quantita` |
| UoM | `uom_operativa_id`, `factor_to_base`, `qta_operativa` |
| Prezzo | `prezzo_unitario`, `iva_id`, `origine_prezzo` |
| Presentazione | `ordine`, `attivo` |

### Campi modificabili in PENDING (allowlist implicita)

`stato_approvazione_prezzo`, `pratica_approvazione_prezzo_id`,
`meta`, `data_update`, `user_update`, `tx_id`.

---

### Codici errore

| Codice | Quando |
|---|---|
| `E_COMPONENTE_PREZZO_PENDENTE` | UPDATE su campo struttura quando `stato_approvazione_prezzo = 'PENDING'` |

---

### Note operative

- **Pattern difensivo**: se la tabella viene estesa con nuove colonne struttura, aggiornare la denylist nella funzione.
- **Attivo solo se OLD era PENDING**: nessun overhead su UPDATE normali (guard cortocircuita immediatamente se `OLD.stato_approvazione_prezzo IS DISTINCT FROM 'PENDING'`).
- **Migrazione contratti**: il changeset `20260526-23-12` ha aggiornato il trigger su `contratti_righe_componenti` da `trgfn_contratti_righe_componenti_guard_pending()` (funzione specifica ora droppata) a `script.trgfn_componenti_guard_pending('riga_contratto_id')`.
