# Analisi — Osservabilità: consultare i log dall'applicazione

> **Destinatari:** Tid, backend, team DB
>
> **Tipo:** analisi di stato + piano. È il documento **principale** per il
> lavoro sull'osservabilità operativa.
>
> **Stato:** WIP — stato misurato il 2026-08-03, piano da validare
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
[brief-db-seed-messaggi-errore-mancanti.md](brief-db-seed-messaggi-errore-mancanti.md)
(207 codici, proposta SQL validata e idempotente).

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

---

## 4. Piano proposto

L'ordine non è per dimensione ma per **dipendenza**: ogni passo rende utile il
successivo.

### Passo 1 — Rendere nominabili gli errori *(prerequisito)*

Applicare il seed dei 207 codici
([brief](brief-db-seed-messaggi-errore-mancanti.md), già pronto e validato) e
decidere il check CI che impedisca il ripetersi del disallineamento fra
`error_policies.py` e il catalogo DB.

Senza questo, tutto ciò che segue mostra `MESSAGGIO_NON_DEFINITO`.

### Passo 2 — Chiudere la correlazione

- `request_id` nel formatter di logging Python (**B5**, Fase 0 della
  diagnostica: una riga di `settings.py` più il filtro);
- `correlation_id` passato da `commesse_push_orchestrator` a `log_event`
  (**B4**), e valutare con il team DB la colonna su `task_runs`;
- identità reale al posto di `service:django` (**B3**): i GUC
  `app.current_user_id` e `app.ruolo_applicativo` la hanno già, va solo
  passata ai chiamanti;
- già che si tocca il push: `entity_id` reale al posto dello `0` segnaposto.

### Passo 3 — Un endpoint di lettura su `event_log` *(la chiave di volta)*

Filtri: dominio, entità, `severity`, **finestra temporale a ore**,
`correlation_id`. Read-only, `DomainAPIView`, envelope standard, paginazione —
niente di nuovo rispetto a [api.md](../api.md).

È il passo che sblocca tre cose insieme: la timeline nella diagnostica del
lotto, una «vista errori» che guardi davvero gli eventi, e la sorgente per le
notifiche.

> ⚠️ **Scope emittente.** `event_log` non ha RLS. L'endpoint deve applicare lo
> scope in lettura come fanno le viste dei cruscotti (`security_invoker` + GUC,
> fail-closed) — o l'alternativa è chiedere al team DB una vista scoped. Da
> decidere prima di scrivere la view: è la differenza fra un endpoint di
> diagnosi e una fuga di dati fra emittenti.

### Passo 4 — Le superfici

- **Vista errori** trasversale (non legata al mese di competenza), con salto al
  lotto e alla commessa;
- **UI sugli endpoint orfani** (`job-runs`, `job-summary`): è quasi solo lavoro
  frontend, il backend c'è;
- **consultazione di `error_log`** con filtri area/funzione/codice/`tx_id` — ha
  senso **solo dopo il Passo 1**.

### Passo 5 — Notifiche

Il precedente da imitare esiste: `MaintenanceRepository.job_liveness()` più le
soglie di `coda_lavori/gestione_service.py` producono già il badge «worker
vivo / coda ferma». Serve puntarlo su un'altra sorgente (eventi in errore,
lotti fermi da troppo tempo) e dargli un canale d'uscita — `EmailOutboxService`
è già drenato da un cron.

Non è «costruire il monitoring»: è riusare un meccanismo esistente.

### Passo 6 — Retention sui log di dominio

Estendere `cleanup_at` a `event_log` e ai log funzionali, con i termini decisi
da chi di dovere (per i documenti fiscali il riferimento è 10 anni). È azione
DB: brief dedicato.

---

## 5. Decisioni da prendere

1. **Scope emittente su `event_log`** — applicato nell'endpoint o in una vista
   DB scoped? (Passo 3, blocca la scrittura della view)
2. **Check CI** sul disallineamento codici — solo sui codici nuovi o su tutti?
   (Passo 1, §4.2 del brief)
3. **Retention dei log di dominio** — quali termini, e quali tabelle
   (Passo 6)
4. **Notifiche** — canale email o solo badge in-app in prima battuta?
   (Passo 5)

---

## 6. Rapporto con gli altri documenti

| Documento | Rapporto |
| --- | --- |
| [Messaggi-di-Errore-e-Generazione-Log.md](../../guide/Messaggi-di-Errore-e-Generazione-Log.md) | La guida **stabile**: modello di scrittura + mappa di consultazione. Quando un passo di qui atterra, la guida si aggiorna e qui resta la storia |
| [analisi-diagnostica-produzione-senza-accesso-db.md](analisi-diagnostica-produzione-senza-accesso-db.md) | Altro mestiere (§0). Ne condividiamo la **Fase 0** (Passo 2) e ne siamo il fornitore per la Fase 1 |
| [fatturazione-roadmap.md](fatturazione-roadmap.md) | I suoi item **#5 vista errori**, **#6 alerting**, **#7 correlation_id** sono qui dentro. La roadmap resta il documento di dominio, questo quello trasversale |
| [brief-db-seed-messaggi-errore-mancanti.md](brief-db-seed-messaggi-errore-mancanti.md) | Il Passo 1, già scritto |
| [audit-e-tracciabilita.md](../../guide/audit-e-tracciabilita.md) | Il suo §8 «Pianificato» chiede già `GET /core/request-log/` e una «dashboard anomalie»: stesso bisogno, arrivato prima |

---

*Analisi WIP — Osservabilità e consultazione dei log (3 agosto 2026).*
