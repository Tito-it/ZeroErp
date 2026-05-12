# trgfn_listini_righe_guard_no_composito

> **Vedi anche**
>
> - [vendite.listini_righe](/dbzero/vendite/tabelle/listini_righe) — tabella su cui il trigger opera
> - [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — lookup `is_composito`
> - [vendite.listini_righe_componenti](/dbzero/vendite/manual/listini_righe_componenti) — tabella corretta per i prezzi bundle
> - [catalogo.trgfn_articoli_guard_listino_se_composito](/dbzero/catalogo/manual/trgfn_articoli_guard_listino_se_composito) — guard simmetrico su UPDATE is_composito dell'articolo
> - [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — gestione errori strutturata

## Scopo

Vieta l'inserimento di righe listino direttamente su articoli compositi. Il modello unificato BoM (2026-05-13) stabilisce che il prezzo di un articolo composito è sempre la somma dei prezzi dei suoi componenti (`SUM` su `listini_righe_componenti`): un prezzo diretto in `listini_righe` per un composito sarebbe semanticamente errato e confliggerebbe con il resolver bundle-aware `fn_resolve_prezzo_listino_v2`.

---

## Schema DB

`vendite`

## Firma

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_listini_righe_guard_no_composito()
RETURNS trigger
LANGUAGE plpgsql
```

## Trigger associato

| Attributo | Valore |
|---|---|
| Nome trigger | `trg_listini_righe_a10_guard_no_composito_ins` |
| Tabella | `vendite.listini_righe` |
| Evento | `BEFORE INSERT` |
| Fase | `_a10_` (guard) |
| Scope | `FOR EACH ROW` |
| UPDATE escluso | `articolo_id` è bloccato da altri guard esistenti su `listini_righe` |

---

## Logica

```
1. SELECT a.is_composito, a.codice
   FROM catalogo.articoli a
   WHERE a.id = NEW.articolo_id

2. IF COALESCE(v_is_composito, FALSE) = TRUE
      → raise E_LISTINO_RIGA_COMPOSITO_VIETATO (446)
```

Se l'articolo non esiste nella query (FK violation intercettata prima), `COALESCE(NULL, FALSE)` restituisce `FALSE` e il trigger non blocca.

---

## Codici errore

| Codice | ID | Quando |
|---|---|---|
| `E_LISTINO_RIGA_COMPOSITO_VIETATO` | 446 | Si tenta di inserire una riga listino per un articolo con `is_composito = TRUE` |

Contesto JSON: `articolo_id`, `listino_versione_id`.

---

## Dipendenze

| Oggetto | Tipo | Motivo |
|---|---|---|
| `catalogo.articoli` | Tabella | Lookup `is_composito` e `codice` |
| `script.fn_log_and_raise_error` | Funzione | Registrazione e raise strutturato dell'errore |

---

## Guard simmetrico

Questo trigger e `catalogo.trgfn_articoli_guard_listino_se_composito` formano una coppia simmetrica:

| Trigger | Evento | Cosa blocca |
|---|---|---|
| `trgfn_listini_righe_guard_no_composito` | INSERT su `listini_righe` | Inserimento diretto per articolo già composito |
| `trgfn_articoli_guard_listino_se_composito` | UPDATE OF `is_composito` su `articoli` | Promozione a composito di articolo con righe listino esistenti |

I due trigger insieme garantiscono che compositi e `listini_righe` non si sovrappongano mai in nessuna direzione.

---

## Note operative

- Per assegnare prezzi a un composito, usare `vendite.listini_righe_componenti` per ciascun componente della BoM. Il prezzo del composito viene calcolato automaticamente come somma.
- Se un articolo standalone viene promosso a composito, è necessario prima rimuovere (disattivare) le eventuali righe in `listini_righe`, poi procedere con l'UPDATE di `is_composito`.
- Migration di riferimento: `20260513-04`.
