# Analisi — Diagnostica di produzione senza accesso al database

> **Stato:** ✅ **CHIUSA e archiviata in `work-done/` il 2026-09-19** (Tid:
> «credo che anche questo sia chiudibile»). ⚠️ **Chiusa senza costruire**: non
> è la chiusura di un lavoro fatto, è l'archiviazione di un'analisi che **non
> ha mai avuto la validazione che chiedeva** (§11) e il cui terreno — una
> produzione da diagnosticare — oggi non esiste. Il riquadro sotto dice che
> cosa ne è uscito e che cosa resta, con la destinazione; il resto del
> documento è com'era (25 luglio, rivalutato il 24 agosto).
>
> **✅ CHIUSA — 2026-09-19.** Letto sul repo, non dalle parole del documento:
>
> | Parte | Stato | Dove si legge |
> | --- | --- | --- |
> | **La metà delegata** (§3.1, osservabilità) | ✅ **tutta consegnata**: giornale per entità e trasversale, `error_log` consultabile dietro permesso, `request_id` nei log, `cleanup_at` anche su `fatturazione_lotti_log` e `fatture_log` (Passo D, 18-09 — l'ultimo «🟡 parziale» del §0-bis), R-1 chiuso a DB | [analisi-osservabilita-log.md](analisi-osservabilita-log.md), chiusa lo stesso giorno |
> | **La decisione del 24-08** («un diario tecnico non diventa una superficie per tutti: se si mostra, è per i tecnici e dietro un permesso») | ✅ **è diventata una regola applicata**: `error_log` sta dietro `AdminAPIView` | piano BE/FE, D-E1 |
> | **La metà sua** — classificare i dati dello schema, mascherare, riprodurre un caso altrove, profilo di supporto, perimetro AI (§5.4–§5.6, §6, §7) | ⛔ **zero righe di codice, zero brief**, e le **sei domande del §10.2 ferme dal 24-08** (otto settimane dalla stesura). Nessuno l'ha usata: la citano la mappa e tre archivi | `git log`: ultimo contenuto 24-08 |
>
> ⭐ **La lezione, ed è la stessa della sua §0-bis.** Un'analisi che aspetta una
> validazione senza data invecchia *senza dirlo*: qui era scritto (il 67% smentito
> il giorno dopo) ed è successo di nuovo al documento intero. Le fondamenta che
> inventaria sono vere e restano; il piano in cinque fasi **non è stato
> rifiutato** — è stato **superato dal tempo** e va riscritto **da una
> produzione reale**, se e quando ci sarà, non aggiornato da qui.
>
> **Che cosa resta, e dove va:**
>
> * 🧭 **Le sei decisioni del §10.2** (provider AI in produzione; staging C o D;
>   profilo supporto — bypass RLS o GUC controllato; error tracker esterno;
>   classi di dato; chi risponde dei pacchetti) → **una riga** in
>   [mappa-concentrica.md](../../mappa-concentrica.md) §«Decisioni aperte»,
>   che le tiene come decisione, non come lavoro. La prima precede tutto il
>   resto, com'era scritto.
> * 🔵 **Le eccezioni non gestite non finiscono in `error_log`**
>   (`ApiExceptionMiddleware`, Fase 0 seconda di tre): l'unico pezzo concreto e
>   piccolo. Non ha un cantiere; è del BE, e sta scritto qui perché chi aprirà
>   `error_log` e non ci troverà un 500 sappia perché.
> * 📌 [integrazione-server-mcp.md](../work-in-progress/integrazione-server-mcp.md)
>   la chiama «documento padre» per il canale diagnostico e il profilo supporto:
>   è dello stesso luglio e nello stesso stato («non ancora pianificato»). Il
>   link è ripuntato; se e quando quel documento si muoverà, ripartirà da una
>   produzione, non da questa analisi.
>
> ---
>
> **Destinatari:** Tid, team DB, sviluppatori backend/frontend
>
> **Tipo:** analisi + base di sviluppo (non è ancora un piano operativo per-fase)
>
> **Stato (storico):** ~~WIP~~ — proposta da validare prima della progettazione tecnica.
> ⚠️ **Perimetro ristretto il 2026-08-24**: la parte di osservabilità è stata
> **delegata** ai documenti che la possiedono (§3.1). Qui restano
> classificazione dei dati, mascheratura, riproduzione, profilo di accesso e
> perimetro AI.
>
> **Data:** 2026-07-25 · **rivalutato** il 2026-08-24 (§0-bis)
>
> **Origine:** documento di analisi di Tid («Diagnostica di produzione senza accesso
> al database», luglio 2026), qui **riscritto e ancorato al codice e alla
> documentazione vivi** del repo.
>
> **Postura del documento.** L'analisi originale è impostata come costruzione da zero.
> La verifica sul repo dice altro: ZeroERP ha **già** le fondamenta (storicizzazione a
> snapshot, tre strati di tracciabilità, framework automazioni DB, grafo di genealogia
> documenti, capabilities per entità, canale di sistema RLS). Il lavoro nuovo è
> **comporre, classificare e chiudere**, non fondare.

---

## 0-bis. 🔄 RIVALUTAZIONE — 2026-08-24, dopo il cantiere osservabilità

> **Perché.** L'analisi è del 25 luglio, con un aggiornamento del 3 agosto. Da
> allora due cantieri hanno lavorato **esattamente sul suo inventario**:
> `event_log`/osservabilità e «l'errore porta un bersaglio». Tre affermazioni del
> §3 oggi sono **false**, e due fasi non partono più da zero. L'impianto regge —
> è la misura sotto che va rifatta.
>
> 📌 Il documento più vicino a questo è
> [analisi-osservabilita-log.md](analisi-osservabilita-log.md), che ha lo stato
> passo per passo (§3-quater): quello è il piano, questo è il perché.

### Cosa è cambiato — e cosa ne è seguito

| Diceva | Oggi |
| --- | --- |
| *«`vendite.event_log` è **write-only**: zero endpoint, zero consumatori»* | ⛔ **superato**: il primo consumatore è in servizio — `script.vw_giornale_entita` e la scheda «Storia» del drawer fattura, validata in-app |
| *«l'`actor` vale **sempre** `service:django`: non si può ricostruire chi ha agito»* | ⛔ **superato**: la riga porta `auth_user_id`, l'emittente (NOT NULL, con RLS), `tx_id` e `correlation_id` per corsa. È il **Passo 0**, fatto |
| `request_log` … `tx_id` | ⚠️ **la colonna non esiste più** (tolta il 2026-08-24): quella riga nasce quando l'unità di lavoro ha già chiuso, quindi il suo `tx_id` non esisteva davvero. La correlazione HTTP↔DB resta su `request_id` |
| *«il 67% delle righe di `error_log` ha codice `MESSAGGIO_NON_DEFINITO`»*, prerequisito della Fase 1 | ⛔ **chiuso il giorno dopo che fu scritto** (2026-08-04, `brief-db-seed-messaggi-errore-mancanti`), ed è l'esempio che ha deciso la delega qui sotto. ⚠️ Se quel numero serve, si **rimisura** — e col contesto giusto: su una tabella con RLS un conteggio senza GUC torna zero e **sembra un dato** |
| *«lo standard `cleanup_at` non è applicato ai log di dominio»* | 🟡 **parziale**: `event_log` ce l'ha; `fatturazione_lotti_log` e `fatture_log` no |

### ⛔ La conseguenza: il §3.1 è stato DELEGATO

Non una correzione riga per riga — una **cessione di proprietà**. L'inventario
dell'osservabilità ha oggi documenti vivi che lo possiedono, e tenerne qui una
copia significa risincronizzarla a ogni loro movimento: il caso del 67% mostra
che non succede, e che una copia invecchia **senza dirlo**.

➡️ Questo documento resta su ciò che **nessun altro copre**: classificare i dati
dello schema, mascherarli, **riprodurre** un caso altrove, e decidere **con quale
identità** si guarda la produzione — più il **perimetro AI** (R7), che dal 25
luglio non ha ancora una risposta e precede tutto il resto.

### Le fasi non partono più da zero

**Fase 0 — correlazione: 1 su 3 fatta.**

| | |
| --- | --- |
| `request_id` nei log Python | ✅ **fatto** (consegna BE-8): filtro + `req=%(request_id)s` nel formatter. Il criterio di accettazione **n. 7** del §9 è soddisfatto |
| persistere le **eccezioni non gestite** | 🔵 **aperto**: `ApiExceptionMiddleware` non scrive su `error_log` |
| error tracker esterno sì/no | 🔵 aperto, ed è ancora una decisione di Tid |

**Fase 1 — endpoint diagnostico: due contenuti su sette hanno già la sorgente.**
Il punto 4 (*cronologia*) ha ora un lettore vero — la vista cucita e il pannello
«Storia» — e il punto 7 (*frontiera del grafo*) era già servito da `passaggi/`.
Il punto 6 (*correlazione per `tx_id`*) è diventato possibile su `event_log`
adesso che la colonna c'è. ⭐ L'aggregatore ha meno da inventare di quanto il §5.3
supponesse: **quello che manca è il lato che nessuno ha ancora provato**, non il
materiale.

### Tre cose nuove che l'analisi non poteva sapere

1. ⭐ **Un errore adesso dice su QUALE cosa** è successo (cantiere del bersaglio,
   chiuso: [brief-db-bersaglio-errore.md](brief-db-bersaglio-errore.md)).
   Per il **report diagnostico** è materiale gratis: l'entità da guardare non va
   dedotta dalla prosa, viaggia su un canale suo;
2. ⛔ **Decisione di Tid del 2026-08-24 che vincola il §5.3 e il §5.6**: un
   diario tecnico **non diventa una superficie per tutti**. Se si mostra, è per i
   tecnici e **dietro un permesso dichiarato**. Motivo: *«altrimenti continuiamo a
   creare tabelle per le segnalazioni tecniche che poi qualcuno mette a video»*.
   ⭐ Conferma il §5.6 invece di contraddirlo — ma lo rende una **regola**, non
   una preferenza di disegno, e vale anche per il report diagnostico;
3. 🔴 **R-1: il tempo, da solo, non ordina.** Le colonne di orario dei registri
   hanno default `now()` (istante di **transazione**): 38 righe su 3 istanti. Ogni
   cronologia diagnostica eredita il problema — il punto 4 della Fase 1 compreso.
   Richiesta al team DB già scritta (§13 del brief `event_log`).

### ➡️ Conclusione della rivalutazione

L'impianto **non cambia**: due artefatti, cinque fasi, mascheratura in estrazione.
Cambiano **il punto di partenza** (la Fase 0 è a un terzo, la Fase 1 ha già due
sorgenti) e **due presupposti da rifare**: la misura del 67% e la frase
sull'`actor`. ⚠️ Le questioni del §10.2 restano **tutte aperte** — nessuno dei due
cantieri le ha toccate, e la prima (provider AI in produzione) precede ancora
tutto il resto.

---

## 0. Rapporto con i documenti già esistenti

Questo documento non nasce in un vuoto: tre documenti aperti toccano lo stesso
perimetro. Vanno riconciliati **adesso**, prima di scrivere codice, altrimenti fra
sei mesi ci sono tre progetti che si contraddicono.

| Documento | Stato | Rapporto con questa analisi |
|---|---|---|
| [integrazione-server-mcp.md](../work-in-progress/integrazione-server-mcp.md) §6.1 (investigazione bug erratici), §6.3 (profilo «supporto») | WIP | **Sovrapposizione forte.** Descrive già il canale diagnostico, i tool `investigazione_*`, il profilo supporto e il vincolo «lettura cross-org ⇒ bypass RLS a livello DB». Da qui in poi: **MCP è un *consumatore*** del canale definito in questo documento, non il progettista del canale. Il §6.3 va sostituito da un rimando al §5.5 di qui. |
| [integrazione-ai-sviluppo-v2.md](../work-in-progress/integrazione-ai-sviluppo-v2.md) | WIP | Evoluzione tool/RAG/rendering dell'assistente. **Nessuna sovrapposizione** salvo il punto «audit `ai_initiated`», che qui diventa rilevante (§7.3). |
| [analisi-sicurezza-aggiornata.md](analisi-sicurezza-aggiornata.md) | Chiuso (Step 1+2 applicati) | Fornisce il **framing di sicurezza già validato**: difese vere = permessi + RLS + conferma umana + assenza esfiltrazione + audit affidabile; free-text = dato ostile (P3). Questa analisi lo eredita, non lo rinegozia. |
| [framework-automazione-db-migliorie.md](framework-automazione-db-migliorie.md) | Archiviato | La Fase 2 (§5.3) è una **nuova regola dentro quel framework**, non un sottosistema separato. Il §3.1 «Report stato automazioni» di quel documento e il check di classificazione sono lo stesso mestiere. |

Documenti di riferimento (non modificati da questa analisi, ma presupposti):
[audit-e-tracciabilita.md](../../guide/audit-e-tracciabilita.md) ·
[storicizzazione-tabelle.md](../../guide/storicizzazione-tabelle.md) ·
[automazione-db.md](../../guide/automazione-db.md) ·
[sorgente-polimorfa.md](../../guide/sorgente-polimorfa.md) ·
[architettura-permessi-e-autorizzazioni.md](../../guide/architettura-permessi-e-autorizzazioni.md) ·
[contratto-guc-app.md](../../guide/contratto-guc-app.md) ·
[api.md](../api.md) ·
[catalogo-building-block-backend.md](../backend/catalogo-building-block-backend.md).

---

## 1. Contesto e problema

Oggi ZeroERP è pre-produzione e il debug avviene per ispezione diretta del database di
test. Con la prima installazione in produzione questo metodo cade per tre ragioni
indipendenti:

1. **Rischio operativo** — un accesso in scrittura al DB di produzione è un rischio non
   giustificato, per chiunque, autore incluso.
2. **Riservatezza** — i dati contengono anagrafiche, importi, contratti e testi liberi
   di terzi. Esporli a strumenti esterni va evitato **per costruzione**.
3. **Vincoli non applicabili** — «non cancellare» detto a un assistente AI è un vincolo
   interpretativo, non tecnico, e può essere disatteso (è già successo in sviluppo). Un
   vincolo affidabile è un **permesso negato a livello di database**.

**Il problema in una frase.** Rendere osservabile e riproducibile lo stato di un caso di
produzione senza che nessuno — persona o strumento — debba accedere al database di
produzione, e senza che dati personali reali escano dal perimetro.

**Nota di realtà sul punto 3.** Il «vincolo tecnico» che serve **esiste già** in ZeroERP:
`system_process_context` ([system_context.py](../../../../backend/apps/core/services/system_context.py))
ripunta la connessione a un **alias di ruolo DB** dedicato, con guard *fail-loud* se il
ruolo non ha i privilegi attesi, e il middleware web rifiuta con `E_DB_ROLE_UNSAFE` una
connessione `BYPASSRLS` sul percorso richiesta. Il profilo diagnostico va costruito come
**alias di connessione a un ruolo read-only**, non come un livello di permesso
applicativo in più (§5.5).

---

## 2. Requisiti

Ripresi dall'analisi originale, con un'aggiunta.

| ID | Requisito | Motivazione |
|----|-----------|-------------|
| R1 | **Riproducibilità** — da un caso segnalato si ricostruisce su test una situazione che manifesta lo stesso comportamento | condizione perché la correzione sia verificabile e non congetturale |
| R2 | **Nessuna scrittura sul DB di produzione** fuori dall'applicazione e dalle migrazioni versionate | elimina alla radice il rischio distruttivo |
| R3 | **Minimizzazione** — esce solo il necessario, mascherato | principio di minimizzazione; riduce l'impatto di un pacchetto finito nel posto sbagliato |
| R4 | **Basso attrito per chi raccoglie** — un amministratore, non necessariamente lo sviluppatore | in produzione la segnalazione parte dal cliente |
| R5 | **Tracciabilità** — chi, quando, su quale entità, con quale livello di mascheratura | è un accesso a dati personali e va trattato come tale |
| R6 | **Manutenibilità rispetto allo schema** — una colonna nuova non deve poter creare un buco silenzioso | uno strumento disallineato dallo schema è peggio che inutile: è dannoso |
| **R7** | **Coerenza di perimetro** — nessun canale *già attivo* deve vanificare R3 | *nuovo*: vedi §7.1, il canale AI oggi manda dati reali a un fornitore esterno |

---

## 3. Inventario — cosa ZeroERP ha già

È il cuore di questa revisione. Ogni riga è verificata sul repo.

### 3.1 Osservabilità — ⛔ **non è più materia di questo documento** *(delegato il 2026-08-24)*

Qui c'era l'inventario dei tre strati di log, i loro buchi e due riquadri di
misure. **Non ci sta più**, e non perché sia sbagliato: perché nel frattempo
quell'inventario ha **un proprietario vivo**, e una copia va risincronizzata a
ogni movimento dell'originale — cioè invecchia in silenzio. Era già successo: il
riquadro del 2026-08-03 dava il *67% di errori non nominabili* come prerequisito
della Fase 1, e quel problema è stato **chiuso il giorno dopo**.

➡️ **Dove vive adesso**

| Cosa | Documento |
| --- | --- |
| Stato dei registri, i passi, cosa manca | [analisi-osservabilita-log.md](analisi-osservabilita-log.md) — il **piano**, §3-quater per lo stato |
| `event_log`: scope emittente, RLS, `auth_user_id`, `tx_id`, `correlation_id`, `cleanup_at` | [brief-db-event-log-scope-e-riga-parlante.md](brief-db-event-log-scope-e-riga-parlante.md) |
| Errori nominabili — seed, segnaposti, classi, presidi | **dieci brief chiusi** in `work-done`, dal 2026-08-04 al 19 (`brief-db-seed-messaggi-errore-mancanti`, `-round-2`, `brief-db-segnaposti-messaggi-errore`, `brief-db-be-classe-codici-errore`, `brief-db-be-terzo-lato-presidio-codici`, `brief-db-codice-errore-strutturato`, …) |
| «Su QUALE entità è successo» — il bersaglio dell'errore | [brief-db-bersaglio-errore.md](brief-db-bersaglio-errore.md) *(chiuso)* |

➡️ **Cosa questo documento continua a chiedere all'osservabilità**, e sono due
cose sole:

1. **la correlazione**, che è ciò che permette di sapere *quale* entità
   estrarre: `request_id` sulla richiesta HTTP e `tx_id` sulla transazione DB.
   ⚠️ Non sono la stessa cosa e non stanno sulla stessa riga — `request_log` il
   `tx_id` **non ce l'ha più** (tolto il 2026-08-24: quella riga nasce quando
   l'unità di lavoro ha già chiuso);
2. **la cronologia di un caso**, che oggi ha un lettore vero — la vista cucita
   `script.vw_giornale_entita` e la scheda «Storia» del drawer fattura.
   🔴 Con un limite che questo documento eredita: **il tempo, da solo, non
   ordina** (default `now()` = istante di transazione). Vedi R-1.

### 3.2 Stato e storia di un'entità

| Cosa | Dove |
|---|---|
| Snapshot completo per ogni UPDATE/DELETE | schema `storico.*`, snapshot **JSONB** dell'intero record, `valid_from`/`valid_to`, `tipo_operazione`, `tx_id` — [storicizzazione-tabelle.md](../../guide/storicizzazione-tabelle.md) |
| Provisioning automatico tabelle+trigger storico | `dbops.fn_run_automations_storico`, `fn_run_automations_storico_provision`, `fn_ensure_storico_table` |
| Stato a una data | [`script.fn_get_snapshot_as_of`](/dbzero/script/funzioni/fn_get_snapshot_as_of), [`fn_get_record_id_as_of`](/dbzero/script/funzioni/fn_get_record_id_as_of) |
| Diff fra versioni | [`script.fn_audit_summary`](/dbzero/script/manual/fn_audit_summary) + registro [`dbops.audit_sources`](/dbzero/dbops/tabelle/audit_sources) |
| UI audit già esistente | endpoint `/api/v1/amm/audit-log/` + [AuditLogView.vue](../../../../frontend/src/amministrazione/views/AuditLogView.vue) |
| Azioni/transizioni ammesse | `script.fn_available_actions_{preventivo,offerta,ordine,ddt,reso,contratto,commessa}` + `fn_capability_promo_articolo`; lato FE `useEntityCapabilities` |
| Contesto identità/permessi | `script.fn_current_identita_context`, `fn_get_user_permissions_map`, `fn_get_user_object_permissions_map`, `fn_get_user_actions_map`, i 5 GUC `app.*` ([contratto-guc-app.md](../../guide/contratto-guc-app.md)) |

### 3.3 Il grafo del caso

| Cosa | Dove |
|---|---|
| Dizionario dei tipi di entità (radici candidate) | [`config.sorgenti`](/dbzero/config/tabelle/sorgenti) — `codice_interno`, `target_table`, `key_selector` (`id`\|`uid`); [sorgente-polimorfa.md](../../guide/sorgente-polimorfa.md) |
| Traversal ricorsivo documenti | [`vendite.fn_documento_lineage`](/dbzero/vendite/manual/fn_documento_lineage) su `vw_documento_lineage_archi` — direzione avanti/indietro, cycle guard, profondità 10, `SECURITY INVOKER` (RLS applicata) |
| API già esposta | `GET /<dominio>/<id>/passaggi/` su 7 domini (factory `build_passaggi_view`) — [api_lineage_passaggi.md](../../backend/vendite/manual/api_lineage_passaggi.md) |

**Limite da mettere a verbale:** il lineage copre i **documenti di vendita**. Il
*contorno* di un caso (anagrafiche, listini, parametri, permessi, emittenti, categorie
cliente, configurazione) **non è nel grafo**. È il contorno, non il documento, a far
fallire una riproduzione (§5.5, §6.2).

### 3.4 Precedente diretto di «endpoint diagnostico»

[`PricingDiagnoseService`](../../../../backend/apps/vendite/services/pricing_diagnose_service.py):
read-only, nessun side-effect, **non risolve: ispeziona la configurazione** ed espone i
check a stadi con l'`esito_atteso`. È esattamente la forma dell'artefatto §5.1 — e
dimostra che il pattern è già accettato nel progetto.

### 3.5 Motore per la classificazione (R6)

| Cosa | Dove |
|---|---|
| Regole dichiarative per schema/tabella/colonna | [`dbops.automation_rules_tbl`](/dbzero/dbops/tabelle/automation_rules_tbl) + [`automation_scope`](/dbzero/dbops/tabelle/automation_scope) + `automation_overrides_cols` |
| Orchestratore con `exec_mode` (AUTO/CI/SCHEDULED) e `dry_run` | `dbops.fn_run_automations` |
| Precedente di registro colonna-per-colonna con «consentito» | `dbops.fk_index_policy` + `fn_seed_fk_index_policy` / `fn_populate_fk_index_policy` |
| Precedenti di check CI che *fallisce* | `apps/core/tests/test_transaction_atomicity_guardrail.py` (AST, gira senza DB), `test_system_context_usage_whitelist` |

### 3.6 Retention e ciclo di vita dei dati temporanei

`cleanup_at` + `dbops.fn_apply_cleanup_at` (TTL per tabella) +
`dbops.fn_purge_cleanup_expired` (purge a batch) — già in uso su `request_log`,
`error_log`, `audit_log`, `ai_query_log`. È **lo standard di progetto** per i dati a
scadenza: il registro estrazioni e i pacchetti ci vanno sopra, non su una regola nuova.

> ✅ **Verificato il 2026-08-03: il meccanismo funziona** (job `automations_cleanup`,
> ultimo giro 2026-08-02) — quindi la scelta di appoggiarcisi regge. Due precisazioni
> che non la invalidano ma vanno sapute:
>
> - lo standard è applicato alle `dbops.*` e **non ai log di dominio**.
>   ⚠️ **Aggiornato il 2026-08-24**: `vendite.event_log` la `cleanup_at` ora ce
>   l'ha (arrivata col Passo 0); restano senza `fatturazione_lotti_log` e
>   `fatture_log`, che crescono senza policy — è il **Passo D** del piano
>   osservabilità. Per i pacchetti è irrilevante; diventa rilevante se un domani
>   il pacchetto includesse i log di dominio del caso;
> - su `error_log` restano **530 righe già scadute e non ancora rimosse**: il purge
>   passa, ma non è a saldo zero. Da tenere presente se si dimensiona il TTL dei
>   pacchetti sul comportamento osservato invece che su quello dichiarato.

---

## 4. Opzioni — rivalutate

**A — Accesso read-only diretto alla produzione.** Risolve R2 ma non R3 (i dati reali
restano visibili) né R1 (leggere non è riprodurre). *Resta misura di contenimento
eccezionale, non canale ordinario.*

**B — Solo logging ed error tracking.** Necessaria, non sufficiente: un traceback dice
*dove* si è rotto, non *su quale configurazione di dati* — e in un sistema con la logica
nel DB la causa è quasi sempre lo stato. **Ma in ZeroERP non è «già fatto»**: manca lo
strato applicativo correlato. *Diventa la Fase 0, prerequisito di tutto — e dal
2026-08-24 il primo dei suoi tre punti è fatto (§5.2).*

**C — Replica di staging anonimizzata.** L'analisi originale la rimanda per costo e
latenza. **Va rivalutata al rialzo**: il criterio «il pacchetto supera i vincoli di
integrità e i controlli di dominio» è la parte più costosa dell'opzione D proprio perché
qui NOT NULL, CHECK, FK, trigger guard e RLS sono fitti (cfr. memoria di progetto
`feedback_audit_db_preventivo_smoke`). Con **una installazione e un DB non enorme**, uno
staging rigenerato da dump mascherato costa meno di un traversal corretto e soddisfa R1
senza il problema della chiusura del grafo. *Candidata primaria per la riproduzione.*

**D — Estrazione mirata per caso, mascherata.** Elegante e minimale, ma il costo vero è
la **chiusura** (§3.3) e la **coerenza sotto vincoli**. *Da tenere come evoluzione, non
come primo passo.*

**Conclusione della revisione:** **D per capire** (endpoint diagnostico, §5.2) e **C per
riprodurre** (§5.4), con il bundle per-caso come Fase 3b solo se C si dimostra
insufficiente.

---

## 5. Soluzione proposta — cinque fasi

### 5.1 I due artefatti (invarianti)

| Artefatto | Risponde a | Natura | Profilo |
|---|---|---|---|
| **Report diagnostico** | «cosa vede il sistema, adesso, su questa entità» | sincrono, read-only, leggibile da persona, già mascherato | amministratore del cliente (attrito basso, rischio basso) |
| **Pacchetto riproduttivo** | «come rimetto in piedi questo caso altrove» | asincrono, leggibile da macchina, TTL definito, audit rinforzato | sviluppatore, con autorizzazione esplicita del cliente (attrito alto, rischio alto) |

> **Correzione rispetto all'analisi originale.** R4 («basso attrito per l'amministratore»)
> e §7 («funzionalità privilegiata, non concessa per comodità») **non stanno insieme sullo
> stesso artefatto**. Separarli per profilo di rischio è la condizione perché entrambi i
> requisiti restino veri.

### 5.2 Fase 0 — Correlazione (prerequisito, costo basso)

Senza questa fase non si sa nemmeno **quale** entità estrarre.

- ✅ **FATTO (2026-08-24, consegna BE-8)** — `request_id` nel formatter/filter di
  logging Python: `settings.py` ha il filtro `request_id` e ogni riga porta
  `req=%(request_id)s`. ⭐ Con lui è soddisfatto il **criterio di accettazione
  n. 7** del §9 (un traceback è correlabile alla riga di `request_log`).
- 🔵 **APERTO** — Persistenza delle eccezioni **non gestite** — passano già da
  `ApiExceptionMiddleware` — con codice, `request_id`, `tx_id`, traccia troncata.
  Destinazione naturale: `dbops.error_log` (oggi alimentata solo DB-side).
- 🔵 **APERTO** — Decisione esplicita su un error tracker esterno: **se** lo si introduce, va trattato
  come destinatario di dati personali (R3/R7) e richiede l'ok di Tid sulla dipendenza
  (memoria `feedback_autorizzazioni_esplicite`).

### 5.3 Fase 1 — Endpoint diagnostico (aggregatore)

Non un sottosistema: un **aggregatore** dei componenti già esistenti (§3.2), sul modello
di `PricingDiagnoseService`.

Contenuto della risposta, per un'entità radice:

1. valori correnti dell'entità (con classificazione applicata, §5.4);
2. stato + fase normalizzata + **azioni ammesse** (`fn_available_actions_*`) con motivo
   di indisponibilità;
3. esito dei check di dominio rilevanti (guard/`fn_check_*`) senza eseguire nulla;
4. cronologia: catena snapshot `storico.*` + `fn_audit_summary`;
5. contesto permessi con cui l'utente segnalante l'ha vista (`fn_get_user_permissions_map`,
   GUC, scope emittente);
6. correlazione: ultime richieste HTTP e errori con lo stesso `request_id`/`tx_id`;
7. **frontiera del grafo**: nodi adiacenti da `fn_documento_lineage` (non l'intero grafo).

Vincoli di costruzione: `DomainAPIView`/`AdminAPIView` secondo [api.md](../api.md),
read-only, `@extend_schema`, envelope standard, nessuna query nuova che duplichi logica
già nel DB (filosofia DB-first).

> **Valore collaterale, confermato:** l'esercizio obbliga a dichiarare *cosa il sistema
> considera stato rilevante* di un'entità. Parte di questa dichiarazione esiste già
> (`config.sorgenti`, fase/stato normalizzati della proiezione di dominio); il resto va
> esplicitato, ed è utile a prescindere dal debug.

### 5.4 Fase 2 — Classificazione dei dati nello schema (R6)

**Non un meccanismo nuovo: una regola in più nel framework che già esiste** (§3.5).

- La classificazione vive nel catalogo DB, accanto alla colonna, sul modello di
  `dbops.fk_index_policy` (registro `(schema, tabella, colonna) → classe`, con seed +
  popolamento assistito).
- L'applicazione avviene via `automation_rules_tbl` con un nuovo `rule_type`
  (es. `DATA_CLASS`), `exec_mode='CI'`, e `dry_run` per la verifica preventiva.
- Il **check che fallisce** su colonna non classificata segue i precedenti già in CI
  (`test_transaction_atomicity_guardrail`, whitelist `system_context`).
- Classi minime: `PUBBLICO` / `INTERNO` / `PERSONALE` / `PERSONALE_SENSIBILE` /
  `LIBERO_NON_CLASSIFICABILE` (l'ultima è la categoria dei testi liberi, §7.2).

**Decisione conseguente (chiude la domanda aperta 2 dell'originale):** si maschera **in
estrazione**, mai in caricamento. Motivo tecnico, non di gusto: mascherare in caricamento
attiva i trigger `BEFORE UPDATE/DELETE` di storicizzazione, che scriverebbero snapshot
con i valori **in chiaro** in `storico.*`, oltre a sporcare `tx_id` e i campi
`user_insert`/`user_update`.

**Conseguenza sugli snapshot JSONB:** lo storico contiene l'**intero record serializzato**.
La classificazione per colonna va quindi riusata sulle **chiavi omonime** dello snapshot,
altrimenti lo storico è un canale di fuga. In prima battuta: gli storici **restano fuori**
dal pacchetto (§6.3).

### 5.5 Fase 3 — Riproduzione

**3a — Staging rigenerato (opzione C, candidata primaria).** Dump di produzione →
mascheratura applicata secondo la classificazione (Fase 2) → carico su ambiente di test
dedicato. Vantaggi: R1 pieno, nessun problema di chiusura del grafo, i vincoli di
integrità sono soddisfatti per costruzione. Costi da quantificare: dimensione del DB,
finestra di rigenerazione, spazio.

**3b — Pacchetto per-caso (opzione D).** Da affrontare solo se 3a è insufficiente. In tal
caso, la struttura del pacchetto **è a tre strati**, e questo scioglie da solo la domanda
aperta 5 dell'originale:

| Strato | Contenuto | Come viaggia |
|---|---|---|
| 1 — configurazione | schemi, funzioni, trigger, seed `config`/`dbops` | **non nel pacchetto**: è presupposto dell'ambiente, ricostruito da Liquibase |
| 2 — contorno anagrafico | soggetti, BA, emittenti, listini, parametri, permessi coinvolti | nel pacchetto, **mascherato** |
| 3 — grafo del caso | entità radice + chiusura via `config.sorgenti` + `fn_documento_lineage` | nel pacchetto, **mascherato** |

**Versione (chiude le domande aperte 3 e 4).** Il pacchetto porta il **changeset
Liquibase massimo applicato** (`DATABASECHANGELOG`) più la versione applicativa; il
caricamento **rifiuta** se l'ambiente di destinazione è a un changeset precedente.
*Da verificare:* `public.version_info` è citata in `.codex/PROJECT_CONTEXT.md` ma non
risulta nelle migrazioni `migrations_v2` — se non esiste più, la fonte è la sola
`DATABASECHANGELOG`.

### 5.6 Trasversale — Profilo diagnostico e perimetro AI

**Profilo «supporto» (assorbe [integrazione-server-mcp.md](../work-in-progress/integrazione-server-mcp.md) §6.3).**
Va costruito come **alias di connessione DB a un ruolo dedicato read-only**, coerente con
`system_process_context`, e **non** come quarto livello accanto a `TUTTO`/`LETTURA`/`BLOCCATO`.
Requisiti: nessuna scrittura (privilegio negato dal DB, non dall'app); lettura
cross-emittente **esplicita e tracciata**; sessioni a scadenza breve; ogni accesso marcato
in modo distinguibile con motivo. La scelta fra «bypass RLS» e «GUC ampio controllato»
è una **decisione DB** e va nel brief al team DB (§10).

**Perimetro AI (R7).** Con `AI_PROVIDER=anthropic|mistral` ogni `tool_result`
dell'assistente invia **dati reali di clienti** a un fornitore esterno in esercizio
ordinario, e `dbops.ai_query_log.input_text` conserva le domande in chiaro. Progettare la
minimizzazione sul canale diagnostico mentre resta aperto quello ordinario è
incoerente: la decisione «quale provider gira in produzione» (self-hosted / EU / DPA col
fornitore) **precede** il pacchetto riproduttivo. Il documento di riferimento per il
framing di sicurezza resta [analisi-sicurezza-aggiornata.md](analisi-sicurezza-aggiornata.md).

---

## 6. Modello concettuale

### 6.1 Entità radice

Le radici ammesse **non si inventano**: sono le voci di `config.sorgenti` (che portano già
`target_table` e `key_selector`). Il criterio di ammissione è: esiste una
`fn_available_actions_*` o una proiezione di stato per quel tipo. Radici plausibili di
partenza: `PREVENTIVO`, `ORDINE_VENDITA`, `DDT_VENDITA`, `FATTURA`, `COMMESSA`, `PRATICA`.

### 6.2 Chiusura

Tre direzioni, con regole diverse:

- **avanti/indietro sul grafo documenti** → `fn_documento_lineage` (già limitato: cycle
  guard, livello < 10);
- **verso il basso** (righe, note, allegati, indirizzi documento) → per FK dirette;
- **verso il contorno** (BA, soggetti, listini, parametri, permessi) → **fermarsi al primo
  livello** e includerlo nello strato 2; è la scelta che tiene il pacchetto finito.

Ciò che **non** entra: log e tracciabilità (`request_log`, `ai_query_log`, `audit_log`) —
vedi §7.2 — e gli storici (§5.4).

### 6.3 Coerenza sotto mascheratura

Il dato mascherato deve restare **utilizzabile**: uguaglianze preservate (stessa
sostituzione per lo stesso valore, con seed registrato), vincoli di dominio soddisfatti
(CF/PIVA/IBAN formalmente validi, perché i CHECK e i trigger li verificano), valori
derivati coerenti. Un pacchetto che non supera i controlli del sistema che deve
diagnosticare è inservibile — ed è il motivo per cui l'opzione C è candidata primaria.

### 6.4 Livelli di mascheratura

Due, decisi ora perché condizionano il resto: **INTERNO** (struttura integra, dati
personali sostituiti, testi liberi rimossi) e **RISTRETTO** (in più: importi
perturbati/azzerati e riferimenti esterni rimossi) per eventuali usi fuori dal team.

---

## 7. Sicurezza, privacy e rischio residuo

### 7.1 Perimetro già aperto

Vedi §5.6: il canale AI in esercizio è oggi la superficie più ampia di uscita dati.
È il primo rilievo, non una nota a piè di pagina.

### 7.2 Il rischio residuo è più largo del «testo libero»

L'analisi originale cita note e descrizioni. L'elenco reale in ZeroERP:

| Fonte | Perché è un rischio |
|---|---|
| `vendite.note` (partizionate) + note articoli/pratiche | testo digitato liberamente |
| `dbops.audit_log.params` / `.result` (jsonb) | parametri e risultati di funzioni, non classificabili per colonna |
| `dbops.error_log.context` (jsonb) | contesto d'errore con valori reali |
| `dbops.request_log.query_string` | **le ricerche contengono nomi e codici fiscali** |
| `dbops.ai_query_log.input_text` / `response_text` | domande in linguaggio naturale sui clienti |
| `documenti.documenti_generati_file` | PDF con dati reali |

**Regola operativa:** se il pacchetto include i log correlati, i dati personali rientrano
dalla finestra dopo essere stati mascherati alla porta. I log **non entrano nel
pacchetto**; entrano, se serve, come estratti separati e classificati.

**Free-text come dato ostile.** Confermata la regola già fissata in
[integrazione-server-mcp.md](../work-in-progress/integrazione-server-mcp.md) §6.1 e
[analisi-sicurezza-aggiornata.md](analisi-sicurezza-aggiornata.md) (P3): se un
contenuto free-text viene passato a un modello, va delimitato ed etichettato come dato non
fidato. Vale a maggior ragione nel contesto diagnostico, che gira con i privilegi più alti.

### 7.3 Tracciabilità delle estrazioni (R5)

Ogni estrazione è un accesso a dati personali: va registrata (chi, quando, entità, livello
di mascheratura, motivo) e il pacchetto va eliminato a chiusura del caso, con TTL tecnico
su `cleanup_at` (§3.6). Se e quando si introduce il marker `ai_initiated`
([integrazione-ai-sviluppo-v2.md](../work-in-progress/integrazione-ai-sviluppo-v2.md)), la stessa logica serve
a distinguere le estrazioni fatte tramite agente.

### 7.4 Perimetro normativo

Informativa, base giuridica, ruolo dei fornitori coinvolti (incluso il provider AI): da
verificare con un consulente. Qui è trattato solo come vincolo di progettazione.

---

## 8. Ciclo di vita di una correzione

1. Segnalazione dal campo, con riferimento all'entità.
2. **Report diagnostico** per capire (Fase 1); pacchetto/staging per riprodurre (Fase 3).
3. Riproduzione su ambiente di test.
4. Correzione: patch applicativa **e/o brief al team DB**. Le azioni DB
   (DDL/trigger/funzioni/migrazioni/pgTAP) **non** si eseguono dal lato backend: passano
   dal team DB su `dev/db-tid` (memoria `feedback_db_actions_passaggio_team`).
5. Test di regressione che **fallisce prima e passa dopo**.
6. Applicazione su collaudo, verifica, poi produzione, con backup verificato a monte.
7. Eliminazione del pacchetto a chiusura del caso.

> **Precisazione obbligatoria sul rollback.** I changelog Liquibase già mergiati **non si
> modificano** (`.codex/AGENTS.md`): la «procedura di rollback» è una **nuova migrazione
> inversa** con numerazione successiva, non un rollback del changeset. Va scritto qui,
> altrimenti al primo incidente qualcuno tocca uno YAML già pushato.

---

## 9. Criteri di accettazione

Su ambiente di test:

1. da un caso noto, il **report diagnostico** spiega lo stato senza che nessuno apra il DB;
2. la ricostruzione (staging o pacchetto) **riproduce il comportamento difettoso**;
3. nessun dato personale in chiaro nelle colonne classificate;
4. la ricostruzione **supera vincoli di integrità e controlli di dominio** (NOT NULL,
   CHECK, FK, trigger guard, RLS);
5. l'aggiunta di una colonna non classificata **fa fallire il check in CI**;
6. il report diagnostico è eseguibile da un amministratore senza intervento dello
   sviluppatore; il pacchetto riproduttivo **no**, e il tentativo è tracciato;
7. un traceback applicativo è **correlabile** a `request_id` e alla riga di `request_log`.

---

## 10. Questioni aperte

### 10.1 Chiuse da questa analisi

| Domanda originale | Chiusura |
|---|---|
| 1 — quali entità radice | quelle registrate in `config.sorgenti` con proiezione di stato/azioni (§6.1) |
| 2 — mascheratura in estrazione o in caricamento | **in estrazione**, per i trigger di storicizzazione (§5.4) |
| 3/4 — formato e disallineamento di versione | changeset Liquibase massimo + versione app; caricamento rifiuta ambienti indietro (§5.5) |
| 5 — configurazione e anagrafiche comuni | modello a tre strati: configurazione = presupposto dell'ambiente (§5.5) |
| 6 — retention e responsabilità | `cleanup_at` + `fn_apply_cleanup_at` + `fn_purge_cleanup_expired`, standard di progetto (§3.6) |

### 10.2 Aperte, da decidere

1. **Provider AI in produzione** (R7) — precede tutto il resto. Decisione di Tid.
2. **C vs D** — dimensione DB e finestra di rigenerazione dello staging: servono i numeri.
3. **Profilo supporto** — bypass RLS vs GUC ampio controllato: decisione DB (§10.3).
4. **Error tracker esterno** sì/no in Fase 0, con le implicazioni R3/R7.
5. **Classi di dato** — l'insieme minimo proposto al §5.4 va confermato.
6. **Chi risponde** dei pacchetti prodotti (persona, non ruolo generico).

### 10.3 Prerequisiti verso il team DB (da trasformare in brief)

Nessuna azione DB parte da qui. Da mettere in un brief dedicato su `dev/db-tid`:

- registro di classificazione colonne + `rule_type` nel framework automazioni (§5.4);
- ruolo/alias DB read-only per il profilo diagnostico, con la scelta su RLS (§5.6);
- eventuale `cleanup_at` sulle nuove tabelle di registro estrazioni (§7.3).

---

## 11. Prossimo passo

Validare l'impostazione (in particolare §4 opzione C, §5.6 perimetro AI, §10.2). Alla
validazione seguono, nell'ordine: (a) aggiornamento di
[integrazione-server-mcp.md](../work-in-progress/integrazione-server-mcp.md) §6.3 con rimando a questo
documento; (b) brief DB §10.3; (c) piano operativo della Fase 0.

---

*Analisi WIP — Diagnostica di produzione senza accesso al database (25 luglio 2026).*
