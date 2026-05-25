## 📘 Documentazione Concettuale – Funzione `vendite.fn_push_offerta_a_contratto(...)`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
> [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali)
> [vendite.offerte_commerciali_eccezioni](/dbzero/vendite/tabelle/offerte_commerciali_eccezioni)
> [vendite.offerte_commerciali_utilities](/dbzero/vendite/tabelle/offerte_commerciali_utilities)
> [vendite.contratti](/dbzero/vendite/tabelle/contratti)
> [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe)
> [vendite.contratti_utilities](/dbzero/vendite/tabelle/contratti_utilities)
> [config.sorgenti](/dbzero/config/tabelle/sorgenti)
> [pratiche.pratiche_sorgenti](/dbzero/pratiche/tabelle/pratiche_sorgenti)
>
> Trigger correlati:
> [vendite.trgfn_contratti_snapshot_precontrattuali](/dbzero/vendite/funzioni/trgfn_contratti_snapshot_precontrattuali)
>
> Funzioni correlate:
> [vendite.fn_crea_revisione_offerta](/dbzero/vendite/funzioni/fn_crea_revisione_offerta)
>
> Contesto di sviluppo:
> [Brief DB offerte commerciali — Step 8](/dev/work-in-progress/analisi-offerta-commerciale-db)
> [analisi-pratiche-domini-anello3.md §6.9.3 — Pattern A idempotenza](/dev/work-in-progress/analisi-pratiche-domini-anello3)

---

### 🎯 Scopo Principale

(rev 2026-05-25)

`vendite.fn_push_offerta_a_contratto(p_offerta_id, p_pratica_id)` genera un
**contratto DRAFT** da un'offerta commerciale **ACCETTATA**, copiando 1:1
eccezioni e utility. La funzione è **idempotente per costruzione**: una seconda
invocazione sulla stessa offerta fallisce con errore semantico, senza creare
duplicati (pattern A §6.9.3 analisi pratiche domini).

---

### Regole principali

- **Stato ammesso**: solo offerte in stato `ACCETTATA`. Qualsiasi altro stato
  (BOZZA, EMESSA, RIFIUTATA, SUPERATA, ANNULLATA) produce
  `E_OFFERTA_PUSH_STATO_NON_AMMESSO`.
- **Idempotenza**: se esiste già un contratto con `offerta_id = p_offerta_id`,
  la funzione fallisce con `E_OFFERTA_CONTRATTO_GIA_GENERATO` senza creare
  duplicati. La UNIQUE `uq_contratti_offerta_id` garantisce la protezione anche
  a livello strutturale.
- **Contratto creato in DRAFT**: l'auto-attivazione non è prevista in v1
  (§1.2 analisi). Il passaggio DRAFT → ATTIVO avviene separatamente.
- **Copia 1:1 (§5.2 analisi)**:
  - Testata: `billing_account_id`, `istanza_utility_id`, `utility_id`,
    `listino_id`, `listino_versione_id`, `valore/tipo_variazione_globale`,
    `valido_dal`/`valido_al` (da `offerta.validita_dal`/`al`), `meta`.
  - `emittente_fiscale_id` non copiato: non esiste su `vendite.contratti`
    (verificato 2026-05-25).
- **Eccezioni → `contratti_righe`**: copia 1:1 di tutte le righe
  (`offerte_commerciali_eccezioni`). `stato_approvazione_prezzo` e
  `pratica_approvazione_prezzo_id` inseriti `NULL` (I4 del brief: il contratto
  DRAFT li acquisisce in fase di negoziazione interna).
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
| `E_CONFIG_MANCANTE`                 | `DRAFT` non trovato in `stati_doc_contratti`; `OFFERTA_COMMERCIALE` o `CONTRATTO` non trovati in `config.sorgenti`. |

---

### Interazione con i trigger di `contratti`

La sequenza di eventi al momento dell'INSERT del contratto:

```text
fn_push_offerta_a_contratto
  └─ INSERT contratti (DRAFT)
       ├─ BEFORE INSERT: trgfn_contratti_gen_codice → assegna numero contratto
       ├─ BEFORE INSERT: trgfn_contratti_normalize → default ambito/campi
       ├─ BEFORE INSERT: trgfn_contratti_set_categoria_cliente_snapshot
       └─ AFTER INSERT:  trg_contratti_z90_snapshot_precontrattuali_ins
                           └─ crea contratti_utilities dai precontrattuali
                                (se non esiste già — idempotente)
  └─ INSERT contratti_righe (da offerte_commerciali_eccezioni)
       └─ trigger righe: guard aggiunta, default fonte_qta, ecc.
  └─ UPSERT contratti_utilities (da offerte_commerciali_utilities)
       └─ ON CONFLICT DO UPDATE → sovrascrive il record creato dal trigger
          precontrattuali con i dati negoziati dell'offerta
  └─ [se p_pratica_id NOT NULL] INSERT pratiche.pratiche_sorgenti
```

---

### Esempio d'uso

```sql
-- Push offerta 42 (ACCETTATA) senza pratica collegata
SELECT vendite.fn_push_offerta_a_contratto(42, NULL);
-- Restituisce: 101  (id del nuovo contratto DRAFT)

-- Push con collegamento pratica 7
SELECT vendite.fn_push_offerta_a_contratto(42, 7);
-- Stessa offerta: fallisce con E_OFFERTA_CONTRATTO_GIA_GENERATO (idempotenza)
```

---

{% include-markdown "signature-core.md" %}
