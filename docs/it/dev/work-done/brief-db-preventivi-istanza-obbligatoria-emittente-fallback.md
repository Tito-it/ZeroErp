# Brief DB — Preventivi: istanza_utility obbligatoria + emittente da operatore + coerenza utility/istanza

> **Status**: ✅ **COMPLETATO** — landed 2026-05-02 su `dev/db-tid` + `dev/backend-tid`.
>
> **Implementazione DB**: vedi [risposta-db-brief-preventivi-rev2.md](risposta-db-brief-preventivi-rev2.md) (12 changeset A→L applicati, 5 deviazioni motivate, 3 file pgTAP, doc manual aggiornata).
>
> **Implementazione BE/FE**: completata sessione 2026-05-02 — commit `1f7daf69` (validator dominio + BB IstanzeUtility + 4 codici errore + componente FE IstanzaUtilityLookup) + commit successivo (refactor §9 PK vs SR scope, vedi `refactor-emittente-id-canonico.md`).
>
> **Osservazione §9 (PK vs SR scope)**: risolta con migration `20260502-01/-02` + nuovo `PermissionResolver.get_emittenti_pk_ids` + sostituzione filtro in `preventivi_repository.py:81-87` da `_sr_ids` a `_pk_ids`.
>
> ---
>
> **Status originale (per cronologia)**: 🆕 **WIP** — rev2 (2026-05-01) — da applicare su `dev/db-tid`.
>
> **Target team**: DB (`dev/db-tid`)
> **Origine**: backend agent (`dev/backend-tid`), sessione 2026-05-01 (validazione UI v5 §2.1 preventivi)
> **Impatto**: `vendite.preventivi` (nuova colonna emittente_fiscale_id), `vendite.vw_preventivi_list` (semplificata), `anagrafiche.istanze_utilities` (trigger create-time), `anagrafiche.istanze_dati_precontrattuali` (backfill Strategia C), schema `script` (nuova fn coerenza generica), schema `vendite` (2 nuovi trigger).
> **No produzione**: ZeroErp non in produzione, breaking change ammessi e regole strette applicabili da subito (memoria progetto `project_no_produzione_solo_sviluppo`).
>
> **Changelog rev**:
> - **rev2 (questa)**: cambio modello emittente — non più derivato dal BA via fn dinamica nella view, ma **persistito su `vendite.preventivi.emittente_fiscale_id` valorizzato a INSERT-time da trigger via GUC `app.current_user_id`**. Rimossa proposta `fn_get_emittente_fiscale_pk_by_istanza_utility` (non più necessaria). Aggiunta sezione §0 "Risposta al blocker team DB" con conferma GUC già attive.
> - rev1: prima stesura con fn dedicata + view CASE.

---

## 0. Risposta al blocker del team DB (multi-face GUCs)

> **Domanda team DB**: il middleware multi-face auth popola già le GUC `app.identita_id` / `app.soggetto_ruolo_id` su tutte le richieste autenticate? Se sì la risoluzione lato DB è una chiamata a `fn_resolve_emittente_for_user` senza altro lavoro. Se no, serve sistemare il middleware (PR2 multi-face) — prerequisito di tutto il flusso preventivo.

**Risposta secca**: **SÌ, le GUC sono già popolate**. Nessun prerequisito middleware.

### Evidenze (codice landed)

`JwtAuditAuthentication` ([jwt_audit_authentication.py:122-141](../../../backend/apps/core/api/jwt_audit_authentication.py)) setta 5 GUC post-auth con un'unica CTE:

```python
WITH id_row AS (
    SELECT id, ruolo_applicativo, soggetto_ruolo_id
      FROM anagrafiche.identita_digitali
     WHERE id = %s AND auth_user_id = %s AND attivo = true
)
SELECT
    set_config('app.jwt_user',            %s,                                                     false),
    set_config('app.current_user_id',     %s,                                                     false),
    set_config('app.current_identita_id', COALESCE((SELECT id::text               FROM id_row), ''), false),
    set_config('app.ruolo_applicativo',   COALESCE((SELECT ruolo_applicativo::text FROM id_row), ''), false),
    set_config('app.soggetto_ruolo_id',   COALESCE((SELECT soggetto_ruolo_id::text FROM id_row), ''), false),
    (SELECT COUNT(*) FROM id_row) AS identita_count
```

`JwtAuditMiddleware.process_response` ([jwt_audit_middleware.py:130-134](../../../backend/apps/core/middleware/jwt_audit_middleware.py)) resetta tutte e 5 le GUC simmetricamente quando la response esce.

### Naming GUC esatte (per il trigger DB)

Il team DB nella domanda menziona `app.identita_id` — il nome reale è **`app.current_identita_id`** (con prefisso `current_`). Tabella riepilogativa:

| Nome esatto GUC | Tipo valore | Quando popolata | Note |
|---|---|---|---|
| `app.jwt_user` | username Django (text) | sempre se auth ok | per audit |
| `app.current_user_id` | `auth_user.id` (text → cast `::bigint`) | **sempre se auth ok** | quello da usare per `fn_resolve_emittente_for_user` |
| `app.current_identita_id` | `identita_digitali.id` (text → `::bigint`) | solo se identita attiva, else `''` | multi-face context |
| `app.ruolo_applicativo` | enum (`OPERATORE`, `CLIENTE_PORTALE`, ...) | solo se identita attiva, else `''` | multi-face context |
| `app.soggetto_ruolo_id` | `soggetti_ruoli.id` (text → `::bigint`) | solo se identita attiva, else `''` | scope per RLS |

### Stato deploy

PR §8.3.4 multi-face GUCs è **landed** in `dev/backend-tid`. Tutte le base view (`DomainAPIView`, `AdminAPIView`, `PortaleAPIView`, `ShopAPIView`) usano `JwtAuditAuthentication`. **Il trigger preventivi ha tutto a disposizione adesso, non serve attendere PR2**.

### Conseguenza per il design del brief

Cambia il modello: invece di calcolare `emittente_fiscale_id` dinamicamente nella view (con fn `fn_get_emittente_fiscale_pk(billing_account_id)` o nuova fn da BA-via-istanza), **persistiamo `emittente_fiscale_id` direttamente sulla riga `vendite.preventivi`** valorizzandolo nel trigger BEFORE INSERT da `script.fn_resolve_emittente_for_user(current_setting('app.current_user_id')::bigint)`.

Vantaggi rispetto a rev1:
- **Niente fn nuova**: `fn_resolve_emittente_for_user` esiste già (refactor operatore-emittenti)
- **Niente fn call dinamica nella view**: lookup colonna indicizzata = zero overhead a SELECT-time
- **Snapshot proprietà a save-time**: l'emittente non cambia se il BA del preventivo viene modificato
- **Risolve elegantemente il caso "preventivo prospect senza BA"**: emittente = quello dell'operatore loggato
- **Allineato al pattern operatore-emittenti 1-a-1** del refactor recente

---

## 1. Contesto

Durante la validazione UI v5 §2.1 (apertura preventivo nuovo) sono emersi 3 bug correlati che svelano un gap di modello sulla coppia `istanza_utility_id` / `billing_account_id` in `vendite.preventivi`.

### 1.1 Bug osservato (E_PARAMETRO_INVALIDO sulla lista)

Il drawer preventivo permetteva di salvare un nuovo preventivo con solo `utility_id` valorizzato (BA e istanza nulli). Salvataggio andato a buon fine. Apertura della lista `/vendite/preventivi/` → 500 con codice DB `E_PARAMETRO_INVALIDO`, perché:

- La view `vendite.vw_preventivi_list` chiama incondizionatamente:
  ```sql
  anagrafiche.fn_get_emittente_fiscale_pk(p.billing_account_id) AS emittente_fiscale_id
  ```
- `fn_get_emittente_fiscale_pk` ha guard "p_billing_account_id obbligatorio e > 0"
- Una sola riga con `billing_account_id IS NULL` fa esplodere TUTTA la lista (anche le righe valide non vengono restituite)

### 1.2 Gap di modello — istanza obbligatoria

Confronto con tabelle gemelle del dominio vendite:

| Tabella | `istanza_utility_id` | `billing_account_id` |
|---|---|---|
| `vendite.attivita_fatturabili` | richiesto (doc: "punto tecnico") | "(opz. intestazione economica)" |
| `vendite.commesse_attivita` | "**sempre valorizzata** (anche tramite istanza fittizia)" | opzionale |
| `vendite.preventivi` | DB nullable, doc lista solo "perimetro fiscale/operativo" | DB nullable |

Pattern dominio cross-vendite consolidato: **istanza obbligatoria, BA opzionale**. Su preventivi non è stato enforced (incoerenza). La doc manual `preventivi.md` non lo distingue.

L'utente conferma la regola di dominio: "il preventivo deve essere collegato all'istanza ... il sistema anche se generale si basa sulla idea delle utilities ... ma è valido per qualsiasi" (da [guida istanze utility](../../guide/gestione-delle-istanze-utility.md): "in azienda non-utility l'istanza viene generata in automatico come contenitore tecnico").

### 1.3 Gap derivazione utility da istanza orfana

`istanze_utilities` non ha `utility_id` proprio. Le sorgenti sono:

| Tabella | UNIQUE | Quando esiste |
|---|---|---|
| `billing_account` | `(istanza_utility_id, utility_id)` | dopo creazione BA |
| `istanze_dati_precontrattuali` | `(istanza_utility_id, utility_id)` | solo in fase pratica con utility `richiede_pdp = true` |
| `clienti` | `(istanza_utility_id)` + col `utility_id` | dopo creazione cliente |

Per business **non-utility** (commercio, servizi) `dati_precontrattuali` NON viene creato. Un'istanza orfana standalone per commercio non ha alcuna sorgente per dichiarare la sua utility → il filtro "istanza per utility X" è impossibile.

L'utente ha sollevato il punto e chiesto soluzione strutturale (Strategia C: rendere `dati_precontrattuali` obbligatoria sempre).

### 1.4 Modello emittente — corretto: deriva dall'operatore

Il modello giusto (chiarito in sessione, vedi §0):
- L'`emittente_fiscale_id` di un documento di vendita = **quello dell'operatore loggato che ha creato la riga**
- NON deriva dal BA del documento (rev1 sbagliata)
- Risolto a INSERT-time da `script.fn_resolve_emittente_for_user(GUC app.current_user_id)`
- Persistito su colonna dedicata, immutabile post-create

Conseguenze:
- Niente fn `fn_get_emittente_fiscale_pk_by_istanza_utility` (rev1 cancellata)
- View `vw_preventivi_list` semplificata: legge la colonna direttamente
- Caso "preventivo prospect senza BA" risolto: emittente sempre derivabile dall'operatore
- Admin globale (no EF assegnato): trigger raise → admin globale deve specificare emittente esplicitamente nel payload (caso edge gestito dal BE)

### 1.5 Mancanza guard coerenza utility-istanza

Nessun trigger/CHECK su `vendite.preventivi` (verificato con `grep` su tutte le migrations) garantisce che `preventivi.utility_id` sia coerente con la utility risolvibile dall'`istanza_utility_id`. Un operatore (o un bug FE) potrebbe salvare `utility_id=GAS` con un'istanza GAS-incompatibile.

---

## 2. Decisione di design

### 2.1 Strategia C — istanza ha SEMPRE una utility dichiarata

Estendere il vincolo `istanze_dati_precontrattuali` (oggi creato solo per utility con `richiede_pdp=true`) a **tutte le utility**: ogni `istanze_utilities` deve avere almeno 1 record satellite (BA, IDP, cliente) per dichiarare la propria utility.

**Backfill**: per ogni `istanze_utilities` esistente che non ha né BA né dati_precontrattuali, creare un `dati_precontrattuali` derivando l'utility dal contesto (vedi §3.2).

**Trigger create-time**: `CONSTRAINT TRIGGER` `DEFERRABLE INITIALLY DEFERRED` su `istanze_utilities`: al COMMIT verifica che almeno 1 satellite esista per l'istanza, altrimenti errore parlante. Permette di creare istanza + satellite nella stessa transazione (es. `create_istanza_fittizia` + `create_billing_account`).

### 2.2 Istanza obbligatoria su preventivi (regola di dominio)

Allineare `vendite.preventivi` al pattern di `commesse_attivita`/`attivita_fatturabili`:

- `ALTER TABLE vendite.preventivi ALTER COLUMN istanza_utility_id SET NOT NULL`
- `billing_account_id` resta nullable (preventivo prospect prima del BA è ammesso)
- Update doc `manual/preventivi.md` per declassare BA a "opzionale" e promuovere istanza a "obbligatoria"

### 2.3 Emittente fiscale persistito + derivato dall'operatore

Modello "user-derived" (vedi §0 e §1.4):
- **Nuova colonna** `vendite.preventivi.emittente_fiscale_id bigint` FK → `anagrafiche.emittenti_fiscali(id)`
- **Backfill** righe esistenti (vedi §3.5)
- **NOT NULL** post-backfill
- **Trigger BEFORE INSERT** `_a05_` (prima del trigger `_a10_` di coerenza utility/istanza): se `NEW.emittente_fiscale_id IS NULL` → setta da `script.fn_resolve_emittente_for_user(current_setting('app.current_user_id')::bigint)`
- **Lock columns** `_a10_` su UPDATE: colonna immutabile post-create (pattern `script.trgfn_lock_columns` come per `numero`)

### 2.4 Fn coerenza generica `script.fn_check_utility_istanza_coerenza`

Cross-tabella (preventivi, attivita_fatturabili, commesse_attivita, ddt, fatture, ...). Stessa logica:

- Verifica esistenza riga `billing_account` con `(istanza_utility_id, utility_id)` matching
- OPPURE riga `istanze_dati_precontrattuali` con stessa coppia (post Strategia C, sempre presente)
- Ritorna `boolean`

Trigger thin per tabella che richiama la fn → errore `E_PREV_UTILITY_ISTANZA_INCOERENTE`.

### 2.5 View `vw_preventivi_list` semplificata

Niente più CASE / fn dinamica. Lettura diretta della nuova colonna persistita:

```sql
-- prima (rev1, fragile):
anagrafiche.fn_get_emittente_fiscale_pk(p.billing_account_id) AS emittente_fiscale_id

-- adesso (rev2, semplice):
p.emittente_fiscale_id
```

Performance migliore (zero call a fn per riga), zero rischio di crash su BA NULL, comportamento consistente.

### 2.6 Cleanup riga test malformata

DELETE puntuale del preventivo creato durante la sessione 2026-05-01 (BA NULL + istanza NULL).

### 2.7 Safety net cross-tabella (CHECK semplice)

Su tutte le tabelle vendite con coppia `(billing_account_id, istanza_utility_id)`:

```sql
CHECK (billing_account_id IS NOT NULL OR istanza_utility_id IS NOT NULL)
```

Per `vendite.preventivi` post Changeset F è ridondante (istanza NOT NULL implica almeno uno NOT NULL). Ma utile come "cintura" su tabelle dove istanza è ancora nullable.

---

## 3. Richieste al team DB (changeset suggeriti, ordine di applicazione)

### 3.1 Changeset A — Cleanup riga test (urgente, sblocca lista in dev)

**Scopo**: ripristinare l'operatività della lista preventivi in dev cancellando le righe malformate residue.

**SQL (verifica + delete)**:

```sql
-- 1. Verifica preliminare (dovrebbe essere 1 sola riga in dev)
SELECT id, numero, data, billing_account_id, istanza_utility_id, user_insert
  FROM vendite.preventivi
 WHERE billing_account_id IS NULL AND istanza_utility_id IS NULL;

-- 2. Delete (eseguire dopo verifica)
DELETE FROM vendite.preventivi
 WHERE billing_account_id IS NULL AND istanza_utility_id IS NULL;
```

**Naming**: `YYYYMMDD-NN-cleanup-preventivi-malformati-mctit.yaml` in `80_data/sql/...` o equivalente.

### 3.2 Changeset B — Strategia C: backfill `istanze_dati_precontrattuali` per tutte le istanze

**Scopo**: per ogni `istanze_utilities` senza dati_precontrattuali, creare il record satellite derivando `utility_id` dal BA collegato (catena `billing_account.istanza_utility_id → utility_id`). Per istanze totalmente orfane (no BA, no IDP), strategia da concordare:

- **Opzione 1** (più safe): identificare e segnalare → l'utente le valuterà manualmente (cancellazione o assegnazione utility)
- **Opzione 2** (auto): se il soggetto ha già almeno 1 cliente con utility nota, ereditarla. Altrimenti rigetto.

**Pseudocodice backfill** (Opzione 1):

```sql
-- Backfill: per ogni istanza con BA, crea IDP se manca
INSERT INTO anagrafiche.istanze_dati_precontrattuali (istanza_utility_id, utility_id)
SELECT DISTINCT ba.istanza_utility_id, ba.utility_id
  FROM anagrafiche.billing_account ba
  WHERE NOT EXISTS (
    SELECT 1 FROM anagrafiche.istanze_dati_precontrattuali idp
     WHERE idp.istanza_utility_id = ba.istanza_utility_id
       AND idp.utility_id = ba.utility_id
  )
ON CONFLICT (istanza_utility_id, utility_id) DO NOTHING;

-- Report istanze orfane senza BA e senza IDP (per decisione manuale)
SELECT iu.id, iu.soggetto_id, iu.fittizia, iu.data_insert
  FROM anagrafiche.istanze_utilities iu
  LEFT JOIN anagrafiche.billing_account ba ON ba.istanza_utility_id = iu.id
  LEFT JOIN anagrafiche.istanze_dati_precontrattuali idp ON idp.istanza_utility_id = iu.id
 WHERE ba.id IS NULL AND idp.id IS NULL;
```

### 3.3 Changeset C — Trigger create-time su `istanze_utilities`

**Scopo**: post-backfill, garantire che ogni nuova istanza abbia almeno 1 satellite (BA, IDP, cliente) entro la stessa transazione.

**Naming**: `trgfn_istanze_utilities_require_utility_dichiarata` + `trg_istanze_utilities_a90_require_utility_dichiarata` (constraint trigger DEFERRABLE INITIALLY DEFERRED).

**Pseudocodice**:

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_istanze_utilities_require_utility_dichiarata()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM anagrafiche.billing_account WHERE istanza_utility_id = NEW.id
    UNION ALL
    SELECT 1 FROM anagrafiche.istanze_dati_precontrattuali WHERE istanza_utility_id = NEW.id
    UNION ALL
    SELECT 1 FROM anagrafiche.clienti WHERE istanza_utility_id = NEW.id
  ) THEN
    PERFORM script.fn_log_and_raise_error(
      'anagrafiche', 'trgfn_istanze_utilities_require_utility_dichiarata',
      'E_ISTANZA_UTILITY_SENZA_UTILITY',
      jsonb_build_object('istanza_id', NEW.id),
      NULL::uuid,
      'Istanza utility senza utility dichiarata: serve almeno un satellite (BA, dati_precontrattuali, cliente)'
    );
  END IF;
  RETURN NEW;
END $$;

CREATE CONSTRAINT TRIGGER trg_istanze_utilities_a90_require_utility_dichiarata
  AFTER INSERT ON anagrafiche.istanze_utilities
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION anagrafiche.trgfn_istanze_utilities_require_utility_dichiarata();
```

### 3.4 Changeset D — Add column `vendite.preventivi.emittente_fiscale_id`

**Scopo**: persistere l'emittente fiscale del documento direttamente sulla riga del preventivo.

**Naming file**: `YYYYMMDD-NN-add-emittente-fiscale-id-preventivi-mctit.yaml`

**SQL**:

```sql
ALTER TABLE vendite.preventivi
  ADD COLUMN emittente_fiscale_id bigint;

ALTER TABLE vendite.preventivi
  ADD CONSTRAINT fk_preventivi_emittente_fiscale
  FOREIGN KEY (emittente_fiscale_id) REFERENCES anagrafiche.emittenti_fiscali(id);

COMMENT ON COLUMN vendite.preventivi.emittente_fiscale_id
  IS 'Emittente fiscale del documento. Valorizzato a INSERT-time dal trigger trgfn_preventivi_set_emittente_from_user via GUC app.current_user_id (catena script.fn_resolve_emittente_for_user). Immutabile post-create (lock_columns). NOT NULL post-backfill.';

-- Indice per scope filtering della view (operatore vede solo i propri preventivi)
CREATE INDEX ix_preventivi_emittente_fiscale_id
  ON vendite.preventivi (emittente_fiscale_id);
```

> **Nota FK index policy**: la FK index policy ZeroErp gestisce indici FK in `90_end` via `dbops.apply_fk_index_policy()`. L'indice esplicito sopra è per performance del filtro scope; verificare con `dbops.fn_seed_fk_index_policy()` se serve registrarlo.

### 3.5 Changeset E — Backfill `emittente_fiscale_id`

**Scopo**: popolare la nuova colonna su tutti i preventivi esistenti.

**Strategia**: dato che in dev (post Changeset A) ci sono solo preventivi con BA valorizzato, derivare l'emittente dal BA usando la fn esistente `fn_get_emittente_fiscale_pk`. Per eventuali preventivi senza BA (caso anomalo, dovrebbe essere zero post-cleanup): usare il gestore globale come fallback.

**SQL**:

```sql
-- Pre-check: quanti preventivi senza emittente
SELECT COUNT(*) FROM vendite.preventivi WHERE emittente_fiscale_id IS NULL;

-- Backfill 1: preventivi con BA → derivare da BA
UPDATE vendite.preventivi p
   SET emittente_fiscale_id = anagrafiche.fn_get_emittente_fiscale_pk(p.billing_account_id)
 WHERE p.emittente_fiscale_id IS NULL
   AND p.billing_account_id IS NOT NULL;

-- Backfill 2: preventivi senza BA (caso anomalo) → gestore globale
UPDATE vendite.preventivi p
   SET emittente_fiscale_id = (
       SELECT ef.id FROM anagrafiche.emittenti_fiscali_billing_account efba
         JOIN anagrafiche.emittenti_fiscali ef ON ef.soggetto_ruolo_id = efba.emittente_soggetto_ruolo_id
        WHERE efba.billing_account_id IS NULL AND efba.is_default = true AND ef.attivo = true
        LIMIT 1
   )
 WHERE p.emittente_fiscale_id IS NULL
   AND p.billing_account_id IS NULL;

-- Post-check: deve essere 0
SELECT COUNT(*) FROM vendite.preventivi WHERE emittente_fiscale_id IS NULL;
```

### 3.6 Changeset F — `NOT NULL` su `vendite.preventivi.emittente_fiscale_id` + `istanza_utility_id`

**Scopo**: enforce regole di dominio "preventivo deve avere emittente" e "preventivo deve avere istanza".

**Pre-requisito**: Changeset A (cleanup), B (backfill IDP), E (backfill emittente) applicati. Verificare zero NULL su entrambe le colonne prima di applicare.

**SQL**:

```sql
-- Pre-check: deve essere 0 entrambi
SELECT 'emittente_null' AS col, COUNT(*) FROM vendite.preventivi WHERE emittente_fiscale_id IS NULL
UNION ALL
SELECT 'istanza_null', COUNT(*) FROM vendite.preventivi WHERE istanza_utility_id IS NULL;

-- Apply NOT NULL
ALTER TABLE vendite.preventivi ALTER COLUMN istanza_utility_id SET NOT NULL;
ALTER TABLE vendite.preventivi ALTER COLUMN emittente_fiscale_id SET NOT NULL;
```

### 3.7 Changeset G — Trigger BEFORE INSERT set emittente da operatore

**Scopo**: valorizzare automaticamente `emittente_fiscale_id` da GUC `app.current_user_id` se non specificato esplicitamente nel payload.

**Naming**: `trgfn_preventivi_set_emittente_from_user` + `trg_preventivi_a05_set_emittente_from_user_ins`

> **Nota fase `_a05_`**: viene PRIMA del trigger `_a10_` di coerenza utility/istanza (Changeset I), così il flusso è: 1) setta emittente da user, 2) verifica coerenza utility/istanza.

**Pseudocodice**:

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_preventivi_set_emittente_from_user()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
  v_user_id_text text;
  v_user_id      bigint;
BEGIN
  -- Skip se gia' valorizzato esplicitamente nel payload (es. admin globale
  -- che specifica emittente per documenti su scope altrui — caso ammesso
  -- gestito dal BE).
  IF NEW.emittente_fiscale_id IS NOT NULL THEN
    RETURN NEW;
  END IF;

  -- GUC sempre settata da JwtAuditAuthentication post-auth (PR §8.3.4 landed).
  -- '' se la fn viene chiamata da un contesto non-API (script manuale,
  -- pgagent job): in quel caso il caller DEVE specificare emittente
  -- esplicitamente nel payload.
  v_user_id_text := current_setting('app.current_user_id', true);
  IF v_user_id_text IS NULL OR v_user_id_text = '' THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'trgfn_preventivi_set_emittente_from_user',
      'E_PREV_EMITTENTE_NON_RISOLTO',
      jsonb_build_object('detail', 'Contesto utente non disponibile e nessun emittente esplicito nel payload'),
      NULL::uuid,
      'Emittente fiscale non risolvibile: GUC app.current_user_id vuota e payload senza emittente_fiscale_id'
    );
  END IF;

  v_user_id := v_user_id_text::bigint;

  -- script.fn_resolve_emittente_for_user gia' esistente (refactor
  -- operatore-emittenti). Ritorna NULL per admin globale (1:N senza
  -- emittente assegnato) o istanza "0 emittenti".
  NEW.emittente_fiscale_id := script.fn_resolve_emittente_for_user(v_user_id);

  IF NEW.emittente_fiscale_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'trgfn_preventivi_set_emittente_from_user',
      'E_PREV_EMITTENTE_NON_RISOLTO',
      jsonb_build_object(
        'detail', 'Operatore admin globale o senza emittente assegnato: specificare emittente_fiscale_id nel payload',
        'auth_user_id', v_user_id
      ),
      NULL::uuid,
      'Operatore senza emittente: payload deve specificare emittente_fiscale_id esplicitamente'
    );
  END IF;

  RETURN NEW;
END $$;

CREATE TRIGGER trg_preventivi_a05_set_emittente_from_user_ins
  BEFORE INSERT ON vendite.preventivi
  FOR EACH ROW
  EXECUTE FUNCTION vendite.trgfn_preventivi_set_emittente_from_user();
```

### 3.8 Changeset H — Lock columns su `emittente_fiscale_id` (immutabile post-create)

**Scopo**: una volta valorizzato, `emittente_fiscale_id` non può essere modificato. Pattern già esistente con `script.trgfn_lock_columns`.

**Pseudocodice** (parametri esatti dipendono dalla firma di `trgfn_lock_columns`, da verificare):

```sql
CREATE TRIGGER trg_preventivi_a10_lock_emittente_upd
  BEFORE UPDATE ON vendite.preventivi
  FOR EACH ROW
  EXECUTE FUNCTION script.trgfn_lock_columns('emittente_fiscale_id', 'EMITTENTE_NON_MODIFICABILE');
```

> **Nota**: il trigger esistente `trg_preventivi_a10_lock_columns_upd` già blocca `numero`. Valutare se estendere la stessa chiamata per evitare 2 trigger separati, oppure aggiungere un nuovo trigger come sopra. Decisione di estetica/manutenibilità del team DB.

### 3.9 Changeset I — Fn coerenza generica `script.fn_check_utility_istanza_coerenza`

**Scopo**: validare coerenza `(istanza, utility)` cross-tabella.

**Naming file**: `YYYYMMDD-NN-create-fn-check-utility-istanza-coerenza-mctit.yaml`

**Pseudocodice**:

```sql
CREATE OR REPLACE FUNCTION script.fn_check_utility_istanza_coerenza(
    p_istanza_utility_id anagrafiche.istanze_utilities.id%TYPE,
    p_utility_id config.utilities.id%TYPE
)
RETURNS boolean
LANGUAGE plpgsql STABLE AS $$
BEGIN
  -- Guard
  IF p_istanza_utility_id IS NULL OR p_utility_id IS NULL THEN
    RETURN false;
  END IF;

  -- Verifica via BA
  IF EXISTS (
    SELECT 1 FROM anagrafiche.billing_account
     WHERE istanza_utility_id = p_istanza_utility_id AND utility_id = p_utility_id
  ) THEN
    RETURN true;
  END IF;

  -- Verifica via dati_precontrattuali (post Strategia C: sempre presente)
  IF EXISTS (
    SELECT 1 FROM anagrafiche.istanze_dati_precontrattuali
     WHERE istanza_utility_id = p_istanza_utility_id AND utility_id = p_utility_id
  ) THEN
    RETURN true;
  END IF;

  RETURN false;
END $$;

COMMENT ON FUNCTION script.fn_check_utility_istanza_coerenza(
  anagrafiche.istanze_utilities.id%TYPE, config.utilities.id%TYPE
) IS 'Pure check: ritorna true se la coppia (istanza_utility_id, utility_id) è coerente via BA o dati_precontrattuali. Riusabile cross-tabella (preventivi, attivita_fatturabili, commesse_attivita, ddt, fatture, ...).';
```

### 3.10 Changeset J — Trigger guard coerenza utility/istanza su `vendite.preventivi`

**Scopo**: applicare la fn coerenza generica come guard BEFORE INSERT/UPDATE su preventivi.

**Naming**: `trgfn_preventivi_guard_utility_istanza_coerenza` + `trg_preventivi_a10_guard_utility_istanza_coerenza_ins_upd`

**Pseudocodice**:

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_preventivi_guard_utility_istanza_coerenza()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  -- Skip se istanza non valorizzata (post Changeset F è impossibile, ma safety)
  IF NEW.istanza_utility_id IS NULL THEN
    RETURN NEW;
  END IF;
  -- Verifica coerenza via fn generica
  IF NOT script.fn_check_utility_istanza_coerenza(NEW.istanza_utility_id, NEW.utility_id) THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'trgfn_preventivi_guard_utility_istanza_coerenza',
      'E_PREV_UTILITY_ISTANZA_INCOERENTE',
      jsonb_build_object(
        'detail', 'utility_id non coerente con istanza_utility_id (no BA né dati_precontrattuali matching)',
        'istanza_utility_id', NEW.istanza_utility_id,
        'utility_id', NEW.utility_id
      ),
      NULL::uuid,
      concat('Coppia (istanza ', NEW.istanza_utility_id::text, ', utility ', NEW.utility_id::text, ') non coerente')
    );
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER trg_preventivi_a10_guard_utility_istanza_coerenza_ins_upd
  BEFORE INSERT OR UPDATE OF istanza_utility_id, utility_id ON vendite.preventivi
  FOR EACH ROW
  EXECUTE FUNCTION vendite.trgfn_preventivi_guard_utility_istanza_coerenza();
```

### 3.11 Changeset K — Update view `vw_preventivi_list` (semplificata)

**Scopo**: rimuovere la chiamata dinamica a `fn_get_emittente_fiscale_pk(billing_account_id)` (origine del bug). Leggere la nuova colonna persistita `p.emittente_fiscale_id`.

**Naming file**: `YYYYMMDD-NN-update-vw-preventivi-list-emittente-persisted-mctit.yaml`

**Pseudocodice**:

```sql
CREATE OR REPLACE VIEW vendite.vw_preventivi_list AS
SELECT
  p.id, p.uid, p.numero, p.rev, p.is_revision_attiva, p.data,
  p.stato_doc_preventivo_id, sdp.codice AS stato_codice, sdp.descrizione AS stato_descrizione,
  p.billing_account_id, ba.utility_id AS ba_utility_id,
  s.id AS soggetto_id, s.ragione_sociale AS cliente_denominazione,
  -- Emittente fiscale: lettura diretta colonna persistita (rev2)
  p.emittente_fiscale_id,
  p.utility_id, p.istanza_utility_id,
  p.totale_imponibile, p.totale_iva, p.totale_documento,
  p.valuta_id, v.codice AS valuta_codice,
  p.termine_pagamento_id, tp.descrizione AS termine_pagamento_descrizione,
  p.validita_dal, p.validita_al, p.competenza_mese,
  p.fatturazione_immediata, p.storicizza, p.data_insert
FROM vendite.preventivi p
JOIN config.stati_doc_preventivi sdp ON sdp.id = p.stato_doc_preventivo_id
LEFT JOIN anagrafiche.billing_account ba ON ba.id = p.billing_account_id
LEFT JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ba.soggetto_ruolo_id
LEFT JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
LEFT JOIN config.valute v ON v.id = p.valuta_id
LEFT JOIN config.termini_pagamento tp ON tp.id = p.termine_pagamento_id
ORDER BY p.data DESC, p.numero DESC, p.id;
```

> **Nota tiebreaker `, p.id`**: già aggiunto da BE rev2 nel repo Python; per coerenza propagare anche nel default ORDER BY della view.

### 3.12 Changeset L (opzionale, safety net) — CHECK "almeno uno NOT NULL" su tabelle gemelle

Da valutare con team DB se utile su tabelle in cui istanza non è ancora NOT NULL (es. `attivita_fatturabili` se applicabile):

```sql
ALTER TABLE vendite.attivita_fatturabili
  ADD CONSTRAINT chk_attivita_fatturabili_istanza_o_ba_richiesto
  CHECK (billing_account_id IS NOT NULL OR istanza_utility_id IS NOT NULL);
```

Per `vendite.preventivi` post Changeset F è ridondante.

---

## 4. Codici errore da registrare

Tutti i codici nuovi vanno aggiunti a `config.codici_errore` (CSV seed) **solo IT** (fallback `it` gestito da `fn_get_messaggio` come da brief `brief-db-fallback-lingua-errori.md`):

| Codice | HTTP | Messaggio IT |
|---|---|---|
| `E_PREV_EMITTENTE_NON_RISOLTO` | 400 | "Operatore senza emittente fiscale assegnato: specificare emittente esplicitamente." |
| `E_PREV_UTILITY_ISTANZA_INCOERENTE` | 409 | "Utility non coerente con l'istanza selezionata." |
| `E_ISTANZA_UTILITY_SENZA_UTILITY` | 409 | "Istanza utility senza utility dichiarata: serve almeno un riferimento (billing account, dati precontrattuali, cliente)." |
| `EMITTENTE_NON_MODIFICABILE` | 409 | "L'emittente fiscale di un preventivo non può essere modificato post-creazione." |

> Il codice `E_PREV_NO_BA_FOR_ISTANZA_UTILITY` proposto in rev1 **non serve più** (modello user-derived).

Lato BE, registrazione in `apps/core/services/error_policies.py` con `ui_action` appropriata (`show_toast_error` o `highlight_form_fields`).

---

## 5. Test pgTAP suggeriti

1. `test-trgfn-preventivi-set-emittente-from-user.sql`
   - Setta GUC `app.current_user_id` con utente con EF assegnato → emittente risolto correttamente
   - Setta GUC vuota → solleva `E_PREV_EMITTENTE_NON_RISOLTO`
   - Utente admin globale (no EF) + payload senza emittente → solleva `E_PREV_EMITTENTE_NON_RISOLTO`
   - Utente admin globale + payload con emittente esplicito → ok (skip trigger)

2. `test-fn-check-utility-istanza-coerenza.sql`
   - Coppia con BA matching → true
   - Coppia con dati_precontrattuali matching (no BA) → true
   - Coppia senza match → false
   - Param NULL → false

3. `test-trgfn-preventivi-guard-utility-istanza-coerenza.sql`
   - INSERT preventivo con coppia coerente → ok
   - INSERT con coppia incoerente → solleva `E_PREV_UTILITY_ISTANZA_INCOERENTE`
   - UPDATE solo `descrizione` → trigger non scatta (UPDATE OF specifico)

4. `test-trgfn-istanze-utilities-require-utility-dichiarata.sql`
   - INSERT istanza + INSERT BA same tx → ok (deferred)
   - INSERT istanza + INSERT IDP same tx → ok
   - INSERT istanza orfana → solleva `E_ISTANZA_UTILITY_SENZA_UTILITY` al COMMIT

5. `test-vw-preventivi-list-emittente-persisted.sql`
   - Mix di righe → no crash, count atteso, `emittente_fiscale_id` letto direttamente dalla colonna
   - Riga con BA NULL ma istanza valorizzata → `emittente_fiscale_id` valorizzato (post-trigger create)

6. `test-trg-preventivi-lock-emittente.sql`
   - UPDATE su `emittente_fiscale_id` → solleva `EMITTENTE_NON_MODIFICABILE`
   - UPDATE su altri campi → ok

---

## 6. Documentazione da aggiornare

- `docs/it/dbzero/vendite/manual/preventivi.md`: declassare BA a "opzionale", promuovere istanza a "obbligatoria post 2026-05-XX". Aggiungere `emittente_fiscale_id` come "obbligatoria, immutabile, derivata dall'operatore". Riferimento al pattern `commesse_attivita`/`attivita_fatturabili`.
- `docs/it/guide/gestione-delle-istanze-utility.md`: aggiungere sezione "Strategia C: ogni istanza ha utility dichiarata via dati_precontrattuali" (post landing).
- `docs/it/guide/risorse-umane-e-accessi.md`: cross-link al nuovo trigger `trgfn_preventivi_set_emittente_from_user` come consumer della GUC `app.current_user_id`.

---

## 7. Backend agent — lavoro in parallelo

Mentre il team DB applica i changeset, il backend agent procederà su `dev/backend-tid` con:

1. **Building block**: `IstanzeUtilityRepository` + `IstanzeUtilityService` + endpoint `GET /api/v1/anagrafiche/istanze-utility/lookup/?q=&utility_id=&soggetto_id=` con scope emittente identico a `BillingAccountLookup` (visibile se almeno 1 BA dell'istanza è nello scope EF dell'utente; admin globale vede tutto). Restore singolo `GET /api/v1/anagrafiche/istanze-utility/{id}/lookup/`.
2. **Service `crea_preventivo`**: `ErrorManager.require(istanza_utility_id is not None, ...)`. Se BA presente, derivare istanza dal BA. Validator coerenza utility-istanza pre-trigger. Per admin globale: payload può specificare `emittente_fiscale_id` esplicito (passato al DB → trigger lo accetta come override).
3. **Drawer FE preventivo**: nuovo `IstanzaUtilityLookup.vue` (autocomplete con prop `utilityId`/`soggettoId` opzionali, badge BA per istanze già usate, badge "Solo istanza" per orfane). Integrazione: se BA selezionato → istanza auto-popolata (già fatto); se no BA → picker istanza obbligatorio. Asterisco `*` su utility e istanza.
4. **Registrazione codici errore**: `error_policies.py` con i 4 nuovi codici (vedi §4).
5. **Aggiornamento doc cataloghi BB** (FE + BE).

Nessuna di queste azioni richiede attendere il landing dei changeset DB — il backend lavora con la fn esistente `fn_resolve_emittente_for_user` quando il trigger arriverà; nel frattempo i test mock-only del service passano già.

---

## 8. Domande residue per il team DB

1. **Changeset B Opzione 1 vs 2** (backfill orfane): preferenza tua, team DB?
2. **Changeset C** (trigger create-time istanze): la modalità `DEFERRABLE INITIALLY DEFERRED` permette INSERT istanza + satellite nella stessa tx — confermare compatibilità coi flussi attuali (`create_istanza_fittizia` in `clienti_repository.py` viene già usato dentro `create_cliente` che probabilmente crea anche BA nella stessa tx).
3. **Changeset H** (lock columns emittente): preferenza fra estendere il trigger esistente `trg_preventivi_a10_lock_columns_upd` (oggi blocca `numero`) o creare un trigger separato? Estesa = più clean / meno trigger; separata = più chiara la genesi.
4. **Changeset L** (CHECK safety net): applicare anche su tabelle non-preventivi? Quali?

---

## 9. Osservazione di passaggio (fuori scope, da verificare)

Mentre verificavo lo scope filter, ho notato un possibile mismatch in [`preventivi_repository.py:81-87`](../../../backend/apps/vendite/db/preventivi_repository.py#L81-L87):

```python
"(script.fn_get_emittenti_scope_sr_ids(%s) IS NULL "
"OR v.emittente_fiscale_id = ANY(script.fn_get_emittenti_scope_sr_ids(%s)))"
```

Confronta `v.emittente_fiscale_id` (PK numerica reale di `emittenti_fiscali.id`, post commit `20260407-03-update-vw-preventivi-list-emittente-pk-mctit`) con `fn_get_emittenti_scope_sr_ids` (il nome `_sr_ids` suggerisce `soggetto_ruolo_id[]`, in coerenza con la memoria progetto `feedback_emittente_pk_vs_soggetto_ruolo`).

Se confermato il mismatch:
- O esiste una fn `fn_get_emittenti_scope_pk_ids` che ritorna PK reali, e il BE deve usare quella
- O la fn attuale è erroneamente nominata `_sr_ids` ma di fatto ritorna PK
- O il filtro sta confrontando PK con sr_id e in dev "funziona per caso" perché molti operatori hanno EF con coincidenza PK ≈ sr_id

Non è blocker per questo brief, ma da verificare separatamente con un test dedicato sullo scope filter. Spiega potenziali risultati strani sulla lista preventivi quando l'operatore non vede i propri preventivi attesi (o vede preventivi non suoi).

---

*Brief preparato dal backend agent il 2026-05-01 (rev2). Da applicare su `dev/db-tid`. Spostare in `work-done/` post-landing con note di eventuali modifiche apportate dal team DB rispetto al brief originale.*
