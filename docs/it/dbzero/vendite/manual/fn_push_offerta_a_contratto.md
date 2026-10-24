## 📘 Documentazione Concettuale – Funzione `vendite.fn_push_offerta_a_contratto(...)`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
> [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali)
> [vendite.offerte_commerciali_eccezioni](/dbzero/vendite/tabelle/offerte_commerciali_eccezioni)
> [vendite.offerte_commerciali_eccezioni_componenti](/dbzero/vendite/tabelle/offerte_commerciali_eccezioni_componenti)
> [vendite.offerte_commerciali_utilities](/dbzero/vendite/tabelle/offerte_commerciali_utilities)
> [vendite.contratti](/dbzero/vendite/tabelle/contratti)
> [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe)
> [vendite.contratti_righe_componenti](/dbzero/vendite/tabelle/contratti_righe_componenti)
> [vendite.contratti_utilities](/dbzero/vendite/tabelle/contratti_utilities)
> [config.sorgenti](/dbzero/config/tabelle/sorgenti)
> [pratiche.pratiche_sorgenti](/dbzero/pratiche/tabelle/pratiche_sorgenti)
>
> Trigger correlati:
> [vendite.trgfn_contratti_snapshot_precontrattuali](/dbzero/vendite/funzioni/trgfn_contratti_snapshot_precontrattuali)
>
> Funzioni correlate:
> [vendite.fn_crea_revisione_offerta](/dbzero/vendite/funzioni/fn_crea_revisione_offerta)
> [vendite.fn_contratto_sovrapposto](/dbzero/vendite/funzioni/fn_contratto_sovrapposto)
> [vendite.fn_chiudi_contratto_per_successione](/dbzero/vendite/funzioni/fn_chiudi_contratto_per_successione)
>
> Contesto di sviluppo:
> [Brief DB offerte commerciali — Step 8](/dev/work-done/analisi-offerta-commerciale-db)
> [analisi-pratiche-domini-anello3.md §6.9.3 — Pattern A idempotenza](/dev/work-in-progress/analisi-pratiche-domini-anello3)
> [Brief DB — successione contratti su overlap](/dev/work-done/brief-db-offerta-push-successione-contratto-overlap)

---

### 🎯 Scopo Principale

(rev6 2026-06-08 — guard **mutua esclusività** offerta→contratto/ordine; rev5 2026-06-01 — trasporto 1:1 stato approvazione prezzo anche sulle **righe**; rev4 2026-05-31 — successione contratti su overlap; rev3 2026-05-26 — copia `offerte_commerciali_eccezioni_componenti` → `contratti_righe_componenti`)

`vendite.fn_push_offerta_a_contratto(p_offerta_id, p_pratica_id, p_chiudi_contratto_esistente)`
genera un **contratto DRAFT** da un'offerta commerciale **ACCETTATA**, copiando
1:1 eccezioni e utility. La funzione è **idempotente per costruzione**: una
seconda invocazione sulla stessa offerta fallisce con errore semantico, senza
creare duplicati (pattern A §6.9.3 analisi pratiche domini).

Dalla rev4 il push è **consumatore del meccanismo generico di successione
contratti**: se per la stessa quintupla (`billing_account`, `istanza_utility`,
`utility`, `ambito`, periodo) esiste già un contratto attivo sovrapposto, il push
non lascia trapelare l'errore grezzo del vincolo di esclusione, ma lo gestisce in
modo esplicito (vedi *Successione su overlap*). La logica di rilevamento e
chiusura vive nelle funzioni di dominio
[`fn_contratto_sovrapposto`](/dbzero/vendite/funzioni/fn_contratto_sovrapposto) e
[`fn_chiudi_contratto_per_successione`](/dbzero/vendite/funzioni/fn_chiudi_contratto_per_successione);
il push aggiunge solo *lock*, *routing* e *rete di sicurezza*.

---

### Regole principali

- **Stato ammesso**: solo offerte in stato `ACCETTATA`. Qualsiasi altro stato
  (BOZZA, EMESSA, RIFIUTATA, SUPERATA, ANNULLATA) produce
  `E_OFFERTA_PUSH_STATO_NON_AMMESSO`.
- **Idempotenza**: se esiste già un contratto con `offerta_id = p_offerta_id`,
  la funzione fallisce con `E_OFFERTA_CONTRATTO_GIA_GENERATO` senza creare
  duplicati. La UNIQUE `uq_contratti_offerta_id` garantisce la protezione anche
  a livello strutturale.
- **Mutua esclusività contratto/ordine (rev6, 2026-06-08)**: se l'offerta ha
  già generato un **ordine** (`vendite.ordini` con `documento_origine_tipo =
  'OFFERTA' AND documento_origine_id = p_offerta_id`), il push fallisce con
  `E_OFFERTA_ORDINE_GIA_GENERATO`. Contratto e ordine sono **alternativi**:
  un'offerta ne genera al massimo uno. È lo specchio write-path del guard di
  capability [`fn_available_actions_offerta`](/dbzero/script/funzioni/fn_available_actions_offerta);
  il guard speculare lato ordine (impedire l'ordine se esiste un contratto) vive
  dal 2026-10-21 nel verbo gemello
  [`vendite.fn_genera_ordine_da_offerta`](/dbzero/vendite/funzioni/fn_genera_ordine_da_offerta)
  (prima nel BE `crea_ordine_da_offerta`), che blocca l'offerta `FOR UPDATE`.
  Non esiste un vincolo strutturale incrociato
  contratti↔ordini: la race cross-tab non è coperta (scelta esplicita,
  [brief §10](/dev/work-done/brief-db-univocita-offerta-ordine)).
- **Contratto creato in DRAFT**: l'auto-attivazione non è prevista in v1
  (§1.2 analisi). Il passaggio DRAFT → ATTIVO avviene separatamente.
- **Copia 1:1 (§5.2 analisi)**:
  - Testata: `billing_account_id`, `istanza_utility_id`, `utility_id`,
    `listino_id`, `listino_versione_id`, `valore/tipo_variazione_globale`,
    `valido_dal`/`valido_al` (da `offerta.validita_dal`/`al`), `meta`.
  - `emittente_fiscale_id` copiato 1:1 da `v_offerta.emittente_fiscale_id`
    (rev2, 2026-05-26). Il trigger di default dell'emittente (dal 2026-09-15
    `script.trgfn_default_emittente_fiscale`, prima la copia `trgfn_contratti_default_emittente`) salta
    (campo già valorizzato); il guard `script.trgfn_doc_guard_emittente_ba`
    valida la coerenza BA↔emittente.
- **Eccezioni → `contratti_righe`** + **componenti → `contratti_righe_componenti`**: il batch INSERT di eccezioni è stato convertito in un loop `FOR v_eccezione IN SELECT * FROM offerte_commerciali_eccezioni WHERE offerta_id = p_offerta_id ORDER BY id` che, per ogni eccezione, esegue:
  1. `INSERT INTO contratti_righe (...) RETURNING id INTO v_riga_id` — ottiene il PK della riga appena creata.
  2. `INSERT INTO contratti_righe_componenti (...) SELECT v_riga_id, occ.* FROM offerte_commerciali_eccezioni_componenti occ WHERE occ.eccezione_offerta_id = v_eccezione.id` — copia i componenti.
  - `stato_approvazione_prezzo` e `pratica_approvazione_prezzo_id` delle eccezioni copiati **1:1** su `contratti_righe` (rev5, 2026-06-01). Prima di rev5 venivano forzati a `NULL` perché la sorgente `offerte_commerciali_eccezioni` non aveva le colonne (aggiunte da `20260601-01`): l'approvazione L3 ottenuta in offerta viaggia ora fino al contratto senza riapprovazione (guida §6/§11.3).
  - `stato_approvazione_prezzo` e `pratica_approvazione_prezzo_id` dei **componenti** copiati **1:1** da `offerte_commerciali_eccezioni_componenti` (preservazione stato approvazione pre-negoziazione).
  - Il loop evita la necessità di correlare eccezione→riga_contratto tramite `ROW_NUMBER + INSERT RETURNING` (non ordinamento garantito).
- **Utility → `contratti_utilities`** (UPSERT): il trigger
  `trg_contratti_z90_snapshot_precontrattuali_ins` (AFTER INSERT su contratti)
  può aver già creato un record in `contratti_utilities` dai dati precontrattuali.
  La funzione usa `INSERT ... ON CONFLICT DO UPDATE` per sovrascrivere con i
  dati negoziati dell'offerta, che hanno precedenza sul precontrattuale generico.
- **`sorgente_tipo_id`** = id di `OFFERTA_COMMERCIALE` da `config.sorgenti`.
- **`sorgente_uid`** = `offerta.uid` (UUID).
- **`offerta_id`** valorizzato sul contratto: unico punto di lookup per
  idempotenza e tracciabilità della sorgente.
- **Collegamento pratica** (facoltativo): se `p_pratica_id IS NOT NULL`,
  inserisce in `pratiche.pratiche_sorgenti` il contratto generato come sorgente
  `CONTRATTO` con ruolo `COLLEGATO`. La registrazione dell'evento nel giornale
  pratica è delegata al livello applicativo (`pratiche_service.log_evento_dominio`).

---

### Successione su overlap (rev4)

Subito dopo le guard e prima dell'INSERT del contratto, il push:

1. **Advisory lock sulla quintupla** — `pg_advisory_xact_lock` su una chiave
   derivata da `billing_account_id : istanza_utility_id : utility_id : ambito`.
   Serializza i push concorrenti sullo **stesso** combo (due operatori non
   possono creare contratti sovrapposti nello stesso istante), **senza** bloccare
   l'intera tabella; il lock si rilascia a fine transazione.
2. **Rilevamento** — chiama
   [`fn_contratto_sovrapposto`](/dbzero/vendite/funzioni/fn_contratto_sovrapposto)
   con `ambito = 'COMMODITY'`. *Invariante*: l'INSERT del push non valorizza
   `ambito`, quindi il nuovo contratto assume il default `'COMMODITY'`; se un
   giorno il push valorizzasse `ambito`, va allineato anche il rilevamento.
3. **Routing**:
   - **A — nessun overlap**: comportamento standard, crea il contratto.
   - **B — overlap e `p_chiudi_contratto_esistente = false`** (default): solleva
     `E_CONTRATTO_OVERLAP_ESISTENTE` con il numero del contratto in conflitto.
     **Nessun contratto creato.** È il caso che il frontend usa per mostrare il
     conflitto e chiedere conferma.
   - **C — overlap e `p_chiudi_contratto_esistente = true`**: chiama
     [`fn_chiudi_contratto_per_successione`](/dbzero/vendite/funzioni/fn_chiudi_contratto_per_successione)
     (accorcia il vecchio a `validita_dal − 1`), poi crea il nuovo.
4. **Backstop** — l'INSERT in `contratti` è avvolto in
   `EXCEPTION WHEN exclusion_violation`: se il vincolo di esclusione scattasse
   comunque (gara sfuggita al lock, percorso futuro senza lock, conflitto residuo
   multi-overlap), l'errore grezzo viene **ritradotto** in
   `E_CONTRATTO_OVERLAP_ESISTENTE` parlante. Il client non vede mai l'errore GiST.

> La successione **accorcia** il contratto preesistente, non lo annulla, e **non**
> ne cambia lo stato: la cessazione `ATTIVO → CESSATO` la fa il job notturno
> `chiusura_scadenze_daily`.

---

### Ridondanza intenzionale `offerta_id` + `sorgente_uid`

`vendite.contratti` espone due chiavi di lookup verso la sorgente offerta:

| Colonna         | Tipo   | Scopo                                                      |
| --------------- | ------ | ---------------------------------------------------------- |
| `offerta_id`    | bigint | FK diretta + UNIQUE: idempotenza strutturale, JOIN veloce. |
| `sorgente_uid`  | UUID   | Pattern cross-dominio (§6.3 pratiche): lookup universale senza FK diretta (es. da pratiche_sorgenti che usa text). |

La ridondanza è intenzionale e documentata (O1 brief). `offerta_id` è la
chiave operativa; `sorgente_uid` è la chiave di integrazione cross-dominio.

---

### Parametri

| Parametro      | Tipo     | Note                                                                  |
| -------------- | -------- | --------------------------------------------------------------------- |
| `p_offerta_id` | `bigint` | ID offerta commerciale ACCETTATA. Obbligatorio, > 0.                  |
| `p_pratica_id` | `bigint` | ID pratica da collegare al contratto. Opzionale — `NULL` ammesso.     |
| `p_chiudi_contratto_esistente` | `boolean` | Default `false`. Se `true` e c'è un contratto sovrapposto, lo chiude per successione e poi crea il nuovo; se `false`, su overlap solleva `E_CONTRATTO_OVERLAP_ESISTENTE` senza creare nulla. |

---

### 📦 Output

| Campo           | Tipo     | Descrizione                          |
| --------------- | -------- | ------------------------------------ |
| `RETURNS BIGINT` | bigint  | ID del contratto DRAFT generato.     |

---

### Codici errore

| Codice                              | Quando                                                            |
| ----------------------------------- | ----------------------------------------------------------------- |
| `E_PARAMETRO_INVALIDO`              | `p_offerta_id` NULL o <= 0; offerta non trovata.                  |
| `E_OFFERTA_PUSH_STATO_NON_AMMESSO`  | Stato offerta diverso da `ACCETTATA`.                             |
| `E_OFFERTA_CONTRATTO_GIA_GENERATO`  | Esiste già un contratto con `offerta_id = p_offerta_id`.          |
| `E_OFFERTA_ORDINE_GIA_GENERATO`     | Esiste già un ordine generato dall'offerta (`documento_origine ('OFFERTA', p_offerta_id)`) — mutua esclusività contratto/ordine (rev6). |
| `E_CONTRATTO_OVERLAP_ESISTENTE`     | Esiste un contratto attivo sovrapposto e `p_chiudi_contratto_esistente = false` (caso B), oppure conflitto residuo intercettato dal backstop. |
| `E_CONFIG_MANCANTE`                 | `DRAFT` non trovato in `stati_doc_contratti`; `OFFERTA_COMMERCIALE` o `CONTRATTO` non trovati in `config.sorgenti`. |

---

### Interazione con i trigger di `contratti`

La sequenza di eventi al momento dell'INSERT del contratto:

```text
fn_push_offerta_a_contratto
  └─ pg_advisory_xact_lock(quintupla)            → serializza push concorrenti
  └─ fn_contratto_sovrapposto(...)               → rilevamento overlap (routing A/B/C)
  └─ [caso C] fn_chiudi_contratto_per_successione → accorcia il vecchio
  └─ INSERT contratti (DRAFT, emittente_fiscale_id = v_offerta.emittente_fiscale_id)
       │  (avvolto in EXCEPTION WHEN exclusion_violation → backstop E_CONTRATTO_OVERLAP_ESISTENTE)
       ├─ BEFORE INSERT: trg_contratti_a10_default_emittente_ins (script.trgfn_default_emittente_fiscale) → SKIP (già valorizzato)
       ├─ BEFORE INSERT: script.trgfn_doc_guard_emittente_ba → valida coerenza BA↔EF
       ├─ BEFORE INSERT: trgfn_contratti_gen_codice         → assegna numero contratto
       ├─ BEFORE INSERT: trgfn_contratti_normalize          → default ambito/campi
       ├─ BEFORE INSERT: trgfn_contratti_set_categoria_cliente_snapshot
       └─ AFTER INSERT:  trg_contratti_z90_snapshot_precontrattuali_ins
                           └─ crea contratti_utilities dai precontrattuali
                                (se non esiste già — idempotente)
  └─ FOR EACH eccezione IN offerte_commerciali_eccezioni ORDER BY id:
       ├─ INSERT contratti_righe (...) RETURNING id INTO v_riga_id
       │    └─ trigger righe: guard aggiunta, default fonte_qta, ecc.
       └─ INSERT contratti_righe_componenti SELECT v_riga_id, occ.*
            FROM offerte_commerciali_eccezioni_componenti
            WHERE eccezione_offerta_id = v_eccezione.id
  └─ UPSERT contratti_utilities (da offerte_commerciali_utilities)
       └─ ON CONFLICT DO UPDATE → sovrascrive il record creato dal trigger
          precontrattuali con i dati negoziati dell'offerta
  └─ [se p_pratica_id NOT NULL] INSERT pratiche.pratiche_sorgenti
```

---

### Esempio d'uso

```sql
-- Push offerta 42 (ACCETTATA) senza pratica collegata.
-- p_chiudi_contratto_esistente omesso = false (default).
SELECT vendite.fn_push_offerta_a_contratto(42, NULL);
-- Restituisce: 101  (id del nuovo contratto DRAFT)

-- Push con collegamento pratica 7
SELECT vendite.fn_push_offerta_a_contratto(42, 7);
-- Stessa offerta: fallisce con E_OFFERTA_CONTRATTO_GIA_GENERATO (idempotenza)

-- Offerta 55 sovrapposta a un contratto esistente, senza conferma:
SELECT vendite.fn_push_offerta_a_contratto(55, NULL, false);
-- Fallisce con E_CONTRATTO_OVERLAP_ESISTENTE (mostra il contratto in conflitto).

-- Stessa offerta 55 con conferma di successione:
SELECT vendite.fn_push_offerta_a_contratto(55, NULL, true);
-- Accorcia il contratto esistente e crea il nuovo DRAFT. Restituisce il nuovo id.
```

---

{% include-markdown "signature-core.md" %}
