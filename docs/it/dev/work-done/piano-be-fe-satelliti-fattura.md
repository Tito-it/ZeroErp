# Piano BE/FE — satelliti della fattura (indirizzi + piano rate)

> 🟢 **CANTIERE CHIUSO — 2026-08-22.** Le tre decisioni di prodotto del §7 sono
> state prese da Tid: **tutte e tre «no, non adesso»**. Non c'è codice in sospeso
> e non resta nulla da decidere: il documento è archiviato.
>
> | §7 | Decisione (2026-08-22) | Perché |
> | --- | --- | --- |
> | **7.1** — indirizzo correggibile su fattura DRAFT | ❌ **no** | `fn_snapshot_indirizzi_fattura` riscrive la riga a ogni passata (`ON CONFLICT … DO UPDATE`): una correzione a mano verrebbe **sovrascritta dal rilancio dello step DRAFT**, che è esattamente la via di correzione prevista da D-Q. Sarebbe un campo che torna indietro da solo. Si corregge in anagrafica e si rilancia |
> | **7.2** — lista indirizzi per tipo nel dettaglio | ❌ **no, non adesso** | Con D-P la fattura è del BA **padre**, dove `FATT` è in pratica l'unica riga che esiste, e il suo display è già esposto in `cliente_indirizzo`. Una lista aggiungerebbe una chiave al payload per mostrare una riga sola. Si riapre quando arriverà il **sotto-dettaglio utilities**, che comunque non può vivere in `fatture_indirizzi` (D-P punto c) |
> | **7.3** — badge documenti nella barra azioni | ❌ **no, non qui** | Non è di questo cantiere: appartiene all'archivio documenti/stampe. Il dict `contatori` regge già il contatore nuovo senza cambiare shape, quindi non c'è debito di predisposizione |
>
> ℹ️ **Il rischio RLS del §6 è rientrato da solo**: `vendite.fatture_indirizzi` e
> `fatture_scadenze` hanno oggi RLS attiva con 2 policy ciascuna (chiuso da
> `brief-db-rls-satelliti-fattura-portale.md`). La riga del §6 resta com'è scritta
> perché fotografa la situazione di allora.
>
> ---
>
> 🟡 **STATO AL 2026-08-04 — lavoro tecnico FINITO, restano tre decisioni di prodotto.**
>
> Fasi 0-5 chiuse fra il 31-07 e il 02-08. Il 04-08 sono state chiuse anche le
> quattro voci del §4-bis che dipendevano dalle fasi DB:
>
> | §4-bis | Esito |
> | --- | --- |
> | **6.6** — flag `esclusa` fuori da filtro API e `types.py` | ✅ fatto (era **rotto**: la lista fatture del lotto interrogava una colonna droppata) |
> | **6.7** — ritorno a DRAFT / eliminazione per-fattura | ✅ fatto. ⚠️ **La «lista estratte» non serve più**: con RD-7 togliere una fattura vuol dire cancellarla, quindi non c'è nulla da elencare — quella riga è superata, non rinviata |
> | **D-L** — rinomina funzioni di reset | ✅ allineata su entrambi gli strati (`fn_annulla_lotto_da_draft`, `fn_elimina_fattura_da_lotto`); URL e `task_code` invariati come previsto |
> | **D-Q** — «non avanzare» ≠ «non ripartire» | ✅ implementato: il blocco per criticità non impedisce più il rilancio dello stesso step |
>
> **Fase 6 FE:** piano rate e campi pagamento non richiedevano lavoro. La
> **validazione a video di «Termine» e «Modalità di pagamento» è OK** (Tid,
> 2026-08-04) — era il primo momento utile, perché serviva una fattura nuova.
>
> ⏸️ **Restano aperte solo le tre decisioni del §7**, che sono di prodotto e non
> di implementazione: indirizzo correggibile su fattura DRAFT, lista degli
> indirizzi per tipo nel dettaglio, badge documenti nella barra azioni. Finché
> non sono prese, questo piano resta qui: non c'è codice in sospeso.
>
> ---

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
> | **nuovo** | Fase 6 DB aggiunge un verbo al `LottoDrawer` (ritorno a DRAFT / eliminazione fattura). ⚠️ La **lista «estratte»** prevista qui **non si farà**: RD-7 (04-08) ha deciso che togliere una fattura vuol dire cancellarla | D-N-bis |
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
> **Stato (2026-08-01, sera): cantiere indirizzi+intestazione COMPLETO.** Fasi
> 0, 1, **2** e **5** ✅ (guard uscita DRAFT col criterio allargato +
> `E_FATTURA_NON_EMETTIBILE_INCOMPLETA` registrato 409) · 4-bis: D-Q ✅, DB 2.3
> ✅, 3a.7 ✅ · **giro pipeline reale ✅** (lotti 603/604, prime 3 fatture
> interamente conformi — §3.1 lezione 2).
> **Fase 4 ✅ CHIUSA (2026-08-01)** dalla chiusura della Fase 3b DB: nessuna
> regressione, **smoke §3.3 scritto e verde** (6/6, con prova di mutazione),
> ricaduta **D-S** (utility in colonna) corretta, e la nostra segnalazione sui
> clienti senza termine **chiusa da D-J** (fallback `TP_1RATA` nella catena).
> **Fase 3 (task scadenze) ✅ CHIUSA (2026-08-02)**. Il DB aveva già consegnato la
> sua Fase 4 la sera del 01-08 (`20260801-08/-09`, PR #1119) e noi non ce ne
> eravamo accorti. Task registrato, handler cablato, guard d'ordine scritto,
> **binding provato con chiamata reale** (i 3452 verdi mockano il repository e non
> provano una riga di SQL); poi il DB ha **armato entrambe le corsie** — corsia 2
> inclusa, che era vuota — e lo **smoke §3.2 è verde (10 casi, con prova di
> mutazione)**. Il cantiere satelliti non ha più fasi aperte lato nostro.
> ✅ **D-L.1 e D-L.2** chiuse su entrambi gli strati.
> ⚠️ Il `brief-db-generazione-scadenze-fattura.md` **non va riscritto**: è stato
> riscritto dal DB il 02-08 ed è ora il **contratto verso il BE**; il
> design-of-record dello stato resta il piano DB §9.
> ✅ **D-K (Fase 4b) è ATTERRATO** (`20260802-24`, applicato il 2026-08-02 alle
> 22:31 — il nostro commit delle 23:05 non lo sapeva ancora): `numera_fatture`
> ora può dire di no. Ricaduta nostra chiusa: **574
> `E_FATTURA_NON_NUMERABILE_INCOERENTE` registrato** in `error_policies.py`.
> **Prerequisiti:**
> [brief-db-snapshot-indirizzi-fattura.md](brief-db-snapshot-indirizzi-fattura.md) ·
> [piano-db-satelliti-fattura.md](piano-db-satelliti-fattura.md) §Fase 4
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

> **Stato 2026-07-31 (notte): 8/8 verde, caso 8 ACCESO con la Fase 2** — il
> ciclo D-Q completo (errore → marcatura → correzione → rilancio → ritiro
> segnalazioni) più la ristampa conforme vera: contesto ancorato ai **valori
> congelati** (display della riga `FATT` + `emittente_snapshot`, non solo
> confrontato con sé stesso — due letture live sarebbero uguali fra loro anche
> senza snapshot), poi deriva anagrafica → contesto **identico**
> (`identici_post_deriva=True`). Dal rinominarsi del wrapper mostra anche
> `intestazioni_scritte` (1 alla correzione, 0 al terzo giro: l'intestazione è
> idempotente come le righe).
>
> ⚠️ **Due lezioni di fixture, pagate sul campo.**
>
> 1. **Non si cancellano righe di `anagrafiche.indirizzi`.** La fase «errore»
>    toglieva al cliente il tipo `FATT` con una DELETE; il 2026-07-31 ha smesso
>    di funzionare perché un DDT aveva **congelato quell'indirizzo** come
>    `origine_indirizzo_id`, e la FK ha fatto morire lo smoke *nella fixture*,
>    non in un'asserzione. Ora le righe si **ri-puntano a un tipo di
>    parcheggio** — ammesso al ruolo ma fuori dall'ambito `FATTURE` — così la
>    riga sopravvive alla FK e la catena non trova comunque `FATT`. Due
>    finezze uscite dalla review critica, entrambe misurate sul DB: (a) la
>    selezione del parcheggio rispecchia il guard della matrice **per intero**
>    (`attivo` E finestra `valido_dal/valido_al` — solo-attivo passerebbe la
>    selezione e morirebbe sul guard); (b) **un solo tipo basta per tutte le
>    righe**: le unique di `anagrafiche.indirizzi` sono parziali — `(sr, tipo)`
>    con istanza NULL, `(sr, istanza, tipo)` altrimenti — quindi la generica è
>    al più una e le altre non collidono mai fra loro. Vale per qualunque smoke
>    futuro: più snapshot congeliamo, meno i dati anagrafici sono cancellabili,
>    anche dentro una transazione che fa rollback.
> 2. **Passa dal wrapper, non dallo step** (rilievo del team DB, §10.7 del brief
>    intestazione). Finché lo smoke chiama `run_snapshot_indirizzi_lotto_task`
>    direttamente, dimostra la catena wrapper → funzione DB → D-Q → contesto di
>    stampa, **non** che la pipeline invochi quel wrapper.
>    ✅ **CHIUSO il 2026-08-01 con un giro reale** (`run_fatturazione_batch
>    --modalita differita`, canale di sistema): lotti **603/604**
>    (`LTF-0000679/680`), `snapshot_indirizzi_lotto` **COMPLETATO nei
>    task_run di entrambi** — cioè seed → executor → handler → wrapper
>    rinominato, la catena intera. Le 3 fatture prodotte (834-836) sono le
>    **prime interamente conformi**: `emittente_snapshot` + `cliente_snapshot`
>    + 2 righe indirizzo ciascuna, `prov` pulita (`AV`/`MC`/`CB`), sede
>    emittente valorizzata dal layer SOGGETTO — e hanno **attraversato il
>    guard di uscita DRAFT**, che è la controprova positiva dell'asserzione
>    2b. Lo smoke resta com'è: la copertura pipeline la dà il giro, non una
>    fixture che simula lo step.
>    📎 *Coda del giro (2026-08-01)*: le fatture reali hanno smascherato un
>    **falso positivo** nel caso 5 di `smoke-fatturazione-render-stampa.py` —
>    segnalava *qualunque* trattino in una riga con *qualche* campo
>    valorizzato, e le righe **kit padre** del percorso pull (sconto NULL →
>    trattino legittimo) lo facevano scattare a vuoto; mascherato fin lì da
>    fixture con tutti i campi pieni. Rilevatore reso **posizionale** (mappa
>    campo→colonna letta dai `<th>`, fail-loud se gli header cambiano) e
>    auto-verifica riancorata al contratto vero — un `any('-')` generico
>    sarebbe diventato banalmente verde per sempre. Ora verde su fattura 835.

### 3.2 `smoke-fattura-scadenze.py` ✅ **SCRITTO E VERDE (2026-08-02)** — 10 casi, con prova di mutazione

| # | Asserzione | Stato |
| --- | --- | --- |
| 1 | Dopo un giro EMESSA, ogni fattura ha **almeno una rata** in `fatture_scadenze` | ✅ caso 1 |
| 2 | `Σ importo` delle rate **quadra** con `fatture.totale_a_pagare` (base corretta, non `totale_doc`) | ✅ caso 2, **condizionato a base > 0** |
| 3 | Su un piano non divisibile la differenza è **sull'ultima rata** | ✅ caso 3, riscritto — vedi sotto |
| 4 | `numero_rata` progressivo da 1, nessun buco | ✅ caso 4 |
| 5 | `meta.modalita_codice` popolato — è il campo che il contesto PDF legge già | ✅ caso 5 |
| 6 | Testata: `termine_pagamento_id`, `modalita_pagamento_id`, `termine_pagamento_snapshot` **valorizzati** | ✅ caso 6 |
| 7 | Il **PDF stampa il piano rate** (sezione non vuota, date e importi presenti) | ✅ **coperto altrove**: `smoke-fatturazione-render-stampa.py` **caso 9** — vedi sotto |
| 8 | ~~Percorso coppia legacy (cliente con giorni)~~ | ⛔ **decaduto**: D-I ha eliminato le colonne. Verificato sul DB — `clienti.tipo_gg_scadenza_ft`, `nr_giorni_scadenza`, `fatture.giorni_pagamento`, `fine_mese` **non esistono più** |
| 9 | Idempotenza: doppia esecuzione → stesse rate, nessun duplicato | ✅ caso 7, sul **piano intero** |

In più, non previsti qui e aggiunti perché il contratto li richiede: **caso 0**
(controprova a monte: la catena risolve termine e modalità dalla commessa — se è
rosso lì il difetto è in 3b, non nelle scadenze), **caso 8** (base zero → zero rate
senza fallimento, D-D) e **caso 9** (D-F: fattura oltre EMESSA in `skipped_rows` e
non in `failed_rows`, i due contatori distinti).

✅ **L'asserzione 7 è coperta, ma non qui: è il caso 9 di
`smoke-fatturazione-render-stampa.py`** (2026-08-02, ora **9/9 verde**). Il piano rate
a video è un fatto di **rendering**, e la macchina per verificarlo — template
pubblicato, contesto, render Jinja `StrictUndefined`, PDF reale — vive già lì:
duplicarla nel nostro smoke avrebbe creato due posti che sanno come si stampa una
fattura. Tre cose emerse scrivendolo:

- **è l'unico caso di quel file che SCRIVE**, e non è aggirabile: nessuna fattura del
  sistema ha un piano rate, quindi un caso «trova una fattura con rate» sarebbe uno
  **SKIP perenne** — una copertura che sembra esserci e non c'è. Le rate si generano
  in `transaction.atomic()` e si fa rollback; l'intestazione del file lo dichiara;
- **il controllo è integrato, non aggiunto**: la sezione è `{% if scadenze %}`, quindi
  si asserisce **assente prima** della generazione e **presente dopo**, coi valori del
  context nelle celle. Una sola asserzione di presenza sarebbe passata anche su un
  template che stampa quattro trattini;
- 🔎 **al primo giro la colonna «Modalità» stampava `-`** — legittimo, perché quella
  fattura ha `modalita_pagamento_id` NULL, ma significava che il caso era **cieco
  proprio sulla colonna più esposta** al difetto storico. Il fixture ora valorizza
  anche la modalità e l'asserzione copre tutte e quattro le colonne. Reso:
  `1 | 31-08-2026 | MP01 | 100,65 EUR`.

✅ **Prova di mutazione**: togliendo `importo` dal context passato al template — il
difetto storico esatto, chiave sbagliata → `.get()` None → trattino — il caso 9
diventa rosso e gli altri restano verdi.

⚠️ **L'esempio «100,00 / 3» non è riproducibile** e l'asserzione è stata riscritta.
Il catalogo riformato **non ha termini a 3 rate** (massimo 2: `TP_30_60_2R`,
`TP_30_60_EOM_2R`), quindi il caso si esercita con una base non divisibile costruita
sul numero di rate reale. E soprattutto: con **due** rate la formulazione «le prime
uguali fra loro, l'ultima diversa» è **vacua** — un insieme di un elemento è sempre
omogeneo — e non distingue «resto sull'ultima» da «resto sulla prima». Il caso
confronta quindi i **valori attesi rata per rata**, replicando la formula del brief.

📐 **Come cade il resto, misurato** (domanda di Tid, 2026-08-02). Le prime *n−1* rate
valgono `round(base / n)` col metodo del termine; l'**ultima è ciò che resta**. Non ha
una direzione fissa — dipende da come arrotonda la divisione:

| Base | Rate | |
| --- | --- | --- |
| 10,03 su 2 | 5,02 · **5,01** | 5,015 arrotonda per **eccesso** → l'ultima riceve **meno** |
| 100,00 su 3 | 33,33 · 33,33 · **33,34** | 33,3333 arrotonda per **difetto** → l'ultima riceve **più** |

L'invariante è uno solo: **Σ = `totale_a_pagare`, esatta al centesimo**. Con 2 rate
`base/2` finisce sempre per 0 o 5 al terzo decimale, quindi HALF_UP arrotonda sempre
per eccesso e la prima rata è sempre ≥ dell'ultima: il verso opposto si osserva solo
da 3 rate in su. Misurato sulla funzione reale con un termine temporaneo a 3 rate,
creato e annullato dentro la transazione.

### 3.3 `smoke-fattura-aggregazione-termini.py` — il presidio di D-7 ✅ **SCRITTO E VERDE (2026-08-01)**

> **6 casi verdi** sul percorso reale (`FattureRigheService.generate_fatture_righe`,
> il servizio del task di pipeline). Il fixture passa dalla **via reale di
> D-R**: il termine si mette sulla **commessa** e la catena
> `fn_resolve_termini_pagamento` lo raccoglie — così un solo smoke esercita
> D-R, la catena, la chiave e il lookup. Un fixture che avesse forzato
> `fatture.termine_pagamento_id` avrebbe testato sé stesso.
>
> **Come è costruito:** tre commesse sullo **stesso** cliente/utility/emittente
> — C1 e C3 con `TP_30G_1R`, C2 con `TP_90G_1R` — e un'attività ciascuna.
> Attesa: **2 fatture, non 3**. È la forma che dimostra le due metà insieme:
> termini diversi separano, e due commesse **diverse** con lo stesso termine
> **confluiscono** (§3.3 asserzioni 1 e 2 in un colpo).
>
> ✅ **Prova di mutazione**: rieseguito con i tre termini uguali nasce **1
> fattura invece di 2** e i casi 1, 2 e 5 diventano rossi — il file morde dove
> dice di mordere.
>
> ⚠️ **Un caso del §3.3 non è esercitabile qui, e sta scritto nel file**: «utility
> diverse → due fatture». L'utility in chiave viene dal BA dell'**attività**,
> quindi servirebbero due BA distinti — e allora a separare sarebbe anche il
> BA: l'asserzione non discriminerebbe. È presidiato dove può esserlo davvero,
> il pgTAP `test-chiave-fattura-tre-specchi-v1` (3b.5). Qui resta il **caso 6**,
> che copre la metà applicativa del difetto: che la testata **porti** la propria
> `utility_id` invece di dedurla (D-S).

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

### Fase 0 — Ripuntamento del mixin indirizzi ✅ **FATTA (2026-07-31)**

> **Sbloccata** dal push del team DB fino al punto 2 del piano DB: verificato sul
> DB vivo che esistono `script.fn_resolve_indirizzo_documento`,
> `script.fn_snapshot_indirizzo_soggetto` e
> `vendite.trgfn_fattura_satellite_guard_congelamento`, mentre
> `fn_snapshot_indirizzi_fattura`/`_lotto` (2.1/2.2) **non** ci sono ancora —
> quindi la Fase 0 è arrivata **prima** della 2.1, come doveva.
>
> **Cosa è stato fatto**
>
> | File | Modifica |
> |---|---|
> | `db/_indirizzi_repo_mixin.py` | nuovo `resolve_indirizzo_documento(*, soggetto_ruolo_id, istanza_utility_id, tipo_codice)` che delega alla funzione DB; **rimossi** `find_indirizzo_ruolo_per_tipi` e `find_snapshot_soggetto_per_tipi` (la catena non è più duplicata in Python); nuovo `get_ancora_indirizzi_documento` → coppia `(soggetto_ruolo, istanza)` in **una** query, con `get_soggetto_ruolo_documento` che ora vi delega (un solo SQL da mantenere); nuovo attributo `_indirizzi_doc_istanza_column` |
> | `services/_indirizzi_documento_helpers.py` | `auto_assegna_indirizzo_default` passa l'**istanza del documento** e usa le origini restituite dal DB. Resta **best-effort**: politica d'errore invariata per i 5 domini interattivi |
> | `db/{preventivi,offerte,contratti}_repository.py` | `_indirizzi_doc_istanza_column = "istanza_utility_id"` — i soli **precontrattuali** hanno l'istanza in testata; ordini/DDT/fatture la ricavano dal BA (invariante 1:1 della guida istanze) |
> | `tests/services/test_indirizzi_documento_helpers.py` | **nuovo, 9 test.** Questo percorso girava su 5 domini **senza un solo test**: è il motivo per cui il difetto dell'istanza è vissuto inosservato |
> | `scripts/tests/smoke-indirizzi-documento-catena.py` | **nuovo, 9 casi** sul DB reale (3, 3b, 3c: precedenza istanza, senza istanza, cross-istanza) |
>
> **Esito delle verifiche:** 2062 test verdi · smoke catena **9/9** · smoke
> render-stampa e contatore-note verdi (nessuna regressione) · rollback pulito ·
> **validazione in-app di Tid (2026-07-31)**: la creazione documento continua a
> popolare lo slot indirizzo come prima — chiuso l'unico residuo (il tratto
> `crea_<documento>` → helper dei 5 service, che la fase non toccava).
> **Fase 0 chiusa senza riserve.**
>
> **La prova che il difetto è chiuso** è il caso 3 dello smoke: con due indirizzi
> dello stesso tipo — uno generico e uno per istanza — ora vince **quello
> dell'istanza** (col vecchio `NULLS FIRST` vinceva il generico), e un documento
> **senza** istanza continua a prendere il generico (caso 3b).
>
> **Due scoperte da riportare al team DB** (§4-ter).

**Era la fase più delicata di tutto il piano BE**, perché è l'unica che
**cambia il comportamento di cinque flussi già in esercizio**.

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

### Fase 1 — Task snapshot indirizzi ✅ **FATTA (2026-07-31)** — con la metà applicativa di D-Q

> Sbloccata dal push DB fino a 2.4 (2.0-2.2 applicate, 2.3 parte inerte
> seminata, pgTAP verdi). Realizzato in un passaggio unico il cablaggio del
> task E i **tre punti della nota D-Q** (§4-bis):
>
> | Pezzo | Dove |
> |---|---|
> | Wrapper `run_snapshot_indirizzi_lotto_task` (5 contatori; **6 dal 2026-07-31 sera**: la funzione DB è diventata `fn_snapshot_fattura_lotto` e aggiunge `intestazioni_scritte` — vedi la riga «DB 2.3» del §4-bis) + voce in `ALLOWED_TASK_FUNCTIONS` + **`disattiva_segnalazioni_lotto_be`** | `db/pipeline_repository.py` |
> | Handler `_handle_snapshot_indirizzi_lotto_task` + **`TaskEsitoParziale`**: `failed_rows > 0` → task_run **ERRORE senza sollevare** (D-Q p.3 — con COMPLETATO il rilancio darebbe SKIP; con un raise il rollback cancellerebbe il lavoro delle fatture sane) | `services/pipeline_step_executor.py` |
> | **Gate D-Q p.1**: il blocco critico vale per l'**avanzamento**; il **rilancio dello stesso step è ammesso**. A fine step con fatture in errore il lotto va in ERRORE (abilita il rerun); il **ritiro bandiere BE** (p.2, errori runner + fotografie esito derivate) avviene a inizio step dentro la transazione — rollback-safe = «solo al successo» | `services/pipeline_runner.py` |
> | Driver `until_done`: si ferma con `BLOCCATO_CRITICITA` + errore strutturato su step con fatture in errore; **prosegue** dopo un rilancio riuscito (flusso «correggo → premo una volta → finisce») | `services/pipeline_runner.py` |
>
> **Verifiche:** 2073 test verdi (**9 nuovi**: 4 executor, 5 runner) · smoke
> §3.1 **attivo e verde** (`smoke-fattura-indirizzi-snapshot.py`: ciclo D-Q
> reale — errore → C log + ponte ERRORE → correzione → rilancio → **ritiro
> segnalazioni** → idempotenza; caso ristampa in SKIP fino alla Fase 2) ·
> 4 smoke esistenti senza regressioni.
>
> **Palla al DB**: armamento 2.3 parte 2 (il nodo nei `processi` DRAFT di
> entrambe le corsie) → poi 2.5 (guard `FATT`). I tre prerequisiti BE citati
> nel loro piano sono chiusi.

(Contenuto originale della fase, realizzato come sopra:)

| Punto di intervento | Cosa |
|---|---|
| `backend/apps/vendite/db/vendite_repository.py` | agganciare `IndirizziDocumentoRepositoryMixin` con `_indirizzi_table="vendite.fatture_indirizzi"`, `_indirizzi_fk_documento="fattura_id"`, `_indirizzi_ambito="FATTURE"`, `_indirizzi_documento_table="vendite.fatture"`, `_indirizzi_doc_sr_column=None` (risoluzione via billing account) |
| stesso file | wrapper `run_snapshot_indirizzi_lotto_task(*, lotto_id, batch_size)` |
| `backend/apps/vendite/db/pipeline_repository.py` | voce in `ALLOWED_TASK_FUNCTIONS` |
| `backend/apps/vendite/services/pipeline_step_executor.py` | handler `_handle_snapshot_indirizzi_lotto_task` + entry nel `handler_registry` (modello: `_handle_ricalcola_iva_lotto_task`) |
| `backend/apps/vendite/tests/services/test_pipeline_step_executor.py` | 2 test (esecuzione + skip in dry-run), indice test nel docstring, mappa `ALLOWED_TASK_FUNCTIONS` mockata |

Verifica di fase: smoke §3.1 casi 1-4 e 6 verdi.

### Fase 2 — Ristampa conforme ✅ **FATTA (2026-07-31, sera)**

> **Realizzata la sera stessa dello sblocco.** Perimetro effettivo — piu'
> piccolo del previsto, perche' le chiavi piatte della testata sono il
> contratto condiviso di drawer FE e template PDF, e derivarle **dentro la
> SQL** dagli snapshot lascia builder e FE intatti per costruzione:
>
> | File | Cosa |
> |---|---|
> | `db/vendite_repository.py` (`get_fattura_testata`) | intestazioni delle due parti derivate da `emittente_snapshot`/`cliente_snapshot` (`->>`), indirizzo cliente dalla riga `FATT` di `fatture_indirizzi`; **rimosse** le due subquery su `vw_indirizzi_resolved_ruolo` (con entrambi i difetti §10.3) e le JOIN su `vw_soggetti_ruoli_dettaglio`/`emittenti_fiscali`; esposti anche gli snapshot integrali (shape non contrattuale); ritirata la costante `TIPO_INDIRIZZO_SEDE_LEGALE` |
> | `services/fattura_document_context_builder.py` | **solo commenti**: shape e codice invariati, la sorgente e' cambiata sotto le stesse chiavi |
> | `scripts/tests/smoke-fattura-indirizzi-snapshot.py` | asserzione 8 **accesa**: contesto ancorato ai valori congelati (non solo a se' stesso) + deriva anagrafica → contesto identico |
> | `docs/it/backend/vendite/manual/api_fattura_dettaglio.md` | «Dipendenze DB» riscritte (cadute le 3 JOIN) + nota di provenienza: chiavi invariate, sorgente = snapshot, NULL senza fallback, avvertenza D-P sul BA padre |
>
> **Verifiche:** smoke §3.1 **8/8 verde** (caso 8: `identici_post_deriva=True`)
> · `smoke-fatturazione-render-stampa.py` verde (PDF reale 18KB dal contesto
> nuovo) · suite 2487 verdi. Le fatture **pre**-snapshot stampano intestazione
> vuota: voluto (§9, dati di test — si rigenerano).
>
> **Review critica post-scrittura (2026-08-01)**: tre assunzioni verificate sul
> DB e non sulla fiducia — la subquery scalare `FATT` senza `LIMIT 1` non può
> esplodere (`uq_tipi_indirizzi_codice_interno` × `uq_fatture_indirizzi_uno_per_tipo_`,
> e a vincoli rotti l'errore sarebbe rumoroso, che è il fallimento giusto); il
> confronto `ctx_dopo == ctx_prima` non può flappare (i tre lettori del builder
> hanno ORDER BY deterministici); `jsonb_out` è NULL-preserving (pre-snapshot →
> `null`, non `{}`). Un solo fix: la doc manuale qui sopra, ultimo consumatore
> della vecchia provenienza. **Asimmetria nota e voluta**: la lista fatture del
> `LottoDrawer` mostra la ragione sociale **live**, il dettaglio/PDF quella
> **congelata** — la lista è una vista operativa, il documento è il documento.

(Testo originale della fase:)

> ⚠️ **Estesa il 2026-07-31 — leggere
> [brief-db-snapshot-intestazione-fattura.md](brief-db-snapshot-intestazione-fattura.md)
> prima di scrivere questa fase.** Misurando per rispondere a una domanda di Tid
> («per l'emittente possiamo usare lo storico degli indirizzi?» — no, §2 del
> brief) è emerso che il perimetro qui sotto è **incompleto**: congela
> l'indirizzo del cliente e lascia live la sua ragione sociale e P.IVA, più
> l'intera intestazione dell'emittente. Risultato: incoerenza dentro lo stesso
> blocco stampato.
>
> Due fatti che cambiano la fase:
>
> - la **sede legale dell'emittente non è mai stata stampata**: la subquery di
>   `vendite_repository.py:1600-1605` filtra `tipo_indirizzo_codice = 'SEDELEG'`
>   ma la vista espone in quella colonna il `codice` (`SEDE-LEG`) — 0 match
>   sempre. Il tipo `FATT` funziona solo perché i due codici coincidono per caso;
> - le fatture in tabella sono **8** (conteggio con bypass RLS: senza GUC
>   operatore `vendite.fatture` appare vuota, fail-closed), tutte di test e già
>   dichiarate sacrificabili dal §9 — quindi niente da migrare, ma il numero
>   cresce a ogni giro di prova: la forma definitiva costa oggi meno di
>   qualsiasi giorno futuro.
>
> **Conseguenza operativa:** questa fase si scrive **una volta sola**, sulla
> forma decisa nel brief (snapshot intestazione in testata + indirizzo cliente da
> `fatture_indirizzi`), invece di ripuntare il context builder due volte.
>
> ---
>
> ### ✅ Sbloccata la sera del 2026-07-31 — il DB ha accolto e applicato
>
> Risposta del team DB nel §10 del brief, e **tutto già a DB**: colonne
> `fatture.emittente_snapshot` / `cliente_snapshot` con guard di congelamento
> (`20260731-05`), `fn_snapshot_intestazione_fattura` (`-06`), wrapper
> `fn_snapshot_fattura_lotto` che chiama le due sorelle (`-07`), più
> l'armamento del nodo nelle corsie DRAFT. **Nulla resta da attendere: la Fase 2
> è nostra e basta scriverla.**
>
> **Correzione di merito da recepire (§10.3 del brief): i difetti sono due,
> non uno.** Oltre al confronto `codice`/`codice_interno`, la subquery legge
> `vw_indirizzi_resolved_ruolo`, che per costruzione contiene il **solo layer
> RUOLO** (`WHERE scope = 'RUOLO'`) — e il ruolo `EF` non ha **alcun**
> indirizzo: la sede dell'emittente sta sul layer SOGGETTO. È il secondo a
> spiegare la sede vuota, e vale **identico sulla riga del cliente**. Leggere lo
> snapshot li chiude entrambi in un colpo, perché lo snapshot è composto da
> `fn_resolve_indirizzo_documento`, che i due layer li attraversa già.
>
> **Lo shape contro cui scrivere `_shape_emittente` / `_shape_cliente`**:
> `denominazione`, `codice_fiscale`, `id_fiscale`, `regime_fiscale_rf`, `sede`,
> `rea`, `capitale_sociale`, `forma_giuridica`, `socio_unico`, `liquidazione`;
> lato cliente `codice_sdi`, `pec_fatturazione`, `destinatario_fe`,
> `billing_account_id`/`ba_codice`. Regola dichiarata dal DB: di ogni entità
> referenziata si congela il **valore** e l'id sta **accanto**, non al posto suo
> — un id da solo non è uno snapshot. ⚠️ Lo shape è **interno e non
> contrattuale** finché il builder XML FatturaPA non esiste: aggiungere o
> rinominare chiavi resta lecito senza migrazioni.
>
> ⚠️ **Normalizzare le chiavi mancanti**: il DB **omette** le chiavi nulle e il
> template gira con `StrictUndefined`. Il builder deve proiettare sull'elenco
> completo e ordinato, come fa già `DdtDocumentContextBuilder` con
> `SNAPSHOT_KEYS_ORDERED`.
>
> **Il `billing_account_id` dello snapshot cliente è il BA *padre*** (D-P), non
> il conto di chi ha consumato: non va letto come «il conto del cliente».

| Punto di intervento | Cosa |
|---|---|
| `backend/apps/vendite/db/vendite_repository.py` (`get_fattura_testata`, ~1576-1650) | le **quattro** letture live → snapshot: `emittente_snapshot` e `cliente_snapshot` dalla testata, indirizzo cliente dalla riga `FATT` di `fatture_indirizzi`. **Spariscono** le due subquery su `vw_indirizzi_resolved_ruolo` (e con loro entrambi i difetti del §10.3 del brief) e le JOIN su `vw_soggetti_ruoli_dettaglio` per i dati che ora vivono negli snapshot |
| `backend/apps/vendite/services/fattura_document_context_builder.py` (`_shape_cliente`, ~199-211) | `_shape_cliente` legge lo snapshot + nuovo `_shape_emittente`; proiezione su chiavi complete e ordinate (StrictUndefined) |
| — | modello già fatto: `DdtDocumentContextBuilder` è l'unico context builder che legge gli snapshot |

**Nessun fallback** (rev. 2026-07-30, §9). La prima stesura prevedeva di ricadere
sulla vista live per le fatture senza snapshot, per non rompere la ristampa delle 7
storiche. Non si fa: sono dati di test, si rigenerano. Il lettore legge **solo** lo
snapshot — se manca, manca, ed è giusto che si veda.

Verifica di fase: smoke §3.1 caso 5, il test di conformità (modifico l'anagrafica,
ristampo, il documento non cambia).

### Fase 3 — Task generazione scadenze ✅ **CHIUSA (2026-08-02)** — armata dal DB, smoke verde

> **Cos'è cambiato.** Il DB **aveva già consegnato la sua Fase 4** la sera del
> 2026-08-01 (`20260801-08` e `-09`, merge PR #1119): `fn_genera_scadenze_fattura`
> e `fn_genera_scadenze_lotto` sono applicate e verdi (pgTAP 14/14 e 11/11), e il
> seed **inerte** è a posto (registry **20**, impl **20**, `task_policy` **19-23**,
> queste ultime comprese le tre che D-C assegna alla corsia GIORNALIERO).
> Il brief `brief-db-generazione-scadenze-fattura.md` **non va più riscritto**: il
> design-of-record è il piano DB, con la formula a ramo unico post-D-E e i tre casi
> di D-D già implementati.

Stessa forma della Fase 1, sui punti di intervento gemelli.

| # | Cosa | Dove |
| --- | --- | --- |
| 3.1 | `genera_scadenze_lotto` → `vendite.fn_genera_scadenze_lotto` in `ALLOWED_TASK_FUNCTIONS` | `db/pipeline_repository.py` |
| 3.2 | `run_genera_scadenze_lotto_task` — sei contatori; ⚠️ `skipped_rows` (oltre EMESSA, D-F) e `skipped_errore_rows` (critico altrui, D-Q) restano **separati**: per il cockpit «chiusa» e «rotta» sono l'opposto | `db/pipeline_repository.py` |
| 3.3 | `_handle_genera_scadenze_lotto_task` + registry `genera_scadenze_lotto_default`; `failed_rows > 0` → `TaskEsitoParziale` (task_run **ERRORE senza raise**, D-Q p.3) | `services/pipeline_step_executor.py` |
| 3.4 | `E_SCADENZE_LOTTO_PARZIALE` + `E_INDIRIZZO_FATTURA_MANCANTE` registrati (422) | `core/services/error_policies.py` |
| 3.5 | Guard d'ordine `_TASK_ORDER_DEPENDENCIES` + 8 test | `services/pipeline_step_executor.py` |

**Il codice d'errore del parziale non è uno dei quattro `E_SCADENZE_*` di dominio.**
A differenza degli indirizzi — dove `E_INDIRIZZO_FATTURA_MANCANTE` è la causa
dominante reale — qui le cause per-fattura sono quattro (termine mancante, base non
pronta, termine inconciliabile, fattura bloccata) e **nessuna domina**: sceglierne
una farebbe raccontare al cockpit una diagnosi che il wrapper non ha misurato. Il
messaggio originale del DB resta sui log fattura, che è dove si guarda.

⚠️ **L'ordine dentro lo step non è più solo una riga di seed.** Il task va **dopo**
`ricalcola_iva_lotto` (la base di ripartizione è `totale_a_pagare`, che prima non
esiste). Ora c'è un **guard nell'executor** (`_TASK_ORDER_DEPENDENCIES`) che rifiuta
la sequenza invertita **prima che il primo task scriva**: senza, il generatore
solleverebbe `E_SCADENZE_BASE_NON_PRONTA` su *ogni* fattura, e un giro interamente
rosso sembrerebbe un difetto dei dati invece di una riga di configurazione girata.
Due esclusioni volute, entrambe casi legittimi: se il predecessore **non è in questo
step** non si fallisce (può vivere in uno step precedente), e in **rollback** non si
verifica (la catena di annullamento va a ritroso).

**Verifica.** 3452 test verdi (+8). ⚠️ **Ma mockano il repository e non provano una
riga di SQL** ([[feedback_rinomina_db_binding_mockato]]): il binding è stato provato
con **chiamata reale** in transazione con rollback, attraverso `system_process_context`
— senza il canale di sistema la RLS restituisce zero lotti, e uno zero fail-closed
somiglia a un dato ([[feedback_rls_query_contesto_sistema]]). Esiti misurati:

| Caso | Esito |
| --- | --- |
| lotto inesistente | sei contatori a zero — il nome risolve (una fn assente darebbe `42883`) |
| `lotto_id = 0` | guard DB: «p_lotto_id obbligatorio e > 0» |
| lotti **278/245** (DEFINITIVA) | `skipped_rows = 1`, `failed = 0` → **D-F verificato dal vivo** |
| lotti **603/604/489** (EMESSA) | `failed_rows` = tutte, con `E_SCADENZE_TERMINE_MANCANTE` |

🟢 **L'ultima riga NON è un difetto, ed è stato verificato invece che assunto.** Le 4
fatture esistenti (632, 834-836) sono state create il **31/07 alle 15:19 e 23:09**;
la catena che scrive il termine in testata è entrata con la Fase 3b il **01/08 fra le
12:32 e le 13:39** (`20260801-04/05/06`), e la `fn_get_or_create_fattura_header` viva
oggi scrive sia `termine_pagamento_id` sia `modalita_pagamento_id`. Sono fatture
**anteriori di ~13 ore** al meccanismo: il rifiuto è il comportamento corretto per una
testata senza termine. **Conseguenza operativa: lo smoke §3.2 va girato su fatture
nuove**, prodotte da un giro post-3b — sulle quattro esistenti sarà rosso per sempre,
e sarebbe un rosso che non dice niente.

✅ **Armamento fatto dal DB (2026-08-02)**, verificato sul DB vivo e non sulla parola:

```text
2 GIORNALIERO EMESSA -> genera_fondi_source_lotto > applica_fondi_lotto > ricalcola_iva_lotto > genera_scadenze_lotto
3 MASSIVO     EMESSA -> genera_fondi_source_lotto > applica_fondi_lotto > ricalcola_iva_lotto > genera_scadenze_lotto
```

La corsia 2, che era `processi = []`, è stata riempita (D-C). Entrambe rispettano
`_TASK_ORDER_DEPENDENCIES`. Il DB ha aggiunto un pgTAP che presidia lo stesso
invariante **sul seed**: i due non sono un doppione — quello impedisce alla
configurazione sbagliata di nascere, il nostro impedisce a una configurazione
sbagliata di scrivere. Vanno tenuti entrambi.

✅ **Smoke §3.2 scritto e verde (2026-08-02)**: `smoke-fattura-scadenze.py`, **10 casi**,
con **prova di mutazione eseguita**. Il fixture mette il termine sulla **commessa**
(D-R) e lascia che la catena lo porti in testata passando dalla chiave: forzare
`fatture.termine_pagamento_id` avrebbe testato il fixture. Poi chiama gli stessi tre
metodi repository dello step EMESSA nell'ordine reale. Copre, oltre alle sei
asserzioni del §3.2: idempotenza sul **piano intero** (non sul conteggio — un
generatore che sbaglia le date le riscriverebbe diverse mantenendo lo stesso numero
di righe), base zero → zero rate senza fallimento (D-D), e D-F con i **due `skipped`
tenuti distinti**.

Tre correzioni di rotta accolte dal team DB, tutte già dentro il file:

1. **Si gira su fatture nuove** — il fixture crea la propria. Sulle 4 preesistenti il
   570 è il comportamento corretto, e uno smoke che le includesse sarebbe rosso per
   sempre di un rosso che non dice niente.
2. **La quadratura è condizionata a `totale_a_pagare > 0`** — stesa su tutto il lotto
   fallirebbe sulla prima fattura coperta da acconti, e fallirebbe *correttamente*:
   il modo peggiore di accorgersene. Il caso a base zero ha un test proprio.
3. ✅ **D-K (Fase 4b) NON è più un heads-up: è atterrato** (`20260802-24` applicato
   alle 22:31 del 2026-08-02; il nostro commit delle 23:05 lo dava ancora come
   futuro — segnalato dal team DB, e avevano ragione). `fn_assign_numero_fattura`
   rifiuta con **574 `E_FATTURA_NON_NUMERABILE_INCOERENTE`** un documento che violi
   una di **sei** condizioni, e le riporta **tutte insieme** nel payload invece che
   una per giro. Verificano una catena continua senza anelli scoperti:
   `riepiloghi IVA →(5) totale_doc →(6) totale_a_pagare →(3/4) rate`.
   Tre ricadute, e la previsione ha retto solo in parte:
   - lo smoke §3.2 **non cambia**, come previsto: asseriva già l'invariante che il
     guard presidia, quindi ne era il presidio anticipato;
   - ✅ **574 registrato** in `error_policies.py` (422). Era seedato in
     `config.messaggi_errore` dalla Fase 1.3 ma non qui, quindi il fallback lo
     mostrava come «Errore di validazione». ⚠️ Non confonderlo con il **571**
     `E_SCADENZE_BASE_NON_PRONTA`: il 571 è dello step EMESSA e dice «i totali non
     ci sono ancora», il 574 è dello step DEFINITIVA e dice «il documento non
     merita un numero fiscale». Stesso sintomo a monte, momenti e rimedi diversi;
   - **le fixture che numerano**: lato nostro nessuna si rompe — i test unitari
     mockano il repository e non attraversano il guard, che è a DB. L'unica cosa
     che numera contro il DB reale è `smoke-c9-fatturazione-parte-alta.py`.
     🔎 **Girato il 2026-08-02: verde, ma il verde NON copre D-K** — `numerati=0`,
     `lotti=0`, perché la competenza 2026-06 è già interamente lavorata e il giro
     non produce lotti nuovi. Il guard non è mai stato invocato: è un verde a
     vuoto sul punto che interessa, e va detto invece di contarlo come prova.
   > 📌 **La prova end-to-end di D-K manca ancora.** Il modo economico e
   > deterministico per averla è aggiungere allo smoke §3.2 — che una fattura
   > completa la costruisce già — due casi in rollback: la fattura con le rate
   > **è numerabile**, e la stessa fattura **senza** rate viene rifiutata con 574.
   > Esercita il guard sul percorso vero senza consumare numeri fiscali sul DB
   > condiviso, che è ciò che rende C-9 inadatto a presidiarlo.

⚠️ Due cose misurate scrivendolo, che valgono più della riga di codice che le ha
prodotte:

- il `100,00 / 3` scritto nel §3.2 **non è riproducibile**: il catalogo riformato non
  ha termini a 3 rate (massimo 2). La proprietà che quell'esempio voleva presidiare è
  però esercitata con una base non divisibile costruita sul numero di rate reale — e
  l'asserzione confronta i **valori attesi** rata per rata, non «le prime uguali e
  l'ultima diversa», che con due rate è **vacuo** e non distinguerebbe «resto
  sull'ultima» da «resto sulla prima»;
- i `jsonb` letti da cursore raw arrivano **stringa** (psycopg 3 non li decodifica
  fuori dall'ORM): serve `coerce_jsonb_dict`. È lo stesso difetto già pagato dal
  worker della coda.

Verifica di fase: ✅ completa.

### Fase 4 — Regressioni di D-7 ✅ **CHIUSA (2026-08-01)**

> **Cos'è cambiato.** La **Fase 3b del piano DB è CHIUSA** (`20260801-01..07`):
> il termine è in chiave, `fn_build_fattura_key` e il lookup di
> `fn_get_or_create_fattura_header` si specchiano, l'ambito arrotondamenti
> segue la chiave. Quindi questa fase non ha aspettato la Fase 3: le regressioni
> di D-7 erano osservabili subito. ℹ️ La riga «la Fase 3 resta l'unica ferma»
> che stava qui è **decaduta** il 2026-08-02, quando si è scoperto che il DB
> aveva già consegnato la sua Fase 4 la sera prima.
>
> **Prima verifica fatta (2026-08-01): nessuna regressione.**
> `smoke-fatturazione-aggregazione-righe.py` **verde, 10/10** — e la riga
> «da rileggere» qui sotto si chiude con una precisazione che vale la pena
> scrivere: quello smoke aggrega **righe dentro una fattura**, non fatture
> dentro un lotto. D-7 cambia *quante fatture nascono*, non *come si
> raggruppano le righe*: due presidi diversi, e il timore del piano era mal
> indirizzato.
>
> **Due ricadute DB arrivate con 3b, una già chiusa:**
>
> | Decisione | Ricaduta BE | Stato |
> |---|---|---|
> | **D-S** — `vendite.fatture.utility_id` diventa una **colonna vera** (la chiave prende l'utility dal BA dell'**attività**, la testata porta il BA **padre**: due derivazioni che divergono al primo BA gerarchico) | `get_fattura_testata` deduceva l'utility da `ba.utility_id` — **stesso difetto latente** che D-S ha tolto dal ricalcolo totali | ✅ **corretto**: la testata legge `f.utility_id` e la JOIN su `config.utilities` segue la colonna. Verificato su fattura 835: `utility_id=5 → BASE / Servizio Base` |
> | **D-L.1** — rinomina `fn_reset_lotto_draft` → `fn_annulla_lotto_da_draft`, `fn_reset_lotto_fattura_draft` → **`fn_elimina_fattura_da_lotto_draft`** (⚠️ *seconda passata del DB il 2026-08-02*: prima era `fn_elimina_fattura_draft_da_lotto` — «draft» qualifica il **lotto**, non la fattura, perché la funzione accetta anche fatture EMESSE non fiscali. Riallineato lo stesso giorno) | allineamento Python su entrambi gli strati | ✅ **FATTA (2026-08-01, riallineata il 2026-08-02)**, subito dopo l'apply DB — le vecchie funzioni erano già state droppate, quindi il task di rollback `reset_lotto_draft` era **rotto**. Rinominati: le 2 chiamate SQL, i 2 metodi del repository, i 2 metodi del service, i 2 entrypoint `fn_*`, i 2 TypedDict (`AnnullaLottoDaDraftResult`, `EliminaFatturaDraftDaLottoResult`), `__init__`, `views`, 5 file di test. ⚠️ **Restano invariati per progetto**, e il perché è nei commenti: il `task_code` `reset_lotto_draft` (seed CSV dei `rollback`), la chiave handler `reset_lotto_draft_default`, i due `post_permission` (seed `config.azioni_processo`) e gli URL `reset-draft/` (contratto API + FE). Verifica: 2075 test verdi **e** chiamata reale in transazione — gli unit test mockano il repository e non avrebbero visto un nome SQL sbagliato |
>
> **E una risposta che chiude una nostra segnalazione.** Il timore sui
> **19 clienti su 21 senza `termine_pagamento_id`** («zero rate in silenzio»)
> era **già deciso** da **D-J**: la colonna resta nullable e la catena
> `fn_resolve_termini_pagamento` scende al default **`TP_1RATA`**, quindi quei
> clienti producono **una rata alla data fattura**, non zero. Il fallback vive
> **nella catena, non nel generatore** (che «legge e non risolve», 4.1 DB) —
> altrimenti rinascerebbe il secondo risolutore che C-13 esiste per
> eliminare. Nessuna azione BE: la voce si chiude.

Il termine in chiave cambia **quante** fatture nascono. Da sorvegliare:

| Cosa | Azione |
|---|---|
| Test e smoke esistenti che contano le fatture di un lotto | rileggere le aspettative: `smoke-fatturazione-aggregazione-righe.py` oggi assume che le attività dello stesso BA finiscano in una fattura |
| Cockpit / dashboard competenza | i **gruppi fatturabili** e i contatori riflettono l'aggregazione: verificare che il perimetro mostrato resti coerente con le fatture prodotte |
| Emissione mirata per gruppi | ✅ **nessun follow-up** (§9): un gruppo fatturabile è un solo documento sorgente — o gli oneri di una sola commessa — quindi porta un solo termine per costruzione, e D-7 non può spaccarlo |

Verifica di fase: smoke §3.3 + suite completa vendite.
✅ **Entrambe fatte il 2026-08-01**: `smoke-fattura-aggregazione-termini.py`
**6/6 verde** con prova di mutazione (§3.3), `smoke-fatturazione-aggregazione-righe.py`
10/10 senza regressioni, suite **2075 verdi**. **Fase 4 chiusa** per quanto
riguarda D-7 lato aggregazione; resta da guardare il **cockpit/dashboard
competenza** (riga 2 della tabella) quando ci saranno dati con termini misti:
oggi ogni commessa ha un solo termine e il perimetro mostrato non può divergere.

### Fase 5 — Accensione del guard `FATT` obbligatorio ✅ **FATTA (2026-07-31, notte)**

> **Acceso dal DB col criterio GIÀ allargato** (I.4, brief intestazione §10.9,
> changeSet `20260731-11/-12`, pgTAP plan(11) verde):
> `trgfn_fatture_guard_uscita_draft` presidia l'**uscita dalla bozza** — per
> QUALUNQUE percorso, UPDATE diretto compreso, senza bypass GUC — e pretende
> il documento completo: indirizzi obbligatori dell'ambito `FATTURE` **e**
> intestazione congelata (`emittente_snapshot`/`cliente_snapshot`). La
> sequenza chiesta da questa fase è stata rispettata: armamento 2.3 parte 2
> confermato su giro reale **prima** dell'accensione.
>
> **Metà BE, fatta contestualmente:**
>
> | Cosa | Dove |
> |---|---|
> | ⚠️ Il codice errore **non è quello annunciato** dal brief indirizzi §5.3 (`E_INDIRIZZO_DOC_OBBLIGATORIO`, scritto quando il criterio era il solo indirizzo): il guard solleva **`E_FATTURA_NON_EMETTIBILE_INCOMPLETA`** (id 575). Registrato con **409** (stato della risorsa, non input malformato — famiglia `_DUPLICATO`/`_IN_ESECUZIONE`; `_INCOMPLETA` non era nella tassonomia api.md, decisione nostra come richiesto). UN codice solo: chi lo riceve fa la stessa cosa in entrambi i casi — rieseguire lo step DRAFT; la diagnosi sta nel messaggio e nel payload (`indirizzi_mancanti`/`intestazione_mancante`) | `error_policies.py` |
> | Asserzione **2b** nello smoke: nella fase «errore» la fattura è incompleta per costruzione — UPDATE diretto verso EMESSA respinto col codice giusto (savepoint dedicato, la transazione dello smoke sopravvive). È l'asserzione 14 del brief (§6) dal lato applicativo | `smoke-fattura-indirizzi-snapshot.py` |
> | Censimento percorsi: **nessuno** script BE o smoke muove lo stato fattura con UPDATE diretto (verificato su `backend/`) — l'avvertenza §10.9 punto 2 per noi è a vuoto | — |
>
> **Verifiche:** smoke §3.1 **9 casi verdi** (2b incluso: il messaggio DB
> compone davvero le due metà della diagnosi) · suite 2487 verdi.
>
> Resta vera l'ultima riga di questa fase com'era scritta: la verifica che
> conta è che il task popoli le fatture **nuove** — ✅ data dal **giro reale
> del 2026-08-01** (lotti 603/604: 3 fatture complete attraverso il guard,
> dettaglio in §3.1 lezione 2).

Le fatture storiche senza snapshot **non si bonificano** (§9): se inciampano nel
guard si cancellano e si rifà un giro.

### Fase 6 — Frontend

| Cosa | Stato |
|---|---|
| Piano rate nel drawer | ✅ **nessun lavoro**: `ScadenzeSintesi` e il campo «Prossima rata» esistono e mostrano `—` finché le rate non arrivano. Con la Fase 3 chiusa (2026-08-02) si popolano da soli |
| Campi «Modalità di pagamento» e «Termine» | ✅ **validati a video da Tid (2026-08-04)**. Erano già nel drawer, ma prima della Fase 3 non avevano niente da mostrare; sulle fatture preesistenti la testata resta NULL, quindi la prova richiedeva una fattura **nuova** |
| Sezione indirizzi nel drawer fattura | ⏸️ decisione aperta, §7 |

---

## 4-bis. Lavoro applicativo dentro le fasi del piano DB (owner: BE)

Queste voci **compaiono solo nel piano DB**, dentro fasi marcate come sue. Il
rischio non è il doppio lavoro — nessuna è anche altrove — ma l'**omissione**: il
team DB non tocca i `.vue` né `types.py`, e noi non guardiamo una fase marcata DB.
Sono elencate qui perché **l'owner è il BE**; la fase DB resta il loro innesco.

| Innesco (piano DB) | Cosa tocca a noi | Quando |
|---|---|---|
| **3a.7** — riforma condizioni di pagamento (D-I) | ✅ **FATTA (2026-07-31, PR #1100), ANTICIPATA rispetto al DROP** — decisione presa con Tid e team DB: le colonne legacy non avevano lettori a valle e il `NOT NULL` ha un `DEFAULT`, quindi anticipare **elimina** l'accoppiamento invece di gestirlo — 3a.5/3a.6 diventano DROP pure, senza deploy FE da sincronizzare. Fatto: `ClienteDrawer.vue` (via i 2 campi + `tipoGgOptions`), 6 chiavi i18n it+en, `clienti_repository` (2 whitelist + SELECT), `clienti_service`, `views_clienti`, `test_clienti_repository`. Verifiche: 1068 test verdi, `check_i18n_keys` pulito, eslint + build Vite ok. **Residui CHIUSI la sera stessa**: `fn_update_cliente` riscritta dal DB (`20260731-08`, con 3a.5) e `E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI` **ritirato** da `error_policies.py` — il trigger non esiste più, la policy era codice morto; resta il gemello fornitori, che il suo trigger ce l'ha ancora. **3a.7 completamente chiusa** | ~~Contestuale al DROP~~ → anticipata |
| **6.6** — eliminazione del flag `esclusa` (D-M) | ✅ **FATTO (2026-08-04)**: filtro API, parametro OpenAPI, `types.py`, service, client FE e i due test dedicati (rimossi: il filtro non esiste più, non è stato «adattato»). ⚠️ Era **rotto adesso** — la lista fatture del lotto interrogava una colonna droppata dal DB | Con la Fase 6 DB |
| **6.7** — ritorno a DRAFT / eliminazione per-fattura (D-N-bis) | ✅ **CHIUSO (2026-08-04)**. Il verbo «Riporta in lavorazione» è nel drawer **e** nel kebab della lista lotti, con conferma che dice cosa si perde; l'eliminazione per-fattura funziona ora anche su lotto **EMESSA** (il DB ha allargato il perimetro a pre-fiscale, chiudendo il vicolo cieco che il fix del 01-08 aveva solo tamponato lato FE). ⚠️ **La «lista estratte» NON si fa**: RD-7 ha stabilito che togliere una fattura vuol dire **cancellarla**, quindi non esiste un archivio di estratte da elencare — la riga è superata dalla decisione, non rinviata | ~~Dopo 6.0-6.5 DB~~ → fatto |
| **D-L** — rinomina funzioni di reset | ✅ **FATTO**: `fn_annulla_lotto_da_draft` (02-08) e `fn_elimina_fattura_da_lotto` (04-08) allineate su repository, service, view e test. URL (`reset-draft/`), permesso e `task_code` **non** seguono la rinomina: sono contratti verso client e catalogo | Contestuale alla rinomina |
| **D-Q** — fattura in errore, lotto non avanza ma si rilancia (decisione Tid 2026-07-31) | ✅ **FATTO**: il blocco per criticità distingue ora l'avanzamento dal **rilancio dello stesso step** (`blocks_next_step and not is_rilancio_stesso_step`), e il ritiro delle segnalazioni di lotto scritte dal BE avviene dentro la transazione dello step | **Prima** dell'accensione del task in pipeline (DB 2.3) |
| **DB 2.3** — seed del task snapshot indirizzi | ✅ **FATTA** (registrazione + handler in Fase 1; armamento DB applicato il 2026-07-31). **Coda del 2026-07-31 sera**: il DB ha rinominato il wrapper in `fn_snapshot_fattura_lotto` (scrive anche l'intestazione — brief §10.8) e il BE è stato riallineato: valore in `ALLOWED_TASK_FUNCTIONS`, query del wrapper, **sesto contatore `intestazioni_scritte`** già letto. Il `task_code` e il nome del metodo Python restano `snapshot_indirizzi_lotto`/`run_snapshot_indirizzi_lotto_task`: l'ancora stabile è il task, non la funzione dietro il wrapper | ~~Prima che il DB armi lo step DRAFT~~ → chiusa |

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

> 🔄 **Rev. 2026-07-30 (decisione Tid, che supera il paragrafo precedente).**
> **Si rinomina su ENTRAMBI gli strati**: i nomi Python vanno resi coerenti con
> quelli DB. La proposta di rinunciare alla rinomina **non è stata accolta**, e
> nemmeno quella di rinominare solo a DB.
>
> **Motivo**: rinominare solo a DB scambia un disallineamento con uno peggiore.
> Un nome che mente ma è coerente ovunque si impara una volta; due nomi diversi
> per la stessa cosa su due strati si sbagliano ogni volta. Il «debito accettato
> consapevolmente» sarebbe stato pagato da chiunque leggesse il codice dopo.

**Oltre alle quattro righe obbligatorie, vanno rinominati anche i nomi Python**
(~12 punti, meccanici):

| File | Cosa |
|---|---|
| `services/pipeline_service.py` | entrypoint `fn_reset_lotto_draft` / `fn_reset_lotto_fattura_draft` → nomi allineati a quelli DB |
| `services/__init__.py` | import e `__all__` |
| `api/views.py` | import e chiamate nelle due view |
| `db/pipeline_repository.py` | i metodi `reset_lotto_draft` / `reset_lotto_fattura_draft` |
| `services/lotto_reset_service.py` | il metodo omonimo |
| test | i `@patch` che puntano ai nomi vecchi |

⚠️ Il **`task_code`** del registry (`reset_lotto_draft`) **resta invariato**: è il
nome del *task* di pipeline, non della funzione, e vive nei CSV di seed.
Rinominarlo sarebbe una migrazione di dati senza guadagno.

> **I punti 2, 3 e 4 di D-L restano il valore vero della decisione** — in
> particolare l'**over-free del `lock_batch_id`** (C-22), che è un bug e va
> corretto comunque, e che non induce nessun lavoro applicativo.

### D-Q: la metà applicativa — 📎 nota del team DB (2026-07-31)

> **Chi scrive:** DB (`dev/db-tid`), scrivendo la Fase 2.2. Simmetrica alla vostra
> §4-ter. **Perché vi riguarda:** la decisione D-Q di Tid è per metà vostra, e
> senza quella metà il disegno non sta in piedi — il lato DB è pronto ma il
> runner non lo lascia partire.

**La regola decisa da Tid** (piano DB §2, D-Q): se una fattura è difettosa, lo
step **si completa lo stesso**, la fattura resta **marcata in errore**, il lotto
**non avanza** allo step successivo. Per uscirne, due strade: **estrarre** il
documento dal lotto, oppure **rilanciare lo stesso step** — *ero su DRAFT
rilancio DRAFT, ero su EMESSA rieseguo EMESSA*.

**Cosa abbiamo già fatto lato DB.** La marcatura per-fattura esiste da sempre e
funziona: log `'C'` su `fatture_log` → `fn_sync_fatture_log_critical_lotto` →
`fn_resolve_stato_esecuzione` (`critical` → `ERRORE`) su
`fatturazione_lotti_fatture`. In `fn_snapshot_indirizzi_lotto` (2.2) abbiamo
aggiunto il pezzo mancante: **al successo il task ritira le proprie segnalazioni
precedenti** (`disabilitato = true`, filtrando su `meta->>'source'`), così il
rilancio dello step riporta davvero a posto la fattura. Il ricalcolo lo fa da sé
il trigger `AFTER UPDATE` su `fatture_log`.

**I due punti che restano a voi.**

| # | Dove | Cosa |
|---|---|---|
| 1 | `services/lotto_segnalazioni_service.py` (`evaluate_lotto_status`) + `services/pipeline_runner.py:410-431` | Oggi `blocks_next_step` è vero se esiste **una** criticità o **una** fattura in `ERRORE`, e il runner rifiuta **qualunque** esecuzione con `E_PIPELINE_LOTTO_CRITICAL`. Va distinto **«non avanzare»** da **«non ripartire»**: il rilancio dello **stesso** step deve essere ammesso, l'avanzamento al successivo no. Finché questa riga non cambia, la via d'uscita di D-Q è vietata dal codice |
| 2 | `services/pipeline_error_logger.py` + `services/pipeline_runner.py:76-86` | Su **qualunque** errore di pipeline il runner scrive un critical di **scope LOTTO**, e **nessuno lo ritira mai**. Quindi anche risolto il punto 1, un lotto che ha avuto un giro fallito resterebbe bloccato per una segnalazione vecchia. Stesso principio che abbiamo applicato a DB: **chi alza la bandiera la abbassa** — al successo dello step, le segnalazioni di lotto scritte dal BE per quello step vanno disattivate |
| 3 | Handler del task (`pipeline_step_executor`, scrittura di `fatturazione_lotti_task_runs`) | 🔴 **Senza questo, il punto 1 non basta.** `fn_resolve_lotto_task_execution_mode` risolve `task_stato = 'COMPLETATO'` → **`SKIP`**. Il nostro task **non solleva** quando una fattura fallisce (per disegno: le altre devono essere lavorate), quindi il `task_run` risulterebbe COMPLETATO e **il rilancio dello step salterebbe il task** — l'anagrafica corretta non verrebbe mai riletta. L'handler deve registrare il `task_run` come **`ERRORE`** quando `failed_rows > 0`: allora la risoluzione dà `RESUME` (la policy è `RESUME_TASK`) e il rilancio funziona. È il motivo per cui `fn_snapshot_indirizzi_lotto` ritorna **cinque** contatori invece di tre: `failed_rows` esiste perché voi possiate distinguere «fatto» da «fatto, ma con rifiuti» |

**Tre fatti verificati il 2026-07-31**, perché non li ridobbiate cercare:

- **nessuno** porta `disabilitato` a `true`, in tutto `backend/apps/` — la colonna
  esiste, i lettori la rispettano, ma non ha scrittori;
- i log critici spariscono **solo** con `fn_cleanup_fatture_by_ids`, cioè
  distruggendo la fattura: oggi l'unica uscita reale è rifare il lotto;
- disattivare un log **basta**: il trigger `AFTER UPDATE` su `fatture_log`
  richiama `fn_sync_fatture_log_critical_lotto`, che conta i soli log con
  `disabilitato IS FALSE` e riallinea `critical` e `stato_esecuzione`. Non serve
  scrivere nient'altro.

> ⚠️ **Sfumatura da non invertire**, vale per entrambi i lati: lo step **corrente
> riprova** le fatture in errore (è la correzione), gli step **a valle le
> saltano** (lì la fattura è un rifiuto). Se il DRAFT le filtrasse, non si
> potrebbe più correggere; se l'EMESSA le riprovasse, una fattura senza
> indirizzo arriverebbe alla numerazione.
>
> 📌 È anche il **punto B dell'analisi 6.0** del piano DB, dove è annotato come
> «rinviato, vedremo». Segnaliamo che **morde prima**: si presenterà al primo
> cliente senza indirizzo di fatturazione, non in Fase 6.

## 4-ter. 📎 Due note per il team DB, emerse scrivendo la Fase 0 (2026-07-31)

Nessuna delle due è un difetto: sono **trappole da fixture** che ho incontrato di
persona collaudando la catena, e che si ripresenteranno scrivendo i pgTAP del
punto **2.4** del piano DB. Riportarle qui fa risparmiare due giri a vuoto.

### (a) `CON` non è ottenibile dal layer RUOLO di un cliente

Misurato sul DB il 2026-07-31:

| Insieme | Tipi |
|---|---|
| Whitelist ambito `FATTURE` (`tipi_indirizzi_allowed`) | `RES`, **`FATT`** (obbligatorio), `FORNITURA`, `CON` |
| Ammessi al **ruolo cliente** (`tipi_ruolo_tipi_indirizzo`, tipo_ruolo 1) | `RES`, `DOMFISC`, `POSTA`, `SPED`, `FATT`, `FORNITURA` — **`CON` assente** |
| Presenti sul layer **SOGGETTO** (dati reali) | `RES`, `DOMFISC`, `SEDELEG`, `POSTA`, `SPED`, `FATT`, **`CON`** |

`CON` è ammesso al solo `tipo_ruolo = 8`. Quindi sul layer RUOLO di un cliente
**non può esistere**, e per una fattura può arrivare solo dal layer SOGGETTO.

Non è un problema di comportamento — D-2 dice che i tipi opzionali mancanti non
generano errore, quindi il task 2.1 fa la sua ricerca e va avanti. Ma ha **due
conseguenze pratiche**:

1. **la fixture pgTAP di 2.4 non può inserire un `CON` sul ruolo cliente**: il
   trigger `trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo` la respinge con
   `E_TIPO_INDIRIZZO_NON_PERMESSO`. Per esercitare `CON` bisogna passare dal
   layer SOGGETTO (o usare un ruolo di tipo 8);
2. vale la pena **decidere consapevolmente** se lo slot `CON` sulla fattura ha
   senso: oggi resterà vuoto in tutti i casi in cui il cliente non ha un
   indirizzo di consegna sul soggetto. Le alternative sono ammettere `CON` al
   ruolo cliente, togliere `CON` dalla whitelist `FATTURE`, o accettarlo come
   slot che si popola solo per via anagrafica indiretta. Non urge, ma meglio
   scritto che scoperto in validazione.

### (b) Gli indirizzi «liberi» hanno un CHECK a quattro campi

`anagrafiche.indirizzi` non ha colonne CAP/città. Per una riga **non
normalizzata** il vincolo `chk_indirizzi_free_requirements` pretende
`indirizzo_libero` **+** `stato_id` **+** la terna
`(locality, postal_box, administrative_area | sublocality)` — oppure la coppia
normalizzata `(comune_id, codice_postale_id)`. Una `INSERT` con il solo
`indirizzo_libero` viene respinta.

È il secondo inciampo che ho avuto: le fixture di 2.4 vanno scritte con la terna
completa (nel mio smoke: `'Roma', '00100', 'RM'` + `stato_id` dell'Italia).

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

## 7. Decisioni FE ~~ancora aperte~~ — **TUTTE CHIUSE il 2026-08-22**

> ✅ **Chiuse da Tid il 2026-08-22: «no» a tutte e tre.** Il testo sotto resta
> com'era scritto (è il ragionamento con cui le domande erano state poste); la
> risposta e il motivo sono nel box in testa al documento. In sintesi:
>
> 1. **No** — lo snapshot si riscrive a ogni passata dello step DRAFT, quindi una
>    correzione a mano non sopravvive al rilancio: si corregge a monte;
> 2. **No, non adesso** — sul BA padre la riga `FATT` è in pratica l'unica, e il
>    suo display è già nel payload; si riapre col sotto-dettaglio utilities;
> 3. **No, non qui** — il badge documenti appartiene al cantiere archivio/stampe,
>    e il dict `contatori` è già pronto ad accoglierlo.

1. **L'operatore deve poter correggere un indirizzo su fattura DRAFT?**
   - **Sì** → serve l'endpoint (factory `build_indirizzi_documento_views` già
     pronta) + `stati_modificabili = {"DRAFT"}` + un lettore di stato
     (`get_stato_codice` **assente** su `VenditeRepository`, da scrivere) + montare
     `DocumentoIndirizziSection` nel drawer.
   - **No** → la tabella è scritta solo dalla pipeline; nel drawer gli indirizzi si
     mostrano in sola lettura (o non si mostrano affatto).
2. **Gli indirizzi vanno esposti nel dettaglio fattura?** Se sì, il payload cresce
   di una chiave e vale l'avvertenza RLS del §6.
   ℹ️ *Aggiornamento Fase 2 (2026-07-31)*: il payload del dettaglio espone già
   `emittente_snapshot` e `cliente_snapshot` integrali (additivo, shape non
   contrattuale — brief intestazione §10.2) e `cliente_indirizzo` ora è il
   display della riga `FATT` congelata. La decisione aperta resta quella sulla
   **lista** delle righe di `fatture_indirizzi` (gli slot per tipo), non
   sull'intestazione.
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
