# Analisi — Osservabilità: consultare i log dall'applicazione

> **Destinatari:** Tid, backend, team DB
>
> **Tipo:** analisi di stato + piano. È il documento **principale** per il
> lavoro sull'osservabilità operativa.
>
> **Stato:** WIP — stato misurato il 2026-08-03, **piano rivisto il 2026-08-22**:
> i log servono prima a *trovare* un problema (§0-bis), lo scope emittente
> smette di essere una decisione rinviata e diventa il **Passo 0** (§4).
> ⭐ **Sempre il 2026-08-22, seconda passata:** lo stato è stato **riletto sul
> database e sul codice** prima di scrivere il brief — §0-ter. Tre premesse del
> piano non reggono più (il 67% di B1, il caveat sul `FORCE`, il rischio sul
> canale batch), ne emergono due buchi nuovi (**B10** `tx_id`, **B11** colonne
> morte di `request_log`) e un difetto di scrittura. **Leggere il §1 attraverso
> il §0-ter.**
>
> **Origine:** richiesta di Tid (2026-08-03): *«dobbiamo fornire uno strumento
> per accedere velocemente ai log, specialmente a quelli della fatturazione»*.
>
> ⭐ **Il brief del Passo 0 è scritto** (2026-08-22):
> [brief-db-event-log-scope-e-riga-parlante.md](../work-done/brief-db-event-log-scope-e-riga-parlante.md)
> — **18 decisioni chiuse, zero domande aperte**. ✅ **L1, L2 e L4 APPLICATI E
> VERDI il 2026-08-22**: 18 changeSet, 5 CSV, 33 asserzioni pgTAP con zero skip.
> ⭐ **La riga del giornale è parlante e i suoi vocabolari sono governati**:
> `entity_type` punta a `config.tipi_entita`, `domain` è stata **tolta** e i
> codici evento hanno il loro catalogo. Restano **L3** (la vista, che si accende
> col Passo A) e le **9 consegne BE** del suo §5 — senza le quali il registro
> resta a zero righe.
>
> ⭐ Il secondo giro di domande ha **rovesciato due decisioni**: un diario non
> si blocca mai per lo stato di un padre, quindi la colonna di perimetro è
> `emittente_soggetto_ruolo_id` (non la PK) ~~e il vocabolario è un `CHECK` (non
> una FK)~~ — così i lucchetti `require_attivo` non nascono proprio.
> ⚠️ **La seconda metà è stata superata** (D-17, applicata il 2026-08-22): il
> vocabolario **è** una FK, verso un catalogo che nasce **senza la colonna
> `attivo`** — che è ciò che impedisce al lucchetto di nascere. Il difetto stava
> in *quel* catalogo (`config.sorgenti`, che `attivo` ce l'ha), non nell'idea di
> catalogo.
>
> **Cosa NON è.** Non è la guida al modello di logging — quella è
> [Messaggi-di-Errore-e-Generazione-Log.md](../../guide/Messaggi-di-Errore-e-Generazione-Log.md),
> che descrive scrittura e consultazione **stabili**. Qui vive ciò che
> invecchia: lo stato misurato, i buchi, il piano.

---

## 0. Il confine con la diagnostica di produzione

Esiste un documento vicino che è **un'altra cosa**, e vale la pena dirlo subito
per non farne un contenitore unico:
[analisi-diagnostica-produzione-senza-accesso-db.md](analisi-diagnostica-produzione-senza-accesso-db.md).

| | Questo documento | Diagnostica di produzione |
| --- | --- | --- |
| Chi | operatore e amministratore | sviluppatore |
| Quando | ogni giorno | quando un caso è già rotto |
| Domanda | «cosa sta succedendo adesso» | «come rimetto in piedi questo caso altrove» |
| Rischio | basso | alto: dati personali fuori perimetro |
| Esito | schermate e notifiche | report diagnostico, pacchetto, staging mascherato |

Si toccano in due punti, e sono punti di **dipendenza**, non di sovrapposizione:
la **Fase 0** di quel documento (correlazione: `request_id` nei log Python) è
prerequisito anche di qui, e il suo **endpoint diagnostico** consumerà i
registri che qui si tratta di rendere leggibili.

⭐ **E c'è un terzo vicino, che è la leva opposta** (aperto il 2026-08-22):
[analisi-presidi-percorso-storto.md](analisi-presidi-percorso-storto.md).
Questo documento serve a **capire in fretta** un caso già rotto; quello a
**evitare che esca**. Un log si consulta quando già sai che qualcosa non va, un
cancello ti ferma quando non lo sai ancora: il primo riduce il tempo per
difetto, il secondo il numero dei difetti. Il «binario parallelo» del §4 — i
fallimenti visibili nelle liste — è il candidato **C3** di là.

---

## 0-bis. A cosa serve un log, e in che ordine (2026-08-22)

Il documento nasceva da una richiesta di **consultazione**. Rileggendolo con Tid
è emerso che l'ordine giusto è un altro, e cambia il piano:

> **Un log serve prima a *trovare* un problema, e solo dopo a *misurare* uno stato.**

Sono due mestieri con requisiti opposti:

| | Trovare (forense) | Misurare (aggregato) |
| --- | --- | --- |
| Domanda | «cos'è successo a **questo** lotto» | «quanti errori questa settimana» |
| Dati che servono | le sei righe di quel caso | volumi significativi |
| Qualità che serve | bassa: un evento anche innominabile, letto in sequenza, si capisce dal contesto | alta: un codice muto falsa il conto |
| Vale in ambiente di sviluppo | **sì, identico all'esercizio** | no |
| Superficie | timeline di un'entità | vista errori, notifiche, cruscotti |

**Conseguenza sul piano.** La metà forense dell'endpoint è piccola, non dipende
dalla qualità dei dati storici e **non ha come prerequisito il seed dei codici**;
la metà aggregata sì. Erano un passo solo (il vecchio Passo 3): da qui in avanti
sono **A** e **B** (§4).

### Cosa vale, dei numeri del §1

Osservazione di Tid (2026-08-22), e va scritta perché ha già prodotto una
conclusione sbagliata: **i numeri del §1 sono misurati su un database di
sviluppo.** Non tutti sopravvivono al trasloco.

> **Regola: qui reggono le prove di esistenza e le assenze di meccanismo.
> Non reggono le frequenze.**

Se una riga esiste, esiste davvero. Se un meccanismo non ha *mai* scritto nulla,
non è un campione scarso: è un filo staccato, e lo si conferma leggendo il
codice, non contando. Ma una percentuale descrive **come abbiamo usato
l'ambiente** — esperimenti, rotture volute, codice a metà — non come si
comporterà in esercizio.

| Misura del §1 | Regge? | Perché |
| --- | --- | --- |
| `event_log` scritto da due repository, **zero endpoint di lettura** | 🟢 | fatto di codice |
| `correlation_id` mai passato dal ramo push | 🟢 | le due `log_event` di `commesse_push_orchestrator` non lo passano: non è «0 su 196 righe», è la riga che non lo scrive |
| `actor` sempre `service:django` | 🟢 | è il default del repository e nessun chiamante lo sovrascrive |
| 207 codici assenti dal catalogo | 🟢 | è il catalogo, non il traffico |
| 309 / 62.418 / 136.462 righe nei registri | 🔴 | volume d'uso dell'ambiente |
| **67%** di `MESSAGGIO_NON_DEFINITO` | 🔴 *come percentuale* | la **lista** dei codici mancanti resta valida, la proporzione no |
| `fatture_log` = 0 righe | 🟡 | ambiguo: o non è successo niente di critico, o il canale non scrive. Lo dice il codice, non il conteggio |

⚠️ Per la stessa ragione **non si dimensiona la retention** (Passo D) su questi
volumi: la crescita reale non è nota.

---

## 0-ter. Verifiche sul DB e sul codice (2026-08-22, sessione DB)

Prima di scrivere il brief del Passo 0 lo stato è stato **riletto sul database e
sul codice**, non ripreso dal §1. Sette misure cambiano il piano; sono qui in
blocco perché il §1 resta com'era (è una fotografia del 3 agosto) e va letto
attraverso questa sezione.

| # | Verifica | Esito | Cosa cambia |
| --- | --- | --- | --- |
| V1 | Chi è l'owner delle tabelle `vendite` | **`titodb`**; l'applicazione è `zeroerp_app`, che **non** è owner, non è superuser e non ha `BYPASSRLS` | ⛔ **La RLS morde già il canale web.** Il caveat «l'owner applicativo la bypassa» del §4 nasce da un commento sbagliato in `20260720-05` (dice «l'owner (zeroerp_app)»); `20260730-05` dice la cosa giusta («l'owner della tabella (titodb)»). La decisione 5 non è un bivio: vedi sotto |
| V2 | Canale batch | `zeroerp_batch_fatturazione` ha `BYPASSRLS` **e** i GRANT su tutte e 84 le tabelle `vendite` (su `event_log`: `INSERT`+`SELECT`) | Il precedente `vendite.note` **non** si ripete: là mancava il GRANT, qui c'è. Resta da presidiare con un pgTAP, non da progettare |
| V3 | `E_MESSAGGIO_NON_DEFINITO` in `error_log` | **327 su 116.569 = 0,3%** (era il 67%) | Il seed dei codici legacy **è applicato** (`20260805-07`, eseguito il 2026-08-07) e la retention ha portato via le righe degradate. **B1 è chiuso di fatto**; del Passo 1 resta il solo rubinetto (check CI) |
| V4 | Cosa domina oggi `error_log` | `E_PARAMETRO_INVALIDO` 18.780 righe (16%), `E_GENERICO` 1.913 — ma su **70 `function_name` distinti**, e la colonna è `NOT NULL` | ⚠️ **Rettifica del 22/08 (seconda lettura):** *non* blocca il Passo B, come avevo scritto prima. L'aggregato si raggruppa per *(area, `function_name`, codice)* e `function_name` discrimina già. Lo split di `E_PARAMETRO_INVALIDO` è un problema di **qualità della frase che legge l'operatore**, e ha un brief suo (Aperte #14). **Il Passo B non è bloccato da niente** |
| V4-bis | Recinto fra test ed esercizio su `error_log` | assente (la suite Django ci scrive: punte settimanali da 54k e 40k righe) | ⚠️ Difetto vero e già a memoria, ma **fuori dal percorso critico**: `error_log` non è append-only e ha retention, quindi una colonna aggiunta domani inizia a popolarsi domani. **Non è un now-or-never** |
| V5 | `fatture_log` | **3 righe** (erano 0) | §1.4 sciolto: il canale scrive, non era rotto |
| V6 | `event_log` non ha `tx_id` | tutti gli altri registri ce l'hanno (`error_log`, `audit_log`, `request_log`, `fatture_log`, `fatturazione_lotti_log`, `fatturazione_lotti_task_runs`, `commesse_attivita_log`, `pratiche.giornale`) | 🔴 **Buco nuovo, B10.** La timeline di un caso è cross-registro: senza `tx_id` `event_log` non si aggancia a `error_log`. Ed è **non recuperabile**: vedi V7 |
| V7 | Il trigger append-only | `trgfn_event_log_append_only` vieta `UPDATE` **e `DELETE`** | Nessun backfill è possibile su questa tabella, **mai**. L'unica via è `TRUNCATE` (i trigger di riga non scattano; il privilegio `D` ce l'ha `titodb`, non `zeroerp_app`). Chiude la decisione 6 sul piano tecnico: o si azzera, o le righe restano mute per sempre |

### La regola d'ordine che ne discende

> **Su una tabella append-only la linea di taglio non è DB/BE, né forense/aggregato:
> è *lato scrittura* contro *lato lettura*.**

| | Contenuto | Recuperabile dopo? |
| --- | --- | --- |
| **Lato scrittura** | `emittente_fiscale_id`, `tx_id`, `correlation_id`, `actor`, `entity_id` | ❌ **mai** (V7). Ogni giorno di rinvio è un giorno di righe inutilizzabili |
| **Lato lettura** | policy, indici, `cleanup_at`, endpoint, viste, UI, notifiche | ✅ sempre, senza ricostruire nulla |

Conseguenza operativa: **tutto ciò che sta nella riga entra in una passata sola.**
Il rischio del Passo 0 non è che l'emittente costi troppo — costa poco (V1/V2 tolgono
due incognite, il cantiere gemello `brief-db-rls-commesse` è stato 3 changeSet più un
pgTAP) — è che si faccia l'emittente e si **dimentichi il `tx_id`**.

### Il difetto trovato strada facendo

`backend/apps/vendite/services/commesse_service.py:221` scrive
`severity="WARNING"`, ma `chk_event_log_severity` ammette solo
`INFO | WARN | ERROR`. Quindi **`EMITTIBILITA_FALLITA` non è mai scrivibile**:
solleva `23514` e — non essendo in `try` — fa saltare `pr_run_commesse_push`
**proprio nel ramo in cui qualcosa era già andato storto**. In tabella: zero
righe. Il test `test_pr_run_commesse_push_emittibilita_tipo_doc_mancante_osservabile`
asserisce `severity == "WARNING"` su un mock, quindi blinda il valore rotto.

È il §0-bis dimostrato: un registro che nessuno rilegge non si accorge di non
essere scritto. Correzione BE di una parola più il test (`WARN`), da fare nella
stessa passata del Passo 0.

---

## 1. Stato misurato (2026-08-03)

Tutti i numeri sono stati letti dal database di sviluppo, non stimati.

### 1.1 Cosa c'è dentro i registri

| Registro | Righe | Nota |
| --- | ---: | --- |
| `dbops.request_log` | 136.462 | |
| `dbops.error_log` | 62.418 | 🔴 vedi §1.2 |
| `maintenance.job_run_log` | 29.999 | drainer code + batch |
| `dbops.audit_log` | 1.087 | |
| `vendite.event_log` | 309 | 🔴 vedi §1.3 |
| `vendite.fatturazione_lotti_log` | 276 | |
| `vendite.fatturazione_lotti_task_runs` | 100 | |
| `vendite.commesse_push_log` | 101 | |
| `vendite.fatture_log` | **0** | ⚠️ vedi §1.4 |
| `vendite.attivita_fatturabili_log` | **0** | |
| log applicativi Python | 3,2 MB + 5 backup da 10 MB | solo su filesystem |

### 1.2 ~~🔴 Il registro errori non sa nominare due terzi degli errori~~ — SUPERATA

> ⛔ **Superata il 2026-08-22 (V3 del §0-ter): 327 righe su 116.569, cioè lo 0,3%.**
> Il seed dei codici legacy è applicato dal 2026-08-07 e la retention ha portato
> via le righe degradate. Il testo resta perché descrive il *meccanismo* — un
> codice fuori catalogo diventa un errore non più attribuibile — che è ancora
> vero e che il check CI deve chiudere. La misura sotto no.

**41.885 righe su 62.418 (67%)** hanno codice `MESSAGGIO_NON_DEFINITO`: il
codice usato dal chiamante non è in `config.messaggi_errore` e la funzione di
log ripiega sul segnaposto.

Il punto grave non è il messaggio generico: `error_log` conserva
`messaggio_errore_id` (una **FK**), non il codice in chiaro, e il `context`
jsonb non lo contiene. Verificato:

```
context delle righe degradate:
  {"field": "articolo_id", "value": "xxx"}
  {"uom_id": 0}
```

Quindi **quegli errori non sono più attribuibili**, e non lo saranno mai. Un
visualizzatore costruito oggi mostrerebbe in maggioranza righe che non sanno
dire cosa rappresentano.

➡️ Prerequisito, già scritto:
[brief-db-seed-messaggi-errore-mancanti.md](../work-done/brief-db-seed-messaggi-errore-mancanti.md)
(207 codici, proposta SQL validata e idempotente).

⚠️ **Due precisazioni del 2026-08-22.** La **percentuale** qui sopra non regge
fuori da questo ambiente (§0-bis); la **lista dei 207 codici** sì. E questo non è
più il prerequisito di *tutto*: lo è del solo Passo B — vedi §4, Passo 1.

### 1.3 🔴 `event_log` è write-only

`vendite.event_log` è scritto da due repository e **non è mai riletto**: zero
endpoint di lettura, zero consumatori nel frontend. È il registro pensato come
timeline unificata dei domini di vendita, e nessuno può vederlo.

Conseguenze misurate:

| | |
| --- | --- |
| `correlation_id` su `PIPELINE`/`LOTTO` | 112 su 113 🟢 |
| `correlation_id` su `COMMESSE`/`TASK_RUN` | **0 su 196** 🔴 |
| eventi con `entity_id = 0` **e** `correlation_id` NULL | **98 su 309** (32%) — non collegabili né a un'entità né a un run |
| colonna `correlation_id` su `fatturazione_lotti_task_runs` | **assente** |
| `actor` valorizzato | 309 su 309 — ⚠️ ma **sempre** `service:django` |

L'ultimo è un falso positivo istruttivo: la colonna è popolata al 100% con un
valore costante che non informa. `fn_log_event` accetta l'`actor`, il
repository ha il default `"service:django"`, **nessun chiamante lo
sovrascrive** — l'audit dice «è stato il servizio», mai chi.

### 1.4 ~~⚠️ `fatture_log` è vuota~~ — SCIOLTA

> ✅ **Sciolta il 2026-08-22 (V5 del §0-ter): 3 righe.** Il canale scrive; era
> l'ipotesi buona delle due. Nessun filo staccato.

La tabella dei log per fattura ha **0 righe**, e di conseguenza il pannello
errori della dashboard competenza trova 0 record. Da capire se è fisiologico
(nessun critico finora) o se il routing verso quella tabella non scrive più:
i trigger che ne derivano `fatture.critical` sono attivi, quindi il canale
esiste.

### 1.5 Retention

`cleanup_at` + `fn_apply_cleanup_at` + `fn_purge_cleanup_expired` sono lo
standard di progetto e **funzionano** (job `automations_cleanup`, ultimo giro
2026-08-02). Ma:

- sono applicati alle `dbops.*`, **non ai log di dominio**: `event_log`,
  `fatturazione_lotti_log`, `fatture_log` non hanno `cleanup_at` e crescono
  senza policy;
- su `error_log` restano **530 righe già scadute** e non ancora rimosse.

---

## 2. Cosa esiste già (e non va rifatto)

L'inventario stabile è nella guida
([§Consultare i log](../../guide/Messaggi-di-Errore-e-Generazione-Log.md)).
In sintesi: la diagnosi **di processo** è ben coperta — code di lavoro con
drawer di dettaglio, diagnostica del lotto con task-run e segnalazioni,
pannello errori della Lente 1, esiti dei giri, audit ed email log per gli
amministratori.

Esistono inoltre **endpoint già scritti e senza interfaccia**:
`tracciamento/job-runs`, `job-summary`, `audit-log`, `task-registry`,
`domini-task`, `task-implementations` e `core/email/log/`. La documentazione
API dichiara testualmente che servono «per la futura UI». Il backend, per
quella parte, è già pagato.

---

## 3. I buchi, in ordine di quanto pesano

| # | Buco | Effetto |
| --- | --- | --- |
| ~~B1~~ | ~~Il 67% di `error_log` non è attribuibile~~ ✅ **chiuso** (V3) | resta il **rubinetto**: 327 righe residue e il check CI ancora da fare |
| B2 | `event_log` non è leggibile da nessuna parte | manca la timeline per entità; l'alerting non ha sorgente; il `correlation_id` non ha consumatori che ne dimostrino il valore |
| B3 | Identità non tracciata sugli eventi | l'audit non dice **chi**: requisito di compliance non soddisfatto |
| B4 | `correlation_id` assente sul ramo push | «una query ricostruisce la timeline» vale solo per la pipeline |
| B5 | Log Python non correlabili | un traceback non si lega alla richiesta che l'ha generato (Fase 0 della diagnostica) |
| B6 | Endpoint senza UI | lavoro già fatto e inutilizzato |
| B7 | Nessuna notifica | un lotto fermo in errore resta invisibile finché qualcuno non guarda |
| B8 | Retention assente sui log di dominio | crescita non governata |
| **B9** | **`event_log` non ha scope emittente né RLS** *(aggiunto 22/08)* | qualunque endpoint di lettura mostrerebbe gli eventi di **tutti** gli emittenti: è il buco che manda il Passo 0 in testa al piano |
| **B10** | **`event_log` è l'unico registro senza `tx_id`** *(aggiunto 22/08, V6)* | la timeline di un caso è cross-registro e `event_log` non si aggancia a `error_log`. Costa una colonna (il trigger generico `dbops.trgfn_tx_id_managed` lo attacca l'automazione) e **non è recuperabile dopo**: append-only, nessun backfill (V7) |
| **B11** | **`request_log.emittente_attivo_id` e `tx_id` sono colonne morte** *(aggiunto 22/08)* | 0 valorizzate su 353.758: le colonne ci sono, l'`INSERT` del middleware non le elenca. Il «per chi» a livello di richiesta è già progettato e non collegato |

---

## 3-quater. 📍 Dove siamo — **stato dei passi al 2026-08-24 sera**

> Rilettura fatta contro il **codice e il database vivi**, non contro il piano.
> Serve perché tre passi su sette sono cambiati di stato in due giorni e il §4
> qui sotto li descrive ancora come da fare.
>
> ⏱️ **Rimisurato il 2026-09-05** (dodici giorni dopo). Tre voci del §5 «Aperte»
> erano **già chiuse nel codice** e non lo diceva nessuno — vedi le note ⏱️ lì.
> Qui cambia una riga sola, il Passo D. Il resto del quadro regge.
>
> ⚠️ **E si legge con il contesto operatore addosso**: `vendite.event_log` ha la
> RLS attiva, quindi un `count(*)` da una sessione senza GUC torna **0**. Non è
> «il registro è vuoto», è **fail-closed**. Con il contesto: **236 righe**
> (2026-09-05).

| Passo | Stato | Come si verifica |
| --- | --- | --- |
| **0** — la riga dice *chi*, *per chi*, *in che giro* | ✅ **FATTO** | `vendite.event_log` ha oggi `emittente_soggetto_ruolo_id` **NOT NULL** (+ RLS), `auth_user_id`, `tx_id`, `cleanup_at`. 12 consegne BE, verificate su **7 giri veri** |
| **1** — rendere nominabili gli errori | ✅ seed applicato (2026-08-07) | resta il **check CI**, come già scritto |
| **2** — `request_id` nei log Python | ✅ **FATTO** *(consegna BE-8)* | `settings.py`: filtro `request_id` + `req=%(request_id)s` nel formatter. ⭐ **B11 chiuso nello stesso giro, e in due direzioni opposte**: `emittente_attivo_id` ora si **scrive** (si collega in SQL, non passa dal Python), `tx_id` su `request_log` si è **tolto** — quella riga nasce quando l'unità di lavoro ha già chiuso, quindi il suo `tx_id` non esiste più. ⭐ *Una colonna che nessuno scrive si valorizza o si toglie: qui è successo l'uno e l'altro, sulla stessa tabella* |
| **A** — la timeline di un caso | ✅ **CHIUSO — fattura e lotto** *(2026-08-24 sera)* | `GET /vendite/fatture/<id>/giornale/` (validato in-app da Tid) e `GET /vendite/lotti/<id>/giornale/` + le due schede «Storia». ⭐ Sono i **due soli consumatori** di `script.vw_giornale_entita`. Sul lotto: il lotto **più le sue fatture**, righe non-INFO, con `entity_type` su ogni riga — e alla prima chiamata vera *il lotto dice che è andata male, la fattura dice perché* (R-3). 🔵 Resta la validazione in-app del pannello lotto |
| **B** — superfici aggregate | 🔵 aperto | invariato |
| **C** — notifiche | 🔵 aperto | invariato |
| **D** — retention sui log di dominio | 🟡 **parziale** — ma la parte difficile è fatta | ⏱️ *2026-09-05*: su `event_log` il `cleanup_at` è **valorizzato su tutte le 236 righe** (scadenza 2028-09-10) e `trgfn_event_log_append_only` distingue **alterare la storia** da **ritirare ciò che è scaduto** ⇒ la decisione #11 è chiusa e implementata. ⛔ Resta il pezzo meccanico: `fatturazione_lotti_log` e `fatture_log` non hanno `cleanup_at` |

### ✅ R-1 — l'orario ora è quello vero *(chiesto dal BE, scritto dal team DB il 2026-08-24)*

Era **la** cosa che teneva fermo il pannello del lotto: le colonne di orario dei
registri avevano default `now()`, cioè l'istante della **transazione** (misurato:
38 righe di un lotto su **3 istanti**). Sulla fattura non mordeva — un registro
solo; sul lotto i registri sono **tre** e i loro contatori di scrittura non sono
confrontabili, quindi la timeline sarebbe uscita **plausibile e falsa**.

➡️ **Risposta: `clock_timestamp()`**, changeSet `20260824-16` (i `DEFAULT`) e
`-17` (il comportamento), **nella stessa passata** + 7 asserzioni pgTAP.
⭐ L'argomento che ha deciso: l'orario di transazione è oggi coperto dal `tx_id`,
che quando quei default furono scelti non esisteva — sono colonne di
**osservabilità**, non di audit, e `data_insert` continua a portare l'orario di
transazione. *Non si erode una convenzione: si scioglie una sovrapposizione.*

⚠️ **Tre cose emerse misurando, che la richiesta non prevedeva** e che vale la
pena non riscoprire:

1. **i `DEFAULT` erano quasi tutti inerti** — tre registri su quattro passano la
   colonna a mano. Cambiare i soli default avrebbe mosso **un registro su
   quattro**, con un changeSet che dichiarava di aver risolto: *la forma
   peggiore, perché sembra fatta*;
2. **c'era un quinto punto** — `ended_at`, scritto con `now()`: spostando il solo
   `started_at`, un tentativo aperto e chiuso nella stessa transazione avrebbe
   violato il `CHECK (ended_at >= started_at)`. **165 corse su 319** sono
   esattamente quel caso;
3. **su `fatture_log` è un trigger, non cinque riscritture** — e il trigger
   copre anche il **sesto scrittore, che è il backend**: ⛔ **nessuna consegna
   BE su questo punto.**

⭐ **L'ancoraggio del «giro corrente» è deciso e pinnato** (Tid): una riga scritta
nella stessa transazione ma **prima** del `PIPELINE_STARTED` cade **fuori** dal
giro corrente. Con `now()` quel predicato non distingueva niente. Le funzioni
ancorate sono **due** (`fn_list_lotto_segnalazioni` **e** `fn_list_lotto_task_runs`).

⚠️ **Nessun backfill**, per scelta: le righe già scritte conservano l'orario di
transazione, quindi in tabella convivono **due generazioni** (R-5) — e a reggerle
è il pannello.

### ✅ Il perimetro del pannello lotto è deciso *(Tid, 2026-08-24)*

Il lotto **più le sue fatture**, righe **non-INFO**. La misura che l'ha decisa:
filtrando il solo lotto tornano 213 righe che dicono otto volte «Esito fatture
lotto · WARN» e **non contengono il motivo**, che sta sulla fattura.
⚠️ «Non-INFO» include il **NULL**, che è la riga che dichiara un difetto.

➡️ **Con R-1 applicato e il perimetro deciso, il pannello del lotto è stato
scritto** la sera stessa — ✅ e con lui il Passo A si chiude. Il racconto sta nel
§12 di
[brief-db-event-log-scope-e-riga-parlante.md](../work-done/brief-db-event-log-scope-e-riga-parlante.md);
il manuale dell'endpoint è `api_lotto_giornale.md`.

### ⚠️ I rilievi della ricognizione ancora vivi

Misurati il 2026-08-24 sui lotti **6260** (sporco) e **7133** (pulito), col
contesto operatore dichiarato. R-1 è risolto qui sopra, R-3 ha deciso dove
approdava il Passo A; questi restano, e chi scrive il pannello del lotto li
incontra tutti:

| # | Rilievo | Perché conta |
| --- | --- | --- |
| **R-2** | `LOTTO_LOG` e `FATTURA_LOG` hanno `correlation_id` **NULL per costruzione della vista** | Filtrare per «filo» tiene `event_log` + `task_run` e butta via le righe scritte **per una persona**. ⛔ Un filtro per giro nasconderebbe metà del contenuto |
| **R-4** | Il **perimetro non è mai stato esercitato** su nessuno dei quattro rami | Un solo emittente ha righe. Il fail-closed funziona (senza GUC la vista torna 0), la **discriminazione** no: va collaudata **apposta**, i dati non lo faranno |
| **R-5** | Due **generazioni di righe** convivono | Le vecchie hanno `tx_id` NULL e per «filo» il lotto; le nuove il giro. A video sono **indistinguibili** — e da R-1 in poi si aggiunge l'orario |
| **R-6** ⏱️ | La riga `TASK_RUN` è **incoerente con sé stessa** — ⛔ *ancora vero il 2026-09-05*: `script.vw_giornale_entita` usa tuttora `COALESCE(ended_at, started_at)` | `quando` è `COALESCE(ended_at, started_at)`, e `ended_at` lo scrive la corsa **successiva**: un task partito il 21 compare col timestamp del 22 |
| **R-7** | **Rumore**: sul 6260, 213 righe, 82 non-INFO — e **81 sono la stessa storia ripetuta otto volte**. L'errore vero è **una riga** | Il filtro non-INFO da solo non basta: nascondere le ritirate ne toglie una parte, il resto è **de-duplicazione**, da guardare col pannello davanti |

---

## 4. Piano proposto *(rivisto il 2026-08-22)*

L'ordine non è per dimensione ma per **dipendenza**: ogni passo rende utile il
successivo. Rispetto alla prima stesura cambiano due cose, entrambe dal §0-bis:
lo scope emittente non è più una decisione rinviata ma il **Passo 0**, e il
vecchio Passo 3 si divide in **A** (forense) e **B** (aggregato).

| Passo | Chi | Blocca |
| --- | --- | --- |
| **0** — la riga dice chi, per chi, in che giro *(+ `tx_id`, 22/08)* | 🔴 team DB **+ BE** | A e B |
| ~~**1**~~ — rendere nominabili gli errori | ✅ **seed applicato** il 2026-08-07 (V3); resta il **check CI** | niente: non blocca più B |
| **2** — `request_id` nei log Python | backend | niente (indipendente) |
| **A** — la timeline di un caso | backend + frontend | C |
| **B** — le superfici aggregate | backend + frontend | — |
| **C** — notifiche | backend | — |
| **D** — retention sui log di dominio | team DB | — |

---

### Passo 0 — La riga di `event_log` dice *chi*, *per chi*, *in che giro* 🔴 DB

> **Decisione di Tid (2026-08-22):** si parte da qui, pur essendo la strada più
> lunga. La ragione è che tutto il resto ci si appoggia — un endpoint scritto
> prima nascerebbe con lo scope applicato in Python, e andrebbe disfatto
> all'arrivo della RLS.
>
> ⭐ **E c'è una ragione più forte di quella**, emersa parlandone: il Passo 0
> **paga prima che esista qualunque schermata**. Oggi il diario è illeggibile
> anche per chi ha accesso diretto al database — `entity_id` a zero su un terzo
> delle righe, `actor` costante, `correlation_id` assente sul ramo push: una
> `SELECT` a mano non ricostruisce niente. La query esiste già ed è indicizzata
> (`ix_event_log_entity_time`); quello che manca è che le righe **dicano
> qualcosa**. Il Passo 0 non è quindi un investimento sull'endpoint futuro: è la
> cosa che rende utile il registro **subito**, a chi sta sviluppando.

Oggi la riga di `event_log` non sa dire nessuna delle tre cose:

| Cosa | Stato | Nota |
| --- | --- | --- |
| **per chi** — `emittente_fiscale_id` | ❌ **la colonna non esiste** | verificato sulla doc auto-gen della tabella: nessuna colonna emittente, nessuna policy |
| **chi** — `actor` | ⚠️ esiste, vale sempre `service:django` | l'audit dice «è stato il servizio», mai chi |
| **in che giro** — `correlation_id` | 🟡 metà: pipeline sì, push no | fatto di codice, non di dati (§0-bis) |
| *(e un quarto)* `entity_id` | ⚠️ `0` segnaposto sul ramo push | non è un segnaposto: è un id **che non esiste ancora**, perché `commesse_push_log` nasce a fine giro (verificato 22/08 su `commesse_push_orchestrator._run_locked`) |
| *(e un quinto, 22/08)* **`tx_id`** | ❌ **la colonna non esiste** | è l'unico registro del progetto senza. Vedi **B10** e V6 del §0-ter |

Sono **cinque difetti dello stesso lato** — il lato **scrittura** — e toccano
gli stessi due punti: `vendite.fn_log_event` e i suoi due chiamanti
(`pipeline_repository.log_event`, `commesse_repository.log_event`). Vanno in un
**cantiere solo**: farli in due passaggi vuol dire riaprire due volte gli stessi
file e rimettere due volte le mani su una funzione che tutti chiamano.

⛔ **E c'è una ragione più stringente della comodità (22/08).** La tabella è
append-only *per trigger*, e quel trigger vieta `UPDATE` **e `DELETE`** (V7): su
questi cinque campi **non esiste nessun rimedio a posteriori**, né oggi né fra un
anno. Il lato lettura — policy, indici, `cleanup_at`, endpoint, viste, UI — si
aggiunge invece in qualsiasi momento senza ricostruire niente. **È questa, e non
la ripartizione DB/BE, la linea che decide cosa va per primo.**

⚠️ **I due `log_event` sono copia carbone.** `pipeline_repository.log_event` e
`commesse_repository.log_event` sono identici carattere per carattere: la regola
del 2 dice che è un BB da estrarre, e comunque **qualunque cosa si aggiunga qui
va scritta due volte** finché resta così.

**Cosa chiedere al team DB** — brief dedicato, questo documento non è il brief:

1. `emittente_fiscale_id` su `vendite.event_log` + RLS con il pattern **già in
   casa**: policy `rls_*_ef_whitelist` (`FOR ALL`, `script.fn_scope_ef_whitelist`,
   gate `OPERATORE`) e guard di scrittura `script.trgfn_guard_emittente_scope`,
   come su DDT, ordini, preventivi, fatture e resi. Niente di inventato: è
   l'ondata a cui la tabella non ha partecipato;
2. ~~`fn_log_event` con il parametro nuovo~~, più la decisione su **come si
   valorizza** (sotto). ⭐ *22/08: se a derivare è il trigger (decisione 3), la
   firma non cambia — e si evita la trappola dell'overload;*
3. **`tx_id`** nello stesso `ALTER TABLE` (B10): il trigger generico
   `dbops.trgfn_tx_id_managed` lo attacca l'automazione, quindi costa la sola
   colonna — ⚠️ ma sul migrate manuale l'automazione gira col pgagent, non subito;
4. **`cleanup_at`** nello stesso `ALTER TABLE` (Passo D): stesso lucchetto, costo
   zero, e i termini si decidono dopo;
5. nella stessa passata: `correlation_id` sul ramo push, `actor` reale al posto
   della costante, `entity_id` reale al posto dello `0`.

⚠️ **Due cose che il brief NON deve dare per scontate, perché sono già risolte**
(V1/V2 del §0-ter): il canale batch **non** è a rischio — `zeroerp_batch_fatturazione`
ha `BYPASSRLS` e i GRANT su `event_log` (`INSERT`+`SELECT`) — e la RLS **non** è
decorativa, perché l'applicazione non è owner. Restano da presidiare con pgTAP,
non da progettare.

**Le domande che il brief deve porre**, perché nessuna ha risposta ovvia:

* **Chi calcola l'emittente?** `event_log` è polimorfa (`LOTTO`, `FATTURA`,
  `COMMESSA`, `TASK_RUN`): un trigger che lo derivi dall'entità dovrebbe
  dispacciare per `entity_type`, e diventerebbe l'unico punto del DB che conosce
  tutte e quattro le sorgenti. L'alternativa è che lo passi il chiamante — meno
  elegante, ma senza dispatch. Il precedente `trgfn_ddt_normalize` non si applica
  tale e quale: lì la sorgente da cui ereditare è **una**;
* **E gli eventi che un emittente non ce l'hanno?** Avvio di un giro, drainer
  della coda, eventi di sistema. `NOT NULL` li rende non scrivibili; nullable
  obbliga la policy a dire **chi vede i NULL** — e fail-closed significa
  «nessuno», cioè eventi di sistema invisibili a tutti;
* ~~**Il canale batch.**~~ ✅ **verificato il 22/08 (V2): non è un rischio.** Il
  ruolo `zeroerp_batch_fatturazione` ha `BYPASSRLS` **e** i GRANT
  (`INSERT`+`SELECT`) su `event_log` — sul canale batch la policy non si applica
  proprio. Resta un **pgTAP che lo dimostri**, non una decisione da prendere. Il
  testo sotto resta perché il ramo «`app.current_user_id` non settato» del guard
  va comunque deciso, ed è un'altra cosa dal ruolo. *(originale: I worker scrivono
  con un ruolo proprio. Una RLS che non
  contempla quel canale rompe la scrittura **solo da lì**: è esattamente il
  difetto già capitato con `vendite.note`
  ([brief-db-grant-batch-cleanup-note.md](../work-done/brief-db-grant-batch-cleanup-note.md)),
  e fu trovato per caso da una prova reale, non da un test.)* Il guard DDT skippa
  quando `app.current_user_id` non è settato: **quel ramo va deciso**, non
  ereditato per copia — ed è la parte di questo punto che resta viva;
* **Le 309 righe esistenti.** La tabella è append-only per trigger — `UPDATE`
  vietato — quindi un backfill ordinario non esiste. E per il §0-bis quelle
  righe non hanno valore probatorio. Proposta: non convertirle, **azzerare la
  tabella**. ⚠️ È una cancellazione: serve l'ok esplicito di Tid, e va nel brief
  come richiesta, non come fatto compiuto.

⚠️ ~~**Attenzione al «attivo senza FORCE».** Sulle tabelle gemelle la policy è
`ENABLE` **senza** `FORCE`, e l'owner applicativo la bypassa: la protezione che
agisce oggi è il filtro applicativo del BE. Se `event_log` nasce con la stessa
configurazione, l'endpoint del Passo A **non può** considerare la RLS come sua
unica difesa. O il brief chiede il `FORCE` per questa tabella, o l'endpoint
filtra anche lui — e va scritto quale delle due, perché è la differenza fra uno
strumento di diagnosi e una fuga di dati fra emittenti.~~

⛔ **Rettificato il 2026-08-22 (V1 del §0-ter): la premessa era falsa.** L'owner
delle tabelle `vendite` è **`titodb`**; l'applicazione gira come `zeroerp_app`,
che non è owner, non è superuser e non ha `BYPASSRLS` — quindi **la RLS morde
già** il canale web, `FORCE` o no. Il `FORCE` cambierebbe qualcosa solo per
`titodb` (il ruolo di migrazione), e romperebbe le `SECURITY DEFINER` di
proprietà di `titodb` che leggono fuori dalla row security — in testa
`script.fn_resolve_emittente_fiscale_id`, che lo dichiara nel proprio commento.
Il paragrafo nasce da un commento sbagliato in
`20260720-05-enable-rls-commesse-ef-whitelist` («l'owner (zeroerp_app)»);
`20260730-05-enable-rls-fatture-indirizzi` dice la cosa giusta. **Va corretto
anche il commento**, o rifarà lo stesso danno al prossimo che lo legge.

➡️ Quindi la decisione 5 non è un bivio: **parità con la famiglia (`ENABLE`, no
`FORCE`) e filtro applicativo lo stesso**, che è già la regola scritta in
[api.md §Scope emittente](../api.md) — *«i filtri applicativi restano come
defense-in-depth e si sommano»*.

### Passo 1 — Rendere nominabili gli errori *(prerequisito del solo Passo B)*

Applicare il seed dei 207 codici
([brief](../work-done/brief-db-seed-messaggi-errore-mancanti.md), già pronto e validato) e
decidere il check CI che impedisca il ripetersi del disallineamento fra
`error_policies.py` e il catalogo DB.

⭐ **Declassato il 2026-08-22.** Nella prima stesura era il prerequisito di
tutto. Per il §0-bis non lo è più della metà forense: nella timeline di un caso
singolo, un evento innominabile si legge lo stesso dal contesto degli altri.
Resta prerequisito **stretto** del Passo B, dove un codice muto falsa il conto.

⭐⭐ **Seconda revisione, stesso giorno (V3/V4).** Il seed **è già applicato** —
`20260805-07-seed-messaggi-errore-codici-legacy`, eseguito il 2026-08-07 — e il
segnaposto è sceso a **327 righe su 116.569 (0,3%)**. Del Passo 1 resta quindi
**solo il rubinetto**: le 327 residue dimostrano che il disallineamento continua
a produrne, ed è il check CI a doverlo chiudere.
⚠️ **E il Passo B non ha più nessun prerequisito**, ed è la parte da non perdere.
Avevo scritto che lo bloccavano lo split D11 di `E_PARAMETRO_INVALIDO` e il
recinto test/esercizio: **è sbagliato**. `error_log.function_name` è `NOT NULL` e
per quel codice ha **70 valori distinti**: l'aggregato si raggruppa per *(area,
`function_name`, codice)* e discrimina già. Lo split resta una cosa da fare — per
la **frase che legge l'operatore**, non per la leggibilità di un cruscotto — e ha
un brief suo (§5, Aperte #14). Il recinto test/esercizio è un difetto vero ma non
è un now-or-never (V4-bis).

### Passo 2 — `request_id` nei log Python

L'unico pezzo di correlazione che **non** entra nel Passo 0, perché non tocca il
DB: `request_id` nel formatter di logging (**B5**, Fase 0 della diagnostica —
una riga di `settings.py` più il filtro). Indipendente da tutto il resto, si può
fare in qualsiasi momento.

⭐ **E già che si è lì (2026-08-22, B11).** `request_id` esiste già come
contextvar (`apps/core/services/request_context.py`, assegnato da
`RequestContextMiddleware`) ed è **valorizzato al 100%** su `dbops.request_log`:
il pezzo mancante è davvero solo il filtro di logging. Ma nello stesso `INSERT`
(`request_log_middleware.py`) mancano **due colonne che esistono in tabella e
nessuno scrive**: `emittente_attivo_id` (0 su 353.758 — e il valore ce l'ha già
il JWT, `JWT_CLAIM_EMITTENTE_ATTIVO_ID`) e `tx_id`. O si valorizzano — e allora
il «per chi» è tracciato a livello di richiesta, gratis — o si tolgono: una
colonna che nessuno scrive è un invito a fidarsene.

### Passo A — La timeline di un caso *(la metà forense)*

> «Dammi la storia **di questa entità**, in ordine di tempo»: un lotto, una
> fattura, un push.

Filtri: `entity_type` + `entity_id`, e `correlation_id`. **Nessun aggregato,
nessuna finestra temporale, nessun cruscotto.** Read-only, `DomainAPIView`,
envelope standard, paginazione — niente di nuovo rispetto a [api.md](../api.md).

Perché è questa la prima superficie:

* **funziona identica in sviluppo e in esercizio** — le servono le sei righe di
  quel caso, non volumi;
* **non aspetta il Passo 1** (vedi sopra);
* è l'indice già presente sulla tabella (`ix_event_log_entity_time`): la query
  che serve è quella per cui la tabella è stata indicizzata.

Approda dove il caso si guarda già: la diagnostica del lotto e il pannello
«Passaggi» della fattura.

> ⛔ **VINCOLO DECISO DA TID IL 2026-08-24, e arriva da un altro cantiere**
> ([brief-db-bersaglio-errore.md](../work-done/brief-db-bersaglio-errore.md) §8.3): **un
> diario tecnico non diventa una superficie per tutti.** Se una schermata mostra
> `dbops.error_log` — o qualunque altro registro di appunti tecnici — nasce
> **dietro un permesso dichiarato**, per i tecnici, non visibile a chiunque apra
> l'applicazione.
>
> ⭐ **La ragione, con le sue parole**: *«altrimenti continuiamo a creare altre
> tabelle per mettere le segnalazioni tecniche che poi qualcuno mette a video…
> un loop infinito. Tutto il lavoro attuale è stato per dividere le due aree.»*
> Il loop si riconosce così: si separa l'appunto tecnico dalla frase per la
> persona, poi si mette l'appunto a video «così si vede meglio», e a quel punto
> serve un terzo posto per gli appunti. La separazione **non si difende
> scrivendo meglio: si difende negando la superficie**.
>
> ⚠️ Conseguenza diretta su questo passo: il `context` di una riga resta
> **appunti per chi indaga** e non va ripulito o riscritto per renderlo
> presentabile — la timeline di questo passo è **forense**, per chi ha il
> permesso di indagare, non una vetrina.

### Passo B — Le superfici aggregate

Dopo il Passo 1, e **dopo che esistano dati veri da aggregare**:

- **vista errori** trasversale (non legata al mese di competenza), con salto al
  lotto e alla commessa;
- **UI sugli endpoint orfani** (`job-runs`, `job-summary`): quasi solo lavoro
  frontend, il backend c'è;
- **consultazione di `error_log`** con filtri area/funzione/codice/`tx_id`.

⚠️ Costruita oggi, su questo ambiente, una vista aggregata sarebbe **illeggibile**
— e chi la guardasse ne trarrebbe conclusioni sbagliate, esattamente come è già
successo leggendo il §1.

### Passo C — Notifiche

Il precedente da imitare esiste: `MaintenanceRepository.job_liveness()` più le
soglie di `coda_lavori/gestione_service.py` producono già il badge «worker vivo /
coda ferma». Serve puntarlo su un'altra sorgente (eventi in errore, lotti fermi
da troppo tempo) e dargli un canale d'uscita — `EmailOutboxService` è già drenato
da un cron.

Non è «costruire il monitoring»: è riusare un meccanismo esistente.

### Passo D — Retention sui log di dominio

Estendere `cleanup_at` a `event_log` e ai log funzionali, con i termini decisi
da chi di dovere (per i documenti fiscali il riferimento è 10 anni). È azione
DB: brief dedicato. ⚠️ I termini **non** si dimensionano sui volumi del §1 (§0-bis).

⭐ **Proposta 2026-08-22:** la **colonna** `cleanup_at` su `event_log` entra nello
stesso `ALTER TABLE` del Passo 0 — è lo stesso lucchetto aperto una volta sola, e
costa zero. Restano di qui i **termini**, che sono un dato e non un codice: si
decidono con calma senza riaprire niente.

---

### Binario parallelo — i fallimenti visibili nelle liste

Non è un passo di questo piano e **non va messo in coda a nessuno di questi**:
non dipende da `event_log`. È lo stesso bisogno visto dal lato dell'operatore —
*«questa riga è ferma, ed ecco perché»* — e vive nella
[roadmap di fatturazione](fatturazione-roadmap.md).

Stato misurato il 2026-08-22, **dal seed, non dai dati**: su **47 liste**
registrate, due hanno una colonna che parli di errore — `config.email_log` (che
è un log per mestiere) e `vendite.lotto_fatture`, costruita quel giorno. Il
componente riusabile esiste già (`core/components/ErroreRigaInfo.vue`) e ha **un
solo consumatore**.

Va segnalato qui perché i due binari si somigliano e rischiano di essere
sequenziati: questo dà all'operatore il *perché* di una riga ferma, il Passo A dà
a chi ripara la *storia* di un caso. Servono a persone diverse.

---

## 5. Decisioni

### Chiuse

1. ✅ **Scope emittente su `event_log`** — *decisa il 2026-08-22 da Tid*: colonna
   emittente **e** RLS sulla tabella, prima dell'endpoint, non filtro
   applicativo. Motivo: «altrimenti mescoliamo troppe cose insieme». Diventa il
   Passo 0.
2. ✅ **Ordine dell'endpoint** — *2026-08-22*: prima la timeline per entità
   (Passo A), poi l'aggregato (Passo B). Motivo nel §0-bis.
3. ✅ **Eventi senza padrone fuori da `event_log`** — *decisa il 2026-08-22 da
   Tid*: `emittente_fiscale_id` **`NOT NULL`**; `PUSH_STARTED`/`PUSH_COMPLETED`
   restano nel loro registro di giro (`commesse_push_log`, creato in testa allo
   stato `IN_ESECUZIONE` così da avere `entity_id` vero e id del giro), ed
   `EMITTIBILITA_FALLITA` diventa **per commessa**. `event_log` resta
   uniformemente **per entità**: nessun NULL, nessun ramo speciale nella policy.
   *(era la #4 delle aperte)*
4. ✅ **`TRUNCATE` di `event_log`** — *autorizzata da Tid il 2026-08-22*. È
   l'unica via: il trigger append-only vieta `UPDATE` e `DELETE` (V7).
   *(era la #6)*
5. ✅ **La vista `vw_giornale_entita` entra nel Passo 0 come disegno** —
   *2026-08-22*: il Passo A legge una vista normalizzata su più registri, non il
   solo `event_log` (che da solo darebbe **quattro** codici per lotto). Il
   disegno sta nel Passo 0 perché decide **cosa deve reggere la riga** di
   `event_log`, che è l'unica cosa non rifacibile.
   ⏱️ **E dal 2026-08-23 non è più solo un disegno**: `script.vw_giornale_entita`
   è scritta (changeSet `20260822-70`, 12 asserzioni pgTAP verdi) e mostra **767
   righe da quattro registri** — di cui solo 12 vengono da `event_log`. ⭐ È la
   conferma di ciò che motivava la vista: il Passo A sul solo diario avrebbe
   consegnato l'1,6% della storia. Dettagli nel
   [brief del Passo 0](../work-done/brief-db-event-log-scope-e-riga-parlante.md) §3.6 e §4.
6. ✅ **`FORCE` sulla policy** — non è un bivio: parità con la famiglia
   (`ENABLE`, no `FORCE`) più filtro applicativo. Vedi la rettifica nel Passo 0
   (V1). *(era la #5)*

### Aperte

> ⚠️ Le vecchie **3, 4, 5 e 6** sono state decise il 2026-08-22 e sono passate
> fra le Chiuse. Le voci qui sotto sono quelle **residue**, più quelle nate dalla
> verifica sul DB dello stesso giorno.

7. ✅ **CHIUSA di fatto — verificato il 2026-09-05.** **Check CI** sul
   disallineamento codici: *solo sui codici nuovi o su tutti?* La risposta è nel
   codice e non era stata riportata qui — `backend/apps/core/tests/test_error_codes_db_policy_guardrail.py`
   (step CI *«Codici errore — nessun codice allarga il proprio significato»*)
   presidia i **nuovi** (`test_nessun_codice_nuovo_senza_policy`) e tiene il
   pregresso a **soglia** (`test_la_misura_non_e_degradata`), che deve calare.
   ⚠️ Il registro oggi conta **502** codici da dichiarare: è un debito misurato,
   non un errore. ⇒ Il Passo 1 è chiuso.
8. 🔵 **APERTA, e serve una decisione di Tid** — **Notifiche**: canale email o
   solo badge in-app in prima battuta? (Passo C). ⭐ È l'unica delle voci
   originali che non si è chiusa da sola: le altre le ha chiuse il lavoro, questa
   aspetta una scelta.
> ✅ **Le voci 9, 10, 11, 12 e 13 sono state decise il 2026-08-22 e sono
> confluite nel [brief del Passo 0](../work-done/brief-db-event-log-scope-e-riga-parlante.md)
> come D-6 (`actor`/`source` via), D-7 (il giro), D-8 (retention),
> D-9 (`entity_type` → `config.sorgenti`) e D-10 (niente guard). Restano qui
> in forma abbreviata come storia; le motivazioni complete stanno nel brief,
> insieme alle **sei domande nuove** che la scrittura del brief ha fatto
> emergere (§8 di là).**

9. ✅ **CHIUSA — verificato il 2026-09-05: le colonne non ci sono più.**
   `vendite.event_log` non ha né `actor` né `source`; «chi» resta su
   `user_insert`, dove il progetto lo mette già. La proposta qui sotto è stata
   accolta, e il testo resta come storia.
   🔴 **`actor` è ridondante, e B3 non è vero come scritto.** `event_log.user_insert`
   **dice già chi**: il trigger generico `script.trgfn_audit_data_user_generic` lo
   riempie da `app.jwt_user`, e in tabella ci sono `tid`, `pochi`, `fara`,
   `BATCH_FATTURAZIONE` — non `zeroerp_app`. La colonna costante e inutile è
   `actor` (`service:django` su tutte le righe), che duplica male `source`
   (`django` su tutte le righe). *Proposta: si eliminano `actor` e `source`* —
   siamo in `TRUNCATE`, togliere una colonna costa zero — *e «chi» resta dove il
   progetto lo mette già su 806 colonne.* Decisione di Tid.
10. 🔴 **`correlation_id` non identifica un giro: identifica il lotto.** Sul ramo
    pipeline vale `fatturazione_lotti.lock_batch_id`, che nasce col lotto
    (`COALESCE(p_lock_batch_id, uuidv7())`) e **non cambia mai** — mentre lo
    stesso lotto ha fino a **27 `task_runs`**. Quindi oggi duplica `entity_id` e
    la domanda «in che giro» resta senza risposta anche dopo il Passo 0, se non
    si decide **cosa sia un giro**: un `uuid` nuovo generato dal runner a ogni
    `run_pipeline`, il `tx_id` della transazione, o l'id del `task_run`.
    ⚠️ È lato scrittura: non è recuperabile dopo.
11. ✅ **CHIUSA — la via (a) è stata scritta, verificato il 2026-09-05.**
    `trgfn_event_log_append_only` distingue **alterare la storia** (UPDATE:
    sempre vietato) da **ritirare ciò che è scaduto** (DELETE: ammesso con la GUC
    di manutenzione **oppure** su riga con `cleanup_at <= now()`). ⭐ Il criterio
    del secondo ramo non è **chi** cancella ma **cosa**, così
    `dbops.fn_purge_cleanup_expired` funziona com'è. E il veto sull'UPDATE rende
    `cleanup_at` immutabile: nessuno può anticipare la scadenza di una riga
    scomoda. Il testo resta come storia.
    🔴 **La retention standard NON funziona su una tabella append-only.**
    `dbops.fn_apply_cleanup_at` valorizza `cleanup_at` con un **`UPDATE`**, e
    `dbops.fn_purge_cleanup_expired` cancella con un **`DELETE`**: il trigger
    `trgfn_event_log_append_only` li vieta **entrambi**. Aggiungere la colonna e
    basta non produce retention: produce un job che fallisce. Tre vie:
    (a) `cleanup_at` calcolato **all'INSERT** più un'eccezione al veto sul solo
    `DELETE` di purge (riconoscibile da una GUC o dal ruolo di manutenzione);
    (b) **partizionamento per `event_time`** e retention per `DROP PARTITION` —
    i trigger di riga non c'entrano; costa poco **ora** che la tabella è vuota e
    molto dopo, ma la PK diventa `(id, event_time)`;
    (c) nessuna retention, finché il volume non la chiede.
    *Proposta: (a).* Il volume di `event_log` è basso per costruzione (quattro
    righe per giro di pipeline) e (b) è complessità comprata su un rischio non
    misurato. Ma è una scelta, e va scritta.
12. ✅ **CHIUSA il 2026-08-22 — nessuna delle tre: un catalogo suo.**
    `config.tipi_entita`, con dentro il **modo di risoluzione dell'emittente**,
    e `entity_type` che ci punta con una FK (D-17 del brief). ⭐ La ragione per
    cui non è `config.sorgenti`: quel catalogo ha la colonna `attivo`, e una FK
    verso un padre con `attivo` fa **generare all'automazione** il lucchetto che
    spegnerebbe il diario. ⭐ E la nota qui sotto sul `key_selector` **aveva
    ragione e resta valida**: per il giornale `entity_id` è la PK `id`, sempre;
    la chiave `uid` serve a chi *punta* a un'entità da fuori — il **bersaglio**
    di un errore — e il catalogo la dichiarerà per quello
    ([brief-db-bersaglio-errore](../work-done/brief-db-bersaglio-errore.md) §6, changeSet 63).
    ~~**`entity_type`: vocabolario libero, `CHECK`, o `config.sorgenti`?** Oggi è
    `text` senza vincolo.~~ Il progetto **ha già** un registro polimorfo,
    `config.sorgenti` (15 voci, con `target_table` e `key_selector`), che però
    non conosce `LOTTO`. Legarlo darebbe alla derivazione un dispatch **guidato
    dai dati** invece che da un `CASE`. ⚠️ Ma `config.sorgenti.key_selector`
    ammette `uid` (preventivi, offerte) mentre `event_log.entity_id` è `bigint`:
    la regola resta **`entity_id` = la PK `id` della tabella, sempre** — il
    `key_selector` serve al grafo di lineage, non al giornale.
13. **Serve il guard di scrittura `trgfn_guard_emittente_scope`?** Se l'emittente
    lo **deriva il DB** dall'entità, il guard verificherebbe un valore che il DB
    ha appena calcolato, e direbbe la stessa cosa del `WITH CHECK` della policy.
    *Proposta: non attaccarlo*, e scrivere nel brief **perché** — così il
    prossimo non lo aggiunge «per simmetria con DDT».
14. 📌 **Nota — `E_PARAMETRO_INVALIDO`: brief a parte, dopo** *(decisione di Tid,
    2026-08-22)*. Non è meccanico: lo sollevano **126 funzioni in 7 schemi** (88
    in `vendite`, 18 in `script`), e la scelta del codice sostitutivo si fa
    **parametro per parametro** sulla domanda «chi può rimediare». Fuori da
    questo cantiere, e **non** è prerequisito del Passo B (`error_log.function_name`
    è `NOT NULL` e ha 70 valori distinti su quel codice: l'aggregato discrimina).
    Materiale già pronto per quel brief: `config.codici_errore` ha già la colonna
    **`obsoleto_dal`** (il pattern di deprecabilità del progetto, non
    `attivo=false`), esiste `dbops.vw_codici_errore_da_dichiarare` e il suo test
    di guardia lato Django. ⚠️ **Il rubinetto va prima della rincorsa**, non
    dopo — §9.1 del brief classi.

---

## 6. Rapporto con gli altri documenti

| Documento | Rapporto |
| --- | --- |
| [Messaggi-di-Errore-e-Generazione-Log.md](../../guide/Messaggi-di-Errore-e-Generazione-Log.md) | La guida **stabile**: modello di scrittura + mappa di consultazione. Quando un passo di qui atterra, la guida si aggiorna e qui resta la storia |
| [analisi-diagnostica-produzione-senza-accesso-db.md](analisi-diagnostica-produzione-senza-accesso-db.md) | Altro mestiere (§0). Ne condividiamo la **Fase 0** (Passo 2) e ne siamo il fornitore per la Fase 1 |
| [fatturazione-roadmap.md](fatturazione-roadmap.md) | I suoi item **#5 vista errori**, **#6 alerting**, **#7 correlation_id** sono qui dentro. La roadmap resta il documento di dominio, questo quello trasversale |
| [fatturazione-roadmap.md](fatturazione-roadmap.md) — *binario parallelo* | I **fallimenti visibili nelle liste** restano di là: stesso bisogno, altra persona (operatore, non chi ripara) e **nessuna dipendenza** da questo piano — vedi §4 |
| [brief-db-seed-messaggi-errore-mancanti.md](../work-done/brief-db-seed-messaggi-errore-mancanti.md) | Il Passo 1, già scritto |
| [audit-e-tracciabilita.md](../../guide/audit-e-tracciabilita.md) | Il suo §8 «Pianificato» chiede già `GET /core/request-log/` e una «dashboard anomalie»: stesso bisogno, arrivato prima |

---

*Analisi WIP — Osservabilità e consultazione dei log (3 agosto 2026;
piano rivisto il 22 agosto 2026: §0-bis, Passo 0, divisione A/B).*
