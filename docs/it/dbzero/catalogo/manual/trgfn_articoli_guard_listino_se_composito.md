# trgfn_articoli_guard_listino_se_composito

> **Vedi anche**
>
> - [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — tabella su cui il trigger opera
> - [vendite.listini_righe](/dbzero/vendite/tabelle/listini_righe) — tabella verificata per righe attive
> - [script.fn_check_articolo_riga](/dbzero/script/manual/fn_check_articolo_riga) — il lato riga: il motivo `E_LISTINO_RIGA_COMPOSITO_VIETATO` della versione di listino (dal 2026-10-13; prima `vendite.trgfn_listini_righe_guard_no_composito`)
> - [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — gestione errori strutturata

## Scopo

Impedisce di marcare un articolo come composito (`is_composito = TRUE`) se l'articolo ha già righe attive in `vendite.listini_righe`. Quei prezzi diretti sarebbero semanticamente errati per un composito, il cui prezzo deve essere calcolato come somma dei componenti. Il trigger costituisce il guard simmetrico di `trgfn_listini_righe_guard_no_composito`: i due trigger insieme garantiscono che compositi e `listini_righe` non si sovrappongano mai in nessuna direzione.

---

## Schema DB

`catalogo`

## Firma

```sql
CREATE OR REPLACE FUNCTION catalogo.trgfn_articoli_guard_listino_se_composito()
RETURNS trigger
LANGUAGE plpgsql
```

## Trigger associato

| Attributo | Valore |
|---|---|
| Nome trigger | `trg_articoli_a10_guard_listino_se_composito_upd` |
| Tabella | `catalogo.articoli` |
| Evento | `BEFORE UPDATE OF is_composito` |
| Fase | `_a10_` (guard) |
| Scope | `FOR EACH ROW` |
| Ottimizzazione | `UPDATE OF is_composito` — non aggiunge overhead su update di altri campi articolo |

---

## Logica

Il trigger scatta solo quando `is_composito` transita da `FALSE`/`NULL` a `TRUE`. Non interviene su altre variazioni del campo (es. `TRUE → FALSE`, bloccato da
[`trgfn_articoli_guard_flags_struttura_bom_attiva`](/dbzero/catalogo/manual/trgfn_articoli_guard_flags_struttura_bom_attiva)
quando la BoM e' attiva — migration `20260522-01`).

```
1. IF NOT COALESCE(OLD.is_composito, FALSE)
      AND COALESCE(NEW.is_composito, FALSE)
   THEN
       IF EXISTS (
           SELECT 1 FROM vendite.listini_righe lr
            WHERE lr.articolo_id = NEW.id
              AND lr.attivo = TRUE
           LIMIT 1
       )
           → raise E_LISTINO_RIGA_COMPOSITO_VIETATO (446)
```

---

## Codici errore

| Codice | ID | Quando |
|---|---|---|
| `E_LISTINO_RIGA_COMPOSITO_VIETATO` | 446 | Si tenta di promuovere a composito un articolo con righe attive in `listini_righe` |

Contesto JSON: `articolo_id`, `hint` con indicazione di disattivare le righe listino prima della promozione.

---

## Dipendenze

| Oggetto | Tipo | Motivo |
|---|---|---|
| `vendite.listini_righe` | Tabella | Verifica esistenza di righe attive per l'articolo |
| `script.fn_log_and_raise_error` | Funzione | Registrazione e raise strutturato dell'errore |

---

## Guard simmetrico

| Trigger | Evento | Cosa blocca |
|---|---|---|
| `trgfn_articoli_guard_listino_se_composito` | UPDATE OF `is_composito` su `articoli` | Promozione a composito di articolo con righe listino esistenti |
| `script.fn_check_articolo_riga` (guard di tabella su `listini_righe`) | INSERT/UPDATE su `listini_righe` | Inserimento diretto per articolo già composito |

---

## Note operative

- Per promuovere un articolo a composito quando ha già righe in `listini_righe`, è necessario prima disattivare tutte le righe listino esistenti (`attivo = FALSE`), poi eseguire l'UPDATE `is_composito = TRUE`.
- L'hint incluso nel contesto JSON dell'errore riporta esplicitamente questa procedura.
- La query di verifica usa `LIMIT 1` per fermarsi al primo match senza scansionare l'intera tabella.
- Migration di riferimento: `20260513-05`.
