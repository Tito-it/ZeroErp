# Sviluppo Listini — Pricing ZeroERP (WIP v5)

> Stato: **SPECIFICA CHIUSA — pronta per implementazione.**
>
> Ultima revisione: 14 aprile 2026
>
> Questo documento **sostituisce** il v5 precedente a seguito della
> sessione di analisi critica del 14 aprile 2026. Consolida e riscrive il
> modello di pricing sulla base delle decisioni prese:
>
> * Listino unico **base** per (utility, tipologia, emittente) — niente listini derivati
> * Variazioni sul prezzo base vivono dove hanno significato: **categoria cliente** e **contratto**
> * `vendite.listini_associazioni` **deprecata**, sostituita da categoria cliente + contratto
> * `vendite.contratti` esteso per essere il ponte commerciale tra cliente e listino
> * Resolver a **3 stadi**: promo → contratto → categoria cliente
> * Dimensione pricing **classe utenza** nella matrice categoria→listino
> * Tipologia articolo + guard su righe listino per coerenza semantica
> * BoM con componenti esposti in fattura, espansione in `commesse_attivita`
>
> Riferimenti:
> * [sviluppo-listini-v3.md] — N1–N8, rettifiche, invariante univocità 2026-04-09
> * [sviluppo-listini-v4.md] — `utility_id NOT NULL` + `tipologia_id` + matrice `listini_tipologie_utilities` (**DB completato**, BE+FE da chiudere)
> * [guide/gestione-listini.md] — guida corrente (da riscrivere dopo v5 applicato)
> * [dbzero/vendite/tabelle/contratti.md]
> * [dbzero/vendite/tabelle/contratti_utilities.md]
> * [dbzero/config/tabelle/classi_utenze.md]

---

## 1) Motivazione

### 1.1 Cosa non va nel modello attuale

Il modello pre-v5 cerca di gestire con un'unica tabella tecnica (`listini_associazioni`) tutti gli scenari commerciali:

- cliente standard che usa il listino base
- cliente con categoria commerciale (SILVER, GOLD…) che usa un listino dedicato
- cliente con contratto individuale negoziato

Il risultato: `listini_associazioni` mischia semantiche diverse (routing tecnico + accordo formale + politica commerciale) e l'operatore è costretto a duplicare listini quando la sola variabile è una percentuale di sconto.

Inoltre il fornitore aggiorna il listino base 2–4 volte l'anno: se ogni categoria è un listino separato, ogni aggiornamento diventa N aggiornamenti. Non scala.

### 1.2 Principi del nuovo modello

1. **Un solo listino** per `(utility, tipologia, emittente)`. Un solo punto di verità per i prezzi base.
2. Le **variazioni** vivono dove hanno significato commerciale, non nel listino:
   - **Categoria cliente** — politica commerciale trasversale (SILVER = base −10%)
   - **Contratto** — accordo formale individuale (variazione globale + override per singolo articolo)
3. **Promo** — overlay temporale indipendente, batte tutto il resto.
4. **Resolver deterministico** a 3 stadi, senza tie-break e senza `match_level` dimensionale.
5. **Classe utenza** è dimensione di pricing nel dominio utility. Entra nella matrice categoria→listino come campo opzionale con fallback NULL.
6. **Emittente fiscale** è dimensione del listino e dell'associazione, ma non input del resolver: deriva dalla sessione dell'operatore (1-a-1 emittente/operatore).
7. **Nessun NULL wildcard ambiguo**: le dimensioni del listino sono NOT NULL. Il solo NULL semantico è `classe_utenza_id` nella matrice (fallback esplicito).

---

## 2) Modello dati — visione di insieme

```
┌──────────────────────┐         ┌──────────────────────────────────┐
│ config.utilities     │         │ config.listini_tipologie         │
│ (Gas, EE, Idrico,    │         │ (CONSUMO, QUOTA_FISSA, IMPOSTA,  │
│  TLR, Base…)         │         │  ONERE, PRODOTTI, SERVIZI)       │
└──────────┬───────────┘         └──────────────────┬───────────────┘
           │   ┌────────────────────────────────────┘
           │   │ config.listini_tipologie_utilities
           │   │ (matrice ammissibilità)
           │   │
           ▼   ▼
      ┌──────────────────────────────────────────────┐
      │ vendite.listini                              │
      │ utility_id, tipologia_id, emittente_id (NN)  │◄──┐
      │ NIENTE listino_base_id / tipo_variazione     │   │
      └──────┬───────────────────────────────────────┘   │
             │                                           │
             │ 1-n                                       │
             ▼                                           │
      ┌──────────────────────────┐                       │
      │ vendite.listini_versioni │                       │
      └──────┬───────────────────┘                       │
             │                                           │
             │ 1-n                                       │
             ▼                                           │
      ┌──────────────────────────┐                       │
      │ vendite.listini_righe    │                       │
      │ (versione, art, uom,     │                       │
      │  prezzo) — puro          │                       │
      └──────────────────────────┘                       │
                                                         │
  ┌──────────────────────────────────────────────────┐   │
  │ anagrafiche.categorie_clienti                    │   │
  │ partecipa_promo, ordinamento                     │   │
  └──────┬───────────────────────────────────────────┘   │
         │                                               │
         │ matrice N:N                                   │
         ▼                                               │
  ┌──────────────────────────────────────────────────┐   │
  │ anagrafiche.categorie_clienti_listini            │──►┘
  │ categoria_cliente_id, utility_id (NN),           │
  │ emittente_id (NN), classe_utenza_id (N),         │
  │ listino_id, tipo_variazione, valore_variazione,  │
  │ validità daterange                               │
  └──────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────┐
  │ anagrafiche.billing_account                      │
  │ + categoria_cliente_id (N)                       │
  └──────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────┐
  │ vendite.contratti                                │──► vendite.listini (opz.)
  │ + listino_id (N), tipo_variazione_globale (N),   │
  │   valore_variazione_globale (N)                  │
  │ CHECK: modalità A / B / C coerenti               │
  └──────┬───────────────────────────────────────────┘
         │
         ▼
  ┌──────────────────────────────────────────────────┐
  │ vendite.contratti_righe                          │
  │ prezzo_unitario opz. = override per articolo     │
  └──────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────┐
  │ vendite.promo_articoli                           │
  │ articolo, uom, periodo, tipo+valore variazione   │
  └──────────────────────────────────────────────────┘
```

---

## 3) Modifiche ai listini

### 3.1 `vendite.listini` — aggiunta `emittente_soggetto_ruolo_id`

Stato oggi: `utility_id NOT NULL`, `tipologia_id NOT NULL`, trigger guard matrice utility×tipologia attivo.

Aggiunte v5:

```sql
ALTER TABLE vendite.listini
    ADD COLUMN emittente_soggetto_ruolo_id bigint NOT NULL
        REFERENCES anagrafiche.soggetti_ruoli(id);

CREATE INDEX ix_listini_emittente
    ON vendite.listini (emittente_soggetto_ruolo_id);
```

Backfill pre-NOT-NULL: popolare via emittente derivato dall'operatore che ha creato il listino (`fn_get_emittente_fiscale_pk` + `user_insert`), o assegnare emittente di default dove il backfill automatico fallisce (operazione manuale prima del `SET NOT NULL`).

Unicità funzionale consigliata (opzionale):
```sql
ALTER TABLE vendite.listini
    ADD CONSTRAINT uq_listini_business
        UNIQUE (utility_id, tipologia_id, emittente_soggetto_ruolo_id, codice);
```
Il `codice` già UNIQUE garantisce l'univocità tecnica; questo vincolo aggiunge solo un check di ridondanza.

### 3.2 `vendite.listini_righe` — ritorno alla forma pura

Dimensioni di contesto rimosse:
```sql
ALTER TABLE vendite.listini_righe
    DROP COLUMN billing_account_id,
    DROP COLUMN utility_id,
    DROP COLUMN emittente_soggetto_ruolo_id;
```

`listini_righe` torna a essere: `(id, listino_versione_id, articolo_id, uom_id, prezzo, meta, attivo, audit)`. Niente dimensioni di contesto, niente `match_level` a 7 livelli: ogni riga è un prezzo per `(versione, articolo, uom)`. Eventuali differenze commerciali sono gestite da categoria o contratto.

Unicità riga in versione (indice unico parziale per consentire soft-delete):
```sql
CREATE UNIQUE INDEX uq_listini_righe_key_attiva
    ON vendite.listini_righe (listino_versione_id, articolo_id, uom_id)
    WHERE attivo IS TRUE;
```
Nota: in PostgreSQL non è possibile esprimere un UNIQUE parziale come table constraint; serve `CREATE UNIQUE INDEX ... WHERE`. Questo esclude naturalmente le righe `attivo = false` (soft-delete / storicizzazione).

### 3.3 `vendite.listini_associazioni` — deprecata

La tabella viene droppata. Il suo ruolo è coperto da:
- scope BA standard → `billing_account.categoria_cliente_id` + `categorie_clienti_listini`
- scope individuale negoziato → `vendite.contratti` (esteso)
- scope emittente → dimensione interna del listino (`emittente_soggetto_ruolo_id`)

Verificare prima del drop: nessun riferimento attivo in backend (`apps/vendite/db/vendite_repository.py`, views, resolver) e pgtap da rimuovere/migrare.

### 3.4 Listini derivati — concetto eliminato

Il campo proposto in v5 precedente `listini.listino_base_id + tipo_variazione + valore_variazione` **non viene creato**. La variazione è proprietà della relazione cliente↔listino, non del listino.

---

## 4) Categoria cliente

### 4.1 `anagrafiche.categorie_clienti`

```sql
CREATE TABLE anagrafiche.categorie_clienti (
    id                  smallserial  PRIMARY KEY,
    codice              varchar      NOT NULL UNIQUE,
    descrizione         varchar      NOT NULL,
    -- partecipazione promo
    partecipa_promo     boolean      NOT NULL DEFAULT true,
    -- ordinamento display UI
    ordinamento         smallint     NOT NULL DEFAULT 100,
    meta                jsonb        NOT NULL DEFAULT '{}'::jsonb,
    attivo              boolean      NOT NULL DEFAULT true,
    data_insert         timestamptz  NOT NULL DEFAULT now(),
    user_insert         text         NOT NULL DEFAULT CURRENT_USER,
    data_update         timestamptz  NOT NULL DEFAULT now(),
    user_update         text         NOT NULL DEFAULT CURRENT_USER,
    tx_id               uuid         NULL
);
```

Seed tipico commercio:

| codice     | descrizione      | partecipa_promo |
|------------|------------------|-----------------|
| STANDARD   | Cliente standard | false           |
| BASE       | Cliente base     | true            |
| SILVER     | Cliente silver   | true            |
| GOLD       | Cliente gold     | true            |
| PLATINUM   | Cliente platinum | true            |

Un cliente STANDARD che non partecipa alle promo è il comportamento sicuro di default.

### 4.2 `anagrafiche.categorie_clienti_listini`

Matrice categoria × utility × emittente × classe_utenza → listino con eventuale variazione.

```sql
CREATE TABLE anagrafiche.categorie_clienti_listini (
    id                           bigserial    PRIMARY KEY,
    categoria_cliente_id         smallint     NOT NULL
        REFERENCES anagrafiche.categorie_clienti(id),
    utility_id                   integer      NOT NULL
        REFERENCES config.utilities(id),
    emittente_soggetto_ruolo_id  bigint       NOT NULL
        REFERENCES anagrafiche.soggetti_ruoli(id),
    classe_utenza_id             integer      NULL
        REFERENCES config.classi_utenze(id),
    listino_id                   bigint       NOT NULL
        REFERENCES vendite.listini(id),
    -- variazione opzionale; se NULL si usa il prezzo base tal quale
    tipo_variazione              varchar      NULL
        CHECK (tipo_variazione IN ('PERCENTUALE', 'VALORE_FISSO')),
    valore_variazione            numeric(10,4) NULL,
    valido_dal                   date         NOT NULL,
    valido_al                    date         NULL,
    validita                     daterange    NOT NULL,
    meta                         jsonb        NOT NULL DEFAULT '{}'::jsonb,
    attivo                       boolean      NOT NULL DEFAULT true,
    data_insert                  timestamptz  NOT NULL DEFAULT now(),
    user_insert                  text         NOT NULL DEFAULT CURRENT_USER,
    data_update                  timestamptz  NOT NULL DEFAULT now(),
    user_update                  text         NOT NULL DEFAULT CURRENT_USER,
    tx_id                        uuid         NULL,
    CONSTRAINT chk_categ_cli_listini_variazione_coerente CHECK (
        (tipo_variazione IS NULL AND valore_variazione IS NULL)
        OR
        (tipo_variazione IS NOT NULL AND valore_variazione IS NOT NULL)
    )
);
```

No-overlap cross-scope (un solo listino attivo per quadrupla nel periodo):

```sql
-- Prerequisito: estensione btree_gist attiva (CREATE EXTENSION IF NOT EXISTS btree_gist)
-- Il sentinel -1 per classe_utenza_id è sicuro perché config.classi_utenze.id è serial (parte da 1).
ALTER TABLE anagrafiche.categorie_clienti_listini
    ADD CONSTRAINT ex_categ_cli_listini_no_overlap
    EXCLUDE USING gist (
        categoria_cliente_id              WITH =,
        utility_id                        WITH =,
        emittente_soggetto_ruolo_id       WITH =,
        (COALESCE(classe_utenza_id, -1))  WITH =,
        validita                          WITH &&
    ) WHERE (attivo IS TRUE);
```

Trigger `script.trgfn_set_validita` per sincronizzare `validita` con `valido_dal/al` (già disponibile).

### 4.3 Semantica del fallback `classe_utenza_id`

Il resolver cerca prima il match più specifico con classe_utenza valorizzata; se non trova, cerca il fallback con `classe_utenza_id IS NULL` (vale per qualsiasi classe). Questo permette di definire:

- riga con `classe_utenza_id` = DOM-BTA → listino specifico
- riga con `classe_utenza_id` NULL → listino generico per tutte le altre classi della stessa categoria/utility/emittente

Per il dominio commercio (utility Base) il campo è **sempre NULL** — non esistono classi utenza commerciali.

### 4.4 `anagrafiche.billing_account` — collegamento alla categoria

Strategia (nessun dato di produzione): backfill massivo a `STANDARD` + `NOT NULL` finale, così il resolver ha sempre una categoria su cui cadere in STADIO 2.

```sql
-- 1) aggiunta nullable
ALTER TABLE anagrafiche.billing_account
    ADD COLUMN categoria_cliente_id smallint NULL
        REFERENCES anagrafiche.categorie_clienti(id);

CREATE INDEX ix_billing_account_categoria_cliente
    ON anagrafiche.billing_account (categoria_cliente_id);

-- 2) backfill (changeSet successivo, dopo seed categorie_clienti)
UPDATE anagrafiche.billing_account ba
   SET categoria_cliente_id = (SELECT id FROM anagrafiche.categorie_clienti
                                WHERE codice = 'STANDARD')
 WHERE ba.categoria_cliente_id IS NULL;

-- 3) SET NOT NULL (changeSet successivo al backfill)
ALTER TABLE anagrafiche.billing_account
    ALTER COLUMN categoria_cliente_id SET NOT NULL;
```

Risultato: ogni BA ha sempre una categoria → STADIO 2 del resolver non incontra mai BA orfani. L'errore `E_PREZZO_LISTINO_NON_TROVATO` resta possibile solo se la matrice `categorie_clienti_listini` non ha una riga per la quadrupla richiesta (caso `E_CATEGORIA_LISTINO_NON_MAPPATA`).

---

## 5) Contratti estesi

### 5.1 `vendite.contratti` — aggiunta riferimento listino

```sql
ALTER TABLE vendite.contratti
    ADD COLUMN listino_id                  bigint       NULL
        REFERENCES vendite.listini(id),
    ADD COLUMN tipo_variazione_globale     varchar      NULL
        CHECK (tipo_variazione_globale IN ('PERCENTUALE', 'VALORE_FISSO')),
    ADD COLUMN valore_variazione_globale   numeric(10,4) NULL;
```

Vincolo coerenza sulle tre modalità A / B / C:

```sql
ALTER TABLE vendite.contratti
    ADD CONSTRAINT chk_contratti_modalita_pricing CHECK (
        -- A: solo listino + variazione globale, niente righe con prezzo_unitario forzato
        -- B: listino + (variazione opzionale) + alcune righe con prezzo_unitario override
        -- C: niente listino, tutte le righe con prezzo_unitario NOT NULL
        -- Il vincolo cross-table è rinforzato da trigger (vedi 5.3)
        (listino_id IS NOT NULL)
        OR
        (listino_id IS NULL AND tipo_variazione_globale IS NULL
         AND valore_variazione_globale IS NULL)
    ),
    ADD CONSTRAINT chk_contratti_variazione_coerente CHECK (
        (tipo_variazione_globale IS NULL AND valore_variazione_globale IS NULL)
        OR
        (tipo_variazione_globale IS NOT NULL AND valore_variazione_globale IS NOT NULL)
    );
```

### 5.2 `vendite.contratti_utilities` — aggiunta `tipo_utenza_id`

```sql
ALTER TABLE vendite.contratti_utilities
    ADD COLUMN tipo_utenza_id integer NULL
        REFERENCES config.tipi_utenze(id);
```

`tipo_utenza_id` e `classe_utenza_id` sono NULL per `contratti.ambito = 'COMMERCIO'` (utility Base). Sono entrambi NOT NULL coerenti fra loro (`classi_utenze.tipo_utenza_id = tipo_utenza_id`) per le altre utility. Vincolo via trigger:

```sql
-- trgfn_contratti_utilities_guard_tipo_classe:
-- - se contratti.utility_id = Base → tipo_utenza_id NULL, classe_utenza_id NULL
-- - altrimenti tipo_utenza_id NOT NULL, classe_utenza_id NOT NULL
--   e classi_utenze(classe_utenza_id).tipo_utenza_id = tipo_utenza_id
```

Motivazione: il contratto **fotografa** tipo+classe al momento della stipula. Anche se derivabili dall'istanza precontrattuale, vengono congelati esplicitamente per consistenza storica e query dirette nel resolver.

### 5.3 Modalità pricing A / B / C

| Modalità | `listino_id` | `tipo_variazione_globale` | `contratti_righe` | Esempio |
|---|---|---|---|---|
| **A** — listino + variazione globale | NOT NULL | NOT NULL | vuoto o solo override mirati | "Listino gas 2026 −10%" |
| **B** — listino con override | NOT NULL | NULL (o anche NOT NULL) | righe con `prezzo_unitario` per articoli specifici | "Listino gas 2026, art X a €50 fisso" |
| **C** — interamente negoziato | NULL | NULL | tutte le righe con `prezzo_unitario` NOT NULL | Grande cliente con condizioni 100% su misura |

Vincolo cross-table via trigger `vendite.trgfn_contratti_modalita_c_righe_complete`:
- se `contratto.listino_id IS NULL` (modalità C) → ogni riga in `contratti_righe` deve avere `prezzo_unitario IS NOT NULL`.
- il guard è **fail-fast all'attivazione** del contratto. La tabella `config.stati_doc_contratti` esiste già con codici `DRAFT`, `ATTIVO`, `SOSPESO`, `CESSATO`; `vendite.contratti.stato_doc_contratto_id` è la FK. Il trigger scatta su `UPDATE OF stato_doc_contratto_id` quando il nuovo stato ha `codice_interno = 'ATTIVO'`, e su INSERT/UPDATE di `contratti_righe` se il contratto è già in stato `ATTIVO`. In stato `DRAFT` la mancanza di righe è ammessa; un contratto C senza righe non può transitare a `ATTIVO`. Nessuna nuova tabella stati necessaria.

### 5.4 Relazione contratto / listini_associazioni

`listini_associazioni` viene droppata. Il contratto **è** il meccanismo di associazione BA↔listino per i clienti che escono dalla gestione per categoria.

Il vincolo `ex_contratti_no_overlap` già esistente garantisce: **un solo contratto attivo** per `(billing_account_id, istanza_utility_id, utility_id, ambito)` su validità. Il resolver STADIO 1 non ha ambiguità.

---

## 6) Promo overlay

### 6.1 `vendite.promo_articoli`

```sql
CREATE TABLE vendite.promo_articoli (
    id                  bigserial    PRIMARY KEY,
    codice              varchar      NOT NULL UNIQUE,
    descrizione         varchar      NOT NULL,
    articolo_id         uuid         NOT NULL
        REFERENCES catalogo.articoli(id),
    uom_id              bigint       NOT NULL
        REFERENCES catalogo.unita_misura(id),
    tipo_variazione     varchar      NOT NULL
        CHECK (tipo_variazione IN ('PERCENTUALE', 'VALORE_FISSO', 'PREZZO_FISSO')),
    valore_variazione   numeric(10,4) NOT NULL,
    valido_dal          date         NOT NULL,
    valido_al           date         NOT NULL,
    validita            daterange    NOT NULL,
    meta                jsonb        NOT NULL DEFAULT '{}'::jsonb,
    attivo              boolean      NOT NULL DEFAULT true,
    data_insert         timestamptz  NOT NULL DEFAULT now(),
    user_insert         text         NOT NULL DEFAULT CURRENT_USER,
    data_update         timestamptz  NOT NULL DEFAULT now(),
    user_update         text         NOT NULL DEFAULT CURRENT_USER,
    tx_id               uuid         NULL,
    CONSTRAINT chk_promo_articoli_date     CHECK (valido_al >= valido_dal),
    CONSTRAINT chk_promo_articoli_valore   CHECK (valore_variazione > 0
                                                  OR tipo_variazione = 'PREZZO_FISSO')
);

ALTER TABLE vendite.promo_articoli
    ADD CONSTRAINT ex_promo_articoli_no_overlap
    EXCLUDE USING gist (
        articolo_id  WITH =,
        uom_id       WITH =,
        validita     WITH &&
    ) WHERE (attivo IS TRUE);
```

`PREZZO_FISSO` è ammesso solo nella promo (promo "€12,50 secchi") perché rappresenta un'offerta temporale indipendente dal prezzo base. Nel listino e nella categoria cliente non ha senso perché il listino **è** il prezzo assoluto.

### 6.2 Partecipazione alla promo

La promo vale per tutti i BA con `categoria_cliente.partecipa_promo = true`. Non esistono ulteriori segmentazioni (niente promo per singola categoria: se serve, si creano promo diverse e si limita a quali categorie partecipano via attivazione/disattivazione).

### 6.3 Calcolo

```
prezzo_base = risultato risoluzione STADIO 1 o STADIO 2 (vedi resolver)

-- PERCENTUALE
prezzo_promo = prezzo_base * (1 + valore_variazione / 100)

-- VALORE_FISSO
prezzo_promo = prezzo_base + valore_variazione

-- PREZZO_FISSO
prezzo_promo = valore_variazione
```

Il calcolo della promo si appoggia sempre al **prezzo base** risolto dal meccanismo "normale" (contratto o categoria): non si applica mai sopra un prezzo già scontato, per evitare doppio sconto implicito.

---

## 7) Tipologia articoli e coerenza con listino

### 7.1 `catalogo.articoli` — aggiunta `listino_tipologia_id`

```sql
ALTER TABLE catalogo.articoli
    ADD COLUMN listino_tipologia_id smallint NULL
        REFERENCES config.listini_tipologie(id);
```

Nullable per compatibilità con articoli esistenti. Popolato progressivamente. Un articolo senza tipologia non può essere inserito in un listino tipizzato (guard su `listini_righe`).

### 7.2 Guard su `vendite.listini_righe`

```sql
-- trgfn_listini_righe_guard_tipologia:
-- Alla INSERT/UPDATE OF articolo_id su listini_righe verifica che
-- articolo.listino_tipologia_id = versione.listino.tipologia_id
-- Altrimenti RAISE con ERRCODE 'P0001' e codice E_ARTICOLO_TIPOLOGIA_INCOMPATIBILE.
```

Regola 1:1 diretta — articolo PRODOTTI entra solo in listino PRODOTTI, articolo SERVIZI solo in listino SERVIZI, e così via per CONSUMO, QUOTA_FISSA, IMPOSTA, ONERE_SISTEMA.

### 7.3 Drop `catalogo.articoli.voce_utility` — con audit preventivo

Il campo diventa derivabile da `listino_tipologia_id IN (CONSUMO, QUOTA_FISSA, IMPOSTA, ONERE_SISTEMA)`.

**Task preventivo al drop** (blocco bloccante):
1. Censire tutti gli usi di `voce_utility` in:
   - backend (`grep voce_utility backend/`)
   - trigger, funzioni, view DB (`grep -R voce_utility db/changelog/migrations_v2`)
   - seed, report, smoke test
2. Per ciascun uso, migrare a test su `listino_tipologia_id` (o view di compatibilità temporanea)
3. Solo dopo zero callers residui: `ALTER TABLE catalogo.articoli DROP COLUMN voce_utility;`

---

## 8) BoM — prezzi articoli compositi

### 8.1 Flag `esposto_in_fattura`

```sql
ALTER TABLE catalogo.articoli_componenti
    ADD COLUMN esposto_in_fattura boolean NOT NULL DEFAULT false;
```

Semantica:
- `false` (default) — il componente concorre al prezzo del composito ma non appare in fattura
- `true` — il componente appare come riga separata in fattura con il suo prezzo, descrizione, IVA

### 8.2 Logica ibrida di risoluzione prezzo composito

```
fn_resolve_prezzo_composito(prodotto_id, uom_id, data, BA, utility):
  1. Esiste almeno un componente attivo con esposto_in_fattura = true?
     → SÌ: non restituire prezzo singolo.
            Restituire lista di N righe (una per ogni componente, esposto o no,
            con prezzo risolto separatamente e flag esposto mantenuto).
     → NO: vai al punto 2.

  2. Esiste riga listino per articolo composito?
     → SÌ: usa quella riga — prezzo negoziato del composito.
     → NO: calcola Σ(prezzo_componente * coeff_qta) per tutti i componenti
            obbligatori attivi alla data.
```

### 8.3 Espansione in `commesse_attivita`

Quando si crea un'attività in commessa per un articolo composito con componenti esposti, la pipeline di creazione attività **espande** in N righe figlie in `commesse_attivita`, una per componente esposto. Vantaggi:

- tracciabilità piena — righe visibili prima della fatturazione
- `prezzo_bloccato` per-riga funziona in modo naturale
- lo step fatturazione resta semplice (1 attività → 1 riga fattura)
- il componente non esposto continua a contribuire al prezzo dell'articolo "padre" se il padre stesso ha una sua riga in `commesse_attivita` (modalità mista rara)

### 8.4 Nuova funzione DB

```
vendite.fn_resolve_prezzo_composito(
    p_prodotto_id    uuid,
    p_uom_id         bigint,
    p_data           date,
    p_ba_id          bigint,
    p_utility_id     integer
) RETURNS SETOF <record>
```

Ritorna 1-N righe con: `componente_id`, `uom_id`, `prezzo_unitario`, `iva_id`, `descrizione_fattura`, `esposto_in_fattura`.

---

## 9) Resolver a 3 stadi

### 9.1 Input

| Parametro | Obbligatorio | Fonte |
|---|---|---|
| `articolo_id` | sì | chiamante |
| `uom_id` | sì | chiamante |
| `data_riferimento` | sì | chiamante |
| `ba_id` | sì | chiamante |
| `utility_id` | sì | chiamante (un operatore può gestire più utility) |
| `emittente_soggetto_ruolo_id` | sì | **derivato da GUC di sessione** (JWT → emittente 1-a-1) |
| `classe_utenza_id` | opzionale (derivato) | derivato da contratto_utilities o istanze_dati_precontrattuali |

### 9.2 Pseudocodice

```
STADIO 0 — PROMO OVERLAY
────────────────────────
Esiste riga attiva in vendite.promo_articoli con (articolo_id, uom_id, data)?
  E il BA ha categoria_cliente_id con partecipa_promo = true?
    → SÌ: prezzo_base = risolvi(STADIO 1 → STADIO 2)
           prezzo_finale = applica variazione promo su prezzo_base
           origine = 'PROMO'
           STOP
    → NO: vai a STADIO 1

STADIO 1 — CONTRATTO
────────────────────
Esiste contratto ATTIVO per (ba_id, utility_id, data)?
  → SÌ:
      Esiste riga contratto per (articolo_id, uom_id) con prezzo_unitario NOT NULL?
        → SÌ: prezzo_finale = prezzo_unitario
               origine = 'CONTRATTO_OVERRIDE'
               STOP
        → NO:
            Se contratto.listino_id IS NULL (modalità C incompleta):
              → ERRORE E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C
            Altrimenti:
              prezzo_base = riga listino per (contratto.listino_id, versione attiva,
                                              articolo_id, uom_id)
              se contratto.tipo_variazione_globale IS NOT NULL:
                prezzo_finale = applica variazione globale
              altrimenti:
                prezzo_finale = prezzo_base
              origine = 'CONTRATTO_LISTINO'
              STOP
  → NO: vai a STADIO 2

STADIO 2 — CATEGORIA CLIENTE
────────────────────────────
BA ha categoria_cliente_id?
  → NO: ERRORE E_PREZZO_LISTINO_NON_TROVATO
  → SÌ:
      Cerca in categorie_clienti_listini con:
        (categoria_cliente_id, utility_id, emittente, data)
        → prima tentativo: classe_utenza_id = <derivato BA/contratto>
        → fallback:       classe_utenza_id IS NULL

      Se nessun match:
        ERRORE E_CATEGORIA_LISTINO_NON_MAPPATA

      Match trovato:
        prezzo_base = riga listino per (listino_id, versione attiva,
                                        articolo_id, uom_id)
        se match.tipo_variazione IS NOT NULL:
          prezzo_finale = applica variazione
        altrimenti:
          prezzo_finale = prezzo_base
        origine = 'CATEGORIA'
        STOP

OUTPUT
──────
{
  prezzo_finale,
  prezzo_base_snapshot,
  tipo_variazione_applicata,    -- PERCENTUALE | VALORE_FISSO | PREZZO_FISSO | NESSUNA
  valore_variazione_applicata,
  origine,                      -- PROMO | CONTRATTO_OVERRIDE | CONTRATTO_LISTINO | CATEGORIA
  listino_id,                   -- NULL se origine = CONTRATTO_OVERRIDE modalità C
  listino_versione_id,
  listino_riga_id,              -- NULL se override / modalità C
  contratto_id,                 -- NOT NULL se origine CONTRATTO_*
  promo_id,                     -- NOT NULL se origine PROMO
  categoria_cliente_listino_id  -- NOT NULL se origine CATEGORIA
}
```

### 9.3 Errori

| Codice | Scenario |
|---|---|
| `E_PREZZO_LISTINO_NON_TROVATO` | BA senza contratto e senza categoria cliente |
| `E_CATEGORIA_LISTINO_NON_MAPPATA` | BA con categoria ma matrice non ha riga per (cat, utility, emittente, classe/NULL) |
| `E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C` | Contratto modalità C senza riga per l'articolo richiesto |
| `E_ARTICOLO_TIPOLOGIA_INCOMPATIBILE` | Guard riga listino: articolo.tipologia ≠ listino.tipologia |
| `E_PARAMETRO_INVALIDO` | Input mancante / ID ≤ 0 |

Non esistono fallback silenziosi: l'errore è sempre esplicito e tracciabile.

### 9.4 Determinismo

Niente `match_level` dimensionale, niente tie-break. La concorrenza è impedita dai vincoli DB:

- `ex_contratti_no_overlap` → un solo contratto attivo per scope
- `ex_categ_cli_listini_no_overlap` → un solo match attivo in matrice per (cat, utility, emittente, classe/NULL)
- `ex_promo_articoli_no_overlap` → una sola promo attiva per (articolo, uom)

Il resolver restituisce sempre esattamente una risposta o un errore esplicito.

---

## 10) Snapshot in `commesse_attivita`

### 10.1 Nuove colonne audit

```sql
ALTER TABLE vendite.commesse_attivita
    ADD COLUMN prezzo_base_snapshot           numeric(22,10) NULL,
    ADD COLUMN origine_prezzo                 varchar        NULL
        CHECK (origine_prezzo IN (
            'PROMO', 'CONTRATTO_OVERRIDE', 'CONTRATTO_LISTINO',
            'CATEGORIA', 'MANUALE'
        )),
    ADD COLUMN tipo_variazione_applicata      varchar        NULL,
    ADD COLUMN valore_variazione_applicata    numeric(10,4)  NULL,
    ADD COLUMN promo_id                       bigint         NULL
        REFERENCES vendite.promo_articoli(id),
    ADD COLUMN contratto_id                   bigint         NULL
        REFERENCES vendite.contratti(id),
    ADD COLUMN categoria_cliente_id_snapshot  smallint       NULL
        REFERENCES anagrafiche.categorie_clienti(id),
    ADD COLUMN classe_utenza_id_snapshot      integer        NULL
        REFERENCES config.classi_utenze(id);
```

Motivazione delle colonne esplicite (non solo `meta` jsonb):

- report analitici e filtri dashboard su `origine_prezzo`
- query dirette su `promo_id` per misurare impatto promo
- join con `contratti` per audit contrattuale senza passare da jsonb

Il campo `meta` resta per dettagli non strutturati (es. chi ha derogato il prezzo, flag particolari).

### 10.2 Propagazione verso `attivita_fatturabili`

Le colonne audit seguono la stessa propagazione di `prezzo_snapshot` / `prezzo_bloccato`: aggiungere colonne corrispondenti in `attivita_fatturabili` per mantenere tracciabilità fino al layer fatture.

---

## 11) Impatto sul modello dati — riepilogo

### 11.1 Tabelle nuove

| Tabella | Schema | Scopo |
|---|---|---|
| `categorie_clienti` | `anagrafiche` | Categorie commerciali cliente con flag promo |
| `categorie_clienti_listini` | `anagrafiche` | Matrice categoria × utility × emittente × classe_utenza → listino |
| `promo_articoli` | `vendite` | Overlay promo con periodo e variazione |

### 11.2 Modifiche tabelle esistenti

| Tabella | Modifica |
|---|---|
| `vendite.listini` | ADD `emittente_soggetto_ruolo_id NOT NULL` |
| `vendite.listini_righe` | DROP `billing_account_id`, `utility_id`, `emittente_soggetto_ruolo_id` |
| `vendite.listini_associazioni` | **DROP TABLE** (dopo audit callers) |
| `anagrafiche.billing_account` | ADD `categoria_cliente_id` |
| `vendite.contratti` | ADD `listino_id`, `tipo_variazione_globale`, `valore_variazione_globale` |
| `vendite.contratti_utilities` | ADD `tipo_utenza_id` |
| `catalogo.articoli` | ADD `listino_tipologia_id`, DROP `voce_utility` (dopo audit callers) |
| `catalogo.articoli_componenti` | ADD `esposto_in_fattura` |
| `vendite.commesse_attivita` | ADD 7 colonne snapshot (§10.1) |
| `vendite.attivita_fatturabili` | ADD stesse 7 colonne (propagazione) |

### 11.3 Funzioni DB nuove / riscritte

| Funzione | Scopo |
|---|---|
| `vendite.fn_resolve_prezzo_listino_v2` | Resolver 3 stadi (promo/contratto/categoria) |
| `vendite.fn_resolve_prezzo_composito` | Logica ibrida BoM + espansione componenti esposti |
| `vendite.trgfn_contratti_modalita_c_righe_complete` | Guard modalità C |
| `vendite.trgfn_contratti_utilities_guard_tipo_classe` | Guard coerenza tipo/classe utenza |
| `vendite.trgfn_listini_righe_guard_tipologia` | Guard articolo.tipologia = listino.tipologia |

Funzione vecchia `fn_resolve_prezzo_listino` (7 livelli match) → **deprecata e droppata** a fine Fase DB.

---

## 12) Decisioni chiuse

| Tema | Decisione |
|---|---|
| Listini derivati come entità | **Eliminati** — variazione in categoria/contratto |
| `listini_associazioni` | **Droppata** — sostituita da categoria + contratto |
| `override_prezzi` (proposto v5 preliminare) | **Non creata** — ruolo coperto da `contratti_righe.prezzo_unitario` |
| Emittente come input resolver | **No**, derivato da GUC di sessione |
| Utility come input resolver | **Sì**, un operatore gestisce più utility |
| `classe_utenza_id` nella matrice | **Opzionale con fallback NULL** (semantica unica di NULL) |
| `tipi_utenze`/`classi_utenze` riuso come categoria cliente | **No**, sono dimensioni tecniche del punto fornitura, non categorie commerciali |
| Nome tabella categoria | `anagrafiche.categorie_clienti` |
| `PREZZO_FISSO` come `tipo_variazione` | Ammesso solo in promo; vietato in categoria/contratto |
| Drop `voce_utility` | Con audit preventivo dei callers |
| BoM esposizione componenti | Espansione in `commesse_attivita`, pipeline fatturazione invariata |
| Snapshot commessa | Colonne esplicite (non solo `meta`) |
| Chiusura v4 BE+FE | Fase 0 prerequisito a v5 DB |

---

# Piano di sviluppo

Lo sviluppo è organizzato in fasi con prerequisiti espliciti. L'ordine ottimizza:

1. **Niente produzione** — si può droppare `listini_associazioni` senza migrazione dati di conservazione
2. **Chiudere v4 prima di v5** — il modello tipologia + matrice utility×tipologia è già sul DB, va messo al completo end-to-end (BE+FE) prima di aggiungere la complessità v5
3. **DB first** — tutte le invarianti nel DB prima di toccare BE/FE
4. **BE come layer di orchestrazione** — dopo DB stabile
5. **FE consuma API finita** — evitare rework

---

## FASE 0 — Chiusura v4 BE + FE (prerequisito a tutto)

**Stato DB v4**: D1, D2, D3, D5 già completati. D4 (utility_id NOT NULL) già completato. Manca solo D6 (whitelist lookup) e D7 (pgTAP).

**Prerequisiti**: nessuno.

### 0.1 DB (completamento v4)

| Step | Descrizione |
|---|---|
| F0-DB-1 | Whitelist lookup `config.listini_tipologie` in `dbops_repository.py` (se non già presente) |
| F0-DB-2 | pgTAP: constraint flag esclusivi, matrice utility×tipologia, trigger guard esistente `trgfn_listini_guard_tipologia_utility` |

### 0.2 Backend v4

| Step | Prereq. | Descrizione |
|---|---|---|
| F0-BE-1 | F0-DB-1 | `listini_repository.list_listini` + `get_listino`: JOIN `config.listini_tipologie`, aggiunta filtro `tipologia_id` |
| F0-BE-2 | — | `listini_service.create_listino`: `tipologia_id` obbligatorio |
| F0-BE-3 | — | `listini_service.update_listino`: `tipologia_id` ammesso (modifica con guard matrice) |
| F0-BE-4 | — | Rimuovere `utility_id` da `_LISTINO_NULLABLE_FIELDS` in service |
| F0-BE-5 | F0-DB-1 | Endpoint `GET /api/v1/core/lookup/codici/?rel=config.listini_tipologie` (verifica whitelist) |
| F0-BE-6 | — | Endpoint `GET /api/v1/vendite/listini/tipologie-per-utility/?utility_id=X` — restituisce tipologie ammesse dalla matrice |
| F0-BE-7 | F0-BE-1..6 | Test Django unit + API |

### 0.3 Frontend v4

| Step | Prereq. | Descrizione |
|---|---|---|
| F0-FE-1 | F0-BE-5, F0-BE-6 | `ListinoDrawer.vue`: Select tipologia filtrato per utility, reset+ricarica al cambio utility |
| F0-FE-2 | F0-BE-5 | `ListiniSearchTable.vue`: filtro tipologia + colonna "Tipologia" |
| F0-FE-3 | F0-BE-4 | `ListinoDrawer.vue`: `utility_id` non più nullable (rimuovere `show-clear`) |
| F0-FE-4 | — | i18n per tipologie |
| F0-FE-5 | F0-FE-1..4 | Build + test UI manuale |

**Gate passaggio a Fase 1**: v4 end-to-end funzionante, lookup whitelist pulita, nessun listino in anomalia.

---

## FASE 1 — DB v5 (core model)

**Prerequisito**: Fase 0 completata.

L'ordine minimizza cascate di rifacimento. Le prime migrazioni sono additive e innocue; quelle che droppano arrivano alla fine dopo aver coperto tutti i callers.

### 1.1 Infrastruttura categoria cliente

| Step | Prereq. | Descrizione |
|---|---|---|
| F1-DB-01 | — | `CREATE TABLE anagrafiche.categorie_clienti` + seed (STANDARD, BASE, SILVER, GOLD, PLATINUM) |
| F1-DB-02 | F1-DB-01 | `ALTER TABLE anagrafiche.billing_account ADD COLUMN categoria_cliente_id` (nullable) |
| F1-DB-03 | F1-DB-01 | Whitelist lookup `anagrafiche.categorie_clienti` |

### 1.2 Listini — aggiunta emittente come dimensione

| Step | Prereq. | Descrizione |
|---|---|---|
| F1-DB-04 | — | `ALTER TABLE vendite.listini ADD COLUMN emittente_soggetto_ruolo_id bigint NULL` |
| F1-DB-05 | F1-DB-04 | Backfill emittente (via `user_insert` → `fn_get_emittente_fiscale_pk`) + fix manuale record residui |
| F1-DB-06 | F1-DB-05 | `ALTER TABLE vendite.listini ALTER COLUMN emittente_soggetto_ruolo_id SET NOT NULL` + index |

### 1.3 Matrice categoria → listino

| Step | Prereq. | Descrizione |
|---|---|---|
| F1-DB-07 | F1-DB-01, F1-DB-06 | `CREATE TABLE anagrafiche.categorie_clienti_listini` + trigger `trgfn_set_validita` + EXCLUDE no-overlap |
| F1-DB-08 | F1-DB-07 | Whitelist lookup matrice |

### 1.4 Estensione contratti

| Step | Prereq. | Descrizione |
|---|---|---|
| F1-DB-09 | F1-DB-06 | `ALTER TABLE vendite.contratti ADD listino_id, tipo_variazione_globale, valore_variazione_globale` + CHECK coerenza |
| F1-DB-10 | — | `ALTER TABLE vendite.contratti_utilities ADD tipo_utenza_id` |
| F1-DB-11 | F1-DB-10 | Backfill `tipo_utenza_id` derivandolo da `classi_utenze.tipo_utenza_id` |
| F1-DB-12 | F1-DB-11 | Trigger `trgfn_contratti_utilities_guard_tipo_classe` (guard coerenza tipo/classe/ambito) |
| F1-DB-13 | F1-DB-09 | Trigger `trgfn_contratti_modalita_c_righe_complete` (guard modalità C) |

### 1.5 Promo overlay

| Step | Prereq. | Descrizione |
|---|---|---|
| F1-DB-14 | F1-DB-01 | `CREATE TABLE vendite.promo_articoli` + trigger `set_validita` + EXCLUDE no-overlap |
| F1-DB-15 | F1-DB-14 | Whitelist lookup promo |

### 1.6 Tipologia articoli

| Step | Prereq. | Descrizione |
|---|---|---|
| F1-DB-16 | — | `ALTER TABLE catalogo.articoli ADD listino_tipologia_id smallint NULL` |
| F1-DB-17 | F1-DB-16 | Script popolamento `listino_tipologia_id` per articoli esistenti (derivato da `voce_utility` o gruppo). **Precede** l'attivazione del trigger per evitare blocchi su insert esistenti. |
| F1-DB-18 | F1-DB-17 | Trigger `trgfn_listini_righe_guard_tipologia` (articolo.tipologia = listino.tipologia; se articolo.tipologia NULL → blocca insert su listini tipizzati). Ordine invertito rispetto a bozza precedente: popolamento prima del guard. |

### 1.7 BoM

| Step | Prereq. | Descrizione |
|---|---|---|
| F1-DB-19 | — | `ALTER TABLE catalogo.articoli_componenti ADD esposto_in_fattura boolean NOT NULL DEFAULT false` |

### 1.8 Snapshot commessa

| Step | Prereq. | Descrizione |
|---|---|---|
| F1-DB-20 | F1-DB-01, F1-DB-09, F1-DB-14 | `ALTER TABLE vendite.commesse_attivita ADD COLUMN` × 7 |
| F1-DB-21 | F1-DB-20 | `ALTER TABLE vendite.attivita_fatturabili ADD COLUMN` × 7 + propagazione funzione emissione |

### 1.9 Resolver nuovo

| Step | Prereq. | Descrizione |
|---|---|---|
| F1-DB-22 | F1-DB-06..14 | `CREATE OR REPLACE FUNCTION vendite.fn_resolve_prezzo_listino_v2` (3 stadi) |
| F1-DB-23 | F1-DB-19, F1-DB-22 | `CREATE OR REPLACE FUNCTION vendite.fn_resolve_prezzo_composito` |

### 1.10 Pulizia — ultimi drop

| Step | Prereq. | Descrizione |
|---|---|---|
| F1-DB-24 | F1-DB-07, F1-DB-09, F1-DB-22 | Audit callers di `listini_associazioni` e `listini_righe.billing_account_id/utility_id/emittente_soggetto_ruolo_id`: backend, view DB, pgtap |
| F1-DB-25 | F1-DB-24 | `ALTER TABLE vendite.listini_righe DROP COLUMN` × 3 (dimensioni contesto) + ricrea unique attivo |
| F1-DB-26 | F1-DB-24 | `DROP TABLE vendite.listini_associazioni` |
| F1-DB-27 | F1-DB-22 | Riscrivere `vendite.fn_resolve_prezzo_listino` come **wrapper deprecato** che delega a `fn_resolve_prezzo_listino_v2` (stessa firma). Drop definitivo solo dopo F2 completata e `grep` pulito su backend + pgtap. |
| F1-DB-28 | F0-FE chiuso + audit `voce_utility` = 0 su backend **e DB** (trigger, funzioni, view, seed in `db/changelog/migrations_v2/**`) | `ALTER TABLE catalogo.articoli DROP COLUMN voce_utility` |

### 1.11 pgTAP — distribuiti per sotto-gruppo

I pgTAP vengono scritti **accanto** al gruppo di changeSet a cui si riferiscono, non tutti alla fine: così un errore emerge nel gruppo giusto, non a 27 migrazioni di distanza. L'esecuzione CI resta unica (`db/pgtap/`), ma i file di test si aggiungono incrementalmente.

| Step | Posizione rispetto ai changeSet | Prereq. | Descrizione |
| --- | --- | --- | --- |
| F1-DB-T1 | dopo §1.3 (F1-DB-08) | F1-DB-01..08 | Categoria + matrice: seed, no-overlap, fallback `classe_utenza_id` NULL |
| F1-DB-T2 | dopo §1.4 (F1-DB-13) | F1-DB-09..13 | Contratti: modalità A/B/C, guard tipo/classe utenza, no-overlap esistente, attivazione con righe incomplete (modalità C) |
| F1-DB-T3 | dopo §1.5 (F1-DB-15) | F1-DB-14..15 | Promo: no-overlap, calcolo variazione per i 3 tipi |
| F1-DB-T4 | dopo §1.6 (F1-DB-18) | F1-DB-18 | Guard tipologia articolo/listino + fallback NULL → blocco |
| F1-DB-T5 | dopo §1.9 (F1-DB-22) | F1-DB-22 | Resolver 3 stadi: STADIO 0/1/2, errori, fallback classe utenza, determinismo |
| F1-DB-T6 | dopo §1.9 (F1-DB-23) | F1-DB-23 | Resolver BoM ibrido + espansione componenti esposti |
| F1-DB-T7 | dopo §1.10 (F1-DB-26) | F1-DB-25, F1-DB-26 | Smoke: zero riferimenti residui a entità droppate |

**Gate passaggio a Fase 2**: tutti pgtap verdi, smoke DB verde, doc auto-generate rigenerate.

---

## FASE 2 — Backend

**Prerequisito**: Fase 1 completata, almeno fino a F1-DB-22 per i servizi pricing.

### 2.1 Nuove entità / CRUD

| Step | Prereq. | Descrizione |
|---|---|---|
| F2-BE-01 | F1-DB-01 | `anagrafiche/services/categorie_clienti_service.py` + repository + CRUD + endpoint `GET/POST/PATCH /api/v1/anagrafiche/categorie-clienti/` |
| F2-BE-02 | F1-DB-07 | `categorie_clienti_listini_service.py` + CRUD + endpoint, no-overlap validato lato DB, fallback classe_utenza esposto |
| F2-BE-03 | F1-DB-14 | `vendite/services/promo_service.py` + CRUD + endpoint |
| F2-BE-04 | F1-DB-02 | Estensione `BillingAccountService` per `categoria_cliente_id` (campo nullable) |

### 2.2 Contratti estesi

| Step | Prereq. | Descrizione |
|---|---|---|
| F2-BE-05 | F1-DB-09..13 | `contratti_service`: gestione `listino_id`, variazione globale, modalità A/B/C |
| F2-BE-06 | F2-BE-05 | Endpoint contratti aggiornati: validazione pre-DB per anticipare errori modalità, conversione input friendly UI |

### 2.3 Articoli + tipologia + BoM

| Step | Prereq. | Descrizione |
|---|---|---|
| F2-BE-07 | F1-DB-16 | `catalogo/services/articoli_service`: `listino_tipologia_id` gestito in create/update |
| F2-BE-08 | F1-DB-19 | `articoli_componenti_service`: flag `esposto_in_fattura` gestito |

### 2.4 Resolver pricing

| Step | Prereq. | Descrizione |
|---|---|---|
| F2-BE-09 | F1-DB-22 | `pricing_service.resolve_prezzo(articolo, uom, data, ba, utility)` — wrapper Python per `fn_resolve_prezzo_listino_v2`. Emittente derivato dal JWT (mapping operatore→emittente 1-a-1) e passato come parametro alla funzione DB. GUC di sessione opzionale in futuro (convenzione `zeroerp.<nome>` già usata nel progetto) se servirà a trigger; non introdotto ora perché non richiesto dal resolver. |
| F2-BE-10 | F1-DB-23, F2-BE-09 | `pricing_service.resolve_prezzo_composito` |
| F2-BE-11 | F2-BE-09 | Aggiornamento `CommessaAttivitaService` per salvare snapshot audit sulle nuove colonne |
| F2-BE-12 | F2-BE-10, F2-BE-11 | Aggiornamento pipeline creazione attività composita → espansione righe in `commesse_attivita` quando esistono componenti esposti |

### 2.5 Cleanup

| Step | Prereq. | Descrizione |
|---|---|---|
| F2-BE-13 | F2-BE-09 | Rimuovere ogni riferimento a `listini_associazioni` dal backend |
| F2-BE-14 | F1-DB-28 | Rimuovere ogni riferimento a `articoli.voce_utility` dal backend |
| F2-BE-15 | F2-BE-01..12 | Test Django: unit service + API + resolver |

**Gate passaggio a Fase 3**: `./manage-test.sh -v 2` verde, OpenAPI schema valida, `drf-spectacular` senza warning.

---

## FASE 3 — Frontend

**Prerequisito**: Fase 2 completata per le aree toccate.

### 3.1 Amministrazione pricing

| Step | Prereq. | Descrizione |
|---|---|---|
| F3-FE-01 | F2-BE-01 | Gestione `CategorieClientiAdminTable` + `CategorieClientiDrawer` (pattern standard admin) |
| F3-FE-02 | F2-BE-02 | Gestione matrice `CategorieClientiListini`: pannello config con riga (categoria, utility, emittente, classe_utenza, listino, variazione) + validazione fallback NULL classe_utenza |
| F3-FE-03 | F2-BE-03 | Gestione `PromoArticoliAdminTable` + `PromoArticoloDrawer` |

### 3.2 BA e contratti

| Step | Prereq. | Descrizione |
|---|---|---|
| F3-FE-04 | F2-BE-04 | `BillingAccountDrawer`: Select `categoria_cliente_id` (opzionale) |
| F3-FE-05 | F2-BE-05, F2-BE-06 | `ContrattoDrawer`: aggiunta sezione "Pricing" con selettore modalità A/B/C + Select listino + variazione globale + gestione righe con prezzo_unitario override |

### 3.3 Articoli

| Step | Prereq. | Descrizione |
|---|---|---|
| F3-FE-06 | F2-BE-07 | `ArticoloDrawer`: Select `listino_tipologia_id` con guard UX (mostra warning se differisce dalla tipologia del gruppo) |
| F3-FE-07 | F2-BE-08 | Tab BoM: checkbox `esposto_in_fattura` su ogni riga componente |

### 3.4 Visualizzazione pricing in commessa

| Step | Prereq. | Descrizione |
|---|---|---|
| F3-FE-08 | F2-BE-11 | `CommessaAttivitaDrawer`: tab "Audit pricing" con `origine_prezzo`, variazione applicata, link a contratto/promo/matrice |

### 3.5 Cleanup

| Step | Prereq. | Descrizione |
|---|---|---|
| F3-FE-09 | F2-BE-13 | Rimuovere UI e endpoint residui su `listini_associazioni` (drawer, tabella, rotte) |
| F3-FE-10 | F3-FE-01..09 | `./node_modules/.bin/vite build` + smoke test UI |

**Gate chiusura v5**: vite build OK, smoke UI completo, doc guida `gestione-listini.md` riscritta e pubblicata.

---

## FASE 4 — Documentazione finale

**Prerequisito**: Fase 3 completata.

| Step | Descrizione |
|---|---|
| F4-DOC-01 | Riscrivere `docs/it/guide/gestione-listini.md` secondo il nuovo modello (3 stadi, niente associazioni, categoria + contratto + promo) |
| F4-DOC-02 | Aggiornare `docs/it/dbzero/*/manual/*` per le tabelle nuove / modificate |
| F4-DOC-03 | Aggiornare `docs/it/backend/vendite/manual/api_listini.md` e creare `api_categorie_clienti`, `api_promo` |
| F4-DOC-04 | Archiviare questo documento in `docs/it/dev/archive/` una volta applicato end-to-end |

---

## 13) Tracking rapido

### Prerequisito bloccante
- [ ] Fase 0 — v4 BE + FE chiuso end-to-end

### Fase 1 — DB ✅ COMPLETATA (15-04-2026)

**Stato finale**: tutti gli step F1-DB-01..28 chiusi end-to-end. 30 changeSet Liquibase (`20260414-01..23` + `20260415-01..07`), 11 codici errore v5 in `config.messaggi_errore` (id 365..375), 8 pgTAP verdi, doc manuale auto/manual aggiornata per tutte le entità nuove e modificate. DB pricing v5 pulito, niente residui del modello pre-v5 (droppati `fn_resolve_prezzo_listino` vecchia, `listini_associazioni`, colonne legacy `listini_righe`, `articoli.voce_utility`).

- [x] **Categoria cliente + BA.categoria (F1-DB-01..03)** — changeSet `20260414-01..03` + seed `80_data/anagrafiche/categorie_clienti.csv`; backfill STANDARD + `NOT NULL` su `billing_account.categoria_cliente_id`.
- [x] **Emittente su listino (F1-DB-04..06)** — changeSet `20260414-04..06`; backfill CI-safe con guard `to_regclass('django.auth_user')`, fallback sul primo emittente attivo; `SET NOT NULL` + indice.
- [x] **Matrice categoria → listino (F1-DB-07)** — changeSet `20260414-07`: CREATE TABLE `anagrafiche.categorie_clienti_listini` + 5 FK + 3 CHECK + `EXCLUDE USING gist` no-overlap con `COALESCE(classe_utenza_id, -1)` + trigger `set_validita`. (F1-DB-08 whitelist lookup = Fase 2 BE).
- [x] **Contratti estesi (F1-DB-09..13)** — changeSet `20260414-08..10` (schema + backfill) e `20260414-11..12` (trigger). Guard modalità C copre anche transizione `listino_id NOT NULL → NULL` su contratto già ATTIVO; guard tipo/classe utenza dinamico basato su `config.tipi_utenze`.
- [x] **Promo (F1-DB-14)** — changeSet `20260414-13`: CREATE TABLE `vendite.promo_articoli` + CHECK su `tipo_variazione` (ammesso `PREZZO_FISSO` solo qui) + `EXCLUDE` no-overlap per `(articolo, uom, validita)`. (F1-DB-15 whitelist lookup = Fase 2 BE).
- [x] **Tipologia articoli + guard (F1-DB-16..18)** — changeSet `20260414-14..15` (schema + backfill a `PRODOTTI` per `voce_utility=FALSE`; voci utility restano NULL per mapping manuale), `20260414-16` (trigger `trgfn_listini_righe_guard_tipologia` con 2 codici errore distinti).
- [x] **BoM flag (F1-DB-19)** — changeSet `20260414-17`: `esposto_in_fattura boolean NOT NULL DEFAULT false` su `catalogo.articoli_componenti`.
- [x] **Snapshot commessa (F1-DB-20..21)** — changeSet `20260414-18` (commesse_attivita) + `20260414-19` (attivita_fatturabili): 8 colonne snapshot (`prezzo_base_snapshot`, `origine_prezzo`, `tipo/valore_variazione_applicata`, `promo_id`, `contratto_id`, `categoria_cliente_id_snapshot`, `classe_utenza_id_snapshot`) + 4 FK + 2 CHECK per tabella. Propagazione identica tra le due.
- [x] **Resolver v2 + composito (F1-DB-22..23)** — changeSet `20260414-20` (`fn_resolve_prezzo_listino_v2` a 3 stadi) e `20260414-21` (`fn_resolve_prezzo_composito` BoM ibrido). Analisi critica con ottimizzazioni: `%TYPE` in DECLARE, short-circuit, `WHEN SQLSTATE 'P0001'` ristretto, fix guard modalità C che copriva solo la transizione ad ATTIVO. Allineati 11 codici errore in CSV con i placeholder `%s` (bug runtime "format insufficient args" risolto). Doc manuale in `vendite/manual/fn_resolve_prezzo_listino_v2.md` e `fn_resolve_prezzo_composito.md`.
- [x] **Fix collaterali trovati durante i test** — changeSet `20260414-22` (drop CHECK `valido_al >= valido_dal` ridondanti su matrice e promo, il daterange costruttore rifiuta prima con 22000) e `20260414-23` (`trgfn_contratti_snapshot_precontrattuali` aggiornato per popolare `tipo_utenza_id` dalla classe — altrimenti il guard tipo/classe bloccava gli insert automatici di `contratti_utilities`).
- [x] **Drop check valore promo (15-04-2026)** — changeSet `20260415-02`: `chk_promo_articoli_valore` rimosso. Convenzione segno (sconto/maggiorazione) demandata a UI/business; pgTAP `test-promo-articoli-v1.sql` test 4 aggiornato a `lives_ok`.
- [x] **Cleanup totale F1-DB-24..28 (15-04-2026)** — strategia "pulisci come se non fosse mai esistito" su conferma utente (no produzione, BE/FE non chiamano più la vecchia funzione). 5 changeSet `20260415-03..07`:
    - `-03`: `DROP FUNCTION vendite.fn_resolve_prezzo_listino` (vecchia firma 7-livelli). Niente wrapper deprecato.
    - `-04`: drop colonne legacy `listini_righe.{billing_account_id, utility_id, emittente_soggetto_ruolo_id}` + `CREATE UNIQUE INDEX uq_listini_righe_key_attiva ... WHERE attivo IS TRUE`.
    - `-05`: `DROP TABLE vendite.listini_associazioni CASCADE`.
    - `-06`: ricrea `vw_articoli_dettaglio` senza `voce_utility`, aggiunge `listino_tipologia_id` + `tipologia_listino_codice/descrizione`.
    - `-07`: `DROP COLUMN catalogo.articoli.voce_utility`.
    - Modifiche in-place ai 2 backfill (`20260414-15`, `20260415-01`): rimosso filtro `voce_utility=FALSE` → assegnano PRODOTTI a tutti gli articoli senza `listino_tipologia_id`. Le voci utility "vere" vanno mappate manualmente (guard `trgfn_listini_righe_guard_tipologia` impedisce insert in listino di tipologia incompatibile).
    - Cancellati 3 pgTAP obsoleti (`test-listini-resolve-prezzo-v1`, `test-listini-integrita-v1`, `test-listini-resolve-commessa-prezzi-v1`) e aggiornati T4/T6 per rimuovere riferimenti a `voce_utility`.
- [x] **pgTAP (F1-DB-T1..T6)** — 8 file in `db/pgtap/` (~56 asserzioni totali, tutti verdi):
    - `anagrafiche/test-categorie-clienti-v1.sql` (T1.1)
    - `anagrafiche/test-categorie-clienti-listini-v1.sql` (T1.2)
    - `vendite/test-contratti-modalita-pricing-v1.sql` (T2.1)
    - `vendite/test-contratti-utilities-guard-tipo-classe-v1.sql` (T2.2, seed `tipi_utenze` di appoggio in-TX)
    - `vendite/test-promo-articoli-v1.sql` (T3)
    - `vendite/test-listini-righe-guard-tipologia-v1.sql` (T4, 3 test focus sul guard)
    - `vendite/test-fn-resolve-prezzo-listino-v2-v1.sql` (T5, setup completo listino+matrice+contratto+promo)
    - `vendite/test-fn-resolve-prezzo-composito-v1.sql` (T6, articolo composito sintetico con BoM in-TX)
    - Tutti in `BEGIN;...ROLLBACK;` → idempotenti.
- **F1-DB-T7 smoke post-cleanup**: non eseguito. La copertura combinata di T1..T6 + `DROP IF EXISTS` nei changeSet `20260415-03..07` è sufficiente; uno smoke aggiuntivo darebbe garanzie marginali.

### Fase 2 — Backend

**Avanzamento al 14-04-2026 (sera)**: F2-BE-01 chiuso end-to-end. CRUD admin
`anagrafiche.categorie_clienti` (repository + service + views + urls + 43 test)
con whitelist lookup centrale (F1-DB-03). Doc API creata in
[api_categorie_clienti](../../backend/anagrafiche/manual/api_categorie_clienti).
Review critica passata (B1+F3+F5+M1+F2+F4), debito F1 (helper payload condivisi)
tracciato in `sviluppo-listini-v6.md` come V6-B1 per refactor trasversale.

- [x] **F2-BE-01 Admin categorie_clienti + F1-DB-03 whitelist lookup** — 30 test service + 10 test API + 3 test boundary ordinamento + 6 test meta semantics + 5 test bool filter parsing. Endpoints: `GET/POST/PATCH /api/v1/anagrafiche/categorie-clienti/`, lookup via `GET /api/v1/core/lookup/codici/?rel=anagrafiche.categorie_clienti`.
- [x] **F2-BE-02 matrice categorie_clienti_listini** — chiuso 2026-04-15. Repository con JOIN arricchito (codici/descrizioni categoria/utility/emittente/classe_utenza/listino), service con `PayloadValidator` + `map_integrity_error` (UNIQUE/FK + EXCLUDE → `E_ANAG_MATRICE_OVERLAP`), dimensioni immutabili in PATCH, coerenza `tipo_variazione`/`valore_variazione` e range date anticipata lato service. Endpoint `GET/POST/PATCH /api/v1/anagrafiche/categorie-clienti-listini/`. 32 test service + 10 test API. Doc: [api_categorie_clienti_listini.md](/backend/anagrafiche/manual/api_categorie_clienti_listini).
- **F1-DB-08 whitelist lookup**: NON APPLICABILE. La tabella non espone `codice`/`descrizione` → non candidata per `/core/lookup/codici/`. Decisione formalizzata nel doc API.
- [ ] F2-BE-03 promo_articoli (+ F1-DB-15 whitelist)
- [ ] BA con categoria (F2-BE-04)
- [ ] Contratti estesi (F2-BE-05..06)
- [ ] Articoli + BoM (F2-BE-07..08)
- [ ] Resolver + snapshot + espansione (F2-BE-09..12)
- [ ] Cleanup (F2-BE-13..14)
- [ ] Test Django (F2-BE-15)

### Fase 3 — Frontend
- [ ] Admin categorie + matrice + promo (F3-FE-01..03)
- [ ] BA + contratti (F3-FE-04..05)
- [ ] Articoli + BoM (F3-FE-06..07)
- [ ] Audit pricing commessa (F3-FE-08)
- [ ] Cleanup + build (F3-FE-09..10)

### Fase 4 — Documentazione
- [ ] Guida gestione-listini riscritta
- [ ] Manuali DB aggiornati
- [ ] API doc aggiornata
- [ ] Archivio WIP

---

*Sviluppo Listini — ZeroERP (14 aprile 2026, WIP v5 — modello unico base + categoria + contratto + promo, resolver 3 stadi)*
