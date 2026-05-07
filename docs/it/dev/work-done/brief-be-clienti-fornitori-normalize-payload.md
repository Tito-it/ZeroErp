# Brief BE/FE — LANDED `clienti.tipo_gg_scadenza_ft` / `nr_giorni_scadenza` normalize+guard (Fase 2 refactor anagrafiche)

> **Stato**: LANDED 2026-04-27
> **Branch BE/FE**: `dev/backend-tid`
> **Branch DB**: `dev/db-tid` (landed in parallelo lo stesso giorno)
> **Origine**: brief DB del 2026-04-27 in risposta alle 6 domande sulla
> Fase 2 dell'analisi `analisi-refactor.frontend-anagrafiche.md`
> **Pattern**: normalize+guard simmetrico (terza occorrenza dopo
> `trgfn_fornitori_guard_normalize` e ora `trgfn_clienti_normalize_giorni_scadenza`)

## 1. Cosa ha fatto il DB (recap)

Package atomico in 5 componenti su `dev/db-tid`:

1. **Backfill** record incoerenti — `UPDATE … SET nr_giorni_scadenza=NULL WHERE tipo NOT IN ('G','F')`
2. **DROP DEFAULT** su `nr_giorni_scadenza` (era `0`, misleading; default implicito ora NULL)
3. **CHECK constraint** `chk_clienti_tipo_gg_scadenza_ft` su `IN ('G','M','F','N')`
4. **Function** `anagrafiche.trgfn_clienti_normalize_giorni_scadenza()` asimmetrica:
   - normalize silenzioso quando tipo NOT IN ('G','F') → `nr_giorni := NULL`
   - raise fail-fast `E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI` quando tipo IN ('G','F') AND `nr_giorni IS NULL OR <= 0`
5. **Trigger** `trg_clienti_normalize_giorni_scadenza_ins_upd BEFORE INSERT OR UPDATE OF tipo_gg_scadenza_ft, nr_giorni_scadenza`

Seed errori in `config.messaggi_errore.csv` (id 397 + 398 fix opportunistico per fornitori).
pgTAP `test-clienti-normalize-giorni-scadenza-v1.sql` plan(10) verde.

**Fornitori**: nessuna nuova migration. La regola `ritenuta_acconto=false → aliquota=NULL` era gia' applicata dal trigger esistente `trgfn_fornitori_guard_normalize` (clausola 4) — confermato in fase di analisi critica del brief originario.

## 2. Cosa ha fatto il BE (questo brief)

### 2.1 Mapping policy errori

[`apps/core/services/error_policies.py`](../../../backend/apps/core/services/error_policies.py) — aggiunte 2 policy nella sezione "Clienti / Fornitori — normalize+guard payload pagamento/fiscali":

```python
"E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI": ErrorPolicy(
    http_status=400,
    ui_action="highlight_form_fields",
    user_message="Numero giorni scadenza obbligatorio quando il tipo "
                 "calcolo scadenza e' G (somma giorni) o F (fine mese + somma).",
),
"E_FORNITORI_RITENUTA_ALIQUOTA_OBBLIGATORIA": ErrorPolicy(
    http_status=400,
    ui_action="highlight_form_fields",
    user_message="Aliquota ritenuta obbligatoria (> 0) quando ritenuta "
                 "d'acconto e' attiva.",
),
```

Il trigger DB raise via `script.fn_log_and_raise_error` include il codice nel messaggio: il pattern esistente `ErrorTranslator._extract_app_error_code()` lo intercetta e applica automaticamente la policy registrata. Nessun catch IntegrityError custom necessario nei service.

### 2.2 Verifica payload INSERT cliente

[`apps/anagrafiche/db/clienti_repository.py`](../../../backend/apps/anagrafiche/db/clienti_repository.py) gia' usa colonne opzionali con `if val is not None: cols.append(col)`. Quindi:

- payload senza `nr_giorni_scadenza` → la colonna non e' inclusa nell'INSERT → DB applica default (ora NULL post DROP DEFAULT).
- payload `tipo='G'` senza `nr_giorni_scadenza` → INSERT con tipo='G' e default NULL → trigger solleva `E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI` ✅
- payload `tipo='N', nr_giorni=30` → trigger normalizza silenziosamente a `('N', NULL)` ✅

Nessuna modifica ai service necessaria.

### 2.3 CHECK constraint dominio

Il dropdown UI [ClienteDrawer.vue:59-64](../../../frontend/src/anagrafiche/components/ClienteDrawer.vue#L59-L64) chiude gia' i valori a `N/G/M/F`. Il CHECK e' defense-in-depth contro abuso API. Caso edge gestito implicitamente: cade su `E_DATABASE` (500 tecnico) — accettabile perche' irragiungibile via UI.

## 3. Cosa ha fatto il FE (questo brief)

### 3.1 Rimozione pre-clean payload

[`ClienteDrawer.vue:286`](../../../frontend/src/anagrafiche/components/ClienteDrawer.vue#L286):

```diff
- nr_giorni_scadenza: ['G', 'F'].includes(f.tipo_gg_scadenza_ft) ? (f.nr_giorni_scadenza || 0) : null,
+ nr_giorni_scadenza: f.nr_giorni_scadenza,
```

[`FornitoreDrawer.vue:135`](../../../frontend/src/anagrafiche/components/FornitoreDrawer.vue#L135):

```diff
- ritenuta_aliquota: f.ritenuta_acconto ? f.ritenuta_aliquota : null,
+ ritenuta_aliquota: f.ritenuta_aliquota,
```

Il trigger DB normalizza lato server. Niente piu' regola di dominio replicata in JS.

## 4. Test eseguiti (BE)

```
./manage-test.sh apps.anagrafiche.tests apps.core.tests -v 1
Ran 810 tests in 1.607s — OK
```

## 5. Smoke test consigliato (UI, manuale)

- Crea cliente con `tipo='G'`, `nr_giorni=30` → ok
- Cambia modalita' a `'N'` lasciando `nr_giorni=30` nel form → save ok, response mostra `nr_giorni: null`
- Cambia modalita' a `'G'` e azzera `nr_giorni` → 400 `E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI`, highlight campo
- Crea fornitore con `ritenuta_acconto=true`, `aliquota=20` → ok
- Disattiva `ritenuta_acconto` lasciando `aliquota=20` → save ok, response mostra `aliquota: null`

## 6. Pattern emerso (terza occorrenza)

Il pattern **normalize+guard simmetrico** ora ha tre occorrenze nella codebase:

| Trigger | Tabella | Coppia campi | Normalize | Guard fail-fast |
|---|---|---|---|---|
| `trgfn_fornitori_guard_normalize` | `anagrafiche.fornitori` | `(ritenuta_acconto, ritenuta_aliquota)` | acconto=false → aliquota=NULL | acconto=true AND aliquota IS NULL/<=0 → raise |
| `trgfn_clienti_normalize_giorni_scadenza` | `anagrafiche.clienti` | `(tipo_gg_scadenza_ft, nr_giorni_scadenza)` | tipo NOT IN ('G','F') → giorni=NULL | tipo IN ('G','F') AND giorni IS NULL/<=0 → raise |

Pattern riusabile per qualunque coppia `(flag/tipo, value)` dove il `value` e' significativo solo per certi `flag/tipo`. Il trigger fa BEFORE INSERT OR UPDATE OF (campi specifici), il backend espone codice errore via policy registry, il frontend rimuove pre-clean.

## 7. Riferimenti

- [analisi-refactor.frontend-anagrafiche.md](analisi-refactor.frontend-anagrafiche.md) — Fase 2 sezione del piano refactor (ora marcata LANDED)
- DB doc concettuale: `docs/it/dbzero/anagrafiche/manual/trgfn_clienti_normalize_giorni_scadenza.md`
- Pattern gemello fornitori: `docs/it/dbzero/anagrafiche/funzioni/trgfn_fornitori_guard_normalize.md`
- Tabella: [`anagrafiche.clienti`](../../dbzero/anagrafiche/tabelle/clienti.md)
