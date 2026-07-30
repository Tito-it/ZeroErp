# Piano BE/FE — satelliti della fattura (indirizzi + piano rate)

> ⚠️ **REVISIONE 2026-07-30 — leggere prima
> [piano-db-satelliti-fattura.md](piano-db-satelliti-fattura.md).**
> La verifica critica sui due brief ha cambiato alcune premesse di questo piano:
>
> | § di qui | Cosa cambia | Rif. |
> |---|---|---|
> | §4 Fase 2 | Il **fallback «transitorio»** del context builder alla vista live **non si scrive**: non siamo in produzione, le 7 fatture di test si cancellano e rigenerano. Era codice che nasceva già da rimuovere | §3.8 |
> | §4 Fase 5 | Cade la **bonifica/esclusione** delle fatture storiche prima di accendere il guard `FATT`, per lo stesso motivo | §3.8 |
> | §4 Fase 4 | Il follow-up temuto sui **«gruppi con termini misti» non serve**: un gruppo fatturabile è **un solo** documento sorgente (o gli oneri di **una** commessa), quindi porta un solo termine per costruzione. D-7 non può spaccarlo. Resta vero che una corsa su tutto il mese può produrre **più fatture** di prima: è lo smoke §3.3 a sorvegliarlo | C-10 |
> | §4 Fase 1 | Il mixin `IndirizziDocumentoRepositoryMixin` va **ripuntato** su `script.fn_resolve_indirizzo_documento`: oggi `find_indirizzo_ruolo_per_tipi` preferisce l'indirizzo generico e **ignora l'istanza** del documento. È una **correzione**, non un refactor estetico | C-14c |
> | **nuovo** | La riforma **D-I** elimina due campi dal `ClienteDrawer` (`tipo_gg_scadenza_ft`, `nr_giorni_scadenza`) con le 4 opzioni `opt_gg_*` e le relative chiavi i18n. Lavoro FE non previsto qui | D-I |
> | **nuovo** | Fase 6 DB aggiunge un verbo al `LottoDrawer` (ritorno a DRAFT / estrazione fattura) e una **lista «estratte»** nel cockpit | D-N-bis |
>
> **Revisione 2026-07-30 (seconda passata) — riallineamento dei perimetri.**
> Verifica richiesta da Tid: *«il DB non si è preso carico di attività che avevamo
> definito BE?»*. Esito: **nessuna sovrapposizione** (nessun doppio lavoro), ma
> **quattro blocchi applicativi vivono solo dentro fasi del piano DB** e uno
> **spostamento di responsabilità** (la catena indirizzi passa in SQL) genera
> lavoro BE che nessuno dei due piani conteneva. Recepiti qui: **§0** (nuova
> fase), **§4-bis** (i blocchi dentro le fasi DB) e **§9** (cosa non facciamo).
> Da qui in avanti **questo** è l'unico elenco del lavoro applicativo: il piano DB
> ci rimanda e non lo duplica.
>
> **Owner:** BE (`dev/backend-tid`)
> **Stato:** in attesa dei prerequisiti DB
> **Prerequisiti (bloccanti):**
> [brief-db-snapshot-indirizzi-fattura.md](brief-db-snapshot-indirizzi-fattura.md) ·
> [brief-db-generazione-scadenze-fattura.md](brief-db-generazione-scadenze-fattura.md)
>
> Questo documento è il **piano di lavoro applicativo**: cosa si tocca, in quale
> ordine, e come si verifica. Le decisioni di dominio e le richieste al team DB
> stanno nei due brief, non qui (regola: modello / brief / piano separati).

---

## 1. Perché serve un piano e non si parte "a sentimento"

Il lavoro applicativo è **cablaggio**, non logica: due handler di pipeline, due
wrapper di repository, un mixin da agganciare, un context builder da ripuntare.
Poche ore di codice. Il valore sta tutto in **tre cose che vanno decise prima**:

1. **l'ordine**, perché una sequenza sbagliata blocca la fatturazione (il guard di
   obbligatorietà `FATT` acceso prima che il popolamento funzioni ferma la pipeline);
2. **cosa consideriamo "fatto"**, perché i satelliti sono esattamente il tipo di
   cosa che «sembra funzionare» e invece è vuota — ce lo siamo già trovati due
   volte (la stampa fattura a trattini, `fn_generate_fatture_righe` mai eseguita);
3. **le regressioni attese**, perché D-7 (termine in chiave di aggregazione)
   **cambia il numero di fatture generate**: va sorvegliato, non scoperto.

## 2. Cosa NON si può anticipare (e va detto)

| Attività | Perché è bloccata |
|---|---|
| Handler + wrapper repository | Devono chiamare funzioni DB di cui non conosciamo ancora nome e firma definitivi |
| Codice degli smoke | Le asserzioni sono già definite (§3), ma il codice tocca le firme reali: scriverlo ora vorrebbe dire riscriverlo |
| Context builder PDF sullo snapshot | Richiede che `fatture_indirizzi` sia popolata, altrimenti la stampa peggiora invece di migliorare |
| Endpoint gestione indirizzi fattura | Dipende da una decisione FE ancora aperta (§7) |

Niente di sostanziale è anticipabile: è cablaggio su superfici che il DB deve
ancora creare. **L'unica cosa utile da fare adesso è questo piano.**

---

## 3. Definizione di «fatto»: gli smoke di accettazione

Sono il **criterio di collaudo del brief DB**, non un complemento del BE: oggi
sarebbero **rossi**, dopo l'apply devono essere verdi. Vanno scritti come primo
atto del lavoro applicativo, prima degli handler, perché descrivono cosa stiamo
cercando di ottenere.

Passano **dalla pipeline reale** (non chiamano le funzioni DB direttamente): così
verificano la catena intera, che è il punto in cui abbiamo già trovato due volte
codice morto con i test verdi.

### 3.1 `smoke-fattura-indirizzi-snapshot.py`

| # | Asserzione |
|---|---|
| 1 | Dopo un giro DRAFT, ogni fattura del lotto ha **almeno la riga `FATT`** in `fatture_indirizzi` |
| 2 | Lo `snapshot` ha lo shape canonico (`intestazione, via, cap, citta, prov, stato, display`) e **non è vuoto** |
| 3 | `origine_indirizzo_id` valorizzato quando l'indirizzo viene dall'anagrafica (tracciabilità della provenienza) |
| 4 | I tipi opzionali (`CON`, `FORNITURA`, `RES`) **non fanno fallire** il giro se assenti |
| 5 | **Ristampa conforme**: il PDF stampa l'indirizzo dello **snapshot**; modificando l'indirizzo in anagrafica e ristampando, il documento **non cambia** ⟵ *l'asserzione che giustifica tutto il lavoro* |
| 6 | Idempotenza: rigenerando il giro non nascono righe duplicate |

### 3.2 `smoke-fattura-scadenze.py`

| # | Asserzione |
|---|---|
| 1 | Dopo un giro EMESSA, ogni fattura ha **almeno una rata** in `fatture_scadenze` |
| 2 | `Σ importo` delle rate **quadra** con `fatture.totale_a_pagare` (base corretta, non `totale_doc`) |
| 3 | Su un piano non divisibile (es. 100,00 / 3) la differenza è **sull'ultima rata** |
| 4 | `numero_rata` progressivo da 1, nessun buco |
| 5 | `meta.modalita_codice` popolato — è il campo che il contesto PDF legge già |
| 6 | Testata: `termine_pagamento_id`, `modalita_pagamento_id`, `termine_pagamento_snapshot` **valorizzati** |
| 7 | Il **PDF stampa il piano rate** (sezione non vuota, date e importi presenti) |
| 8 | Percorso coppia legacy (cliente con giorni): **una sola rata**, data = data fattura + giorni, spostata a fine mese quando previsto |
| 9 | Idempotenza: doppia esecuzione → stesse rate, nessun duplicato |

### 3.3 `smoke-fattura-aggregazione-termini.py` — il presidio di D-7

Lo smoke **più importante**, perché D-7 cambia quante fatture nascono:

| # | Asserzione |
|---|---|
| 1 | Due attività dello stesso BA con **termini diversi** → **due fatture** |
| 2 | Due attività dello stesso BA con **termine uguale** → **una fattura** |
| 3 | Riesecuzione del giro → **nessuna fattura in più** (chiave e lookup allineati) |
| 4 | Due attività con **utility diverse** → due fatture (regressione sul bug chiave/lookup del brief §4.2) |

Modello per tutti e tre: `backend/scripts/tests/smoke-fatturazione-aggregazione-righe.py`
(fixture in transazione + `set_rollback(True)`, nessun dato persistito).

---

## 4. Fasi, in ordine obbligato

### Fase 0 — Ripuntamento del mixin indirizzi (nuova, 2026-07-30)

**Prerequisito della Fase 1**, e la fase più delicata di tutto il piano BE —
perché è l'unica che **cambia il comportamento di cinque flussi già in esercizio**.

Il piano DB (2.0-b) crea `script.fn_resolve_indirizzo_documento`, che assorbe in
SQL la catena di risoluzione oggi implementata nel mixin Python. La scelta è
corretta (era la seconda implementazione della stessa regola, e quella Python ha
un difetto reale), ma la conseguenza è nostra:

| Punto di intervento | Cosa |
|---|---|
| `backend/apps/vendite/db/_indirizzi_repo_mixin.py` | `find_indirizzo_ruolo_per_tipi` + `find_snapshot_soggetto_per_tipi` → **una sola** chiamata a `script.fn_resolve_indirizzo_documento` (SQL fuori dal mixin). Il metodo deve passare l'**istanza utility** del documento |
| `backend/apps/vendite/services/_indirizzi_documento_helpers.py` | `auto_assegna_indirizzo_default` si adegua alla nuova firma. Resta **best-effort** per i fratelli: la politica d'errore non si tocca, si riusa solo la catena (C-14d) |

⚠️ **Perché è delicata.** Il mixin è montato su **preventivi, offerte, ordini, DDT
e contratti**. Oggi la catena ordina `istanza_utility_id NULLS FIRST`, quindi
**preferisce l'indirizzo generico e ignora l'istanza del documento**; dopo il
ripuntamento preferirà quello dell'istanza. Per quei cinque domini **cambia
l'indirizzo che viene proposto**. È la correzione che vogliamo, ma va trattata
come modifica funzionale, non come refactor:

- test di **regressione** sui cinque domini (creazione documento → slot default
  popolato) **prima** e **dopo**, per vedere la differenza invece di scoprirla;
- un caso mirato: soggetto con due istanze e indirizzi `FATT` diversi → ogni
  documento prende quello della **propria** istanza (è l'asserzione che oggi
  fallirebbe);
- verifica che il layer SOGGETTO continui a produrre `origine_indirizzo_id` NULL
  con `origine_soggetto_ruolo_id` valorizzato: è ciò che distingue «derivato
  dall'anagrafica del soggetto» da un una-tantum digitato a mano.

Senza questa fase la Fase 1 gira su una catena diversa da quella dei fratelli, ed
è esattamente il problema che il piano DB voleva chiudere.

### Fase 1 — Task snapshot indirizzi (dopo apply brief indirizzi)

| Punto di intervento | Cosa |
|---|---|
| `backend/apps/vendite/db/vendite_repository.py` | agganciare `IndirizziDocumentoRepositoryMixin` con `_indirizzi_table="vendite.fatture_indirizzi"`, `_indirizzi_fk_documento="fattura_id"`, `_indirizzi_ambito="FATTURE"`, `_indirizzi_documento_table="vendite.fatture"`, `_indirizzi_doc_sr_column=None` (risoluzione via billing account) |
| stesso file | wrapper `run_snapshot_indirizzi_lotto_task(*, lotto_id, batch_size)` |
| `backend/apps/vendite/db/pipeline_repository.py` | voce in `ALLOWED_TASK_FUNCTIONS` |
| `backend/apps/vendite/services/pipeline_step_executor.py` | handler `_handle_snapshot_indirizzi_lotto_task` + entry nel `handler_registry` (modello: `_handle_ricalcola_iva_lotto_task`) |
| `backend/apps/vendite/tests/services/test_pipeline_step_executor.py` | 2 test (esecuzione + skip in dry-run), indice test nel docstring, mappa `ALLOWED_TASK_FUNCTIONS` mockata |

Verifica di fase: smoke §3.1 casi 1-4 e 6 verdi.

### Fase 2 — Ristampa conforme (il motivo per cui esiste la Fase 1)

| Punto di intervento | Cosa |
|---|---|
| `backend/apps/vendite/db/vendite_repository.py:1564-1573` | l'indirizzo cliente **non** più dalla vista live `vw_indirizzi_resolved_ruolo`, ma dallo **snapshot** `fatture_indirizzi` (tipo `FATT`) |
| `backend/apps/vendite/services/fattura_document_context_builder.py:206-208` | consumare il nuovo campo |
| — | modello già fatto: `DdtDocumentContextBuilder` è l'unico context builder che legge gli snapshot |

**Nessun fallback** (rev. 2026-07-30, §9). La prima stesura prevedeva di ricadere
sulla vista live per le fatture senza snapshot, per non rompere la ristampa delle 7
storiche. Non si fa: sono dati di test, si rigenerano. Il lettore legge **solo** lo
snapshot — se manca, manca, ed è giusto che si veda.

Verifica di fase: smoke §3.1 caso 5, il test di conformità (modifico l'anagrafica,
ristampo, il documento non cambia).

### Fase 3 — Task generazione scadenze (dopo apply brief scadenze)

Stessa forma della Fase 1, sui punti di intervento gemelli
(`run_genera_scadenze_lotto_task`, `_handle_genera_scadenze_lotto_task`).

⚠️ **Attenzione all'ordine dentro lo step**: il task va **dopo**
`ricalcola_iva_lotto` (prima i totali non esistono). L'ordine è nel seed DB, ma i
test dell'executor devono asserirlo, non fidarsi.

Verifica di fase: smoke §3.2 completo.

### Fase 4 — Regressioni di D-7 (contestuale alla Fase 3)

Il termine in chiave cambia **quante** fatture nascono. Da sorvegliare:

| Cosa | Azione |
|---|---|
| Test e smoke esistenti che contano le fatture di un lotto | rileggere le aspettative: `smoke-fatturazione-aggregazione-righe.py` oggi assume che le attività dello stesso BA finiscano in una fattura |
| Cockpit / dashboard competenza | i **gruppi fatturabili** e i contatori riflettono l'aggregazione: verificare che il perimetro mostrato resti coerente con le fatture prodotte |
| Emissione mirata per gruppi | ✅ **nessun follow-up** (§9): un gruppo fatturabile è un solo documento sorgente — o gli oneri di una sola commessa — quindi porta un solo termine per costruzione, e D-7 non può spaccarlo |

Verifica di fase: smoke §3.3 + suite completa vendite.

### Fase 5 — Accensione del guard `FATT` obbligatorio (coordinata col DB)

Il guard sta nel brief DB, ma la **sequenza è condivisa**: si accende **solo dopo**
che la Fase 1 gira, altrimenti blocca la pipeline.

Le 7 fatture storiche senza snapshot **non si bonificano** (§9): se inciampano nel
guard si cancellano e si rifà un giro. L'unica verifica che serve è che il task
della Fase 1 popoli davvero le fatture **nuove** — cioè lo smoke §3.1, non un
censimento dello storico.

### Fase 6 — Frontend

| Cosa | Stato |
|---|---|
| Piano rate nel drawer | ✅ **nessun lavoro**: `ScadenzeSintesi` e il campo «Prossima rata» esistono e mostrano `—` finché le rate non arrivano. Dopo la Fase 3 si popolano da soli |
| Campi «Modalità di pagamento» e «Termine» | ✅ già nel drawer, oggi sempre vuoti perché la testata è NULL. Dopo la Fase 3 vanno **verificati a video** (è il primo momento in cui mostrano un valore) |
| Sezione indirizzi nel drawer fattura | ⏸️ decisione aperta, §7 |

---

## 4-bis. Lavoro applicativo dentro le fasi del piano DB (owner: BE)

Queste voci **compaiono solo nel piano DB**, dentro fasi marcate come sue. Il
rischio non è il doppio lavoro — nessuna è anche altrove — ma l'**omissione**: il
team DB non tocca i `.vue` né `types.py`, e noi non guardiamo una fase marcata DB.
Sono elencate qui perché **l'owner è il BE**; la fase DB resta il loro innesco.

| Innesco (piano DB) | Cosa tocca a noi | Quando |
|---|---|---|
| **3a.7** — riforma condizioni di pagamento (D-I) | `ClienteDrawer.vue`: via i due campi `tipo_gg_scadenza_ft` / `nr_giorni_scadenza`, le **4 opzioni `opt_gg_*`** e le loro chiavi i18n (it+en). Lato BE: `fn_update_cliente`, `clienti_repository`, `clienti_service`, `views_clienti`, `error_policies` | **Contestuale** al DROP delle colonne (3a.5): appena cadono, il drawer mostrerebbe campi inesistenti |
| **6.6** — eliminazione del flag `esclusa` (D-M) | **filtro API** e **`types.py`** (il resto è DB) | Con la Fase 6 DB |
| **6.7** — ritorno a DRAFT / estrazione (D-N-bis) | Verbo nel `LottoDrawer` con conferma esplicita di **cosa si perde**, e **lista «estratte»** nel cockpit | Dopo 6.0-6.5 DB |
| **D-L** — rinomina funzioni di reset | **Solo 4 righe** (vedi sotto) | Contestuale alla rinomina |

### D-L: il minimo indispensabile, misurato

Se il DB rinomina (`fn_reset_lotto_draft` → `fn_annulla_lotto_da_draft`,
`fn_reset_lotto_fattura_draft` → `fn_elimina_fattura_draft_da_lotto`), **queste
quattro righe devono seguire**, altrimenti il reset lotto muore con
`42883 function does not exist`:

| File:riga | Cosa |
|---|---|
| `backend/apps/vendite/db/pipeline_repository.py:174` | valore in `ALLOWED_TASK_FUNCTIONS` |
| `backend/apps/vendite/db/pipeline_repository.py:1985` | `FROM vendite.fn_reset_lotto_draft(%s)` |
| `backend/apps/vendite/db/pipeline_repository.py:2006` | `FROM vendite.fn_reset_lotto_fattura_draft(%s, %s)` |
| `backend/apps/vendite/tests/services/test_pipeline_step_executor.py:64` | mappa `ALLOWED_TASK_FUNCTIONS` mockata |

**Tutto il resto NON si tocca** (decisione Tid 2026-07-30): gli entrypoint Python
omonimi (`pipeline_service.fn_reset_lotto_draft` e gemello), i loro import in
`services/__init__.py` e `api/views.py`, le due view e i `@patch` dei test sono
**nomi Python**, invisibili al database. Rinominarli sarebbe allineamento
estetico su ~12 punti.

> **Debito accettato consapevolmente**: resta un disallineamento nominale — la
> funzione DB si chiamerà «annulla», l'entrypoint Python continuerà a chiamarsi
> «reset». Si scioglie quando qualcuno passerà da lì per altri motivi.
>
> 💡 **Osservazione per il team DB**: se l'obiettivo è ridurre al minimo il lavoro
> applicativo, **la rinomina è la parte rinunciabile di D-L**. Il valore di quella
> decisione sta nei punti 2 e 3 — l'asimmetria di perimetro e soprattutto
> l'**over-free del `lock_batch_id`** (C-22: resettare *una* fattura libera le
> attività di *tutto* il lotto), che è un bug e va corretto comunque. Rinunciando
> alla sola rinomina, il lavoro BE di D-L scende a **zero** e il disallineamento
> nominale non nasce.

## 5. Verifiche trasversali (a ogni fase)

- `./manage-test.sh apps.vendite.tests apps.core.tests` verde;
- `python3 scripts/check_i18n_keys.py` pulito (se si aggiungono etichette FE);
- build Vite + eslint (solo se si tocca il FE);
- `scripts/pgtap-baseline.sh vendite` — confronto con la baseline, per non
  attribuirsi rossi preesistenti né mascherare regressioni;
- gli smoke §3 **rieseguiti**, non solo la prima volta: sono il presidio contro il
  ritorno del difetto.

## 6. Rischi noti

| Rischio | Mitigazione |
|---|---|
| Guard `FATT` acceso troppo presto → pipeline bloccata | Fase 5 esplicita, con conteggio preventivo |
| Ristampa delle 7 fatture storiche senza snapshot | **rischio accettato** (§9): dati di test, si rigenerano. Nessun fallback in codice |
| D-7 frammenta le fatture più del previsto | smoke §3.3 + revisione delle aspettative sui test esistenti (Fase 4) |
| `fatture_indirizzi` letta nel dettaglio API senza RLS | la tabella **non ha policy**: se la esponiamo, la protezione resta l'ordine «testata prima → 404» già presidiato da `test_note_non_contate_se_testata_none` e gemelli. Valutare l'estensione delle policy satelliti |
| Storicizzazione gonfiata dalle rigenerazioni | `DELETE+INSERT` su `fatture_scadenze` scrive in `storico.fatture_scadenze_id` a ogni giro: atteso, da tenere presente nei conteggi |

## 7. Decisioni FE ancora aperte

1. **L'operatore deve poter correggere un indirizzo su fattura DRAFT?**
   - **Sì** → serve l'endpoint (factory `build_indirizzi_documento_views` già
     pronta) + `stati_modificabili = {"DRAFT"}` + un lettore di stato
     (`get_stato_codice` **assente** su `VenditeRepository`, da scrivere) + montare
     `DocumentoIndirizziSection` nel drawer.
   - **No** → la tabella è scritta solo dalla pipeline; nel drawer gli indirizzi si
     mostrano in sola lettura (o non si mostrano affatto).
2. **Gli indirizzi vanno esposti nel dettaglio fattura?** Se sì, il payload cresce
   di una chiave e vale l'avvertenza RLS del §6.
3. **Badge documenti** nella barra azioni del drawer: il payload ha già
   `contatori` come dict proprio per questo — se serve, si aggiunge un contatore
   senza cambiare la shape.

---

## 8. Stima

| Fase | Effort |
|---|---|
| §3 — smoke di accettazione (3 file) | mezza giornata (è la parte che richiede pensiero) |
| **0 — ripuntamento mixin + regressione 5 domini** | **~mezza giornata**: il codice è poco, la verifica sui cinque flussi è il lavoro |
| 1 — task indirizzi | ~2 ore |
| 2 — ristampa conforme | ~2 ore |
| 3 — task scadenze | ~2 ore |
| 4 — regressioni D-7 | variabile, dipende da quanto emerge |
| 6 — FE | 0 se la decisione §7.1 è «No» |
| **4-bis — 3a.7** (drawer cliente + BE condizioni) | ~mezza giornata |
| **4-bis — 6.6 / 6.7** (flag `esclusa`, verbo lotto + lista estratte) | con la Fase 6 DB |
| **4-bis — D-L** | 4 righe, oppure **zero** se il DB rinuncia alla rinomina |

Il grosso del tempo non è scrivere il cablaggio: è **verificare che i satelliti
esistano davvero** e che il documento stampato dica la verità.

---

## 9. Cosa NON facciamo, e perché

Deciso con Tid il 2026-07-30. Serve scritto, perché sono tutte cose che un
lettore diligente cercherebbe e non troverebbe.

| Cosa | Perché non si fa |
|---|---|
| **Rigenerare le 7 fatture storiche** dopo l'accensione dello snapshot | Sono **dati di test**. Non vale un passo di piano: se una vecchia fattura stampa un indirizzo letto live o inciampa nel guard `FATT`, si cancella e si rifà un giro. Nessun codice, nessuna procedura, nessuna bonifica |
| **Fallback del context builder** alla vista live per le fatture senza snapshot | Stessa ragione (piano DB §3.8): sarebbe codice che nasce già da rimuovere |
| **Bonifica/esclusione** delle fatture storiche prima del guard `FATT` | Idem |
| **Rinominare gli entrypoint Python** di D-L (~12 punti) | Sono nomi interni, invisibili al DB. Restano le sole **4 righe** che nominano la funzione SQL (§4-bis) |
| **Follow-up «gruppi con termini misti»** | Non serve: un gruppo fatturabile è **un solo** documento sorgente (o gli oneri di **una** commessa), quindi porta un solo termine per costruzione — D-7 non può spaccarlo (piano DB C-10) |

> **Criterio generale che ne emerge, e che vale oltre questo cantiere:** non siamo
> in produzione. Davanti a un dato di test sbagliato la risposta è **rifare il
> dato**, non scrivere codice che lo tollera. Ogni riga scritta per accomodare
> sette fatture di prova sarebbe debito con la data di scadenza già stampata sopra.

---

## 10. Un'offerta al piano DB: gli smoke coprono anche la 3a

L'autocritica del piano DB (W-2) nota che **le fasi DB non hanno un criterio di
«fatto» end-to-end**: hanno i pgTAP, che verificano le funzioni ma non la catena —
e la 3a è la fase con più superficie e nessun collaudo.

Gli smoke di §3 passano dalla **pipeline reale**, quindi possono chiudere quel
buco senza scrivere niente di nuovo: dopo la riforma delle condizioni di pagamento,
`smoke-fattura-scadenze.py` asserisce già che la testata porta
`termine_pagamento_id` e `modalita_pagamento_id` e che le rate quadrano — cioè che
la catena **risolve** attraverso il catalogo riformato. Se la 3a ha rotto qualcosa,
lo smoke lo dice.

Va aggiunta una sola asserzione: **nessun cliente resta senza condizioni** dopo la
migrazione (3a.4) — un conteggio, non un test complicato.
