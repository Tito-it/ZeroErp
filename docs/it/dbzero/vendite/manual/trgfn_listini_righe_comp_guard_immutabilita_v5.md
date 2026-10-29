# trgfn_listini_righe_comp_guard_immutabilita_v5

> **Vedi anche**
>
> - [vendite.listini_righe_componenti](/dbzero/vendite/manual/listini_righe_componenti) — tabella su cui il trigger opera
> - [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni) — fonte dello stato versione
> - [vendite.trgfn_listini_righe_guard_stato](/dbzero/vendite/manual/trgfn_listini_righe_guard_stato) — policy identica applicata alle righe listino standard
> - [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — gestione errori strutturata

## Scopo

Applica la policy di immutabilità v5 dei listini alle righe bundle in `vendite.listini_righe_componenti`. Una versione listino in stato diverso da `BOZZA` è immutabile: non si possono aggiungere nuove righe bundle, non si possono modificare prezzo, IVA o validità delle righe esistenti, e non si cancellano righe (usare `attivo = FALSE`). In una versione `BOZZA` le righe bundle si cancellano, come le righe normali: così una bozza si elimina con tutto quello che contiene ([vendite.fn_elimina_versione_listino](/dbzero/vendite/funzioni/fn_elimina_versione_listino)). Il trigger replica la policy già applicata alle righe listino standard (`trgfn_listini_righe_guard_stato`), estendendola alla tabella bundle.

> ⚠️ **Revoca parziale (28-10-2026, E-1 di Tid, brief `brief-modello-documento-vendita` §16.11).** Fino a quella data il DELETE era bloccato **sempre**, anche in bozza (regola del 13-05-2026, `brief-db-componenti-modello-unificato` §8.2). Una bozza con un composito non si poteva eliminare, contro la decisione O2 di `sviluppo-listini-v3`. Da `20261028-38` il DELETE in BOZZA si accetta; fuori dalla bozza resta bloccato.

---

## Schema DB

`vendite`

## Firma

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_listini_righe_comp_guard_immutabilita_v5()
RETURNS trigger
LANGUAGE plpgsql
```

## Trigger associato

| Attributo | Valore |
|---|---|
| Nome trigger | `trg_listrighe_comp_a10_guard_immutabilita_v5_ins_upd_dlt` |
| Tabella | `vendite.listini_righe_componenti` |
| Evento | `BEFORE INSERT OR UPDATE OR DELETE` |
| Fase | `_a10_` (guard) |
| Scope | `FOR EACH ROW` |

---

## Logica

Il trigger gestisce tre casi in base a `TG_OP`:

### DELETE — solo su versione BOZZA

```
stato della versione di OLD.listino_versione_id

IF TG_OP = 'DELETE' AND v_stato IS DISTINCT FROM 'BOZZA'
    → raise E_RIGA_LISTINO_VERSIONE_CHIUSA (362)
       context: { operazione: 'DELETE', hint: 'Usare attivo=FALSE', stato_versione,
                  listino_versione_id, riga_id }
```

Una versione che non si legge non è una bozza: il DELETE si rifiuta.

### INSERT — solo su versione BOZZA

```
SELECT lv.stato FROM vendite.listini_versioni lv
WHERE lv.id = NEW.listino_versione_id

IF TG_OP = 'INSERT' AND COALESCE(v_stato, 'BOZZA') <> 'BOZZA'
    → raise E_RIGA_LISTINO_VERSIONE_CHIUSA (362)
       context: { operazione: 'INSERT', stato_versione, listino_versione_id }
```

### UPDATE — campi core bloccati se versione non BOZZA

```
IF TG_OP = 'UPDATE' AND COALESCE(v_stato, 'BOZZA') <> 'BOZZA' THEN
    IF NEW.prezzo    IS DISTINCT FROM OLD.prezzo
    OR NEW.iva_id    IS DISTINCT FROM OLD.iva_id
    OR NEW.validita  IS DISTINCT FROM OLD.validita
        → raise E_RIGA_LISTINO_VERSIONE_CHIUSA (362)
           context: { operazione: 'UPDATE_CAMPI_CORE', stato_versione, listino_versione_id, riga_id }
```

Gli altri campi (es. `attivo`, `meta`) rimangono modificabili anche su versioni non-BOZZA.

---

## Campi core protetti su UPDATE

| Campo | Protetto in versione non-BOZZA |
|---|---|
| `prezzo` | Si |
| `iva_id` | Si |
| `validita` | Si |
| `attivo` | No — soft-delete sempre consentito |
| `meta` | No |

---

## Codici errore

| Codice | ID | Quando |
|---|---|---|
| `E_RIGA_LISTINO_VERSIONE_CHIUSA` | 362 | DELETE, INSERT o UPDATE dei campi core su versione non-BOZZA |

Il campo `operazione` nel contesto JSON distingue i tre scenari: `DELETE`, `INSERT`, `UPDATE_CAMPI_CORE`.

---

## Dipendenze

| Oggetto | Tipo | Motivo |
|---|---|---|
| `vendite.listini_versioni` | Tabella | Lettura stato versione per determinare immutabilità |
| `script.fn_log_and_raise_error` | Funzione | Registrazione e raise strutturato dell'errore |

---

## Coerenza con listini standard

Questo trigger replica la policy di `trgfn_listini_righe_guard_stato` applicata a `listini_righe`. Il codice errore `E_RIGA_LISTINO_VERSIONE_CHIUSA` (362) è condiviso tra le due tabelle per uniformità del comportamento dal punto di vista del backend Django e dell'API.

---

## Note operative

- Su INSERT e UPDATE il `COALESCE(v_stato, 'BOZZA')` lascia passare: se la versione non viene trovata (improbabile per vincolo FK), il trigger non blocca l'operazione. Sul DELETE no: una versione che non si legge non è una bozza.
- Per modificare una riga bundle in una versione attiva o chiusa, è necessario creare una nuova versione listino in stato `BOZZA` e replicare la riga con i nuovi valori.
- Migration di riferimento: `20260513-20`; stato dal vocabolario `20261028-22`; DELETE in BOZZA `20261028-38`.
