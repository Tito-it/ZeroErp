# trgfn_componenti_guard_obbligatorio

> **Vedi anche**
>
> - [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — lookup flag `obbligatorio`
> - [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — lookup `codice` del componente
> - [script.trgfn_componenti_check_prezzo_obbligatorio](/dbzero/script/manual/trgfn_componenti_check_prezzo_obbligatorio) — guard complementare su prezzo zero
> - [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — gestione errori strutturata

## Scopo

Blocca la disattivazione (`attivo: TRUE → FALSE`) di componenti BoM marcati `obbligatorio = TRUE` nelle tabelle `*_righe_componenti`. Un componente obbligatorio fa sempre parte del documento e non può essere escluso dall'operatore: per rimuoverlo è necessario modificare la BoM stessa in `catalogo.articoli_componenti`. I componenti opzionali (`obbligatorio = FALSE`) possono invece essere attivati e disattivati liberamente dall'operatore nel contesto del singolo documento.

---

## Schema DB

`script` (funzione generica riusata da più tabelle)

## Firma

```sql
CREATE OR REPLACE FUNCTION script.trgfn_componenti_guard_obbligatorio()
RETURNS trigger
LANGUAGE plpgsql
```

## Trigger registrati

La stessa funzione è registrata su 4 tabelle:

| Trigger | Tabella | Evento |
|---|---|---|
| `trg_prevrighe_comp_a10_guard_obbligatorio_upd` | `vendite.preventivi_righe_componenti` | `BEFORE UPDATE OF attivo` |
| `trg_ordrighe_comp_a10_guard_obbligatorio_upd` | `vendite.ordini_righe_componenti` | `BEFORE UPDATE OF attivo` |
| `trg_ddtrighe_comp_a10_guard_obbligatorio_upd` | `vendite.ddt_righe_componenti` | `BEFORE UPDATE OF attivo` |
| `trg_contrighe_comp_a10_guard_obbligatorio_upd` | `vendite.contratti_righe_componenti` | `BEFORE UPDATE OF attivo` |

Tutti con fase `_a10_` (guard), scope `FOR EACH ROW`.

---

## Logica

```
1. IF OLD.attivo = TRUE AND NEW.attivo = FALSE THEN

2.     SELECT ac.obbligatorio, a.codice
       FROM catalogo.articoli_componenti ac
       JOIN catalogo.articoli a ON a.id = ac.componente_id
       WHERE ac.id = OLD.articolo_componente_id

3.     IF COALESCE(v_obbligatorio, TRUE)
           → raise E_DOC_COMPONENTE_OBBLIGATORIO (443)
```

Il trigger si attiva solo sulla transizione `TRUE → FALSE` del flag `attivo`. Attivazioni (`FALSE → TRUE`) non sono verificate. Il `COALESCE(v_obbligatorio, TRUE)` è conservativo: se il record BoM non viene trovato, il componente viene trattato come obbligatorio.

---

## Ottimizzazione

L'uso di `BEFORE UPDATE OF attivo` garantisce che il trigger venga invocato esclusivamente quando la colonna `attivo` viene modificata, senza aggiungere overhead su update di altri campi delle righe componente (es. aggiornamento prezzo, quantità, note).

---

## Codici errore

| Codice | ID | Quando |
|---|---|---|
| `E_DOC_COMPONENTE_OBBLIGATORIO` | 443 | Si tenta di disattivare un componente con `obbligatorio = TRUE` |

Contesto JSON: `articolo_componente_id`, `componente_id`.

---

## Dipendenze

| Oggetto | Tipo | Motivo |
|---|---|---|
| `catalogo.articoli_componenti` | Tabella | Lookup flag `obbligatorio` |
| `catalogo.articoli` | Tabella | Lookup `codice` del componente per il messaggio di errore |
| `script.fn_log_and_raise_error` | Funzione | Registrazione e raise strutturato dell'errore |

---

## Note operative

- La distinzione obbligatorio/opzionale è definita a livello di BoM catalogo (`catalogo.articoli_componenti.obbligatorio`) e non può essere sovrascritta nel documento.
- Per escludere un componente obbligatorio dai nuovi documenti si cambia la distinta, non il documento: si chiude il legame (`valido_al`, al più presto ieri) e, se il componente deve restare come opzionale, si inserisce un legame nuovo con `obbligatorio = FALSE` che parte dal giorno dopo. `obbligatorio` è un campo di struttura e non si modifica sul legame esistente, e un legame citato da un documento non si spegne (`attivo`): li rifiutano i trigger della distinta.
- I componenti opzionali (`obbligatorio = FALSE`) non sono soggetti a questo guard e possono essere attivati/disattivati liberamente.
- Migration di riferimento: `20260513-17`.
