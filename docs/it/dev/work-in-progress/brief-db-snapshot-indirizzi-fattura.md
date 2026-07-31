# Brief DB — Snapshot indirizzi della fattura

> ⚠️ **REVISIONE 2026-07-30 — questo brief è SUPERATO IN PIÙ PUNTI.**
> Il documento operativo di riferimento è
> **[piano-db-satelliti-fattura.md](piano-db-satelliti-fattura.md)**: unifica
> questo brief e il fratello, riporta la verifica critica sul codice vivo
> (22 rilievi) e le decisioni chiuse da Tid il 2026-07-29/30.
> **Non lavorare da questo brief senza aver letto quel piano.**
>
> | § di qui | Cosa è cambiato | Rif. |
> |---|---|---|
> | §4 D-1 | La motivazione era **sbagliata**: i documenti fratelli **copiano** lo snapshot dal sorgente, e risolvono dall'anagrafica solo quando nascono **senza** sorgente. La decisione resta (la fattura risolve sempre dall'anagrafica) ma per un altro motivo: aggrega N sorgenti e le attività sourceless non hanno snapshot da copiare | C-1, C-14 |
> | §5.1 | La catena ha **due layer** (RUOLO → SOGGETTO), non uno; e va risolta **per istanza** (`istanza_utility_id = ba.istanza_utility_id`, fallback `IS NULL`), altrimenti è non deterministica: un soggetto può avere N indirizzi dello stesso tipo, uno per istanza. Estratta in `script.fn_resolve_indirizzo_documento` + `fn_snapshot_indirizzo_soggetto` | C-2, C-14, D-O |
> | §5.3-5.4 | Il lock è **uno solo, parametrico**, condiviso con `fatture_scadenze`. La bonifica dello storico **non si fa**: non siamo in produzione, le fatture di test si rigenerano | C-11, §3.8 del piano |
> | §5.5 | Id di seed **fissati** e coordinati col brief fratello, che rivendicava gli stessi | C-6 |
> | §7 | RLS e guard di scope emittente **non sono più «da valutare col consumer»**: entrano in Fase 1 | C-12 |
>
> **Destinatario:** team DB (`dev/db-tid`)
> **Richiedente:** BE (`dev/backend-tid`) — Tid ha approvato disegno e precedenze il 2026-07-29
> **Stato:** superato dal piano unificato (vedi sopra)
> **Vincolo:** il BE non procede fino all'apply di questo brief (regola prerequisiti DB)
> **Fratello:** [brief-db-generazione-scadenze-fattura.md](brief-db-generazione-scadenze-fattura.md) — stesso cantiere, step diverso della pipeline
> **Lavoro applicativo a valle:** [piano-be-fe-satelliti-fattura.md](piano-be-fe-satelliti-fattura.md) — include gli **smoke di accettazione** che collaudano questo brief

---

## 1. Scopo

Popolare `vendite.fatture_indirizzi` durante la pipeline di fatturazione, così
che la fattura porti lo **snapshot congelato** dei propri indirizzi e la stampa
sia **ristampa-conforme**.

## 2. Il problema: la ristampa oggi non è conforme

`vendite.fatture_indirizzi` ha **0 righe**. Le sorelle sono popolate:
`ddt_indirizzi` 16, `ordini_indirizzi` 10, `preventivi_indirizzi` 5,
`contratti_indirizzi` 1 (verificato 2026-07-29).

Poiché lo snapshot non esiste, il contesto del PDF legge l'indirizzo **live
dall'anagrafica** al momento della stampa:

- `backend/apps/vendite/db/vendite_repository.py:1564-1573` — subquery scalare su
  `anagrafiche.vw_indirizzi_resolved_ruolo` filtrata su `tipo_indirizzo_codice = 'FATT'`;
- `backend/apps/vendite/services/fattura_document_context_builder.py:206-208` —
  `"indirizzo": testata.get("cliente_indirizzo")`.

**Conseguenza:** se il cliente cambia sede dopo l'emissione, la **ristampa della
stessa fattura riporta l'indirizzo nuovo**. Su un documento fiscale già emesso e
trasmesso allo SDI è un difetto di conformità — ed è esattamente ciò che la
tabella esiste per impedire.

## 3. Cosa è già pronto (e non va toccato)

| Pezzo | Stato |
|---|---|
| `vendite.fatture_indirizzi` | ✅ **identica** alle 5 sorelle: `fattura_id`, `tipo_indirizzo_id`, `snapshot jsonb`, `origine_indirizzo_id`, `origine_soggetto_ruolo_id` + audit/`tx_id`; UNIQUE `(fattura_id, tipo_indirizzo_id)`; FK `origine_*` soft (SET NULL) |
| Trigger whitelist | ✅ `trg_fatture_indirizzi_a10_only_allowed_tipi_ins_upd` → `trgfn_tipi_indirizzi_only_allowed('FATTURE')`, fail-closed |
| Seed whitelist ambito `FATTURE` | ✅ `FATT` (marcato **obbligatorio**), `CON`, `FORNITURA`, `RES` |
| `script.fn_snapshot_indirizzo(indirizzo_id)` | ✅ agnostico al dominio, compone lo snapshot **server-side** → `(snapshot jsonb, origine_soggetto_ruolo_id)` |
| Helper obbligatorietà | ✅ `script.fn_indirizzi_obbligatori_mancanti(p_ambito, p_tipi_presenti)` già ambito-parametrico |
| FK verso `vendite.fatture` | ✅ **CASCADE** (verificato): il reset lotto pulisce senza orfani |
| BB Python upsert | ✅ `IndirizziDocumentoRepositoryMixin.upsert_indirizzo` (`ON CONFLICT DO UPDATE`), da mixare su `VenditeRepository` |
| BB frontend | ✅ `DocumentoIndirizziSection` / `DocumentoIndirizziDrawer` (montati su 5 drawer) |

Il guard di obbligatorietà **è deliberatamente spento**: il brief
`work-done/brief-db-indirizzi-documenti-simmetria-e-cascata.md:29-33` lo dichiara
esplicitamente — accenderlo prima che qualcuno popoli la tabella
**bloccherebbe la pipeline di fatturazione**. «Si accende con quella cascata»:
questo brief è quella cascata.

---

## 4. Decisioni prese (Tid, 2026-07-29)

| # | Decisione |
|---|---|
| D-1 | La fattura **applica la stessa cascata** degli altri documenti, cioè risolve gli indirizzi **dall'anagrafica del cliente del billing account**. **NON** copia gli indirizzi dai documenti sorgente (ordine/preventivo sono esempi di chi ha già fatto quella risoluzione, non fonti da cui leggere). Se l'indirizzo non è risolvibile → **errore** |
| D-2 | Tipi da snapshottare: **tutti e quattro** quelli in whitelist per l'ambito `FATTURE` — `FATT`, `CON`, `FORNITURA`, `RES`. **Solo `FATT` è obbligatorio**; per gli altri tre, se l'indirizzo non esiste **si procede senza errore** |
| D-3 | Il task va nello step **DRAFT**, dopo `generate_fatture_righe` (non dipende dai totali) |

> ⚠️ **Rev. 2026-07-30 — la motivazione qui sotto è sbagliata nei fatti.**
> I documenti fratelli **non** risolvono dall'anagrafica alla loro creazione:
> **copiano 1:1 lo snapshot del documento sorgente** (`fn_push_preventivo_a_ordine`
> §4-bis, `fn_genera_ddt_da_ordine`, `fn_push_offerta_a_contratto`). Risolvono
> dall'anagrafica **solo quando nascono senza sorgente**, e per via di un helper
> Python **best-effort** che riempie **un solo slot**.
> La **decisione resta valida** — la fattura risolve sempre dall'anagrafica — ma
> il motivo è un altro: la fattura aggrega N sorgenti, e le attività *sourceless*
> (oneri di commessa, consumi) **non hanno alcuno snapshot da copiare**. È
> l'unica regola che copre tutti i casi. Conseguenza da accettare
> esplicitamente: la fattura può stampare un indirizzo **diverso** da quello del
> DDT/ordine che sta fatturando. Rif. C-1 e C-14 del piano.

### Perché non serve nessuna regola di conflitto (D-1)

Una prima stesura di questo brief prevedeva una cascata documentale con regola di
precedenza fra sorgenti divergenti. **Era sbagliata**: la chiave di aggregazione
della fattura (`vendite.fn_build_fattura_key`) **include `billing_account_id`**,
quindi una fattura ha per costruzione **un solo billing account → un solo cliente
→ un solo indirizzo di fatturazione**. Indirizzi divergenti nella stessa fattura
non sono improbabili: sono **impossibili**.

Il numero di attività aggregate e di documenti sorgente coinvolti è quindi
**irrilevante** per gli indirizzi. Non serve leggere i sorgenti, non serve una
regola di conflitto, non serve il puntatore al documento sorgente (che
`fn_get_or_create_fattura_header` non popola).

L'invariante che regge tutto questo è **documentato e presidiato da vincoli DB**,
non una convenzione — vedi la guida
[gestione-delle-istanze-utility](../../guide/gestione-delle-istanze-utility.md)
§«Istanza e billing account: relazione 1:1 per utility»:

- `billing_account.istanza_utility_id` è **FK singola NOT NULL** → ogni BA punta
  a **una sola** istanza;
- `UNIQUE (istanza_utility_id, utility_id)` su `billing_account` → per una coppia
  (istanza, utility) esiste **al massimo un** BA;
- `UNIQUE` su `clienti.istanza_utility_id` (`uq_clienti_istanza_utility`) →
  un'istanza ospita **al massimo un cliente**.

Catena rigida: **1 BA → 1 istanza → 1 cliente**. Confermato anche dai dati
(21 BA / 21 istanze / 21 clienti, 2026-07-29).

### Perché DRAFT (D-3)

Lo snapshot richiede solo la testata, che a quel punto esiste. Diversamente dalle
scadenze — che devono attendere i totali dello step EMESSA — qui non c'è
dipendenza: prima si scrive, prima ogni uscita (video, PDF, SDI) vede lo stesso
documento.

---

## 5. Cosa serve al DB

### 5.1 Funzione madre

Proposta: **`vendite.fn_snapshot_indirizzi_fattura(p_fattura_id bigint)`**
→ `RETURNS TABLE(inserted_rows int, updated_rows int)`
più il wrapper di lotto **`vendite.fn_snapshot_indirizzi_lotto(p_lotto_id bigint, p_batch_size int DEFAULT 1000)`**
→ `RETURNS TABLE(fatture_count int, inserted_rows int, updated_rows int)`.

Stessa coppia (per-fattura + wrapper batched) di
`fn_ricalcola_riepilogo_iva_fattura` / `fn_ricalcola_riepiloghi_iva_lotto`: il BE
clona handler e wrapper senza inventare nulla.

**Per ciascuno dei quattro tipi di D-2**, due passi soli:

> ⚠️ **Rev. 2026-07-30 — il Passo 1 qui sotto è incompleto su due fronti.**
>
> **(a) La catena ha due layer, non uno.** Oltre a
> `vw_indirizzi_resolved_ruolo` esiste il layer **SOGGETTO**
> (`vw_indirizzi_resolved_soggetto`), che il helper Python interroga come
> fallback. Guardando solo il primo, un cliente il cui `FATT` vive sul layer
> soggetto farebbe **fallire la fattura** con `E_INDIRIZZO_FATTURA_MANCANTE`
> — mentre il suo ordine si era risolto benissimo.
>
> **(b) Va risolto per ISTANZA.** `anagrafiche.indirizzi` ha due unique
> parziali — `(ruolo, istanza, tipo)` e `(ruolo, tipo) WHERE istanza IS NULL` —
> quindi **un soggetto_ruolo può avere N indirizzi dello stesso tipo**, uno per
> istanza utility più uno generico. Risolvere per `(ruolo, tipo)` e basta è
> **non deterministico**. Regola: precedenza a
> `istanza_utility_id = ba.istanza_utility_id`, fallback `IS NULL`.
> *(Il codice esistente ha lo stesso difetto: ordina `istanza_utility_id NULLS
> FIRST LIMIT 1`, cioè preferisce il generico e ignora l'istanza del documento.)*
>
> **Realizzazione (piano, Fase 2.0):** `script.fn_snapshot_indirizzo_soggetto`
> (gemella di `fn_snapshot_indirizzo` per il layer che non ha `indirizzo_id`) +
> `script.fn_resolve_indirizzo_documento(ruolo, istanza, tipo)` come **unica**
> implementazione della catena, riusata poi dal mixin Python.
> Rif. C-2, C-14, D-O del piano.

**Passo 1 — risoluzione dall'anagrafica del cliente.**
Risolve l'indirizzo del tipo richiesto sul `soggetto_ruolo` del cliente della
fattura (via `billing_account_id` → `ba.soggetto_ruolo_id`), usando le viste
`anagrafiche.vw_indirizzi_resolved_ruolo` / `_soggetto` come fanno gli altri
domini, e compone lo snapshot con **`script.fn_snapshot_indirizzo`** (mai a mano:
D-5 del design-of-record).

È **la stessa cascata** che gli altri documenti applicano alla loro creazione: la
fattura non è un caso speciale, è solo l'ultimo anello che non la eseguiva.

**Passo 2 — indirizzo non risolvibile.**

| Tipo | Comportamento |
| --- | --- |
| **`FATT`** (obbligatorio nel seed) | **errore** `E_INDIRIZZO_FATTURA_MANCANTE` — la fattura non è emettibile senza indirizzo di fatturazione |
| `CON`, `FORNITURA`, `RES` (opzionali) | nessuna riga, **nessun errore**: si procede |

L'errore va emesso con scope **FATTURA** (`vendite.fatture_log`), non lotto: il
giro prosegue sulle altre fatture e l'operatore vede esattamente quali sono
bloccate e perché. La severità critica blocca poi l'avanzamento del lotto
attraverso il meccanismo esistente (`fn_log_lotto_esito_fatture`).

### 5.2 Idempotenza

`ON CONFLICT (fattura_id, tipo_indirizzo_id) DO UPDATE SET snapshot = EXCLUDED.snapshot,
origine_indirizzo_id = EXCLUDED.origine_indirizzo_id,
origine_soggetto_ruolo_id = EXCLUDED.origine_soggetto_ruolo_id`
— è il pattern del BB Python e l'esempio canonico della doc concettuale della
tabella. Il task è così rieseguibile (il reset di un lotto a DRAFT rigenera).

⚠️ **Ma attenzione all'interazione col congelamento** (§5.4): dopo l'emissione
l'`UPDATE` dello snapshot **non deve più poter avvenire**, altrimenti una
rigenerazione riscriverebbe l'indirizzo di una fattura già emessa — cioè
esattamente il difetto che stiamo chiudendo. L'upsert è idempotente **finché la
fattura è editabile**.

### 5.3 Accensione del guard di obbligatorietà

Una volta che il task popola la tabella, va agganciato il guard che pretende
`FATT` all'emissione, sul modello **esatto** del DDT
(`trg_ddt_a10_guard_indirizzi_obbligatori_upd` → `trgfn_ddt_guard_indirizzi_obbligatori`
→ `script.fn_check_ddt_emittibile` → `script.fn_indirizzi_obbligatori_mancanti`).
L'helper è già ambito-parametrico: serve il trigger su `vendite.fatture` per
l'ambito `FATTURE`, ~~con errore `E_INDIRIZZO_DOC_OBBLIGATORIO`~~ — **entrambe
queste due frasi sono state superate: vedi la rev. 2026-07-31 qui sotto.**

⚠️ **Ordine di accensione, non negoziabile**: prima il task che popola, poi il
guard. Invertirli blocca la fatturazione. ~~Con dati storici privi di snapshot
(le 7 fatture attuali) va valutata una bonifica o l'accensione limitata alle
fatture nuove.~~

> ⚠️ **Rev. 2026-07-30 — la bonifica non si fa.** Non siamo in produzione: le 7
> fatture sono dati di test e **si cancellano e rigenerano**. Niente accensione
> graduale, niente migration di bonifica, e — nel piano BE/FE — niente fallback
> «transitorio» del context builder. Rif. §3.8 del piano.

<!-- separatore: due revisioni distinte, non un unico blockquote -->

> ✅ **Rev. 2026-07-31 — fatto, ma con due scostamenti da questo paragrafo.**
> Il guard è applicato e verde: `vendite.trgfn_fatture_guard_uscita_draft`
> (changeSet `20260731-11` funzione, `20260731-12` montaggio), pgTAP
> `test-fattura-guard-uscita-draft-v1.sql` `plan(11)`.
>
> 🔴 **1. Il codice errore non è `E_INDIRIZZO_DOC_OBBLIGATORIO`.** È
> **`E_FATTURA_NON_EMETTIBILE_INCOMPLETA`** (id 575), da registrare in
> `error_policies.py`. Il motivo è che nel frattempo il criterio si è allargato:
> il brief intestazione §3.5 ha stabilito che una fattura non lascia `DRAFT`
> senza **anche** l'intestazione fiscale congelata delle due parti
> (`emittente_snapshot`, `cliente_snapshot`). Segnalare una `cliente_snapshot`
> mancante con un codice che dice «indirizzo obbligatorio mancante» direbbe una
> cosa **falsa**, non solo imprecisa, e manderebbe a cercare un indirizzo che
> c'è. Il dettaglio di cosa manca sta nel messaggio e nel payload
> (`indirizzi_mancanti`, `intestazione_mancante`), non in codici distinti: chi
> riceve l'errore fa comunque la stessa cosa, cioè rieseguire lo step DRAFT.
> Razionale completo in `brief-db-snapshot-intestazione-fattura.md` §10.9.
>
> **2. Non è «il modello esatto del DDT».** La catena del DDT passa da
> `script.fn_check_ddt_emittibile` perché quella lista ha **due** lettori — i
> guard e `fn_available_actions_ddt`, che ne fa il «disabled + reason» della UI.
> Per la fattura il secondo lettore non esiste: lo stato lo muove la pipeline,
> non un pulsante. La logica sta quindi dentro il trigger, e si estrarrà in una
> `fn_check_*` pura quando arriverà il secondo consumatore — che è esattamente
> come ci è arrivato il DDT (delega introdotta il 2026-07-19, **dopo** i guard).
> Il building block condiviso resta `script.fn_indirizzi_obbligatori_mancanti`,
> chiamato direttamente: gli indirizzi obbligatori restano data-driven dalla
> matrice, non da un `FATT` cablato.

### 5.4 Lock post-emissione

Come per le scadenze (D-5 del brief fratello), `fatture_indirizzi` **non ha** un
guard di congelamento. Serve un trigger `_a10_` che blocchi INSERT/UPDATE/DELETE
quando la fattura è oltre EMESSA, con il **bypass per il percorso di reset**
(GUC `zeroerp.maintenance_reset_lotto_draft`), sul modello di
`trgfn_fatture_righe_guard_congelamento`.

Senza questo lock lo «snapshot congelato» resta una promessa non presidiata.

### 5.5 Seed: registrazione del task

Solo append a CSV esistenti.

> ⚠️ **Rev. 2026-07-30 — collisione di id col brief fratello.** Entrambi i brief
> rivendicavano «ultimo id occupato: 18» sul registry e «16» sulla task_policy.
> Allocazione **fissata** nel piano (§3.1): indirizzi → registry **19**, impl
> **19**, policy **17** (pipeline 1) e **18** (pipeline 8); scadenze → registry
> **20**, impl **20**, policy **19-23**. Rif. C-6.

| File | Riga |
|---|---|
| `80_data/sql/dbops/pipeline_task_registry.csv` | task `snapshot_indirizzi_lotto`, `dominio_id = 1` — ultimo id occupato: 18 |
| `80_data/sql/dbops/pipeline_task_registry_impl.csv` | `default` → `snapshot_indirizzi_lotto_default`, `is_default = true` |
| `80_data/sql/vendite/fatturazione_pipeline.csv` | append a `processi` dello step **DRAFT** — righe **id 1 (MASSIVO)** e **id 8 (GIORNALIERO)**, dopo `generate_fatture_righe`: `{"task":"snapshot_indirizzi_lotto","fase":"Snapshot indirizzi fattura","params":{"implementation_key":"default","batch_size":1000}}` |
| `80_data/sql/vendite/fatturazione_pipeline_task_policy.csv` | una riga per pipeline_id (1 e 8): `annullabile = t`, `resume_mode = RESUME_STEP` — ultimo id: 16 |

Nota: lo step DRAFT è presente e popolato in **entrambe** le corsie, quindi qui
il problema della corsia GIORNALIERO vuota (§4.8 del brief fratello) **non si
presenta**.

---

## 6. Test pgTAP attesi

1. Passo 1: cliente con indirizzo `FATT` in anagrafica → snapshot scritto, shape
   canonico (`intestazione, via, cap, citta, prov, stato, display`),
   `origine_indirizzo_id` valorizzato.
2. Fattura che aggrega attività da **più documenti sorgente diversi** → un solo
   indirizzo `FATT`, quello del cliente del BA: il numero di sorgenti **non
   influenza** il risultato (è l'invariante «1 fattura = 1 BA = 1 cliente»).
3. Passo 2: cliente senza indirizzo `FATT` risolvibile →
   `E_INDIRIZZO_FATTURA_MANCANTE`, **zero righe** scritte, log scope FATTURA;
   nessun errore per `CON`/`FORNITURA` assenti.
4. Whitelist: tentativo di scrivere un tipo non ammesso per `FATTURE` (es. `SEDELEG`)
   → `E_TIPO_INDIRIZZO` dal trigger esistente.
5. Idempotenza: doppia esecuzione → stesso risultato, nessun duplicato
   (UNIQUE uno-per-tipo rispettato), `updated_rows` coerente.
6. Guard §5.3: emissione di fattura senza `FATT` → ~~`E_INDIRIZZO_DOC_OBBLIGATORIO`~~
   **`E_FATTURA_NON_EMETTIBILE_INCOMPLETA`** (rev. 2026-07-31, vedi §5.3); con
   `FATT` → passa **solo se anche l'intestazione è congelata**, perché il
   criterio è allargato. Coperto da
   `db/pgtap/vendite/test-fattura-guard-uscita-draft-v1.sql`, che prova le due
   metà **separatamente**: senza nulla, con il solo indirizzo, e con
   l'intestazione a `{}` invece che NULL.
7. Lock §5.4: scrittura su fattura oltre EMESSA → errore; percorso reset → ammesso.
8. Seed: presenza e posizione del task in `processi` di **entrambe** le corsie
   DRAFT + presenza delle task_policy.

---

## 7. Cosa fa il BE dopo l'apply

1. **mixare** `IndirizziDocumentoRepositoryMixin` su `VenditeRepository`
   (`_indirizzi_table="vendite.fatture_indirizzi"`, `_indirizzi_fk_documento="fattura_id"`,
   `_indirizzi_ambito="FATTURE"`, `_indirizzi_documento_table="vendite.fatture"`,
   `_indirizzi_doc_sr_column=None` → risoluzione via billing account, come
   preventivi/offerte/contratti);
2. handler `_handle_snapshot_indirizzi_lotto_task` + entry nel `handler_registry`,
   wrapper `run_snapshot_indirizzi_lotto_task` nel repository, voce in
   `ALLOWED_TASK_FUNCTIONS`;
3. **passare il PDF allo snapshot**: `FatturaDocumentContextBuilder` deve leggere
   `fatture_indirizzi` invece della vista live (`vendite_repository.py:1564-1573`)
   — è il punto che rende la ristampa conforme. Modello già fatto:
   `DdtDocumentContextBuilder` è l'unico context builder v2 che legge gli
   snapshot;
4. **endpoint di gestione** (opzionale, da decidere): la factory
   `build_indirizzi_documento_views` è pronta, ma il service BB presuppone un
   documento editabile → servirebbe `stati_modificabili = {"DRAFT"}` e un
   lettore di stato (`get_stato_codice` **assente** su `VenditeRepository`).
   Se si vuole che l'operatore possa correggere un indirizzo su fattura DRAFT, va
   cablato; se la fattura resta sola-lettura, si omette e la tabella è scritta
   solo dalla pipeline;
5. FE: montare `DocumentoIndirizziSection` sul `FatturaDrawer` **solo** se si fa
   il punto 4 (in sola lettura basta esporre gli indirizzi nel dettaglio).

> ⚠️ **Rev. 2026-07-30 — non è più «da valutare col consumer».** `fatture_indirizzi`
> è l'**unica** satellite senza né RLS né guard di scope emittente
> (`fatture_scadenze` ha entrambi; `fatture_righe` e `fatture_riepiloghi_iva`
> hanno le policy dal 2026-07-29). La simmetria costa poco ed entra in **Fase 1**
> del piano, non quando il consumer sarà già scritto. Rif. C-12.

⚠️ **Vincolo RLS da rispettare**: `vendite.fatture_indirizzi` **non ha policy
RLS** (a differenza di `fatture`, `fatture_righe`, `fatture_riepiloghi_iva`,
`fatture_scadenze`). Se il dettaglio fattura inizierà a leggerla, la protezione
dipende **interamente** dall'ordine «testata prima → 404» già presidiato in
`get_fattura_dettaglio` e dal suo test. Da valutare se estendere le policy
satelliti (cfr. `work-done/brief-db-rls-satelliti-fattura-portale.md`, che le
aveva lasciate fuori in attesa di un consumer).

---

## 8. Fuori scope

- Endpoint e UI di gestione indirizzi fattura (punto 4 sopra, da decidere).
- Policy RLS su `fatture_indirizzi` (da valutare col consumer).
- Rollout degli snapshot negli altri 4 context builder PDF (preventivo, ordine,
  offerta, contratto): nota aperta del design-of-record, indipendente da qui.
