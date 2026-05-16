# Brief DB — Refactor contratti (cascata parametri + modello unificato)

> **Stato**: IN CORSO — `dev/db-tid` (2026-05-15).
> Fase 1 ✅. Fase 2: Step 2.0–2.6 ✅ — **COMPLETATA**.
>
> **Workstream BE+DOC Fase 1 chiusi (2026-05-15)** su `dev/backend-tid`:
> ParameterService cascata estesa, `BillingAccountRepository.get_categoria_cliente_id`,
> `_check_limite_variazione_prezzo` con lookup BA post-early-return,
> `PricingLimitiUtenteView` con query param `billing_account_id`,
> doc `api_preventivi.md` + `api_pricing.md` + catalogo BB aggiornati. 2393/2393 test verdi.
> Resta FE 1.1 (banner soglia per categoria). Procede BE Fase 2 (contratti).
>
> | Step | Migration | pgTAP | Stato |
> |---|---|---|---|
> | 1.1 `config.parameter_overrides` + `categoria_cliente_id` | 20260515-06, -07 | test-parameter-overrides-categoria-cliente-v1 12/12 | ✅ |
> | 1.2 `fn_get_parameter_full` 7 param | 20260515-08 | test-fn-get-parameter-full-categoria-cliente-v1 9/9 | ✅ |
> | 1.3 Doc DB | — | — | ✅ |
> | 2.0 TRUNCATE contratti dev reset | 20260515-09 | — | ✅ |
> | 2.1 `contratti.listino_versione_id` + drop modalità A/B/C | 20260515-10 | test-contratti-schema-step21-v1 10/10 | ✅ |
> | 2.2 `contratti_righe.tipo_eccezione` ENUM + CHECK + UNIQUE + guard AGGIUNTA | 20260515-11, -12 | test-contratti-schema-step22-v1 17/17 | ✅ |
> | 2.3 Freeze `listino_versione_id` + lock post-attivazione testata + righe | 20260515-13, -14 | test-contratti-step23-v1 13/13 | ✅ |
> | 2.4 `fn_resolve_prezzo_listino_v2` (DROP + ricreare con 3 tipi eccezione) | 20260515-15 | test-fn-resolve-prezzo-listino-v2-step24-v1 9/9 | ✅ |
> | 2.5 Drop parameter `VENDITE_CONTRATTO_DEFAULT_MODALITA` | 20260515-16 (80_data) | — | ✅ |
> | 2.6 Doc DB | — | — | ✅ |
>
> **Origine**: decisioni chiuse in
> [`refactor-contratti-modalita.md`](refactor-contratti-modalita.md) §3 e §3-bis.
>
> **Strategia**: due fasi sequenziali, ognuna applicabile in PR separata
> (§3-bis-D del refactor). Ogni fase è suddivisa in **step incrementali**: alla
> chiusura di ogni step (DDL + pgTAP verde) il backend agent può iniziare le
> attività BE/FE che dipendono solo da quello step, senza aspettare il
> completamento dell'intera fase.
>
> **Convenzioni**: Liquibase 5 / PostgreSQL 18. Naming changeSet
> `YYYYMMDD-NN-<tipo>-<descrizione>.yaml` in `db/changelog/migrations_v2/`.
> Trigger naming `trg_<schema>_<tabella>_<fase>_<descrizione>_<eventi>` per
> [`linee-guida-trigger.md`](../../../linee-guida-trigger.md). Errori sempre
> via `script.fn_log_and_raise_error`.

---

## FASE 1 — Estensione cascata parametri con `categoria_cliente_id` ✅ COMPLETATA

### Scopo

Estendere `script.fn_get_parameter_full` perché la cascata di risoluzione di un parametro
soglia (es. `VENDITE_MAX_SCONTO_PCT`) tenga conto della **categoria cliente** del
billing account destinatario, oltre alle dimensioni esistenti.

Cascata attuale (vedi `script.fn_get_parameter_full`):

```
user → group → emittente → session → function → default
```

Cascata target:

```
user → categoria_cliente → group → emittente → session → function → default
```

Motivazione: la regola commerciale ("categoria PREMIUM ha max sconto 5%") deve vincere sul
seniority dell'operatore. Eccezioni per singoli senior si configurano come override a
livello `user` (livello più alto della cascata).

### Step 1.1 — Schema `config.parameter_overrides` ✅

**Modifica**:

- Nuova colonna `categoria_cliente_id smallint NULL` su `config.parameter_overrides`
- FK a `anagrafiche.categorie_clienti(id)`, naming `fk_overrides_categoria_cliente`
- Indice `ix_overrides_param_categoria_cliente` su `(parameter_id, categoria_cliente_id)`
  per supportare la lookup della cascata
- Aggiornare UNIQUE `uq_overrides_full_scope_v3` → nuovo nome `uq_overrides_full_scope_v4`
  che include `categoria_cliente_id` fra le colonne di unicità (la `v3` va droppata):
  `(parameter_id, emittente_fiscale_id, django_user_id, django_group_id,
   categoria_cliente_id, session_key, function_name)`
- Aggiornare `dbops.fk_index_policy` se non automatico (registrare la nuova FK)

**Note**:

- `categoria_cliente_id` è `smallint` per allinearsi al tipo già in uso su
  `billing_account.categoria_cliente_id` e `contratti.categoria_cliente_id_snapshot`
- Trigger esistenti (`trgfn_parameter_overrides_fk_surrogate_dispatch`,
  `trgfn_storico_generic`, `trgfn_audit_data_user_generic`,
  `trgfn_child_requires_active_parent` su emittenti) restano invariati
- Va aggiunto un nuovo trigger `trg_parameter_overrides_a10_cat_clienti_req_attivo_ins_upd`
  con `dbops.trgfn_child_requires_active_parent('anagrafiche', 'categorie_clienti', 'attivo',
  'categoria_cliente_id', 'id')` per coerenza con il pattern già adottato sull'emittente.
  Nome abbreviato deliberatamente: il nome completo supererebbe i 63 caratteri di PostgreSQL
  (stesso motivo dell'hash nel trigger analogo su emittenti_fiscali)

**pgTAP**:

- Esistenza colonna + tipo + nullable
- Esistenza FK con ON UPDATE/DELETE policy
- Esistenza indice
- Vincolo UNIQUE v4 attivo, v3 droppato
- Trigger guard "categoria attiva" presente

**Chiusura step 1.1 → nessun workstream BE/FE abilitato**
(serve almeno anche lo step 1.2 perché la fn risolutore usi la colonna)

---

### Step 1.2 — Nuovo signature `script.fn_get_parameter_full` ✅

**Modifica** (file con `runOnChange: true` o nuovo file numerato):

Nuovo signature, parametro aggiunto **in coda** (backward compatible: tutti i
caller posizionali esistenti continuano a funzionare con DEFAULT NULL):

```sql
CREATE OR REPLACE FUNCTION script.fn_get_parameter_full(
    p_code text,
    p_emittente_fiscale_id bigint DEFAULT NULL,
    p_django_user_id integer DEFAULT NULL,
    p_group_ids integer[] DEFAULT NULL,
    p_session_key text DEFAULT NULL,
    p_function_name text DEFAULT NULL,
    p_categoria_cliente_id smallint DEFAULT NULL  -- NUOVO, in coda
) RETURNS text ...
```

**Logica cascata** (5 livelli + 2 esistenti + default):

```
COALESCE(
  -- 1. user
  (SELECT overridden_value WHERE django_user_id = p_django_user_id),
  -- 2. categoria_cliente  (NUOVO)
  (SELECT overridden_value WHERE categoria_cliente_id = p_categoria_cliente_id),
  -- 3. group
  (SELECT overridden_value WHERE django_group_id = ANY(p_group_ids)),
  -- 4. emittente
  (SELECT overridden_value WHERE emittente_fiscale_id = p_emittente_fiscale_id),
  -- 5. session
  (SELECT overridden_value WHERE session_key = p_session_key),
  -- 6. function
  (SELECT overridden_value WHERE function_name = p_function_name),
  -- 7. default
  default_value
)
```

**Note**:

- Tutte le sotto-query vanno scoped per `parameter_id = v_param_id AND attivo = TRUE`
  come oggi
- Aggiornare il `COMMENT ON FUNCTION` per dichiarare la nuova cascata
- Verificare se esistono altri caller della fn (oltre `ParameterService` Python) che
  potrebbero rompersi con il signature change. Se la fn è chiamata con argomenti
  posizionali in qualche SQL, sostituire con keyword args
- **Decisione di compatibilità**: nessuna funzione wrapper di compatibilità — chiamanti
  passano `NULL` per `p_categoria_cliente_id` se non hanno la dimensione

**pgTAP — tutti i 7 percorsi della cascata**:

1. Test "user vince su tutto": override su user + override su categoria → ritorna user
2. Test "categoria vince su group": override su categoria + override su group → ritorna
   categoria (CASO CHIAVE del refactor)
3. Test "group vince su emittente": override su group + override su emittente → ritorna
   group
4. Test "emittente vince su session": override su emittente + session → ritorna emittente
5. Test "session vince su function": override su session + function → ritorna session
6. Test "function vince su default": override su function → ritorna function
7. Test "fallback default": nessun override → ritorna default_value
8. Test "categoria_cliente NULL skippa il livello": p_categoria_cliente_id=NULL → cerca da
   group in poi (lookup non scatta su categoria)
9. Test "parametro inesistente solleva ERRORE_PARAMETRI_TABELLA"

**Chiusura step 1.2 → abilita workstream**:

- ✅ **BE preventivi step 1.1**: `preventivi_service` può chiamare la nuova fn passando
  `categoria_cliente_id` recuperato dal BA
- ✅ **BE contratti step 2.2**: i 3 gate prezzo dei contratti possono usare la cascata
  estesa (non dipende da DB Fase 2)

---

### Step 1.3 — Documentazione DB ✅

**Modifica**:

- Aggiornare `docs/it/dbzero/script/manual/fn_get_parameter_full.md` con nuova signature +
  cascata
- Aggiornare `docs/it/dbzero/config/manual/parameter_overrides.md` con nuova colonna +
  esempio d'uso

**Chiusura step 1.3 → chiude Fase 1**.

---

## FASE 2 — Refactor contratti unificato

### Scopo

Eliminare la classificazione A/B/C delle modalità contratto e adottare:

- Modello unificato "con listino / senza listino" (forma derivata, non più scelta utente)
- Righe come **eccezioni del listino** (`tipo_eccezione` enum: OVERRIDE/ESCLUSIONE/AGGIUNTA)
- Snapshot della **versione listino** all'attivazione (decisione §3-bis-A)
- Cleanup dei vincoli CHECK e trigger che enforcono le modalità

**Prerequisito**: Fase 1 chiusa (il refactor contratti usa la cascata estesa nei 3 gate
prezzo).

### Step 2.0 — Reset dati contratti (sviluppo) ✅

**Modifica** (decisione §3.8 — schema pulito, no backward compat):

Primo changeSet della Fase 2, eseguito **prima** di qualsiasi DDL, per evitare
conflitti con colonne NOT NULL senza default su dati pre-esistenti. Ambiente
sviluppo/test, nessun dato da preservare.

```sql
TRUNCATE vendite.contratti_righe_componenti,
         vendite.contratti_righe,
         vendite.contratti_utilities,
         vendite.contratti
  RESTART IDENTITY CASCADE;
```

**pgTAP**: nessun test dedicato — lo step è prerequisito operativo, non logica.

**Chiusura step 2.0 → nessun workstream abilitato** (solo prerequisito DDL).

---

### Step 2.1 — Schema `vendite.contratti`: versione listino + cleanup modalità ✅

**Modifica**:

- Nuova colonna `listino_versione_id bigint NULL` su `vendite.contratti`
  - FK a `vendite.listini_versioni(id)`, naming `fk_contratti_listino_versione`
  - Indice `ix_contratti_listino_versione`
- **Drop** dei CHECK constraint legati alla modalità:
  - `chk_contratti_modalita_pricing` → drop
  - `chk_contratti_variazione_globale_coerente` → drop (era il vincolo che impediva
    coesistenza variazione + override; ora rilassato)
  - `chk_contratti_tipo_variazione_globale` → resta (vincola i valori validi del campo,
    indipendente da modalità)
- **Drop** dei trigger legati alla modalità:
  - `trg_contratti_a10_guard_modalita_c_activation_ins_upd` → drop (era il guard che
    bloccava attivazione modalità C senza righe; vedi step 2.4 per logica sostitutiva)
  - `trg_contratti_righe_a10_guard_modalita_c_ins_upd` → drop (era il guard sulle righe
    per la modalità C; ora le righe sono eccezioni, regole diverse)

**Note**:

- `listino_versione_id` resta NULL durante DRAFT (il contratto segue la versione corrente
  del listino)
- Il vincolo "listino_versione_id NOT NULL post-attivazione" è enforced da trigger (step
  2.3), non da CHECK declarativo, perché dipende dallo stato del contratto

**pgTAP**:

- Esistenza colonna + tipo + nullable + FK
- Drop dei CHECK e trigger sopra elencati confermato
- Inserimento contratto DRAFT con `listino_versione_id=NULL` → ok
- Inserimento contratto DRAFT con listino_id + tipo_variazione_globale + variazione →
  ok (era bloccato dal vecchio CHECK)

**Chiusura step 2.1 → abilita workstream**:

- ✅ **BE contratti step 2.1**: rimuovere la logica gating modalità in
  `contratti_service.py` (`_validate_modalita_coerente`)
- ✅ **FE contratti step 2.1**: rimuovere SelectButton modalità A/B/C in `ContrattoDrawer.vue`

---

### Step 2.2 — Schema `vendite.contratti_righe`: tipo eccezione

**Modifica**:

- Nuovo ENUM o `varchar` + CHECK per `tipo_eccezione`:
  - Valori: `OVERRIDE`, `ESCLUSIONE`, `AGGIUNTA`
  - Suggerito: enum PostgreSQL `vendite.tipo_eccezione_contratto` per type safety
- Nuova colonna `tipo_eccezione vendite.tipo_eccezione_contratto NOT NULL` su
  `vendite.contratti_righe`
- CHECK `chk_contrighe_prezzo_per_tipo_eccezione`:
  - `prezzo_unitario IS NULL` se `tipo_eccezione = 'ESCLUSIONE'`
  - `prezzo_unitario IS NOT NULL` se `tipo_eccezione IN ('OVERRIDE', 'AGGIUNTA')`
- Constraint univocità parziale `uq_contrighe_one_eccezione_per_articolo`:
  - `CREATE UNIQUE INDEX ... ON vendite.contratti_righe (contratto_id, articolo_id)
    WHERE tipo_eccezione IN ('OVERRIDE', 'ESCLUSIONE')`
  - Non vincola AGGIUNTA (un articolo fuori-listino può apparire una sola volta come
    AGGIUNTA — ma fra OVERRIDE e ESCLUSIONE vince comunque l'unicità)
- Constraint univocità parziale `uq_contrighe_one_aggiunta_per_articolo`:
  - `CREATE UNIQUE INDEX ... ON vendite.contratti_righe (contratto_id, articolo_id)
    WHERE tipo_eccezione = 'AGGIUNTA'`
  - Cioè 1 AGGIUNTA al massimo per stessa coppia
- Nuovo trigger `trg_contratti_righe_a10_guard_aggiunta_fuori_listino_ins_upd`:
  - Scatta solo se `NEW.tipo_eccezione = 'AGGIUNTA'`
  - Legge `contratto.listino_id` e `contratto.listino_versione_id` via JOIN su
    `vendite.contratti` (contratto padre di `NEW.contratto_id`)
  - **Branch 1 — `listino_id IS NULL`**: nessun listino di riferimento → AGGIUNTA sempre
    valida, trigger esce con `RETURN NEW` senza check
  - **Branch 2 — `listino_id NOT NULL` e `listino_versione_id IS NULL`** (contratto DRAFT):
    cerca l'articolo nella versione attiva alla `CURRENT_DATE` del listino
    (`listini_versioni WHERE listino_id = ... AND validita @> CURRENT_DATE AND attivo`)
  - **Branch 3 — `listino_id NOT NULL` e `listino_versione_id IS NOT NULL`** (contratto ATTIVO):
    cerca l'articolo nella versione fissata (`listini_righe WHERE listino_versione_id = ...`)
  - Se l'articolo è trovato in qualsiasi dei Branch 2/3 → raise
    `E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO` (l'operatore avrebbe dovuto usare OVERRIDE)

**Note**:

- Il `tipo_eccezione` è un'informazione strutturale, non derivata: l'operatore (via UI)
  o il service backend la inserisce esplicitamente
- Articolo composito (`is_composito=TRUE`): il padre vive in `contratti_righe` come
  AGGIUNTA o OVERRIDE; i figli stanno in `contratti_righe_componenti` (non interessati
  dal `tipo_eccezione`, hanno la loro logica già esistente)

**pgTAP**:

- Enum / CHECK presente con i 3 valori
- INSERT con prezzo NULL + ESCLUSIONE → ok
- INSERT con prezzo NOT NULL + ESCLUSIONE → fallisce
- INSERT con prezzo NULL + OVERRIDE → fallisce
- INSERT due OVERRIDE stessa (contratto, articolo) → fallisce su unicità
- INSERT un OVERRIDE + un'ESCLUSIONE stessa (contratto, articolo) → fallisce su unicità
- INSERT AGGIUNTA su contratto senza listino (`listino_id NULL`) → ok (nessun check)
- INSERT AGGIUNTA per articolo presente nel listino (contratto DRAFT, versione corrente) → fallisce su guard
- INSERT AGGIUNTA per articolo fuori listino (contratto DRAFT) → ok
- INSERT AGGIUNTA per articolo presente nella versione fissata (contratto ATTIVO) → fallisce su guard
- INSERT AGGIUNTA per articolo fuori dalla versione fissata (contratto ATTIVO) → ok

**Note implementazione (2026-05-15)**:

- Migration split: `20260515-11` (DDL schema) + `20260515-12` (trigger function + trigger)
- Seed CSV: tutti e 5 i codici errore (450-454) seedati in questo step in `messaggi_errore.csv` (non distribuiti tra i vari step come implicito nel piano)
- Il trigger usa `WHEN (NEW.tipo_eccezione = 'AGGIUNTA')` per efficienza — non scatta per OVERRIDE/ESCLUSIONE
- Fixture pgTAP richiedeva `qta_operativa` in tutti gli INSERT (trigger `trgfn_qta_from_operativa` BEFORE INSERT lo richiede NOT NULL)

**Chiusura step 2.2 → abilita workstream**:

- ✅ **BE contratti step 2.3**: implementare logica gestione 3 tipi eccezione in
  `contratti_service.py` (`list_righe_preview`, `aggiungi_eccezione`, `rimuovi_eccezione`)
- ✅ **BE contratti step 2.4**: implementare blocco rimozione listino con eccezioni
  OVERRIDE/ESCLUSIONE (422 `E_CONTRATTO_LISTINO_RIMOZIONE_CON_ECCEZIONI`)
- ✅ **FE contratti step 2.3**: azioni di riga "Modifica prezzo" / "Escludi" /
  "Aggiungi articolo" in `ContrattoRigheDrawer.vue`

---

### Step 2.3 — Trigger attivazione: fissa `listino_versione_id`

**Modifica**:

Nuovo trigger `trg_contratti_a10_freeze_listino_versione_ins_upd`:

- BEFORE UPDATE OF `stato_doc_contratto_id`
- Logica:
  - Se la transizione è DRAFT → ATTIVO (vecchio stato_codice_interno = 'DRAFT', nuovo =
    'ATTIVO') E `listino_id IS NOT NULL` E `listino_versione_id IS NULL` →
    SELECT la versione attiva alla data del contratto + assegnala a
    NEW.listino_versione_id
  - Se la versione attiva non esiste (caso §4.4 listino senza versione attiva alla data):
    consenti comunque l'attivazione, `listino_versione_id` resta NULL → la UI mostrerà
    warning "listino senza versione" come da §4.4
  - Se `listino_id IS NULL` (contratto senza listino, ex-modalità C): `listino_versione_id`
    resta NULL — nessun snapshot da fissare
- Errore se la transizione DRAFT → ATTIVO è fatta con `listino_id IS NULL` E NON esistono
  righe AGGIUNTA con `prezzo_unitario` valorizzato → solleva
  `E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE` (sostituisce il vecchio guard `modalita_c`)

**Trigger di lock post-attivazione sulla testata**:

Nuovo trigger `trg_contratti_a10_lock_post_attivazione_upd`:

- BEFORE UPDATE OF `listino_id, listino_versione_id, tipo_variazione_globale,
  valore_variazione_globale`
- Se vecchio stato = 'ATTIVO' → solleva
  `E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE` (Profilo A §3-bis-A)
- `UPDATE OF` su colonne specifiche per non scattare su aggiornamenti di `meta`,
  `data_update` e altri campi non bloccati

**Trigger di lock eccezioni post-attivazione su `contratti_righe`**:

Nuovo trigger `trg_contratti_righe_a10_lock_post_attivazione_ins_upd_dlt`:

- BEFORE INSERT OR UPDATE OR DELETE
- Logica: legge `stato_codice_interno` del contratto padre tramite JOIN su
  `vendite.contratti` + `config.stati_doc_contratti`
- Se stato padre = 'ATTIVO' → solleva `E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE`
  con contesto `{contratto_id, articolo_id, operazione}`
- Motivazione: enforcement DB-first coerente con §3-bis-A ("né le eccezioni");
  garantisce il blocco anche da psql diretto, non solo via service

**pgTAP**:

- Transizione DRAFT → ATTIVO con listino + listino_versione_id NULL → versione fissata
- Transizione DRAFT → ATTIVO senza listino + senza righe AGGIUNTA → errore
- Transizione DRAFT → ATTIVO senza listino + con righe AGGIUNTA prezzo valorizzato → ok
- UPDATE listino_id su contratto ATTIVO → bloccato
- UPDATE valore_variazione_globale su contratto ATTIVO → bloccato
- UPDATE valore_variazione_globale su contratto DRAFT → ok
- INSERT eccezione su contratto ATTIVO → bloccato (trigger righe)
- UPDATE eccezione su contratto ATTIVO → bloccato (trigger righe)
- DELETE eccezione su contratto ATTIVO → bloccato (trigger righe)
- INSERT eccezione su contratto DRAFT → ok

**Note implementazione (2026-05-15)**:

- Nome trigger freeze: `trg_contratti_a10_freeze_listino_versione_upd` (solo BEFORE UPDATE, non INSERT+UPDATE come indicato nel piano — non necessario l'INSERT)
- Migration split: `20260515-13` (freeze + guard negoziato puro) + `20260515-14` (lock testata + lock righe)
- Ordine lessicografico confermato: `freeze` scatta PRIMA di `guard_transizione_stato` — se freeze raise, il guard non esegue
- Il trigger freeze NON causa il firing del lock testata (il lock è su UPDATE OF colonne specifiche, non scatta su trigger-internal modifications di NEW)
- Il trigger lock righe gestisce correttamente DELETE con `RETURN OLD`

**Chiusura step 2.3 → abilita workstream**:

- ✅ **BE contratti step 2.5**: aggiornare la logica di attivazione contratto in
  `contratti_service.py` per intercettare i nuovi errori e mappare codici/HTTP corretti
- ✅ **FE contratti step 2.4**: handling 403/422 nei vari drawer

---

### Step 2.4 — Aggiornamento `fn_resolve_prezzo_listino_v2`

**Modifica**:

Riscrivere lo STADIO 1 (CONTRATTO) della funzione per:

1. **Leggere `listino_versione_id` dal contratto se il contratto è ATTIVO**:
   - Se `listino_versione_id IS NOT NULL` → lookup riga listino con
     `listino_righe.listino_versione_id = <fissato>`
   - Se `listino_versione_id IS NULL` (contratto DRAFT) → lookup versione attiva alla
     data, come oggi
2. **Gestire i 3 tipi di eccezione**:
   - SELECT su `contratti_righe` aggiunto `tipo_eccezione` nella proiezione
   - Se trovata eccezione OVERRIDE → ritorna prezzo override, origine
     `CONTRATTO_OVERRIDE`
   - Se trovata eccezione ESCLUSIONE → solleva `E_ARTICOLO_ESCLUSO_DA_CONTRATTO` con
     contesto (articolo, contratto)
   - Se trovata eccezione AGGIUNTA → ritorna prezzo AGGIUNTA, origine
     `CONTRATTO_AGGIUNTA`
   - Nessuna eccezione → procede a leggere listino con eventuale variazione globale
     (logica attuale del ramo "stadio 1b")

**Modifica al COMMENT**: aggiornare con la nuova logica 3-tipi.

**Modifica colonna OUT**: aggiungere `tipo_eccezione vendite.tipo_eccezione_contratto`
nella TABLE return (utile per banner/badge FE e audit).

**⚠️ Nota operativa obbligatoria — DROP prima del CREATE**: PostgreSQL non permette
`CREATE OR REPLACE FUNCTION` se cambiano le colonne di `RETURNS TABLE`. Il changeSet
Liquibase deve includere il DROP esplicito prima del CREATE.

**Note implementazione (2026-05-15)**:

- **Deviazione critica**: la funzione aveva già **8 parametri** (non 7 come indicato nel piano). La versione bundle-prioritario (migration `20260513-35`) aveva aggiunto `p_articolo_padre_contesto catalogo.articoli.id%TYPE DEFAULT NULL`. Il piano citava solo 7 parametri perché basato su un'istantanea precedente.
- Il DROP usa un **DO-block** che pulisce tutti gli overload (non un DROP statico per firma), perché il %TYPE aveva risolto a tipi diversi tra le versioni creando più overload in conflitto.
- La migration `20260515-15` incorpora tutta la logica bundle-prioritario (STADIO BUNDLE, Step 1b-1/1b-2/1b-3, Step 2-1/2-2/2-3) + le modifiche Step 2.4.
- Il Python `pricing_repository.py` seleziona colonne per nome (`r.prezzo_finale`, ecc.) — l'aggiunta di `tipo_eccezione` in RETURNS TABLE non rompe il codice BE esistente.
- STADIO 1b versione fissata: se `v_contr_listino_versione_id IS NOT NULL`, la versione è usata direttamente (senza query su `listini_versioni`). Questo si integra con il BUNDLE: il lookup bundle usa `v_listino_versione_id` già valorizzato.

**pgTAP**:

- Resolver con contratto ATTIVO + OVERRIDE → ritorna prezzo override
- Resolver con contratto ATTIVO + ESCLUSIONE → errore
- Resolver con contratto ATTIVO + AGGIUNTA → ritorna prezzo aggiunta
- Resolver con contratto ATTIVO + nessuna eccezione + variazione globale → applica
  variazione su prezzo listino
- Resolver con contratto ATTIVO + listino_versione_id fissato → legge da quella versione
  anche se è uscita versione successiva
- Resolver con contratto DRAFT + nessun listino_versione_id → legge versione corrente

**Chiusura step 2.4 → abilita workstream**:

- ✅ **BE contratti step 2.6**: endpoint contesto pricing su contratti (mutuato
  preventivi) — `GET /api/v1/vendite/contratti/<id>/contesto-pricing/`
- ✅ **FE contratti step 2.2**: banner contesto pricing in `ContrattoRigheDrawer.vue`

---

### Step 2.5 — Drop parameter `VENDITE_CONTRATTO_DEFAULT_MODALITA`

**Modifica**:

```sql
DELETE FROM config.parameters WHERE code = 'VENDITE_CONTRATTO_DEFAULT_MODALITA';
-- Eventuali parameter_overrides cascade-deleted via FK
```

**Note implementazione (2026-05-15)**:

- Migration `20260515-16` in `80_data/changelog/` con Liquibase `delete` tag + rollback `insert`
- Rimossa anche la riga dal CSV `parameters_vendite_defaults.csv` per prevenire re-inserimento da `loadUpdateData` con `runOnChange: true`
- `preCondition: onFail: MARK_RAN` — se il parametro non esiste già (ambienti puliti), il changeSet è marcato come eseguito senza errore

### Step 2.6 — Documentazione DB

**Modifica**:

- Aggiornare `docs/it/dbzero/vendite/manual/contratti.md` con nuova colonna
  `listino_versione_id` e cleanup CHECK/trigger
- Aggiornare `docs/it/dbzero/vendite/manual/contratti_righe.md` con nuova colonna
  `tipo_eccezione` + constraint
- Aggiornare `docs/it/dbzero/vendite/manual/fn_resolve_prezzo_listino_v2.md` con nuovi
  origini `CONTRATTO_AGGIUNTA` + gestione `ESCLUSIONE`
- Aggiornare `docs/it/dbzero/script/manual/fn_get_parameter_full.md` se non già fatto in
  step 1.3

**Note implementazione (2026-05-15)**:

- Documenti aggiornati: `contratti.md`, `contratti_righe.md`, `fn_resolve_prezzo_listino_v2.md`
- Documenti manuali creati (nuove trigger function): `trgfn_contratti_freeze_listino_versione.md`, `trgfn_contratti_lock_post_attivazione.md`, `trgfn_contratti_righe_lock_post_attivazione.md`, `trgfn_contratti_righe_guard_aggiunta_fuori_listino.md`
- `fn_get_parameter_full.md` già aggiornato in Step 1.3 ✅

**Chiusura step 2.6 → chiude Fase 2**.

---

## Riepilogo dipendenze step DB ↔ workstream BE/FE

| Workstream | Dipende da | Indipendente da |
| --- | --- | --- |
| BE preventivi 1.1 (chiamata fn estesa) | Step 1.2 | Tutta Fase 2 |
| BE preventivi 1.2 (`PricingLimitiUtenteView`) | Step 1.2 | Tutta Fase 2 |
| FE preventivi 1.1 (client limiti utente) | BE 1.2 | Tutta Fase 2 |
| BE contratti 2.1 (rimozione gating modalità) | Step 2.1 | Step 2.2-2.6 |
| BE contratti 2.2 (3 gate prezzo + categoria) | Step 1.2 | Step 2.x (può partire post Fase 1) |
| BE contratti 2.3 (gestione 3 tipi eccezione) | Step 2.2 | Step 2.3-2.6 |
| BE contratti 2.4 (blocco rimozione listino) | Step 2.2 | Step 2.3-2.6 |
| BE contratti 2.5 (logica attivazione) | Step 2.3 | Step 2.4-2.6 |
| BE contratti 2.6 (endpoint contesto pricing) | Step 2.4 | Step 2.5-2.6 |
| FE contratti 2.1 (rimozione SelectButton) | BE 2.1 | Resto FE |
| FE contratti 2.2 (banner contesto) | BE 2.6 | Resto FE |
| FE contratti 2.3 (azioni riga) | BE 2.3 | Resto FE |
| FE contratti 2.4 (handling 403/422) | BE 2.5 | Resto FE |
| FE contratti 2.5 (cleanup default prop recap) | Nessuno | Può partire subito |

---

## Note operative al team DB

- Il refactor è in **due PR DB sequenziali** (§3-bis-D del refactor doc), non in un solo
  drop. PR DB-1 = Fase 1, PR DB-2 = Fase 2
- Ogni step ha pgTAP dedicati: la chiusura dello step include i test verdi
- Per il backend agent: alla chiusura di ogni step (notifica del team DB), inizia in
  parallelo i workstream BE indipendenti come da tabella sopra
- Errori applicativi nuovi — **due azioni obbligatorie per ognuno**:
  1. Aggiungere riga al CSV seed di `config.messaggi_errore` (regola: seed 80_data
     sempre in CSV, non YAML SQL standalone)
  2. Aggiungere mappatura in `apps/core/services/error_policies.py` (sub-task di
     **BE contratti 2.5**, unico workstream che tocca già quel file)

  | Codice | HTTP | Contesto |
  | --- | --- | --- |
  | `E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO` | 422 | trigger Step 2.2 |
  | `E_ARTICOLO_ESCLUSO_DA_CONTRATTO` | 422 | resolver Step 2.4 |
  | `E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE` | 422 | trigger Step 2.3 |
  | `E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE` | 409 | trigger Step 2.3 + righe |
  | `E_CONTRATTO_LISTINO_RIMOZIONE_CON_ECCEZIONI` | 422 | service BE 2.4 |

## Riferimenti

- [`refactor-contratti-modalita.md`](refactor-contratti-modalita.md) — decisioni di
  modello complete (§3, §3-bis)
- [`recap-contratti-post-componenti.md`](recap-contratti-post-componenti.md) — bug
  puntuali da assorbire nel refactor o fixare prima
- [`Analisi-iniziale-offerta-commerciale.md`](Analisi-iniziale-offerta-commerciale.md) —
  out-of-scope ma collegato, da riprendere in futuro
