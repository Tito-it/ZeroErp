# Brief DB — Pratica `PREVENTIVI` (fatturazione immediata / differita)

> **Tipo documento**: brief operativo **per il team DB** (canale `dev/db-tid`).
> Spiega *cosa* fare e *perché*; **non contiene DDL pronto** (lo scrive il team
> DB nel changelog liquibase). I punti §3 del brief sorgente sono qui
> **risolti** contro lo schema reale: ogni V-point riporta FOUND/MISSING con
> nomi e firme verificati.
>
> **Data**: 2026-06-06 · **Stato**: 🟢 **IMPLEMENTATO A DB (2026-06-08)** —
> commit `58169e9ed`: tutti i deliverable consegnati (B4-B7 seed catalogo,
> B-PREREQ motore esito-aware, B-NEW `fn_log_evento_dominio` + CHECK regex
> `DOMINIO_*`, B-GRANT `competenze_flussi`, B9 codici `E_VENDITA_*`), pgTAP
> verdi. Prerequisito V9 (macchina transizioni commesse) consegnato nello
> stesso commit. Cantiere applicativo a valle committato (`327140116`,
> handler `vendita.push_preventivo` BE+FE).
>
> **Sorgente**: Brief Fase B — Pratica PREVENTIVI (questo turno) +
> [analisi-pratiche-domini-anello3.md](../work-in-progress/analisi-pratiche-domini-anello3.md) §11 +
> [gestione-pratiche-v2.md](../work-in-progress/gestione-pratiche-v2.md) +
> [sviluppo-push-singolo-preventivo.md](sviluppo-push-singolo-preventivo.md)
>
> **Decisione di prodotto (Tid, 2026-06-06)**: la politica immediata/differita
> vive **in configurazione** (modello "Brief Fase B come scritto"): due
> `tipi_prestazione`, `handler_params` sul flusso `CONFERMA`, vocabolario
> controllato `config.modalita_fatturazione`. L'operatore **non** sceglie la
> politica al runtime del flusso. Conseguenza obbligata documentata in §5.
>
> **Aggiornamento revisione critica (Tid, 2026-06-07)** — chiusi due blocker
> emersi verificando il brief contro lo schema reale:
>
> - **V9 (commessa emittibile)** — RISOLTO. Era sottostimato: la commessa nata
>   dal push resta in `BOZZA` e **nessuna** funzione la porta a
>   `PRONTA_FATTURAZIONE`; idem le righe restano `BOZZA` di `stato_approvazione`
>   → il ramo commessa→fattura è oggi **dormiente**. Decisione: costruire una
>   **macchina di transizioni commesse** completa (come preventivi/ordini) in un
>   **brief commesse separato** (prerequisito), e l'handler la invoca. Dettaglio
>   in §3 V9 e §7.1.
> - **B-NEW (giornale `DOMINIO_*`)** — RISOLTO. `pratiche.giornale.azione` ha un
>   `CHECK` whitelist (non testo libero): si sostituisce con regex
>   `^DOMINIO_[A-Z][A-Z0-9_]*$` **OR** la lista fissa attuale. Dettaglio §3 V11 e
>   §4 B-NEW.
> - **B5/prerequisiti esito-aware** — il motore oggi filtra i prerequisiti solo
>   su `COMPLETATO`, **ignorando l'esito** (la colonna `flussi.esito` esiste già).
>   Decisione (Tid, da esperienza): una fase **deve** avere esito, e il passo
>   successivo si abilita in base all'esito del precedente → si estende il motore
>   (esito-aware) + vincolo "esito obbligatorio su COMPLETATO". Nuovo deliverable
>   **B-PREREQ**. Dettaglio §3 V15 e §4.
> - **B2/B3 (`config.modalita_fatturazione`)** — RIMOSSI (decisione modeling Tid,
>   2026-06-07). Una tabella-vocabolario per un flag binario locale a un handler è
>   eccessiva: il parametro vive in `handler_params` (JSONB) e la **validazione la
>   fa l'handler** (codice errore già previsto). Tabella-vocabolario solo per
>   *valori di dominio condivisi/gestiti da admin*, non per flag di handler. Il
>   bisogno generale ("parametrizzare i flussi") è già coperto dai 4 livelli di
>   configurabilità del motore (analisi §4); un eventuale *descrittore dei
>   parametri di handler* si costruirà **una volta sola**, quando 3-4 handler lo
>   chiederanno (manifesto §7) — non ora. Dettaglio §3 V10 e §4.

---

## 1. Scope DB

In scope (questo brief, destinazione **fissa = commessa diretta**, nessuno
split per natura, nessun ordine/contratto — coerente con §2 del brief sorgente):

1. ~~Nuova tabella vocabolario `config.modalita_fatturazione`~~ → **RIMOSSA**
   (decisione modeling 2026-06-07): il parametro vive in `handler_params` JSONB,
   validato dall'handler. Nessuna tabella.
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
| `config.modalita_fatturazione` | **Manca** | **Non si crea** (modeling 2026-06-07: JSONB + validazione handler) |
| Seed 2 `tipi_prestazione` + 8 `template_flussi` + handler | **Mancano** | **Seed** (B4–B7) |
| Scrittura giornale `DOMINIO_*` da applicativo | **Manca** + `azione` ha CHECK whitelist | **Regex CHECK + fn** (B-NEW) |
| Transizione commessa → emittibile (testata + righe) | **Manca** (mai sviluppata) | **Brief commesse separato** (prerequisito, V9) |
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

### V9 — commessa emittibile / `PRONTA_FATTURAZIONE` → **RISOLTO (2026-06-07)**

**Correzione fattuale**: `PRONTA_FATTURAZIONE` **esiste** ed è lo stato `id 4` di
`vendite.stati_commessa`, l'unico con `emittibile=true` (la riga originale del
brief "non esiste come stato" era errata). L'emittibilità è quindi uno **stato**
(testata) + l'approvazione (righe).

**Verifica (codice reale)**:

- `fn_get_or_create_commessa` crea in `stato_commessa_id = 1` = `BOZZA`
  (`emittibile=false`); `fn_upsert_commessa_attivita` crea righe in
  `stato_approvazione = 'BOZZA'`.
- `fn_list_commesse_emittibili` richiede testata `emittibile=true` (stato 4) +
  righe `stato_emissione='NON_EMESSA'`; `fn_emit_attivita_fatturabili_da_commessa`
  emette solo righe `stato_approvazione='APPROVATA'`.
- **Nessuna funzione/trigger porta testata→`PRONTA_FATTURAZIONE` o
  righe→`APPROVATA` in produzione** (solo i pgTAP lo fanno con UPDATE manuale).
  Le commesse — a differenza di preventivi/ordini — **non hanno macchina di
  transizioni**. → ramo commessa→fattura **oggi dormiente**.

**Decisione (Tid, 2026-06-07)**:

1. Costruire una **macchina di transizioni commesse** completa, fedele al
   pattern preventivi/ordini: nuova `vendite.transizioni_stati_commessa`
   (matrice + seed) + `vendite.fn_cambia_stato_commessa(p_commessa_id,
   p_nuovo_stato, p_user)`. In schema `vendite` (lì vivono già `stati_commessa`),
   non `config`.
2. **Brief commesse separato** (proprio changelog + pgTAP): è prerequisito di
   questo brief, **non** un suo deliverable. L'handler `vendita.push_preventivo`
   si limita a invocarlo (vedi §7.1). → scritto in
   [brief-db-commesse-transizioni-stati.md](brief-db-commesse-transizioni-stati.md)
   e ✅ **IMPLEMENTATO (2026-06-08)**: `vendite.transizioni_stati_commessa` +
   `trgfn_commesse_guard_transizione` + `fn_cambia_stato_commessa` +
   `fn_approva_commessa_attivita` (`20260607-01..06`), pgTAP verdi. Il
   prerequisito V9 è quindi **chiuso a livello di codice**; restano da fare i
   deliverable propri di *questo* brief (B4-B7, B-NEW, B-PREREQ, B9, B-GRANT).
3. **Righe**: l'handler le porta ad `APPROVATA` nel push (il preventivo accettato
   è l'autorizzazione). Meccanismo (fn dedicata `fn_approva_commessa_attivita`
   vs parametro su `fn_upsert_commessa_attivita`) da fissare nel brief commesse;
   preferenza: fn dedicata (tracciabile).
4. **Testata**: l'handler la porta a `PRONTA_FATTURAZIONE` nel push, **zero
   click**. **Guard** sulla transizione verso `PRONTA_FATTURAZIONE`: ammessa solo
   con ≥1 riga `APPROVATA` e `NON_EMESSA` (i due livelli non possono divergere).
5. Il timing immediata/differita **non** passa dallo stato testata: resta su
   `competenza_mese` delle righe, già filtrato da `fn_list_commesse_emittibili`.

Il §5 punto 7 del brief sorgente ("porta la commessa a `PRONTA_FATTURAZIONE`")
si riscrive così: l'handler chiama `fn_approva_commessa_attivita` (righe) +
`fn_cambia_stato_commessa(..., 'PRONTA_FATTURAZIONE')` (testata), entrambe del
brief commesse.

### V10 — semantica "immediata" sulla commessa → **FOUND, mapping confermabile**
`commesse` ha sia `policy_fatturazione varchar` sia `fatturazione_immediata
boolean` in testata; `commesse_attivita.competenza_mese` per riga.
`fn_get_commessa_stato` ritorna `policy_fatturazione` + `fatturazione_immediata`.
**Mapping proposto (da ratificare col team DB)**:
- `IMMEDIATA` → `p_fatturazione_immediata=true` + `competenza = mese corrente`;
- `DIFFERITA` → `p_fatturazione_immediata=false` + `competenza = mese scelto`.

Tutte le manopole esistono già: **nessuna ALTER**.

> **Decisione modeling (Tid, 2026-06-07)**: il valore `IMMEDIATA/DIFFERITA`
> **non** ha una tabella-vocabolario dedicata (B2/B3 rimossi). Vive in
> `handler_params` (JSONB) come stringa e la **validazione la fa l'handler**.
> Regola generale: tabella-vocabolario solo per valori di dominio condivisi o
> gestiti da admin a runtime; un flag binario locale a un handler sta nel JSONB +
> check in codice. Il bisogno "parametrizzare i flussi in modo generale" è già
> coperto dai 4 livelli di configurabilità del motore (analisi §4); un eventuale
> *descrittore strutturato dei parametri di handler* (uno schema per
> `handler_params`, con admin UI a form) si costruisce **una volta sola** quando
> 3-4 handler lo richiederanno (manifesto §7) — **non** una tabella per ogni set
> di valori (anti-pattern di proliferazione).

### V11 — scrittura giornale `DOMINIO_*` → **RISOLTO (2026-06-07)**
`pratiche.giornale` è **append-only alimentata solo da trigger** DB; **non
esiste** alcun metodo applicativo di scrittura (`log_evento_dominio` assente) —
confermato. Per gli eventi `DOMINIO_COMMESSA_CREATA` / `DOMINIO_PREVENTIVO_EVASO`
serve un **canale di scrittura controllato dal DB**. Vedi deliverable **B-NEW**.

**Correzione**: le colonne reali sono **`azione`** (varchar 50) e **`dettaglio`**
(jsonb), non `tipo_evento`/`meta`; esiste anche **`origine`** con CHECK
`{SISTEMA,UTENTE,HANDLER,SCHEDULER}`. E soprattutto **`azione` ha un `CHECK`
whitelist** (`chk_giornale_azione`, 11 valori), quindi "tipo evento testuale
libero" (decisione §3.2 analisi) **non è applicabile com'è**.

**Decisione (Tid, 2026-06-07)**: sostituire la whitelist con regola a prefisso —
`CHECK (azione IN (<lista fissa attuale>) OR azione ~ '^DOMINIO_[A-Z][A-Z0-9_]*$')`.
Mantiene blindati gli 11 eventi di motore, ammette i `DOMINIO_*` liberi senza
nuove migration per evento. **Costo accettato**: nessuna protezione dai refusi
sui `DOMINIO_*` (mitigazione: elencarli nel catalogo BB; rivalutare promozione a
tabella `config` dopo 3-4 eventi reali). La fn mappa
`p_tipo_evento→azione`, `p_meta→dettaglio`, `origine='HANDLER'`. Nuovo test
pgTAP: `DOMINIO_*` accettato, nome arbitrario rifiutato.

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

### V15 — prerequisiti esito-aware → **RISOLTO (2026-06-07), estende il motore**

**Gap verificato**: `pratiche.flussi` **ha già** la colonna `esito`
(`POSITIVO/NEGATIVO/PARZIALE/NON_APPLICABILE`, CHECK `chk_flussi_esito`),
valorizzata da `completa_flusso`. Ma `fn_check_prerequisiti_flusso` considera un
prerequisito soddisfatto **solo** se il flusso precedente è in stato
`COMPLETATO` — **ignora l'esito**. Quindi oggi il motore lascerebbe avviare
`CONFERMA` anche dopo un `APPROVAZIONE_CLIENTE` chiuso `NEGATIVO`.

**Principio (Tid, da esperienza)**: una fase **deve** avere un esito, e
l'abilitazione del passo successivo dipende dall'esito del precedente. Non è
duplicazione del dominio: l'esito è proprietà **nativa** del workflow (il
preventivo `ACCETTATO/RIFIUTATO` ne è lo specchio, garantito coerente perché
"completa APPROVAZIONE_CLIENTE POSITIVO" e "preventivo→ACCETTATO" sono la stessa
azione del dialog).

**Decisione** → deliverable **B-PREREQ** (estensione motore, retro-compatibile):

1. Colonna `esito_richiesto` su `pratiche.template_flussi_prerequisiti`
   (`NULL` = qualsiasi esito = comportamento attuale → nessun workflow esistente
   cambia). CHECK sui valori dell'enum esito.
2. `fn_check_prerequisiti_flusso` (`CREATE OR REPLACE`, firma invariata): soddisfatto
   se prerequisito `COMPLETATO` **e** (`esito_richiesto IS NULL` OR
   `esito = esito_richiesto`).
3. Vincolo **`COMPLETATO ⇒ esito NOT NULL`** (guard/trigger su `flussi`): nessuna
   fase si chiude senza verdetto. **Nessuna sanatoria dati** richiesta (no
   produzione, conferma Tid 2026-06-07).
4. Seed: i 3 prerequisiti della catena preventivi con `esito_richiesto='POSITIVO'`.
5. pgTAP: prerequisito `COMPLETATO` con esito sbagliato → non soddisfatto; e
   completamento senza esito → bloccato. **Caveat**: i pgTAP esistenti che
   completano un flusso devono passare sempre un `esito` (grep prima — memoria
   `feedback_guard_breaks_existing_tests`).

---

## 4. Deliverable DB (cosa fare)

| ID | Oggetto | Cosa fare |
|---|---|---|
| ~~**B2**~~ ~~**B3**~~ | ~~`config.modalita_fatturazione` + seed~~ | **RIMOSSI** (modeling 2026-06-07). Niente tabella-vocabolario per un flag binario locale all'handler: il valore sta in `handler_params` (JSONB) ed è validato in codice dall'handler (`E_VENDITA_PARAM_MODALITA_FATTURAZIONE_INVALIDA`, B9). Tabella solo per valori di dominio condivisi/admin. Vedi §3 V10 |
| **B4** | Seed `pratiche.tipi_prestazione` | 2 righe `PREVENTIVI_IMMEDIATA`, `PREVENTIVI_DIFFERITA`; `categoria='COMMERCIALE'`; `pre_attivazione=false`, `post_attivazione=false` |
| **B5** | Seed `pratiche.template_flussi` (×2 tipi) | 4 flussi per tipo: `RICHIESTA_CLIENTE`→`PREVENTIVAZIONE`→`APPROVAZIONE_CLIENTE`→`CONFERMA`. Prerequisiti lineari con `esito_richiesto='POSITIVO'` (vedi B-PREREQ; il motore ora filtra per esito). Canali standard sui flussi ENTRATA. `CONFERMA` ha `handler_id` → riga B7 |
| **B-PREREQ** | Estensione motore prerequisiti esito-aware | (1) Colonna `esito_richiesto` su `template_flussi_prerequisiti` (`NULL`=qualsiasi, retro-compat). (2) `fn_check_prerequisiti_flusso` filtra su `COMPLETATO + esito`. (3) Vincolo `COMPLETATO ⇒ esito NOT NULL` su `flussi` (no sanatoria, no produzione). (4) pgTAP esito-aware + fix test esistenti che completano flussi. Vedi §3 V15 |
| **B6** | `handler_params` su `CONFERMA` (×2) | `PREVENTIVI_IMMEDIATA`: `{"modalita_fatturazione":"IMMEDIATA"}`; `PREVENTIVI_DIFFERITA`: `{"modalita_fatturazione":"DIFFERITA"}`. Valore = **stringa validata in codice dall'handler** (nessuna FK/tabella; l'handler la mappa su `fatturazione_immediata`+competenza) |
| **B7** | Seed `pratiche.handler_flussi` | 1 riga `handler_key='vendita.push_preventivo'`, `attivo=true`. `template_flussi.handler_id` dei due `CONFERMA` punta qui |
| **B-NEW** | Funzione scrittura giornale di dominio | (1) Nuova migration `DROP/ADD chk_giornale_azione` con regex `azione IN (<lista fissa>) OR azione ~ '^DOMINIO_[A-Z][A-Z0-9_]*$'`. (2) Funzione `pratiche.fn_log_evento_dominio(p_pratica_id, p_flusso_id, p_tipo_evento text, p_meta jsonb)`: INSERT controllato in `pratiche.giornale` mappando `azione=p_tipo_evento`, `dettaglio=p_meta`, `origine='HANDLER'`, stesso `tx_id`. (3) pgTAP: `DOMINIO_*` accettato, nome arbitrario rifiutato. Vedi §3 V11 |
| **B-GRANT** | GRANT `pratiche.competenze_flussi` | Concedere al ruolo applicativo Django i privilegi mancanti (sblocca smoke 26 / coda lavoro) |
| **B9** | Seed `config.messaggi_errore` | Registrare i codici di §6 (it). NB: `config.messaggi_errore` è **tabella** (chiave `(codice, lingua)`), il `.csv` del brief sorgente è solo il formato-seed |
| ~~**V9?**~~ | Commessa emittibile → **RISOLTO** | Non è più una domanda: serve la macchina di transizioni commesse (`vendite.transizioni_stati_commessa` + `fn_cambia_stato_commessa`) + approvazione righe. **Prerequisito = brief commesse separato** (non deliverable di questo brief). Dettaglio §3 V9 e §7.1 |

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

1. ~~**V9** (bloccante)~~ → **CHIUSO (2026-06-07)**. La commessa nata dal push
   non è emittibile e nessuna funzione esistente la rende tale. Decisione:
   **macchina di transizioni commesse** completa in un **brief commesse
   separato** (prerequisito), invocata dall'handler. Dettaglio §3 V9.
   *Aperto sub-punto (per il brief commesse, non bloccante qui)*: meccanismo
   approvazione righe — `fn_approva_commessa_attivita` dedicata (preferita) vs
   parametro su `fn_upsert_commessa_attivita`.
2. ~~**B-NEW**~~ → **CHIUSO (2026-06-07)**. Sì alla
   `pratiche.fn_log_evento_dominio(...)` append-only come unico canale, **ma** il
   `CHECK` whitelist su `azione` va sostituito con regex `DOMINIO_*` + lista
   fissa (la "nessuna whitelist" non è applicabile com'è). Dettaglio §3 V11.
3. ~~**B2**~~ → **CHIUSO (modeling 2026-06-07)**: la tabella
   `config.modalita_fatturazione` **non si fa** (B2/B3 rimossi). Il valore vive
   in `handler_params` JSONB, validato dall'handler. Regola generale e pattern
   futuro (descrittore parametri handler) in §3 V10. La convenzione `config.*`
   (PK `id` IDENTITY + `codice_interno`/`codice` UNIQUE + audit) resta documentata
   per quando servirà una *vera* tabella-vocabolario.

---

*Brief DB — Pratica PREVENTIVI / fatturazione immediata-differita — ZeroERP
(2026-06-06). Verificato contro schema reale. Da passare a `dev/db-tid`.*
