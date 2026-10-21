## 📘 Documentazione Concettuale – Tabella `vendite.contratti`

> 👀 **Vedi anche**
>
**Guide generali:**    
>
• [Generazione di un cliente](/guide/generazione-cliente)    
> • [Gestione delle istanze utility](/guide/gestione-delle-istanze-utility)    
>
**Approfondimento tabelle:**    
>
• [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe)    
> • [vendite.note_contratto](/dbzero/vendite/tabelle/note_contratto)    
> • [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)    
> • [anagrafiche.istanze_dati_precontrattuali](/dbzero/anagrafiche/tabelle/istanze_dati_precontrattuali)     
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)    
> • [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti)    
> • [config.utilities](/dbzero/config/tabelle/utilities)    
> • [config.stati_doc_contratti](/dbzero/config/tabelle/stati_doc_contratti)   
>
**Approfondimento funzioni:**
>
• [`vendite.trgfn_contratti_gen_codice`](/dbzero/vendite/funzioni/trgfn_contratti_gen_codice)
>
### 🎯 Scopo Principale
(Initial version - 19-01-26)
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
  dal 2026-10-11 al posto di `trg_contratti_z90_sync_is_abortito_snapshot_ins_upd`):
  mantiene `is_abortito_snapshot` e `is_draft_snapshot` allineati allo stato a
  ogni scrittura, anche se qualcuno li scrive a mano. Serve anche all'indice
  unico sui vivi `uq_contratti_offerta_id` (un'offerta genera al più un
  contratto vivo).
  Deve essere BEFORE (non AFTER): il predicato WHERE del constraint e’
  valutato al momento della scrittura della riga.
* La colonna `validita` (GENERATED ALWAYS STORED) rimane immutata e continua
  ad essere usata per query di date (`@>`, `&&`). Il constraint parziale la
  usa come operand temporale solo per le righe non abortite.

> **Nota PG18**: `UNIQUE WITHOUT OVERLAPS` non supporta predicati `WHERE`
> parziali e non ammette `’empty’::daterange` nel temporal part. Per questo
> motivo si usa `EXCLUDE USING gist` parziale anziche’ il temporal UNIQUE
> SQL:2011 introdotto in PG18 (migration `20260521-03`, vedi
> `linee-guida-sql §7b`).

---

### Collegamenti anagrafici

* **Billing Account** (`billing_account_id`) = intestatario economico del contratto.
* **Istanza utility** (`istanza_utility_id`) = punto tecnico/fornitura del servizio.
* **Utility** (`utility_id`) = dominio tecnico (gas, energia, ecc.), coerente con BA e istanza.
* **Cliente**: deriva dalla relazione BA/istanza (`anagrafiche.clienti`), non e` salvato direttamente in `vendite.contratti`.

---

### 📄 Riferimenti dell'atto: CIG, CUP e commessa (dal 2026-08-29)

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
contratto — solo `billing_account_id` e la coppia `sorgente_tipo_id`/`sorgente_uid` — quindi
i tre codici vanno **copiati** al momento dell'emissione.
⭐ E la sede giusta e` la **riga di fattura**, non la testata: `vendite.fatture_righe` porta
una sorgente per riga fra **quindici tipi** (`config.sorgenti`), quindi una fattura puo`
mescolare righe di **contratti diversi** — un campo di testata dovrebbe sceglierne uno fra
tanti. E` anche cio` che la FatturaPA prevede, con `RiferimentoNumeroLinea`.
Da costruire insieme a chi lo riempie (cantiere IVA, `I4`).

📌 **Fuori perimetro, annotato**: negli accordi quadro PA il contratto ha un CIG «padre» e
ogni ordine attuativo ne ha uno derivato. Se quel caso arrivera`, la forma sono gli stessi
tre campi su `vendite.ordini`, nullable, col contratto come ripiego (`COALESCE`).

Cantiere: `brief-db-be-iva-risolutore-e-regime-cliente.md`, D9 / I8.

---

### Integrazione con `anagrafiche.istanze_dati_precontrattuali`

I dati precontrattuali sono **tipici del dominio utilities** e sono riferiti a `istanza_utility_id` e `utility_id`. Il contratto li integra in modo **non invasivo**:

* **Durante la creazione**: i parametri tecnici (potenza, classe utenza, ecc.) possono essere **copiati in `meta`** o usati per valorizzare righe e regole di fatturazione.
* **Durante l’attivazione**: i dati precontrattuali diventano **baseline** per pricing e configurazioni di erogazione.
* **Dopo l’attivazione**: il contratto governa il ciclo commerciale; i precontrattuali restano **storico di raccolta**, utili per audit o riconciliazioni.

Per attivita **non‑utilities** o servizi eterogenei, i dati precontrattuali possono **non essere presenti**: in tal caso le condizioni specifiche risiedono in `vendite.contratti.meta` e in `vendite.contratti_righe.meta`.

---

### Pricing — modello unificato (dal 2026-05-15)

> **Refactor da modalità A/B/C a modello unificato** (migration 20260515-10,
> `brief-db-refactor-contratti-completo.md` Fase 2 Step 2.1).
> La distinzione A/B/C è eliminata: il contratto è **uno solo** con forma
> derivata automaticamente dai campi compilati.

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
un campo `tipo_eccezione` (introdotto in Step 2.2):

| `tipo_eccezione` | Significato | `prezzo_unitario` |
| --- | --- | --- |
| `OVERRIDE` | Prezzo personalizzato per articolo del listino | NOT NULL |
| `ESCLUSIONE` | Articolo del listino non disponibile per questo cliente | NULL |
| `AGGIUNTA` | Articolo non presente nel listino, aggiunto al contratto | NOT NULL |

Vincoli CHECK attivi:

* `chk_contratti_tipo_variazione_globale`: solo `PERCENTUALE`/`VALORE_FISSO` o NULL.

Vincoli CHECK rimossi (modello unificato):

* ~~`chk_contratti_modalita_pricing`~~ — droppato in Step 2.1: qualsiasi combinazione listino/variazione è ora ammessa
* ~~`chk_contratti_variazione_globale_coerente`~~ — droppato in Step 2.1: ora rilassato

Trigger modalità C rimossi:

* ~~`trg_contratti_a10_guard_modalita_c_activation_ins_upd`~~ — droppato in Step 2.1; sostituito dal trigger di freeze versione (Step 2.3)
* ~~`trg_contratti_righe_a10_guard_modalita_c_ins_upd`~~ — droppato in Step 2.1; ora le righe hanno logica propria per `tipo_eccezione`

**Comportamento attivazione** (dal Step 2.3) — trigger
`trg_contratti_a10_freeze_listino_versione_upd`:

* Transizione DRAFT→ATTIVO con `listino_id IS NULL`: richiede almeno una riga AGGIUNTA con `prezzo_unitario NOT NULL`. Errore: `E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE` (451).
* Transizione DRAFT→ATTIVO con `listino_id IS NOT NULL`: fissa `listino_versione_id` sulla versione attiva a `CURRENT_DATE`. Se non trovata: attivazione consentita, `listino_versione_id` resta NULL (§4.4).
* Dal 2026-10-21 il guard di transizione (`vendite.trgfn_contratti_guard_transizione_stato`) rifiuta
  anche un contratto con una riga che la regola intera (articolo, erogazione, fonte) non ammette
  più: `script.fn_check_righe_documento`, `E_DOC_RIGA_NON_AMMESSA`; la capability spegne «Attiva»
  con lo stesso motivo. Le regole di una riga dipendono da dati che stanno fuori dalla riga, e in
  DRAFT la riga si corregge (`brief-db-offerta-emissione-ed-erogazione` §I.2, H-R4).

**Lock post-attivazione** (dal Step 2.3):

* **Testata** — trigger `trg_contratti_a05_lock_fuori_bozza_upd`
  (→ [`trgfn_doc_testata_lock_fuori_bozza`](/dbzero/vendite/funzioni/trgfn_doc_testata_lock_fuori_bozza)):
  fuori bozza sono fermi identità, cliente, condizioni (pricing compreso) e
  sorgente; `valido_al`, CIG, CUP, codice commessa e note si cambiano in ATTIVO
  e si fermano in CESSATO e ANNULLATO. Dal 2026-10-10 (brief
  `brief-db-testata-dopo-emissione`); prima le quattro colonne di pricing le
  fermava `trgfn_contratti_lock_post_attivazione` solo in ATTIVO
  (`E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE`, ritirati).
* **Righe** — trigger `trg_contratti_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt`
  (→ [`trgfn_doc_righe_lock_fuori_bozza`](/dbzero/vendite/funzioni/trgfn_doc_righe_lock_fuori_bozza),
  il building block «le righe di un documento si toccano solo in bozza»):
  blocca qualsiasi INSERT/UPDATE/DELETE su `contratti_righe` quando il contratto
  padre **non è in DRAFT** — quindi in ATTIVO, e da questa revisione anche in
  CESSATO e ANNULLATO, dove il backend le negava già.
  Errore: `E_RIGA_DOC_NON_BOZZA`. La copia dedicata
  (`trgfn_contratti_righe_lock_post_attivazione`, che bloccava il solo ATTIVO)
  è stata ritirata il 2026-09-22 e riassorbita nel building block.

---

### Valuta del contratto (dal 2026-05-29)

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
* Indice FK gestito dalla policy centralizzata (`consentito=false` come
  `fk_preventivi_valuta`): nessun indice manuale.

---

### Workflow stato e cessazione automatica (dal 2026-04-26)

Le transizioni di stato sono **vincolate da guard trigger**
(`trg_contratti_a10_guard_transizione_stato_upd` →
`vendite.trgfn_contratti_guard_transizione_stato`,
migration `20260426-05-...`).

Lo `stato_doc_contratto_id` e' FK a `config.stati_doc_contratti`. Il
guard fa lookup via `codice_interno` (immutabile per `lock_columns`)
per stabilita' rispetto a relabelling.

**Matrice transizioni ammesse**:

| Da | A | Ammessa | Condizione |
| --- | --- | --- | --- |
| DRAFT | ATTIVO | si | — |
| DRAFT | ANNULLATO | si | sempre (nessuna fatturazione su DRAFT) |
| ATTIVO | CESSATO | si | `valido_al IS NOT NULL AND valido_al < CURRENT_DATE` |
| ATTIVO | ATTIVO | si | no-op |
| DRAFT | DRAFT | si | no-op |
| DRAFT | CESSATO | **no** | una bozza si annulla, non si cessa |
| ATTIVO | DRAFT | **no** | irreversibile |
| ATTIVO | ANNULLATO | **no** | un contratto attivo va cessato ordinariamente |
| CESSATO | * | **no** | stato terminale |
| ANNULLATO | * | **no** | stato terminale (`is_abortito = true`) |

**Stato ANNULLATO** (`codice_interno = 'ANNULLATO'`, `is_abortito = true`,
migration `20260520-07..08`):

* Raggiungibile **solo da DRAFT** — annullamento di una bozza non ancora attivata.
* Terminale: nessuna transizione successiva ammessa.
* Il constraint `ex_contratti_no_overlap` **esclude** le righe ANNULLATO
  (`WHERE NOT is_abortito_snapshot`): un contratto annullato non blocca
  la creazione di nuovi contratti sulla stessa quadrupla.
* Il campo `meta` di `config.stati_doc_contratti` per ANNULLATO e` `{}`:
  stato terminale, nessuna azione manuale in uscita.
* L'azione UI "Annulla" e` esposta da `script.fn_available_actions_contratto`
  leggendo `outgoing_action` dal `meta` dello stato DRAFT
  (migration `20260430-61` + `20260520-10`).

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

**Path utente per cessare un contratto**: non esiste un'azione
manuale "cambia stato a CESSATO" tradizionale. L'utente imposta
`valido_al` (PATCH); la cessazione di stato avviene automaticamente
alla scadenza tramite il **framework `dbops.automazione_chiusura_scadenze`**
(vedi sotto).

#### Cessazione automatica via framework

Il job pgAgent unico **`chiusura_scadenze_daily`** (00:05) invoca
`dbops.fn_apply_chiusura_scadenze()` che, leggendo la riga
configurata in `dbops.automazione_chiusura_scadenze`, esegue:

```sql
-- Lookup id stati via codice_interno
SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'CESSATO';
SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'ATTIVO';

-- UPDATE dinamico
UPDATE vendite.contratti
   SET stato_doc_contratto_id = <id_cessato>
 WHERE stato_doc_contratto_id = <id_attivo>
   AND valido_al IS NOT NULL
   AND valido_al < CURRENT_DATE;
```

L'UPDATE attraversa il guard transizione e lo soddisfa per
costruzione (`valido_al < CURRENT_DATE` identica al WHERE).

**Semantica `valido_al`** (importante per UX):

* `valido_al = oggi` → contratto ancora ATTIVO oggi (ultimo giorno **incluso**); cessazione scatta dalle 00:05 di domani.
* `valido_al = ieri` → contratto cessato; il job notturno gia' scattato lo ha portato a CESSATO.
* `valido_al = data_futura` → cessazione **programmata**; il contratto resta ATTIVO fino al giorno seguente la data, dove il job lo chiude automaticamente.

**Effetto pratico**: l'utente programma `valido_al` (PATCH) senza
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

### Corsia di fatturazione: `fatturazione_immediata` (27-07-2026)

Colonna `boolean NOT NULL DEFAULT false` aggiunta dalla slice di simmetria del
flag (brief `brief-db-emissione-fattura-per-documento-sorgente` PARTE B,
migration `20260727-02`). Prima esisteva **solo** su `vendite.preventivi`: le altre
sorgenti esponevano il campo nel contratto delle `fn_list_*_da_pushare` ma con
valore costante `FALSE`, quindi **solo un preventivo poteva essere fatturato
subito** — non per una scelta di dominio, ma per un buco di modello.

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

Il default `false` garantisce che l'aggiunta della colonna **non cambi la corsia
di nessun documento esistente**.

{% include-markdown "signature-core.md" %}

---

### Il listino del documento (dal 2026-10-08)

Il contratto si riferisce solo a un listino della **sua utility** e del **suo emittente**. Lo dice la
check pura `script.fn_check_listino_documento(listino, utility, emittente_fiscale_id)`, che il guard
`script.trgfn_doc_guard_listino_documento` solleva all'INSERT e quando cambiano `listino_id`,
`utility_id` o `emittente_fiscale_id` (`E_DOC_LISTINO_UTILITY_DIVERSA`,
`E_DOC_LISTINO_EMITTENTE_DIVERSO`, campo `listino_id`). I documenti già scritti non si
rigiudicano. La tendina del form legge la stessa check da `vendite.fn_listini_selezionabili(utility,
emittente_fiscale_id)`. Brief `brief-db-offerta-emissione-ed-erogazione` §F.2.

