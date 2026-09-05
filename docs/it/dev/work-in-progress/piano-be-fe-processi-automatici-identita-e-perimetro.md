# Piano BE/FE — processi automatici: attore, perimetro, ritiro del bypass, UI

> **Che cos'è questo documento.** Il **piano operativo di backend e frontend** che
> raccoglie ciò che il cantiere «nessun processo senza operatore» lascia da fare
> **fuori da `db/`**. Le decisioni sono già prese e motivate in
> [analisi-db-be-processi-automatici-identita-e-perimetro.md](analisi-db-be-processi-automatici-identita-e-perimetro.md);
> ciò che il database ha costruito sta in
> [brief-db-processi-automatici-identita-e-perimetro.md](brief-db-processi-automatici-identita-e-perimetro.md).
> ⛔ **Qui non si riaprono le decisioni**: si traduce in endpoint, service, command,
> store e viste.
>
> **Destinatario:** backend (`dev/backend-tid`) e frontend.
>
> **Origine.** Il lavoro DB è **completo e pushato** (merge `e09a4c2cf`, changeSet
> `20260904-07…-51`). ⚠️ L'ultimo push porta nel messaggio il nome di un altro brief
> (`brief-residuo-fatturabili…`): il contenuto è questo cantiere.
>
> **Stato:** 🟢 **QUASI CHIUSO** (2026-09-05). ✅ Fatti e verdi: **0**, **6.3**,
> **1**, **2** (con R-4), **3**, **5**, **6**.
> 🔵 Resta il **lotto 4** (chiusura scadenze sulla coda), che aspetta **DB-1**.
> ⚠️ Due code fuori dal backend: il **`DROP ROLE`** del passepartout (provisioning)
> e lo **smoke C-9**, che osservava da quel ruolo — §11.
> ✅ **Decisioni di Tid, 2026-09-05**: le quattro domande del §7 sono chiuse; il
> passo 0 (la misura) è **stato eseguito**, e le tre regressioni che ha trovato
> sono **corrette** — §2.1.
>
> ⚠️ **Perimetro:** *chi* esegue un processo automatico, *dentro quale emittente*, e
> come lo si vede da dentro l'applicazione. ⛔ **Non** è di questo piano cosa fanno i
> processi.

---

## 0. In due parole

Il database adesso sa **chi sono i processi automatici** (un registro), sa **chi li
esegue** (una colonna sul giornale dei run e un utente tecnico per processo × azienda),
e **rifiuta** una scrittura di dominio da una sessione che non dice chi è.

Il backend, oggi, non gli parla ancora in quella lingua: i suoi comandi si registrano
senza nominare il processo, tre non si registrano affatto, e la fatturazione notturna
attraversa tutte le aziende con un ruolo che scavalca il perimetro.

⭐ **Il lavoro non è grande, ma ha un ordine obbligato**: il ruolo che scavalca si
toglie **per ultimo** — finché un processo lo usa, toglierlo lo ferma.

E in fondo c'è la parte che oggi non esiste per nessuno: **vedere tutto questo da
dentro l'applicazione** invece che da `psql`.

---

## 1. Il contratto: che cosa il DB offre adesso, e cosa smette di offrire

### 1.1 Offre

| Cosa | Dove | A che serve al BE |
| --- | --- | --- |
| il **registro dei processi** | `dbops.processi` (catalogo, 20 righe) · `processi_bersagli` · `processi_identita` (macchina) | il vocabolario dei codici processo, e la fonte della UI |
| l'**attore sul giornale** | `maintenance.job_run_log.processo_codice` (**hard FK** → `dbops.processi.codice`) + `auth_user_id` | un codice non registrato **non si scrive**: è un cancello, non un referto |
| due funzioni di run | `script.fn_job_run_start(…, p_processo_codice, p_auth_user_id)` · `maintenance.fn_run_and_log(… idem)` | ⚠️ **solo la seconda deriva** il codice dal jobname (i 12 job pgAgent si autodichiarano). La prima — quella dei command — **no**: il codice lo passa il chiamante |
| il **guard di classe** sulla coda | `dbops.coda_lavori_tipi.processo_codice NOT NULL` + `fn_accoda_lavoro` → `E_JOB_DOMINIO_SENZA_OPERATORE` | un tipo di dominio non si accoda più come `SISTEMA` |
| la **fabbrica degli utenti tecnici** | `script.fn_crea_utente_tecnico(processo, emittente[, profilo])` | il verbo dietro la futura UI |
| la classe **per bersaglio** | `dbops.automazione_chiusura_scadenze.classe` + `fn_apply_chiusura_scadenze(p_classe)` | serve alla migrazione della chiusura scadenze sulla coda |
| **sei viste di presidio** | `dbops.vw_processi_che_bypassano` · `…_dominio_senza_emittente` · `…_dominio_senza_difesa` · `vw_run_senza_attore` · `…_dominio_senza_identita` · `vw_emittenti_non_serviti` | ⭐ tutte con `GRANT SELECT` a `zeroerp_app`: sono **leggibili dall'applicazione**, ed è il materiale della UI |

### 1.2 Smette di offrire

| Cosa non si può più fare | Da dove arriva il rifiuto |
| --- | --- |
| scrivere su una delle **15 tabelle** con write-guard da una sessione **applicativa** senza `app.current_user_id` | `script.trgfn_guard_emittente_scope` → `E_SCOPE_SENZA_UTENTE` (500) |
| accodare un lavoro il cui processo è di classe `DOMINIO` con `run_as ≠ OPERATORE` | `dbops.fn_accoda_lavoro` → `E_JOB_DOMINIO_SENZA_OPERATORE` (500) |

Le 15 tabelle presidiate: `vendite.{preventivi, offerte_commerciali, ordini, ddt,
fatture, fatture_indirizzi, fatture_scadenze, fatturazione_lotti, contratti}`,
`pagamenti.{sistemazioni, vendite_movimenti, vendite_contabili, vendite_contabili_righe}`,
`documenti.documenti_generati`, `pratiche.pratiche`.

⭐ **Il criterio del guard è `row_security_active()`**, non un elenco di ruoli: chi
bypasserebbe comunque la RLS (proprietario, superuser, `BYPASSRLS`) passa anche di qui.

---

## 2. Lo stato di partenza — il backend regge, e va detto perché

⭐ **Oggi, dopo il push, non c'è niente di rotto a runtime.** Non è una speranza, è la
lettura dei tre percorsi che scrivono sotto guard:

| Percorso | Perché passa |
| --- | --- |
| ciclo **web** | `JwtAuditAuthentication` imposta i 5 GUC su ogni richiesta |
| **coda lavori**, item `OPERATORE` | `operator_identity_context` imposta gli stessi 5 GUC dallo scope catturato |
| i due **command batch** | girano nel canale `system_process_context`, ruolo `zeroerp_batch_fatturazione` (`BYPASSRLS`) |
| `send_pending_emails`, `sync_auth_user_active` | scrivono su tabelle **senza** write-guard (`config.email_outbox`, `auth_user`, `risorse_umane`) |

⚠️ **E gli smoke reggono**: tutti e 15 gli script di `backend/scripts/tests/` impostano
già il contesto operatore. ⛔ Ma «reggono» era una lettura del codice, non una corsa —
ed è stata fatta.

### 2.1 ✅ La misura è stata eseguita (2026-09-05), e ha trovato tre cose

| Cosa | Esito |
| --- | --- |
| suite Django | **4428 test, verde** (10 saltati) |
| smoke | 5 non-verdi su 15 — **2 noti** in baseline, **3 regressioni** |
| pgTAP | ⛔ non lanciato: è del team DB |

⭐ **Nessuna delle tre regressioni viene da questo cantiere**, e distinguerlo è costato
meno che ripararle: vengono tutte da lavori chiusi nei giorni scorsi, e sono di **due
sole specie**.

| Smoke | Specie | Causa |
| --- | --- | --- |
| `smoke-ritorno-lotto-a-draft` (`ASSERZIONE`, 3 casi su 9) · `smoke-push-termine-documento-commessa` (`SENZA_MATERIA`) | **fixture senza marchio** | changeSet `20260904-50`: `fn_select_attivita_fatturabili` prende **solo** le righe marchiate col proprio giro (`emit_batch_id = p_lock_batch_id`). Le due fixture creavano l'attività **senza marchio** ⇒ select a zero, il rilancio non rigenerava righe, e il secondo smoke si fermava sul proprio guard |
| `smoke-titoli-iva-annullo-movimento` (`ERRORE`) | **forma cambiata** | dal 2026-09-02 (`6d4c4209f`) `TitoliIvaRepository.list_movimenti` è paginato e ritorna `(righe, totale)`: lo smoke iterava il metodo, cioè **la tupla** |

⭐ **La prima specie non è un difetto da aggirare: è l'effetto voluto** dal cantiere
«esito parziale» — una riga che nessun giro rivendica non si fattura più. La stessa
correzione l'aveva già fatta il team DB su `db/pgtap/vendite/test-fatturazione-draft.sql`
(brief DB §12.8): ⇒ **la fixture si marchia col proprio giro**, come fa il backend.
⭐ E in `smoke-push-termine…` la correzione è migliore di una `INSERT` sistemata a mano:
quello smoke chiama la **pull vera**, quindi basta darle il giro (`p_emit_batch_id`) —
esattamente ciò che fa `pipeline_step_executor`.

⚠️ **La lezione è quella già scritta in `AGENTS.md`**: nessuno lancia gli smoke, e un
cantiere che quei file non li ha nemmeno aperti li lascia rossi per giorni. ⇒ Ogni lotto
di questo piano si chiude con `scripts/smoke-baseline.sh`, non con «i test unitari sono
verdi».

⚠️ Il database di sviluppo si connette come **`zeroerp_app`** (non il proprietario):
la RLS e il guard nuovo sono **effettivi in dev**. Ciò che passa qui passa anche altrove.

---

## 3. Che cosa NON è di questo piano

* la **colonna emittente su `config.email_outbox`** (R-7) e le **policy mancanti su
  `vendite.listini*`** (R-8): sono debiti del database, che questo piano **nomina** come
  vincoli e non progetta;
* **magazzino e acquisti**: in ristrutturazione, con i loro documenti. Da questo cantiere
  ereditano l'ordine giusto — si **dichiara** la classe del processo, e la RLS arriva
  come conseguenza;
* i **permessi degli operatori umani**: la whitelist emittenti non si tocca;
* il **contenuto** dei processi: cosa fatturano, cosa stampano.

---

## 4. I lotti, nell'ordine in cui vanno fatti

| # | Lotto | Blocca chi viene dopo? | Chiude |
| --- | --- | --- | --- |
| **0** | ✅ **FATTO** — la misura, e i codici errore: erano **sei**, non due | — | — |
| **1** | ✅ **FATTO** — l'attore sui run e i tre command orfani | no | R-3, passo 3 |
| **2** | ✅ **FATTO** — `draina_coda_stampa` gira un emittente alla volta con l'utente tecnico, e R-4 è chiuso | sì per il 5 | passo 4, R-4 |
| **3** | ✅ **FATTO** — la fatturazione accoda un lavoro per azienda; la corsia è entrata nella chiave (opzione A) | sì per il 5 | passo 5 |
| **4** | **`chiusura_scadenze`** migra sulla coda | no | passo 5-bis |
| **5** | ✅ **FATTO** lato applicazione — gateway, alias, credenziali e whitelist ritirati. ⚠️ Resta il `DROP ROLE`: è provisioning | — | passo 6-bis, R-2 |
| **6** | ✅ **FATTO** — 5 endpoint `AdminAPIView`, schermata, drawer a 3 schede, pannello dei presidi, seed della lista | no | R-5 |

✅ **Il lotto 6 gira IN PARALLELO ai lotti 1..5** (decisione di Tid, 2026-09-05). Non
aspetta nessuno: legge le sei viste, che esistono già.

⭐ **E conviene, non è solo permesso**: è la finestra da cui si guardano gli altri lotti
mentre si chiudono. Un presidio che si interroga da `psql` lo guarda chi sta lavorando a
quel pezzo; uno che sta in una schermata lo guarda anche chi passa di lì.

⚠️ **Il parallelo ha un punto di contatto solo**, e va tenuto d'occhio: la lista dei run
del lotto 6 mostra la colonna «attore», che il lotto 1 sta riempiendo. ⇒ Finché il lotto 1
non è chiuso quella colonna è **vuota per molti processi**, ed è corretto che si veda:
è il progresso del lavoro, non un difetto della schermata. ⛔ Non si nasconde la colonna
«finché non è pronta»: sarebbe togliere di mezzo proprio la cosa che si sta costruendo.

---

### Lotto 0 — La misura di partenza (✅ fatta) e i due codici errore

**0.1 — ✅ FATTO (2026-09-05): la misura, e le tre correzioni che ha prodotto.**
Il brief DB (§12.6-c) lasciava una cosa esplicitamente **non misurata** — la suite Django
dopo la chiusura della porta. È stata fatta, l'esito è nel §2.1, e i tre smoke rotti sono
corretti:

| File | Correzione |
| --- | --- |
| `smoke-ritorno-lotto-a-draft.py` | la fixture marchia l'attività col proprio giro (`emit_batch_id`) |
| `smoke-push-termine-documento-commessa.py` | il giro si dichiara **prima** del pull e la pull vera lo riceve (`p_emit_batch_id`) |
| `smoke-titoli-iva-annullo-movimento.py` | `list_movimenti` si spacchetta: ritorna `(righe, totale)` |

`scripts/smoke-baseline.sh` dopo: **2 non-verdi su 15, entrambi noti — zero regressioni**.

⛔ **Il codice di uscita di uno smoke non dice la verità** (uno stampa «ESITO: FALLITO»
ed esce `0`): si usa sempre `smoke-baseline.sh`, che classifica dall'output. ⚠️ E gli
esiti sono **tre**: un `SENZA_MATERIA` vale copertura **zero**, non «parziale» — è il
motivo per cui `smoke-push-termine…` andava guardato invece di contarlo fra i verdi.
⛔ `pgtap-baseline.sh` **non si lancia da qui**: è del team DB.

**0.2 — ✅ FATTO. I codici erano SEI, non due** — ed è la ragione per cui si rigenera
invece di aggiungere a mano ciò che si crede manchi. Oltre a `E_SCOPE_SENZA_UTENTE` e
`E_JOB_DOMINIO_SENZA_OPERATORE` mancavano i quattro di `fn_crea_utente_tecnico`
(`E_PROCESSO_NON_ELEGGIBILE_UTENTE_TECNICO`, `E_UTENTE_TECNICO_EMITTENTE_NON_VALIDO`,
`E_UTENTE_TECNICO_GIA_ESISTE`, `E_UTENTE_TECNICO_PROFILO_VIETATO`), che servono al
lotto 6. Tutti `TECNICO`; sei frasi di ripiego scritte a mano.

⇒ Due cancelli di CI sono rossi appena il migrate passa:
`test_error_codes_db_policy_guardrail` (ogni codice che il DB può nominare deve avere la
sua classe) e `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego`.

```bash
./manage-env.sh genera_error_policies          # riscrive il modulo generato
./manage-env.sh genera_error_policies --check  # la forma che gira in CI
```

⛔ `error_policies_generated.py` **non si tocca a mano**. Le due frasi di ripiego si
scrivono invece a mano in `error_messages_fallback.py`, **senza segnaposto**: è la
variante che serve proprio quando gli argomenti del `%s` non arrivano.
⚠️ Classe `TECNICO` ⇒ 500 ⇒ nessun `fields` da accendere e nessun `targets`: su un guasto
l'operatore non ha un gesto da fare.

---

### Lotto 1 — L'attore sui run (R-3, passo 1-BE e passo 3)

**1.1 — `registered_job` impara a dire chi è.**
`apps/core/services/job_run.py` chiama `script.fn_job_run_start` con **5 parametri**; la
funzione oggi ne prende **7**. I due nuovi restano `NULL` e `vw_run_senza_attore` resta
accesa.

```python
registered_job(job_name, *, processo_codice, origine=..., stepname=..., lock_key=..., auth_user_id=None)
```

⭐ **`processo_codice` keyword-only e SENZA default.** Un job nuovo non deve poter nascere
senza attore: con un default, il prossimo processo lo dimenticherebbe e nessuno se ne
accorgerebbe finché non lo cerca la vista. I call-site oggi sono **tre**.

⛔ **Il BB non deriva il codice dal jobname**, ed è una scelta: `run_fatturazione_batch`
registra `run_fatturazione_batch:immediata` — con la corsia attaccata. *Una derivazione
incompleta è peggio di nessuna derivazione*: copre una parte dei casi e tace sull'altra.
La derivazione completa esiste già dove è lecita, dentro `fn_run_and_log`, per i job
pgAgent.

⚠️ Intanto, nella vista di presidio, quel run compare con `processo_registrato = false`,
che si legge come *«manca la riga in `dbops.processi`»*. Non manca: manca il parametro.
La riga sparisce comunque appena il BE lo passa.

**1.2 — I codici processo hanno bisogno di una sede Python.**
Il catalogo è a database (`dbops.processi`), ma il Python deve **nominarli**. Serve un
modulo di costanti — `apps/core/services/processi.py` — con i codici dei processi che il
backend esegue, e le costanti importate dai command.
✅ **Estrazione autorizzata da Tid, 2026-09-05** (regola del 2 — le occorrenze sono sei
fin dal primo giorno).
⚠️ È un modulo di **costanti**, non un secondo catalogo: la verità sta in `dbops.processi`,
qui c'è solo il nome con cui il Python la indica. ⛔ Nessuna classe, nessun canale, nessuna
descrizione duplicata — quelli si **leggono**, e chi li copiasse creerebbe la seconda
sorgente che poi diverge. ⭐ Il presidio è già in mano al database: la **FK** su
`job_run_log.processo_codice` rifiuta un codice che il registro non conosce, quindi un
refuso in questo modulo non passa in silenzio, fallisce al primo run.

**1.3 — I tre command orfani entrano in `registered_job`.**

| Comando | Classe | Nota |
| --- | --- | --- |
| `send_pending_emails` | **DOMINIO** | ⚠️ per ora **solo** l'attore: l'iterazione per emittente **non è costruibile** finché `config.email_outbox` non porta l'emittente (R-7). Va scritto, non taciuto |
| `sync_auth_user_active` | AMMINISTRAZIONE | nessun perimetro |
| `listen_cambio_reparto` | AMMINISTRAZIONE | ✅ **run di AVVIO** (Tid, 2026-09-05): una riga aperta e chiusa subito, `message='listener avviato'`, host e PID nel `meta`. ⛔ Non un run per ciclo di riconnessione, e non un run lungo quanto il processo — vedi sotto |

⭐ **Perché il run di avvio, e cosa NON risolve.** Le due forme scartate rispondono
male alla stessa domanda: un run che dura quanto il processo resta «aperto» per settimane
(e su una morte improvvisa resta aperto per sempre); un run per riconnessione parla solo
quando c'è un singhiozzo, quindi *«funziona benissimo»* e *«è morto»* si scrivono uguali —
cioè non si scrivono affatto.

⚠️ **E il run di avvio non risponde a «è vivo adesso?».** Non è una mancanza di questa
scelta: è una domanda **diversa**, e ha già la sua risposta nel progetto —
`MaintenanceRepository.job_liveness` (l'ultimo run entro soglia, confrontato col clock
del DB), che alimenta il pallino del badge code in topbar. ⇒ Il battito periodico di un
listener è **un cantiere suo**, e si aggancia a quel meccanismo invece di inventarne un
secondo qui. Questo lotto gli dà l'attore, che è ciò che non aveva.

**1.4 — `auth_user_id` sul run.** Per i processi di dominio il run porta **anche**
l'utente tecnico. ⛔ Ma `run_fatturazione_batch` senza `--emittente-id` non ha **un**
utente: ne ha N, uno per emittente. ⇒ Il campo si valorizza dove la risposta è una sola
(`draina_coda_stampa` per-emittente, lotto 2), e resta `NULL` sul produttore, che di suo
non scrive niente di dominio.

**Come si vede che è chiuso:** `SELECT * FROM dbops.vw_run_senza_attore` → vuota, dopo
una corsa di ciascun comando.

---

### Lotto 2 — `draina_coda_stampa`: il primo processo di dominio con identità (passo 4, R-4)

⭐ **È la fatturazione in piccolo, sullo stesso binario**: ogni riga di coda è una fattura
di **un** emittente, il worker ha già il motore, usa il bypass, e contiene il guard da
riscrivere. Ci si misura il meccanismo prima del caso grande.

**2.1 — Il worker gira come utente tecnico, un emittente alla volta.**
Il roster è `dbops.processi_identita` ⋈ `config.user_emittenti_fiscali` per il processo
`draina_coda_stampa`: per ogni riga, un giro dentro `operator_identity_context` con
l'identità di quell'utente.
⭐ La RLS su `vendite.fatture_stampa_coda` è **armata dal 2026-09-04**
(`rls_fatture_stampa_coda_ef_whitelist`): dentro l'identità tecnica il claim vede solo le
righe del proprio emittente, **per costruzione**. Non serve un filtro applicativo nuovo —
serve *non aggirarlo*.

⚠️ **Prima di scriverlo, verificare che il roster sia leggibile**: né
`dbops.processi_identita` né `config.user_emittenti_fiscali` hanno RLS, quindi la lettura
senza GUC vede tutto. Se un giorno l'avessero, il produttore leggerebbe **zero righe** e
il giro chiuderebbe con «FATTO, 0» — un guasto che non assomiglia a un errore.

**2.2 — `_guard_canale_sistema` si riscrive, non si aggira** (R-4).
`document_generation_service._guard_canale_sistema` oggi **pretende** una connessione
`BYPASSRLS` quando si genera senza utente e senza scope. È una difesa scritta bene per il
mondo di oggi: nel mondo nuovo la generazione avviene **dentro** l'identità dell'utente
tecnico, quindi lo scope si risolve dall'utente esattamente come nel web e il ramo «senza
utente e senza scope» **non esiste più**.
⛔ Non si allarga il guard per farci passare il worker: si toglie il caso che lo rendeva
necessario.

**Come si vede che è chiuso:** una fattura di un emittente A non viene mai stampata dal
giro dell'emittente B, e il test BE del guard riscritto è verde.

---

### Lotto 3 — La fatturazione diventa un produttore di lavori (passo 5)

**3.1 — Il command smette di essere l'esecutore.**
`run_fatturazione_batch` accoda **N lavori `FATTURAZIONE_GIRO`**, uno per emittente
servito, `run_as=OPERATORE`, con lo `scope` dell'utente tecnico di quell'emittente. Il
corpo del giro resta `esegui_giro_fatturazione` — che ha **già** `--emittente-id`: il
mattone «un giro per un emittente solo» esiste, mancava chi lo chiama N volte e con quale
identità.

| | Oggi | Dopo |
| --- | --- | --- |
| corse | 1, attraverso tutti gli emittenti | N lavori in coda, in parallelo |
| perimetro | ⛔ nessuno (bypass) | ✅ l'emittente dell'utente tecnico |
| se uno fallisce | ⚠️ può fermare la corsa di tutti | ⭐ fallisce da solo, ritenta col backoff della coda |

**3.2 — 🔴 La chiave di idempotenza è l'unica cosa da disegnare bene.**
Il brief dice `emittente + corsia + competenza`. ⛔ **Oggi la corsia non c'è**: la chiave
business della coda è `competenza + scope [+ gruppi]`, e la corsia (`modalita`) viaggia
solo dentro `fino_a_stato`. Con un utente tecnico per emittente lo `scope` porta già
l'emittente — ma **immediata e differita dello stesso emittente e mese si deduplicano a
vicenda**, e la seconda sparisce senza errore.

⚠️ È il caso «troppo grossa» della tabella §10.1 dell'analisi: *silenzioso*. Va chiuso
in questo lotto, non dopo.

**3.3 — L'utente tecnico non ha capability, e va bene così.**
`fn_crea_utente_tecnico` non assegna nessun profilo: zero capability **è** minimo
privilegio. ⭐ Verificato: `fatturazione_giro_handler` non interroga nessuna azione di
processo — il gate `genera_fatture_lotti` sta sulla **view API**, che il worker non
attraversa.
⚠️ **Corollario da tenere presente**: il giorno in cui un handler della coda chiedesse
un'azione di processo, l'utente tecnico la troverebbe negata **in silenzio**. Lì servirà
un profilo `AD_HOC` — mai `SUPER_ADMIN`, che bypasserebbe lo scope *prima* della
whitelist.

**3.4 — Una nota sul modello, perché nessuno «corregga» la vista dopo.**
`vw_processi_dominio_senza_identita` e `vw_emittenti_non_serviti` escludono il canale
`CODA` perché *«sono accodati da un operatore»*. Dopo questo lotto un `FATTURAZIONE_GIRO`
può essere accodato da un **processo** — ma con l'identità di un utente **vero** (quello
tecnico), quindi l'invariante *«un job `OPERATORE` ha un'identità completa nello scope»*
regge intatta. ⛔ Le viste non vanno toccate.

---

### Lotto 4 — `chiusura_scadenze` migra sulla coda (passo 5-bis)

Il job pgAgent `chiusura_scadenze_daily` è l'unico processo di **dominio** che gira in
pgAgent: cambia lo stato gestionale di `vendite.contratti` e `vendite.listini_versioni`
ogni notte, senza attore.

* **prerequisito DB**: un tipo nuovo in `dbops.coda_lavori_tipi` (con il suo
  `processo_codice`, che è `NOT NULL` e ha la FK) — è un **seed**, quindi un brief al team
  DB (§6);
* **BE**: handler registrato in `handler_registry` che chiama
  `fn_apply_chiusura_scadenze(p_classe)`, più il produttore che accoda un lavoro per
  emittente servito;
* ⚠️ **vincolo dichiarato**: `vendite.listini*` **non ha policy RLS** (R-8). Finché è
  così, sul bersaglio listino il perimetro **non è applicato dal database**: il Caso A
  («si ferma da solo») non vale, un filtro dimenticato passerebbe. Il lotto si può fare;
  ⛔ non si può **dichiarare chiuso** il perimetro finché quel debito è aperto.

---

### Lotto 5 — ⛔ Ritiro del `BYPASSRLS` applicativo (passo 6 e 6-bis, R-2)

Ultimo, e non per prudenza: **finché un processo lo usa, toglierlo lo ferma.**

| Punto | Cosa cambia |
| --- | --- |
| `apps/core/services/coda_lavori/drainer_service.py` | `_dispatch_item`: il ramo `RUN_AS_SISTEMA` **non apre più il canale**. `SISTEMA` significa adesso «senza emittente», non «con bypass»: gira col ruolo applicativo normale ⇒ può toccare solo tabelle senza RLS. ⭐ Non rompe niente di vivo: i due tipi seedati sono entrambi `DOMINIO`/`OPERATORE` |
| `apps/core/services/system_context.py` | sparisce `system_process_context` e il letterale `SYSTEM_FATTURAZIONE_DB_ALIAS`. ⚠️ **`connection_role_bypasses_rls` RESTA**: lo usa `JwtAuditMiddleware` come guard fail-closed del percorso web (`E_DB_ROLE_UNSAFE`) |
| `zeroerp_backend/settings.py` | esce l'alias `system_fatturazione` |
| `apps/core/tests/test_system_context_usage_whitelist.py` | esce insieme alla funzione che presidia — ⭐ il cancello vero diventa `dbops.vw_processi_che_bypassano`, che guarda i **ruoli**, non gli import |
| `scripts/sql/provision_db_role_batch_fatturazione.sql` | ⛔ **non è un changeSet**: i privilegi dei ruoli batch vivono nel provisioning. Va ritirato lì, non in Liquibase |
| `.env` / `.env.systemd` | escono `DB_SYSTEM_FATTURAZIONE_USER` / `_PASSWORD` |

**Come si vede che è chiuso:** `SELECT * FROM dbops.vw_processi_che_bypassano` → **vuota**
(oggi ha una riga, marcata `DEBITO_DICHIARATO`).

---

### Lotto 6 — La UI dei processi automatici (R-5) — BE + FE

⭐ **Oggi tutto questo si vede solo da SQL**, e `GET /tracciamento/job-runs/` esiste da
mesi **senza un solo consumatore nel frontend**. Il registro, gli utenti tecnici e i sei
presidi hanno il `GRANT` per `zeroerp_app` apposta.

**6.0 — Dove vive.** ✅ **Decisione di Tid, 2026-09-05, rivista lo stesso giorno:
`amm-software`, non `strumenti`.** Rotta `/amm-software/processi-automatici`, voce in
`core/navigation.js` accanto ad Audit log e Operatori.

⭐ **La revisione è la scelta giusta, e la ragione è che il posto e il permesso tornano a
dire la stessa cosa.** La prima stesura metteva la schermata sotto `strumenti` e il
permesso su `SUPER_ADMIN`, e giustificava la divergenza — *«il posto lo decide la
famiglia, il permesso cosa mostra»*. È un ragionamento che regge in astratto e che in
pratica **lascia una voce sotto un'area che un operatore può avere in lettura, con dietro
un 403**: chi la vede e non può aprirla non impara niente, e chi mantiene la sidebar deve
ricordarsi che *quella* voce si filtra diversamente dalle altre. ⛔ Un'eccezione che
vive nella testa di chi l'ha scritta.

⇒ In `amm-software` non c'è niente da giustificare: **tutto** il dominio è SUPER_ADMIN,
il route guard e il filtro di sidebar esistono già, e la schermata eredita il
comportamento invece di dichiararne uno suo.

⭐ **E c'è un precedente esatto**: `AuditLogView` sta in `src/amministrazione/`, la sua
rotta è `/amm-software/audit-log`, l'endpoint è `/api/v1/amm-software/audit-log/` — e i
dati che mostra vengono da `dbops.audit_log`, cioè materiale di infrastruttura esposto
dall'amministrazione. È **la stessa forma** di questa schermata, e seguirla vuol dire non
inventare un secondo modo di fare una cosa che il progetto fa già.

| | Prima stesura | Dopo |
| --- | --- | --- |
| rotta | `/strumenti/processi-automatici` | **`/amm-software/processi-automatici`** |
| cartella FE | `src/strumenti/` | **`src/amministrazione/`** |
| client API | — | `src/amministrazione/api/amministrazione.js` (`BASE = '/amm-software'`) |
| endpoint | `core/tracciamento/processi/` | **`amm-software/processi/`** |
| voce di menu | filtro `auth.isAdmin` scritto a mano | ⭐ **niente**: il dominio è già admin-only |
| namespace i18n | `strumenti.processi.*` | **`amministrazione.processi.*`** |

**6.1 — BE: la lettura, e dove va il codice.**

| Rotta (`AdminAPIView`) | Cosa |
| --- | --- |
| `GET /api/v1/amm-software/processi/` | lista paginata del registro: codice, descrizione, classe, canale, attivo, `obsoleto_dal` + colonne **derivate a JOIN** — `ha_identita`, `emittenti_serviti`, `ultimo_run`, `ultimo_esito` |
| `GET /api/v1/amm-software/processi/<codice>/` | dettaglio: bersagli con il percorso all'emittente, utenti tecnici per emittente, ultimi run |
| `GET /api/v1/amm-software/processi/presidi/` | ⭐ le **sei viste** in un round-trip: per ognuna conteggio + prime righe |

⛔ **Il repository NON va in `apps/amm_software/db/`, e non è pedanteria di layering.**
La lettura del roster — *«quali utenti tecnici ha questo processo, e per quali
emittenti»* — serve **anche al produttore della fatturazione** (lotto 3) e al worker
della coda stampa (lotto 2), che vivono in `apps/vendite`. E `api.md` vieta le chiamate
laterali fra moduli allo stesso livello: `vendite` non può importare da `amm_software`.

⇒ **Repository e service in `apps/core/`** (`processi_repository.py` +
`processi_service.py`), **view in `apps/amm_software/api/`**. Il pezzo riusabile sta
nell'anello interno, il pezzo esposto sta dove lo si espone.
⭐ È lo stesso taglio del lotto 2: il roster lo legge il core, l'amministrazione lo
**mostra**, il produttore lo **usa**. Se la lettura nascesse dentro `amm_software`, al
lotto 3 servirebbe una seconda copia — e sarebbe la copia che diverge.

⚠️ **Le colonne di decodifica si fanno a JOIN nel backend**, mai con lookup client-side.
⚠️ Il `count` di ogni lista si calcola con una **valutazione indipendente** dalle righe
consegnate (`fetch_paged_with_total`): `len(results)` è un'eco, non un conteggio.
⚠️ `AdminAPIView` su **tutte** le rotte: è `IsAdminZeroERP`, cioè il binding
`SUPER_ADMIN` — le sei viste di presidio nominano tutti gli emittenti e non hanno RLS.

**6.2 — BE: il verbo.**
`POST /api/v1/amm-software/processi/<codice>/identita/` →
`script.fn_crea_utente_tecnico(codice, emittente_codice)`. `Idempotency-Key` obbligatoria.

⭐ **In `amm-software` l'azione di processo dedicata NON serve**, ed è la ragione per cui
non compare fra i prerequisiti DB (§6): `AdminAPIView` è già il gate, e un'azione di
processo sopra un endpoint che solo il super admin raggiunge sarebbe un cancello dentro un
cancello — due sedi per la stessa decisione, che prima o poi dissentono.
⚠️ **D-9 resta**: il sistema non **sceglie** l'emittente, lo riceve da una persona;
segnala il mancante, non lo concede.
⛔ La funzione DB solleva codici registrati: il backend **traduce e passa**, non tiene una
copia dei sei guard.

**6.3 — ⛔ Un difetto già vivo, da chiudere in questo lotto.**
`AmmSoftwareRepository.list_operatori` parte `FROM auth_user au` senza nessun filtro:
i **quattro utenti tecnici** creati dal DB (`run_fatturazione_batch@<EMITTENTE>` e
compagni) compaiono **adesso** nella lista Operatori di Amm. Software, come se fossero
persone — senza reparto, senza risorsa umana, con la ragione sociale «Processo
automatico: …».

⚠️ Nessuno fallisce: la lista mostra **righe vere di una specie sbagliata**. È la classe
di difetto che non dà errore.
⇒ Si escludono le identità con `tecnica = true` (o le si mostra dietro un filtro
esplicito). ⭐ **E si cercano i gemelli**: ogni lista, lookup o conteggio che parte da
`auth_user` o da `anagrafiche.identita_digitali` senza qualificare la specie.
*Un flag nuovo su una tabella vecchia ha tanti consumatori quanti erano quelli della
tabella.*

**6.4 — FE: la lista.**
⛔ **Regola zero: `<ListaConfigurabile codice="amm_processi">`**, mai una
`DataTable` grezza. La configurazione della lista è **dato, non DDL** — una riga in
`ui.lista_definizione` più N in `ui.lista_colonna`, create dall'amministrazione in-app o
con `scripts/gen_seed_lista.py`: **non serve un brief e non si aspetta nessuno.**

* `useListaConfigurabilePage(store, …)` per lo scaffolding (search, export, azioni,
  `@config-loaded`);
* store con `createListaStore` — la lista **non possiede** l'entità che mostra (il ciclo
  di vita è del catalogo DB), quindi non `createCrudStore`. `userScoped: true`;
* `PageActionsBar` con `ReadonlyBadge` nello slot `#suffix`. ⚠️ **Niente
  `useReadonlyMode`**: in `amm-software` non c'è un livello d'area da risolvere — o sei
  super admin e vedi tutto, o non arrivi alla pagina. Aggiungerlo sarebbe un terzo
  cancello che non decide niente;
* azioni di riga nel kebab **`RowActionsMenu`** — ⚠️ lo slot si chiama **`#actions`**, e
  col nome sbagliato la colonna non viene resa **senza errore**;
* **permesso ⇒ nascondi, stato ⇒ `disabled` + `tooltip` col motivo**. ⛔ Il campo del
  motivo si chiama `tooltip`, non `motivo`: un `motivo:` non lo legge nessuno.

**6.5 — FE: il drawer di dettaglio.**
`ProcessoDrawer` con tre schede — **Bersagli** · **Identità** · **Ultimi run** — montate
con `useDrawerTabLista` + `<DrawerTabLista>`: ⛔ «è dentro un drawer» **non è**
un'eccezione alla regola zero. Prop `readonly` + `useInjectReadonly()` con effetto
cumulativo; `FormFooter close-only` (è un drawer di consultazione).

**6.6 — FE: il pannello dei presidi.**
Sei riquadri «questa vista deve restare vuota», col conteggio e le prime righe.
⚠️ **Due specie diverse, e vanno rese diverse a video**: `vw_processi_dominio_senza_difesa`
è un **registro di debito** (deve *calare*), le altre cinque devono essere **zero**.
Renderle uguali insegnerebbe a ignorarle tutte.
⛔ **Niente `useRefreshPeriodico`**: un registro di catalogo non cambia ogni quindici
secondi. Il refresh resta a mano (`PageActionsBar`), come per ogni lista.

**6.7 — i18n.** Namespace `amministrazione.processi.*`, in `it.json` **e** `en.json`. Nessuna
stringa a video fuori da `$t()`. ⚠️ Il vocabolario di classi e canali arriva dal database:
si risolve con ripiego sul codice grezzo (`labelOrCode`), così un valore nuovo compare da
sé invece di lasciare una cella vuota.

---

## 5. Difetti già vivi, trovati leggendo (non misurando)

| # | Difetto | Dove | Lotto |
| --- | --- | --- | --- |
| **D-a** | ✅ **CHIUSO** — erano **12 utenti tecnici in mezzo a 10 persone**, in due liste (`list_operatori` e `get_permessi_riepilogo`). Un filtro solo, presidiato da un test che si dichiara senza materia se i soggetti non ci sono | 6.3 |
| **D-b** | La chiave di dedup della coda **non porta la corsia** — `{job_type}:{competenza}:{scope_key}[:digest]`. Oggi è **latente** (il verbo web usa una corsia sola); diventa vivo con il produttore, dove immediata e differita dello stesso emittente/mese si scarterebbero a vicenda in silenzio. 🔵 **Decisione per Tid**: la corsia entra nella chiave **per tutti** (cambia il dedup anche del pulsante «Fattura competenza», oggi innocuo) o **solo per il produttore** (⛔ due formati per lo stesso `job_type`, cioè la cosa che diverge)? | enqueue `FATTURAZIONE_GIRO` | 3.2 |
| **D-c** | ✅ **CHIUSO** — erano **sei**, non due: quattro venivano da `fn_crea_utente_tecnico` | 0.2 |
| **D-d** | 🔵 **APERTO (DB-2)** — ⚠️ **Asimmetria fra i presidi**: `vw_processi_che_bypassano` **dichiara** il proprio debito in una colonna (`DEBITO_DICHIARATO`); `vw_processi_dominio_senza_emittente` dice «deve restare vuota» ma il seed dei bersagli **si aspetta** la riga di `config.email_outbox`. ⇒ Una vista che non è mai vuota smette di essere letta | DB (§6) | — |

⭐ **D-d è un difetto di contratto, non di dati**: due presidi della stessa famiglia
raccontano il debito in due modi. La simmetria si fa **adesso**, non in una «fase 2»:
o la colonna di stato c'è in entrambe, o non c'è in nessuna.

---

## 6. Prerequisiti DB — che cosa va chiesto al team `dev/db-tid`

⛔ **Nessuna di queste è un'azione del backend**: il BE **attende** i prerequisiti invece
di aggirarli.

✅ **Sono passate al team DB** (2026-09-05):
[brief-db-processi-automatici-residui-be.md](brief-db-processi-automatici-residui-be.md).
⭐ **Quel brief è la sede autorevole**, e la numerazione è la sua: la tabella qui sotto
serve a chi legge il piano per sapere **da cosa dipende**, e non va tenuta in vita per
conto suo. Se le due divergono, vince il brief.

| # | Richiesta | Serve al lotto | Blocca? |
| --- | --- | --- | --- |
| **DB-1** | un tipo di coda per la **chiusura scadenze**, col suo processo registrato. 🔵 Da concordare insieme: **chi accoda** (il job pgAgent di stasera o un command su cron) | 4 | ⛔ sì |
| **DB-2** | che `vw_processi_dominio_senza_emittente` distingua una riga **attesa** da una **nuova** — oggi la vista dice «deve restare vuota» e il seed dei bersagli si aspetta una riga | 6.6 | ⚠️ no, ma peggiora col tempo |
| **DB-3** | **R-7** — colonna emittente su `config.email_outbox`: senza, `send_pending_emails` è di dominio **senza percorso al perimetro** | 1.3 | ⛔ sì, per la parte «un emittente alla volta» |
| **DB-4** | ⚠️ *riscritta*: il **write-guard** su `vendite.fatture_stampa_coda` — ultima riga del livello 2. `listini*` è già a posto | 2 | ⚠️ no |
| **DB-5** | `maintenance.job_run_log.processo_codice` → obbligatorio, **quando** `vw_run_senza_attore` è vuota | dopo 1 | ⛔ oggi impossibile: aspetta **DB-7** |
| **DB-6** | poter rifare l'utente tecnico di un processo ritirato male | 6 | ⚠️ no |
| **DB-7** | 🔴 i nomi di **4 job pgAgent** non esistono nel registro: non si dichiareranno mai | — | ⛔ blocca DB-5 |
| **DB-8** | un codice per «processo non trovato nel registro» | 6 | ⚠️ no, c'è un ripiego dichiarato |

⚠️ **L'azione di processo per «crea utente tecnico» è caduta** con la decisione di mettere
la schermata in `amm-software` (§6.0): `AdminAPIView` è già il gate.

---

## 6-bis. ✅ Il cantiere parallelo su `amm-software` non blocca

Rilevato il 2026-09-05 nel working tree (`piano-be-fe-ui-permessi-operatore.md`,
`MatriceOverride.vue`, `OperatorePermessiTab.vue`, `get_permessi_ereditati`).
**Tid: è fermo, ha solo rifatto la UI per gestirla meglio.** ⇒ Il lotto 6 è partito.

⭐ Le due modifiche convivono senza conflitto: quel cantiere ha **aggiunto** un metodo
al repository, il 6.3 ne ha **filtrato** due query esistenti, e il lotto 6 ha aggiunto
view e rotte nuove accanto alle sue.

⚠️ Una cosa da segnalare e non da sistemare qui: `frontend/src/core/components/MatriceOverride.vue`
è un file **nuovo senza header di licenza**, e `scripts/check_license.py` guarda i file
aggiunti — bloccherà il commit di quel cantiere. Non l'ho toccato perché non è mio.

---

## 6-ter. 🔵 Quello che resta fuori dal backend

| Cosa | Perché non è del backend | Come si vede che è chiuso |
| --- | --- | --- |
| **`DROP ROLE zeroerp_batch_fatturazione`** + ritiro di `scripts/sql/provision_db_role_batch_fatturazione.sql` | i privilegi dei ruoli batch vivono nel **provisioning**, mai in un changeSet | `dbops.vw_processi_che_bypassano` **vuota** (oggi ha ancora la sua riga: il ruolo esiste, non lo usa più nessuno) |
| **Smoke C-9** (`smoke-c9-fatturazione-parte-alta.py`) | ⚠️ osservava da una **seconda connessione** col ruolo di bypass, per due ragioni insieme: vedere tutte le aziende **e** leggere da fuori la propria transazione. La seconda non si sostituisce con la connessione Django. Ora si **dichiara** `SENZA_MATERIA` invece di rompersi con un `KeyError`, ed è nel registro del debito | va riscritto con uno snapshot **per emittente**, iterando il roster |
| **Seed della lista `amm.processi`** | ⭐ **già fatto**: i quattro CSV di `ui.lista_*` sono mirror `runOnChange`, quindi una riga nuova è un **append** — è la via che AGENTS.md indica («non serve un brief e non si aspetta nessuno»). Serve un `migrate` perché il mirror la carichi | la schermata `/amm-software/processi-automatici` disegna la tabella invece di `E_UI_LISTA_NON_TROVATA` |

---

## 7. Le decisioni — ✅ tutte chiuse (Tid, 2026-09-05)

| # | Domanda | Decisione | Dove vive |
| --- | --- | --- | --- |
| 1 | Dove vive la UI dei processi | **`amm-software`** — ⚠️ *rivista lo stesso giorno*: la prima risposta era «`strumenti`, SUPER_ADMIN only», e faceva divergere il posto dal permesso. In `amm-software` coincidono, e c'è già il precedente di `AuditLogView` | §6.0 |
| 2 | `listen_cambio_reparto`, long-running | **run di AVVIO**, chiuso subito. Il battito periodico è un cantiere suo, sopra `job_liveness` | §1.3 |
| 3 | Estrazione `apps/core/services/processi.py` (regola del 2) | **autorizzata** — costanti soltanto, la verità resta a catalogo | §1.2 |
| 4 | Il lotto UI in parallelo o dopo | **in parallelo** ai lotti 1..5 | §4 |
| 5 | La **corsia** nella chiave di dedup (§5 D-b) | **opzione A: per tutti** — un formato solo; sul verbo web il valore è determinato dal perimetro, quindi cambia la forma e non il comportamento | §lotto 3 |
| 6 | Quando si toglie il passepartout `BYPASSRLS` | **subito**: siamo su dati di test, e un fermo non è un problema | §lotto 5 |

⭐ **Nessuna decisione resta aperta lato BE/FE.** Ciò che manca sono i **prerequisiti DB**
del §6, che non sono decisioni: sono lavoro di un altro ramo.

---

## 8. Presidi: dove siamo, misurato

⭐ **Dove c'è un presidio non si va a memoria: si interroga la vista.** Stato al
2026-09-05, dopo i lotti chiusi.

| Presidio / prova | Atteso | Oggi |
| --- | --- | --- |
| `./manage-env.sh genera_error_policies --check` | esce 0 | ✅ allineato |
| suite Django | verde | ✅ **4442 test** |
| `scripts/smoke-baseline.sh` | nessuna regressione | ✅ 3 non-verdi, **tutti noti** |
| `dbops.vw_run_senza_attore` | vuota | 🟡 **5 righe**: 3 sono i job pgAgent di **DB-7** (nomi che il registro non conosce, non si toglieranno mai da soli), 2 si toglieranno alla prossima corsa notturna |
| `dbops.vw_processi_che_bypassano` | vuota | 🟡 **una riga**: il ruolo esiste ancora a database, ma non lo usa più nessuno — manca il `DROP ROLE` (§6-ter) |
| `dbops.vw_processi_dominio_senza_emittente` | vuota | 🟡 **una riga**: `config.email_outbox`, debito dichiarato (DB-3) |
| `dbops.vw_processi_dominio_senza_difesa` | deve **calare** | 🟡 **una riga**: manca il write-guard su `vendite.fatture_stampa_coda` (**DB-4**, riscritta). ⭐ `vendite.listini*` **è uscito**: la policy c'è — l'elenco scritto era invecchiato, la vista no |
| `dbops.vw_processi_dominio_senza_identita` | vuota | ✅ **vuota** |
| `dbops.vw_emittenti_non_serviti` | vuota | ✅ **vuota** |
| `grep -rl "from 'primevue/datatable'" frontend/src --include=*.vue \| wc -l` | non sale | ✅ la schermata nuova monta `<ListaConfigurabile>` |

⚠️ **Nessuno dei 🟡 è un lavoro del backend**: quattro sono richieste al team DB
(DB-2, DB-3, DB-4, DB-7), uno è provisioning, e i due run si chiudono da soli.

---

## 9. Trappole da tenere davanti

* ⛔ **Il ruolo `BYPASSRLS` si toglie per ultimo.** È l'unica cosa dell'ordine che non è
  negoziabile.
* ⚠️ **«Zero righe» non è un allarme.** Togliere il bypass trasforma un danno silenzioso
  in un *niente* silenzioso: molto meglio, ma «non è successo niente» lo nota solo chi si
  aspettava qualcosa. È per questo che `vw_emittenti_non_serviti` esiste — e per questo
  la UI del lotto 6 non è un accessorio.
* ⚠️ **Un flag nuovo su una tabella vecchia**: `identita_digitali.tecnica` ha tanti
  consumatori quanti ne aveva la tabella. Si cercano **tutti** (D-a).
* ⚠️ **`useApiHandler.execute()` solo per response axios**: le chiamate che passano da uno
  store vanno dirette. E i blob non passano da lì.
* ⚠️ **Drawer**: `if (result !== null)`, non `if (result)`.
* ⛔ **Mai committare** senza richiesta esplicita; **mai** applicare migrazioni: l'hook
  `guardrail_no_db_migrate.py` le blocca, e non si disattiva per farle passare.

---

## 10. Riferimenti

* [analisi-db-be-processi-automatici-identita-e-perimetro.md](analisi-db-be-processi-automatici-identita-e-perimetro.md)
  — le decisioni e il **perché**: le tre classi (§2), la porta in scrittura (§4), gli
  utenti tecnici (§6), i limiti dei presidi (§13.1)
* [brief-db-processi-automatici-identita-e-perimetro.md](brief-db-processi-automatici-identita-e-perimetro.md)
  — che cosa il DB ha costruito, e il **registro dei residui** (§12)
* [api.md](../api.md) — base view, envelope, `count` indipendente, tassonomia errori
* [frontend-standards.md](../frontend/frontend-standards.md) — regola zero della lista,
  drawer, readonly, azioni
* [catalogo BB backend](../backend/catalogo-building-block-backend.md) ·
  [catalogo BB frontend](../frontend/catalogo-building-block-frontend.md)
* Codice toccato: `apps/core/services/job_run.py`, `system_context.py`,
  `coda_lavori/{drainer_service,context}.py`,
  `apps/vendite/management/commands/{run_fatturazione_batch,draina_coda_stampa}.py`,
  `apps/core/management/commands/{draina_coda_lavori,send_pending_emails}.py`,
  `apps/anagrafiche/management/commands/{sync_auth_user_active,listen_cambio_reparto}.py`,
  `apps/documenti/services/document_generation_service.py`,
  `apps/amm_software/db/amm_software_repository.py`
* Oggetti DB: `dbops.{processi,processi_bersagli,processi_identita,coda_lavori_tipi,fn_accoda_lavoro}`,
  `maintenance.{job_run_log,fn_run_and_log}`,
  `script.{fn_job_run_start,fn_crea_utente_tecnico,trgfn_guard_emittente_scope}`,
  le sei viste di presidio in `dbops`
