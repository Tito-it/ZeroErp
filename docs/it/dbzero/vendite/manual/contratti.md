## 📘 Documentazione Concettuale – Tabella `vendite.contratti`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe) — le eccezioni del contratto rispetto al listino
> * [vendite.note_contratto](/dbzero/vendite/tabelle/note_contratto) — le note del contratto
> * [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali) — l'offerta da cui il contratto può nascere
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — il punto di fornitura
> * [anagrafiche.istanze_dati_precontrattuali](/dbzero/anagrafiche/tabelle/istanze_dati_precontrattuali) — i dati raccolti prima del contratto
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — l'intestatario economico
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti) — il cliente
> * [config.utilities](/dbzero/config/tabelle/utilities) — il dominio tecnico
> * [config.stati_doc_contratti](/dbzero/config/tabelle/stati_doc_contratti) — il vocabolario degli stati
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il catalogo dei tipi di documento d'origine
>
> Approfondimento funzioni:
>
> * [vendite.trgfn_contratti_gen_codice](/dbzero/vendite/funzioni/trgfn_contratti_gen_codice) — il numero del contratto
> * [vendite.fn_push_offerta_a_contratto](/dbzero/vendite/funzioni/fn_push_offerta_a_contratto) — il contratto che nasce da un'offerta
> * [vendite.trgfn_doc_guard_delete_solo_bozza](/dbzero/vendite/funzioni/trgfn_doc_guard_delete_solo_bozza) — si cancella solo la bozza vuota
> * [script.trgfn_guard_sorgente](/dbzero/script/funzioni/trgfn_guard_sorgente) — il guard unico della provenienza
>
> Guide:
>
> * [Generazione di un cliente](/guide/generazione-cliente) — da dove arrivano BA e istanza
> * [Gestione delle istanze utility](/guide/gestione-delle-istanze-utility) — l'istanza a cui il contratto si lega
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza

---

### 🎯 Scopo Principale

`vendite.contratti` rappresenta la **testata del contratto commerciale**: l’accordo che lega un **billing account** a una **istanza/utility** e ne definisce **ambito**, **periodo di validita** e **stato**. E` la base di aggregazione delle righe (`vendite.contratti_righe`) e il punto di riferimento per la generazione di **attivita fatturabili**.

Obiettivi principali:

* Modellare la **relazione contrattuale** tra cliente (via BA) e fornitura/servizio (istanza utility).
* Delimitare un **periodo di validita** con regole anti‑overlap.
* Tracciare lo **stato del contratto** (bozza, attivo, chiuso, ecc.).
* Stabilire un **contenitore unico** per condizioni, righe e metadati eterogenei.

---

### Collocazione nel flusso operativo

1. **Fase pre‑cliente**: raccolta dati tecnici/commerciali su `anagrafiche.istanze_dati_precontrattuali`.
2. **Creazione contratto**: assegnazione `billing_account_id`, `istanza_utility_id`, `utility_id` e periodo di validita.
3. **Definizione righe**: aggiunta di servizi/beni in `vendite.contratti_righe` con regole di canone/erogazione.
4. **Attivazione**: cambio `stato_doc_contratto_id` e innesco processi di fatturazione.
5. **Rinnovo/chiusura**: gestione del ciclo di vita tramite `valido_al` e `parent_contratto_id`.

---

### Identita contratto & numerazione

* **Numero** (`numero`) generato da `vendite.trgfn_contratti_gen_codice()` se non fornito.
* **UID** (`uid`) per integrazioni esterne e idempotenza applicativa.
* **Blocco modifiche**: `script.trgfn_lock_columns('numero', ...)` impedisce aggiornamenti non autorizzati.
* **Data contratto** (`data`) valorizzata automaticamente alla prima assegnazione di `numero`.


---

### Validita, ambito e anti‑overlap

* **Periodo**: `valido_dal` e `valido_al` (NULL = aperto).
* **Ambito** (`ambito`) separa domini diversi (es. COMMODITY vs servizi extra).
* **Anti‑overlap**: il constraint `ex_contratti_no_overlap` (EXCLUDE USING gist,
  `btree_gist`) impedisce sovrapposizioni temporali sulla stessa quadrupla
  `billing_account_id + istanza_utility_id + utility_id + ambito`.
  Il constraint e` **parziale** (`WHERE NOT is_abortito_snapshot`): i contratti
  in stato ANNULLATO sono esclusi dal check e non bloccano nuovi contratti
  sulla stessa quadrupla.

#### Colonna `is_abortito_snapshot` e trigger di sincronizzazione

* **`is_abortito_snapshot BOOLEAN NOT NULL DEFAULT false`**: snapshot
  denormalizzato di `config.stati_doc_contratti.is_abortito` sulla riga del
  contratto. Necessario perche’ i constraint DB non possono referenziare altre
  tabelle — il predicato `WHERE` di `ex_contratti_no_overlap` dipende da un
  campo sulla stessa riga.
* **Trigger `trg_contratti_z90_snapshot_da_stato_ins_upd`** (BEFORE INSERT OR
  UPDATE, fase `_z90_`; BB
  [`vendite.trgfn_doc_snapshot_da_stato`](/dbzero/vendite/funzioni/trgfn_doc_snapshot_da_stato),
  mantiene `is_abortito_snapshot` e `is_draft_snapshot` allineati allo stato a
  ogni scrittura, anche se qualcuno li scrive a mano. Serve anche all'indice
  unico sui vivi `uq_contratti_sorgente_offerta` (un'offerta genera al più un
  contratto vivo).
  Deve essere BEFORE (non AFTER): il predicato WHERE del constraint e’
  valutato al momento della scrittura della riga.
* La colonna `validita` (GENERATED ALWAYS STORED) rimane immutata e continua
  ad essere usata per query di date (`@>`, `&&`). Il constraint parziale la
  usa come operand temporale solo per le righe non abortite.

> **Nota PG18**: `UNIQUE WITHOUT OVERLAPS` non supporta predicati `WHERE`
> parziali e non ammette `’empty’::daterange` nel temporal part. Per questo
> motivo si usa `EXCLUDE USING gist` parziale anziche’ il temporal UNIQUE
> SQL:2011 introdotto in PG18 (vedi `linee-guida-sql §7b`).

---

### Collegamenti anagrafici

* **Billing Account** (`billing_account_id`) = intestatario economico del contratto.
* **Istanza utility** (`istanza_utility_id`) = punto tecnico/fornitura del servizio.
* **Utility** (`utility_id`) = dominio tecnico (gas, energia, ecc.), coerente con BA e istanza.
* **Cliente**: deriva dalla relazione BA/istanza (`anagrafiche.clienti`), non e` salvato direttamente in `vendite.contratti`.

---

### Da quale documento nasce: l'offerta

Un contratto può nascere da un'offerta commerciale, e lo dice con le colonne del modello della
provenienza: `sorgente_tipo_id` (l'offerta, `OFFERTA_COMMERCIALE` in `config.sorgenti`) e la
chiave del documento in `sorgente_uid`, perché l'offerta si riconosce dall'uid. Un contratto nato
da solo le ha tutte vuote; la forma la tiene `chk_contratti_sorgente_forma`. La scrive
`vendite.fn_push_offerta_a_contratto`; il guard unico `script.trgfn_guard_sorgente` verifica
che l'offerta esista, e ne blocca la cancellazione finché un contratto la cita.

* ⭐ **Un'offerta genera al più un contratto vivo**: l'indice unico `uq_contratti_sorgente_offerta`
  vale sulle righe con tipo offerta e non annullate.
* Fuori bozza la provenienza è ferma, con il resto della testata.

### ⛔ Si cancella solo la bozza vuota

Un contratto si cancella solo nello stato in cui nasce, senza righe attive e senza contratti
che lo dichiarano come precedente (`parent_contratto_id`): la regola la tiene
`vendite.trgfn_doc_guard_delete_solo_bozza`, la stessa delle altre testate di vendita
(`E_DELETE_DOC_NON_BOZZA`, `E_DELETE_DOC_CON_RIGHE`, `E_DELETE_CONTRATTO_CON_SUCCESSIVI`).

---

### 📄 Riferimenti dell'atto: CIG, CUP e commessa

Tre colonne nullable — `codice_cig`, `codice_cup`, `codice_commessa` — che portano i
riferimenti dell'**atto** da cui il contratto nasce: rispettivamente la gara, il progetto
d'investimento e il riferimento di commessa/convenzione che il cliente chiede di vedere in
fattura.

⭐ **Vanno insieme, e non e` comodita`**: in fattura elettronica stanno nello **stesso
blocco** (`DatiContratto` / `DatiOrdineAcquisto`: `IdDocumento`, `CodiceCUP`, `CodiceCIG`,
`CodiceCommessaConvenzione`). Nascono insieme, si compilano insieme e nominano lo stesso
atto: separarli vorrebbe dire costruire un blocco XML da due tabelle con due cicli di vita.

⛔ **Prima stavano su `anagrafiche.clienti`, e sbagliavano in due direzioni insieme.** Li` la
riga e` **per fornitura**, mentre un CIG identifica una **gara**: una PA con tre contratti ha
tre CIG. Su una riga per fornitura ne entrava uno solo — ripetuto identico su tutte le
forniture dello stesso contratto (troppo) e incapace di tenerne due sulla stessa (troppo
poco).

⚠️ **In fattura non ci arrivano ancora.** `vendite.fatture` non ha **nessun** collegamento al
contratto — solo `billing_account_id` e la provenienza (`sorgente_tipo_id` con la chiave del
documento) — quindi
i tre codici vanno **copiati** al momento dell'emissione.
⭐ E la sede giusta e` la **riga di fattura**, non la testata: `vendite.fatture_righe` porta
una provenienza per riga fra i tipi di `config.sorgenti`, quindi una fattura puo`
mescolare righe di **contratti diversi** — un campo di testata dovrebbe sceglierne uno fra
tanti. E` anche cio` che la FatturaPA prevede, con `RiferimentoNumeroLinea`.
Da costruire insieme a chi lo riempie.

📌 **Fuori perimetro, annotato**: negli accordi quadro PA il contratto ha un CIG «padre» e
ogni ordine attuativo ne ha uno derivato. Se quel caso arrivera`, la forma sono gli stessi
tre campi su `vendite.ordini`, nullable, col contratto come ripiego.

---

### Integrazione con `anagrafiche.istanze_dati_precontrattuali`

I dati precontrattuali sono **tipici del dominio utilities** e sono riferiti a `istanza_utility_id` e `utility_id`. Il contratto li integra in modo **non invasivo**:

* **Durante la creazione**: i parametri tecnici (potenza, classe utenza, ecc.) possono essere **copiati in `meta`** o usati per valorizzare righe e regole di fatturazione.
* **Durante l’attivazione**: i dati precontrattuali diventano **baseline** per pricing e configurazioni di erogazione.
* **Dopo l’attivazione**: il contratto governa il ciclo commerciale; i precontrattuali restano **storico di raccolta**, utili per audit o riconciliazioni.

Per attivita **non‑utilities** o servizi eterogenei, i dati precontrattuali possono **non essere presenti**: in tal caso le condizioni specifiche risiedono in `vendite.contratti.meta` e in `vendite.contratti_righe.meta`.

---

### Pricing — modello unificato

Il contratto è **uno solo**, con forma derivata automaticamente dai campi compilati.

Il contratto e' il **ponte commerciale** tra billing account e listino (STADIO 1
del resolver prezzi). Due **forme derivate** (non scelta dell'operatore):

| Forma derivata | Condizione | Note |
| --- | --- | --- |
| **Con listino** | `listino_id NOT NULL` | Corrisponde alle vecchie modalità A + B fuse |
| **Senza listino** | `listino_id IS NULL` | Corrisponde alla vecchia modalità C; righe AGGIUNTA obbligatorie all'attivazione |

Campi pricing sulla testata:

| Colonna | Tipo | Nullable | Note |
| --- | --- | --- | --- |
| `listino_id` | bigint | YES | FK a `vendite.listini(id)`. NULL = contratto senza listino di riferimento |
| `tipo_variazione_globale` | varchar(16) | YES | `PERCENTUALE` o `VALORE_FISSO`. Opzionale anche con listino. |
| `valore_variazione_globale` | numeric | YES | Valore della variazione globale applicata al listino |
| `listino_versione_id` | bigint | YES | FK a `vendite.listini_versioni(id)`. NULL in DRAFT; fissato all'attivazione (snapshot versione). Immutabile post-attivazione. |
| `categoria_cliente_id_snapshot` | smallint | YES | FK a `anagrafiche.categorie_clienti`. Snapshot categoria BA. Auto-populate su INSERT. |

**Snapshot versione listino** (`listino_versione_id`): in DRAFT il contratto segue
la versione corrente del listino; all'attivazione (DRAFT→ATTIVO) il trigger
`trg_contratti_a10_freeze_listino_versione_upd`
(→ [`trgfn_contratti_freeze_listino_versione`](/dbzero/vendite/funzioni/trgfn_contratti_freeze_listino_versione))
fissa la versione attiva al momento dell'attivazione — da quel punto il contratto legge sempre quella
versione, anche se ne esce una successiva.

**Righe come eccezioni del listino**: `vendite.contratti_righe` contiene solo le
**eccezioni** rispetto al listino (non le righe del listino copiate). Ogni riga ha
un campo `tipo_eccezione`:

| `tipo_eccezione` | Significato | `prezzo_unitario` |
| --- | --- | --- |
| `OVERRIDE` | Prezzo personalizzato per articolo del listino | NOT NULL |
| `ESCLUSIONE` | Articolo del listino non disponibile per questo cliente | NULL |
| `AGGIUNTA` | Articolo non presente nel listino, aggiunto al contratto | NOT NULL |

Vincoli CHECK attivi:

* `chk_contratti_tipo_variazione_globale`: solo `PERCENTUALE`/`VALORE_FISSO` o NULL.

Qualsiasi combinazione di listino e variazione globale è ammessa.

**Comportamento attivazione** — trigger
`trg_contratti_a10_freeze_listino_versione_upd`:

* Transizione DRAFT→ATTIVO con `listino_id IS NULL`: richiede almeno una riga AGGIUNTA con `prezzo_unitario NOT NULL`. Errore: `E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE` (451).
* Transizione DRAFT→ATTIVO con `listino_id IS NOT NULL`: fissa `listino_versione_id` sulla versione attiva a `CURRENT_DATE`. Se non trovata: attivazione consentita, `listino_versione_id` resta NULL (§4.4).
* Il guard di transizione (`vendite.trgfn_contratti_guard_transizione_stato`) rifiuta
  anche un contratto con una riga che la regola intera (articolo, erogazione, fonte) non ammette
  più: `script.fn_check_righe_documento`, `E_DOC_RIGA_NON_AMMESSA`; la capability spegne «Attiva»
  con lo stesso motivo. Le regole di una riga dipendono da dati che stanno fuori dalla riga, e in
  DRAFT la riga si corregge.

**Lock post-attivazione**:

* **Testata** — trigger `trg_contratti_a05_lock_fuori_bozza_upd`
  (→ [`trgfn_doc_testata_lock_fuori_bozza`](/dbzero/vendite/funzioni/trgfn_doc_testata_lock_fuori_bozza)):
  fuori bozza sono fermi identità, cliente, condizioni (pricing compreso) e
  provenienza; `valido_al`, CIG, CUP, codice commessa e note si cambiano in ATTIVO
  e si fermano in CESSATO e ANNULLATO.
* **Righe** — trigger `trg_contratti_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt`
  (→ [`trgfn_doc_righe_lock_fuori_bozza`](/dbzero/vendite/funzioni/trgfn_doc_righe_lock_fuori_bozza),
  il building block «le righe di un documento si toccano solo in bozza»):
  blocca qualsiasi INSERT/UPDATE/DELETE su `contratti_righe` quando il contratto
  padre **non è in DRAFT**: in ATTIVO, CESSATO e ANNULLATO.
  Errore: `E_RIGA_DOC_NON_BOZZA`.

---

### Valuta del contratto

* `valuta_id` — FK a `config.valute(id)`, **nullable**. Source-of-truth della valuta
  sulla testata, fissata come **snapshot a INSERT-time** (simmetria con
  `vendite.preventivi` e `vendite.offerte_commerciali`).
* Valorizzata dal trigger `trg_contratti_a10_default_valuta_ins`
  (→ [`trgfn_contratti_default_valuta`](/dbzero/vendite/funzioni/trgfn_contratti_default_valuta))
  **solo se non passata esplicitamente** (es. push da offerta che propaga la
  valuta dell'offerta): il trigger delega al resolver canonico
  [`vendite.fn_get_valuta_id`](/dbzero/vendite/funzioni/fn_get_valuta_id) con catena
  **BA → emittente → gestore**. Nessuna logica di risoluzione duplicata.
* Ordina dopo `_a10_default_emittente_*`: `emittente_fiscale_id` e' gia' risolto e
  viene mappato a `soggetto_ruolo_id` per la fn.
* Se la catena non risolve, `fn_get_valuta_id` solleva `E_CONFIG_MANCANTE` (id 205)
  via `script.fn_log_and_raise_error`.
* Indice FK governato dalla politica centralizzata (`dbops.fk_index_policy`): nessun
  indice manuale. Nel CSV della politica la FK non ha una decisione, come
  `fk_preventivi_valuta`: finché resta scoperta e senza decisione la mostra il presidio
  `dbops.vw_fk_da_decidere`.

---

### Workflow stato e cessazione automatica

Le transizioni di stato sono **vincolate da guard trigger**
(`trg_contratti_a10_guard_transizione_stato_upd` →
`vendite.trgfn_contratti_guard_transizione_stato`).

Lo `stato_doc_contratto_id` e' FK a `config.stati_doc_contratti`. Il
guard fa lookup via `codice_interno` (immutabile per `lock_columns`)
per stabilita' rispetto a relabelling.

**Matrice transizioni ammesse**:

| Da | A | Ammessa | Condizione |
| --- | --- | --- | --- |
| DRAFT | ATTIVO | si | — |
| DRAFT | ANNULLATO | si | sempre (nessuna fatturazione su DRAFT) |
| ATTIVO | CESSATO | si | `valido_al` valorizzata e arrivata (`<=` la data operativa): oggi dall'operatore, il giorno dopo dalla scadenza |
| ATTIVO | ATTIVO | si | no-op |
| DRAFT | DRAFT | si | no-op |
| DRAFT | CESSATO | **no** | una bozza si annulla, non si cessa |
| ATTIVO | DRAFT | **no** | irreversibile |
| ATTIVO | ANNULLATO | **no** | un contratto attivo va cessato ordinariamente |
| CESSATO | * | **no** | stato terminale |
| ANNULLATO | * | **no** | stato terminale (`is_abortito = true`) |

**Stato ANNULLATO** (`codice_interno = 'ANNULLATO'`, `is_abortito = true`):

* Raggiungibile **solo da DRAFT** — annullamento di una bozza non ancora attivata.
* Terminale: nessuna transizione successiva ammessa.
* Il constraint `ex_contratti_no_overlap` **esclude** le righe ANNULLATO
  (`WHERE NOT is_abortito_snapshot`): un contratto annullato non blocca
  la creazione di nuovi contratti sulla stessa quadrupla.
* Il campo `meta` di `config.stati_doc_contratti` per ANNULLATO e` `{}`:
  stato terminale, nessuna azione manuale in uscita.
* L'azione UI "Annulla" e` esposta da `script.fn_available_actions_contratto`
  leggendo `outgoing_action` dal `meta` dello stato DRAFT.

> **Nota su SOSPESO**: il `codice_interno='SOSPESO'` esiste in
> `config.stati_doc_contratti` ma **non rientra nel workflow operativo
> attuale**. La sua semantica (effetti su fatturazione, ripristino)
> sara' affrontata come piano separato.

Violazione → `script.fn_log_and_raise_error` con codice
`E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA` (id 392 in `config.messaggi_errore`).

**Principio di applicabilita' operativa** (linee-guida-sql §7c): un
contratto e' *operativamente applicabile* quando `validita @> data_riferimento`.
Lo `stato` e' flag gestionale per UI/audit/reportistica; la logica
operativa (resolver prezzi, lookup attivi) **non** filtra per stato —
le date comandano.

**INSERT non vincolato**: il guard scatta solo su UPDATE OF
`stato_doc_contratto_id`. Consente seed/import e creazione di
contratti direttamente in stato non-DRAFT se necessario.

**Come si cessa un contratto**.

* **Dall'operatore**: [`vendite.fn_cessa_contratto`](/dbzero/vendite/funzioni/fn_cessa_contratto)
  con la data di fine. Oggi → `CESSATO` subito; futura → **cessazione programmata**, si scrive
  solo `valido_al` e il contratto resta ATTIVO; passata → rifiutata
  (`E_CONTRATTO_VALIDO_AL_RETROATTIVO`). Chiede l'azione `emetti_contratto`.
* **Alla scadenza**: [`vendite.fn_cessa_contratti_scaduti`](/dbzero/vendite/funzioni/fn_cessa_contratti_scaduti),
  chiamata dalla chiusura per scadenza (`dbops.fn_apply_chiusura_scadenze`, eseguita dal lavoro
  di coda `CHIUSURA_SCADENZE` di ogni azienda, che il job `chiusura_scadenze_daily` sveglia), cessa uno per uno, dalla scrittura comune del modello del
  documento, i contratti ATTIVO con `valido_al` prima di oggi.
* Finché il contratto è ATTIVO `valido_al` si può ancora spostare (o togliere): se un canone
  anticipato è già stato addebitato oltre la data nuova, il push storna o riaddebita la
  differenza ([guida dei contratti §4-bis.4](/guide/gestione-contratti#4-bis4-la-cessazione-e-gli-storni)).

**Semantica `valido_al`** (importante per UX):

* `valido_al = oggi` → l'ultimo giorno è **incluso**. Scritta oggi da `fn_cessa_contratto` il contratto passa subito a CESSATO; una cessazione programmata che arriva a oggi la chiude il job di domani.
* `valido_al = ieri` → contratto cessato; il job notturno gia' scattato lo ha portato a CESSATO.
* `valido_al = data_futura` → cessazione **programmata**; il contratto resta ATTIVO fino al giorno seguente la data, dove il job lo chiude automaticamente.

**Effetto pratico**: l'utente programma la fine con `fn_cessa_contratto` a una data futura, senza
toccare lo stato. Il job allinea lo stato `CESSATO` quando la
finestra e' effettivamente scaduta. Il principio fail-safe garantisce
che, anche se il job non scatta, la logica operativa resta corretta
(basata su `validita @> data`, non su `stato`).

Riferimenti:

* [linee-guida-sql §7c](/linee-guida-sql) — pattern "ciclo stato + finestra di validita'"
* [Catalogo processi pgAgent funzionali](/guide/processi-pgagent-funzionali) — scheda `chiusura_scadenze_daily`
* [WIP automazione-chiusure-scadenze](/dev/work-done/automazione-chiusure-scadenze)

---

### Meta, rinnovi e storicizzazione

* **`meta jsonb`**: contenitore estendibile per condizioni specifiche (SLA, clausole, parametri di calcolo).
* **Rinnovi/collegamenti**: `parent_contratto_id` collega contratti successivi (rinnovi, subentri, varianti).
* **Audit**: `data_insert`, `user_insert`, `data_update`, `user_update` e `storicizza` per tracciabilita e storico.



---

### Best practice

* Valorizzare sempre `billing_account_id`, `istanza_utility_id` e `utility_id` in modo coerente.
* Gestire `valido_dal`/`valido_al` per evitare sovrapposizioni contrattuali.
* Usare `meta` solo per **estensioni specifiche** del dominio, non per dati core duplicati.
* Collegare i rinnovi via `parent_contratto_id` per ricostruire la **storia contrattuale**.

---

### Ruolo nel sistema

`vendite.contratti` e` il **centro di gravita commerciale** tra istanza tecnica e fatturazione. In ambito utilities consolida i dati precontrattuali e li trasforma in **condizioni operative**, mentre in ambiti eterogenei diventa un contenitore flessibile di servizi e canoni da erogare nel tempo.

---

### Corsia di fatturazione: `fatturazione_immediata`

Colonna `boolean NOT NULL DEFAULT false`: dice se il contratto si fattura subito o nel giro
differito, come per gli altri documenti che vanno in commessa.

| Valore | Corsia | Arriva a |
|---|---|---|
| `true` | immediata (lotto `GIORNALIERO`) | `DEFINITIVA` — numera da sola |
| `false` *(default)* | differita (lotto `MASSIVO`) | `EMESSA` — la numerazione è un atto separato |

**Si stabilisce PRIMA del push.** Il valore viene letto una sola volta, da
`vendite.fn_list_contratti_da_pushare`, e propagato alla commessa dove è **parte della chiave di dedup** di
`fn_get_or_create_commessa`. Dopo il push è inerte, e la modifica è respinta
dal guard
[`trgfn_guard_fatturazione_immediata_immutabile`](/dbzero/vendite/funzioni/trgfn_guard_fatturazione_immediata_immutabile)
(`E_FATT_IMMEDIATA_NON_MODIFICABILE`). Il caso «cambio idea dopo» è coperto
dall'**emissione mirata per gruppo fatturabile**, non da questo flag.

⚠️ **Non governa `prezzo_bloccato`.** L'accoppiamento
`prezzo_bloccato = COALESCE(fatturazione_immediata, false)` esiste **solo sui
preventivi**: qui i due valori sono indipendenti e vanno tenuti tali.

---

### Il listino del documento

Il contratto si riferisce solo a un listino della **sua utility** e del **suo emittente**. Lo dice la
check pura `script.fn_check_listino_documento(listino, utility, emittente_fiscale_id)`, che il guard
`script.trgfn_doc_guard_listino_documento` solleva all'INSERT e quando cambiano `listino_id`,
`utility_id` o `emittente_fiscale_id` (`E_DOC_LISTINO_UTILITY_DIVERSA`,
`E_DOC_LISTINO_EMITTENTE_DIVERSO`, campo `listino_id`). I documenti già scritti non si
rigiudicano. La tendina del form legge la stessa check da `vendite.fn_listini_selezionabili(utility,
emittente_fiscale_id)`.

---

### Note di migrazione

* 2026-04-26 — il workflow degli stati passa sotto il guard di transizione.
* 2026-05-15 — il pricing a modalità A/B/C diventa il modello unificato: ritirati
  `chk_contratti_modalita_pricing`, `chk_contratti_variazione_globale_coerente` e i trigger
  della modalità C (brief-db-refactor-contratti-completo).
* 2026-05-29 — arriva `valuta_id`, snapshot alla nascita.
* 2026-07-27 — arriva `fatturazione_immediata`: prima il flag esisteva solo sul preventivo, e solo
  un preventivo poteva essere fatturato subito (brief-db-emissione-fattura-per-documento-sorgente).
* 2026-08-29 — CIG, CUP e codice commessa passano da `anagrafiche.clienti` al contratto
  (brief-db-be-iva-risolutore-e-regime-cliente).
* 2026-09-22 — il lock dedicato delle righe (`trgfn_contratti_righe_lock_post_attivazione`) si
  ritira nel building block delle righe in bozza.
* 2026-10-10 — il lock della testata fuori bozza prende il posto di
  `trgfn_contratti_lock_post_attivazione` (brief-db-testata-dopo-emissione).
* 2026-10-11 — lo snapshot dello stato passa al BB `vendite.trgfn_doc_snapshot_da_stato`.
* 2026-10-31 — arrivano le porte di cessazione `fn_cessa_contratto` e
  `fn_cessa_contratti_scaduti`.
* 2026-11-07 — la provenienza passa al modello: la colonna parallela `offerta_id` e
  `uq_contratti_offerta_id` si ritirano, la chiave testuale `sorgente_uid` diventa la coppia
  tipizzata `sorgente_id` / `sorgente_uid` (uuid) col guard unico, e l'unicità dell'offerta
  diventa `uq_contratti_sorgente_offerta`; la cancellazione passa sotto la regola della bozza
  vuota, e la FK del contratto precedente (`fk_contratti_parent`) diventa `NO ACTION`
  (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
