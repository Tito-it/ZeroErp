# Brief DB — Motore pratiche: step a esito di dominio (`DOMINIO`) + definizioni workflow versionate

> **Per**: team DB (`dev/db-tid`). · **Da**: backend/frontend agent (analisi congiunta 2026-07-02).
> **Priorità**: Parte 1 🔴 **alta** (buco API vivo, vedi §1.1) · Parte 2 🟠 media (fondazione,
> nessun comportamento visibile fino alla Fase 2). · **Data**: 2026-07-02.
>
> **Assorbe/attua due cantieri**:
>
> 1. [brief-db-guard-esito-smistamento.md](brief-db-guard-esito-smistamento.md) — invariante
>    step bivio (incidente `PRA-0000243`) → **Parte 1**, con correzioni fattuali (§1.1).
> 2. [brief-design-workflow-definizioni-versionate.md](brief-design-workflow-definizioni-versionate.md)
>    — modello C «edizioni versionate + fork» (decisione 2026-07-02) → **Parte 2** = la delega
>    DB delle Fasi 0–2 prevista da quel brief.
>
> **Companion BE/FE**:
> [brief-be-fe-step-dominio-e-definizioni-versionate.md](brief-be-fe-step-dominio-e-definizioni-versionate.md)
> — consumi backend/frontend, da rilasciare in lockstep dove indicato.
>
> **Stato (2026-07-02)**: **Parte 1 ✅ APPLICATA + TESTATA** (dettaglio in coda a §1.8) ·
> **Parte 2 Fase 0 ✅ APPLICATA + TESTATA** (dettaglio in coda a §2.1) · **doc manuale
> fatta** per entrambe · commit in attesa di "procedi" · prossimo: **Fase 1** (§2.2).

---

## 0. Perché un documento unico — contratto anti-collisione

I due cantieri toccano lo stesso oggetto (`pratiche.template_flussi`) da direzioni opposte:
la Parte 1 vi aggiunge **semantica per-step** (classe di esito ammessa), la Parte 2 lo
**re-parenta** sotto `workflow_definizioni` e lo rende copiabile (fork/nuova versione) e
immutabile (PUBBLICATA). Senza un contratto comune, la semantica della Parte 1 andrebbe persa
nelle copie o si aggancerebbe a chiavi che la Parte 2 distrugge. Il contratto:

- **C1 — Chiave di aggancio.** Ogni oggetto nuovo della Parte 1 (valori, guard, seed, pgTAP)
  si aggancia a `template_flussi.id`, **mai** alla coppia `(tipo_prestazione_id, codice)`:
  la riga template sopravvive al re-parent, l'unique `uq_pratiche_template_flussi_tipo_codice`
  no (migra a `(definizione_id, codice)` in Fase 0).
- **C2 — Il marker bivio è un attributo del template**, dentro l'asse esistente
  `modalita_esito` (nuovo valore `DOMINIO`, §1.2). Nessuna tabella config globale.
- **C3 — L'eventuale whitelist "esiti producibili per step" (L2, rinviata)** sarà una tabella
  figlia di `template_flussi` (`template_flussi_esiti_ammessi (template_flusso_id, esito)`),
  duale simmetrico di `template_flussi_prerequisiti.esito_richiesto`. Entra automaticamente
  nel set di copia del fork e nel lock strutturale.
- **C4 — Lock strutturale della PUBBLICATA** (chiude la domanda aperta #3 del brief design):
  include l'**asse esito completo** (`modalita_esito`, `esito_default`, futura whitelist),
  oltre a step, grafo prerequisiti e automazioni. Correggibili solo i campi display
  (`descrizione`).
- **C5 — Contratto runtime invariato.** `completa_step_pratica(pratica_id, template_codice)`
  risolve dentro il percorso della pratica; con la Parte 2 il `codice` resta unico *per
  definizione* e la pratica pinna la definizione ⇒ la risoluzione per codice resta ben
  definita. I guard runtime leggono il template via `flussi.template_flusso_id` ⇒ sono
  indifferenti al genitore del template.
- **C6 — Set di copia enumerato in un solo punto.** Ogni figlio di `template_flussi`
  (presente o futuro) entra per definizione nel perimetro copia-fork + lock; la funzione di
  copia (§2.4) è l'unico posto che lo elenca.

**Ordine di atterraggio: Parte 1 prima, poi Parte 2 Fase 0.** Per costruzione (C1) l'ordine è
invertibile senza danni, ma Parte-1-prima chiude il buco API vivo e fa sì che il seed "v1
preset" della Fase 0 fotografi template già completi di semantica bivio.

---

## Parte 1 — Step a esito di dominio (`modalita_esito = 'DOMINIO'`)

### 1.1 Contesto e problema (correzioni al brief origine)

Lo step **SMISTAMENTO** (`template_flussi` id 9012, tipo 9004 PREVENTIVI) è un bivio: il suo
esito non è un verdetto scelto dall'operatore ma è **calcolato dal dominio**
(`vendite.completa_smistamento` → `MERCE_PRESENTE` id 5 / `SOLO_SERVIZI` id 6, entrambi
`is_verdetto = false`). Su `PRA-0000243` è stato chiuso con `POSITIVO` (verdetto,
`is_verdetto = true`): il ramo merce non si è attivato e la pratica si è auto-chiusa.

**Correzioni fattuali rispetto al brief origine** (verificate sul codice vivo):

1. Il percorso che ha accettato `POSITIVO` non è (solo) il generico `cambia_stato_flusso`:
   è il percorso **mainstream** di completamento — `ApiPraticaFlussoStato` instrada
   `COMPLETATO` su `completa_flusso`/`avvia_e_completa_flusso`, che validano l'esito con
   `_require_esito_valido` (solo esistenza+attivo a vocabolario). `POSITIVO` passa.
2. La mitigazione esistente è **solo FE** (registry `flussoDomainCompletionRegistry.js` che
   sopprime il picker e instrada su `completa-smistamento`). L'endpoint
   `POST /pratiche/<id>/flussi/<id>/stato/` con `{nuovo_stato: COMPLETATO, esito: POSITIVO}`
   **riproduce ancora oggi l'incidente**: `require_esito_selezionabile_operatore` blocca solo
   gli esiti di ramo scelti a mano, non i verdetti su uno step bivio.
3. Da cui la priorità **alta**: la corruzione è silenziosa (mis-routing + auto-chiusura) e
   costosa da riparare.

A DB, oggi, l'esito è vincolato solo da `fk_flussi_esito` (esistenza a vocabolario) e da
`trgfn_flussi_guard_esito_completato` (COMPLETATO ⇒ esito NOT NULL, err 477). **Nessun
vincolo di classe** (verdetto vs ramo) per step.

### 1.2 Modello: quarto valore `DOMINIO` di `modalita_esito`

Si estende l'asse esistente (`MANUALE` / `AUTOMATICO` / `CONTESTUALE`) con:

> **`DOMINIO`** — l'esito dello step è **calcolato da un building block di dominio** (es.
> `vendite.completa_smistamento`); nessuna scelta operatore; `esito_default` deve essere
> NULL; l'esito accettato al completamento deve avere `is_verdetto = false`.

Perché questo e non una colonna `is_bivio` o la whitelist subito:

- riusa l'asse che descrive già "come lo step ottiene l'esito" e il guard config-time che lo
  presidia (`trgfn_template_flussi_guard_modalita_esito`, err 494/495);
- il payload flussi BE **espone già** `template_modalita_esito` al FE → la soppressione del
  picker diventa data-driven senza campi nuovi;
- **attenzione**: gli step "bivio su verdetto" (l'operatore sceglie POSITIVO/NEGATIVO e il
  percorso ramifica sui prerequisiti esito-aware — pattern testato in
  `test-bivi-condizionali.sql`) **non sono DOMINIO**: restano MANUALE/CONTESTUALE.
  `DOMINIO` marca solo gli step il cui esito è calcolato, non ogni biforcazione;
- la whitelist per-step (L2) è rinviata per regola-del-2: il primo consumatore è solo
  SMISTAMENTO; il secondo arriverà col rollout offerte/ordini/contratti (D4 di
  `brief-db-proiezione-stato-dominio-rollout-offerte-ordini-contratti.md`). Il design L2 è
  già fissato dal contratto C3, quindi l'estensione **non riscrive** il meccanismo L1: lo
  raffina (da "classe is_verdetto" a "insieme esplicito").

Deliverable:

- **D1-1** (`00_schema/pratiche`): DROP+ADD di `chk_template_flussi_modalita_esito` →
  `IN ('MANUALE','AUTOMATICO','CONTESTUALE','DOMINIO')` + aggiornamento COMMENT colonna.

### 1.3 Invariante runtime: guard di classe esito al completamento

Nuova trigger function `pratiche.trgfn_flussi_guard_esito_classe()` + trigger
`trg_flussi_a10_guard_esito_classe_ins_upd` (BEFORE INSERT OR UPDATE su `pratiche.flussi`).
Logica (schema, non DDL finale):

```text
SE (NEW.stato = COMPLETATO) E (INSERT oppure OLD.stato <> COMPLETATO) E NEW.esito IS NOT NULL:
    v_modalita := modalita_esito del template (via NEW.template_flusso_id; NULL template ⇒ 'MANUALE')
    v_is_verdetto := is_verdetto dell'esito (config.esiti_flussi_pratiche per codice_interno)
    SE v_modalita = 'DOMINIO'  E v_is_verdetto        → raise FLUSSI_ESITO_NON_AMMESSO
    SE v_modalita <> 'DOMINIO' E NOT v_is_verdetto    → raise FLUSSI_ESITO_NON_AMMESSO
```

Note di progetto:

- **Bidirezionale**: chiude sia l'incidente reale (verdetto su step DOMINIO) sia il caso
  simmetrico (esito di ramo scritto su step normale via percorso generico/SQL diretto — oggi
  fermato solo dal guard BE operatore).
- **Scoped alla transizione di completamento** (non "ogni riga con esito"): il flusso 543 di
  `PRA-0000243` porta storicamente `POSITIVO` su SMISTAMENTO — la riga resta toccabile
  (nessuna migrazione dati, coerente col brief origine); la matrice transizioni ammette solo
  `IN_CORSO → COMPLETATO` e nessuna uscita da COMPLETATO, quindi le righe legacy non
  ri-attraversano il guard.
- **Idempotenza**: il no-op sul re-fire è già garantito a monte in Python
  (`completa_step_pratica` corto-circuita sugli stati terminali) e dalla matrice transizioni.
  Il guard **non deve** assorbire re-fire: nessuna logica aggiuntiva.
- Il caso `esito NULL` a COMPLETATO resta di competenza del guard esistente 477.
- Errori via `script.fn_log_and_raise_error('pratiche', ..., NEW.tx_id, VARIADIC ...)`.

Deliverable:

- **D1-2** (`20_code/pratiche`): `trgfn_flussi_guard_esito_classe` + trigger.

### 1.4 Guard config-time: estensione di `trgfn_template_flussi_guard_modalita_esito`

Il corpo attuale (doc autogen, err 494/495) va esteso — **nuovo file con numerazione
successiva, corpo copiato dalla doc autogen** (regola DDL-dalla-doc, mai dagli YAML):

- **Inv1 riformulata**: `esito_default` obbligatorio se `modalita_esito IN
  ('AUTOMATICO','CONTESTUALE')` (oggi: `<> 'MANUALE'`, che con DOMINIO diventerebbe errata)
  → resta err 494.
- **Inv2 invariata**: AUTOMATICO solo su direzione INTERNA (err 495).
- **Inv3 nuova**: `modalita_esito = 'DOMINIO' AND esito_default IS NOT NULL` → raise
  `TEMPLATE_FLUSSO_DOMINIO_ESITO_DEFAULT_VIETATO` (l'esito lo calcola il dominio, un default
  non ha senso e maschererebbe errori).
- **Inv4 nuova**: `modalita_esito IN ('AUTOMATICO','CONTESTUALE') AND esito_default` non è
  un verdetto (`is_verdetto = false`) → raise `TEMPLATE_FLUSSO_ESITO_DEFAULT_NON_VERDETTO`.
  Serve perché dal `20260701-02` `esito_default` è FK al vocabolario **senza** vincolo di
  classe: senza Inv4 un config sbagliato (default = MERCE_PRESENTE su step AUTOMATICO)
  esploderebbe solo a runtime sul guard §1.3 — meglio fail-fast a config-time.

Deliverable:

- **D1-3** (`20_code/pratiche`): CREATE OR REPLACE della trigger function (Inv1–Inv4).

### 1.5 Errori nuovi (catalogo `config.messaggi_errore`)

Id proposti — **verificare `max(id)` al momento della scrittura** (al 2026-07-02 il massimo è
503, prossimo libero 504). Righe CSV (`codice,lingua,messaggio,id,causa,soluzione`):

| Codice | Id | Messaggio (con `%s`) |
| --- | --- | --- |
| `FLUSSI_ESITO_NON_AMMESSO` | 504 | `Esito %s non ammesso per lo step %s: richiesto un esito di %s.` (valori: esito, codice template, `ramo (calcolato dal dominio)` \| `verdetto`) |
| `TEMPLATE_FLUSSO_DOMINIO_ESITO_DEFAULT_VIETATO` | 505 | `Lo step %s in modalita DOMINIO non ammette esito_default (%s): l'esito e' calcolato dal dominio.` |
| `TEMPLATE_FLUSSO_ESITO_DEFAULT_NON_VERDETTO` | 506 | `esito_default %s non valido per lo step %s: AUTOMATICO/CONTESTUALE richiedono un verdetto.` |

Il messaggio di 504 contiene la sottostringa stabile **"non ammesso per lo step"** — è il
marker concordato per `_KNOWN_DB_ERROR_MARKERS` lato BE (companion §BE-1.1): non
riformularla senza coordinarsi.

Deliverable:

- **D1-4** (`80_data`): **solo** append delle 3 righe a `messaggi_errore.csv` — **nessun
  nuovo changeset di load**: il CSV è già agganciato a loader `runOnChange: true`, che
  ri-girano da soli quando il CSV cambia (decisione owner 2026-07-02: basta aggiungere
  un loader per ogni batch di codici).

### 1.6 Seed: flip di SMISTAMENTO a `DOMINIO`

Stato vivo: 9012 ha `modalita_esito = 'MANUALE'`, `esito_default = NULL` (caricato da
`template_flussi_esito_config.csv` via `20260617-04-...`, **già mergiato: non toccarlo**).

- **D1-5** (`80_data/changelog`): nuovo changeset `UPDATE pratiche.template_flussi SET
  modalita_esito = 'DOMINIO' WHERE id = 9012` (chiave per id o per chiave stabile
  tipo+codice — a scelta; con preCondition idempotente, pattern `20260701-05`). Nessun altro
  template cambia: 9009/9011 restano CONTESTUALE (bivi su verdetto legittimi non esistono nel
  tipo 9004; APPROVAZIONE_CLIENTE ramifica sul verdetto POSITIVO ed è correttamente
  CONTESTUALE).
- **Ordine interno Parte 1**: D1-5 deve girare **dopo** D1-1 (CHECK esteso) — su DB vivo e
  in replay CI la sequenza fasi (00_schema → 80_data) lo garantisce già.

### 1.7 pgTAP

Verifica preventiva fatta (regola guard-restrittivo → grep test esistenti):

- **Da adeguare**: `db/pgtap/pratiche/test-chiusura-nessun-lavoro-pendente.sql` — completa lo
  step sintetico `NP_SMIST` con `MERCE_PRESENTE`/`SOLO_SERVIZI` (L148/L199) ma lo crea senza
  marcatore: la fixture deve creare `NP_SMIST` con `modalita_esito = 'DOMINIO'` (e senza
  `esito_default`, coerente con Inv3).
- **NON impattati** (verificato): `test-bivi-condizionali.sql` e
  `test-prerequisiti-esito-aware.sql` chiudono i nodi di biforcazione con **verdetti**
  (POSITIVO/NEGATIVO) su step non-DOMINIO → il guard li ammette. Tutti gli altri test
  completano step normali con verdetti.

Nuovo file `test-guard-esito-classe.sql` (indice casi):

1. step DOMINIO + verdetto (`POSITIVO`) → raise `FLUSSI_ESITO_NON_AMMESSO`;
2. step DOMINIO + `MERCE_PRESENTE` → ok;
3. step DOMINIO + `SOLO_SERVIZI` → ok;
4. step MANUALE + `MERCE_PRESENTE` (UPDATE SQL diretto) → raise;
5. step MANUALE/CONTESTUALE + verdetto → ok (non regressione);
6. riga legacy COMPLETATO con esito "sbagliato": UPDATE di colonna non di stato → nessun
   raise (guard scoped alla transizione);
7. config-time: template DOMINIO con `esito_default` → raise 505; AUTOMATICO con
   `esito_default = MERCE_PRESENTE` → raise 506; AUTOMATICO senza default → raise 494
   (non regressione).

- **D1-6**: nuovo test + fix fixture di cui sopra; smoke e2e percorso PREVENTIVI (smistamento
  merce → 9013/9014 → commessa) già coperto dai test vendite: rieseguirli.

### 1.8 Criteri di accettazione (Parte 1)

1. Completare SMISTAMENTO con `POSITIVO` (o altro verdetto) fallisce con
   `FLUSSI_ESITO_NON_AMMESSO` **da qualunque percorso**: API di completamento normale,
   percorso generico, UPDATE SQL diretto.
2. `vendite.completa_smistamento` funziona invariato su entrambi i rami.
3. Gli step non-DOMINIO restano completabili con i loro verdetti; in più un esito di ramo su
   step non-DOMINIO viene rifiutato (difesa simmetrica, prima solo BE).
4. I "bivi su verdetto" (prerequisiti esito-aware su POSITIVO/NEGATIVO) restano intatti.
5. Idempotenza preservata: nessuna logica di re-fire nel guard (garanzia a monte).
6. pgTAP verdi (nuovo file + `test-chiusura-nessun-lavoro-pendente.sql` adeguato).

**Complementarità col BE (da non semplificare via):** il guard DB enforce l'invariante di
**valore** (classe esito giusta per lo step); `require_esito_selezionabile_operatore` enforce
quella di **autorizzazione** (l'operatore invia a mano solo verdetti) — il DB non distingue
chi scrive. Restano entrambi. Il companion BE/FE aggiunge marker + pre-guard parlante.

**STATO Parte 1 — FATTA (2026-07-02, applicata + pgTAP verdi):**

- changeset: `20260702-15` (CHECK DOMINIO + COMMENT), `20260702-16` (guard config-time
  Inv1–Inv4), `20260702-17` (guard runtime 504);
- CSV: `messaggi_errore.csv` +504/505/506 (**senza nuovo loader** — D1-4 aggiornata),
  `template_flussi_esito_config.csv` 9012 → `DOMINIO` (ripreso dal loader `20260617-04`);
- pgTAP: `test-guard-esito-classe.sql` (nuovo, plan 10), fixture `NP_SMIST → DOMINIO` +
  `is_verdetto` esplicito in `test-chiusura-nessun-lavoro-pendente.sql`,
  `test-esito-configurabile-template-flussi.sql` esteso (plan 13, casi 10–12);
- doc manuale: `manual/trgfn_template_flussi_guard_modalita_esito.md` +
  `manual/trgfn_flussi_guard_esito_classe.md`; autogen rigenerata (Tid).
- Resta: consumi BE/FE (companion), commit.

---

## Parte 2 — Definizioni workflow versionate (Fasi 0–2)

Richiami di design dal brief origine (decisi, non rinegoziare qui): modello C «edizioni
versionate + fork»; identità condivisa = `tipi_prestazione`; pin alla creazione, mai
aggiornato; una sola PUBBLICATA per scope; runtime del motore intatto. **Domanda aperta #3:
chiusa** con C4 (lock strutturale include l'asse esito).

### 2.1 Fase 0 — Fondazione (nessun comportamento visibile)

> **Raffinamenti in corso d'opera (2026-07-02, in sviluppo)** — deviazioni motivate dal
> testo sotto, decise all'avvio dello sviluppo:
>
> 1. **Fix bug di sequenza del brief**: `NOT NULL` su `pratiche.definizione_id` in Fase 0
>    con auto-pin solo in Fase 1 avrebbe rotto `create_pratica` (INSERT BE senza la
>    colonna) alla prima pratica nuova. → `fn_risolvi_definizione` (ex D2-5) e i trigger
>    di **default** (auto-pin su `pratiche`, auto-default su `template_flussi`) sono
>    **anticipati alla Fase 0**. Restano in Fase 1 i guard veri (flusso↔definizione,
>    scope/stato sul pin esplicito, immutabilità, remap generazione).
> 2. **Bootstrap preset per-tipo via trigger**: invariante "ogni tipo di prestazione ha
>    il suo preset v1 PUBBLICATA", garantita da trigger AFTER INSERT su
>    `tipi_prestazione` (+ backfill per i tipi esistenti e per eventuali tipi sintetici
>    residui). Su DB fresco i seed dei tipi generano i preset da soli → **niente seed
>    CSV a id fissi** per `workflow_definizioni`; i backfill mappano per join sul tipo.
> 3. **Drop di `uq_pratiche_template_flussi_tipo_codice` e `uq_template_flussi_chiusura`
>    RINVIATO alla Fase 2**: i pgTAP esistenti fanno `ON CONFLICT (tipo_prestazione_id,
>    codice)` sulle fixture template; il vecchio unique resta corretto finché esiste una
>    sola definizione per tipo (pre-fork). Il **nuovo** unique
>    `(definizione_id, codice)` e il parziale chiusura per definizione nascono ora; il
>    vecchio si toglie col primo fork (prima riga della Fase 2). Zero churn sui test ora.
> 4. Con default+bootstrap, la Fase 0 è **davvero** invisibile: nessun fixture pgTAP,
>    nessun seed e nessuna riga BE da toccare.

#### D2-1 — Tabella `pratiche.workflow_definizioni` (`00_schema/pratiche`)

| Colonna | Tipo | Note |
| --- | --- | --- |
| `id` | `INTEGER GENERATED BY DEFAULT AS IDENTITY` PK | tabella tecnica (convenzione) |
| `tipo_prestazione_id` | INTEGER NOT NULL, FK `tipi_prestazione` | identità condivisa |
| `emittente_fiscale_id` | BIGINT NULL, FK `anagrafiche.emittenti_fiscali(id)` | NULL = **preset** |
| `versione` | INTEGER NOT NULL | progressivo per (tipo, emittente) |
| `stato` | VARCHAR NOT NULL DEFAULT `'BOZZA'`, CHECK `IN ('BOZZA','PUBBLICATA','RITIRATA')` | ciclo §2.2 |
| `preset_origine_id` | INTEGER NULL, FK self | provenance fork |
| `versione_origine` | INTEGER NULL | versione del preset al fork (per drift) |
| `descrizione` | TEXT NOT NULL | |
| `meta` | JSONB NOT NULL DEFAULT `'{}'` | |
| audit std | `tx_id`, `data_insert`, `user_insert`, `data_update`, `user_update` | |

Vincoli:

- `UNIQUE (tipo_prestazione_id, emittente_fiscale_id, versione) NULLS NOT DISTINCT`;
- unique **parziale**: `(tipo_prestazione_id, emittente_fiscale_id) WHERE stato = 'PUBBLICATA'`
  (NULLS NOT DISTINCT) — una sola pubblicata per scope;
- `UNIQUE (id, tipo_prestazione_id)` — abilita la FK composita di D2-2 (coerenza tipo senza
  trigger);
- indici FK: **non crearli a mano** (`dbops.apply_fk_index_policy()` in `90_end`).

#### D2-2 — `template_flussi.definizione_id` + swap unique (`00_schema/pratiche`)

- `ADD COLUMN definizione_id INTEGER NULL` + **FK composita**
  `(definizione_id, tipo_prestazione_id) REFERENCES workflow_definizioni (id, tipo_prestazione_id)`
  → un template non può mai puntare a una definizione di un altro tipo, senza guard.
  `tipo_prestazione_id` **resta** (query/seed esistenti invariati).
- Nuovo unique `uq_template_flussi_definizione_codice (definizione_id, codice)` (NULL
  distinti di default ⇒ non morde durante il replay CI finché il backfill non gira).
- DROP `uq_pratiche_template_flussi_tipo_codice` e `uq_template_flussi_chiusura`; nuovo
  unique parziale `uq_template_flussi_chiusura (definizione_id) WHERE chiude_pratica`.

#### D2-3 — `pratiche.definizione_id` (`00_schema/pratiche`)

`ADD COLUMN definizione_id INTEGER NULL` + FK composita analoga
`(definizione_id, tipo_prestazione_id)` → il pin non può mai divergere dal tipo della pratica.

#### D2-4 — Seed preset + backfill (`80_data`)

- Seed CSV `pratiche/workflow_definizioni.csv` con **id fissi = id tipo** (9001–9004),
  `versione = 1`, `stato = 'PUBBLICATA'`, `emittente_fiscale_id` vuoto (preset),
  descrizione "v1 — fotografia del set corrente". Anche per i tipi ritirati 9002/9003
  (i loro template esistono; l'istanziabilità resta gated da `tipi_prestazione.obsoleto_dal`).
- Backfill changeset (UPDATE, idempotenti con preCondition):
  `template_flussi.definizione_id = tipo_prestazione_id` (mappa 1:1 dei preset);
  `pratiche.definizione_id = tipo_prestazione_id`.
- `ALTER ... SET NOT NULL` su entrambe le colonne **dopo** i backfill. ⚠️ **Replay CI**: il
  NOT NULL non può stare in `00_schema` (su DB fresco i CSV template già mergiati caricano
  con `definizione_id` NULL, backfillato solo dopo). **DECISO (owner, 2026-07-02) — opzione
  A**: i SET NOT NULL sono changeset in `80_data/changelog` con numerazione successiva ai
  backfill (precedente d'uso: `20260701-05`), con commento nel changeset che spiega il
  motivo della collocazione (ordine di replay CI). Scartata l'alternativa guard-trigger
  (vincolo "finto": lo schema dichiarerebbe nullable una colonna obbligatoria). Il companion
  BE assume colonne NOT NULL — coerente.
- **Seed futuri**: da Fase 0 in poi ogni nuovo template nel seed deve valorizzare
  `definizione_id`; i CSV/loader nuovi nascono con la colonna (i loader mergiati non si
  toccano).

**Accettazione Fase 0**: pgTAP e test BE tutti verdi senza modifiche di comportamento; una
definizione per tipo ≡ oggi; `get_percorso_pratica` (BE, join per tipo) restituisce le stesse
righe.

**STATO Fase 0 — FATTA (2026-07-02, applicata + pgTAP verdi):**

- changeset: `20260702-18` (workflow_definizioni + vincoli), `-19` (definizione_id su
  template_flussi + FK composita + uq per-definizione), `-20` (definizione_id su
  pratiche), `-21` (fn_risolvi_definizione, `%TYPE` in firma/RETURNS), `-22` (bootstrap
  preset su tipi_prestazione), `-23`/`-24` (auto-default template / auto-pin pratiche),
  `-25` (backfill + SET NOT NULL in 80_data, opzione A);
- CSV: `messaggi_errore.csv` +`DEFINIZIONE_NON_TROVATA` (507), solo append;
- pgTAP: `test-workflow-definizioni-fase0.sql` (plan 11) — suite pratiche in regressione
  verde; zero modifiche a fixture esistenti (come da raffinamento §2.1 punto 4);
- doc manuale: nuove `manual/workflow_definizioni.md`, `manual/fn_risolvi_definizione.md`,
  `manual/trgfn_tipi_prestazione_bootstrap_definizione.md`,
  `manual/trgfn_template_flussi_default_definizione.md`,
  `manual/trgfn_pratiche_default_definizione.md`; integrate `manual/pratiche.md`,
  `manual/tipi_prestazione.md`, `manual/template_flussi.md` (incluso l'asse esito
  Parte 1 e il pin); autogen rigenerata (Tid).
- Resta: commit; poi Fase 1 (§2.2).

### 2.2 Fase 1 — Pin + guard

#### D2-5 — `pratiche.fn_risolvi_definizione(p_tipo_prestazione_id, p_emittente_fiscale_id)` (`20_code/pratiche`)

1. PUBBLICATA dell'emittente, se esiste; 2. altrimenti preset PUBBLICATA
(`emittente_fiscale_id IS NULL`); 3. altrimenti raise `DEFINIZIONE_NON_TROVATA`.
Guard espliciti su parametri NULL/`<= 0`. STABLE, plpgsql.

#### D2-6 — Auto-pin alla creazione pratica (trigger BEFORE INSERT su `pratiche.pratiche`)

`trg_pratiche_a10_default_definizione_ins`: se `NEW.definizione_id IS NULL` → risolve con
D2-5 (DB-first: `create_pratica` BE resta invariato, INSERT diretto senza la colonna); se
valorizzata → guard: la definizione deve essere `PUBBLICATA` e di scope compatibile
(preset o emittente della pratica). La coerenza tipo è già garantita dalla FK composita D2-3.

#### D2-7 — Guard flusso ↔ definizione (BEFORE INSERT su `pratiche.flussi`)

`trg_flussi_a10_guard_definizione_ins`: il `template_flusso_id` deve appartenere alla
definizione pinnata dalla pratica → raise `FLUSSI_TEMPLATE_FUORI_DEFINIZIONE`.

#### D2-8 — Generazione cross-pratica definizione-aware ⚠️ (collisione non vista dai brief origine)

`pratiche.fn_genera_pratica_da_flusso` oggi inserisce il flusso iniziale della pratica figlia
con `template_flusso_dest_id` **per id** (da `pratiche.regole_generazione`). Con le
definizioni: la figlia pinna la definizione risolta per l'**emittente della pratica sorgente**
(già previsto dal brief design §3.4), ma se quell'emittente ha un fork, il template della
regola (che punta al preset) **non appartiene** alla definizione pinnata → D2-7 lo
bloccherebbe. Adeguamento richiesto:

- il template destinazione va **rimappato per `codice`** dentro la definizione pinnata della
  figlia: `SELECT tf2.id FROM template_flussi tf2 WHERE tf2.definizione_id = v_def_id AND
  tf2.codice = (codice del template della regola)`;
- se il codice non esiste nella definizione pinnata (fork che ha rimosso lo step):
  **fail-fast con errore parlante** (coerente con la filosofia dispatch in-transazione);
  se preferite skip+log, decidetelo esplicitamente e documentatelo;
- verificare le colonne di `regole_generazione`: se referenziano template di **origine** per
  id, in Fase 2 le regole entrano nel set di copia del fork (C6) con remap degli id; il lato
  **destinazione** resta risolto per codice a runtime.
- verificare anche `pratiche.fn_coda_lavoro_operatore`: se joina `template_flussi` per tipo,
  va portata sulla definizione pinnata della pratica.

#### D2-9 — Immutabilità PUBBLICATA + transizioni di stato

- Trigger sulle righe di `workflow_definizioni`: transizioni ammesse solo
  `BOZZA→PUBBLICATA` e `PUBBLICATA→RITIRATA` (raise `DEFINIZIONE_TRANSIZIONE_NON_AMMESSA`);
  header strutturale immutabile fuori da BOZZA (tipo, emittente, versione, provenance)
  → `DEFINIZIONE_PUBBLICATA_IMMUTABILE`; `descrizione`/`meta` sempre correggibili.
- Trigger su `template_flussi` **e figli** (`template_flussi_prerequisiti`,
  `template_flussi_canali`, `template_flussi_handler_eventi`, `competenze_flussi`,
  `formule_tempo`, futura whitelist C3): INSERT/UPDATE/DELETE bloccati se la definizione del
  template non è BOZZA → `DEFINIZIONE_PUBBLICATA_IMMUTABILE`; su `template_flussi` la sola
  `descrizione` resta aggiornabile (C4). ⚠️ Regola guard-restrittivo: prima di scrivere
  questi trigger, grep dei pgTAP che creano/modificano template al volo (molti test creano
  template sintetici: le fixture dovranno crearli dentro una definizione BOZZA di test o
  appoggiarsi a definizioni di test dedicate — prevedere un helper di fixture).

**Accettazione Fase 1**: pratiche nuove pinnate (auto-pin trasparente per il BE); flusso con
template fuori definizione rifiutato; definizioni pubblicate immutabili; generazione
cross-pratica funziona con remap per codice; `get_percorso_pratica` BE passato alla join per
`definizione_id` (companion §BE-2.2 — **lockstep**: da Fase 1 il percorso per tipo diventerebbe
ambiguo appena esistono due definizioni dello stesso tipo).

### 2.3 Fase 2 — Fork, versioni, pubblicazione, drift

- **D2-10 — `fn_copia_definizione(p_sorgente_id, p_emittente_dest, p_provenance boolean)`**
  (interna): copia header (BOZZA, versione calcolata) + `template_flussi` + **tutti i figli**
  con remap degli id (i prerequisiti referenziano coppie di template: rimappare entrambi i
  lati; `formule_tempo` idem; guard finale di coerenza "tutti i riferimenti dentro la nuova
  definizione"). **È l'unico punto che elenca il set di copia (C6)** — la futura whitelist
  C3 e le eventuali `regole_generazione` per-template si aggiungono qui e basta.
- **D2-11 — `fn_fork_definizione(p_definizione_id, p_emittente_fiscale_id)`**: wrapper di
  D2-10 con `preset_origine_id`/`versione_origine` valorizzati.
- **D2-12 — `fn_nuova_versione_definizione(p_definizione_id)`**: wrapper di D2-10 stesso
  scope, `versione + 1`.
- **D2-13 — `fn_pubblica_definizione(p_definizione_id)`**: valida (≥1 template attivo;
  al più un `chiude_pratica` — l'unique parziale lo garantisce già; grafo prerequisiti senza
  cicli; Inv1–Inv4 dell'asse esito valgono già riga per riga) → raise
  `DEFINIZIONE_NON_PUBBLICABILE` con motivo; in transazione: RITIRATA alla precedente
  PUBBLICATA dello scope, PUBBLICATA alla nuova.
- **D2-14 — drift**: vista `pratiche.vw_definizioni_drift` — fork il cui
  `preset_origine` ha una PUBBLICATA con `versione > versione_origine` (consumo FE banner
  DEF-2, Fase 2 BE).

**Accettazione Fase 2**: fork completo e coerente (pgTAP: conta figli sorgente = conta figli
copia, per tabella); pubblicazione atomica con ritiro della precedente; le pratiche in volo
restano sul pin; drift visibile a vista.

### 2.4 Errori nuovi Parte 2 (stesse avvertenze §1.5, id proposti)

| Codice | Id | Messaggio (con `%s`) |
| --- | --- | --- |
| `DEFINIZIONE_NON_TROVATA` | 507 | `Nessuna definizione workflow pubblicata per il tipo prestazione %s (emittente %s).` |
| `FLUSSI_TEMPLATE_FUORI_DEFINIZIONE` | 508 | `Il template flusso %s non appartiene alla definizione %s pinnata dalla pratica %s.` |
| `DEFINIZIONE_PUBBLICATA_IMMUTABILE` | 509 | `La definizione workflow %s non e' in BOZZA: struttura immutabile, creare una nuova versione.` |
| `DEFINIZIONE_TRANSIZIONE_NON_AMMESSA` | 510 | `Transizione di stato definizione non ammessa: %s -> %s.` |
| `DEFINIZIONE_NON_PUBBLICABILE` | 511 | `La definizione %s non e' pubblicabile: %s.` |

(D2-8, se sceglie fail-fast sul codice mancante nel fork, aggiunge un sesto codice, es.
`GENERAZIONE_TEMPLATE_NON_IN_DEFINIZIONE` — deciderlo insieme al meccanismo.)

### 2.5 pgTAP Parte 2 (per fase)

- Fase 0: backfill completo (nessun NULL residuo); unique nuovi attivi; smoke percorso
  PREVENTIVI invariato.
- Fase 1: risoluzione (emittente > preset > errore); auto-pin; guard flusso↔definizione;
  immutabilità (struttura bloccata, descrizione libera); transizioni stato; remap
  generazione cross-pratica (caso fork con e senza codice presente).
- Fase 2: fork/copia integrale; doppia PUBBLICATA rifiutata; pubblica→ritira atomico;
  pratiche in volo non toccate; drift.

---

## 3. Note operative trasversali

- **Numerazione Liquibase**: NN **globale per data** tra tutte le cartelle; al 2026-07-02 il
  massimo è `20260702-14` (prossimo libero: 15). Un changeSet per file, sempre
  `logicalFilePath`, `runOnChange: false` nello stato committato.
- **MAI modificare changelog mergiati** (`20260617-01/02/04`, `20260701-02/05`, ...): ogni
  modifica a funzioni/CHECK esistenti = nuovo file, corpo preso dalla **doc autogen**
  (`docs/it/dbzero/pratiche/...`), non dagli YAML.
- **Dopo l'applicazione**: rigenerare la doc autogen (tabelle/funzioni nuove e modificate) e
  aggiornare la doc manuale (`gestione-pratiche-configurazione.md`: valore DOMINIO; nuova
  sezione definizioni versionate a Fase 1/2).
- **Indici FK**: mai a mano; policy in `90_end`.
- **Coordinamento BE**: i marker dei nuovi codici (504, 507, 508, …) vanno comunicati per
  `_KNOWN_DB_ERROR_MARKERS` — le sottostringhe stabili sono già indicate nel companion; se
  cambiate un messaggio, avvisare.

## 4. Fuori scope

- Whitelist esiti-per-step L2 (design fissato da C3, attivazione al secondo bivio DOMINIO).
- UI admin definizioni (V4/V5) e catalogo preset di settore (V3) — cantieri propri.
- Fix UI/BE del percorso operatore (pre-guard parlante, esclusione DOMINIO
  dall'auto-completamento, marker): **companion BE/FE**, non qui.
- Migrazione dati `PRA-0000243`: nessuna (riga legacy fuori dal guard per costruzione).

---

*Documento unico DB: Parte 1 = invariante di classe esito per step DOMINIO (assorbe
brief-db-guard-esito-smistamento); Parte 2 = delega DB Fasi 0–2 del modello C (attua
brief-design-workflow-definizioni-versionate). Contratto C1–C6 = zero collisioni tra i due.*
