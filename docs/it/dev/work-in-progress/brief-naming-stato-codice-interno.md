# Brief — Convenzione naming `codice_interno` vs `codice` + bonifica mislabel `stato_codice`

> **Tipo**: brief di convenzione + bonifica (DB → team DB; BE/FE → backend agent). · **Priorità**: 🟡 media (debito di modello, rischio latente). · **Data**: 2026-06-28.
> **Origine**: emerso scrivendo lo smoke contratto (`a-test-push-commesse-fatturazione.md §3b`): il contratto espone lo stato come `stato_codice`, mentre preventivi/ordini/commesse usano `stato_codice_interno`. Indagando si è visto che il **valore** di `stato_codice` sui contratti è in realtà `codice_interno` (alias fuorviante).

---

## 1. Il principio (deciso con Tid)

Le tabelle `config.stati_*` (e simili) hanno **due** colonne con ruoli **opposti**:

| Colonna | Natura | Uso |
| --- | --- | --- |
| **`codice_interno`** | **immutabile** (lockata da `script.trgfn_lock_columns`) | **riferimento interno di sistema**: confronti, filtri, state-machine, mapping, seed. È il valore stabile su cui poggia la logica. |
| **`codice`** | **modificabile** dall'utente | **etichetta a video**. Es.: oggi `DRAFT`, domani l'utente può rinominarlo `BOZZA`; la logica non se ne deve accorgere. |

**Regola d'oro**: la **logica usa SEMPRE `codice_interno`**; il `codice` è solo display
(spesso si mostra invece la `descrizione`). I valori `DRAFT`/`ATTIVO`/`CESSATO` sono
`codice_interno`.

## 2. Cos'era l'equivoco

Diverse viste/fn fanno:

```sql
sd.codice_interno AS stato_codice      -- espone l'IMMUTABILE, ma lo CHIAMA come il MUTABILE
```

Il **valore** non è trasformato (resta `DRAFT`): è il **nome** a mentire. Un campo che
dentro ha `codice_interno` si chiama `stato_codice` (sembra il `codice` modificabile).

**Rischio latente**: il FE fa `stato_codice === 'DRAFT'` e funziona *per caso*. Se un
domani qualcuno "corregge" la vista in `sd.codice AS stato_codice` (coerente col nome) e
poi l'utente rinomina il codice in `BOZZA`, **tutta la logica si rompe in silenzio**.

## 3. Convenzione per non avere più equivoci

**L'alias deve rispecchiare la colonna sorgente, 1:1:**

- `codice_interno` → si espone **sempre** come `*_codice_interno` (e la logica usa SOLO questo);
- `codice` → si espone come `*_codice` (e si usa SOLO per display);
- **VIETATO** `codice_interno AS *_codice` (e il simmetrico `codice AS *_codice_interno`).

Se servono entrambi (come fanno già preventivi/ordini), si espongono **entrambi con nome
fedele**: `sd.codice_interno AS stato_codice_interno`, `sd.codice AS stato_codice`.

### Guardrail (per renderla non aggirabile)

Aggiungere un check in CI (grep/test) che **fallisce** su pattern mislabel:

```bash
# Mislabel: codice_interno aliasato a un nome che NON finisce in _codice_interno
grep -rEn "codice_interno[[:space:]]+AS[[:space:]]+[a-z_]*codice\b" db/ \
  | grep -vE "AS[[:space:]]+[a-z_]*codice_interno\b" && exit 1
# Simmetrico: codice (non _interno) aliasato a *_codice_interno
grep -rEn "[^_]codice[[:space:]]+AS[[:space:]]+[a-z_]*codice_interno\b" db/ && exit 1
```

(da affinare su falsi positivi; vive accanto agli altri check DDL).

## 4. Inventario mislabel `codice_interno AS stato_codice` (da bonificare)

### DB (brief al team DB)

**Azione per ogni oggetto**: l'alias `codice_interno AS stato_codice` → `codice_interno AS
stato_codice_interno` (logica) **e** aggiungere `codice AS stato_codice` (display fedele) —
così sia la logica sia il video hanno il campo col nome giusto, nessun equivoco (decisione
Tid: «display codice senza equivoci»). Pattern identico a `vw_preventivi_*`/`vw_ordini_*`.

| Dominio | Oggetto | Nota |
| --- | --- | --- |
| vendite/contratti | `vw_contratti_lista` (`sd.codice_interno AS stato_codice`) | lista contratti |
| vendite/contratti | `script.fn_available_actions_contratto` (jsonb `'stato_codice' → v_stato_cod`) | capability detail — esporre `stato_codice_interno` (+ `stato_codice`=`codice` se utile) |
| anagrafiche | `vw_clienti_lista` (`sc.codice_interno AS stato_codice`) | |
| anagrafiche | `vw_clienti_codice_ba` (`sc.codice_interno AS stato_codice`) | |
| anagrafiche | `vw_fornitori_dettaglio` (`sf.codice_interno AS stato_codice`) | |
| pratiche | `fn_coda_lavoro_operatore` (`sf.codice_interno AS stato_codice`, stato **flusso**) | coda lavoro |

**OK (non toccare)**: `vw_preventivi_pratiche` fa `sp.codice AS stato_codice` — qui
`stato_codice` è *davvero* `codice` (nome fedele). I domini preventivi/ordini/offerte/commesse
espongono già `stato_codice_interno` corretto.

### BE (dopo il rename DB; backend agent)

- **contratti**: `contratti_repository.py` (col_map `"stato_codice"→"v.stato_codice"`, SQL
  capability `sd.codice_interno AS stato_codice`, `get_stato_codice`), `types.py`
  (dataclass capability/list/detail contratti), `api/views_contratti.py` (serializer field
  `stato_codice`, help-text colonne).
- **anagrafiche**: repo/serializer clienti+fornitori (campo `stato_codice`).
- **pratiche**: consumer di `fn_coda_lavoro_operatore` (campo `stato_codice` della coda).

### FE (dopo il rename DB; backend agent)

- **contratti**: `ContrattiSearchTable.vue`, `ContrattiListView.vue`, `ContrattoDrawer.vue`,
  `ContrattiBillingAccountDrawer.vue` (confronti `'DRAFT'/'ATTIVO'/'CESSATO'`,
  `statoContrattoSeverity(...)`, prop `:stato-codice`).
- **anagrafiche**: `ClientiView.vue`, `ClienteDrawer.vue`, `FornitoreDrawer.vue`,
  `FornitoriSearchTable.vue`.
- Display invariato: i Tag mostrano già `stato_descrizione`.

## 5. Nota correlata (secondaria) — filtri lista

I repo preventivi/ordini hanno un **parametro filtro** `stato_codice` che «arriva dal FE
come `codice_interno`» (commenti in `preventivi_repository.py:122`, `ordini_repository.py:94`).
Stesso smell sul nome (parametro `stato_codice` che porta `codice_interno`). Rinominarlo è
un cambio di contratto API lato FE: **fuori da questo giro**, da valutare a parte per non
mischiare output-fields e query-params.

## 6. Piano a fasi

1. **Doc convenzione** in `linee-guida-sql.md` (regola §3) + guardrail in CI. *(non DB-dipendente, si può fare subito)*
2. **DB** (team): rename dei 6 alias (§4) → `stato_codice_interno`. Per dominio, così è
   verificabile/atterrabile a fasi.
3. **BE+FE** (backend agent, **dopo** il rename DB del rispettivo dominio): aggiornare
   consumer (§4). Sequenza consigliata: contratti → anagrafiche → pratiche.
4. **Verifica**: smoke contratto `§3b` riprende usando `stato_codice_interno`; build FE +
   test BE verdi; guardrail CI verde.

## 7. Decisioni (Tid, 2026-06-28)

- **Scope**: ✅ **sweep COMPLETO** — contratti + anagrafiche + pratiche. Eseguibile a fasi
  (ordine consigliato §6), ma tutti i 6 oggetti vanno bonificati.
- **Display `codice`**: ✅ **esporre entrambi con nome fedele** — `codice_interno AS
  stato_codice_interno` (logica) **e** `codice AS stato_codice` (display). Nessun equivoco
  né lato logica né lato video.
- **Convenzione**: ✅ documentata in `linee-guida-sql.md §6c` (alias fedele) + guardrail CI.

---

*Brief naming `codice_interno`/`codice` — ZeroERP 2026-06-28. DB = brief al team; BE/FE = backend agent dopo il rename DB.*
