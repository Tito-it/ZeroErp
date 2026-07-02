# Brief DB — Proiezione stato di dominio: normalizzazione + resolver

> **Tipo**: brief DB (DDL + seed + funzioni/viste) · **Destinatario**: team DB (`dev/db-tid`)
> **Priorità**: 🟠 media-alta (abilita V1 "vista-racconto" e salda il debito GUIDA)
> **Data**: 2026-07-01 · **Stato**: ✅ **CHIUSO 2026-07-02** (spostato in `work-done/`):
> attività DB dell'increment PREVENTIVI (D1-D3 + codici errore + pgTAP + doc) consegnate
> e mergiate dal team DB. I residui NON-DB (fase MOSTRA BE/FE, roll-out
> offerte/ordini/contratti, D4 GUIDA fase 2) restano tracciati nel brief di design
> [brief-design-proiezione-stato-dominio.md](../work-in-progress/brief-design-proiezione-stato-dominio.md),
> che resta aperto in `work-in-progress/`.
>
> **Origine / autorevole**: [brief-design-proiezione-stato-dominio.md](../work-in-progress/brief-design-proiezione-stato-dominio.md)
> (voce **V10**). Qui si estraggono le **sole attività DB** (D1-D4). Modello, principio e
> vincoli sono nel brief di design: leggerlo prima.

## Stato avanzamento (increment PREVENTIVI)

| Attività | Stato |
|---|---|
| D1 — `is_verdetto` su `esiti_flussi_pratiche` (`20260701-13`) | ✅ applicato |
| D1 — `fase`/`esito`/`terminale` + CHECK + FK su `stati_doc_preventivi` (`20260701-14`, seed `-19`) | ✅ applicato |
| D1 — guard generico `trgfn_stati_doc_guard_esito_verdetto` (`20260701-15`) | ✅ applicato |
| D2 — resolver `vendite.vw_stato_sorgente_preventivo` (`20260701-16`) | ✅ applicato |
| D3 — union `script.vw_stato_sorgente` (`20260701-17`) | ✅ applicato |
| D3 — wrapper `pratiche.fn_stato_sorgente` (`20260701-18`) | ✅ applicato |
| Codici errore 502/503 (`20260701-20`) | ✅ applicato |
| pgTAP `test-proiezione-stato-sorgente.sql` (17 test) | ✅ verde |
| Doc auto-gen dbzero (rigenerata da `gen_db_docs.py`) | ✅ |
| Doc manuale: `fn_stato_sorgente`, `vw_stato_sorgente`, `vw_stato_sorgente_preventivo` + update `stati_doc_preventivi`/`esiti_flussi_pratiche` | ✅ |
| **BE** — descrittore nei payload pratica/percorso/coda (fase MOSTRA) | ✅ 2026-07-02 (display fields `doc_*`, frammento `_doc_sorgente_lateral` su `script.vw_stato_sorgente`; doc in `api_percorso.md`) |
| **FE** — vista-racconto V1 | ✅ 2026-07-02 (Tag stato-documento su ADESSO e FATTI-vivi, BB `faseSorgenteSeverity`) |
| Roll-out offerte/ordini/contratti (stesso playbook, guard già generico) | ⬜ dopo validazione — tracciato nel [brief design](../work-in-progress/brief-design-proiezione-stato-dominio.md) |
| **D4** — GUIDA "avanza-su-esito-proiettato" (idempotente) | ⬜ fase 2 — tracciato nel [brief design](../work-in-progress/brief-design-proiezione-stato-dominio.md) |

---

## 0. Decisioni accettate (analisi critica 2026-07-01)

Analisi critica sul DB reale (doc auto-gen + seed CSV) → 5 decisioni confermate da Tid,
che **modificano** i deliverable rispetto alla prima stesura:

| # | Decisione | Effetto sul deliverable |
|---|---|---|
| **A** | **Una sola superficie di dispatch: la vista UNION.** Il trittico `resolver_key` + CASE statico + UNION della prima stesura era una tripla sorgente di verità da tenere allineata a mano. La vista UNION *è* il registro dei resolver (ogni ramo aggancia il proprio `sorgente_tipo_id` via `config.sorgenti.codice_interno`); `fn_stato_sorgente` diventa un **wrapper scalare** sulla vista con fallback `UNKNOWN`. | **Niente colonna `config.sorgenti.resolver_key`** (rimandata: si riconsidera solo se servirà gating/drift-check). Niente CASE. D3 ridotto a vista union + fn wrapper. |
| **B** | **`esito` = FK + discriminatore `is_verdetto`.** `config.esiti_flussi_pratiche` fa doppio lavoro (verdetti *e* esiti di instradamento come `MERCE_PRESENTE`/`SOLO_SERVIZI`): la sola FK non impedirebbe di mappare uno stato documento su un esito di routing (nonsense semantico). | Colonna `esiti_flussi_pratiche.is_verdetto` (bool, default false; true sui 4 strutturali) + guard trigger sulle `stati_doc_*`: `esito` deve essere un verdetto. Utile anche a GUIDA (D4): il motore avanza solo su verdetti. |
| **C** | **`risolto` nel descrittore.** `UNKNOWN` collassato su `fase=APERTO` sarebbe indistinguibile da un APERTO reale: la vista-racconto V1 mentirebbe sui domini senza resolver. | Il descrittore espone `risolto boolean`: `true` = proiezione reale del dominio; `false` = fallback `UNKNOWN` (fase `APERTO` resta per il routing del motore, il FE usa `risolto` per il fallback "milestone manuale come oggi"). |
| **D** | **Placement**: resolver di dominio in `vendite`; vista UNION cross-dominio in **`script`** (layer applicativo riusabile), NON in `pratiche` (l'engine non deve essere editato a ogni nuovo dominio); wrapper scalare in `pratiche` (è l'API del motore). Layering: engine → script → dominio. | `vendite.vw_stato_sorgente_preventivo` → `script.vw_stato_sorgente` → `pratiche.fn_stato_sorgente`. |
| **E** | **`is_abortito` non si tocca** (domanda §7.3 prima stesura). `terminale` è l'asse uniforme; `is_abortito` conserva la sua semantica specifica (abbandono della *revisione*, ≠ terminale: RIFIUTATO/SCADUTO sono terminali ma non abortiti). | Nessun intervento su `is_abortito`. |

Rilievi minori accettati insieme alle decisioni:

- **Naming**: colonne pulite `fase` / `esito` / `terminale` (niente suffisso `_norm`: il
  contesto tabella basta e il misto `fase_norm`+`terminale` era incoerente).
- **`fase` = CHECK, non tabella-vocabolario** (asimmetria voluta rispetto a `esito`):
  `esiti_flussi_pratiche` esiste perché è vocabolario condiviso già referenziato da FK del
  motore; `fase` è vocabolario **posseduto dal motore** (4 valori chiusi su cui l'Anello 2
  ragiona) → CHECK è sufficiente. Aggiunto anche CHECK di coerenza `terminale ⇒ fase=CHIUSO`
  (invariante della mappa §2 su cui poggia l'auto-chiusura milestone).
- **Lag dello stato memorizzato** (da documentare, non da "correggere"): la proiezione
  fotografa lo **stato scritto** sul documento. `EMESSO → SCADUTO` è transizione asincrona
  (job notturno, §7c linee-guida-sql): un preventivo scaduto-per-data ma non ancora flippato
  proietta `IN_ATTESA` fino al giro del job. Il resolver NON ricalcola la scadenza (sarebbe
  logica di dominio duplicata). Nota obbligatoria nel manuale del resolver.
- **`vw_preventivi_pratiche` non è un precedente di D2**: proietta lo stato della *pratica*,
  non del documento. D2 è costruzione genuinamente nuova (stima di conseguenza).
- **D4 (GUIDA)**: `POSITIVO` non è edge-triggered (ACCETTATO *e* EVASO proiettano POSITIVO):
  il meccanismo "avanza-su-esito-proiettato" dovrà essere idempotente. Vincolo annotato per
  la fase 2, fuori scope qui.

## 1. Obiettivo

Dare al motore pratiche un **descrittore normalizzato** dello stato del documento di dominio
collegato (preventivo/offerta/ordine/contratto), **read-time**, senza mirror e senza che il
motore nomini mai uno stato di dominio. Il **dominio dichiara la mappa**; il motore consuma.

**Descrittore universale** (contratto §4 del brief design + decisione C):

| Campo | Origine |
|---|---|
| `risolto` (bool) | motore: `true` = proiezione reale, `false` = fallback `UNKNOWN` |
| `stato_codice_interno` | valore nativo `config.stati_doc_*` (immutabile — logica/test/tracing) |
| `stato_codice` + `stato_descrizione` | valori nativi `config.stati_doc_*` (display, §6c linee-guida) |
| `fase` ∈ `APERTO · IN_CORSO · IN_ATTESA · CHIUSO` | mapping dichiarato dal dominio (D1) |
| `esito` → `config.esiti_flussi_pratiche.codice_interno` con `is_verdetto=true` (`NULL/POSITIVO/NEGATIVO/PARZIALE`) | mapping dominio (D1) |
| `terminale` (bool) | mapping dominio (D1) |

## 2. Vocabolario universale (mappa dichiarata dal dominio)

Verificato sui seed reali (brief design §3). Seedato nelle colonne D1:

```text
stato di dominio               → fase       esito       terminale
──────────────────────────────────────────────────────────────────
DRAFT / BOZZA                  → APERTO     NULL        false
EMESSO / EMESSA                → IN_ATTESA  NULL        false
CONFERMATO / ATTIVO            → IN_CORSO   NULL        false
ALLOCATO/SPEDITO/CONSEGNATO    → IN_CORSO   NULL        false
ACCETTATO / ACCETTATA          → IN_CORSO   POSITIVO    false
RIFIUTAT* / SCADUTO / SUPERATA → CHIUSO     NEGATIVO    true
EVASO / FATTURATO / CESSATO    → CHIUSO     POSITIVO    true
ANNULLAT* (is_abortito)        → CHIUSO     NEGATIVO    true
```

Invariante strutturale: `terminale = true ⇒ fase = CHIUSO` (CHECK).

## 3. Stato di partenza (recon 2026-07-01, docs/it/dbzero)

- `config.stati_doc_{preventivi,offerte,ordini,contratti}`: hanno `codice_interno`, `codice`,
  `descrizione`, `attivo`, `ordine`, `meta`. **`is_abortito` solo su preventivi/contratti**,
  `is_bozza` solo contratti. **Nessuna colonna di normalizzazione**.
- `config.stati_doc_preventivi` seed reale: `DRAFT, EMESSO, ACCETTATO, RIFIUTATO, SCADUTO,
  ANNULLATO(is_abortito), EVASO` — la mappa §2 li copre al 100% → `fase NOT NULL` fattibile.
- `config.sorgenti`: registry con `codice_interno`, `target_table` (regclass),
  `key_selector` (`id`|`uid`), `scope`. PREVENTIVO → `vendite.preventivi`, `key_selector=uid`.
- `pratiche.pratiche_sorgenti`: `sorgente_tipo_id` (→ `config.sorgenti`), `sorgente_uid`
  (text), `ruolo_link`, `flusso_id`, `meta`. Indice `ix_pratiche_sorgenti_tipo_uid`.
- `config.esiti_flussi_pratiche` (2026-07-01): 4 esiti strutturali (verdetti) seedati in
  `00_schema` + 2 di instradamento seedati dal dominio in `80_data`.
- Trappola seed nota: il changeset CSV `20250917-01` (immutabile) ha `nullValue: ""` → la
  CSV **non può esprimere NULL** per `esito` (memoria `feedback_liquibase_csv_null_sentinel`).
  Conseguenza: `fase`/`terminale` (mai NULL) viaggiano in CSV; `esito` in changeset UPDATE.

## 4. Deliverable DB

> **Roll-out per dominio, additivo.** Prima **solo PREVENTIVI**, validare end-to-end con
> BE+FE (fase MOSTRA), poi replicare su offerte/ordini/contratti. Un dominio senza resolver
> → descrittore `UNKNOWN` (`risolto=false`), milestone manuale come oggi (nessuna regressione).

### D1 — Colonne di normalizzazione sulle `config.stati_doc_*` (dominio-owned)

Su `config.stati_doc_preventivi` (poi ogni `stati_doc_*`):

- `fase` varchar NOT NULL — CHECK in (`APERTO`,`IN_CORSO`,`IN_ATTESA`,`CHIUSO`);
- `esito` varchar NULL — FK → `config.esiti_flussi_pratiche.codice_interno` + guard
  `is_verdetto=true` (NULL ammesso = nessun verdetto);
- `terminale` boolean NOT NULL DEFAULT false — CHECK `NOT terminale OR fase='CHIUSO'`.

Prerequisito motore: `config.esiti_flussi_pratiche.is_verdetto` boolean NOT NULL DEFAULT
false (true sui 4 strutturali) + trigger guard generico riusabile
`config.trgfn_stati_doc_guard_esito_verdetto`.

Seed (playbook `is_abortito`, migration `20260515-02`): backfill `UPDATE` keyed su
`codice_interno` in `00_schema` (copre il DB vivo) + colonne `fase`/`terminale` nella CSV
(copre i DB fresh; `esito` via changeset UPDATE idempotente in `80_data`, vedi §3).

### D2 — Resolver per dominio (vista normalizzata)

`vendite.vw_stato_sorgente_preventivo`: espone il descrittore per ogni preventivo —
`(sorgente_tipo_id, sorgente_uid, stato_codice_interno, stato_codice, stato_descrizione,
fase, esito, terminale)`. `sorgente_tipo_id` risolto con join su
`config.sorgenti.codice_interno='PREVENTIVO'` (mai id letterale); `sorgente_uid =
(preventivi.uid)::text` coerente con `key_selector=uid`. **Contratto resolver: al più una
riga per (tipo, uid).**

### D3 — Vista union di motore + wrapper scalare (decisione A: niente `resolver_key`)

- **`script.vw_stato_sorgente`**: UNION ALL dei resolver di dominio (oggi 1 ramo), aggiunge
  `risolto=true` e normalizza i tipi a `text`. Registrare un dominio = aggiungere un ramo
  (changeset nuovo, additivo). Join-abile a `pratiche_sorgenti` su
  (`sorgente_tipo_id`,`sorgente_uid`) → niente N+1 nelle liste; riga assente = non risolto.
- **`pratiche.fn_stato_sorgente(p_sorgente_tipo_id, p_sorgente_uid)`**: wrapper scalare per
  il dettaglio singolo. Sempre **esattamente 1 riga**: la proiezione se esiste, altrimenti
  `UNKNOWN` (`risolto=false`, `stato_codice_interno='UNKNOWN'`, descrizione `'n/d'`,
  `fase='APERTO'`, `esito=NULL`, `terminale=false`) senza errore. Guard fail-fast sui
  parametri (NULL/<=0 → `E_STATO_SORGENTE_PARAM_INVALIDO`).

### D4 — GUIDA "avanza-su-esito-proiettato" *(fase 2, dopo MOSTRA)*

Generalizzare l'handler per-pratica `vendita.accetta_preventivo` in meccanismo config-driven
"quando il documento proietta `esito=POSITIVO` (o `terminale`) → il milestone avanza",
riusando `pratiche.template_flussi_handler_eventi` (o binding dedicato). **Vincolo annotato**:
deve essere idempotente/edge-triggered (ACCETTATO ed EVASO proiettano entrambi POSITIVO).
Salda il debito in `gestione-pratiche-come-procedere.md §5.3`. **Non prima** che MOSTRA
(D1-D3 + BE + FE) sia validato su PREVENTIVI.

## 5. Piano di sviluppo (increment PREVENTIVI — file)

Numerazione globale per data 2026-07-01 (NN successivo libero: 13).

| # | File | Contenuto |
|---|---|---|
| 1 | `00_schema/config/20260701-13-alter-esiti-flussi-pratiche-add-is-verdetto-mctit.yaml` | `is_verdetto` bool NOT NULL DEFAULT false + backfill true sui 4 strutturali + COMMENT |
| 2 | `00_schema/config/20260701-14-alter-stati-doc-preventivi-add-proiezione-mctit.yaml` | `fase`/`esito`/`terminale` + backfill mappa §2 + SET NOT NULL fase + CHECK fase + CHECK terminale⇒CHIUSO + FK esito |
| 3 | `20_code/config/20260701-15-create-trgfn-stati-doc-guard-esito-verdetto-mctit.yaml` | trgfn generico guard verdetto + trigger `_a10_..._ins_upd` su `stati_doc_preventivi` |
| 4 | `20_code/vendite/20260701-16-create-vw-stato-sorgente-preventivo-mctit.yaml` | resolver dominio D2 |
| 5 | `20_code/script/20260701-17-create-vw-stato-sorgente-mctit.yaml` | vista union motore D3 (`risolto`) |
| 6 | `20_code/pratiche/20260701-18-create-fn-stato-sorgente-mctit.yaml` | wrapper scalare D3 con guard + fallback UNKNOWN |
| 7 | `80_data/changelog/20260701-19-upsert-stati-doc-preventivi-esito-proiezione-mctit.yaml` | seed `esito` (UPDATE idempotente; NULL non esprimibile in CSV, §3) |
| 8 | `80_data/changelog/20260701-20-upsert-messaggi-errore-proiezione-stato-mctit.yaml` | codici 502/503 (loadUpdateData `messaggi_errore.csv`) |
| 9 | CSV: `esiti_flussi_pratiche.csv` (+`is_verdetto`), `stati_doc_preventivi.csv` (+`fase`,`terminale`), `messaggi_errore.csv` (+2 righe) | seed fresh-DB |
| 10 | `db/pgtap/pratiche/test-proiezione-stato-sorgente.sql` | criteri §6 + guard + seed |
| 11 | Doc manuali: `vendite/manual/vw_stato_sorgente_preventivo.md`, `script/manual/vw_stato_sorgente.md`, `pratiche/manual/fn_stato_sorgente.md` + aggiornamento `config/manual/stati_doc_preventivi.md`, `config/manual/esiti_flussi_pratiche.md` | inclusa nota lag stato memorizzato |

Codici errore (registry `config.messaggi_errore`):
- `E_STATO_SORGENTE_PARAM_INVALIDO` (id 502) — guard parametri `fn_stato_sorgente`;
- `E_STATO_DOC_ESITO_NON_VERDETTO` (id 503) — guard trigger `esito` non-verdetto.

Fuori scope increment: BE (esposizione descrittore nei payload), FE (vista-racconto V1),
domini offerte/ordini/contratti (replica dopo validazione), D4.

## 6. Criteri di accettazione (PREVENTIVI, prima consegna)

- `config.stati_doc_preventivi` ha `fase`/`esito`/`terminale` seedati per ogni stato
  secondo §2.
- `fn_stato_sorgente(tipo_preventivo, uid)` su un preventivo **EMESSO** ritorna
  `risolto=true, fase=IN_ATTESA, esito=NULL, terminale=false, stato_descrizione='Emesso'`;
  su **ACCETTATO** `fase=IN_CORSO, esito=POSITIVO`; su **ANNULLATO** `fase=CHIUSO,
  esito=NEGATIVO, terminale=true`.
- Un `sorgente_tipo` senza ramo resolver → `fn_stato_sorgente` ritorna `UNKNOWN`
  (`risolto=false`) senza errore. Idem per uid inesistente.
- `script.vw_stato_sorgente` join-abile a `pratiche_sorgenti` restituisce il descrittore
  per riga; al più una riga per (tipo, uid).
- Il guard `is_verdetto` blocca `esito` di instradamento o inesistente sulle `stati_doc_*`.

## 7. Decisioni confermate col team DB

1. ~~Resolver = vista o funzione?~~ → **Vista** union unica superficie + fn wrapper
   (decisione A). `resolver_key` NON introdotto.
2. ~~`esito`: FK o valore libero?~~ → **FK + `is_verdetto`** (decisione B).
3. ~~`terminale` vs `is_abortito`~~ → **`is_abortito` non si tocca** (decisione E).

---

*Alla presa in carico: aggiornato lo stato in testa (2026-07-01) e l'addendum decisioni nel
brief design [brief-design-proiezione-stato-dominio.md](../work-in-progress/brief-design-proiezione-stato-dominio.md).
A chiusura increment: aggiornare la riga V10 di analisi-pratiche-valutazione-stato.md.*
