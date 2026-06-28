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

## 4. Inventario mislabel — sweep a ondate

> ⚠️ **Aggiornamento 2026-06-28 (verifica sul DB live).** Il mislabel è **sistemico**:
> non solo `stato_codice` e non solo i 6 oggetti qui sotto. La scansione delle
> definizioni live ha trovato lo stesso pattern `codice_interno AS *_codice` su molte
> viste indirizzi/istanze/pdp e su funzioni search-detail, con **4 chiavi** diverse:
> `stato_codice`, `tipo_indirizzo_codice`, `stato_pdp_codice`, `utility_codice`.
> **Decisione Tid: opzione A — sweep COMPLETO**, eseguito a **ondate**, con guardrail
> CI **bloccante** attivato *dopo* l'ultima ondata (catalog-based, vedi §6). Ondate
> 2/3 elencate in fondo a questo §4.

### Ondata 1 — contratti + anagrafiche (liste) + pratiche (coda) — ✅ changeset scritti `20260628-02..07`

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

### Ondata 2 — viste indirizzi / istanze (🟡 scope ridotto dopo verifica LIVE)

> **Verifica sullo stato LIVE (doc autogen)**: la maggior parte dei mislabel storici
> erano già stati superati. Live restano **solo 2 viste-sorgente** col pattern
> `codice_interno AS *_codice`; le altre viste indirizzi (`resolved_ruolo/soggetto/all`)
> sono pulite (passano solo attraverso le colonne). Tutte e 3 le tabelle stato/lookup
> (`tipi_indirizzi`, `stati_pdp`, `utilities`) hanno **sia `codice` sia `codice_interno`**.

| Vista-sorgente (mislabel reale) | Chiavi | Catena consumer (passano attraverso la colonna) |
| --- | --- | --- |
| `vw_indirizzi_resolved_base` | `tipo_indirizzo_codice` | `vw_indirizzi_resolved_all/_ruolo/_soggetto`, `fn_get_indirizzi_by_ruolo/_soggetto` |
| `vw_istanze_utilities_dettaglio` | `stato_pdp_codice`, `utility_codice` | `vw_istanze_dati_precontrattuali_dettaglio` |

**Strategia (no DROP, no cascade)**: sulla vista-sorgente `CREATE OR REPLACE` cambiando
l'espressione di `*_codice` → `codice` (display) e **appendendo in coda** `*_codice_interno`
= `codice_interno`. I consumer non si rompono (continuano a leggere `*_codice`, ora display)
e il guardrail diventa verde sull'intera catena (solo la sorgente aveva l'alias letterale).
La cascata "espone anche `*_codice_interno` a valle" (per la logica FE downstream) è un
completamento successivo, non bloccante. Le catene sono ricreate insieme nei changeset
`20260402-04` (indirizzi-resolved) e `20260402-09` (istanze) — usare quelli come sorgente
SQL leggibile, non il blob normalizzato dell'autogen.

### Ondata 3 — funzioni search-detail (🔴 DA FARE)

| Dominio | Oggetto | Chiavi mislabel (jsonb) |
| --- | --- | --- |
| script | `fn_get_search_detail` (+ variante `_emittente`) | `'stato_codice' => sc.codice_interno`, `'utility_codice' => u.codice_interno` |

Builder statici (CASE per tipo_ruolo): leggono `config.*` direttamente, non le viste
Ondata 1, quindi non si rompono — ma il mislabel jsonb va corretto come gli altri.

### ⛔ Esclusi dallo sweep (generici, già conformi / alias-free) — NON toccare

- **`dbops.fn_get_lookup_codici`** (lookup generico tabelle `config.*`): firma
  `RETURNS TABLE(id, codice, codice_interno, descrizione, attivo)` — espone **già**
  entrambi i campi fedeli; mapping dinamico `colonna_reale AS codice` / `AS codice_interno`,
  **mai** `codice_interno AS codice`. Il guardrail non la intercetta.
- **`script.fn_get_entita_ruolo_detail`** (detail dinamico su `entita_tabella`): usa
  `to_jsonb(e.*)` — nessun alias, si adatta ai rename, nessun mislabel.

> Il guardrail catalog-based deve restare verde su questi due: lo è per costruzione
> (nessuna stringa letterale `codice_interno AS *_codice`).

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

## 6. Piano (opzione A — sweep completo, a ondate)

**Principio**: ZeroERP non è in produzione → rename diretto (`*_codice_interno` logica +
`*_codice` display), rotture temporanee dei consumer accettate, conta lo stato finale.
Per ogni vista con rename di colonna: `DROP VIEW + CREATE`. Per le funzioni `RETURNS
TABLE`: `DROP FUNCTION + CREATE`. Per jsonb/scalari: `CREATE OR REPLACE`. Funzioni con
**`%TYPE`** in firma/DECLARE/RETURNS TABLE.

0. **Doc convenzione** `linee-guida-sql.md §6c` — ✅ FATTA (Fase 0).
1. **Ondata 1 DB** — contratti + anagrafiche (liste) + pratiche (coda): 6 changeset
   `20260628-02..07` — ✅ scritti (non applicati/committati). Sblocca lo smoke contratto §3b.
2. **Ondata 2 DB** — viste indirizzi/istanze/pdp (§4). 🔴 DA FARE.
3. **Ondata 3 DB** — funzioni search-detail (§4). 🔴 DA FARE.
4. **BE+FE per ogni ondata** (backend agent, **dopo** il DB della rispettiva ondata):
   migrare i consumer alla logica su `*_codice_interno`; display resta `*_descrizione`.
   Include il `campo_sorgente` dei seed `ui.lista_colonna` usato per la *severity*
   (oggi `stato_codice` → deve puntare a `stato_codice_interno`).
5. **Guardrail CI bloccante** — **catalog-based** (scansiona `pg_views` + `pg_proc`
   delle definizioni **live**, non i changelog storici): fallisce se trova
   `codice_interno AS *_codice` (non `_codice_interno`) o la chiave jsonb speculare.
   **Attivato come bloccante SOLO dopo l'ultima ondata** (finché lo sweep è in corso
   resta in `WARN`/report, per non far rosso ogni PR). Deve restare verde sui due
   generici esclusi (§4).
6. **Verifica finale**: smoke contratto §3b su `stato_codice_interno`; build FE + test
   BE verdi; pgTAP DB verdi; guardrail CI verde su tutto il catalogo.

## 7. Decisioni (Tid, 2026-06-28)

- **Scope**: ✅ **opzione A — sweep COMPLETO** di *tutti* gli oggetti con mislabel
  `codice_interno AS *_codice` (non solo i 6 iniziali: anche indirizzi/istanze/pdp e
  search-detail — vedi §4 ondate 2/3). Eseguito a **ondate**.
- **Display `codice`**: ✅ **esporre entrambi con nome fedele** — `codice_interno AS
  *_codice_interno` (logica) **e** `codice AS *_codice` (display). Nessun equivoco.
- **Generici**: ✅ **`fn_get_lookup_codici` e `fn_get_entita_ruolo_detail` ESCLUSI** —
  già conformi / alias-free, non si toccano (§4).
- **Guardrail**: ✅ **catalog-based**, bloccante **dopo** l'ultima ondata (WARN durante).
- **Convenzione**: ✅ documentata in `linee-guida-sql.md §6c`.

## 7-bis. Registro mislabel collaterali (alias ≠ contenuto) — emersi durante il sweep

> Bug di naming **diversi** da `codice_interno`/`codice` (es. una colonna esposta con un
> nome che non riflette il contenuto). Tracciati qui man mano che emergono; correzione da
> valutare caso per caso (fuori dallo scope stretto del brief).

| Oggetto | Mislabel | Stato | Note |
| --- | --- | --- | --- |
| `vw_istanze_utilities_dettaglio` | `sp.codice AS stato_pdp_descrizione` (esponeva **codice** col nome **descrizione**) | ✅ corretto in `20260628-08` (`sp.descrizione AS stato_pdp_descrizione`) · 📣 **da segnalare al BE** | ⚠ cambio comportamento: `stato_pdp_descrizione` ora restituisce la **descrizione** (prima il codice). Consumer `precontrattuali_dettaglio` (passthrough) → chi mostrava quel campo vedeva il codice. |

Scansione famiglia codice↔descrizione sul LIVE: **1 solo caso** (sopra). `descrizione AS *_codice`
e `codice_interno AS *_descrizione`: **zero**.

| Oggetto | Mislabel | Stato | Note |
| --- | --- | --- | --- |
| `dbops.vw_diag_v_clienti_links` | `tr.codice AS tipo_ruolo_codice_interno` (**tipo B** speculare: mutabile col nome dell'immutabile) | ✅ corretto in `20260628-11` (`tr.codice_interno AS tipo_ruolo_codice_interno`) | Straggler trovato dal **guardrail** (l'autogen non lo mostrava). Vista diagnostica dbops, nessun dipendente. È l'**unico** straggler del DB. |

## 8. Stato (2026-06-28)

- **Ondata 1 — DB**: ✅ **APPLICATA** — changeset `20260628-02..07` (4 viste + 2 funzioni),
  YAML validi, **Liquibase update OK**. Fix in corsa: nella coda (`-07`) la CTE
  `stati_pendenti` proiettava solo `id, codice_interno`; aggiunto `codice` (serviva per
  `sf.codice AS stato_codice`). Nessun consumer DB a valle rotto. Commit/autogen a carico di Tid.
- **Ondata 2 — DB** (viste indirizzi/istanze): ✅ **changeset scritti**.
  - ✅ `vw_istanze_utilities_dettaglio` — changeset `20260628-08` (append, no cascade) +
    fix collaterale `stato_pdp_descrizione` (§7-bis). `vw_pdp` era già corretta.
  - 🟡 `vw_indirizzi_resolved_base` — changeset `20260628-09` (solo base, CREATE OR
    REPLACE). **Confermato in apply**: `tipi_indirizzi.codice_interno`=`varchar(10)`,
    `codice`=`varchar(15)` → type-change vietato. Soluzione **zero-cascade**: cast
    `ti.codice::varchar(10)` → colonna resta `varchar(10)`, niente DROP/cascade sull'hub
    (3 viste `SELECT *` + ~5 funzioni `RETURNS SETOF resolved_*`). ⚠ verificare
    `max(length(codice))<=10` su tipi_indirizzi (atteso sì; altrimenti troncamento display
    → full-chain DROP+CREATE).
  - 📣 **Follow-up (non bloccante)**: i `SELECT *` restano congelati → non espongono
    ancora `tipo_indirizzo_codice_interno` a valle. Cascata di completamento separata.

> ⚠️ **Lezione (2026-06-28)**: l'approccio "append via `CREATE OR REPLACE`" **non è
> affidabile** — `codice` e `codice_interno` hanno spesso lunghezze varchar diverse
> (es. stati_pdp 16 vs 64), e `CREATE OR REPLACE VIEW` **non può cambiare il tipo** di
> una colonna. Regola: per togliere il mislabel usare **sempre `DROP+CREATE`** (come
> Ondata 1), gestendo la cascata dei dipendenti.
- **Ondata 3 — DB** (`fn_get_search_detail`): ✅ changeset `20260628-10` (CREATE OR REPLACE
  jsonb, niente cascade) — branch `CL`:
  - `'utility_codice' => u.codice_interno` → `'utility_codice_interno' => u.codice_interno`
    **+** `'utility_codice' => u.codice` (utilities ha entrambi); `ORDER BY` su
    `utility_codice_interno` per preservare l'ordinamento attuale.
  - `'stato_codice' => sc.codice_interno` → **solo rename** `'stato_codice_interno'`.
    ⚠ **Nuance (registro §7-bis)**: `stati_cliente.codice` NON è il display del codice —
    è già esposto come `'stato_macro'` (raggruppamento, default `'IS'`). Quindi niente
    `'stato_codice' => sc.codice` (sarebbe un duplicato semanticamente errato); il display
    dello stato è `stato_descrizione`. Branch `FO`: pulito, non si tocca.
  - Richiede riproduzione dell'intera funzione (~200 righe, CASE per tipo_ruolo) — da fare
    con cura/apply-test, meglio fresco.
- **Straggler**: ✅ `dbops.vw_diag_v_clienti_links` (tipo B) — changeset `20260628-11`.
- **Guardrail CI**: ✅ `scripts/sql/check_naming_stato_codice.sql` (catalog-based) +
  step **bloccante** in `.github/workflows/ci-validate.yaml` (dopo `liquibase update`).
  Eseguito sul DB live: **OK, nessun mislabel**.
- **DB sweep**: ✅ **COMPLETO** (changeset `20260628-02..11`, applicati).
- **BE/FE**: 🔴 handoff (vedi §9).

---

## 9. Handoff BE/FE — modifiche DB applicate (riepilogo per consumer)

> **Principio**: per la **logica** (confronti stato, severity, state-machine) usare
> **sempre** il campo `*_codice_interno`. Per il **display** usare `*_descrizione`
> (preferito) o `*_codice` (ora porta il `codice` **mutabile**). I campi `*_codice`
> esistenti hanno **cambiato semantica**: prima portavano `codice_interno`, ora portano
> `codice`. Dove servono per logica → migrare a `*_codice_interno`.

**Legenda**: ⚠️ = il BE/FE che leggeva quel campo per LOGICA deve migrare; il valore
oggi coincide (codice == codice_interno finché l'utente non rinomina il `codice`), ma è
una bomba a orologeria.

| Oggetto | Campo PRIMA (= codice_interno) | DOPO | Azione BE/FE |
| --- | --- | --- | --- |
| `vw_contratti_lista` | `stato_codice` | `stato_codice`=codice (display) **+** `stato_codice_interno` | ⚠️ logica/severity → `stato_codice_interno` |
| `vw_clienti_lista` | `stato_codice` | idem | ⚠️ idem |
| `vw_clienti_codice_ba` | `stato_codice` | idem | ⚠️ idem |
| `vw_fornitori_dettaglio` | `stato_codice` | idem | ⚠️ idem |
| `fn_available_actions_contratto` (jsonb) | `stato_codice` | `stato_codice`=codice **+** `stato_codice_interno` | ⚠️ capability detail → `stato_codice_interno` |
| `fn_coda_lavoro_operatore` (RETURNS TABLE) | `stato_flusso_codice` | `stato_flusso_codice`=codice **+** `stato_flusso_codice_interno` | ⚠️ coda lavoro → `stato_flusso_codice_interno` |
| `vw_istanze_utilities_dettaglio` | `stato_pdp_codice`, `utility_codice` | `*_codice`=codice **+** `stato_pdp_codice_interno`, `utility_codice_interno` | ⚠️ logica → `*_codice_interno` |
| `vw_istanze_dati_precontrattuali_dettaglio` | `stato_pdp_codice`, `utility_codice` (passthrough) | idem (+ `*_codice_interno` propagati) | ⚠️ idem |
| `fn_get_search_detail` (jsonb, branch CL) | `utility_codice`; **`stato_codice`** | `utility_codice`=codice **+** `utility_codice_interno`; **`stato_codice` RINOMINATO → `stato_codice_interno`** | 🔴 **BREAKING**: chiave `stato_codice` **non esiste più** → usare `stato_codice_interno`. `utility_codice`→logica usa `utility_codice_interno`. `stato_macro` invariato |
| `vw_indirizzi_resolved_base` | `tipo_indirizzo_codice` | `tipo_indirizzo_codice`=codice (display, **troncato a 10**) **+** `tipo_indirizzo_codice_interno` | ⚠️ logica → `tipo_indirizzo_codice_interno`. NB: i consumer `resolved_ruolo/soggetto/all` (SELECT *) **non espongono ancora** `*_codice_interno` (follow-up §sotto) |

**Cambi di comportamento NON-naming (segnalati):**

- `vw_istanze_utilities_dettaglio.stato_pdp_descrizione` (e passthrough in
  `precontrattuali`): **ora restituisce la descrizione vera** (`stati_pdp.descrizione`);
  prima restituiva erroneamente il `codice`. Chi mostrava quel campo vedrà la descrizione.
- `dbops.vw_diag_v_clienti_links.tipo_ruolo_codice_interno`: ora = `tr.codice_interno`
  (prima `tr.codice`). Vista diagnostica, impatto BE atteso nullo.

**Follow-up DB non bloccanti (per completare la simmetria a valle):**

- Cascata `tipo_indirizzo_codice_interno` sui `SELECT *` `vw_indirizzi_resolved_ruolo/
  soggetto/all` (e nelle fn `fn_get_indirizzi_by_*`): oggi espongono solo
  `tipo_indirizzo_codice` (display). Richiede full-chain DROP+CREATE (hub con `RETURNS
  SETOF`) — vedi §8.
- `fn_get_indirizzi_by_ruolo` (RETURNS TABLE esplicito): per esporre
  `tipo_indirizzo_codice_interno` serve un suo update dedicato.

---

*Brief naming `codice_interno`/`codice` — ZeroERP 2026-06-28. DB sweep COMPLETO
(`20260628-02..11`) + guardrail CI attivo. §9 = handoff BE/FE.*
