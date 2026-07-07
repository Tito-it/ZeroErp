# Brief DB — GUIDA (D4): avanzamento milestone su esito proiettato

> **Tipo**: brief DB (spec per il team DB, ramo `dev/db-tid`) · **Data**: 2026-07-06 · **Owner**: Tid
> **Design-of-record**: [brief-design-guida-avanza-esito-proiettato.md](brief-design-guida-avanza-esito-proiettato.md)
> (decisioni adottate §11). **Prerequisito MOSTRA** (D1-D3) già in produzione per PREVENTIVI.
> **Gate implementazione**: dopo validazione E2E in-app di MOSTRA (non blocca il lavoro DB di design/seed su PREVENTIVI).
>
> Il team DB possiede la **DDL esatta** (nomi, tipi, indici, trigger, pgTAP). Questo brief fissa
> **semantica, invarianti e criteri d'accettazione**, non la forma fisica. **Additivo e per-dominio**:
> senza config, comportamento di oggi (nessun avanzamento automatico).

---

## Decisioni adottate (review DB 2026-07-06)

Chiusura dei punti aperti dopo verifica contro il DB vivo (doc auto-gen) e il codice BE.
Queste decisioni **vincolano** i deliverable sotto.

- **D-B4 — Contesto di scrittura → `SECURITY INVOKER` (nessun contesto SISTEMA).**
  `pratiche.flussi` e `pratiche.giornale` **non hanno RLS** (la RLS operatori è solo sui
  documenti, via `script.trgfn_guard_emittente_scope`). Il reconcile gira nella transazione
  dell'operatore che ha **già** superato il guard di scope sul documento → la pratica è del
  suo stesso emittente. Quindi `fn_reconcile_sorgente` è **INVOKER** (come `fn_stato_sorgente`
  / `fn_log_evento_dominio`, già INVOKER): niente `SECURITY DEFINER`, niente ruolo `BYPASSRLS`,
  niente GUC di sistema, niente "identità di sistema". L'`user_insert/user_update` sul flusso
  resta **l'operatore** (è lui che ha innescato l'avanzamento — audit veritiero). L'apparato
  DEFINER/SISTEMA si riprende **solo se** un domani una tabella `pratiche.*` prende la RLS
  (allora ci si allinea al pattern batch: owner/superuser, non a `system_process_context` BE).
- **D-B2 — Completamento a due salti (no modifica matrice).** La matrice
  `transizioni_stati_flussi_pratiche` **non** ha `DA_ESEGUIRE→COMPLETATO` diretta
  (`trgfn_flussi_guard_transizione` la rifiuta): il BE passa sempre da `IN_CORSO`
  (`avvia_e_completa`). `fn_reconcile_sorgente` **replica la stessa logica** di
  `completa_step_pratica`: se `DA_ESEGUIRE` → due UPDATE (`→IN_CORSO`, poi `→COMPLETATO`);
  se `IN_CORSO` → un solo UPDATE. **Non** si aggiunge la 1→3 alla matrice (sarebbe un cambio
  globale per un caso locale).
- **D-B3 — Binding G2 solo su step non-DOMINIO.** `trgfn_flussi_guard_esito_classe` impone:
  step **non-DOMINIO** → esito **verdetto** (`is_verdetto=true`); step **DOMINIO** → esito di
  **ramo** (`is_verdetto=false`). L'esito proiettato (`fn_stato_sorgente.esito`) è **sempre un
  verdetto** o NULL → è ammesso **solo su step non-DOMINIO**. Il binding G2 è quindi consentito
  **solo** su step non-DOMINIO (regola nel guard di mutua-esclusione, vedi G2-guard).
  *Nota*: i **prerequisiti** non c'entrano — `trgfn_flussi_guard_prerequisiti` scatta **solo
  in INSERT** (istanziazione del flusso), **non** al completamento: l'UPDATE del reconcile non
  li ri-controlla.
- **D-giornale — Traccia automatica sufficiente.** Il cambio-stato del flusso è già giornalato
  da `trgfn_flussi_giornale_stato` col contesto operatore → **non** si aggiunge un evento
  `DOMINIO_*` dedicato per l'avanzamento (se in E2E servisse la semantica "avanzato per
  proiezione", si aggiunge via `fn_log_evento_dominio` ma con **origine dedicata**: oggi è
  cablata `'HANDLER'`).

---

## Stato implementazione DB (2026-07-06) — ✅ SCRITTO + TESTATO (dev), non committato

Deliverable realizzati come changeSet Liquibase `20260706-16..24` (+ pgTAP), applicati e
verdi in dev; **non committati** (attendere «procedi»); doc auto-gen dbzero da rigenerare (Tid).

| # | Deliverable | ChangeSet | Stato |
|---|---|---|---|
| G1 | Colonna `template_flussi.attende_sorgente_tipo_id` | `20260706-16` | ✅ |
| G2 | Tabella `template_flussi_avanzamento_proiezione` | `20260706-17` | ✅ |
| G5 | Tabella osservabilità `reconcile_errori` (D-B7) | `20260706-18` | ✅ |
| G3a | `fn_reconcile_sorgente` (INVOKER, due-salti, tie-break, idempotente) | `20260706-19` | ✅ |
| G3b | `trgfn_documento_reconcile_proiezione` (generica, best-effort, arg espliciti) | `20260706-20` | ✅ |
| G2-guard | non-DOMINIO (D-B3) + mutua esclusione tra binding **attivi** (D-B10); codici errore **517/518** | `20260706-21` | ✅ |
| G1/G2-copia | `fn_copia_definizione` propaga colonna + 8° figlio (D-B8) | `20260706-22` | ✅ |
| G3b-pilota | Trigger su `vendite.preventivi` (dormiente senza binding) | `20260706-23` | ✅ |
| **Cutover** | Disattiva handler `accetta_preventivo` + G1/G2 su step live **9011** (tipo 9004) | `20260706-24` | ✅ scritto — **coordinare col BE** (§4) |
| G4 | Indice `((uid::text))` — **già presente** per PREVENTIVI (`ix_preventivi_uid_text`) | — | ✅ n/d |

**pgTAP**: [test-guida-avanza-esito-proiettato.sql](../../../../db/pgtap/pratiche/test-guida-avanza-esito-proiettato.sql)
— `plan(18)` **verde** (18/18): copre struttura, i guard config-time (CHECK/non-DOMINIO/mutua
esclusione), standalone→avanza E2E via trigger (due-salti), no-verdetto→no-op, additività,
idempotenza, tie-break + osservabilità, copia edizione (G1+G2).

**Note d'implementazione emerse**:
- Tipo prestazione live = **PREVENTIVI (9004)**, step milestone `APPROVAZIONE_CLIENTE` = **9011**
  (i tipi 9002/9003 IMMEDIATA/DIFFERITA sono `obsoleto_dal` 2026-06-30, restano su handler).
- Il cutover è **atomico e ordinato**: disattiva l'handler *prima* di inserire il binding G2, così
  la mutua-esclusione (che considera solo i binding **attivi**) non lo rifiuta.
- Contesto **INVOKER** confermato adeguato: `pratiche.flussi`/`giornale` senza RLS.

**Documentazione (2026-07-06)**:
- **Manual companion** creati/aggiornati in `docs/it/dbzero/pratiche/manual/`:
  `template_flussi_avanzamento_proiezione`, `reconcile_errori`, `fn_reconcile_sorgente`,
  `trgfn_documento_reconcile_proiezione`, `trgfn_tfap_guard_compatibilita`,
  `trgfn_tfhe_guard_no_proiezione` (+ note su `template_flussi` e `fn_copia_definizione`).
  *(Gli auto-gen dbzero li rigenera Tid; i manual sono già pronti da includere.)*
- **Guida concettuale**: nuova sezione «Avanzamento su esito proiettato (GUIDA)» in
  `docs/it/guide/gestione-pratiche.md` (projection-driven vs handler-driven).

---

## 0. Scopo in una riga

Quando un **documento** raggiunge un **verdetto proiettato** (`fn_stato_sorgente.esito` non-null,
un `is_verdetto=true`), il **milestone** della pratica che *attende* quel documento deve
**avanzare automaticamente** — su **qualsiasi** percorso di scrittura (BE, batch, SQL diretto e
soprattutto **standalone**). Generalizza e **rimpiazza** l'handler per-dominio
`vendita.accetta_preventivo`.

## 1. Contesto (cosa esiste già — non ricrearlo)

- `pratiche.fn_stato_sorgente(sorgente_tipo_id, sorgente_uid)` → descrittore normalizzato
  (`risolto, fase, esito, terminale, …`); `esito` è **sempre** un verdetto (`is_verdetto=true`) o NULL.
- `script.vw_pratica_doc_sorgente` → àncora pratica-level (accende anche i COLLEGATO con
  `flusso_id` NULL).
- `pratiche.pratiche_sorgenti(pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link, flusso_id, …)`
  → link pratica↔documento.
- `config.sorgenti(id, target_table regclass, key_selector 'id'|'uid', …)` → registry dei tipi
  sorgente (polimorfismo per la risoluzione dell'uid).
- Avanzamento flusso: la primitiva applicativa è `completa_step_pratica(pratica_id, template_codice,
  esito, user)` (idempotente sui flussi terminali). Il completamento fa `UPDATE pratiche.flussi
  SET stato_id=…(COMPLETATO), esito=…` che **già** fa scattare il trigger DB
  `trgfn_flussi_generazione` (generazione a valle). **Nota**: l'avanzamento GUIDA gira **DB-side**
  → deve replicare lo stesso effetto (transizione a COMPLETATO con l'esito), così la generazione
  a valle scatta come sempre.
- Vocabolario esito: `config.esiti_flussi_pratiche`. Il `esito_richiesto` dei binding e il `esito`
  proiettato sono **entrambi** ristretti ai 4 verdetti → match omogeneo.

## 2. Deliverable

### G1 — Mappa step → sorgente attesa
**Cosa**: dichiarare, sul **template step** (`pratiche.template_flussi`, versionato per definizione),
quale **tipo sorgente** quel milestone attende. Additiva.
- Semantica: `attende_sorgente_tipo_id` (FK → `config.sorgenti.id`, **nullable**; NULL = milestone
  non projection-driven → comportamento di oggi).
- **Deve essere copiata** da `fn_copia_definizione` (fork / nuova-versione): è config di step,
  segue l'edizione. **Deliverable duro, non "verifica"**: `fn_copia_definizione` copia con
  **lista colonne esplicita** (non `SELECT *`) → la nuova colonna va aggiunta a **entrambe** le
  liste (INSERT + SELECT) del blocco `template_flussi`. `CREATE OR REPLACE` (ritorna `integer`,
  no `RETURNS TABLE` → niente DROP), in un nuovo file con numerazione successiva.
- Risolve l'ambiguità "quale documento per quale step" anche per i COLLEGATO con `flusso_id` NULL
  (l'àncora per-flusso non basta; la mappa step→sorgente + `vw_pratica_doc_sorgente` sì).

### G2 — Binding di avanzamento *(dedicato, leggero)*
**Cosa**: dichiarare *quando* il milestone avanza sul verdetto proiettato. **Dedicato** (separato
da `template_flussi_handler_eventi`: semantica diversa, non sovraccaricare `chk_tfhe_evento`).
- Semantica minima per riga: `(template_flusso_id, esito_richiesto)` con
  **`esito_richiesto` nullable = "qualsiasi verdetto"**; l'esito di **completamento** del milestone
  = **il verdetto proiettato** (mappatura 1:1, i vocabolari coincidono → nessun remap).
- `esito_richiesto` (se valorizzato) ∈ 4 verdetti (stesso CHECK di `chk_flussi_esito`).
- **Additiva**: senza binding, nessun avanzamento automatico.
- **Copia edizione**: se G2 è **tabella dedicata**, `fn_copia_definizione` va estesa con un
  **blocco di copia figli aggiuntivo** (come i 6 esistenti, es. `template_flussi_handler_eventi`),
  altrimenti il binding non segue fork/nuova-versione. Se invece G1+G2 collassano in colonne su
  `template_flussi`, basta l'edit di G1.
- *(Il team valuti se G1+G2 collassano in poche colonne su `template_flussi` o in una tabellina
  dedicata `pratiche.template_flussi_avanzamento_proiezione`; la semantica sopra è vincolante,
  la forma fisica no.)*

**G2-guard — mutua esclusione (config-time)** *(nuovo, da D-B3/D-B10)*: uno step o è
**projection-driven** (ha binding G2) o è **handler-driven sul COMPLETATO** (ha
`template_flussi_handler_eventi` `evento='COMPLETATO'`), **mai entrambi** — altrimenti
l'avanzamento standalone (DB) completa il flusso ma **salta l'handler Python**, perdendo
l'azione di dominio in silenzio (la divergenza che GUIDA vuole eliminare). Inoltre il binding
G2 è ammesso **solo su step non-DOMINIO** (l'esito proiettato è un verdetto → lo step DOMINIO,
che vuole esiti di ramo, lo rifiuterebbe via `trgfn_flussi_guard_esito_classe`). `fn_guard_*`
config-time + pgTAP.

### G3 — Detection (trigger generico) + riconciliazione `fn_reconcile_sorgente`
**G3a — `pratiche.fn_reconcile_sorgente(sorgente_tipo_id bigint, sorgente_uid text)`**
(**`SECURITY INVOKER`** — vedi D-B4):
1. `d := fn_stato_sorgente(tipo, uid)`; se `d.esito IS NULL` (nessun verdetto) → esci (no-op).
2. Trova le `pratiche_sorgenti` agganciate a `(tipo, uid)`.
3. Per ciascuna pratica, trova i suoi flussi il cui **template step** ha `attende_sorgente_tipo_id
   = tipo` (G1) **e** un binding G2 con `esito_richiesto IS NULL OR = d.esito`.
   **Tie-break multi-istanza (D-B5)**: quando `pratiche_sorgenti.flusso_id` è valorizzato, agire
   **su quel flusso** (link esplicito documento↔milestone); con `flusso_id` NULL (COLLEGATO)
   agire sui milestone del tipo **solo se univoci** nella pratica, altrimenti **loggare-e-non-avanzare**
   (evita di completare il milestone sbagliato quando la pratica ha più documenti dello stesso tipo).
4. Per quei flussi **non terminali** (il filtro `stato NOT IN {COMPLETATO,ANNULLATO}` **è** la
   garanzia di idempotenza — D-B11), portarli a **COMPLETATO con `esito = d.esito`** **a due
   salti** (D-B2): se `DA_ESEGUIRE` → `→IN_CORSO` poi `→COMPLETATO`; se `IN_CORSO` → un solo
   UPDATE. Replica esatta della logica di `completa_step_pratica` (che è BE, non richiamabile da
   DB) → fa scattare `trgfn_flussi_generazione` come il completamento manuale.
5. **Giornale**: il cambio-stato del flusso è **già** giornalato in automatico da
   `trgfn_flussi_giornale_stato` (contesto operatore) → **nessuna scrittura `DOMINIO_*` dedicata**
   (D-giornale). Del "frammento condiviso" (debito §5.3) al reconcile serve **solo** la risoluzione
   ROOT/sorgenti (la scrittura giornale è già coperta; `fn_log_evento_dominio` esiste già DB-side
   se in futuro servisse un evento esplicito, con **origine dedicata** ≠ `'HANDLER'`).
- **Contesto (D-B4)**: `INVOKER`. `pratiche.flussi`/`pratiche.giornale` non hanno RLS; il reconcile
  gira nella transazione dell'operatore che ha già superato il guard di scope sul documento →
  audit veritiero (l'operatore che ha accettato è chi ha innescato l'avanzamento). Nessun
  `system_process_context`.

**G3b — Trigger DB generico** sulla **colonna-stato** delle tabelle documento (per-dominio, seed):
- Fa scattare `fn_reconcile_sorgente(tipo, uid)` **dopo** un cambio-stato del documento
  (AFTER UPDATE OF <colonna_stato>). Generico e parametrico (stile `dbops.trgfn_*`).
  **Parametrizzazione esplicita (D-B9)**: seminare il trigger con `sorgente_tipo_id` **esplicito**
  come argomento (+ nome colonna-chiave `id`|`uid`), **non** risolverlo a runtime da
  `config.sorgenti.target_table` — una stessa `target_table` può avere **più righe** in
  `config.sorgenti` (per `scope`/`tipo_doc_fiscale_id`) → reverse-lookup ambiguo. L'argomento
  esplicito è univoco e coerente col pattern parametrico `dbops.trgfn_*`.
- **Best-effort — vincolo critico**: il documento è **sovrano**. La logica di reconcile deve
  essere racchiusa in un **blocco eccezioni interno** (`BEGIN … EXCEPTION WHEN OTHERS THEN
  <log>; END`) così che **un errore lato pratiche non propaghi mai** e **non faccia rollback** del
  cambio-stato del documento.
- **Osservabilità (D-B7)**: il best-effort inghiotte **ogni** errore (inclusi bug) → il milestone
  "semplicemente non avanza" in silenzio. Serve una **superficie osservabile**: log del fallimento
  su tabella dedicata `pratiche.reconcile_errori` (o registry errori dbops) con `(tipo, uid,
  pratica_id, errcode, messaggio, tx_id)` + vista di consultazione. È **deliverable** (vedi G5),
  non nota.
- **Cascata (D-B6)**: il completamento del flusso fa girare `trgfn_flussi_generazione` (generazione
  a valle) **dentro la transazione del cambio-stato documento**. Se la generazione tocca lo stato di
  un altro documento → altro trigger → altro reconcile. Bound esplicito: la catena termina quando
  non c'è binding G2 che matcha; verificare in pgTAP che non si inneschi ricorsione non terminante
  e valutare il footprint lock (un cambio-stato documento ora porta con sé milestone + generazione).
- **Pilota**: **PREVENTIVI** (`vendite.preventivi`, ROOT con `flusso_id`); poi OFFERTA.

**G5 — Osservabilità fallimenti reconcile** *(nuovo, da D-B7)*: tabella/vista che registra i
reconcile falliti (inghiottiti dal best-effort di G3b), così un avanzamento mancato è
**diagnosticabile** e non silenzioso. Criterio d'accettazione dedicato (vedi §3.9).

### G4 (roll-out perf) — Indice a espressione per la pushdown del resolver
- **Correzione fattuale (review DB 2026-07-06)**: la nota-roll-out (a) era imprecisa. (1) Le
  viste **non** usano una `LEFT JOIN LATERAL`: `vw_pratica_doc_sorgente` fa un **equi-`LEFT JOIN`**
  su `sorgente_uid` già castato nella leaf-view (`vendite.vw_stato_sorgente_preventivo`:
  `(p.uid)::text`). (2) Per **PREVENTIVI l'indice a espressione esiste già**:
  `ix_preventivi_uid_text` su `(((uid)::text))` → **niente da fare per il pilota**.
- Azione residua: al roll-out di **ogni nuovo dominio** (offerte/ordini/contratti) **verificare**
  l'esistenza dell'indice `((uid::text))` sulla tabella-documento e crearlo se assente. Non è
  pilot-blocking.
  *(La nota (c) — àncora condivisa `vw_pratica_doc_sorgente` — è **già fatta**; la (b) — COLLEGATO
  senza `flusso_id` — è risolta da G1 + àncora pratica-level, senza forzare `flusso_id`.)*

## 3. Invarianti / criteri d'accettazione (pgTAP)

1. **Standalone → avanza**: preventivo (ROOT di una pratica) portato ad ACCETTATO **dal suo
   percorso standalone** (fuori pratica) → il flusso milestone che lo attende risulta COMPLETATO
   con esito POSITIVO. *(È il cuore di GUIDA: prima restava aperto.)*
2. **In-pratica → avanza**: stessa transizione fatta in-pratica → stesso esito (i due percorsi
   convergono).
3. **Idempotenza**: reconcile ripetuto (o doc che ritocca lo stato) → nessun doppio avanzamento,
   nessun errore. La garanzia è il **filtro `stato NOT IN {COMPLETATO,ANNULLATO}` dentro
   `fn_reconcile_sorgente`** (D-B11), non la primitiva BE `completa_step_pratica` (che sul
   percorso DB non è nel giro).
4. **Documento sovrano (best-effort)**: se il reconcile fallisce (es. vincolo pratiche), il
   cambio-stato del **documento** **persiste** comunque (nessun rollback); l'errore è loggato.
5. **Additività**: step senza `attende_sorgente_tipo_id`/binding → **nessun** avanzamento
   automatico (comportamento di oggi immutato).
6. **Nessun verdetto → no-op**: doc che proietta `esito IS NULL` (es. EMESSO) → nessun avanzamento.
7. **Copia edizione**: `fn_copia_definizione` propaga G1/G2 alla nuova edizione (fork /
   nuova-versione).
8. **Generazione a valle**: l'avanzamento GUIDA fa scattare `trgfn_flussi_generazione` come il
   completamento manuale.
9. **Due salti (D-B2)**: milestone partito da `DA_ESEGUIRE` → risulta `COMPLETATO` (il reconcile
   passa da `IN_CORSO`, non fa il salto diretto vietato dalla matrice).
10. **Classe esito (D-B3)**: verdetto proiettato su step **non-DOMINIO** → completa OK; binding G2
    su step **DOMINIO** → **rifiutato** dal `fn_guard_*` config-time (non arriva neppure a runtime).
11. **Mutua esclusione (D-B10)**: step con binding G2 **+** `handler_eventi` `COMPLETATO` →
    respinto config-time dal G2-guard.
12. **Tie-break multi-istanza (D-B5)**: pratica con 2 documenti dello stesso tipo →
    `reconcile(tipo, uidA)` avanza **solo** il milestone legato a `uidA` (via `flusso_id`), non
    l'altro; caso ambiguo `flusso_id` NULL non-univoco → logga e non avanza.
13. **Osservabilità (D-B7)**: reconcile che fallisce (es. verdetto non ammesso dalla classe su uno
    step mal configurato) → il **documento persiste** (già coperto da #4) **e** compare una
    **riga in `pratiche.reconcile_errori`** (il fallimento è diagnosticabile, non silenzioso).

## 4. Fuori scope (BE, dopo il DB)

- Ritiro di `vendita.accetta_preventivo` (il pulsante «Accetta» in-pratica → servizio standalone
  del doc; il milestone avanza per proiezione). Rimozione del binding handler dedicato.
- **Coordinamento con *fatturazione-due-lenti*** (BE/FE): oggi la modalità/`competenza_mese` di
  fatturazione è raccolta al **milestone** (`meta` → `accetta_preventivo_handler`) e persistita
  **sul preventivo** da `preventivi_service.cambia_stato` (single source of truth). Ritirando
  l'handler, il **percorso standalone** («Accetta» del drawer) deve raccogliere lo **stesso
  dialog** (immediata / `competenza_mese`), altrimenti il campo che la **Lente 1** legge resta
  vuoto. Non è azione DB: è vincolo d'integrazione BE/FE dell'inversione.
- Estrazione del frammento condiviso ROOT/sorgenti (debito §5.3) se serve anche lato BE. **La
  scrittura giornale è già DB-side** (`fn_log_evento_dominio`) → del frammento resta rilevante
  solo la **risoluzione ROOT/sorgenti**.
- Seed dei binding G1/G2 per il tipo prestazione PREVENTIVI (config di dominio).

---

## 5. Follow-up DB richiesto — inversione PIENA sul rifiuto (owner, 2026-07-07)

**Deciso (owner)**: inversione **piena** anche sul percorso non-positivo. Il cutover
`20260706-24` ha shippato il binding G2 su `esito_richiesto='POSITIVO'` (conservativo → solo
l'accettazione auto-avanza il milestone). Il BE/FE dell'inversione cabla anche il **Rifiuta**
(→ preventivo `RIFIUTATO`, verdetto proiettato NEGATIVO), ma con G2 POSITIVO-only il milestone
**non** avanza sul rifiuto.

**Richiesta**: cambiare il binding di avanzamento dello step **9011** da `esito_richiesto='POSITIVO'`
a **`NULL`** (qualsiasi verdetto), così il milestone auto-avanza sia su ACCETTATO (POSITIVO) sia
su RIFIUTATO (NEGATIVO) — chiudendo la divergenza in entrambe le direzioni (obiettivo GUIDA).
Changeset dati (una riga): `UPDATE pratiche.template_flussi_avanzamento_proiezione SET
esito_richiesto=NULL WHERE template_flusso_id=9011;` (+ rollback inverso). **Verificare** che
il completamento con esito NEGATIVO su step non-DOMINIO sia ammesso dalla classe esito
(`trgfn_flussi_guard_esito_classe`: NEGATIVO è verdetto → OK).

## 6. Stato BE/FE dell'inversione (2026-07-07) — ✅ FATTO (dev), committato dal team

- **BE**: `preventivi_service.cambia_stato_da_pratica(pratica_id, nuovo_stato, …)` (risolve il
  ROOT via `get_preventivo_id_by_pratica_root`, delega a `cambia_stato`) + endpoint
  `POST /vendite/preventivi/da-pratica/<pratica_id>/stato/` (`ApiPreventivoStatoDaPratica`,
  `post_permission=cambia_stato_preventivi`). Flag **`template_attende_sorgente_tipo_id`**
  esposto sul flusso (SELECT dettaglio + percorso) = discriminante projection-driven.
- **FE**: `flussoCompletionRegistry.APPROVAZIONE_CLIENTE` guadagna `esitoToStato` +`docAction`
  (lazy); `FlussoDrawer` instrada «Accetta/Rifiuta» sul DOCUMENTO **solo** se
  `template_attende_sorgente_tipo_id != null` (gate sul flag, non sul codice → i tipi deprecati
  9002/9003 e le altre edizioni del 9004 restano legacy/handler). Dialog fatturazione condiviso
  col percorso standalone (Lente 1 alimentata).
- **Handler**: `vendita.accetta_preventivo` lasciato **registrato ma dormiente** (binding DB
  disattivato dal cutover → mai dispatchato); rimozione file/test = cleanup separato.
- **Nota permessi**: l'operatore che accetta in-pratica ora esegue un'azione vendite diretta →
  serve `cambia_stato_preventivi` (prima la faceva il sistema via handler). Verificare i profili
  degli operatori-pratica.

## 7. 🔴 Finding smoke E2E (2026-07-07) — GRANT mancante su `reconcile_errori`

Lo smoke E2E sul **percorso HTTP reale** (ruolo app `zeroerp_app`, non owner) ha scoperto un
bug **invisibile al pgTAP** (che gira come owner con tutti i privilegi):

- **`pratiche.reconcile_errori` non ha ALCUN grant** (`role_table_grants` = vuoto) → il ruolo
  app **non può fare INSERT**. Quando il reconcile (INVOKER, gira come `zeroerp_app`) entra nel
  blocco best-effort e tenta di loggare l'errore, l'`INSERT INTO reconcile_errori` fallisce con
  **`permission denied`**; l'eccezione **non è catturata** e **propaga** → **rollback del
  cambio-stato del documento**. **Viola l'invariante "documento sovrano/best-effort" (D-B4/D-B7)**:
  un errore di reconcile NON deve annullare l'accettazione del preventivo.
- **Sintomo E2E**: `POST da-pratica ACCETTATO` → HTTP 400 `E_DATABASE` (`permission denied per
  la tabella reconcile_errori`), il preventivo resta EMESSO e il milestone 9011 non avanza.
- **Fix richiesto (DB)**: `GRANT INSERT ON pratiche.reconcile_errori TO zeroerp_app;` (+ `SELECT`
  per la vista di consultazione se serve). Verificare che il changeSet G5 includa i GRANT come
  le altre tabelle scrivibili dal ruolo app. In più: il blocco best-effort dovrebbe reggere
  **anche** un fallimento del proprio log (es. logging via helper `SECURITY DEFINER`, o log
  "a prova di permesso"), così l'invariante regge davvero.
- **Errore sottostante mascherato**: il reconcile body ha sollevato *qualcosa* (per questo è
  entrato nel blocco best-effort); il log rotto lo nasconde. Dopo il fix del GRANT va ri-eseguito
  lo smoke per far emergere e diagnosticare l'errore originale (potenziale 2° bug del reconcile
  sul percorso app/INVOKER).
- **Smoke**: `backend/scripts/tests/smoke-test-guida-inversione-preventivi.sh` (direct-insert su
  9011 reale + catena prereq 9009→9010 + accept HTTP + assert milestone). Oggi **2 OK / 3 FAIL**
  (cattura il bug); atteso **5/0** dopo il fix GRANT (+ eventuale fix reconcile).

---

*A chiusura: aggiornare §11/§8-D4 del design-of-record e la nota GUIDA in
[brief-design-proiezione-stato-dominio.md](brief-design-proiezione-stato-dominio.md).*
