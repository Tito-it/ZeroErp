# trgfn_listini_righe_comp_guard_coerenza_bom

> **Ultimo aggiornamento**: 8 novembre 2026
>
> **Vedi anche**
>
> - [vendite.listini_righe_componenti](/dbzero/vendite/manual/listini_righe_componenti) — tabella su cui il trigger opera
> - [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — sorgente verità BoM
> - [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — padre e figlio per check IVA e is_composito
> - [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni) — verifica validità versione (guard 7)
> - [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — gestione errori strutturata

## Scopo

Esegue 5 guard di coerenza (1–4 + 7) per garantire che ogni riga inserita o aggiornata in `vendite.listini_righe_componenti` sia perfettamente allineata con la BoM catalogo e con i vincoli di validità temporale. È il punto di verità centralizzato per l'integrità della tabella bundle: senza questi guard, le colonne denorm (`articolo_padre_id`, `articolo_figlio_id`) potrebbero divergere dalla BoM, o potrebbero esistere prezzi bundle per periodi non coperti dalla versione listino.

> La coerenza IVA padre=figlio **non** è più verificata qui: era il Guard 5, rimosso il 2026-06-03 perché ridondante. L'invariante è garantito a punto unico alla sorgente da [`catalogo.trgfn_articoli_componenti_guard_componente`](/dbzero/catalogo/funzioni/trgfn_articoli_componenti_guard_componente) (motivo `E_BOM_IVA_DISCORDANTE`, INSERT + riattivazione) e [`catalogo.trgfn_articoli_guard_iva_bom_attiva`](/dbzero/catalogo/funzioni/trgfn_articoli_guard_iva_bom_attiva).

---

## Schema DB

`script` (funzione generica cross-dominio)

## Firma

```sql
CREATE OR REPLACE FUNCTION script.trgfn_listini_righe_comp_guard_coerenza_bom()
RETURNS trigger
LANGUAGE plpgsql
```

## Trigger associato

| Attributo | Valore |
| --- | --- |
| Nome trigger | `trg_listrighe_comp_a10_guard_coerenza_bom_ins_upd` |
| Tabella | `vendite.listini_righe_componenti` |
| Evento | `BEFORE INSERT OR UPDATE` |
| Fase | `_a10_` (guard) |
| Scope | `FOR EACH ROW` |

---

## Guard attivi

| # | Condizione verificata | Causa errore se fallisce |
| --- | --- | --- |
| 1 | `articolo_componente_id` esiste in `catalogo.articoli_componenti` e `attivo = TRUE` | `articolo_componente_id non trovato o non attivo` |
| 2 | `NEW.articolo_padre_id = ac.prodotto_id` (denorm coerente) | `articolo_padre_id non coincide con BoM.prodotto_id` |
| 3 | `NEW.articolo_figlio_id = ac.componente_id` (denorm coerente) | `articolo_figlio_id non coincide con BoM.componente_id` |
| 4 | `padre.is_composito = TRUE` | `articolo padre non e'' composito` |
| ~~5~~ | ~~`figlio.iva_id = padre.iva_id`~~ | **RIMOSSO** (20260603-03): coerenza IVA garantita a punto unico alla sorgente `articoli_componenti` (guard IVA su INSERT+riattivazione, guard B su `iva_id`, freeze struttura). Il ri-controllo a valle era ridondante |
| ~~6~~ | ~~`NEW.validita ⊆ ac.validita`~~ | **RIMOSSO** (20260514-13): sostituito dalla temporal FK `fk_listrighe_comp_articoli_comp_temporal` su `(articolo_componente_id, PERIOD validita)` → `articoli_componenti (id, PERIOD validita)` |
| 7 | `v_new_validita ⊆ lv.validita` (validità riga ⊆ validità versione listino) | `validita riga listino comp non contenuta in validita versione listino` |

Tutti i guard attivi sollevano `E_LISTINO_COMPONENTE_COERENZA_BOM` (447) con la causa specifica nel contesto JSON.

---

## Logica di esecuzione

La funzione esegue una **singola query con LEFT JOIN** per leggere in un round-trip tutti i dati necessari ai guard 1–4 e 7:

```sql
-- Calcolo range riga: COALESCE simmetrico alla STORED expression di listini_versioni.validita
v_new_validita := daterange(
    COALESCE(NEW.valido_dal, '-infinity'::date),
    COALESCE(NEW.valido_al,  'infinity'::date),
    '[]'
);

-- Unica query: BoM + articolo padre + versione listino
-- (a_figlio non serve più: Guard 5 rimosso; componente_id è FK verso articoli,
--  quindi Guard 1 NOT FOUND resta garantito da ac)
SELECT ac.prodotto_id, ac.componente_id, ac.attivo,
       a_padre.is_composito,
       lv.validita
  FROM catalogo.articoli_componenti ac
  JOIN catalogo.articoli a_padre ON a_padre.id = ac.prodotto_id
  LEFT JOIN vendite.listini_versioni lv ON lv.id = NEW.listino_versione_id
 WHERE ac.id = NEW.articolo_componente_id;
```

`LEFT JOIN` su `listini_versioni`: se la versione non esiste, `lv.validita = NULL` → guard 7 si attiva via `v_lv_validita IS NULL`.

### Calcolo v_new_validita — COALESCE obbligatorio

`listini_righe_componenti.validita` è **STORED generated**: in un BEFORE trigger `NEW.validita` è sempre `NULL`. Il range viene calcolato manualmente applicando COALESCE su entrambi i bounds, in modo simmetrico alla STORED expression di `listini_versioni.validita`.

Il COALESCE è essenziale per evitare un mismatch di rappresentazione interna:

| Sorgente | `valido_al = NULL` → testo range | `upper_inf` interno |
| --- | --- | --- |
| `listini_versioni.validita` (STORED con COALESCE) | `[d,infinity]` | `false` — bound finito |
| `daterange(d, NULL, '[]')` senza COALESCE | `[d,)` | `true` — unbounded |

`[d,infinity] @> [d,)` restituisce `false` anche se i due range sono logicamente identici: PostgreSQL confronta le rappresentazioni interne, non la semantica. Con COALESCE entrambi i lati producono `[d,infinity]` e il confronto è corretto (fix 20260515-01).

---

## Codici errore

| Codice | ID | Quando |
| --- | --- | --- |
| `E_LISTINO_COMPONENTE_COERENZA_BOM` | 447 | Qualsiasi guard attivo fallisce; la causa specifica è nel contesto JSON |

Il campo `causa` nel contesto JSON identifica quale guard ha prodotto l'errore.

---

## Dipendenze

| Oggetto | Tipo | Motivo |
| --- | --- | --- |
| `catalogo.articoli_componenti` | Tabella | Sorgente verità BoM (guard 1–4) |
| `catalogo.articoli` | Tabella | `is_composito` del padre (guard 4) |
| `vendite.listini_versioni` | Tabella | Verifica validità versione via `lv.validita` (guard 7) |
| `fk_listrighe_comp_articoli_comp_temporal` | FK temporale PG 18 | Sostituisce guard 6: containment `riga.validita ⊆ ac.validita` garantito per costruzione |
| `script.fn_log_and_raise_error` | Funzione | Registrazione e raise strutturato dell'errore |

---

## Note operative

- **Guard 6 rimosso (20260514-13)**: il containment `riga.validita ⊆ ac.validita` era ridondante con la temporal FK `fk_listrighe_comp_articoli_comp_temporal` introdotta in PG 18. La FK garantisce la proprietà per costruzione, senza codice procedurale.
- **Guard 7 e `valido_al = NULL`**: il COALESCE in `v_new_validita` gestisce correttamente il caso di apertura indefinita. Se il caller passa `valido_al = NULL`, `COALESCE(NULL, 'infinity'::date)` produce `[d,infinity]`, identico alla STORED della versione con `valido_al = NULL`. Il guard 7 restituisce `true` correttamente.
- **Guard 7 e versione mancante**: se `listino_versione_id` non esiste, il LEFT JOIN ritorna `lv.validita = NULL` → `v_lv_validita IS NULL` → guard 7 scatta.
- **Guard 5 rimosso (20260603-03)**: la coerenza IVA padre=figlio è ora garantita a punto unico alla sorgente `catalogo.articoli_componenti`. Con guard IVA su INSERT+riattivazione (oggi il guard di tabella della distinta, `catalogo.trgfn_articoli_componenti_guard_componente`), guard B su `iva_id` (`trgfn_articoli_guard_iva_bom_attiva`) e freeze struttura (`componente_id` immutabile), una BoM attiva non può avere padre e figlio a IVA diversa: il ri-controllo nel listino era ridondante e creava asimmetria con i guard documento (che non controllano l'IVA).
- **`NEW.validita` non usabile nei BEFORE trigger**: `listini_righe_componenti.validita` è STORED generated → sempre `NULL` nel BEFORE trigger (D-OPEN-1, verificato su PG 18.3). Usare sempre `daterange(COALESCE(NEW.valido_dal,...), COALESCE(NEW.valido_al,...), '[]')`.

---

## Storico revisioni

| Rev | Migration | Modifica |
| --- | --- | --- |
| 2026-05-13 | 20260513-19 | Creazione — guards 1–7, due query separate |
| 2026-05-14 | 20260514-05 | STORED generated su `listini_righe_componenti`: guards 6+7 usano `valido_dal/valido_al` invece di `NEW.validita` (NULL nei BEFORE trigger) |
| 2026-05-14 | 20260514-13 | Guard 6 rimosso — sostituito da temporal FK |
| 2026-05-14 | 20260514-14 | Ottimizzazione: unica query con LEFT JOIN (elimina round-trip extra per guard 7) |
| 2026-05-15 | 20260515-01 | Fix COALESCE simmetrico su `v_new_validita`: corregge mismatch `upper_inf=true` vs `upper='infinity'::date` in `@>` quando `valido_al = NULL` |
| 2026-06-03 | 20260603-03 | Guard 5 rimosso (coerenza IVA a punto unico alla sorgente); eliminati JOIN `a_figlio` e colonne `iva_id` dalla query |
