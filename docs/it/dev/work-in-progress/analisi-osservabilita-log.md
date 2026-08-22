# Analisi — Osservabilità: consultare i log dall'applicazione

> **Destinatari:** Tid, backend, team DB
>
> **Tipo:** analisi di stato + piano. È il documento **principale** per il
> lavoro sull'osservabilità operativa.
>
> **Stato:** WIP — stato misurato il 2026-08-03, **piano rivisto il 2026-08-22**:
> i log servono prima a *trovare* un problema (§0-bis), lo scope emittente
> smette di essere una decisione rinviata e diventa il **Passo 0** (§4).
>
> **Origine:** richiesta di Tid (2026-08-03): *«dobbiamo fornire uno strumento
> per accedere velocemente ai log, specialmente a quelli della fatturazione»*.
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

### 1.2 🔴 Il registro errori non sa nominare due terzi degli errori

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

### 1.4 ⚠️ `fatture_log` è vuota

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
| B1 | Il 67% di `error_log` non è attribuibile | qualunque strumento di consultazione mostra soprattutto rumore |
| B2 | `event_log` non è leggibile da nessuna parte | manca la timeline per entità; l'alerting non ha sorgente; il `correlation_id` non ha consumatori che ne dimostrino il valore |
| B3 | Identità non tracciata sugli eventi | l'audit non dice **chi**: requisito di compliance non soddisfatto |
| B4 | `correlation_id` assente sul ramo push | «una query ricostruisce la timeline» vale solo per la pipeline |
| B5 | Log Python non correlabili | un traceback non si lega alla richiesta che l'ha generato (Fase 0 della diagnostica) |
| B6 | Endpoint senza UI | lavoro già fatto e inutilizzato |
| B7 | Nessuna notifica | un lotto fermo in errore resta invisibile finché qualcuno non guarda |
| B8 | Retention assente sui log di dominio | crescita non governata |
| **B9** | **`event_log` non ha scope emittente né RLS** *(aggiunto 22/08)* | qualunque endpoint di lettura mostrerebbe gli eventi di **tutti** gli emittenti: è il buco che manda il Passo 0 in testa al piano |

---

## 4. Piano proposto *(rivisto il 2026-08-22)*

L'ordine non è per dimensione ma per **dipendenza**: ogni passo rende utile il
successivo. Rispetto alla prima stesura cambiano due cose, entrambe dal §0-bis:
lo scope emittente non è più una decisione rinviata ma il **Passo 0**, e il
vecchio Passo 3 si divide in **A** (forense) e **B** (aggregato).

| Passo | Chi | Blocca |
| --- | --- | --- |
| **0** — la riga dice chi, per chi, in che giro | 🔴 team DB | A e B |
| **1** — rendere nominabili gli errori | team DB (seed già pronto) | **solo B** |
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
| *(e un quarto)* `entity_id` | ⚠️ `0` segnaposto sul ramo push | un evento che non si lega a nessuna entità |

Sono **quattro difetti dello stesso lato** — il lato **scrittura** — e toccano
gli stessi due punti: `vendite.fn_log_event` e i suoi due chiamanti
(`pipeline_repository.log_event`, `commesse_repository.log_event`). Vanno in un
**cantiere solo**: farli in due passaggi vuol dire riaprire due volte gli stessi
file e rimettere due volte le mani su una funzione che tutti chiamano.

**Cosa chiedere al team DB** — brief dedicato, questo documento non è il brief:

1. `emittente_fiscale_id` su `vendite.event_log` + RLS con il pattern **già in
   casa**: policy `rls_*_ef_whitelist` (`FOR ALL`, `script.fn_scope_ef_whitelist`,
   gate `OPERATORE`) e guard di scrittura `script.trgfn_guard_emittente_scope`,
   come su DDT, ordini, preventivi, fatture e resi. Niente di inventato: è
   l'ondata a cui la tabella non ha partecipato;
2. `fn_log_event` con il parametro nuovo, più la decisione su **come si
   valorizza** (sotto);
3. nella stessa passata: `correlation_id` sul ramo push, `actor` reale al posto
   della costante, `entity_id` reale al posto dello `0`.

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
* **Il canale batch.** I worker scrivono con un ruolo proprio. Una RLS che non
  contempla quel canale rompe la scrittura **solo da lì**: è esattamente il
  difetto già capitato con `vendite.note`
  ([brief-db-grant-batch-cleanup-note.md](../work-done/brief-db-grant-batch-cleanup-note.md)),
  e fu trovato per caso da una prova reale, non da un test. Il guard DDT skippa
  quando `app.current_user_id` non è settato: quel ramo va **deciso**, non
  ereditato per copia;
* **Le 309 righe esistenti.** La tabella è append-only per trigger — `UPDATE`
  vietato — quindi un backfill ordinario non esiste. E per il §0-bis quelle
  righe non hanno valore probatorio. Proposta: non convertirle, **azzerare la
  tabella**. ⚠️ È una cancellazione: serve l'ok esplicito di Tid, e va nel brief
  come richiesta, non come fatto compiuto.

⚠️ **Attenzione al «attivo senza FORCE».** Sulle tabelle gemelle la policy è
`ENABLE` **senza** `FORCE`, e l'owner applicativo la bypassa: la protezione che
agisce oggi è il filtro applicativo del BE. Se `event_log` nasce con la stessa
configurazione, l'endpoint del Passo A **non può** considerare la RLS come sua
unica difesa. O il brief chiede il `FORCE` per questa tabella, o l'endpoint
filtra anche lui — e va scritto quale delle due, perché è la differenza fra uno
strumento di diagnosi e una fuga di dati fra emittenti.

### Passo 1 — Rendere nominabili gli errori *(prerequisito del solo Passo B)*

Applicare il seed dei 207 codici
([brief](../work-done/brief-db-seed-messaggi-errore-mancanti.md), già pronto e validato) e
decidere il check CI che impedisca il ripetersi del disallineamento fra
`error_policies.py` e il catalogo DB.

⭐ **Declassato il 2026-08-22.** Nella prima stesura era il prerequisito di
tutto. Per il §0-bis non lo è più della metà forense: nella timeline di un caso
singolo, un evento innominabile si legge lo stesso dal contesto degli altri.
Resta prerequisito **stretto** del Passo B, dove un codice muto falsa il conto.

### Passo 2 — `request_id` nei log Python

L'unico pezzo di correlazione che **non** entra nel Passo 0, perché non tocca il
DB: `request_id` nel formatter di logging (**B5**, Fase 0 della diagnostica —
una riga di `settings.py` più il filtro). Indipendente da tutto il resto, si può
fare in qualsiasi momento.

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

### Aperte

3. **Chi valorizza `emittente_fiscale_id`** — trigger con dispatch per
   `entity_type`, o parametro del chiamante? (Passo 0, blocca il brief DB)
4. **Eventi senza emittente** — colonna nullable e policy che decide chi vede i
   NULL, oppure `NOT NULL` con un emittente convenzionale di sistema? (Passo 0)
5. **`FORCE` sulla policy** — per questa tabella sì, o si resta a parità con le
   gemelle e l'endpoint filtra comunque? (Passo 0 → condiziona il Passo A)
6. **Le 309 righe esistenti** — azzerare la tabella? ⚠️ cancellazione, ok
   esplicito di Tid (Passo 0)
7. **Check CI** sul disallineamento codici — solo sui codici nuovi o su tutti?
   (Passo 1, §4.2 del brief)
8. **Retention dei log di dominio** — quali termini e quali tabelle (Passo D)
9. **Notifiche** — canale email o solo badge in-app in prima battuta? (Passo C)

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
