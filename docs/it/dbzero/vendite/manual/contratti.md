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
* **Anti‑overlap operativo**: l’indice `ex_contratti_no_overlap` supporta query di controllo per evitare sovrapposizioni sulla stessa combinazione `billing_account_id + istanza_utility_id + utility_id + ambito`.

> Nota: l’anti‑overlap e` tipicamente garantito da logiche applicative o trigger di validazione.

---

### Collegamenti anagrafici

* **Billing Account** (`billing_account_id`) = intestatario economico del contratto.
* **Istanza utility** (`istanza_utility_id`) = punto tecnico/fornitura del servizio.
* **Utility** (`utility_id`) = dominio tecnico (gas, energia, ecc.), coerente con BA e istanza.
* **Cliente**: deriva dalla relazione BA/istanza (`anagrafiche.clienti`), non e` salvato direttamente in `vendite.contratti`.

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

**Lock post-attivazione** (dal Step 2.3):

* **Testata** — trigger `trg_contratti_a10_lock_post_attivazione_upd`
  (→ [`trgfn_contratti_lock_post_attivazione`](/dbzero/vendite/funzioni/trgfn_contratti_lock_post_attivazione)):
  blocca UPDATE di `listino_id`, `listino_versione_id`, `tipo_variazione_globale`,
  `valore_variazione_globale` su contratti ATTIVI.
  Errore: `E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE` (452).
* **Righe** — trigger `trg_contratti_righe_a10_lock_post_attivazione_ins_upd_dlt`
  (→ [`trgfn_contratti_righe_lock_post_attivazione`](/dbzero/vendite/funzioni/trgfn_contratti_righe_lock_post_attivazione)):
  blocca qualsiasi INSERT/UPDATE/DELETE su `contratti_righe` quando il contratto padre è ATTIVO.
  Errore: `E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE` (452).

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
| ATTIVO | CESSATO | si | `valido_al IS NOT NULL AND valido_al < CURRENT_DATE` |
| ATTIVO | ATTIVO | si | no-op |
| DRAFT | DRAFT | si | no-op |
| DRAFT | CESSATO | **no** | una bozza si cancella |
| ATTIVO | DRAFT | **no** | irreversibile |
| CESSATO | * | **no** | stato terminale |

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
* [WIP automazione-chiusure-scadenze](/dev/work-in-progress/automazione-chiusure-scadenze)

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

{% include-markdown "signature-core.md" %}

---
