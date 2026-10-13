# trgfn_articoli_guard_iva_bom_attiva

> **Vedi anche**
>
> - [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — tabella su cui il trigger opera
> - [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — lookup BoM attive
> - [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — gestione errori strutturata
> - [catalogo.trgfn_articoli_componenti_guard_componente](/dbzero/catalogo/manual/trgfn_articoli_componenti_guard_componente) — il lato legame: il guard di tabella della distinta (`E_BOM_IVA_DISCORDANTE`)

## Scopo

Impedisce la modifica di `iva_id` su un articolo che partecipa come padre o figlio a una BoM attiva, se tale modifica romperebbe l'invariante IVA uniforme del modello unificato BoM. Il trigger opera in due casi distinti: quando l'articolo modificato è un padre composito (verifica i figli), e quando è un figlio (verifica i padri). In entrambi i casi, la presenza di anche un solo articolo correlato con IVA diversa blocca l'operazione.

---

## Schema DB

`catalogo`

## Firma

```sql
CREATE OR REPLACE FUNCTION catalogo.trgfn_articoli_guard_iva_bom_attiva()
RETURNS trigger
LANGUAGE plpgsql
```

## Trigger associato

| Attributo | Valore |
|---|---|
| Nome trigger | `trg_articoli_a10_guard_iva_bom_attiva_upd` |
| Tabella | `catalogo.articoli` |
| Evento | `BEFORE UPDATE OF iva_id` |
| Fase | `_a10_` (guard) |
| Scope | `FOR EACH ROW` |
| Ottimizzazione | `UPDATE OF iva_id` — non aggiunge overhead su update di altri campi dell'articolo |

---

## Logica

Il trigger esegue due controlli separati in sequenza:

### Caso A — Articolo padre composito

Attivo solo se `NEW.is_composito = TRUE`. Cerca in `articoli_componenti` un figlio attivo con `iva_id` diverso da `NEW.iva_id`:

```
SELECT a.codice, a.iva_id
FROM catalogo.articoli_componenti ac
JOIN catalogo.articoli a ON a.id = ac.componente_id
WHERE ac.prodotto_id = NEW.id
  AND ac.attivo = TRUE
  AND a.iva_id IS DISTINCT FROM NEW.iva_id
LIMIT 1
```

Se trovato → raise `E_BOM_IVA_DISCORDANTE` (445).

### Caso B — Articolo figlio in BoM attive

Sempre eseguito (indipendente da `is_composito`). Cerca in `articoli_componenti` un padre attivo con `iva_id` diverso da `NEW.iva_id`:

```
SELECT a.codice, a.iva_id
FROM catalogo.articoli_componenti ac
JOIN catalogo.articoli a ON a.id = ac.prodotto_id
WHERE ac.componente_id = NEW.id
  AND ac.attivo = TRUE
  AND a.iva_id IS DISTINCT FROM NEW.iva_id
LIMIT 1
```

Se trovato → raise `E_BOM_IVA_DISCORDANTE` (445).

---

## Guard

| Caso | Condizione di attivazione | Cosa cerca | Errore |
|---|---|---|---|
| A — padre composito | `NEW.is_composito = TRUE` | Figlio attivo con `iva_id != NEW.iva_id` | `E_BOM_IVA_DISCORDANTE` (445) |
| B — figlio in BoM | Sempre | Padre attivo con `iva_id != NEW.iva_id` | `E_BOM_IVA_DISCORDANTE` (445) |

---

## Codici errore

| Codice | ID | Quando |
|---|---|---|
| `E_BOM_IVA_DISCORDANTE` | 445 | La nuova `iva_id` è incompatibile con almeno un partner BoM attivo |

Contesto JSON (Caso A): `prodotto_id`, `iva_padre_nuova`, `codice_figlio`, `iva_figlio`.  
Contesto JSON (Caso B): `componente_id`, `iva_figlio_nuova`, `codice_padre`, `iva_padre`.

---

## Dipendenze

| Oggetto | Tipo | Motivo |
|---|---|---|
| `catalogo.articoli_componenti` | Tabella | Lookup BoM attive per trovare partner con IVA incompatibile |
| `script.fn_log_and_raise_error` | Funzione | Registrazione e raise strutturato dell'errore |

---

## Note operative

- Il confronto usa `IS DISTINCT FROM`: NULL = NULL è considerato uguale, quindi un articolo con `iva_id = NULL` che modifica verso `NULL` non viene bloccato anche se ha partner con `iva_id = NULL`.
- La `LIMIT 1` garantisce che anche in BoM con molti figli il trigger si fermi al primo conflitto senza scansionare l'intera tabella.
- Per modificare `iva_id` su un articolo con BoM attive è necessario prima aggiornare tutti i partner BoM alla nuova IVA, poi aggiornare l'articolo stesso.
- Migration di riferimento: `20260513-03`.
