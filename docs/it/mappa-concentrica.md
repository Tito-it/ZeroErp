# Mappa Concentrica — Stato dello Sviluppo ZeroERP

> **Ultimo aggiornamento**: 31 ottobre 2026 — tutte le misure del documento valgono a questa data.
>
> Documento vivo. Aggiornare ad ogni milestone significativa.
>
> Riferimento metodologico: [sviluppo-concentrico.md](sviluppo-concentrico.md)

**Lo stato in breve.** ⭐ *La regola sta nel DB, una volta sola, e il DB la applica*: il permesso
sta nel verbo che scrive, ciò che si cambia dopo l'emissione lo decide il DB per famiglie di
colonne, e l'annullo con legami riapre a monte con la segnalazione. Il **modello del documento di
vendita** vale per tutti i documenti: le regole stanno in una
[guida](guide/modello-documento-di-vendita.md) — ogni cambio di stato da un verbo DB, si emette
solo da `/emetti/`, un documento nasce nel suo stato iniziale, il significato di uno stato si legge
dal vocabolario — e DDT, preventivo, ordine, contratto, offerta, commessa, fattura e versione di
listino lo seguono, DB e BE. **Anello 3 (`vendite`)**: il contratto si addebita anche a canone, a
periodi, con gli storni quando la fine si sposta; il preventivo scade da solo, e oltre la validità
non si accetta; un nome solo per ogni tipo di documento; l'azienda che emette è quella
del cliente, e gli indirizzi del documento seguono il cliente; righe e componenti con le stesse
regole in tutte le famiglie; la fattura in forma 4 (kit in tre modi, IVA per cassa, plafond sul
netto). **Anello 3 (`magazzino`)**: la bolla scarica e il reso ricarica la merce, BE/FE scritti,
il collaudo a video è da eseguire. **Anello 2**: il registro di magazzino è un servizio che non
conosce i suoi consumatori; sei modelli di stampa standard, e un emittente nuovo emette subito.
**Anello 1**: il soggetto senza valori inventati e coi dati fiscali e societari per natura, anche
alla nascita; un cliente manuale per soggetto e utility; un indirizzo fisico, una riga; i
parametri senza override, col valore nella sua forma; il profilo del reparto per area, col tetto
d'area detto dal DB; l'area Accessi col secondo fattore. **Anello 0**: ruoli di sistema
fissi, ambiente dichiarato all'installazione e processi accesi per ambiente; un solo fuso
aziendale; chi guarda si calcola una volta per istruzione; i presidi parlano a chi deve agire;
Idempotency-Key obbligatoria sui POST che scrivono e documentazione API uguale al codice.
⚠️ Aperto: il canone in commessa (l'obbligo della periodicità, il collaudo); la soglia della
ricerca, lato BE; i collaudi a video di bolla, reso e inventario; D18, L-5, il passo 3 del verbo; il divario fra il
registro pgTAP della CI e quello di sviluppo.

> *La storia — che cosa è atterrato e quando — sta nel [changelog della mappa](dev/mappa-concentrica-changelog.md).*
>
> **Come è fatto questo documento.** §1 la **forma** del sistema (anelli, natura,
> dipendenze) — cambia di rado. §2 lo **stato corrente** per anello — cambia a
> ogni milestone. §3 la **roadmap**: solo lavori in corso o previsti, mai storia.
> §4 le **lezioni metodologiche**, che spiegano *perché* la mappa è fatta così.
> ⛔ Qui non ci sono date di esecuzione né serie storiche: il *quando* sta **solo** nel changelog.

---

## 1 · La forma del sistema

## Visione d'insieme

```
                    ┌─────────────────────────────────────────────┐
                    │           ANELLO 3 — PROCESSI               │
                    │                                             │
                    │   vendite    acquisti    magazzino          │
                    │   pagamenti  contabilita*                   │
                    │                                             │
                    │  ┌───────────────────────────────────────┐  │
                    │  │    ANELLO 2 — ORCHESTRAZIONE          │  │
                    │  │                                       │  │
                    │  │      pratiche      documenti          │  │
                    │  │    (workflow, giornale,               │  │
                    │  │     generazione, handler,             │  │
                    │  │     sospensioni, calcoli tempo;       │  │
                    │  │     template, asset, PDF generati)    │  │
                    │  │   registro di magazzino               │  │
                    │  │    (movimenti, giacenza, primitiva)   │  │
                    │  │                                       │  │
                    │  │  ┌─────────────────────────────────┐  │  │
                    │  │  │  ANELLO 1 — DATI BASE           │  │  │
                    │  │  │                                 │  │  │
                    │  │  │  config  anagrafiche  catalogo  │  │  │
                    │  │  │                 ui              │  │  │
                    │  │  │  ┌───────────────────────────┐  │  │  │
                    │  │  │  │  ANELLO 0 — NUCLEO        │  │  │  │
                    │  │  │  │                           │  │  │  │
                    │  │  │  │  core (infrastruttura)    │  │  │  │
                    │  │  │  │  dbops, script            │  │  │  │
                    │  │  │  │                           │  │  │  │
                    │  │  │  └───────────────────────────┘  │  │  │
                    │  │  └─────────────────────────────────┘  │  │
                    │  └───────────────────────────────────────┘  │
                    └─────────────────────────────────────────────┘
```

**Regola fondamentale**: ogni anello dipende solo dagli anelli interni. Mai dipendenze inverse o laterali.

⭐ **Il registro di magazzino è un servizio dell'anello 2, non un processo** (decisione di Tid).
Lo schema `magazzino` contiene **due cose**: il **registro** — magazzini,
ubicazioni, lotti, seriali, causali, movimenti, valore, disponibilità, blocchi, la primitiva
`fn_scrivi_movimento` e lo storno — che ogni documento che muove merce **usa**, come usa
`documenti` per stampare; e i **documenti di magazzino** — inventari, rettifiche, trasferimenti
interni — che sono processi dell'anello 3 come la bolla. Così la bolla e il reso che scaricano e
ricaricano la merce dipendono da un anello **interno**, e la regola resta intera, senza
eccezioni. ⛔ Il verso opposto è vietato: **il registro non conosce i suoi consumatori**. Chi
scrive merce scrive il proprio posting nel proprio schema e chiama la primitiva; il registro
nomina le origini solo attraverso il catalogo `config.sorgenti`. ⭐ La regola **si legge da
sola**: il cancello `dbops.vw_magazzino_dipendenze_inverse` (CI) pretende che
nessun oggetto di `magazzino` — funzione, vista, FK, trigger, policy, default — nomini uno
schema di processo (`vendite`, `acquisti`, `pagamenti`, elenco scritto nella vista).

⛔ **`contabilita*` sta fuori dal perimetro, e lo schema è VUOTO** — zero tabelle, zero
funzioni, zero viste. Non è un processo di Anello 3 e non c'è niente da finire: vedi §2.

## Cronologia aggiornamenti

La storia datata (cosa e' atterrato, quando, con quale impatto sulla mappa) vive **solo** in [mappa-concentrica-changelog.md](dev/mappa-concentrica-changelog.md). Qui c'e' lo **stato corrente** per anello (§2) e cio' che e' aperto (§3).

⚠️ **Non aggiungere cronologia a questo documento.** E' la deriva che lo ha gonfiato in passato: ogni riga «fatto il giorno X» che entra nelle tabelle di stato le trasforma in un secondo changelog, meno curato del primo.

## Natura degli anelli (post-aggiornamento manifesto §III bis)

Ogni anello e' classificato come **autocontenuto** o **di servizio**. La distinzione non riguarda la direzione delle dipendenze (sempre verso l'interno), ma l'**ordine di costruzione** raccomandato.

| Tipo              | Significato                                                                                       | Costruzione                                                                                                                                                                                        |
| ----------------- | ------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Autocontenuto** | Ha un end-to-end di valore proprio (es. "gestisco anagrafica clienti"). Validabile in isolamento. | Si puo' costruire e dichiarare operativo da solo.                                                                                                                                                  |
| **Di servizio**   | Motore/infrastruttura per altri anelli. Senza consumatori esterni reali e' un'astrazione teorica. | Va costruito **dopo o in parallelo** ai consumatori, mai prima. Resta "predisposto, in attesa di validazione" finche' almeno due consumatori reali non l'hanno esercitato (manifesto principio 7). |

| Anello                                       | Natura                       |
| -------------------------------------------- | ---------------------------- |
| 0 — Nucleo Infrastrutturale                  | **Di servizio**              |
| 1 — Dati Base                                | **Autocontenuto**            |
| 2 — Orchestrazione (`pratiche`, `documenti`) | **Di servizio**              |
| 3 — Processi Operativi                       | **Autocontenuti** (ciascuno) |

---

## 2 · Stato corrente per anello

## Anello 0 — Nucleo Infrastrutturale

> **Natura: di servizio.** Il protocollo operativo del sistema. Si tocca solo per correggere limiti reali.

| Componente    | Tipo       | Stato     | Descrizione                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------------- | ---------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `core`        | App Django | Operativo | error_manager, middleware, permissions, endpoint_helpers, pagination, throttling, tracciamento processi/job, audit sessioni, request log                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `dbops`       | Schema DB  | Operativo | fn_run_automations, apply_fk_index_policy, registry task, vw_duplicate_indexes, audit_log (**append-only per l'app**: `REVOKE UPDATE/DELETE`, cancello sugli scrittori), sessioni_utente, request_log, **automazione daterange**, **anti-overlap parametrico** (`automazione_overlap`: `where_predicate`/`key_expressions` + runner notturno auto-guarigione), **chiusura parametrica per scadenza**, **coda lavori generica** (`coda_lavori`: job queue DB-native transazionale, senza broker), **catalogo dei processi** (`processi`: `tolleranza_minuti` come contratto di vitalità, `avvio_manuale` — è il dato dietro «Esegui ora») e **dei presidi** (`presidi`, **49** a catalogo); il catalogo dei processi dice anche **come si eseguono in CI** (`ci_ordine` / `ci_procedura` / `ci_esclusione`: un `ci_apply` chiama in ordine le 11 procedure strutturali che su un DB da zero nessun job lancerebbe); `sec_functions_owner` **in sola lettura per l'app** (la sync si difende nel corpo), **registri del debito a criterio** (`rls_perimetro_debito`, `storico_scope_policy`), **`error_log`** consultabile dietro permesso (`AdminAPIView`) — guida: [automazione DB](guide/automazione-db.md) |
| `script`      | Schema DB  | Operativo | fn_log_and_raise_error (**il codice errore viaggia nel campo strutturato `CONSTRAINT` su `P0001`**, non nel testo), viste e funzioni riusabili, helpers generici trigger (guard coerenza BoM, immutabilità, **date di validità** in una sede sola), `fn_get_conto_bancario_predefinito`; i **BB del permesso nel verbo** (`fn_guard_azione`, `fn_guard_livello`, `fn_guard_super_admin`), l'**ereditato** dei permessi (`fn_get_permessi_ereditati_*`), il **prezzo autorizzato** (`fn_check_prezzi_autorizzati`) e l'**imponibile di riga** (`fn_imponibile_riga`)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `public`      | Schema DB  | Operativo | ⛔ **Nessuna tabella**: `version_info` — una riga, zero lettori — è stata ritirata (la versione applicata si legge da `DATABASECHANGELOG`). Ospita le **estensioni** (`dblink`, `unaccent`, `postgis`, `plpgsql_check`): è il motivo per cui il `search_path` di una `SECURITY DEFINER` che le chiama non può escludere `public`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `maintenance` | Schema DB  | Operativo | Job schedulati pgAgent, job_run_log, **guardiano del digest** (`proc_guardiano_digest_job`, ogni ora: se il digest tace, accoda la notifica su `coda_lavori`). `zeroerp_app` **legge** `job_run_log` dal provisioning (`USAGE` + solo `SELECT`, col suo pgTAP di postura): era un privilegio dato a mano su dev, e senza di esso i test Django in CI non passavano — guida: [lavori automatici](guide/processi-automatici-classe-e-identita.md) |

### Cosa fornisce agli anelli esterni

- Error handling centralizzato (`ServiceError`, `ErrorManager.require`)
- Middleware API (exception handling, JWT audit, request context, request log)
- Pattern uniformi: `handle_post_json`, paginazione, throttling, search validators
- Automazioni DB: audit fields, tx_id, storicizzazione, lock colonne, protezione attivo, **`validita` STORED generated** (PG 18, nessun trigger), chiusura parametrica per scadenza (`dbops.fn_apply_chiusura_scadenze`)
- **Coda lavori generica** (`dbops.coda_lavori`): esecuzione asincrona di job per qualsiasi dominio — accodamento transazionale nella stessa transazione che genera il lavoro, worker che drena, idempotenza. Fondazione async dell'ERP: primo consumatore il giro fatturazione on-demand. Guida: [gestione-code-di-lavoro.md](guide/gestione-code-di-lavoro.md)
- **Errore di dominio come contratto**: il codice viaggia in un **campo strutturato** dell'eccezione (`SQLSTATE P0001` + `CONSTRAINT`), letto in **un solo punto** lato backend. Il suo **significato** — la `classe` — sta a catalogo in Anello 1; status HTTP e `ui_action` si derivano. Due registri del debito (`dbops.codici_errore_senza_policy`, `dbops.messaggi_errore_codici_legacy`) restano **a zero righe**, come presidio di ciò che arriverà — guida: [cosa esce dall'eccezione](guide/Messaggi-di-Errore-e-Generazione-Log.md#cosa-esce-dalleccezione-oltre-al-testo), [presidio del codice](guide/presidi-e-registri-del-debito.md#33-il-codice-errore-che-arriva-al-backend)
- **Presidio dei riferimenti morti**: un riferimento a un oggetto DB che non esiste più non arriva al merge. ⚠️ Il guardrail gira **dopo** `manage.py migrate`. ⚠️ E il checker si è preso due lezioni: il `search_path` del chiamante gli cambiava la risposta (784 fantasmi nel digest, zero in lettura diretta), e su una `DEFINER` di un altro proprietario rispondeva **per ruolo** (ottava classe `FP_DEFINER_PRIVILEGIO`, l'esenzione pgAgent **segue la macchina**) — guida: [presidi §3.1](guide/presidi-e-registri-del-debito.md#31-riferimenti-morti-nelle-funzioni-del-database)
- **Contratto di vitalità dei processi**: ogni processo del catalogo `dbops.processi` dichiara la propria `tolleranza_minuti`; il panorama `vw_processi_programmazione` dice `OK` / `MUTO` / `MAI_PARTITO`, il listener si presidia dalla **sessione** (`application_name`), le code (lavori, stampa, email) hanno una vista `ZERO` ciascuna, e un **guardiano pgAgent** avvisa se il digest stesso tace. *Il discriminante non è «ogni quanto gira»: è «qualcuno aspetta l'esito, e in quanto tempo se ne accorge?»* — guida: [i controlli che guardano il quadro](guide/processi-automatici-classe-e-identita.md#i-controlli-che-guardano-il-quadro)
- **Postura degli oggetti per criterio**: tre pgTAP sul catalogo, non su elenchi — ogni `SECURITY DEFINER` ha un `search_path` pinnato (⚠️ deciso **per funzione**: chi chiama un'estensione tiene `public`), i registri di audit sono append-only per l'app, e lo schema `django` è nel provisioning come gli altri. ⭐ La regola che li tiene insieme — *un privilegio che esiste su una macchina è un ricordo, non una configurazione* — ha avuto la sua **quarta occorrenza** su `maintenance.job_run_log`, chiusa con un blocco in `scripts/sql/provision_zeroerp.sql`, fase `post` **e** un changeSet `90_end` gemello per i database già provisionati. ⚠️ **Aperto**: `zeroerp_log` in CI non ha `USAGE` su `dbops`, quindi ogni test Django lavora con `tx_id = uuid_nil` **verde per sottrazione** (16 114 righe `permission denied` in una corsa verde) — due strade, la decisione è di Tid — guida: [guardrail DB e test di sicurezza](dev/sicurezza-e-qualita-statica.md#guardrail-db-e-test-di-sicurezza)
- **Osservabilità**: i **sette passi** dell'analisi sono a codice. La riga di `event_log` dice chi, per chi e in che giro; «**Errori tecnici**» (`dbops.error_log`, dietro `AdminAPIView`) e «**Giornale eventi**» (`vendite/giornale`) si consultano dall'app; il **pallino dei presidi** in topbar porta il contatore del catalogo; la **retention** (`cleanup_at` + purge) copre anche i log di fatturazione. ⭐ E il **verdetto «lotto fermo» nasce a DB** (`vw_lotti_fermi_da_guardare`), al posto della copia Python: *si sposta la sede, non si copia*. ⚠️ Residui dichiarati: il Giornale eventi **non è multi-emittente** (serve una colonna nei quattro rami della vista), il **catalogo dei registri** del giornale (`config.registri_giornale`: DB chiuso, BE da fare) e il pallino **per l'operatore** (permessi sui presidi, rimandato) — guida: [quale log risponde a quale domanda](guide/Messaggi-di-Errore-e-Generazione-Log.md#quale-log-risponde-a-quale-domanda), [investigare un'anomalia](guide/audit-e-tracciabilita.md#52-investigare-unanomalia-percorso-tipo)
- **Il permesso sta nel verbo che scrive**: *il DB calcolava i permessi ma non li applicava*. Il modello — *una scrittura = un verbo* — vuole che il verbo dichiari il permesso nella prima riga con un BB unico e che l'applicazione perda la scrittura sulle tabelle protette e l'`EXECUTE` sulle primitive. Esercitato dal **magazzino** (inventario e rettifica chiedono `registra_magazzino`) e dal **pannello config** (`fn_pannello_scrivi`: livello sull'oggetto della riga, lista ammessa in `config.tabelle_gestibili`); ⚠️ il **passo 3** (i domini esistenti) è aperto e senza data — il modello sta nella [guida dei permessi §7.4](guide/architettura-permessi-e-autorizzazioni.md#74-il-permesso-nel-verbo-di-scrittura). Il verso opposto lo garantisce il BE: ogni `GET`/`HEAD` gira in `SET TRANSACTION READ ONLY`, *una lettura non scrive* è una garanzia del DB
- **Un lock, una sede**: il registro `automation_lock_columns` è l'**unica** sede di un lock di colonna, un runner solo converge (crea/rigenera/toglie) e il codice nei `tgargs` è letto anche dal guardrail — *un valore che viaggia come dato non si trova cercando codice*. Il rubinetto dello `storico` verifica la colonna FK prima di montare il trigger — guida: [LOCK_COLUMNS](guide/automazione-db.md#41-lock_columns-blocco-colonne-critiche)
- **Un solo fuso aziendale**: il fuso dell'azienda è un dato (`SYSTEM_FUSO_ORARIO`) con una sede sola (`script.fn_fuso_operativo`, `fn_giorno_operativo`); niente `CURRENT_DATE` nel DB, `oggi_aziendale()` nel BE, una sede delle date nel FE, e pgTAP e vitest girano in un fuso ostile. *Se cambiare il fuso di chi esegue cambia un risultato, quello è un difetto*. Nella stessa famiglia: ogni colonna `numeric` rifiuta `NaN` e infiniti (170 CHECK) — guida: [parametri](guide/configurazione-e-gestione-parametri.md), [timestamptz](linee-guida-sql.md#1110-timestamp-nudo-e-senza-fuso-si-scrive-timestamptz-sempre)
- **L'installazione è un dato**: i **ruoli di sistema** sono fissi e fanno parte del prodotto (`zeroerp_owner`, `zeroerp_app`, `zeroerp_job`, `zeroerp_log`), creati da un solo script idempotente per CI, scratch e installazione — chi personalizza *aggiunge un membro, non rinomina*, e si controlla la membership, mai il nome. L'**ambiente** (`SVILUPPO`/`PRODUZIONE`) è un dato scelto all'installazione e senza default, l'accensione dei processi ha un default per ambiente in `dbops.processi` più l'accensione a mano, e i dati di sviluppo hanno un verbo che rifiuta la produzione — guida: [i ruoli all'installazione](installazione.md#i-ruoli-nomi-fissi-uguali-ovunque), [i ruoli di sistema](dev/backend/provisioning-db-roles.md#i-ruoli-di-sistema), [l'ambiente, passo 8](installazione.md#lordine-dei-passi), [accendere un processo](guide/automazione-db.md#10-dallinterfaccia-i-processi-automatici)
- **Le operazioni che non si ripetono**: l'**Idempotency-Key è obbligatoria su ogni POST che scrive**, con la soglia letta dal DB (`dbops.fn_idempotency_soglia_secondi()`) e le chiavi nella pulizia; la documentazione API copre 721 rotte su 721 e coincide col codice ([guida](guide/operazioni-che-non-si-ripetono.md))
- **Il bersaglio dell'errore**: oltre a *cosa* è successo, un errore dichiara **su quale entità** — una coordinata che il backend porta nell'envelope (`targets`) e il frontend trasforma in un gesto («vai lì»). Convenzione unica su tutti e tre i canali di `fn_log_and_raise_error`, presidiata in CI (`dbops.vw_bersagli_non_dichiarati` vuota) — guida: [il nome del campo si dichiara](guide/Messaggi-di-Errore-e-Generazione-Log.md#il-nome-del-campo-non-si-scrive-si-dichiara)
- **Tracciamento processi e job**: API per audit log, task registry multi-dominio, job run log (6 endpoint REST, 27 test) — guida: [tracciamento processi e job](guide/analisi-tracciamento-processi-e-job.md)
- **Audit sessioni**: login/refresh JWT tracciati in `dbops.sessioni_utente` con IP, user_agent, request_id (19 test) — guida: [sessioni utente](guide/audit-e-tracciabilita.md#3-strato-2-sessioni-utente)
- **Request logging**: ogni request `/api/*` registrata in `dbops.request_log` con metodo, path, status, durata — guida: [request log](guide/audit-e-tracciabilita.md#4-strato-3-request-log)
- **Token blacklist**: refresh token rotation con blacklist automatica (SimpleJWT `token_blacklist`) — guida: [revoca token](guide/audit-e-tracciabilita.md#34-revoca-token-blacklist)
- Policy indici FK automatica
- Logging e raise errori DB (`script.fn_log_and_raise_error`)

### Audit sessioni, request logging e token blacklist

Guida: [audit e tracciabilità](guide/audit-e-tracciabilita.md).

| Capacita'                         | Componente DB               | Componente Backend                                                             | Stato     |
| --------------------------------- | --------------------------- | ------------------------------------------------------------------------------ | --------- |
| Audit sessioni (login/refresh)    | `dbops.sessioni_utente`     | `session_audit_service` + `AuditTokenObtainPairView` / `AuditTokenRefreshView` | Operativo |
| Request logging (chi chiama cosa) | `dbops.request_log`         | `RequestLogMiddleware`                                                         | Operativo |
| Token blacklist e revoca          | SimpleJWT `token_blacklist` | Settings `ROTATE_REFRESH_TOKENS` + `BLACKLIST_AFTER_ROTATION`                  | Operativo |

Estensioni non-breaking: nuove tabelle in `dbops`, nuovo middleware in `core`, override view JWT. Nessun contratto esistente modificato. Gli anelli esterni ne beneficiano automaticamente senza alcuna modifica al proprio codice.

### 🔴 I test girano come l'applicazione

*Guida: [quando il test non può girare come l'applicazione](guide/pgtap-come-si-scrive-un-test.md#quando-il-test-non-puo-girare-come-lapplicazione), [girano in CI?](guide/pgtap-come-si-scrive-un-test.md#girano-in-ci), [baseline dei test rossi](guide/presidi-e-registri-del-debito.md#32-baseline-dei-test-rossi)*

Cambio di regime, non una rifinitura: il runner pgTAP di default è l'**utente
applicativo**, non l'owner. **Le policy RLS sono esercitate a ogni corsa.**

|                        |                                                                                                                                                                                                                                                                              |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Conseguenza            | un rosso può essere un **permesso** o una **policy**, non solo una fixture; una fixture che scrive dove l'applicazione non scrive **non passa più**                                                                                                                          |
| Eccezioni              | 29 file marcati `owner`, ognuno **con la ragione scritta**                                                                                                                                                                                                                   |
| In CI                  | sempre sulle PR verso `main`; sui push a `Tito-dev` solo se toccano `db/` o `scripts/`. Baseline **separata**: il DB della CI è ricostruito da zero, quello di sviluppo ha dati veri — i rossi sono **popolazioni diverse**                                                  |
| Preambolo obbligatorio | `BEGIN`, riga di contesto, `SET CONSTRAINTS ALL IMMEDIATE` — presidiato da un cancello. Senza, un file diventa **verde per sottrazione**                                                                                                                                     |
| Debito noto            | **4 rossi** su **917 file** sul database di sviluppo; **358** nel registro della CI — ⚠️ le corse vere misurano meno, ma il registro scende solo col rientro certificato. È un registro che deve calare, non una lista di eccezioni |

⭐ **La stessa scelta vale per i test Django in CI**, che girano
come `zeroerp_app` e non come l'owner del database: *l'owner di una tabella
**salta la RLS*** (il repo rifiuta `FORCE ROW LEVEL SECURITY` apposta). Il primo effetto è stato un rosso vero, non un fastidio: un test
end-to-end che pretendeva il **404 no-leak** dell'altro emittente, col ruolo owner
vedeva tutto e passava. La RLS si esercita solo con un ruolo **non owner e
NOBYPASSRLS** — in CI come nel runner pgTAP.

### 🔴 Il perimetro dei dati ha un criterio, non un elenco

*Guida: [una tabella fuori dal perimetro](dev/trappole.md#non-far-nascere-una-tabella-fuori-dal-perimetro-dei-dati), [RLS](guide/architettura-multi-face-auth.md#6-row-level-security-la-difesa-al-livello-giusto)*

Il perimetro RLS era scritto come **elenco a mano**, e un elenco ha per confine
ciò che chi lo scriveva aveva in mente: mancavano sei figlie di `vendite.fatture`
e le sette partizioni di `vendite.note`.

|                     |                                                                                                                                                        |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Come si misura ora  | `dbops.vw_rls_perimetro_scoperto` — criterio **transitivo**: *ogni tabella con una FK verso una tabella in RLS*                                        |
| Dove vive il debito | `dbops.rls_perimetro_debito`, una riga per tabella **con la sua ragione tecnica**                                                                      |
| L'invariante        | ⛔ **non** «la vista è vuota»: è «nessuna riga fuori da `DEBITO_DICHIARATO`». Un cancello rosso dal primo giorno viene disattivato                      |
| Stato               | **8 righe** di debito dichiarato. Le tabelle nuove entrano nel criterio **da sole** |

⚠️ **Ciò che il criterio NON vede**: lo schema `storico` — le shadow sono
**gemelle** delle madri, non figlie, e nessuna FK le lega. Hanno
un perimetro **loro**: lo scope si **cattura alla scrittura e si congela**
nella riga (`origine_schema` + `scope_emittente_fiscale_id`) — *un archivio che
cambia quando cambia il presente non è un archivio* — la mappa
`dbops.storico_scope_policy` dice per ogni madre dove sta lo scope (colonna,
risalita al padre con ripiego sul suo archivio, billing account), la policy la
genera lo stesso framework che genera la shadow (**37 armate**, l'applicazione
non può cancellare una versione), e `dbops.vw_storico_scope_da_dichiarare`
presidia le shadow che non lo portano.

⭐ **E la riserva del resolver è di chi agisce**: un billing
account non ancora collegato a un emittente appartiene a chi lo sta creando —
prima, l'operatore di un emittente non di default non poteva aprire un cliente
(`RETURNING` respinto dalla policy, perché il legame lo scrive un trigger
`AFTER`). Su un'installazione a due emittenti il secondo era chiuso fuori.

### 🧪 I presidi hanno un catalogo

`dbops.presidi` raccoglie i presidi del progetto (**49** a catalogo, fra cui C1, C2, `vw_funzioni_check_codici`,
il lotto chiuso con errori, il DDT emesso senza scarico, il reso confermato senza
carico), con un
**contatore onesto**: un presidio che non ha mai girato non conta come copertura.
Il **digest** — giornaliero e settimanale — arriva a una persona, un guardiano pgAgent avvisa se il digest stesso tace, e **il
contatore è anche a video**: il pallino dei presidi in topbar, sullo
stesso metro del digest. ⭐ E in CI vale il corollario — *un cancello non deve
poter zittire un altro cancello*: un guardrail che fallisce e ne maschera un
secondo lascia passare due difetti al prezzo di uno. ⚠️
**Tre presidi hanno mentito** (il checker dei riferimenti morti, due volte; il
panorama dei processi), sempre per un difetto del **metro** — il `search_path`
ereditato, una colonna di `pg_stat_activity` mascherata per ruolo, una risposta
che dipendeva da chi chiedeva. *Un presidio si prova dal percorso che lo
attraversa*, non dalla propria sessione. ⚠️ **E altri due hanno parlato
in CI**: la lista `dbops.error_log` entrata fra le globali senza
dichiararsi nell'elenco del pgTAP, e il `SELECT` di `zeroerp_app` su
`maintenance.job_run_log` che esisteva **solo su dev** — due rossi che hanno
fatto il loro lavoro, non due incidenti. Quali presidi sono e dove vivono:
`dbops.presidi` è il catalogo, la guida
[presidi-e-registri-del-debito.md](guide/presidi-e-registri-del-debito.md) li
spiega.
⭐ **E i due presidi del percorso storto ci sono**: uno **stato
ammesso e mai scritto** è una promessa vuota (C1, registro
`dbops.stati_check_dichiarazioni`), e la `ui_action` promessa all'interfaccia
deve avere il canale che la realizza (C2, `vw_punti_canale_campo` a `CANCELLO`) — guida: [uno stato previsto e mai scritto](guide/presidi-e-registri-del-debito.md#36-uno-stato-previsto-dal-modello-e-mai-scritto).

### Stabilita'

Stabile. Modifiche solo per correzioni o estensioni non-breaking (nuove policy, nuovi middleware).

---

## Anello 1 — Dati Base e Configurazione

> **Natura: autocontenuto.** Entita' di riferimento condivise da tutti i processi. Vocabolario comune del sistema.

| Componente     | Tipo       | DB        | Backend   | Frontend  | Descrizione                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| -------------- | ---------- | --------- | --------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `config`       | App Django | Operativo | Operativo | Operativo | Stati, nazioni, UO, termini pagamento, priorita', canali; policy operative trasversali; impostazioni parametri multi-scope; **catalogo dei codici errore** (`classi_errore` 10 classi; 831 righe nel seed) — il **significato** di un errore è un dato di riferimento, lo status HTTP no; **nature del documento fiscale** (`nature_doc_fiscale`) e **tipi di titolo IVA** (`tipi_titolo_iva`); **modi di approvvigionamento** (`modi_approvvigionamento`: acquisto / produzione / stock / non applicabile — la dimensione «da dove arriva» dell'articolo, ortogonale alla natura di vendita che dice «dove va»); il registro email distingue **`SIMULATA`** (stampata a video, terminale e voluta) da `SENT` — una mail non spedita non si registra più come consegnata; il **catalogo dei registri del giornale** (`registri_giornale`, chiuso lato DB col suo pgTAP, il BE da fare: la tendina «Registro» smette di mostrare `EVENT_LOG` grezzo). ⭐ Anche la **credenziale** (`credenziali` + `credenziali_provenienze`: lo stato del login non sta più sulla veste; freno sulla provenienza, attesa crescente, **blocco solo da SUPER_ADMIN**; l'obbligo del secondo fattore sta sulla credenziale o sul profilo, il device TOTP si scrive solo dai verbi), le **mail per ambito** (la RLS applica OPERATORE/REPARTO in AND con l'emittente; una mail inviata non si cancella) e le **tabelle gestibili** (`tabelle_gestibili`: la lista del pannello è un dato, scritta da un verbo; `aree_funzionali` è in **sola lettura** per l'app — il CSV è l'unico padrone) — guida: [parametri](guide/configurazione-e-gestione-parametri.md) |
| `anagrafiche`  | App Django | Operativo | Operativo | Operativo | Soggetti, indirizzi, contatti, risorse umane, emittenti fiscali, billing account; **titoli IVA del soggetto** (`soggetti_titoli_iva` + ambiti + registro movimenti **append-only**, dove anche l'annullo di una forzatura è un movimento) — è da qui, e non da un default sul cliente, che il soggetto influenza l'IVA. Il ponte utente↔risorsa umana è **solo** `identita_digitali` (che è la **veste**, la porta da cui si entra: le colonne del login sono passate alla credenziale in `config` — *cambia la porta, non il ciclo di vita*): la vista col nome vecchio (`risorse_umane_auth_user`, una proiezione filtrata che rispondeva zero righe in silenzio) è ritirata, lettori DB riscritti sulla madre. Un **billing account non ancora collegato appartiene a chi lo sta creando** (riserva del resolver a tre livelli: mapping, emittente dell'operatore in sessione, default) — guida: [soggetti e ruoli](guide/soggetti-e-ruoli-anagrafici.md), [generazione cliente](guide/generazione-cliente.md), [indirizzi](guide/gestione-degli-indirizzi.md), [risorse umane](guide/risorse-umane-e-accessi.md) |
| `catalogo`     | App Django | Operativo | Operativo | Operativo | Articoli (CRUD, UoM, BoM, note) — **completato e testato**. L'articolo dichiara **da dove arriva** (`modo_approvvigionamento_id`, default `ACQUISTO`), se **movimenta giacenza** (`gestito_a_magazzino`, default fail-safe `false`: al rilascio tutti `false`, la merce va marcata) e il `lead_time_giorni`; in lista e drawer via `vw_articoli_dettaglio`. È il perno da cui partono `acquisti` («si compra?») e `magazzino` («movimenta?»). ✅ E la **prontezza** ha il suo presidio a catalogo (`vw_articoli_a_magazzino_prontezza`: una riga, `stato_atteso = MARCATI`) — era la voce che il Lotto 1 di `magazzino` aveva lasciato dichiarata e non scritta                                                                                                                                                                                                                                                                                 |
| `amm-software` | App Django | Operativo | Operativo | Operativo | Gestione operatori, permessi riepilogo, profili reparto, audit log (solo ADMIN), drawer dedicato gestione permessi; il **catalogo degli oggetti personalizzabili** coincide con le quattro porte (BE, FE, verbo DB, catalogo: 27 righe, 17 personalizzabili e 10 riservate, la regola sta in una FK) e l'**ereditato** si calcola a DB (i permessi da operatore contano solo la veste `OPERATORE`). Il **livello dell'area è un tetto**: un permesso specifico può solo restringere quello della sua area, mai allargarlo; il pannello è master-detail per area, e i permessi si leggono nella lista Operatori («Mostra permessi»), non più in una matrice a parte. «Operatori» è diventata l'area **Accessi** (Operatori / Altri accessi / Di sistema) — guida: [risorse umane e accessi](guide/risorse-umane-e-accessi.md), [permessi](guide/architettura-permessi-e-autorizzazioni.md) |
| `ui`           | App Django | Operativo | Operativo | Operativo | Metadato di presentazione: liste configurabili + **dashboard home** (catalogo widget, composizione, preferenza utente), preset per profilo/emittente/sistema. Di servizio. **Due famiglie di consumatori reali**: liste (clienti/fornitori/contratti…) e home a card KPI (`fn_resolve_dashboard_config`). Il **perimetro emittente è un dato della lista**: `perimetro_emittente` sta nella **colonna** di `lista_definizione.csv` (colonne 872/873 a catalogo), `operatori` e `lista_preset` sono certificate `multi_emittente`, e il **seed laterale è ritirato** — *una tabella, un CSV*. ⭐ E la lista **dice da sé che cosa è**: in quali colonne si cerca (`ricercabile_full` letto a ogni ricerca, filtrato dai permessi di colonna), da quanti caratteri (`ricerca_min_caratteri`), con quali misure di pagina (`ui.misure_pagina`: 10/25/50/100, default compreso) — tre fatti che stavano in tre sedi ciascuno — guida: [liste](guide/configurazione-liste.md) |

> **Multi-Face Auth — RLS accesa, restano le API di dominio.** Lo stato vivo — che cosa manca per portale clienti/fornitori e shop B2C, che cosa è costruito e che cosa no — sta nella [guida, §12](guide/architettura-multi-face-auth.md#12-stato-ed-evoluzioni): **è lì che si aggiorna**, e non va ripetuto qui. In una riga: il bridge `identita_digitali` serve tutte le vesti, la **RLS è attiva** per gli operatori sullo scope emittente fiscale (dalle 10 tabelle documentali fino a righe, satelliti e versioni di **storico** — Anello 0, §«Il perimetro dei dati ha un criterio»), e le **API di dominio portale/shop** (fatture, ordini, catalogo B2C) **non** sono sviluppate: si aprono «quando il business lo richiederà». Architettura: [architettura-multi-face-auth.md](guide/architettura-multi-face-auth.md) §14.

### Frontend Anello 1 — Stato dettagliato

| Area                            | Stato      | Note                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ------------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Gestione Geografica             | Operativo  | 7 tab: indirizzi, toponomastica, comuni, CAP, province, regioni, stati — CRUD completo. UI da migliorare — guida: [indirizzi](guide/gestione-degli-indirizzi.md), [riclassificazione vie](guide/riclassificazione-vie.md) |
| Gestione Soggetti               | In test UI | PF/PG/ENTE end-to-end, 3 building block, ruoli, CF validator IT con omocodia — guida: [soggetti e ruoli](guide/soggetti-e-ruoli-anagrafici.md) |
| Pannello Config                 | Operativo  | Tabelle CRUD generiche con drawer dinamico, metadata-driven: la lista è un **dato del DB** (`config.tabelle_gestibili`, 87 voci, **63 nel pannello**) e la scrittura passa da **un verbo** che chiede il livello sull'oggetto della riga; fuori le tabelle con RLS, i profili, le aree e le anagrafiche di magazzino (che hanno casa propria)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Building block soggetto         | Operativo  | SoggettoForm, ContattoForm, IndirizzoSoggettoForm, DatiSocietariForm, ComuneAutocomplete, StradarioAutocomplete, StradarioGeneraleAutocomplete                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Modalita' sola lettura          | Operativo  | Pattern protect CSS + provide/inject: tutti i drawer con app-readonly, 2 componenti core auto-hide (NewButton, DrawerFooter)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| Azioni processo (Livello 2)     | Operativo  | Prop `action` su NewButton/DrawerFooter, composable useActionPermission, mappa da /me/                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |

#### Amministrazione software

| Area                            | Stato      | Note                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ------------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Amm. Software — Operatori       | Operativo  | Lista con filtri/sort, drawer crea/modifica unificato, tab permessi override, rename utenti→operatori                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| Amm. Software — Profili         | Operativo  | Lista reparti; il profilo si gestisce **per area** come l'operatore (BB `ElencoDettaglio`: elenco delle aree, dettaglio a destra; `MatriceCatalogo` per le azioni), confirm save; il limite dell'area sui valori salvati lo dice il DB (`limitata_da_area`), il FE solo in anteprima — guida: [ereditarietà dal reparto](guide/architettura-permessi-e-autorizzazioni.md#24-ereditarieta-dal-reparto)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| Amm. Software — Permessi        | Operativo  | Matrice operatori × aree con Tag colorati, colonne dinamiche, filtri reparto/ruolo                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| Amm. Software — Audit Log       | Operativo  | Timeline globale 6 tabelle storico, paginazione lazy, sort server-side, filtro tipo                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| Amm. Software — Drawer Permessi | Operativo  | Drawer dedicato gestione permessi richiamabile dalla riga lista operatori; `OperatorePermessiTab` riusabile reattivo a `authUserId`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |

#### Catalogo, parametri e liste

| Area                            | Stato      | Note                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ------------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Catalogo — Articoli             | Operativo  | Lista con 7 filtri, drawer 3 tab (UoM, BoM, note), `ArticoloLookup` BB cross-dominio. **Completato e testato**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Catalogo — Unita' di Misura     | Operativo  | Lista, drawer CRUD, conversioni UoM, lookup generico whitelist                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Impostazioni Parametri          | Operativo  | Lista multi-scope (default/emittente/gruppo/utente), drawer override con selettore scope (Personale/Emittente) per admin, `PARAMETER_SCOPE` come unica fonte di verita' — guida: [override contestuali](guide/configurazione-e-gestione-parametri.md#2-gli-override-contestuali-configparameter_overrides) |
| UI — Liste (DB/BE)              | Operativo  | Schema ui (changeset atterrati): catalogo colonne, preset sistema/profilo/EF, preferenze utente. App Django `ui` con repository, servizi (incl. admin + export) ed endpoint REST. — guida: [liste](guide/configurazione-liste.md) |
| UI — Liste (Frontend)           | Operativo  | `ListaConfigurabile.vue`, `ListaColonneModal.vue`, `useListaConfig` + viste admin: **110 file usano il building block**. ⚠️ **Il contatore del presidio conta i file con `DataTable` grezza, non le liste**, e il registro `frontend/scripts/datatable.baseline.json` ne tiene **17**, nessuno senza motivazione: il motivo sta in un commento attaccato all'import, non nell'intestazione del file — un presidio che rosseggia **anche se il numero cala** senza riscrivere il registro, perché una baseline stantia riapre lo spazio appena chiuso. Le categorie del registro: **drawer/dialog**, pannelli o tab annidati, **i wrapper stessi**, `*SearchTable` di dominio e **view di lista** — le prime due categorie sono l'**eccezione ammessa** da `AGENTS.md`, non debito. La **regola zero della lista** sta in cima ad `AGENTS.md`, dove si legge a inizio sessione, e il frontend ha il presidio delle **classi morte** (`scripts/check_classi_morte.py`, pre-commit) più quello del **chrome del dialog** (`check-dialog-chrome.mjs`); i presidi FE sono **13** (confini fra domini, `api.*` fuori dai componenti, soglie dei `@media`…), i filtri compatti vanno in un drawer su 70 view su 70, e le **righe di un documento** diventano liste a catalogo (97-103) con la macchina del form inline in un BB (`useFormInline`) |
| UI — Dashboard home             | Operativo  | Card KPI configurabili: catalogo widget + composizione per profilo/emittente + preferenza utente (`ui.fn_resolve_dashboard_config`), filtro sui permessi dell'operatore, drawer di personalizzazione. Validata in-app.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |

### Cosa fornisce agli anelli esterni

- Entita' master referenziate via FK: soggetti, emittenti, risorse umane
- Tabelle config condivise: stati (doc fiscale, pratiche, flussi), priorita', canali
- Lookup e decodifiche centralizzate
- **Policy operative trasversali**: configurazioni che governano il comportamento del sistema su piu' domini e non appartengono a nessun dominio specifico (es. `user_emittenti_fiscali` — ambito operativo per emittente)
- **Gestione geografica completa**: indirizzi, toponomastica, comuni, province, regioni, stati — API + UI con autorizzazione per area `anagrafiche`
- **Building block frontend riutilizzabili**: composable centralizzati (useSearchTable, useDrawerState, useTabFreshness, useReadonlyMode, useActionPermission), componenti atomici (SoggettoForm, AuthUserForm, autocomplete, NewButton, DrawerFooter con prop `action`), CSS utility classes
- **Sistema permessi a 3 livelli**: Livello 1 area (TUTTO/LETTURA/BLOCCATO) + Livello 2 model/oggetto (override granulare per singola entita') + Livello 3 azioni processo (abilitata/negata), con enforcement backend (ZeroERPPermission) e auto-hide frontend (prop `action`, `useReadonlyMode`) — guida: [tre livelli per area](guide/architettura-permessi-e-autorizzazioni.md#22-tre-livelli-di-accesso-per-area)
- **Metadato di presentazione** (quando `ui` sara' operativo): configurazione colonne per ogni lista, cascata preset sistema/profilo/emittente, preferenze personali utente — leggibile da qualsiasi lista di qualsiasi anello esterno tramite `GET /api/v1/ui/liste/{codice}/config`

### Regola di posizionamento in `config`

`config` e' l'unico schema di Anello 1 con natura cross-schema. Ospita due categorie distinte:

1. **Cataloghi condivisi**: dati di riferimento statici usati come vocabolario comune (stati, priorita', canali, UO, termini pagamento)
2. **Policy operative trasversali**: configurazioni che descrivono regole di governo applicabili a piu' processi, quando non esiste uno schema di dominio piu' appropriato

Una tabella appartiene alla seconda categoria se: (a) non descrive un'entita' di business ma una regola di visibilita' o operativita', e (b) la regola vale trasversalmente su piu' schemi di Anello 3. In assenza di uno schema dedicato, `config` e' la collocazione meno artificiale — non `dbops` (infrastruttura tecnica) ne' `anagrafiche` (entita' anagrafiche).

### Posizionamento schema `ui`

`ui` e' il terzo schema di Anello 1 con natura cross-dominio, accanto a `config` e `amm-software`. Ospita esclusivamente **metadato di presentazione**: non contiene logica di business, non ha dipendenze da Anello 2 o 3, dipende solo da `config.profili_accesso` e `anagrafiche.emittenti_fiscali` (Anello 1) e `django.auth_user` (Anello 0).

E' classificato **di servizio** all'interno di Anello 1: il suo end-to-end richiedeva almeno un consumatore reale (prima lista migrata a `<ListaConfigurabile>`). Questo è avvenuto: le liste clienti e fornitori usano il componente configurabile, quindi il nucleo è stato **validato su casi reali** e si considera operativo. La lezione metodologica del caso pratiche (non completare prima della validazione su un caso reale) è stata rispettata.

Con la **dashboard home** `ui` acquisisce la **seconda famiglia di consumatori**: stesso impianto a cascata (sistema → profilo → emittente → utente), stessa forma di risoluzione lato DB (`fn_resolve_dashboard_config` accanto a quella delle liste), stesso filtro sui permessi dell'operatore. È la conferma richiesta dal principio 7 sull'asse "metadato di presentazione": il pattern non è stato inventato per la home, è stato **riusato** perché già decantato dalle liste.

Guida: [configurazione delle liste](guide/configurazione-liste.md); gli sviluppi differiti nella sua [§12](guide/configurazione-liste.md#12-roadmap-funzionalita-in-sviluppo).

> 🚨 **Il piano PrimeVue 5 non è più una questione tecnica.**
> `primevue`, `@primeuix/themes` e `primeicons` erano **MIT** e passano tutti e
> tre alla **licenza PrimeUI** (community/commerciale, con chiave) dalla nuova
> major. ZeroErp è **AGPL v3 pubblica con doppia licenza commerciale**: è una
> **decisione di licenza**, e non la prende un piano operativo. Il disaccoppiamento tecnico è chiuso e resta valido
> con qualunque esito — è il motivo per cui conviene averlo fatto prima.

### Stabilita'

Stabile. Cresce per aggiunta di nuove tabelle config (es. `config.canali_pratiche` aggiunta per pratiche) senza rompere quanto esistente.

---

## Anello 2 — Orchestrazione di Dominio

> **Natura: di servizio.** Motore trasversale che gli anelli esterni usano per tracciare, orchestrare e automatizzare.
>
> ✅ **`pratiche`: validata con il primo consumatore.** Il giro pratica PREVENTIVI (vendite) e' stato eseguito end-to-end runtime — handler `CONFERMA_VENDITA` con split per natura, giornale `DOMINIO_*`, gate EVASO, generazione cross-pratica, permessi da operatore reale; il workflow ha ripetibilita', bivi condizionali, lenti di contesto e guard di chiusura — guida: [gestione delle pratiche](guide/gestione-pratiche.md). Stato attuale: **validata con primo consumatore (vendite), pronta per il secondo** (Fase F: candidata assistenza/CRM). Resta vero il principio: solo dopo il **secondo** consumatore le astrazioni si promuovono a *contratti* (manifesto principio 1); fino ad allora restano *proposte* (principio 7).
>
> ✅ **`documenti`: validato su 6 consumatori reali.** Il motore documentale e' passato dal pilota (`vendite.preventivi`) a **6 domini** — preventivi, offerte, contratti, ordini, DDT e **fatture** — e con le fatture ha dovuto reggere anche la **stampa massiva** (render fuori dalla transazione che tiene il lock del registro fiscale). Le sue astrazioni sono quindi *contratti*, non piu' *proposte*: template versionato, asset per emittente e `pdf_mode` data-driven sono stati esercitati da domini con esigenze diverse.

| Componente  | Tipo       | DB        | Backend   | Frontend  | Descrizione                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ----------- | ---------- | --------- | --------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `pratiche`  | App Django | Operativo | Operativo | Operativo | Workflow engine, giornale, generazione cross-pratica, handler dispatch, sospensioni, calcoli tempo, macchina a stati, note, allegati; **assegnazione flusso operatore/reparto + coda lavoro** (pannello "Le mie attività"), **esito configurabile flussi**, **aggancio documento↔flusso**, **audit utente reale** — guida: [pratiche](guide/gestione-pratiche.md), [configurazione](guide/gestione-pratiche-configurazione.md) |
| `magazzino` — **registro** | Schema DB  | Operativo | Parziale  | Parziale  | Il registro della merce, letto come **servizio** e non come processo: magazzini, ubicazioni, lotti, seriali, causali, `movimenti`, valore e disponibilità, blocchi; la **primitiva** `fn_scrivi_movimento` (l'unica scrittura), la utility di storno, il catalogo delle **sorgenti** come punto di estensione (un movimento nomina la sua origine per tipo e chiave, senza FK verso i documenti). ⚠️ **Predisposto**: i consumatori esterni sono finora due documenti dello **stesso** dominio, bolla e reso di `vendite`; diventa contratto con il secondo dominio, `acquisti` (Lotto 4). I documenti di magazzino (inventari, rettifiche, trasferimenti) restano processi dell'anello 3 |
| `documenti` | App Django | Operativo | Operativo | Operativo | Motore documentale parametrico: template versionati, asset documentali, render PDF WeasyPrint, archivio documenti generati. **6 domini consumatori** (preventivi, offerte, contratti, ordini, DDT, **fatture**); con le fatture arriva anche la **stampa massiva via coda** (task che accoda → worker che drena, fuori dal lock del registro fiscale). ⭐ **Tre percorsi di stampa distinti**: *genera nuovo* (modello e dati di oggi), *scarica originale* (il file su storage), **ristampa fedele** (ri-renderizza com'era: versione di template pinnata anche OBSOLETA + contesto congelato, senza persistere nulla). ✅ **Il patto fra versione di template e forma dei dati**: ogni versione dichiara la forma che legge (`versione_contesto`, NOT NULL) e si stampa o si pubblica solo se coincide con quella del builder (`CONTEXT_VERSION`) — *Jinja non si lamenta*, e la fattura v3 usciva senza i componenti dei kit. La fattura è alla forma 2, con la v4 del template che scorre `riga.componenti` — guida: [documenti e stampe](guide/documenti-e-stampe.md) |

### Cosa fornisce agli anelli esterni

- **Pratiche**: contenitore tracciabile per qualsiasi processo (onboarding cliente, gestione ordine, assistenza tecnica)
- **Flussi**: step operativi con prerequisiti, esiti, scadenze, assegnazione risorse
- **Assegnazione e coda lavoro operatore**: flusso assegnabile a operatore/reparto (policy reparto-first), coda a 4 livelli (`fn_coda_lavoro_operatore`: ASSEGNATO/COMPETENZA/REPARTO/LIBERO), presa in carico (`fn_prendi_in_carico_flusso`); consumer FE pannello "Le mie attività"
- **Esito configurabile dei flussi**: MANUALE / AUTOMATICO / CONTESTUALE con `esito_default`
- **Giornale di bordo**: audit trail immutabile, append-only, con correlazione `tx_id` e **utente reale** (`user_update`/`data_update`) — guida: [giornale di bordo](guide/audit-e-tracciabilita.md#25-giornale-di-bordo-modulo-pratiche)
- **Generazione cross-pratica**: un flusso completato puo' generare automaticamente nuove pratiche
- **Handler dispatch**: mapping `handler_key` → classe Python per automazione step
- **Canali**: visibilita' dei flussi su sorgenti esterne (WEB_CLIENTI, APP_TECNICA, PORTALE_FORNITORI)
- **Sospensioni**: fermo temporaneo pratica/flusso con propagazione automatica e riattivazione (manuale o pgAgent)
- **Calcoli tempo**: tracking tempi netti tra coppie di flussi (formula da/a), con esclusione giorni sospensione
- **Macchina a stati rigida**: transizioni ammesse validate da trigger DB (config-driven)
- **API interna**: `pratiche_service` come facade per gli anelli esterni
- **Documenti parametrici**: template e versioni separati dai dati, asset per emittente fiscale, PDF finale archiviato con hash, utente e data generazione — guida: [documenti e stampe](guide/documenti-e-stampe.md)
- **Render PDF**: backend con Jinja2 + WeasyPrint, storage configurato via parametri, generazione/lista/download esercitati da 6 domini (preventivi, offerte, contratti, ordini, DDT, fatture)
- **Registro della merce** (`magazzino`): una scrittura sola (`fn_scrivi_movimento`), giacenza e disponibilità, blocchi, storno; chi muove merce compone il proprio posting e lo chiama dalla stessa transazione del suo cambio di stato
- **Stampa massiva disaccoppiata**: il documento di massa si **accoda** e un worker lo renderizza fuori dalla transazione che detiene il lock del registro fiscale — pattern nato sulle fatture, riusabile da ogni dominio che stampi in lotto — guida: [la coda di stampa](guide/documenti-e-stampe.md#7-la-coda-di-stampa-delle-fatture)

### Perche' e' un anello separato (non anello 1)

`pratiche` non e' un dato di riferimento statico — e' un **motore di orchestrazione con stato e ciclo di vita**. Dipende da anello 1 (config, anagrafiche) per le FK, ma fornisce capacita' operative che gli anelli esterni consumano. E' il cuore operativo del sistema: ogni evento significativo (nuovo cliente, nuovo ordine, nuova assistenza) genera una pratica con il suo giornale.

### Perche' non e' anello 3 (processi)

Non e' un processo di business specifico (come vendite o acquisti). E' l'**infrastruttura di processo** che tutti i domini usano. E' al servizio dei processi, non un processo in se'.

### Riferimenti

Guida: [gestione delle pratiche](guide/gestione-pratiche.md) e la sua [configurazione](guide/gestione-pratiche-configurazione.md) — API:
[api_pratiche_list](backend/pratiche/manual/api_pratiche_list.md) ·
[api_pratiche_note](backend/pratiche/manual/api_pratiche_note.md) ·
[api_pratiche_allegati](backend/pratiche/manual/api_pratiche_allegati.md).

ℹ️ Il dettaglio fase-per-fase di v1 e v2 — 115 test,
19 endpoint, le tabelle con le righe «FATTO» — è **storia** e vive nel
[changelog](dev/mappa-concentrica-changelog.md). Qui resta lo stato: operativo su
DB, backend e frontend, **validato dal primo consumatore**, in attesa del
secondo.

---

## Anello 3 — Processi Operativi

> **Natura: autocontenuti (ciascuno).** Cicli di business che usano anelli interni. Ogni processo e' autonomo ma condivide vocabolario e infrastruttura.

| Componente    | Tipo           | DB          | Backend   | Descrizione                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------------- | -------------- | ----------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `vendite`     | App Django     | Operativo   | Operativo | Ciclo attivo: preventivi rev2, offerte, contratti, **ordini operativi**, DDT, **resi**, fatture e **note di credito**, pipeline fatturazione (**batch automatico a corsie + cockpit di azione dalle tre lenti**), lotti, commesse multi-sorgente (quantità immutabili + **porta oneri**), **listini v3**, **pratica PREVENTIVI** (primo consumatore del motore `pratiche`), stampa PDF di 6 domini via `documenti` (fatture con **stampa massiva a coda**), **numerazione governata dal registro**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `acquisti`    | App Django     | Parziale    | Stub      | 🔵 **Prossimo cantiere** (decisione di Tid, con `magazzino`). ⚠️ **Modello disegnato, non in esercizio**: ordini, righe, DDT, indirizzi e ponte di fulfillment esistono con vincoli e trigger, ma **tutte le tabelle sono a 0 righe** — nessun documento di acquisto è mai stato creato. La struttura è lo **specchio** del ciclo vendite; ⚠️ la simmetria dei nomi non garantisce quella delle colonne (il progetto ha già pagato un `sorgente_uid` che significava due cose diverse). Le righe portano già le **date di consegna** con l'attore invertito (`data_consegna_richiesta` la chiediamo noi, `data_consegna_confermata_fornitore` la conferma lui), senza consumatore: le prende il cantiere. Doc concettuale completata                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `magazzino`   | App Django     | Parziale    | Parziale  | 🔵 **Cantiere aperto** (decisione di Tid, con `acquisti`). ✅ **Lotto 1** «il terreno vuoto» chiuso e ✅ **Lotto 2** «il motore» **consegnato intero** (CI da zero verde, prova del lock a due sessioni: *la disponibilità si legge dopo il lock*): la porta `fn_scrivi_movimento` è l'unica scrittura del registro, e **non la chiama l'applicazione** — inventario e rettifica sono **verbi** che chiedono `registra_magazzino` (primo caso del *permesso nel verbo*, Anello 0). ✅ **BE/FE del Lotto 2 chiuso**: documenti interni con capability, inventario e rettifica *una implementazione, due configurazioni*, disponibilità e registro movimenti a video (19 rotte). ✅ Le **anagrafiche** — magazzini, ubicazioni, lotti — **stanno fuori dal pannello config**: sono anagrafiche con FK, non vocabolari, con guard sul padre e anti-ciclo. 🟡 **Lotto 3** «scarico da DDT» **applicato a DB** (24 changeSet, D-L3-a…k): la merce esce con la **bolla**, la sorgente è il **prelievo**, il cambio di stato del DDT è un verbo (`vendite.fn_cambia_stato_ddt`). 🟡 **Lotto 3-bis** «carico da reso» **applicato** (19 changeSet): il reso confermato ricarica al costo dell'uscita d'origine, lotto e seriale *si ritrovano, non si scelgono*. ⚠️ **Aperto**: il **BE/FE dei Lotti 3 e 3-bis** (senza, la bolla che muove merce non si emette), CI da zero, il collaudo a video dell'inventario. |

### Pagamenti, contabilità e storico

| Componente    | Tipo           | DB          | Backend   | Descrizione                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------------- | -------------- | ----------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pagamenti`   | App Django     | Parziale    | Parziale  | ⭐ **Il posting esiste**: registrazione della contabile, saldo della rata, guard di transizione e di capienza, **sistemazione delle eccedenze**, distinta di correzione, RLS sui canali di incasso (`enti_incasso` non ne aveva: l'IBAN di ogni emittente era visibile a tutti). È il **collaudo in-app a governare il modello** — **D16-D20** (la riga nasce cercando la fattura ed è già abbinata; in bozza si elimina; le righe che restano indietro hanno un futuro con `fn_posta_riga_tardiva`), la **distinta prende il numero dal registro** (`DIS-<sigla>-<anno>-<cifre>`), la **ricerca delle rate** è il primo consumatore dello scadenzario — e i due piani, DB e BE/FE, sono **chiusi e archiviati**. ⛔ **Provato il percorso, mai l'esito**: la prova a video dell'ultimo giro è **aperta**. Le righe di una distinta `ANNULLATA` — *non è mai successa* — escono dalle code: una bandiera a catalogo (`righe_lavorabili`) al posto di tre sedi con tre risposte; ⚠️ il BE/FE è da fare — guida: [pagamenti](guide/gestione-dei-pagamenti.md), [termini di pagamento](guide/termini-di-pagamento.md) |
| `contabilita` | Nome di schema | ⛔ **Vuoto** | —         | ⛔ **Lo schema non contiene nulla**: zero tabelle, zero funzioni, zero viste (verificato sulla doc auto-gen e su `migrations_v2`, dove le cartelle `00_schema/contabilita/` e `20_code/contabilita/` sono vuote). ⚠️ Questa riga diceva «DB Operativo — piano conti, registrazioni, partite»: erano **intenzioni scritte come stato**, e quelle tabelle non sono mai esistite. Anche `backend/apps/contabilita/` è uno scheletro vuoto. ⭐ **Ed è la posizione giusta in cui stare**: se un giorno servirà, sarà un **aggancio a una contabilità esterna**, e la forma la detta il **sistema di destinazione** — profondità dei livelli, composizione dei codici, mastro/conto/sottoconto contro albero libero, contropartite sul conto o sulla causale. Non avendo deciso niente, non c'è niente da disfare                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `storico`     | App Django     | Operativo   | Stub      | Audit temporale, storicizzazione — 117 tabelle, di cui 115 shadow generate da `dbops.fn_ensure_storico_table` (le altre due, `comune_trasformazioni` e `stradario_trasformazioni`, sono registri e abitano nello schema che dice il contrario: debito di nome dichiarato). **Portano il proprio perimetro**: `origine_schema` (le shadow condivise fra `vendite` e `acquisti` — `ddt`, `ordini`, `ordini_righe`… — distinguono per origine, prima chiudevano lo snapshot dell'altro schema) e `scope_emittente_fiscale_id` catturato alla scrittura e mai ricalcolato; **37** shadow delle madri protette con policy generata, `REVOKE DELETE` all'app su tutto lo schema, mappa `dbops.storico_scope_policy` e presidio `vw_storico_scope_da_dichiarare`. ⚠️ Le versioni legacy senza padre né archivio restano a scope NULL: invisibili all'operatore, visibili all'amministrazione. Le shadow di tabelle dismesse sono state droppate — guida: [storicizzazione](guide/storicizzazione-tabelle.md) |

### Dipendenze verso anelli interni

```
vendite ──────► config (stati_doc_fiscale, termini_pagamento)
              ► anagrafiche (soggetti, emittenti_fiscali)
              ► catalogo (articoli, UoM, listini)
              ► core (error_manager, endpoint_helpers, coda lavori generica)
              ► documenti (generazione/lista/download PDF su 6 domini + stampa massiva fatture)
              ► pratiche (OPERATIVO — pratica PREVENTIVI: handler, giornale, azioni di processo)
              ► registro di magazzino (bolla e reso: scarico, carico, storno — Lotti 3 e 3-bis)

acquisti ─────► stesse dipendenze di vendite
              ► pratiche (FUTURO)
```

### Integrazione con pratiche

`pratiche` e' stata validata dal primo consumatore reale: la pratica PREVENTIVI di `vendite` esercita creazione pratica, flussi con handler (`CONFERMA_VENDITA`), giornale `DOMINIO_*`, azioni di processo e generazione cross-pratica. Gli altri processi di Anello 3 potranno:

1. **Creare pratiche** per i propri eventi (`pratiche_service.crea_pratica`)
2. **Alimentare il giornale** con eventi di dominio (nuovo cliente → PRATICA_CREATA)
3. **Usare flussi** per step operativi tracciati (approvazione ordine, sopralluogo, collaudo)
4. **Sfruttare generazione cross-pratica** (ordine completato → genera pratica assistenza)

I processi **massivi** (lotto fatturazione, import batch) mantengono la propria infrastruttura di tracking (pipeline, task runs, log fatture) perche' hanno requisiti diversi (parallelismo, resume per singola fattura, tracing per step). Il giornale di pratiche traccia eventi a livello di **processo singolo**, non di batch.

### Stato sviluppo vendite (app leader)

| Area                                       | Stato                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Pipeline fatturazione                      | Operativo — **batch automatico end-to-end** (driver CRON `run-until-done`, discovery a corsie `(emittente, tipo_doc, utility)`, **sync stato fattura per-step `1→2→8`**, run headless in `job_run_log`) — guida: [pipeline a lotti](guide/fatturazione.md#fase-4-pipeline-fatturazione-a-lotti) |
| Cockpit processi fatturazione              | Operativo — dalle tre lenti si **agisce**: «Fattura adesso» (giro on-demand su lotto o perimetro), «Riporta da emettere» (recupero dei residui), stampa/ristampa massiva; atterraggio contestuale dal pannello errori e dal breakdown FATTURATA (l'invio SDI non è esposto). ⚠️ **«Rendi definitive» NON è fra questi**: vive sulla **lista Lotti**, dove sta l'elenco del suo oggetto — dalla card `Fatturate` resta il rimando filtrato. Guida [cruscotti-fatturazione.md](guide/cruscotti-fatturazione.md) §7                                                                                                                                                                                                        |
| Stampa massiva fatture (outbox)            | Operativo — la stampa **accoda** (`vendite.fatture_stampa_coda` + `fn_accoda_stampe_lotto`), un **worker drena** e renderizza fuori dal lock del registro fiscale; numerazione garantita in stampa da backstop idempotente. La fattura è il **6° dominio del motore documentale** — guida: [la coda di stampa](guide/documenti-e-stampe.md#7-la-coda-di-stampa-delle-fatture) |
| Lotti massivi/giornalieri                  | Operativo — stato documentale fattura allineato per-step (giornaliero unificato a `1→2→8`)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Registry task DB multi-dominio             | Operativo — guida: [task registry](guide/analisi-tracciamento-processi-e-job.md#1-task-registry-multi-dominio) |
| Dispatch task con implementation_key       | Operativo                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| Runtime task tracing                       | Operativo — guida: [task runtime](guide/analisi-tracciamento-processi-e-job.md#2-task-runtime-esecuzione-e-policy) |
| Satelliti della fattura                    | Operativo — **cantiere chiuso su tutte le fasi**: **piano rate** (`fatture_scadenze`, generato nello step EMESSA dopo il ricalcolo IVA, idempotente, con snapshot del termine in testata), snapshot di **intestazione** e **indirizzi**, **drawer di consultazione** in un round-trip sugli stessi lettori del PDF, **note fattura** (6° dominio del BB note), ritiro del generatore di righe SQL                                                                                                                                                                                                                                                                                                                                                          |
| Emissione mirata + ritorno a DRAFT         | Operativo — il giro accetta un perimetro ristretto ai **gruppi fatturabili** (stesso verbo, assente = giro di massa invariato); il lotto può **tornare a DRAFT** per rifare un giro andato storto                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| Il lavoro che non torna indietro           | Operativo — le tre porte di reset (elimina fattura, riporta il lotto a DRAFT, annulla il lotto) non disfano più una riga già accreditata: era una violazione di chiave esterna **a metà lavoro**, ora è un rifiuto motivato. Il lavoro rimasto indietro ha un verbo, **«Riporta da emettere»**, con la card spezzata in due per non promettere una fattura che non c'è — guida: [le tre vie d'uscita](guide/cruscotti-fatturazione.md#76-tornare-indietro-le-tre-vie-duscita) |

#### Regole di emissione e correzioni

| Area                                       | Stato                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Nota di credito sui resi                   | Operativo — il **ramo economico** dei resi: il reso portava indietro merce e motivo e nessun valore. Righe di accredito (`resi_righe_accrediti`), nature del documento fiscale a catalogo, DB+BE+FE chiusi e **collaudo in-app superato** — guida: [la nota di credito](guide/fatturazione.md#il-documento-che-torna-indietro-la-nota-di-credito) |
| Numerazione: data documento e registro     | Operativo — la data e la sequenza di un documento fiscale sono una **decisione del registro**, non un effetto del giro: **limite di emissione** (il documento nasce già conforme invece di scoprirsi non più trasmissibile) e **registro + data prevista visibili in lista**, prima di generare. ✅ **Trasloco eseguito**: la commessa è passata sul **motore dei registri** — prefisso, allineamento dei contatori e chiave del contatore esplicita — e la periodicità dentro `config.sistema_codici` non si fa più. Il **CRUD dei registri** e quello delle **famiglie** hanno rotta e maschera; `famiglie_documento.colonna_billing_account` è facoltativa come `colonna_serie` — la porta per il primo documento senza cliente (l'ordine di acquisto) — guida: [numerazione](guide/numerazione-documenti-e-codici.md) |
| IVA di riga: risolutore a due stadi        | Operativo (DB) — l'IVA la decideva l'articolo e nessun altro, e il regime fiscale del cliente era scritto e **letto da nessuno**. Ora c'è un risolutore, e l'influenza del soggetto passa **sempre da un titolo registrato e documentato** (Anello 1, `anagrafiche`), mai da un default sul cliente. ✅ **Chiuso su tutte le fasi**: al lato DB si sono aggiunti i **consumatori applicativi** (fase 3), i movimenti di annullo sui titoli del soggetto, e il default IVA che smette di dipendere da un id di seed per passare a una **chiave naturale** — guida: [risolutore IVA](guide/iva-risolutore-di-riga.md) |
| Un documento rotto non blocca il giro      | Operativo — un lotto che incontrava un documento non emettibile si fermava, e con lui tutti gli altri: il difetto di uno era il blocco di tutti. Ora il documento **esce dal giro** e il lotto prosegue; la domanda «questa riga può entrare in un giro?» ha **una sede sola** invece della stessa condizione riscritta altrove, e il marcatore non scrive più su un documento già uscito                                                                                                                                                                                                                                                                                                                                                               |
| Il rilancio rivede le proprie commesse     | Operativo — al rilancio di un pull fallito la discovery scartava le commesse trattenute **dal lotto stesso che riprovava**, e il lotto usciva `COMPLETATO` senza documenti. Ora la discovery riceve l'identità del giro (`fn_classe_emittibilita_per_giro`: *una riga trattenuta soltanto dal mio giro, per il mio giro è pronta*, sede unica per discovery ed emit), **a valle di un task eseguito in questo giro nessun task si salta** (regola dell'orchestratore; `RESUME_STEP` ritirato), gli esiti `ERRORE` **contano nel verdetto** del lotto, e le porte di reset liberano anche le attività di un giro fermo prima della generazione. Collaudo in-app dell'esito parziale **chiuso**                                                               |
| Esito di un documento nel lotto            | Operativo — l'esito si deduceva dagli stati altrui e sui **giri di massa** la deduzione non reggeva. Ora è un dato con casa propria, e la **segnalazione di un lotto dichiara di quale documento parla** invece di lasciarlo capire                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| Partita di merce per documento             | Operativo — la capability di **un** DDT pagava le partite di **tutti**: ora la partita si legge per documento (`fn_partite_merce`, la vista ne è la proiezione), l'eleggibilità al push ha una sola implementazione, `vw_contatore_merce` è ritirata, e *le righe di un documento si toccano solo in bozza* è un BB montato su DDT, ordini, contratti e resi. D14 chiusa |
| Prezzi autorizzati                         | Operativo — *un prezzo non autorizzato non esce dalla bozza*: cinque sedi DB che dissentivano e una copia nel BE diventano un BB (`fn_check_prezzi_autorizzati`), il `REJECTED` conta, «Annulla» resta sempre acceso e i rientri automatici non si bloccano. Prova a video aperta — guida: [autorizzazioni override prezzo](guide/gestione-listini.md#6-autorizzazioni-override-prezzo-l1) |
| L'annullamento chiude la vita              | Operativo — un lotto si annulla solo se vuoto, quindi l'annullo **è** lo svuotamento (esiti `ESCLUSO` con motivo), e «COMPLETATO con documenti in ERRORE» è impossibile a DB |

#### Regole comuni dei documenti

| Area                                       | Stato                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Righe di documento come liste              | Operativo — le righe di preventivo, ordine, DDT, reso, fattura e contratto e la distinta base sono liste a catalogo (97-103): colonne dal catalogo, ritiro nella riga espandibile, personalizzazione, export. Una sorgente per documento (il contratto legge la sua funzione, coi verbi di riga dal DB), la lettura delle righe e «leggi prima la testata» in un BB solo, l'imponibile di riga in **una** funzione e la versione del listino in vigore in **una** sede |
| Il documento dopo l'emissione | Operativo — che cosa si cambia fuori bozza lo decide il DB, **per famiglie di colonne** (identità bloccata; ciò che arriva dopo e le note modificabili; stampato e condizioni per documento), con un BB per testate e righe; il BE non ripete più i suoi «solo in DRAFT». Le righe evase di una bolla sono ferme (`qta_evasa` append-only, la quantità si corregge col verbo, in bozza); la data confermata di una riga già spedita non si cambia; le date di consegna si scrivono in blocco sulle righe |
| Tornare indietro: annullo con legami | Operativo — annullare un documento che ha legami chiede **conferma** e riapre ciò che stava a monte (lettore unico dei legami, verbi `fn_annulla_<documento>`); annullare la **commessa** riapre il preventivo e l'ordine che l'hanno alimentata, e nei Passaggi il legame resta come storia, marcato «ritirato». ⚠️ Aperto: la commessa vuota lasciata dal push batch — guida: [l'annullo](guide/modello-documento-di-vendita.md#8-lannullo) |
| Il modello del documento | Operativo — le regole stanno in **una** [guida](guide/modello-documento-di-vendita.md) (approvata): ogni cambio di stato da un verbo DB, la porta è un guard sulla colonna di stato, si emette solo da `/emetti/` con numero e PDF nella stessa transazione, un documento **nasce nel suo stato iniziale**, e che cosa *significa* uno stato (emissione, accettazione, cessazione, aborto) lo dice il vocabolario, non un letterale nel codice. Lo seguono tutti, DB e BE: DDT (col DDT d'acquisto), preventivo, ordine, contratto, offerta, commessa, la fattura dal suo lotto (con la catena delle origini in stampa) e la versione di listino (attivazione, «Elimina», «Chiudi», «Clona» come verbi); le azioni per riga di lista vengono da un registro DB — guida: [a che punto è ogni documento](guide/modello-documento-di-vendita.md#10-a-che-punto-e-ogni-documento) |
| Un nome per ogni tipo di documento | Operativo — il nome del tipo è uno solo per DB e backend, il `codice_interno` di `config.sorgenti`; i nomi corti sono ritirati e `config.tipi_entita` è il catalogo dei bersagli, legato da un vincolo — guida: [sorgente polimorfa](guide/sorgente-polimorfa.md#4-la-convenzione-chiave-id-vs-uid-trappola-da-conoscere) |
| Modelli di stampa standard | Operativo — sei modelli standard nascono dal seed già pubblicati: un emittente nuovo emette dal primo giorno, la risoluzione va al modello dell'emittente e poi allo standard, «Personalizza» copia lo standard — guida: [il modello standard](guide/documenti-e-stampe.md#4-il-modello-standard-e-personalizza) |
| L'emittente è quello del cliente | Operativo — ordine, DDT e reso hanno il cliente e il billing account come preventivo, offerta e contratto (FK composte); un esecutivo derivato ha il BA della sua sorgente; la regola «l'azienda che emette è quella del cliente» è **un** BB per sette documenti, commessa compresa; l'istanza nasce col suo billing account; gli indirizzi del documento sono del suo cliente, e in bozza lo seguono quando cambia (D27) — guida: [l'emittente del cliente](guide/generazione-cliente.md#lemittente-del-cliente-si-sceglie-una-volta) |

#### Fatturazione elettronica SDI

| Area                                       | Stato                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Builder XML SDI                            | In corso (payload pronto, generazione XML da fare). ⚠️ Il blocco **`2.4 DatiPagamento`** non è generato: `fn_prepare_sdi_payload` non nomina né le scadenze né il blocco                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| Persistenza esito SDI                      | Da fare                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |

#### Commesse

| Area                                       | Stato                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Commesse (push, orchestrator, handlers)    | Operativo — multi-sorgente (1 ROOT + N COLLEGATO), push idempotente, snapshot pricing v5 nel push, capability azioni stato **con motivo**, pull→`attivita_fatturabili` agganciata agli step DRAFT, **guard di uscita** (niente chiusura/annullo con righe ancora fatturabili), RLS scope emittente anche in scrittura. **Testata leggibile**: `descrizione`, `data_apertura` (default nel fuso dell'azienda) e `responsabile_risorsa_umana_id` → `anagrafiche.risorse_umane` (la convenzione di `pratiche`; il block ATTIVO sul padre è il quarto della sua specie) — `PATCH /commesse/<id>/` e lookup dedicato `GET /anagrafiche/risorse-umane/lookup/`. ⚠️ Nessuna lista configurata `vendite.commesse`: la superficie è il drawer — guida: [commesse](guide/gestione-commesse.md) |
| Quantità immutabili + porta oneri          | Operativo — quantità già fatturate immutabili (guard `commesse_attivita`/`attivita_fatturabili`, cod. 550/551); oneri manuali via `config.causali_onere` + modello **articolo↔causale 1:1** (ogni onere porta la propria IVA), madre `fn_aggiungi_onere_commessa` con log (cod. 552-554, race `segment_key` chiusa a 557→409)                                                                                                                                                                                                                                                                                                                                                                                                                              |
| Guard `tipo_doc_fiscale` emittibile        | Operativo — normalize all'upsert (default da `config.sorgenti`) + guard di riga `APPROVATA+NON_EMESSA ⇒ tipo_doc NOT NULL` (cod. 497) + CHECK backstop: niente "fatturato perso in silenzio"                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |

#### Ordini, DDT, resi e tracciabilità

| Area                                       | Stato                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Ordini di vendita                          | Operativo — CRUD, lista DEF-8, conferma, EVASO automatico, stampa PDF, conversione preventivo/offerta→ordine, lock cliente. **Date di consegna per riga** — richiesta del cliente e promessa nostra (`data_consegna_confermata`), niente CHECK fra le due e niente colonna di testata (`min` dalla vista di lista); la richiesta viaggia dal preventivo con il push. Il **ritardo** (`giorni_ritardo`) sta nel pannello situazione merce accanto al residuo: `null` = non si applica, `0` = in tempo, `N` = giorni oltre la promessa. ⚠️ Aperto: le righe si scrivono solo in `DRAFT`, la promessa si decide alla conferma — serve un verbo suo — guida: [ordini](guide/gestione-ordini.md) |
| DDT di vendita                             | Operativo — documento di trasporto: evasione ordine→DDT (1:N, residuo per riga append-only) o standalone, stati data-driven `DRAFT→EMESSO→SPEDITO→CONSEGNATO` (+RESO/ANNULLATO), numero all'emissione, righe con prezzo opzionale (solo-trasporto), push a commessa (sorgente `DDT_VENDITA`), emittente memorizzato + RLS (§15), stampa PDF (5° dominio documenti), riepilogo IVA, export lista — guida: [DDT](guide/gestione-ddt.md) |
| Resi di vendita                            | Operativo — documento di rientro merce nato dal DDT, **senza valori economici** (ramo nota di credito rinviato): conferma (riapre il residuo ordine, flip DDT→RESO se totale), annullo come storno, **ri-consegna** (`fn_genera_ddt_riconsegna`, parziale e multipla), **rinuncia** con reso DEFINITIVO, due code di lavoro (da accreditare / da ri-consegnare), azioni data-driven — guida: [reso della merce](guide/gestione-ddt.md#11-bis-reso-della-merce) |
| Fatturazione DDT/resi a contatore          | Operativo — **contatore di merce** per riga d'ordine (spedito − reso) al posto del flag logistico `riapre_residuo`: chiusi due bug di doppia fatturazione, lenti Situazione aperta/Backlog estese a DDT e resi, coda accrediti con quantità (DL-19..28)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| Lineage documenti (genealogia)             | Operativo — `vw_documento_lineage_nodi`/`archi` + `fn_documento_lineage`; pannello «Passaggi» nei drawer documento e colonne pratica/fase/transito nelle liste. ⭐ **Il grafo non si ferma più sul reso**: l'arco reso→nota di credito chiude i due rami di ritorno — la merce che torna e il valore che torna — e con lui sono caduti i residui del `root` che dipendeva dagli id, della commessa senza origine e della nota di credito che in lista si chiamava «Fattura». ⭐ **Il grafo si semina per chiave**: il pannello e le sette liste non pagano più il grafo intero, la sintesi si calcola dopo la paginazione e `vw_documento_lineage` è ritirata — guida: [grafi tra documenti](guide/sorgente-polimorfa.md#6-per-chi-costruisce-grafi-tra-documenti-lineage-genealogia-proiezione) |
| Indirizzi documento (UX v2)                | Operativo — building block cross-dominio sui 5 domini vendite (preventivi/offerte/contratti/ordini/DDT): sezione inline + drawer gestione, snapshot indirizzo di consegna congelato all'emissione, auto-assegnazione default — guida: [indirizzi congelati sui documenti](guide/gestione-degli-indirizzi.md#gli-indirizzi-congelati-sui-documenti) |

#### Preventivi, offerte, contratti e listini

| Area                                       | Stato                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Pratica PREVENTIVI (integrazione pratiche) | Operativo — handler `CONFERMA_VENDITA`, split per natura merce→ordine / servizi→commessa, smistamento riga-per-riga, gate EVASO — guida: [preventivi](guide/gestione-preventivi.md) |
| Listini v3 (N2/N5/N6/N7/N8a)               | Operativo — Sprint B-v3 completato — guida: [listini](guide/gestione-listini.md) |
| Pricing commesse (N5/N7/N7-sblocco)        | Operativo — riallineamento, variazione, sblocco — guida: [il prezzo sulla riga commessa](guide/gestione-listini.md#7-ciclo-di-vita-del-prezzo-sulla-riga-commessa) |
| Contratti (modello unificato)              | Operativo — drop modalità A/B/C, eccezioni `tipo_eccezione`, snapshot versione listino, lock post-attivazione, stato ANNULLATO — guida: [contratti](guide/gestione-contratti.md) |
| Canone del contratto in commessa           | Operativo (DB, BE/FE) — una riga si addebita una tantum o **a canone**: periodicità sulla riga (la quota fissa dal listino, anche dentro un kit), mese di partenza e anticipato/normale sulla testata, tipo di riga ADESIONE; i periodi da una regola sola (`vendite.fn_canone_periodi`), gli arretrati si recuperano, la fine che si sposta produce lo **storno** come differenza, e la nota di credito prende la natura dal segno del documento; la dashboard giudica i contratti dalla stessa sede del push. ⚠️ L'obbligo della periodicità sulla riga a canone non è ancora un vincolo — guida: [il canone](guide/gestione-contratti.md#4-bis3-il-canone), [la cessazione e gli storni](guide/gestione-contratti.md#4-bis4-la-cessazione-e-gli-storni) |
| Offerte commerciali                        | Operativo (DB+BE+FE), in consolidamento — proposta condizioni quadro → push 1:1 a contratto; componenti BoM; generazione documento + allegati — guida: [offerte](guide/gestione-offerte-commerciali.md) |
| Componenti BoM compositi (vendite)         | Operativo — modello a 3 livelli condiviso da preventivi/contratti/offerte/ordini/ddt (i resi non hanno componenti) — guida: [distinta base](guide/gestione-listini.md#52-distinta-base-bom-componenti-di-un-kit) |
| Valuta su documenti                        | Operativo (DB) — `valuta_id` su offerte/contratti/preventivi, default da resolver gestore                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| Preventivi rev2                            | Operativo — emittente persistito, istanza obbligatoria, guard utility/istanza; EMESSO → SCADUTO dal job delle scadenze, l'accettazione oltre «Valido al» rifiutata anche per data, l'emissione con la validità già finita rifiutata, la revisione anche da SCADUTO. ⚠️ Il BE non ha ancora i due codici nuovi nelle error policy — guida: [stati e transizioni](guide/gestione-preventivi.md#31-stati-e-transizioni) |
| Revisioni preventivo + riepilogo IVA       | Operativo — scenario 2.1 chiuso end-to-end                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Generazione PDF documenti                  | Operativo — 6 domini serviti dal motore `documenti` (preventivi, offerte, contratti, ordini, DDT, fatture); i resi non generano PDF in questa slice — guida: [documenti e stampe](guide/documenti-e-stampe.md) |

---

## Matrice delle dipendenze

```
                 core   config   anagr.   catal.   pratiche   documenti   vendite
core              -       -        -        -        -          -           -
config           usa      -        -        -        -          -           -
anagrafiche      usa      -        -        -        -          -           -
catalogo         usa      -        -        -        -          -           -
pratiche         usa     usa      usa       -        -          -           -
documenti        usa     usa      usa       -        -          -           -
vendite          usa     usa      usa      usa      usa        usa          -     ► usa il registro di magazzino (anello 2)
acquisti         usa     usa      usa      usa    (futuro)   (futuro)      -
magazzino        usa     usa      usa       -     (futuro)      -           -
pagamenti        usa     usa       -        -     (futuro)      -           -
contabilita       -       -        -        -        -          -           -   ⛔ fuori perimetro
```

Nessuna dipendenza inversa. ⭐ **`vendite` usa il registro di `magazzino`** (Lotti 3 e
3-bis: la bolla scarica, il reso ricarica) — e non è una dipendenza **laterale**: il registro sta
nell'anello 2 (§1, decisione). ✅ **Il verso inverso è chiuso** (`20261001-18 → -26`, applicati): i due posting della bolla e del reso passano da `magazzino` a
`vendite` (`vendite.fn_posta_ddt`, `vendite.fn_posta_reso`), e il presidio scritto per
impedire che tornino ha trovato un **secondo** verso inverso che nessuno cercava — la FK
`magazzino.assets.contratto_id` → `vendite.contratti`, mai letta né scritta — tolta nello
stesso giro (D-3 di Tid: se servirà, il legame nasce nel contratto). Nella matrice qui
sopra la colonna `magazzino` vale per il **registro**.

⛔ **`contabilita` è a zero perché lo schema è vuoto**, non perché sia isolato: il `(futuro)`
che stava su questa riga prometteva un collegamento che **non è previsto**. Se un giorno
arriverà una contabilità, arriverà come **integrazione verso un sistema esterno**, e il lavoro
vero non sarà l'albero dei conti ma la **superficie di associazione** — articolo → conto di
ricavo, aliquota → conto IVA, causale → contropartita, cliente → sottoconto, più il formato con
cui esce la prima nota. ⭐ Quella superficie vive **in `vendite` e `catalogo`**, non qui: le
frecce da disegnare quel giorno partiranno da lì. E il primo passo non sarà scrivere codice,
sarà **farsi dare un tracciato** dal commercialista del primo cliente che lo chiede.

Gli anelli esterni possono dipendere direttamente da anelli non adiacenti — vendite usa `core` e `config` senza passare per `pratiche`. Questo non viola la direzione delle dipendenze, sempre dall'esterno verso l'interno: descrive semplicemente come certi tipi di informazione attraversano il tronco (la linfa, nella metafora del vocabolario).

---

## 3 · Roadmap

> **Regole di questa sezione**, per non farla tornare com'era:
>
> 1. solo lavori **in corso o previsti** — ciò che è finito esce e va nel
>    [changelog](dev/mappa-concentrica-changelog.md);
> 2. un'area **operativa con rifiniture aperte** non è un lavoro in corso: la
>    rifinitura si annota nella tabella del suo anello, non qui;
> 3. ogni voce di «In corso» ha un **documento vivo**. Senza documento non è in
>    corso: è un'intenzione, e va sotto «Previsti».

### 🔨 In corso — con cantiere aperto

| Cosa                                                                | Dove sta                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | Stato                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **La catena di verifica: presidi e copertura reale**                | [migliorie-generali…](dev/work-in-progress/migliorie-generali-da-test-valutazione.md)                                                                                                                                                                                                                                                                                                                                                                                           | Valutazione dello strato DB per difetti numerati: le voci chiuse stanno nel brief, la loro storia nel [changelog](dev/mappa-concentrica-changelog.md). ⛔ Aperti: D6-bis, D7 come **debito residuo** (il divario fra il registro della CI e quello di sviluppo, vedi «Debito dichiarato», e i 18 rossi del lotto 2 da guardare uno per uno), D9, D11, e di D14 due decisioni non prese e i residui dichiarati — guida: [come si scrive un pgTAP](guide/pgtap-come-si-scrive-un-test.md), [presidi](guide/presidi-e-registri-del-debito.md) |

#### Documenti di vendita

| Cosa                                                                | Dove sta                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | Stato                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |

#### Incassi, osservabilità e magazzino

| Cosa                                                                | Dove sta                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | Stato                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Incassi e contabili di pagamento**                                | [brief-incassi…](dev/work-in-progress/brief-incassi-riconciliazione-rate-promemoria.md)                                                                                                                                                                                                                                                                                                                                                   | Codice scritto, piani archiviati. Resta la **prova a video** dell'ultimo giro, nel [collaudo in-app](dev/work-in-progress/collaudo-in-app-incassi-distinte-e-sistemazioni.md); un rilievo apre un brief nuovo — guida: [il giro operativo](guide/gestione-dei-pagamenti.md#il-giro-operativo-dal-denaro-in-banca-alla-distinta-registrata) |
| **`magazzino` — Lotti 3 e 3-bis, la merce che esce e rientra**     | [piano BE/FE](dev/work-in-progress/piano-be-fe-magazzino-lotto-3.md) · [collaudo bolla e reso](dev/work-in-progress/collaudo-in-app-magazzino-bolla-e-reso.md) · [collaudo inventario](dev/work-in-progress/collaudo-in-app-magazzino-inventario-e-rettifica.md) · analisi del cantiere: [carico e scarico](dev/work-in-progress/analisi-db-magazzino-carico-e-scarico.md) §8 · [aggancio documento e produzione](dev/work-in-progress/analisi-db-magazzino-aggancio-documento-e-produzione.md) · [commessa e produzione](dev/work-in-progress/analisi-db-commessa-e-produzione-predisposizione.md) | Scarico dalla bolla (Lotto 3) e carico dal reso (Lotto 3-bis) a DB, BE/FE fatto. ⚠️ **Aperto**: il collaudo a video (bolla e reso, inventario), CI da zero, la vista della merce in viaggio, la merce presso terzi — residui nel piano BE/FE §5. Dopo: ricezione acquisti e reso a fornitore (Lotto 4) |

#### Permessi e accessi

| Cosa                                                                | Dove sta                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | Stato                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Il permesso nel verbo di scrittura — passo 3**                    | [guida dei permessi §7.4](guide/architettura-permessi-e-autorizzazioni.md#74-il-permesso-nel-verbo-di-scrittura) | Il modello vive nella guida. ⛔ **Passo 3** — i domini esistenti — aperto e **senza data**, nei brief dei cantieri. ⚠️ **Due domini a metà non dichiarati** nella loro guida: `magazzino` (`magazzini`, `ubicazioni` e i documenti interni ancora scrivibili dall'app → [brief delle scritture dal verbo](dev/work-in-progress/brief-db-magazzino-tutte-le-scritture-dal-verbo.md), dichiarato nella guida del dominio) e `vendite` (bolla e reso con la sola porta del registro) |
| **Accessi e sicurezza: credenziale, vesti, secondo fattore**        | [piano BE/FE accessi](dev/work-in-progress/piano-be-fe-accessi-credenziale-e-vesti.md) · [piano OAuth](dev/work-in-progress/piano-autenticazione-provider-esterni-oauth.md)                                                                                                                                                                                                                       | Credenziale, vesti e secondo fattore chiusi. ⚠️ **Aperti**: il resto di L-5 (R-4, la revoca della veste, aspetta un brief DB) e il collaudo a video di D-5 — guida: [secondo fattore](guide/risorse-umane-e-accessi.md#secondo-fattore-di-autenticazione), [la credenziale](guide/architettura-multi-face-auth.md#32-la-credenziale-tentativi-freno-blocco) |

#### Fatturazione elettronica, interfaccia e AI

| Cosa                                                                | Dove sta                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | Stato                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Liste configurabili / PrimeVue**                                  | [piano-migrazione-primevue-5.md](dev/work-in-progress/piano-migrazione-primevue-5.md)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | Disaccoppiamento **chiuso**; l'upgrade è fermo su una **decisione di licenza** (vedi Anello 1) — guida: [liste](guide/configurazione-liste.md) |
| **Integrazione AI v2**                                              | [integrazione-ai-sviluppo-v2.md](dev/work-in-progress/integrazione-ai-sviluppo-v2.md)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | Contesto dinamico e nuovi tool — guida: [integrazione AI](guide/integrazione-ai.md) |

### 🎯 Previsti — decisi ma non aperti

- **`acquisti`** (decisione di Tid): il modello è a DB e il
  comportamento è da scrivere; ogni decisione presa su `vendite` — envelope,
  capability, scope, liste, drawer — vale anche per lui, e **`magazzino` è
  «In corso»**: la simmetria fra i due si chiude **subito**, non in una
  «fase due», e le due date di consegna di `acquisti.ordini_righe` (a DB, senza
  consumatore) sono sue. Analisi: `work-in-progress/analisi-simmetria-ordini-acquisto`
  e le due `analisi-db-magazzino-*`
- **Secondo consumatore di `pratiche`** (Fase F, candidata assistenza/CRM): è ciò
  che promuove le sue astrazioni da *proposte* a *contratti* (manifesto §7)
- **ORARIO e CONSUMO del contratto in commessa** (G-4 del brief del canone, chiuso il 2026-11-01 in `work-done/brief-db-contratto-righe-periodiche-in-commessa`): le ore lavorate aspettano il timesheet, i consumi le letture. Il canone è fatto; la voce D31 del registro resta aperta per loro
- **Rettifiche prezzi (DB-L4)**: motore delta + canali manuale/automatico
- **Permessi v3** — sotto-oggetti padre/figlio (v2 a livello oggetto è operativa)
- **Provider di autenticazione esterni** (OAuth, il [piano](dev/work-in-progress/piano-autenticazione-provider-esterni-oauth.md)): il secondo fattore è fatto, i provider no
- **Upload file allegati pratiche** (storage filesystem/object storage)
- **Fatturazione elettronica SDI**: payload pronto; il builder XML e la persistenza dell'esito sono da scrivere, e il blocco `2.4 DatiPagamento` dipende dalle rate, che ora esistono. Nessun documento vivo, quindi non è «In corso»
- **Osservabilità, i residui dichiarati** del cantiere chiuso: il Giornale eventi **non è multi-emittente**, il **catalogo dei registri** (BE), il **pallino per l'operatore** (decisione sui permessi dei presidi, D-P3). Stanno in PROJECT_CONTEXT § «Aperto»

### 🧭 Decisioni aperte — non sono lavori

Stanno qui perché **bloccano** o **riorientano** dei lavori, e nessun piano
operativo può prenderle al posto di una persona.

| Decisione                                                                                                                                                                                                                                                                                                                                                                         | Cosa blocca                                                                                                                                                                                                                                                                                                                                                  |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 🚨 **Licenza PrimeVue** (MIT → PrimeUI su `primevue`, `@primeuix/themes`, `primeicons`) contro **AGPL v3 pubblica + licenza commerciale**                                                                                                                                                                                                                                          | l'upgrade a PrimeVue 5. Il lavoro tecnico è già fatto e vale con qualunque esito                                                                                                                                                                                                                                                                             |
| **API di dominio portale/shop** (fatture, ordini, catalogo B2C)                                                                                                                                                                                                                                                                                                                   | l'infrastruttura auth è pronta e le policy RLS sono in dry-run: si apre «quando il business lo richiederà»                                                                                                                                                                                                                                                   |
| **Riconciliazione pratiche ↔ pipeline vendite**                                                                                                                                                                                                                                                                                                                                   | i due motori di orchestrazione convivono per scope diversi; la decisione resta **rinviata**, non dimenticata                                                                                                                                                                                                                                                 |
| **Che cosa è un *host* per il modello** — forma A (nome dichiarato in `env.sh` + `host` obbligatorio nella richiesta + claim del drenatore filtrato) o B (registro `dbops.host` + `abilita` per host) (D1)                                                                                       | **«Riavvia»** un servizio dall'interfaccia (`systemctl restart`, oggi il solo listener): senza host un pulsante riavvia «un host a caso» alla seconda macchina. «Esegui ora» è in esercizio e non ne aveva bisogno; questo sì, e non si scrive prima. Raccomandazione dell'analisi: A subito, B quando `abilita` per host diventa una domanda vera |
| **Diagnostica di produzione senza accesso al DB** — le sei domande del §10.2 dell'analisi (provider AI in produzione, staging C/D, profilo supporto bypass-RLS o GUC, error tracker esterno, classi di dato, chi risponde dei pacchetti) — **archiviata senza costruire** | niente, oggi: non c'è una produzione da diagnosticare. La metà osservabilità è consegnata; classificazione, mascheratura e riproduzione si riprogettano **da una produzione reale**, non dall'analisi                                                                                                                                              |

### 🧹 Debito dichiarato — deve calare, e si misura

- **pgTAP**: **4 rossi** nel registro del database di sviluppo — guida: [baseline dei test rossi](guide/presidi-e-registri-del-debito.md#32-baseline-dei-test-rossi)
  (`baseline-rossi.tsv`, **935 file** nell'albero `db/pgtap`).
  ⚠️ Un file che fallisce nel *fixture* non esegue nessuna asserzione: la sua
  copertura vale **zero**, non «parziale», ed è un'area che *sembra* coperta.
  🔴 **E il numero che conta è l'altro**: sul database **ricostruito da zero** —
  cioè in CI, cioè il contratto — il registro dice **358**,
  e le corse vere dicono meno, ma non sono certificate. Lo scratch locale ha un
  registro suo: **23 righe** (`baseline-rossi-scratch.tsv`). ⛔ *Lo scratch non è la CI*. ⚠️ Finché il rientro non è certificato (`pgtap-baseline-ci-rientrati.sh`
  sulla corsa del giorno) il numero che vale è quello del registro. Il **divario fra i due registri è il debito vero**, reso
  misurabile facendo compilare la baseline **alla CI**; il triage è
  partito dal perimetro (21 file, fixture che **cercavano** soggetti in un DB
  vuoto → fixture che li **costruiscono**, in due giri chiusi), e la seconda causa
  trovata — `django.auth_user` senza privilegi per l'app su un DB da zero — era un
  GRANT dato a mano su dev che lo scratch **copiava**
- **`DataTable` grezze**: **17 file** nel registro del presidio
  (`frontend/scripts/datatable.baseline.json`), **nessuno senza
  motivazione**: ogni file rimasto porta il suo motivo in un commento attaccato all'import.
  Il secondo giro, che ha portato a catalogo le sei liste vere che restavano, è chiuso il 2026-11-03
  ([brief del secondo giro](dev/work-done/brief-db-liste-datatable-grezze-secondo-giro.md)).
  ⚠️ **Il contatore non misura le liste**: drawer, dialog e pannelli annidati sono
  l'eccezione che `AGENTS.md` ammette, e i wrapper stessi contano come file; il debito vero
  sta nelle **view di lista** e nelle `*SearchTable` di dominio che non passano dal
  building block. ⛔ Il presidio a
  un numero solo non sa distinguerli: finché resta così, misura la crescita del
  frontend più del debito
- **Collaudi in-app aperti**: **tre copioni** scritti e da eseguire — il giro
  incassi ([ultimo giro](dev/work-in-progress/collaudo-in-app-incassi-distinte-e-sistemazioni.md)),
  [inventario e rettifica](dev/work-in-progress/collaudo-in-app-magazzino-inventario-e-rettifica.md)
  (il FE del magazzino non è mai stato aperto in-app), [bolla e reso](dev/work-in-progress/collaudo-in-app-magazzino-bolla-e-reso.md)
  (i blocchi A/B/C dei Lotti 3 e 3-bis, §4 del [piano](dev/work-in-progress/piano-be-fe-magazzino-lotto-3.md)) —
  più le due voci residue dell'area RESI, e due prove a video senza un copione a
  sé: gli indirizzi che seguono il cliente (D27) e i form di DDT e ordine col destinatario. ⚠️ Di quei percorsi è provato il
  *cammino*, mai l'*esito*. Superati a video: la soglia della ricerca,
  le misure di pagina, i filtri compatti su dispositivi veri,
  i permessi ereditati e la UI dei permessi dell'operatore,
  la capability annidata e i prezzi autorizzati,
  l'osservabilità,
  la casella di ricerca delle liste,
  il consenso al riuso della credenziale e il secondo fattore, il soggetto con
  i dati fiscali per natura, la testata dopo l'emissione, l'annullo
  che riapre a monte, le date di consegna in blocco e il modello del documento di
  vendita (offerta, preventivo, cessazione del contratto, versione di listino,
  «Genera ordine» e l'annullo con legami)
- **Perimetro dei dati**: **6 righe** nel seed di `dbops.rls_perimetro_debito` — guida: [una tabella fuori dal perimetro](dev/trappole.md#non-far-nascere-una-tabella-fuori-dal-perimetro-dei-dati)
  — figlie di tabella protetta (chiavi nullable o legami che definiscono il
  perimetro stesso) e le due policy inerti di `acquisti`, che sono D8 e non D4;
  due registri che abitano nello `storico` senza essere shadow. (Il pezzo di D6
  per cui `zeroerp_app` poteva rendersi proprietaria delle `DEFINER` scrivendo
  `sec_functions_owner` è **chiuso**)
- **Debito documentale**: la **revisione delle guide** è **in corso**:
  header standard, il changelog in testa dissolto nel corpo,
  accenti, tabelle rialineate — le regole stanno in
  [standard-guide.md](dev/standard-guide.md), non in ogni guida. Il vecchio
  residuo «le 8 guide dei satelliti fattura» più `pagamenti.sepa_mandati` è in
  quello sweep: il [`manual` di `sepa_mandati`](dbzero/pagamenti/manual/sepa_mandati.md)
  **esiste** ed è citato dalla sua guida
- **Il planner**: due cose diverse, tutte e due fatte.
  ✅ **Le forme dei piani** (**D26-2**):
  `plan_cache_mode = force_generic_plan` **solo** dove la misura mostra la
  ripianificazione a ogni chiamata (capability e lister dei DDT, tetti di
  accredito dei resi — presidio `test-plan-cache-mode-piano-generico-v1`); la
  CTE `src` della diagnosi `MATERIALIZED` (righe² giri sotto RLS, presidiata
  per forma); il grafo del lineage seminato per chiave con le liste che pagano
  solo la pagina (`vw_documento_lineage`
  ritirata); le viste-presidio su `pg_proc` con la
  **cardinalità dichiarata** (`dbops.fn_regexp_occorrenze`)
  invece di una stima che reggeva sull'ultimo autoanalyze del catalogo.
  ✅ **D-3b chiusa** (il verbo dell'accredito): i filtri su
  `segment_key` che sotto RLS non arrivavano all'indice, ora da `segment_base`;
  il **perimetro dell'operatore calcolato una volta per istruzione** in tutte le
  policy ef_whitelist (`fn_scope_ef_perimetro`, linee-guida-sql §10.3), con
  l'emittente della riga dal risolutore DEFINER; il `tx_id` sulla connessione di
  log persistente invece di una connessione per transazione.
  ✅ **D36 chiuso**: anche le policy di cliente, shop, fornitore, email
  e note calcolano chi guarda una volta per istruzione.
  ✅ **Le statistiche delle tabelle** (**D15** in [migliorie-generali](dev/work-in-progress/migliorie-generali-da-test-valutazione.md)):
  **chiusa**: job notturno `analyze_statistiche` con autoverifica, applicato e provato su dbdev. Sede: `dbops`/`maintenance`.
  ⇒ Le cure sopra reggono perché sono **forme** (`loops=1`, una lettura invece
  di N), non millisecondi: un confronto di tempi misurati su tabelle mai
  analizzate, prima che D15 si chiudesse, resta rumore
- **Test UI reali** su Articoli, UoM, Pratiche, Soggetti, Clienti, Fornitori
- **Smoke UI end-to-end** del giro pratica PREVENTIVI (accettazione →
  smistamento → ordine/commessa)
- **Seed azioni di processo** per i domini ancora scoperti (vendite e pratiche
  sono seedate)

### 🌅 Lungo termine

- Tutti i processi di anello 3 usano `pratiche` per tracciabilita' e orchestrazione
- Il giornale di bordo diventa la vista unificata sulle attivita' dell'azienda
- Canali esterni (portale clienti, app tecnica) operano tramite flussi con visibilita' controllata

---
## 4 · Lezioni metodologiche

> Perché la mappa è fatta così. Non è stato: è l'**anticorpo** per chi
> costruirà il prossimo anello. Si legge una volta, non a ogni consultazione.

### 📏 La qualità si misura — indicatori e lezioni per strato

Le valutazioni di qualità hanno lasciato due cose che non devono
scadere: le **lezioni** e un insieme di **indicatori** da rileggere nel tempo.
Ogni strato ha la sua sede; questa tabella è il punto in cui si incontrano.

| Strato | Indicatori e lezioni (sede viva) | Come si rileggono |
| --- | --- | --- |
| Backend e frontend | [qualita-be-fe-indicatori.md](dev/qualita-be-fe-indicatori.md) | `scripts/indicatori-qualita-be-fe.sh` |
| Database | [qualita-db-indicatori.md](dev/qualita-db-indicatori.md) | `scripts/indicatori-qualita-db.sh` (con `--catalogo` su dbdev) |

⛔ Come ogni misura del progetto, questi numeri **trovano gli errori, non
disegnano il progetto** (regola zero).

## Caso di studio: pratiche prima di vendite

> Lezione retrospettiva sull'ordine di costruzione (aggiunta dopo riflessione metodologica).
>
> Questa sezione esiste per dare al lettore futuro l'anticorpo che e' mancato a chi ha costruito ZeroERP. Non e' un'autocritica: e' documentazione di un pattern ricorrente che il manifesto in versione iniziale non descriveva.

### Cosa e' successo

L'ordine effettivo dello sviluppo e' stato:

1. **`pratiche` (Anello 2)** dichiarata Operativo su DB+BE+FE: 19 endpoint, 115 test, sospensioni, calcoli tempo, macchina a stati, giornale di bordo.
2. **Nessun processo di Anello 3** consuma ancora pratiche. La matrice dipendenze segna `pratiche (FUTURO)` per vendite, acquisti, magazzino e pagamenti *(all'epoca anche per `contabilita`, oggi fuori perimetro)*.
3. **`vendite` ha sviluppato infrastruttura propria di orchestrazione** (pipeline fatturazione, lotti, registry task DB multi-dominio, dispatch task con `implementation_key`, runtime task tracing) **in parallelo a pratiche**, senza usarla. Risultato: due motori di orchestrazione paralleli, due vocabolari, un'integrazione futura ancora da disegnare.
4. **L'autore ha riconosciuto il problema** mentre lavorava su listini → contratti → preventivi: "sto facendo questi sviluppi per avere aree dove iniziare ad applicare le pratiche". Cioe': costruire i consumatori per validare l'astrazione, l'inverso del workflow ipotizzato dal manifesto v1.

### Perche' e' successo

Il manifesto v1 prescriveva "cresci un anello per volta" e "ogni incremento chiude un percorso end-to-end reale". Applicato letteralmente a un anello **di servizio** come pratiche, questa regola produce **invenzioni**: un motore di workflow completo, perfettamente formato, ma con astrazioni decise a priori e mai esercitate dal dominio reale.

Pratiche **non ha un end-to-end suo** — il suo end-to-end richiede un consumatore di Anello 3. Senza quel consumatore, le decisioni di design (cosa mette nel giornale, come modella un flusso, quali handler espone, cosa significa "sospensione") sono ipotesi del progettista, non risposte a esigenze osservate.

### Conseguenze concrete

- **Doppia infrastruttura di orchestrazione** in coesistenza: pratiche (giornale + flussi + macchina a stati) e vendite-pipeline (task runs + registry + dispatch). Nate per esigenze diverse, ma con sovrapposizione concettuale che andra' riconciliata. Costo nascosto del modello concentrico applicato troppo presto.
- **Vocabolario non condiviso**: pratiche parla di "flusso/step/handler_key/canali", vendite parla di "lotto/task/registry_impl/runtime tracing". Quando si dovra' integrare, si scoprira' che lo stesso concetto ha due nomi e due forme.
- **Test contro un'idea, non contro un caso d'uso**: i 115 test di pratiche verificano che il motore funzioni come progettato, non che risolva problemi reali della prima vendita o del primo onboarding.

### Cosa avremmo dovuto fare

Lo schema corretto per anelli di servizio e':

1. Aprire pratiche come **stub minimo** (modello dati base + servizio facade vuoto), Stato "Predisposto".
2. Aprire **vendite** o un altro processo di Anello 3 con un caso d'uso concreto end-to-end.
3. Quando vendite genera il primo evento da tracciare (es. "ordine creato"), **far emergere** il giornale di pratiche per servirlo. Il giornale nasce come risposta a una domanda concreta.
4. Quando un secondo processo (es. acquisti) chiede di tracciare i suoi eventi, **promuovere al nucleo di pratiche** le astrazioni che si ripetono, scartare quelle specifiche di vendite.
5. Solo dopo questo passaggio (manifesto principio 7) le astrazioni di pratiche diventano *contratti*; prima sono *proposte*.

### Come uscirne ora

Pratiche e' costruita. Disfarla sarebbe spreco. La via realistica:

- **Marcatura onesta**: ✅ percorso completato — pratiche e' passata da "predisposta" a **"validata con primo consumatore (vendite)"** (vedi Anello 2). La validazione ha confermato la lezione: l'uso reale ha scovato bug invisibili ai test (handler_params persi, fn di push con NOT NULL violabili, generazione non idempotente, azioni di processo mai seedate) che la "completezza tecnica" non aveva intercettato.
- **Prima integrazione concreta**: ✅ fatta — pratica PREVENTIVI end-to-end (accettazione M2, handler CONFERMA_VENDITA, giornale, sorgenti).
- **Riconciliazione con vendite-pipeline**: la decisione resta **rinviata** — i due motori convivono per scope diversi (pratica = processo singolo guidato dall'operatore; pipeline = batch fatturazione); il punto di contatto validato e' la commessa resa emittibile dal push.
- **Riserva di modifica**: con UN consumatore validato la riserva si restringe ma non decade: le astrazioni si promuovono a contratto solo col **secondo** consumatore (Fase F). Fino ad allora pratiche resta modificabile con prudenza (i test — 144 BE + 43 pgTAP workflow v2 — sono base di regressione solida, non ancora contratto).

### Lezione metodologica

**Per ogni anello classificato "di servizio" nella mappa, non costruirlo prima dei suoi consumatori.** Aprilo come stub se serve un punto di aggancio, ma non investire in completezza tecnica finche' non c'e' uso reale che lo eserciti. La completezza senza uso e' debito tecnico travestito da progresso.

### Esempio virtuoso opposto: framework `dbops.automazione_chiusura_scadenze`

Il caso pratiche e' istruttivo perche' mostra cosa succede applicando il manifesto v1 a un anello di servizio. Per contrasto, il framework `dbops.automazione_chiusura_scadenze` e' l'**applicazione corretta del principio 7** appena introdotto.

**Sequenza**:

1. **Primo caso reale**: implementato il pattern "ciclo stato + finestra di validita'" per `vendite.listini_versioni` come componente specifico del dominio (funzione `vendite.fn_listini_versioni_close_scadute()` + job pgAgent dedicato + guard transizione hardcoded). Nessuna astrazione prematura.
2. **Secondo consumatore**: emerge la stessa esigenza per `vendite.contratti` (cessazione data-driven). I requisiti sono **strutturalmente identici** al caso listini, salvo la differenza VARCHAR vs FK come tipo di colonna stato.
3. **Promozione al nucleo**: con due consumatori reali (non ipotetici), il pattern viene **estratto in `dbops`** come framework parametrico:
   - tabella di configurazione `dbops.automazione_chiusura_scadenze` con discriminator `tipo_stato` (VARCHAR/FK)
   - funzione motore `dbops.fn_apply_chiusura_scadenze()` con SQL dinamico + pre-check + audit
   - job pgAgent unico `chiusura_scadenze_daily` che sostituisce il job specifico precedente
   - vecchia funzione `fn_listini_versioni_close_scadute` droppata
4. **Aggiunte future**: una nuova tabella al pattern non richiede piu' nuovo codice DB — basta una INSERT seed nella tabella di configurazione.

**Differenza con il caso pratiche**:

| Aspetto                      | Pratiche (errore v1)                              | Framework chiusura (corretto v2)                                |
| ---------------------------- | ------------------------------------------------- | --------------------------------------------------------------- |
| Quando e' stato astratto     | Prima di qualunque consumatore reale              | Dopo due consumatori reali con requisiti identici               |
| Generalita' delle astrazioni | Decise dal progettista a priori                   | Decantate dal pattern emerso dai due casi                       |
| Validazione                  | Test contro un'idea progettuale                   | Test contro casi d'uso reali (listini + contratti)              |
| Costo se non si usa          | Spreco di lavoro, doppia infrastruttura parallela | Nullo (stub minimale solo se serve, oppure non si fa fino a 2°) |

**Cosa cambia nei tre piani della mappa**:

- Anello 0 cresce per *uso esterno*, non per *progetto interno*: la riga `dbops.automazione_chiusura_scadenze` aggiunta a "Cosa fornisce agli anelli esterni" deriva da bisogni concreti dei processi.
- Anello 3 (vendite) acquisisce un secondo punto di chiusura per scadenza (contratti) **senza dover scrivere infrastruttura propria**: usa il framework gia' validato.
- La promozione e' *non-breaking*: il job specifico precedente e' rimosso, ma il comportamento esterno (versioni listino chiuse a scadenza) e' identico — solo il motore sotto e' cambiato.

**Lezione metodologica generalizzata**:

> **La differenza non sta nel "se astrarre", ma nel "quando".** Astrarre prima di vedere e' progetto; astrarre dopo aver visto e' sintesi. Il manifesto §7 codifica questa distinzione perche' la prima e' debito travestito da architettura, la seconda e' architettura genuina.


## Caso di studio: il centro cresce, la coda resta fuori

> Lezione nata da una rilettura dello sviluppo contro la storia git. Vale per chi lavora da solo più che per chiunque altro.

**Il sospetto era sbagliato.** A leggere il changelog sembrava che il lavoro
sull'anello 0 fosse diventato *verifica della verifica*. Il codice dice altro:
dei 287 changeSet di un mese di lavoro su `dbops` e `script`, circa sette su dieci
aggiungono una **capacità** (identità dei processi, scope RLS, blocco login,
permessi ereditati, prezzi autorizzati, emittente di default…), uno su quattro
è un presidio o una fixture, e solo uno su venti corregge un presidio. E quasi
ogni ritorno al centro è **tirato da fuori**: una schermata, un documento, un
collaudo che scopre che al centro manca qualcosa. È il principio 7 applicato,
non un giro tondo. ⚠️ Il changelog racconta di più le lezioni sui presidi
perché sono le più belle da scrivere: *si pesa il codice, non il racconto*.

**Il difetto vero sta dall'altra parte.** Ogni capacità del centro si
ripercuote fuori (una decisione sulle icone delle azioni ha toccato le
`fn_available_actions_*` di nove documenti), e ogni ricaduta esterna chiede un
**collaudo in-app**. Il collaudo è il lavoro più noioso, quindi il primo a
restare indietro: i copioni aperti si accumulano, e la frase *«è provato il
cammino, mai l'esito»* torna più volte nel changelog. Il centro avanza; la sua coda esterna si accumula.

**Lezione metodologica.**

> **Una capacità del centro è finita quando la sua prima ricaduta esterna si è
> vista a video, non quando il pgTAP è verde.** Il collaudo che la chiude è
> quello della **prima** ricaduta, non di tutte: poche righe, un percorso, un
> esito. Il resto può aspettare il suo brief; quello no, perché è l'unica prova
> che il centro ha servito qualcuno.

Non è una regola in più da amministrare: è il criterio con cui si dichiara
chiuso un brief che tocca l'anello 0 o 1.

---


## 5 · Come aggiornare questo documento

1. **Nuovo componente**: aggiungere nella tabella dell'anello corretto (§2), con stato DB e Backend
2. **Cambio stato**: aggiornare la colonna Stato (Stub → Parziale → Operativo)
3. **Nuova dipendenza**: aggiungere nella matrice (§2) e verificare che rispetti la direzione degli anelli
4. **Nuovo anello**: se emerge un livello intermedio, inserirlo e ri-numerare
5. **Nuova milestone**: riscrivere «Ultimo aggiornamento» in testa — l'unica data del documento — e **spostare il precedente nel [changelog](dev/mappa-concentrica-changelog.md)**: la storia vive lì, non qui

⛔ **La mappa non porta date di esecuzione né serie storiche.** L'unica data è «Ultimo
aggiornamento» in testa, e **tutte le misure** del documento valgono a quella data. Il *quando* —
chi ha chiuso cosa e in che giorno, come un numero è cambiato nel tempo — sta nel
[changelog](dev/mappa-concentrica-changelog.md). Qui resta il fatto e il valore attuale.

⭐ **Un fatto rimanda alla sua guida, mai al brief.** Il brief racconta *come ci si è arrivati*;
la regola che vale oggi sta in una guida (`guide/`, `installazione.md`, `dev/…`) e la mappa ci
punta con «— guida: [sezione](…#anchor)». ⛔ Nessun link a `work-done/`; un brief di
`work-in-progress/` compare **solo** nella roadmap (§3), finché il cantiere è aperto e la sua
regola non ha ancora una guida. L'anchor si legge dall'HTML costruito
(`site-zensical/…/index.html`), non si deduce. Un fatto senza guida è un debito documentale:
si segnala, non si rimedia scrivendo la regola qui.

### ⚠️ Le quattro derive che hanno gonfiato questo documento

Sono già successe. Riconoscerle costa meno che disfarle.

| Deriva                                       | Come si riconosce                                | Dove va invece               |
| -------------------------------------------- | ------------------------------------------------ | ---------------------------- |
| **Cronologia nelle tabelle di stato**        | righe con una data e la parola «fatto»           | nel changelog                |
| **Rifiniture spacciate per lavori in corso** | «operativo — UI da migliorare» dentro la roadmap | nella tabella del suo anello |
| **Voci senza documento**                     | una riga di roadmap che nessun brief sostiene    | sotto «Previsti», o via      |
| **Date di esecuzione e serie storiche**      | «chiuso il …», «erano X il …»                    | nel changelog                |

> La mappa deve riflettere la **realtà**, non le intenzioni — e nemmeno il
> **ricordo**. Se una voce non si può verificare oggi contro il codice o un
> documento vivo, non è stato: è memoria.

---

*Mappa Concentrica — ZeroERP (31 ottobre 2026)*
