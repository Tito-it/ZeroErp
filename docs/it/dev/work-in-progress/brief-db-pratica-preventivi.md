# Brief DB — Pratica `PREVENTIVI` (fatturazione immediata / differita)

> **Tipo documento**: brief operativo **per il team DB** (canale `dev/db-tid`).
> Spiega *cosa* fare e *perché*; **non contiene DDL pronto** (lo scrive il team
> DB nel changelog liquibase). I punti §3 del brief sorgente sono qui
> **risolti** contro lo schema reale: ogni V-point riporta FOUND/MISSING con
> nomi e firme verificati.
>
> **Data**: 2026-06-06 · **Stato**: VERIFICATO, pronto per stima/applicazione DB
>
> **Sorgente**: Brief Fase B — Pratica PREVENTIVI (questo turno) +
> [analisi-pratiche-domini-anello3.md](analisi-pratiche-domini-anello3.md) §11 +
> [gestione-pratiche-v2.md](gestione-pratiche-v2.md) +
> [sviluppo-push-singolo-preventivo.md](sviluppo-push-singolo-preventivo.md)
>
> **Decisione di prodotto (Tid, 2026-06-06)**: la politica immediata/differita
> vive **in configurazione** (modello "Brief Fase B come scritto"): due
> `tipi_prestazione`, `handler_params` sul flusso `CONFERMA`, vocabolario
> controllato `config.modalita_fatturazione`. L'operatore **non** sceglie la
> politica al runtime del flusso. Conseguenza obbligata documentata in §5.

---

## 1. Scope DB

In scope (questo brief, destinazione **fissa = commessa diretta**, nessuno
split per natura, nessun ordine/contratto — coerente con §2 del brief sorgente):

1. Nuova tabella vocabolario `config.modalita_fatturazione` (+ seed 2 righe).
2. Seed catalogo pratiche: 2 `tipi_prestazione` + 8 `template_flussi`
   (4×2) con prerequisiti, canali, `handler_params`, `handler_flussi`.
3. Canale di scrittura giornale per eventi di dominio (`DOMINIO_*`) — oggi
   **assente** (V11): serve una funzione DB dedicata.
4. Sanatoria GRANT su `pratiche.competenze_flussi` (V13) se la demo usa la coda
   lavoro.
5. Verifica/chiarimento del percorso "commessa emittibile" (V9) — nessuna nuova
   colonna prevista, ma serve la conferma del team DB.
6. Registrazione codici errore in `config.messaggi_errore`.

**Esplicitamente NON in scope DB**: nuova `fn_push_preventivo_a_commessa`,
nuovo indice di idempotenza preventivo→commessa, ALTER su `preventivi_righe`,
`config.nature_vendita`. Motivo: il push preventivo→commessa **esiste già** e
l'idempotenza è **già garantita** (vedi §3 V8 e §4).

---

## 2. Riscontro sintetico (cosa esiste, cosa manca)

| Oggetto | Stato reale | Azione DB |
|---|---|---|
| `config.sorgenti` `PREVENTIVO`/`COMMESSA` | **Esistono** (id 2 / id 13) | **Nessuna** |
| `pratiche.pratiche_sorgenti` (M:N, `ruolo_link ROOT/COLLEGATO`) | **Esiste** + UNIQUE idempotente | **Nessuna** (insert dal BE) |
| `vendite.preventivi.uid` (uuid, unique) + stato `EVASO` (id 10) | **Esistono** | **Nessuna** |
| Pipeline push preventivo→commessa + idempotenza | **Esiste** (`commesse_sorgenti` UNIQUE) | **Nessuna** |
| `commesse.fatturazione_immediata` + `commesse_attivita.competenza_mese` | **Esistono** | **Nessuna** (li valorizza il push) |
| `config.modalita_fatturazione` | **Manca** | **Crea + seed** (B2/B3) |
| Seed 2 `tipi_prestazione` + 8 `template_flussi` + handler | **Mancano** | **Seed** (B4–B7) |
| Scrittura giornale `DOMINIO_*` da applicativo | **Manca** (solo trigger) | **Crea fn** (B-NEW) |
| GRANT `competenze_flussi` ruolo Django | **Mancante** (smoke 26 KO) | **GRANT** (B-GRANT) |
| Codici errore `E_VENDITA_*` | **Mancano** | **Seed** (B9) |

---

## 3. Risoluzione punti di verifica del brief sorgente (V1–V14)

### V1 — `config.sorgenti` `PREVENTIVO`/`COMMESSA` → **FOUND, no-op**
Tabella `config.sorgenti` presente; seed CSV contiene `PREVENTIVO` (id 2,
`key_selector='uid'`, `scope='PUSH_COMMESSA'`) e `COMMESSA` (id 13,
`key_selector='id'`, `scope='PIPELINE_MARKER'`). **Nessun seed da aggiungere**
per questo brief (`ORDINE` resta fuori scope).

### V2 — `pratiche.pratiche_sorgenti` → **FOUND, insert dal BE**
Colonne: `pratica_id, sorgente_tipo_id, sorgente_uid (text), sorgente_riga
(nullable), ruolo_link (default 'ROOT'), meta jsonb, …`. CHECK
`chk_pratiche_sorgenti_ruolo` ammette `{ROOT, COLLEGATO}`. UNIQUE su
`(pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link)` → **idempotenza
dell'aggancio già garantita**. **Nessuna funzione dedicata**: l'INSERT (con
`ON CONFLICT DO NOTHING`) lo fa il BE. Nessuna azione DB.

### V3 — stati `vendite.preventivi` → **FOUND**
Colonna stato = `stato_doc_preventivo_id` → `config.stati_doc_preventivi`.
Codici reali: `DRAFT(1)`, `EMESSO(2)`, `ACCETTATO(4)`, `RIFIUTATO(5)`,
`SCADUTO(7)`, `ANNULLATO(9)`, **`EVASO(10)`** (aggiunto 2026-05-10). Le
transizioni `ACCETTATO→EVASO` esistono già nel modello push. Nessuna azione DB.

### V4 — registrazione accettazione → **FOUND (con riserva §5)**
Il passaggio `→ACCETTATO` è già implementato con dialog che cattura
`fatturazione_immediata` + `competenza_mese` (pattern
`feedback_dialog_cambio_stato_dati_processo`). **Sotto il modello scelto da Tid
questo va riconciliato** (vedi §5): sul percorso pratica la politica viene dalla
configurazione, non dall'operatore. Nessuna azione DB diretta (è BE/FE), ma il
team DB deve sapere che il valore "autorevole" per la commessa, sul percorso
pratica, è quello applicato dall'handler.

### V5 — `vendite.preventivi.uid` → **FOUND**
`uid uuid NOT NULL UNIQUE DEFAULT uuidv7()`. È la chiave usata come
`sorgente_uid` da `pratiche_sorgenti` e dalla pipeline commesse. Nessuna azione.

### V6 — `fn_get_or_create_commessa` → **FOUND**
Firma reale:
`fn_get_or_create_commessa(p_billing_account_id bigint, p_utility_id integer,
p_tipo_commessa varchar='AUTO', p_policy_fatturazione varchar='DA_DOCUMENTO',
p_fatturazione_immediata boolean=false, p_priorita_operativa varchar='NORMALE',
p_emittente_soggetto_ruolo_id bigint=NULL, p_competenza_dal date=NULL,
p_competenza_al date=NULL, p_meta jsonb='{}', p_force_new boolean=false)
RETURNS bigint`. BA/utility/emittente li ricava la pipeline esistente dal
preventivo. **Espone già** `p_fatturazione_immediata` e `p_competenza_dal/_al`:
sufficienti a veicolare la politica. Nessuna azione DB.

### V7 — `fn_upsert_commessa_attivita` → **FOUND**
`p_competenza_mese date` è **per riga** (manopola della politica). Idempotenza
riga: `ON CONFLICT (commessa_id, p_segment_key)` (es. `segment_key =
'PREV:<uid>:R:<riga>'`). Nessuna azione DB.

### V8 — funzione push preventivo→commessa → **FOUND, NON serve nuova fn**
**Non esiste** (né serve) una `fn_push_preventivo_a_commessa` monolitica. Il
push passa dall'orchestratore applicativo
`pr_run_commesse_push_one(sorgente_codice='PREVENTIVO', sorgente_uid=<uid>)` →
`fn_list_preventivi_da_pushare` → `fn_get_or_create_commessa` /
`fn_upsert_commessa_attivita`. **Conseguenza**: l'aggancio `p_pratica_id` del
brief sorgente **non va al DB** — è un concern applicativo (il BE scrive
`pratiche_sorgenti` dopo il push). **Nessuna nuova fn, nessun nuovo parametro
DB.**

### V9 — commessa emittibile / `PRONTA_FATTURAZIONE` → **CHIARIMENTO RICHIESTO**
**`PRONTA_FATTURAZIONE` non esiste** come stato. L'emittibilità è un **flag
booleano** `emittibile` su `vendite.stati_commessa`:
`fn_list_commesse_emittibili` include una commessa quando il suo stato ha
`emittibile=true` **e** le righe sono `stato_emissione='NON_EMESSA'`. Le righe
hanno anche `stato_approvazione (BOZZA/APPROVATA)`.

> **Domanda al team DB (bloccante per il piano)**: dopo il push, la commessa
> creata da `fn_get_or_create_commessa` (default `stato_commessa_id=1`) è già in
> uno stato con `emittibile=true`, oppure serve un passo di approvazione/
> transizione (BOZZA→APPROVATA / set-stato) perché compaia in
> `fn_list_commesse_emittibili`? Se serve, **qual è la funzione/azione** che
> porta righe e/o testata allo stato emittibile?

Il §5 punto 7 del brief sorgente ("porta la commessa a `PRONTA_FATTURAZIONE`")
va **riscritto** sulla risposta: o è un no-op (già emittibile) o è una chiamata
a una funzione esistente di set-stato/approvazione (da nominare qui).

### V10 — semantica "immediata" sulla commessa → **FOUND, mapping confermabile**
`commesse` ha sia `policy_fatturazione varchar` sia `fatturazione_immediata
boolean` in testata; `commesse_attivita.competenza_mese` per riga.
`fn_get_commessa_stato` ritorna `policy_fatturazione` + `fatturazione_immediata`.
**Mapping proposto (da ratificare col team DB)**:
- `IMMEDIATA` → `p_fatturazione_immediata=true` + `competenza = mese corrente`;
- `DIFFERITA` → `p_fatturazione_immediata=false` + `competenza = mese scelto`.

Tutte le manopole esistono già: **nessuna ALTER**.

### V11 — scrittura giornale `DOMINIO_*` → **MISSING, serve fn DB**
`pratiche.giornale` è **append-only alimentata solo da trigger** DB; **non
esiste** alcun metodo applicativo di scrittura (`log_evento_dominio` assente).
Per gli eventi `DOMINIO_COMMESSA_CREATA` / `DOMINIO_PREVENTIVO_EVASO` serve un
**canale di scrittura controllato dal DB** (coerente con architettura
DB-centrica). Vedi deliverable **B-NEW** in §4.

### V12 — dispatch handler → **FOUND, non auto-wired (è BE)**
`dispatch_handler(flusso_id)` e `BaseFlussoHandler.execute(flusso_id,
pratica_id, meta, handler_params)` esistono; `HANDLER_MAP` è **vuoto**. Il
dispatch **non** è automatico sul cambio stato → wiring lato BE (vedi brief BE).
Nessuna azione DB.

### V13 — GRANT `pratiche.competenze_flussi` → **MISSING**
Smoke test 26 (coda lavoro) fallisce "permesso negato": mancano i GRANT per il
ruolo applicativo Django. **Sanare** (B-GRANT) se la demo passa dalla coda
lavoro.

### V14 — due `tipi_prestazione` → **confermato (scelta Tid)**
Strada confermata: `PREVENTIVI_IMMEDIATA` / `PREVENTIVI_DIFFERITA`, 4
`template_flussi` ciascuno (8 righe), differenti **solo** nel `handler_params`
del flusso `CONFERMA`. Nessun toggle runtime. Per ridurre la duplicazione del
seed il team DB **può** generare le 8 righe da una sorgente unica (vista/CTE di
seed), ma resta **dato**, non funzione runtime.

---

## 4. Deliverable DB (cosa fare)

| ID | Oggetto | Cosa fare |
|---|---|---|
| **B2** | `config.modalita_fatturazione` (nuova tabella) | Vocabolario controllato. Colonne minime: `codice` (PK logica, maiuscolo singolare), `descrizione`, `richiede_periodo boolean`, `attivo boolean`. Serve perché l'admin scelga la politica da Select, non editi JSON (D-d) |
| **B3** | Seed `config.modalita_fatturazione` | 2 righe: `IMMEDIATA` (`richiede_periodo=false`), `DIFFERITA` (`richiede_periodo=true`) |
| **B4** | Seed `pratiche.tipi_prestazione` | 2 righe `PREVENTIVI_IMMEDIATA`, `PREVENTIVI_DIFFERITA`; `categoria='COMMERCIALE'`; `pre_attivazione=false`, `post_attivazione=false` |
| **B5** | Seed `pratiche.template_flussi` (×2 tipi) | 4 flussi per tipo: `RICHIESTA_CLIENTE`→`PREVENTIVAZIONE`→`APPROVAZIONE_CLIENTE`→`CONFERMA`. Prerequisiti lineari (ognuno richiede il precedente POSITIVO). Canali standard sui flussi ENTRATA. `CONFERMA` ha `handler_id` → riga B7 |
| **B6** | `handler_params` su `CONFERMA` (×2) | `PREVENTIVI_IMMEDIATA`: `{"modalita_fatturazione":"IMMEDIATA"}`; `PREVENTIVI_DIFFERITA`: `{"modalita_fatturazione":"DIFFERITA"}`. Valore = FK logica verso `config.modalita_fatturazione.codice` |
| **B7** | Seed `pratiche.handler_flussi` | 1 riga `handler_key='vendita.push_preventivo'`, `attivo=true`. `template_flussi.handler_id` dei due `CONFERMA` punta qui |
| **B-NEW** | Funzione scrittura giornale di dominio | Funzione DB tipo `pratiche.fn_log_evento_dominio(p_pratica_id, p_flusso_id, p_tipo_evento text, p_meta jsonb)` che fa l'INSERT controllato in `pratiche.giornale` (append-only, stesso `tx_id`/correlazione dei trigger). È il canale per `DOMINIO_*` chiamato dall'handler. **Decisione provvisoria §3.2 analisi**: tipo evento testuale libero, nessuna whitelist iniziale |
| **B-GRANT** | GRANT `pratiche.competenze_flussi` | Concedere al ruolo applicativo Django i privilegi mancanti (sblocca smoke 26 / coda lavoro) |
| **B9** | Seed `config.messaggi_errore` | Registrare i codici di §6 (it). NB: `config.messaggi_errore` è **tabella** (chiave `(codice, lingua)`), il `.csv` del brief sorgente è solo il formato-seed |
| **V9?** | Chiarimento "commessa emittibile" | Rispondere alla domanda §3 V9 e, se serve un passo di approvazione/set-stato, nominare la funzione esistente da usare (no nuova fn salvo necessità) |

> Tutti i deliverable sono **seed/GRANT/1 funzione di logging**. Nessuna ALTER
> sulle tabelle vendite, nessun nuovo indice di idempotenza, nessuna nuova fn di
> push. Questa è la conseguenza diretta del fatto che la pipeline commesse è già
> completa.

---

## 5. Conseguenza obbligata della decisione "politica in configurazione"

La scelta di Tid (politica in `handler_params`) **convive** con il doppio punto
di ingresso §5.8 dell'analisi (preventivo autonomo vs preventivo dentro
pratica). Per il team DB rileva una sola cosa: **sul percorso pratica il valore
autorevole della politica è quello applicato dall'handler al `CONFERMA`**, non
quello eventualmente impostato all'accettazione del preventivo. Concretamente:

- L'handler valorizza `fatturazione_immediata` + `competenza` della commessa
  dai `handler_params`/`flussi.meta` (config), **sovrascrivendo** qualunque
  valore arrivasse dall'accettazione.
- Non serve alcuna modifica DB per questo (i campi esistono e li scrive il
  push). È un vincolo di **comportamento** dell'handler (brief BE) e di **UX**
  (brief FE: nascondere/disabilitare i campi all'accettazione quando il
  preventivo è dentro una pratica `PREVENTIVI`).

Il team DB deve solo essere consapevole che il "single source of truth" per la
commessa, su questo percorso, è l'handler.

---

## 6. Codici errore da seedare (B9)

| Codice | Quando |
|---|---|
| `E_VENDITA_PARAM_MODALITA_FATTURAZIONE_INVALIDA` | `handler_params.modalita_fatturazione` assente o fuori vocabolario `config.modalita_fatturazione` |
| `E_VENDITA_COMPETENZA_RICHIESTA` | politica `DIFFERITA` ma `flussi.meta.competenza_fatturazione` assente/non valida |
| `E_VENDITA_PREVENTIVO_GIA_PUSHATO` | push ripetuto sullo stesso preventivo (idempotenza già garantita da `commesse_sorgenti`; serve il **messaggio semantico** se l'orchestratore oggi non lo espone — da verificare col BE) |

---

## 7. Domande aperte da chiudere col team DB prima del piano

1. **V9** (bloccante): come diventa emittibile la commessa creata dal push?
   No-op o funzione di approvazione/set-stato da usare?
2. **B-NEW**: ok a una `pratiche.fn_log_evento_dominio(...)` append-only come
   unico canale di scrittura `DOMINIO_*`? (alternativa: INSERT diretto dal BE,
   meno coerente con DB-centrico).
3. **B2**: convenzione tabella vocabolario `config.modalita_fatturazione` —
   PK su `id` numerico + `codice` unique, oppure `codice` come PK testuale?
   (allinearsi alle altre tabelle `config.*` whitelist).

---

*Brief DB — Pratica PREVENTIVI / fatturazione immediata-differita — ZeroERP
(2026-06-06). Verificato contro schema reale. Da passare a `dev/db-tid`.*
