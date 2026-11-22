# Brief DB urgente — fn_log_and_raise_error signature mismatch + guard CASO A bloccato

> **Data**: 2026-05-12
> **Owner BE**: Tid
> **Priorità**: ALTA — blocca smoke utente §3.4 BoM CASO A end-to-end
> **Branch DB**: `dev/db-tid`

---

## Sintomo

Lo smoke utente (bash + curl) tenta di creare un preventivo CASO A:
1. POST articolo composito + POST BoM con `esposto_in_fattura=TRUE` valido oggi → OK
2. POST preventivo DRAFT + POST riga su articolo composito → OK 200
3. Backend invoca `vendite.fn_preventivo_riga_componenti_init(riga_id, sr_id, data)` (post-create_riga in `gestisci_riga`)
4. Init **non popola componenti** (0 inserted), `is_composito_caso_a` resta FALSE

Riproduzione manuale via Django shell (psycopg + cursor):

```sql
SELECT vendite.fn_preventivo_riga_componenti_init(129, <sr_id_emittente>, '2026-05-12');
```

Solleva DataError mascherato.

## Errore esatto (psycopg)

```
DataError: numero di argomenti non sufficiente per format()
CONTEXT:  funzione PL/pgSQL fn_log_and_raise_error(text,text,text,jsonb,uuid,text[]) riga 55 a assegnazione
istruzione SQL "SELECT script.fn_log_and_raise_error(
    'script', TG_NAME, 'E_DOC_COMPONENTE_BOM_NON_VALIDA',
    jsonb_build_object(
        'articolo_componente_id', NEW.articolo_componente_id,
        'validita_bom',           v_bom.validita::text,
        'data_riferimento',       v_data_rif
    ),
    NULL::uuid,
    v_riga_padre_id::text     <<< QUI: TEXT singolo, signature richiede TEXT[]
)"
funzione PL/pgSQL trgfn_componenti_guard_coerenza_bom() riga 103 a PERFORM
```

## Diagnosi a 2 livelli

### Livello A — Bug `fn_log_and_raise_error` (cosmetico, ma maschera tutto)

La signature attuale è `(text, text, text, jsonb, uuid, text[])`. L'ultimo
parametro è un **array** di text. Tutti i caller che ho ispezionato passano
**un singolo text** (`v_riga_padre_id::text`, `NEW.id::text`, ecc.) invece di
`ARRAY[v_riga_padre_id::text]`.

Quando la fn invoca `format(...)` con questi args, conta i placeholder >
elementi disponibili → DataError "*numero di argomenti non sufficiente per
format()*".

**Effetto cascata**: ogni guard che tenta di sollevare un errore di dominio
finisce per generare DataError invece del codice business atteso (es.
`E_DOC_COMPONENTE_BOM_NON_VALIDA`). L'utente/operatore vede un messaggio
opaco di Postgres invece del messaggio parlante.

**Caller affetti** (grep `fn_log_and_raise_error` con argomento finale text
non-array): probabilmente molti — verificare l'intero schema `script`.

### Livello B — Falso positivo (?) guard 5 in `trgfn_componenti_guard_coerenza_bom`

Il guard 5 verifica `v_bom.validita @> v_data_rif`. Per il mio fixture:

```sql
SELECT lower(validita)::text, upper(validita)::text,
       lower_inc(validita), upper_inc(validita),
       validita @> '2026-05-12'::date AS contains_today
  FROM catalogo.articoli_componenti
 WHERE id = '019e1934-19a8-796d-a655-c12da60b122a';
-- Output: ('2026-05-12', 'infinity', True, True, True)
```

Quindi `validita @> '2026-05-12'` è TRUE. Il guard 5 NON dovrebbe sollevare.

Eppure dallo stack del DataError il PERFORM partito è proprio
`E_DOC_COMPONENTE_BOM_NON_VALIDA` (guard 5). 2 ipotesi:

1. **Bug guard 5**: il `v_data_rif` letto via JOIN testata contiene un valore
   diverso da quello atteso (es. coercion, timezone, default).
2. **Bug stack trace**: lo stack mostra l'ULTIMA chiamata `PERFORM` che è
   stata compilata dal trigger, ma la guard che effettivamente solleva è
   un'altra (possibile se il bug A "format insufficient args" capita su
   un'invocazione precedente dentro lo stesso trigger).

Per confermare l'ipotesi 2 serve disabilitare temporaneamente il bug A
oppure fare debug PERFORM-by-PERFORM con `RAISE NOTICE` intermedie.

## Riproduzione minimale

```sql
-- Setup (admin via API REST):
-- 1) POST /catalogo/articoli/ -> articolo composito-smk-test (is_composito=TRUE)
-- 2) POST /catalogo/articoli/{id}/componenti/ -> BoM
--    componente esistente, esposto_in_fattura=TRUE, valido_dal=oggi
-- 3) POST /vendite/preventivi/ -> preventivo DRAFT con emittente+BA
-- 4) POST /vendite/preventivi/{id}/righe/ -> riga su articolo composito

-- Reproduzione bug:
SELECT vendite.fn_preventivo_riga_componenti_init(<riga_id>, <sr_id>, '2026-05-12');
-- Atteso: integer >0 (componenti inseriti)
-- Effettivo: DataError format() insufficient args
```

## Fix proposto

### Bug A (priorità alta, semplice)

Due alternative:

1. **Cambiare signature** di `script.fn_log_and_raise_error` per accettare
   l'ultimo arg come `text` (single) invece di `text[]`. Conserva tutti i
   caller esistenti senza modifiche. Internamente, se serve array, fai
   `ARRAY[arg]` localmente.
2. **Aggiornare tutti i caller** per passare `ARRAY[v_riga_padre_id::text]`
   invece di `v_riga_padre_id::text`. Più invasivo.

Preferisco l'opzione 1 (compat backward, fix puntuale).

### Bug B (da indagare post-fix A)

Una volta fixato A, rilanciare la riproduzione e:
- Se l'init popola componenti → guard 5 era un sintomo del bug A (false alarm)
- Se l'init resta a 0 → indagare cosa il guard 5 vede in `v_data_rif`
  (RAISE NOTICE temporaneo nel trigger per loggare).

## Working tree backend correlato

Sul branch `dev/backend-tid` ho appena committato:
- Fix `gestisci_riga`: usa `preventivo.emittente_fiscale_id` se presente,
  fallback a operatore (risolve un bug separato che bloccava admin globale)
- Nuovo helper `repo.get_emittente_sr_id_by_fiscale_id(fiscale_id)`
- Test BE `test_gestisci_riga_init_componenti_usa_emittente_preventivo`

Il fix BE è autonomo e PASSA i test unit. Il bug DB blocca l'integration
test end-to-end via API (smoke §3.4).

## Aperto in attesa fix DB

- Smoke bash `backend/scripts/tests/smoke-test-preventivi-componenti.sh`
  resta sospeso a step 6/7 (fail su is_composito_caso_a + componenti vuoti)
- Smoke utente UI §3.4 a/b/c rimandato (esibirà gli stessi sintomi)
- Working tree fixture residue: vari articoli `composito-smk-<EPOCH>` +
  preventivi `PRV0000049/50/51`. Cleanup manuale o riutilizzabili per
  retry post-fix.

## Riferimenti

- Smoke script: `backend/scripts/tests/smoke-test-preventivi-componenti.sh`
- Service BE: `backend/apps/vendite/services/preventivi_service.py:691`
- Repo BE: `backend/apps/vendite/db/preventivi_repository.py:651`
- Brief componenti originale:
  `docs/it/dev/work-in-progress/brief-db-preventivi-righe-componenti-override.md`
- Refactor componenti: `docs/it/dev/work-in-progress/refactor-componenti.md`
- Memoria: `feedback_audit_db_preventivo_smoke` (audit DB pre-smoke)
