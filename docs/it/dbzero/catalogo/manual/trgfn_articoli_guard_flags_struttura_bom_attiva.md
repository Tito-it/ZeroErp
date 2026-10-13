# trgfn_articoli_guard_flags_struttura_bom_attiva

> **Vedi anche**
>
> - [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — tabella su cui il trigger opera
> - [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — lookup BoM attive
> - [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — gestione errori strutturata
> - [catalogo.trgfn_articoli_guard_iva_bom_attiva](/dbzero/catalogo/manual/trgfn_articoli_guard_iva_bom_attiva) — guard simmetrico su UPDATE OF iva_id
> - [catalogo.trgfn_articoli_guard_listino_se_composito](/dbzero/catalogo/manual/trgfn_articoli_guard_listino_se_composito) — guard correlato su is_composito (direzione FALSE→TRUE)

## Scopo

(latest review 2026-10-13: check 3, un componente non diventa composito)

Blocca le modifiche ai flag di struttura `is_composito`, `is_solo_componente` e
`requires_serial` su `catalogo.articoli` quando esiste una BoM attiva che renderebbe
il cambio semanticamente incoerente.

I tre flag governano il ruolo dell'articolo nel modello BoM. Modificarli con BoM
attive in essere crea incoerenze strutturali non riparabili automaticamente:

- **`is_composito = FALSE`** con figli BoM attivi: il padre diventerebbe "non composito"
  ma avrebbe ancora componenti attivi orfani, con effetti imprevedibili su resolver
  prezzi e pipeline fatturazione.
- **`requires_serial = FALSE`** con figli BoM attivi: si rimuove il requisito di
  tracciabilita' seriale su un articolo che ha ancora partner BoM che lo richiedono.
- **`is_solo_componente = FALSE`** con l'articolo figlio in BoM attive: l'articolo
  passerebbe a "vendibile standalone" mentre e' ancora componente attivo di compositi,
  aprendo la possibilita' di ordini diretti su un pezzo non pensato per essere venduto
  autonomamente.

---

## Schema DB

`catalogo`

## Firma

```sql
CREATE OR REPLACE FUNCTION catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva()
RETURNS trigger
LANGUAGE plpgsql
```

## Trigger associato

| Attributo | Valore |
| --- | --- |
| Nome trigger | `trg_articoli_a10_guard_flags_struttura_bom_attiva_upd` |
| Tabella | `catalogo.articoli` |
| Evento | `BEFORE UPDATE OF is_composito, is_solo_componente, requires_serial` |
| Fase | `_a10_` (guard) |
| Scope | `FOR EACH ROW` |
| Ottimizzazione | `UPDATE OF` sui 3 flag — non aggiunge overhead su UPDATE di altri campi dell'articolo |

---

## Logica

Tre controlli distinti in sequenza: i primi due con semantiche opposte (`prodotto_id` vs
`componente_id`), il terzo sul passaggio a composito.
Ogni controllo esegue la query EXISTS solo se il flag corrispondente cambia effettivamente
(`IS DISTINCT FROM`).

### Check 1 — `is_composito` / `requires_serial` (l'articolo e' padre)

Attivo se `OLD.is_composito IS DISTINCT FROM NEW.is_composito`
**oppure** `OLD.requires_serial IS DISTINCT FROM NEW.requires_serial`.

Cerca in `articoli_componenti` almeno un figlio attivo valido oggi (il giorno aziendale,
`script.fn_data_operativa()`, dal 2026-10-09):

```sql
SELECT EXISTS (
    SELECT 1 FROM catalogo.articoli_componenti
     WHERE prodotto_id = NEW.id
       AND attivo IS TRUE
       AND validita @> (SELECT script.fn_data_operativa())
)
```

Se trovato → raise `E_BOM_MODIFICA_VIETATA` (387).

### Check 2 — `is_solo_componente` (l'articolo e' figlio)

Attivo se `OLD.is_solo_componente IS DISTINCT FROM NEW.is_solo_componente`.

Cerca in `articoli_componenti` almeno una BoM attiva che usa l'articolo come figlio:

```sql
SELECT EXISTS (
    SELECT 1 FROM catalogo.articoli_componenti
     WHERE componente_id = NEW.id
       AND attivo IS TRUE
       AND validita @> (SELECT script.fn_data_operativa())
)
```

Se trovato → raise `E_BOM_MODIFICA_VIETATA` (387).

### Check 3 — `is_composito` da FALSE a TRUE (l'articolo e' figlio)

Dal 2026-10-13 (`20261013-03`, brief-db-articoli-ammessi-per-documento D-4). La distinta ha
un livello solo ([modello componenti BoM §9.2](/dev/manual/modello-componenti-bom)): un
articolo che e' componente di una distinta **in vigore o futura** non diventa composito.

Attivo solo se `NEW.is_composito` e' vero e `OLD.is_composito` non lo era. Cerca il primo
padre (per codice) di un legame attivo con `validita && [oggi, inf)`: a differenza dei check 1
e 2 guarda anche i legami che entrano in vigore piu' avanti, perche' da quel giorno la distinta
avrebbe due livelli. Un legame scaduto e' storia e non conta.

Se trovato → raise `E_BOM_COMPONENTE_DIVENTA_COMPOSITO` (1294), campo `is_composito`, con il
codice dell'articolo e quello del padre nel messaggio. Il lato legame e'
[`catalogo.trgfn_articoli_componenti_guard_componente`](/dbzero/catalogo/manual/trgfn_articoli_componenti_guard_componente) (motivo `E_BOM_COMPONENTE_COMPOSITO` di `script.fn_check_articolo_riga`).
Il gemello per il form e' la regola su `is_composito` in `dbops.lock_columns_conditional`
(`20261013-04`), che spegne il campo solo su un articolo ancora semplice.

---

## Guard

| Check | Flag coinvolti | Ruolo articolo | Query EXISTS su | Errore |
| --- | --- | --- | --- | --- |
| 1 | `is_composito`, `requires_serial` | Padre composito | `prodotto_id = NEW.id` | `E_BOM_MODIFICA_VIETATA` (387) |
| 2 | `is_solo_componente` | Figlio in BoM | `componente_id = NEW.id` | `E_BOM_MODIFICA_VIETATA` (387) |
| 3 | `is_composito` FALSE→TRUE | Figlio in BoM in vigore o futura | `componente_id = NEW.id` | `E_BOM_COMPONENTE_DIVENTA_COMPOSITO` (1294) |

Condizione BoM attiva (check 1 e 2): `attivo IS TRUE AND validita @> script.fn_data_operativa()`; check 3: `attivo IS TRUE AND validita && [oggi, inf)`
(colonna `validita` GENERATED ALWAYS STORED su `articoli_componenti`).

---

## Codici errore

| Codice | ID | Quando |
| --- | --- | --- |
| `E_BOM_MODIFICA_VIETATA` | 387 | Flag di struttura modificato con BoM attiva incompatibile |
| `E_BOM_COMPONENTE_DIVENTA_COMPOSITO` | 1294 | Un componente di una distinta in vigore o futura marcato composito |

Contesto JSON (Check 1): `articolo_id`, `hint` (indica is_composito/requires_serial bloccati).
Contesto JSON (Check 2): `articolo_id`, `hint` (indica is_solo_componente bloccato).

---

## Dipendenze

| Oggetto | Tipo | Motivo |
| --- | --- | --- |
| `catalogo.articoli_componenti` | Tabella | Lookup BoM attive come padre (`prodotto_id`) e come figlio (`componente_id`) |
| `catalogo.articoli_componenti.validita` | Colonna GENERATED | Range temporale calcolato da `valido_dal`/`valido_al`; usato per `@> CURRENT_DATE` |
| `script.fn_log_and_raise_error` | Funzione | Registrazione e raise strutturato dell'errore |

---

## Note operative

- I due check usano colonne diverse (`prodotto_id` vs `componente_id`): un articolo che
  e' contemporaneamente padre e figlio in BoM diverse puo' scatenare entrambi i check
  in sequenza; il primo che trova una BoM attiva interrompe l'esecuzione con raise.
- La condizione `IS DISTINCT FROM` evita che il trigger esegua la query EXISTS quando
  il valore del flag non cambia effettivamente (es. SET is_composito = TRUE su un
  articolo gia' TRUE). Con `UPDATE OF`, il trigger scatta appena il campo e' nel SET,
  non solo quando il valore varia.
- `attivo IS TRUE` (non `= TRUE`) per robustezza su nullable; `validita @> CURRENT_DATE`
  per coerenza con il pattern daterange del progetto (linee-guida-sql §7b).
- Per modificare i flag su un articolo con BoM attive: chiudere prima le righe BoM
  incompatibili (impostare `valido_al < CURRENT_DATE`), poi eseguire il cambio di flag.
- Questo trigger risolve la nota "ottimistica" in
  [`trgfn_articoli_guard_listino_se_composito`](/dbzero/catalogo/manual/trgfn_articoli_guard_listino_se_composito)
  ("TRUE→FALSE gia' bloccato da altri guard se la BoM e' attiva"): il blocco e' ora
  effettivo e DB-enforced.
- Migration di riferimento: `20260522-01`.
