# Brief DB — Modello componenti BoM CASO A — Tabella `vendite.preventivi_righe_componenti` + helper generici `script.*`

> **Tipo**: nuova tabella + 3 trigger + 3 helper generici in `script.*`
> + 1 fn helper di dominio + pgTAP.
> **Branch**: `dev/db-tid`.
> **Autore brief**: backend agent (Tid, sessione 2026-05-11).
> **Trigger**: chiusura bug logico al primo smoke §3.4 push singolo
> preventivo con riga BoM CASO A.
>
> **First of 5**: questa e' la prima delle 5 tabelle simmetriche del
> pattern "righe componenti BoM CASO A". Le 4 successive
> (`ordini_righe_componenti`, `contratto_righe_componenti`,
> `ddt_righe_componenti`, `attivita_consumi_componenti`) replicheranno
> esattamente la stessa struttura e useranno **le stesse 3 helper
> generiche `script.*`** introdotte qui. Vedi §"Pattern da replicare"
> in fondo.

## Contesto e razionale

Per gli articoli compositi con almeno un componente `esposto_in_fattura
= TRUE` (CASO A, §5.2 `gestione-listini.md`), la pipeline commesse
espande la riga padre in N righe `commesse_attivita`. Al push viene
chiamato `vendite.fn_resolve_prezzo_composito` che invoca
`fn_resolve_prezzo_listino_v2` per ogni componente. Bug logici emersi
durante lo smoke 2026-05-11:

1. La riga padre del documento sorgente salva `prezzo_unitario` ma
   questo valore **non e' la fonte di verita'**: al push il resolver
   legge il listino per ogni componente e il prezzo padre viene
   **ignorato silenziosamente**. Cliente vede 1 prezzo nel preventivo,
   fattura ne riporta N differenti.
2. Se uno dei componenti non ha listino mappato, il push esplode
   **dopo** che l'utente ha gia' accettato il preventivo.
3. L'override manuale `prezzo_override_manuale` (regola L1, §6
   `gestione-listini.md`) opera oggi solo sulla riga padre composita —
   inutile, viene ignorato al push.

**Decisione di dominio** (concordata con Tid, sessione 2026-05-11):
ogni componente esposto CASO A diventa una riga negoziabile a se'
stante, con prezzo proprio (suggerito dal resolver + override manuale
ammesso). La riga padre diventa contenitore con `prezzo_unitario`
calcolato come SUM(prezzo_comp × coeff_qta_snapshot) via trigger. Al
push i prezzi vengono propagati ai componenti `commesse_attivita`
**senza ri-chiamare il resolver** — coerente con la regola di
immutabilita' post-accettazione (snapshot pricing).

## Strategia "5 tabelle + helper `script.*`"

5 schemi separati con FK reali (integrita' DB-first, ON DELETE CASCADE
nativo, doc auto-gen leggibile) **ma** logica trigger DRY: 3 helper
generiche in `script.*` parametrizzate su `(schema, tab_padre,
tab_figli)`. I 5 trigger su ogni tabella componenti sono wrapper minimi
che chiamano le helper via `TG_ARGV` — stesso pattern di
`dbops.trgfn_child_requires_active_parent(...)` gia' nel progetto.

**Beneficio**: alla creazione di una nuova tabella `<dominio>_righe_componenti`
basta DDL replicato (struttura colonne identica) + 3 trigger wrapper di
1 riga ciascuno. Niente logica trigger duplicata.

## Perimetro

- **CASO A** (almeno 1 componente con `esposto_in_fattura = TRUE`):
  modello allargato come sotto.
- **CASO B / B1 / B2** (nessun componente esposto, oppure composito a
  riga unica): nessun cambio.

Discriminante: `fn_resolve_prezzo_composito` ritorna N righe in CASO A,
1 riga in CASO B*.

## Azione richiesta al team DB (su `dev/db-tid`)

### 0. Helper generiche in `script.*` (riusabili da tutte 5 le tabelle)

Queste 3 fn vivono in `script.*` ed implementano la logica trigger
una sola volta. I trigger delle 5 tabelle componenti le chiameranno
con TG_ARGV per i parametri schema/tabella.

#### 0.1 `script.fn_ricalcola_prezzo_padre_da_componenti`

```sql
CREATE OR REPLACE FUNCTION script.fn_ricalcola_prezzo_padre_da_componenti(
    p_schema TEXT,        -- es. 'vendite'
    p_tab_padre TEXT,     -- es. 'preventivi_righe'
    p_tab_figli TEXT,     -- es. 'preventivi_righe_componenti'
    p_col_fk_padre TEXT,  -- es. 'riga_preventivo_id' (nome FK su tab_figli)
    p_riga_padre_id BIGINT
) RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE
    v_sql TEXT;
BEGIN
    -- SQL dinamico: SUM su figli attivi * coeff_qta_snapshot,
    -- poi UPDATE sulla tabella padre.
    v_sql := format($f$
        UPDATE %1$I.%2$I
        SET prezzo_unitario = COALESCE((
            SELECT SUM(c.prezzo_unitario * c.coeff_qta_snapshot)
            FROM %1$I.%3$I c
            WHERE c.%4$I = $1
              AND c.attivo = TRUE
        ), 0)
        WHERE id = $1
    $f$, p_schema, p_tab_padre, p_tab_figli, p_col_fk_padre);
    EXECUTE v_sql USING p_riga_padre_id;
END;
$$;
```

**Trigger function wrapper** in `script.*` da usare nelle 5 tabelle:

```sql
CREATE OR REPLACE FUNCTION script.trgfn_componenti_ricalcola_padre()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_riga_padre_id BIGINT;
BEGIN
    -- TG_ARGV: schema, tab_padre, tab_figli, col_fk_padre
    IF TG_OP = 'DELETE' THEN
        EXECUTE format('SELECT ($1).%I', TG_ARGV[3]) INTO v_riga_padre_id USING OLD;
    ELSE
        EXECUTE format('SELECT ($1).%I', TG_ARGV[3]) INTO v_riga_padre_id USING NEW;
    END IF;
    PERFORM script.fn_ricalcola_prezzo_padre_da_componenti(
        TG_ARGV[0], TG_ARGV[1], TG_ARGV[2], TG_ARGV[3], v_riga_padre_id
    );
    RETURN NULL;  -- AFTER trigger
END;
$$;
```

#### 0.2 `script.trgfn_componenti_guard_coerenza_bom`

Trigger function BEFORE INSERT/UPDATE generica che verifica:

- L'`articolo_componente_id` appartiene al BoM dell'`articolo_id` della
  riga padre (`prodotto_id = riga_padre.articolo_id`)
- Il componente ha `esposto_in_fattura = TRUE`
- La BoM e' valida alla data del documento sorgente (`validita @>
  documento.data`)
- La riga padre punta a un articolo composito (`articoli.is_composito = TRUE`)

Riceve via TG_ARGV i nomi per fare il lookup del padre + colonna data:

```sql
TG_ARGV = (
    'vendite',                    -- schema padre
    'preventivi_righe',           -- tabella padre
    'riga_preventivo_id',         -- col FK figli -> padre
    'preventivi',                 -- tabella testata documento
    'preventivo_id',              -- col FK padre -> testata
    'data'                        -- col data riferimento su testata
)
```

Errori parlanti via `script.fn_log_and_raise_error`:

- `E_DOC_COMPONENTE_NON_BOM`
- `E_DOC_COMPONENTE_NON_ESPOSTO`
- `E_DOC_COMPONENTE_BOM_NON_VALIDA`
- `E_DOC_RIGA_NON_COMPOSITO`

(Prefisso `E_DOC_` cross-dominio perche' helper generica usata da 5
sorgenti diverse — preventivi/ordini/contratti/ddt/consumi.)

#### 0.3 `script.trgfn_componenti_propaga_qta`

Trigger function AFTER UPDATE OF `quantita` sulla tabella padre,
ricalcola la `quantita` dei figli come `coeff_qta_snapshot ×
NEW.quantita`. TG_ARGV per nome tabella figli + nome FK padre:

```sql
TG_ARGV = ('vendite', 'preventivi_righe_componenti', 'riga_preventivo_id')
```

#### 0.4 `script.trgfn_componenti_calcola_quantita`

BEFORE INSERT/UPDATE sulla tabella figli: popola `NEW.quantita =
NEW.coeff_qta_snapshot × (SELECT quantita FROM tab_padre WHERE id =
NEW.<col_fk_padre>)`. Defense-in-depth se il BE invia valori
inconsistenti.

```sql
TG_ARGV = ('vendite', 'preventivi_righe', 'riga_preventivo_id')
```

### 1. Tabella `vendite.preventivi_righe_componenti`

```sql
CREATE TABLE vendite.preventivi_righe_componenti (
    id                          BIGSERIAL PRIMARY KEY,
    riga_preventivo_id          BIGINT      NOT NULL,
    articolo_componente_id      UUID        NOT NULL,
    articolo_id                 UUID        NOT NULL,
    coeff_qta_snapshot          NUMERIC     NOT NULL,
    quantita                    NUMERIC     NOT NULL,
    uom_operativa_id            BIGINT,
    factor_to_base              NUMERIC     NOT NULL DEFAULT 1,
    qta_operativa               NUMERIC,
    prezzo_unitario             NUMERIC     NOT NULL,
    iva_id                      INTEGER,
    origine_prezzo              VARCHAR(30) NOT NULL,
    prezzo_resolver_context     JSONB,
    stato_approvazione_prezzo   config.stato_approvazione_prezzo,
    pratica_approvazione_prezzo_id BIGINT,
    meta                        JSONB       DEFAULT '{}'::jsonb,
    ordine                      SMALLINT    DEFAULT 0,
    attivo                      BOOLEAN     NOT NULL DEFAULT TRUE,
    user_insert                 TEXT        NOT NULL DEFAULT CURRENT_USER,
    user_update                 TEXT        DEFAULT CURRENT_USER,
    data_insert                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    data_update                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    tx_id                       UUID,

    CONSTRAINT fk_prevrighe_componenti_riga
        FOREIGN KEY (riga_preventivo_id)
        REFERENCES vendite.preventivi_righe(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_prevrighe_componenti_articolo_componente
        FOREIGN KEY (articolo_componente_id)
        REFERENCES catalogo.articoli_componenti(id),
    CONSTRAINT fk_prevrighe_componenti_articolo
        FOREIGN KEY (articolo_id)
        REFERENCES catalogo.articoli(id),
    CONSTRAINT fk_prevrighe_componenti_uom
        FOREIGN KEY (uom_operativa_id)
        REFERENCES catalogo.unita_misura(id),
    CONSTRAINT fk_prevrighe_componenti_iva
        FOREIGN KEY (iva_id)
        REFERENCES config.iva(id),
    CONSTRAINT fk_prevrighe_componenti_pratica_approvazione
        FOREIGN KEY (pratica_approvazione_prezzo_id)
        REFERENCES pratiche.pratiche(id),

    CONSTRAINT uq_prevrighe_componenti_riga_articolo_componente
        UNIQUE (riga_preventivo_id, articolo_componente_id),

    CONSTRAINT chk_prevrighe_componenti_quantita_pos
        CHECK (quantita > 0),
    CONSTRAINT chk_prevrighe_componenti_prezzo_nonneg
        CHECK (prezzo_unitario >= 0),
    CONSTRAINT chk_prevrighe_componenti_coeff_qta_pos
        CHECK (coeff_qta_snapshot > 0),
    CONSTRAINT chk_prevrighe_componenti_origine
        CHECK (origine_prezzo IN (
            'LISTINO',
            'CATEGORIA',
            'CONTRATTO_LISTINO',
            'CONTRATTO_OVERRIDE',
            'PROMO',
            'MANUALE'
        ))
);
```

**Note campo**:

- `coeff_qta_snapshot` = snapshot `articoli_componenti.coeff_qta`
  all'epoca della creazione. Replicato come campo dedicato per
  ricalcolo veloce padre e isolamento da future evoluzioni BoM.
- `quantita` popolato dal trigger `script.trgfn_componenti_calcola_quantita`
  (= `coeff_qta_snapshot × preventivi_righe.quantita`).
- `iva_id` ed `uom_operativa_id` opzionali: il BE eredita
  dall'articolo componente al popolamento iniziale.

### 2. Indici

```sql
CREATE INDEX ix_vendite_prevrighe_componenti_riga
    ON vendite.preventivi_righe_componenti USING btree (riga_preventivo_id);

CREATE INDEX ix_vendite_prevrighe_componenti_articolo_componente
    ON vendite.preventivi_righe_componenti USING btree (articolo_componente_id);

CREATE INDEX ix_vendite_prevrighe_componenti_stato_approvazione
    ON vendite.preventivi_righe_componenti USING btree (stato_approvazione_prezzo)
    WHERE stato_approvazione_prezzo IS NOT NULL;
```

(FK index policy applicata da `dbops.apply_fk_index_policy()` nello
step `90_end`.)

### 3. Trigger su `vendite.preventivi_righe_componenti` (wrapper su helper `script.*`)

Tutti i trigger sono wrapper minimi delle helper generiche:

```sql
-- 3.1 Guard coerenza BoM (BEFORE INSERT/UPDATE)
CREATE TRIGGER trg_preventivi_righe_componenti_a10_guard_consistency_ins_upd
BEFORE INSERT OR UPDATE ON vendite.preventivi_righe_componenti
FOR EACH ROW
EXECUTE FUNCTION script.trgfn_componenti_guard_coerenza_bom(
    'vendite', 'preventivi_righe', 'riga_preventivo_id',
    'preventivi', 'preventivo_id', 'data'
);

-- 3.2 Ricalcolo prezzo padre (AFTER INSERT/UPDATE/DELETE)
CREATE TRIGGER trg_preventivi_righe_componenti_z90_ricalcola_padre_ins_upd_dlt
AFTER INSERT OR UPDATE OR DELETE ON vendite.preventivi_righe_componenti
FOR EACH ROW
EXECUTE FUNCTION script.trgfn_componenti_ricalcola_padre(
    'vendite', 'preventivi_righe', 'preventivi_righe_componenti', 'riga_preventivo_id'
);

-- 3.3 Calcolo qta da coeff × qta padre (BEFORE INSERT/UPDATE)
CREATE TRIGGER trg_preventivi_righe_componenti_a20_calcola_quantita_ins_upd
BEFORE INSERT OR UPDATE ON vendite.preventivi_righe_componenti
FOR EACH ROW
EXECUTE FUNCTION script.trgfn_componenti_calcola_quantita(
    'vendite', 'preventivi_righe', 'riga_preventivo_id'
);

-- 3.4 Propagazione qta padre -> figli (AFTER UPDATE OF quantita su preventivi_righe)
CREATE TRIGGER trg_preventivi_righe_a30_propaga_qta_componenti_upd
AFTER UPDATE OF quantita ON vendite.preventivi_righe
FOR EACH ROW
EXECUTE FUNCTION script.trgfn_componenti_propaga_qta(
    'vendite', 'preventivi_righe_componenti', 'riga_preventivo_id'
);
```

Trigger audit standard (gia' a catalogo del progetto):

- `trg_preventivi_righe_componenti_audit_data_user_upd` (`script.trgfn_audit_data_user_generic`)
- `trg_preventivi_righe_componenti_gen_tx_id_ins_upd` (`dbops.trgfn_tx_id_managed`)
- `trg_preventivi_righe_componenti_a10_articoli_require_attivo_ins_upd`
  (`dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')`)
- `trg_preventivi_righe_componenti_a10_iva_require_attivo_ins_upd`
  (analogo per `iva_id`, se valorizzato)

### 4. Funzione helper di dominio (preventivi-specific)

`vendite.fn_preventivo_riga_componenti_init(p_riga_id BIGINT,
p_emittente_sr_id BIGINT, p_data_riferimento DATE) RETURNS INTEGER`:

- Legge `articolo_id` + `preventivo_id` + UOM/qta dalla riga padre
- Verifica articolo composito; se no ritorna 0 (no-op)
- Chiama `vendite.fn_resolve_prezzo_composito(...)` con i parametri
  della testata preventivo
- Per ogni riga risolver con `esposto_in_fattura = TRUE`, INSERT in
  `vendite.preventivi_righe_componenti` con:
  - `articolo_componente_id` = id BoM corrispondente
  - `coeff_qta_snapshot` = coeff_qta della BoM
  - `prezzo_unitario` = prezzo suggerito (resolver)
  - `origine_prezzo` = origine dal resolver
  - `prezzo_resolver_context` = JSONB del contesto resolver
- Se resolver fallisce su un componente: INSERT comunque con
  `prezzo_unitario = 0`, `origine_prezzo = 'MANUALE'`,
  `prezzo_resolver_context = {"error": "<codice>", ...}`. L'UI mostra
  warning e l'operatore digita prezzo a mano.
- **Idempotente**: se gia' esistono componenti su `p_riga_id`,
  ritorna 0 senza errore (no-op).
- Ritorna numero componenti inseriti.

Analoghe `fn_<sorgente>_riga_componenti_init` saranno scritte nelle 4
PR successive — stessa logica, parametri presi dalla testata
specifica (ordine/contratto/ddt/attivita_consumi).

### 5. Test pgTAP

**Suite 1**: `db/pgtap/script/componenti_helpers.sql` — test delle 4 helper generiche

- `fn_ricalcola_prezzo_padre_da_componenti` con tabelle fixture:
  insert 2 figli + chiamata helper → SUM corretto
- `trgfn_componenti_guard_coerenza_bom`: 4 scenari errore + 1 OK
- `trgfn_componenti_propaga_qta`: UPDATE qta padre → figli ricalcolati
- `trgfn_componenti_calcola_quantita`: insert con qta omessa → calcolata
- Test idempotenza, edge case (tutti figli inattivi → padre = 0)

**Suite 2**: `db/pgtap/vendite/preventivi_righe_componenti.sql`

- Schema: esistenza tabella + colonne + tipi + nullability
- PK, FK, UNIQUE, CHECK presenti
- Indici presenti
- 4 trigger registrati con TG_ARGV attesi
- Insert componente OK + ricalcolo padre verificato (via helper)
- Cascade DELETE: DROP riga padre → componenti eliminati (FK CASCADE)
- Errori dominio: 4 scenari (`E_DOC_COMPONENTE_NON_BOM` ecc.)

**Suite 3**: `db/pgtap/vendite/fn_preventivo_riga_componenti_init.sql`

- Init su riga composita CASO A con listini popolati → N componenti
- Idempotenza: seconda chiamata → 0
- Listino mancante → riga MANUALE + 0 + error nel context JSONB

### 6. Liquibase

Migration order:

- `YYYYMMDD-NN-create-script-componenti-helpers.yaml` (4 fn `script.*`, `runOnChange: true`)
- `YYYYMMDD-NN-create-vendite-preventivi-righe-componenti.yaml` (DDL + indici)
- `YYYYMMDD-NN-create-vendite-trg-preventivi-righe-componenti.yaml` (4 trigger wrapper)
- `YYYYMMDD-NN-create-vendite-fn-preventivo-riga-componenti-init.yaml` (fn dominio, `runOnChange: true`)
- `YYYYMMDD-NN-pgtap-script-componenti-helpers.yaml` (test suite 1)
- `YYYYMMDD-NN-pgtap-vendite-preventivi-righe-componenti.yaml` (test suite 2+3)

## Smoke post-fix DB

```bash
# 1. Verifica esistenza helper script.*
psql -c "
    SELECT proname FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname = 'script' AND p.proname LIKE '%componenti%';
"
# Atteso: fn_ricalcola_prezzo_padre_da_componenti, trgfn_componenti_ricalcola_padre,
#         trgfn_componenti_guard_coerenza_bom, trgfn_componenti_propaga_qta,
#         trgfn_componenti_calcola_quantita

# 2. Verifica tabella + trigger
psql -c "
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_schema = 'vendite' AND table_name = 'preventivi_righe_componenti'
    ORDER BY ordinal_position;
"
psql -c "
    SELECT trigger_name, action_timing, event_manipulation
    FROM information_schema.triggers
    WHERE event_object_schema = 'vendite'
      AND event_object_table = 'preventivi_righe_componenti';
"

# 3. Smoke funzionale SQL diretto (prima del fix BE)
# Su un preventivo di test, inserire 2 componenti finti + verificare ricalcolo padre + cascade.
```

Smoke utente full end-to-end dopo allineamento BE+FE (PR successiva).

## Pattern da replicare (4 PR DB future, parallelizzabili)

Le 4 tabelle successive replicheranno questa identica struttura — il
team DB puo' iniziarle in parallelo mentre il BE+FE preventivi vengono
implementati e testati. **Riusano le 4 helper `script.*` introdotte
qui**: non serve scrivere nuova logica trigger, solo wrapper + DDL.

### Tabelle in scope (in ordine suggerito di implementazione)

| Sorgente | Tabella padre | Tabella nuova | Col FK padre | Testata | Col FK testata | Col data |
|---|---|---|---|---|---|---|
| Ordini | `vendite.ordini_righe` | `vendite.ordini_righe_componenti` | `riga_ordine_id` | `vendite.ordini` | `ordine_id` | `data` (verificare) |
| Contratti | `vendite.contratto_righe` | `vendite.contratto_righe_componenti` | `riga_contratto_id` | `vendite.contratti` | `contratto_id` | `valido_dal` (verificare) |
| DDT | `vendite.ddt_righe` (o nome equivalente) | `vendite.ddt_righe_componenti` | `riga_ddt_id` | `vendite.ddt` | `ddt_id` | `data` (verificare) |
| Consumi | `vendite.attivita_consumi` | `vendite.attivita_consumi_componenti` | `attivita_consumi_id` | (uso diretto) | (n/a) | `data_lettura` (verificare) |

**Note operative team DB**:

- I nomi colonna `articolo_id` e `quantita` sulle tabelle padre sono
  assunti uguali al pattern di `preventivi_righe`. Se differiscono su
  qualche sorgente, le helper `script.*` non lo gestiscono — va o
  rinominata la colonna padre (consigliato per uniformita') o
  estesa la helper con un parametro aggiuntivo.
- Per ognuna delle 4 tabelle: stessa struttura DDL (copy-paste da
  preventivi_righe_componenti, sostituire prefisso `prevrighe` →
  `<sorg>righe` / nome FK padre → quello del sorgente).
- Stessi 4 trigger wrapper, differiscono solo nei TG_ARGV.
- Fn helper dominio `vendite.fn_<sorgente>_riga_componenti_init`
  specifica per ogni sorgente (parametri estrazione dalla testata
  differiscono — preventivi ha `data + ba_id + utility_id +
  emittente_sr_id`, contratti hanno modello pricing modalita' A/B/C
  che cambia la chiamata al resolver, ecc.). Brief specifici saranno
  inviati prima di iniziare ognuna delle 4 PR.

**Stima effort team DB** post-preventivi: ~0.5 giornata a tabella
(DDL + trigger wrapper + fn init + test pgTAP). Le 4 PR sono
parallelizzabili dopo che la prima (preventivi + helper) e' merged.

## Impatto BE / FE (riferimento, non azione DB)

1. `preventivi_service.crea_riga` / `gestisci_riga`: dopo INSERT della
   riga padre, se articolo `is_composito = TRUE` e CASO A → chiama
   `fn_preventivo_riga_componenti_init`.
2. `preventivi_service` nuovi metodi CRUD componenti
   (`update_componente`, `delete_componente`, `list_componenti`).
3. `commesse_source_handlers.BoMComponentExpander`: in CASO A
   bypassa resolver al push, legge direttamente da
   `preventivi_righe_componenti`. Status quo per CASO B.
4. FE: `PreventiviRigheTable` espander + `PreventiviRigaForm` sezione
   componenti inline (vedi mock sessione 2026-05-11).
5. Stessa logica BE+FE replicata 4 volte (ordini/contratti/ddt/consumi)
   in PR successive — riusano `BoMComponentExpander` con dispatch su
   `sorgente_codice`.

## Riferimenti

- Guida: `docs/it/guide/gestione-listini.md` §5.2 (BoM CASO A) e §6 (override L1)
- Brief gemello in attesa: [brief-db-fn-available-actions-preventivo-meta-nulli.md](brief-db-fn-available-actions-preventivo-meta-nulli.md)
- Memoria progetto: `feedback_bug_logici_modello`, `feedback_concentrico_no_yagni`
- Tabelle correlate:
  - [vendite.preventivi_righe](../../dbzero/vendite/tabelle/preventivi_righe.md)
  - [catalogo.articoli_componenti](../../dbzero/catalogo/tabelle/articoli_componenti.md)
- Resolver: [vendite.fn_resolve_prezzo_composito](../../dbzero/vendite/funzioni/fn_resolve_prezzo_composito.md)

## Note di rollback

DDL: DROP TABLE CASCADE + DROP fn helper `script.*` + DROP fn dominio.
Helper `script.*` restano riusabili anche se preventivi venisse
rollbackato: utili per le altre 4 sorgenti future. Non rimuoverle
selettivamente — vivono nel ciclo di vita del pattern, non della
singola tabella.

ZeroErp in dev, breaking change ammesso, niente backfill obbligatorio
(memoria `project_no_produzione_solo_sviluppo`). Eventuali righe
preventivo CASO A pre-deploy restano con prezzo padre solo — la PR BE
gestira' una migration data-driven una tantum (popolazione componenti
da BoM per righe esistenti su preventivi non `EVASO`/`ANNULLATO`/`RIFIUTATO`).
Brief data migration separato dopo merge DDL.

## Decisioni di dominio (gia' chiuse)

1. Solo CASO A (componenti `esposto_in_fattura = TRUE`) entra nelle 5
   tabelle componenti. CASO B/B1/B2 mantengono modello attuale.
2. L1/L2/L3 sui componenti usano gli stessi parametri di sistema della
   riga padre (`VENDITE_MAX_SCONTO_PCT` ecc.) — niente parametri
   dedicati per componente.
3. La riga padre composita CASO A puo' avere `quantita ≠ 1`. Il prezzo
   padre = SUM(prezzo_comp × coeff_qta_snapshot), il totale padre =
   prezzo × quantita_padre. La `quantita` su tabella componenti e' la
   quantita "per 1 unita' padre" × coeff_qta — al push diventa
   `quantita_componente × quantita_padre` su `commesse_attivita`.
4. Helper `script.*` generiche su (schema, tab_padre, tab_figli, col_fk)
   — niente tabella polimorfica con `sorgente_tipo_id`. FK reali
   preservate (DB-first), logica trigger DRY.
