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
    CONSTRAINT chk_promo_articoli_date     CHECK (valido_al >= valido_dal)
    -- NOTE: il vincolo originario `chk_promo_articoli_valore` (>0 per
    -- PERCENTUALE/VALORE_FISSO, >=0 per PREZZO_FISSO) e' stato dropped
    -- nel changeSet 20260415-02 per ammettere valori negativi (sconto)
    -- coerenti con la formula matematica del resolver (§6.3). La
    -- convenzione di segno e' validata lato BE service + UI.
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

-- PERCENTUALE (convenzione firmata: negativo = sconto, positivo = aumento)
prezzo_promo = prezzo_base * (1 + valore_variazione / 100)

-- VALORE_FISSO (convenzione firmata: negativo = sconto, positivo = aumento)
prezzo_promo = prezzo_base + valore_variazione

-- PREZZO_FISSO (prezzo assoluto sostitutivo, sempre >= 0)
prezzo_promo = valore_variazione
```

Coerente con matrice categorie/listini e variazione globale contratto.
BE service rifiuta valore `0` per PERCENTUALE/VALORE_FISSO (no-op), valori
negativi per PREZZO_FISSO (prezzo non puo' essere negativo).

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
| F3-FE-08 | F2-BE-11 | **SPOSTATO** → `gestione-commesse-v2.md` §28. Richiede CommessaAttivitaDrawer (dominio commesse, non listini). |

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
- [x] **F2-BE-03 promo_articoli** — chiuso 2026-04-15. Repository con JOIN articolo/uom. Service con `PayloadValidator` + `map_integrity_error` (UNIQUE codice + 2 FK + EXCLUDE no-overlap → `E_VENDITE_PROMO_OVERLAP`). `PREZZO_FISSO` ammesso solo qui (coerente con doc v5 §6); coerenza tipo/valore anticipata (> 0 per PERCENTUALE/VALORE_FISSO, >= 0 per PREZZO_FISSO). `codice`/`articolo_id`/`uom_id` immutabili in PATCH. 32 test service. Endpoint `GET/POST/PATCH /api/v1/vendite/promo-articoli/`. Doc: [api_promo_articoli.md](/backend/vendite/manual/api_promo_articoli). F1-DB-15 whitelist lookup: **NON APPLICABILE** (tabella senza `codice/descrizione` anagrafici, semantica temporale).
- [x] **F2-BE-04 BA + categoria_cliente_id** — chiuso 2026-04-15. `ClientiRepository.create_billing_account` accetta `categoria_cliente_id` opzionale (default `STANDARD` via subquery); `ClientiService.crea_cliente` estrae `ba_categoria_cliente_id` dal payload. `ClientiRepository.get_cliente` espone categoria joinata. Nuovo `ClientiRepository.update_ba_categoria` + `update_cliente` integra PATCH misto BA+cliente. 6 test service.
- [x] **F2-BE-05 Contratti Pass A (repo + service)** — chiuso 2026-04-15. `ContrattiRepository` (CRUD testata + righe + utility 1:1 + `generate_numero` + lookup stati/utility), `ContrattiService` con validazione pre-DB modalita' A/B/C (listino + variazione globale coppia coerente, C rifiuta variazione), filtro `data_da` default 01-01 anno-1 (feedback_filtro_data_liste), `numero` generato via `script.fn_generate_codice('contratto')` + rifiuto in payload, stato iniziale DRAFT risolto in service, traduzione P0001 trigger -> codici applicativi (`E_CONTRATTO_MODALITA_C_*`, `E_CONTRATTO_UTILITY_TIPO_CLASSE_*`, `E_CONTRATTO_CLASSE_TIPO_INCOERENTE`, `E_CONTRATTO_UTILITY_SENZA_DIMENSIONE_TIPO_CLASSE_VIETATI`) con match multi-substring stretto coerente col pattern `pricing_service`, `map_integrity_error` per UNIQUE (`uq_contratti_numero`, `uq_contratti_utilities_contratto_id`) + EXCLUDE (`ex_contratti_no_overlap` -> `E_VENDITE_CONTRATTO_OVERLAP`) + FK (13 vincoli). 7 nuovi `ErrorPolicy` in `error_policies.py`. 27 test service (incl. integrity mapping overlap, DB error translation, immutabilita' identificativi). Suite 1454 -> 1481 OK.
- [x] **F2-BE-06 Contratti Pass B (views + API + doc)** — chiuso 2026-04-15. `views_contratti.py` + `urls_contratti.py` registrati in `urls_v1.py`. 6 endpoint:
  - `GET/POST /api/v1/vendite/contratti/`
  - `GET/PATCH /api/v1/vendite/contratti/<id>/`
  - `POST /api/v1/vendite/contratti/<id>/cambia-stato/`
  - `POST /api/v1/vendite/contratti/<id>/righe/` + `PATCH/DELETE /<riga_id>/`
  - `POST/PATCH /api/v1/vendite/contratti/<id>/utility/`

  `DomainAPIView` + `area_funzionale="vendite"` (pattern listini, no model_permission). `OpenApiParameter` per ogni filtro lista, `inline_serializer` per request/response. 16 test API (`test_contratti_api.py`) con mock service + JWT. Doc API completa in `api_contratti.md` (input/output/regole/codici errore/dipendenze DB). Suite 1481 -> 1497 OK (+16).
- [x] **F2-BE-07 Articoli + `listino_tipologia_id`** — chiuso 2026-04-15. Aggiunto `listino_tipologia_id` a `ARTICOLI_CREATE_COLUMNS` (ereditato da UPDATE via comprehension) e a `ARTICOLI_DETAIL_COLUMNS` + proiezioni `tipologia_listino_codice`/`tipologia_listino_descrizione` dalla view `vw_articoli_dettaglio` (refresh DB gia' applicato). Validazione via `_ARTICOLO_INT_FIELDS` (nullable int), allineata al pattern degli altri FK articolo. Filtro opzionale `listino_tipologia_id` in `fn_list_articoli` + endpoint `GET /api/v1/catalogo/articoli/?listino_tipologia_id=` con `OpenApiParameter`. Guard semantico articolo↔riga listino a carico del trigger DB `trgfn_listini_righe_guard_tipologia` (fail-fast, `E_ARTICOLO_TIPOLOGIA_INCOMPATIBILE`).
- [x] **F2-BE-08 BoM + `esposto_in_fattura`** — chiuso 2026-04-15. Aggiunto `esposto_in_fattura: bool` a `COMPONENTE_WRITE_COLUMNS` e a `COMPONENTE_DETAIL_COLUMNS`; flag estratto nel loop bool di `_extract_componente_payload` (default DB `false` se omesso). Nessun default esplicito nel service: coerente con pattern "fail parlante" se malformato. Il campo alimenta `fn_resolve_prezzo_composito` BoM ibrido (§8.2 v5) e l'espansione in `commesse_attivita` (F2-BE-12).
- **Test F2-BE-07/08**: 3 nuovi test in `apps.catalogo.tests.services.test_catalogo_service` (listino_tipologia_id ok + validazione float invalid + componente esposto_in_fattura ok). Suite totale: 1454/1454 OK (+3 vs 1451).
- [x] **F2-BE-09+10 Pricing service (resolver v2 + composito)** — chiuso 2026-04-15. `PricingRepository` wrapper su `fn_resolve_prezzo_listino_v2` + `fn_resolve_prezzo_composito`. `PricingService.resolve_prezzo` + `resolve_prezzo_composito` con validazione input tipizzata (UUID, positive int, date) e traduzione `DatabaseError` P0001 in `ServiceError` preservando codici noti (`E_PREZZO_LISTINO_NON_TROVATO`, `E_CATEGORIA_LISTINO_NON_MAPPATA`, `E_PREZZO_LISTINO_RIGA_NON_TROVATA`, `E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C`). Fallback `E_VENDITE_PRICING_FAILED`. 13 test. Doc: [pricing_service.md](/backend/vendite/manual/pricing_service). **Sblocca F2-BE-13/14 cleanup** (coordinamento con DB F1-DB-24..28).
- [x] **F2-BE-11 Snapshot audit BE wiring** — chiuso end-to-end 2026-04-15. DB team ha esteso `fn_upsert_commessa_attivita` (7 parametri snapshot pricing v5 obbligatori senza DEFAULT) e `fn_batch_upsert_commessa_attivita` (estrae le 8 chiavi dal JSONB e le propaga al single-upsert). BE: `CommessaAttivitaInput` dataclass +8 campi opzionali (`prezzo_base_snapshot`, `origine_prezzo`, `tipo/valore_variazione_applicata`, `promo_id`, `contratto_id`, `categoria_cliente_id_snapshot`, `classe_utenza_id_snapshot`), `upsert_attivita` SQL con 8 named params, `_inp_to_jsonb_row` serializza le 8 chiavi allineate al wrapper batch DB. 2 test nuovi. Suite 1497 -> 1499 OK. Nessuna dipendenza DB residua.
- [ ] **F2-BE-12 Espansione pipeline compositi** — bloccato + scope ridiscusso. Richiede wiring `pricing_service.resolve_prezzo_composito` nei 6 source handler con espansione N righe per componente esposto, `segment_key` differenziato per componente e popolazione snapshot audit. Serve decisione architetturale (espansione lato handler Python vs lato `fn_list_*_da_pushare` DB). Sprint separato.
- [x] **F2-BE-13 Cleanup `listini_associazioni`** — chiuso 2026-04-15. Rimossi: `ASSOCIAZIONE_*_COLUMNS` + 5 metodi repo (list/get/create/update/delete + `test_resolver` vecchio) + 5 funzioni service `fn_*_associazione*` + `fn_test_resolver_prezzo` + helper `_get_associazione_or_raise`/`_extract_associazione_payload` + 2 regole `_translate_integrity_error` + 2 classi view `ApiListinoAssociaz*` + `ApiListinoTestPrezzo` + 2 inline serializer + 2 rotte `/associazioni/` + rotta `/test-prezzo/` + 5 test API + 2 test service. `fn_get_listino_dettaglio` non popola piu' il campo `"associazioni"`. `fn_delete_listino` guard solo su `versioni_count` (la colonna `associazioni_count` resta esposta con valore costante 0 per retrocompatibilita' FE finche' DB non droppa la tabella).
- [x] **F2-BE-14 Cleanup `articoli.voce_utility`** — chiuso 2026-04-15. Rimossi in BE: `ARTICOLI_CREATE_COLUMNS["voce_utility"]`, `ARTICOLI_DETAIL_COLUMNS` (proiezione `a.voce_utility`), param repo `list_articoli`/`lookup_articoli`, param service `fn_list_articoli`/`fn_lookup_articoli`, campo serializer `_articolo_write_fields`, 2 `OpenApiParameter`, 2 estrazioni query param, schema + field mapping `CercaArticoliTool` AI. La colonna DB `articoli.voce_utility` e' ora orfana lato BE: safe per `DROP COLUMN` nel batch DB F1-DB-28.
- [ ] Test Django (F2-BE-15)

**Cleanup DB (F1-DB-24..28) sbloccato dopo F2-BE-13/14**: l'ultimo batch atomico puo' ora procedere (DROP `listini_associazioni`, DROP `fn_resolve_prezzo_listino` vecchia, DROP `articoli.voce_utility` + ricreazione `vw_articoli_dettaglio`).

### Fase 3 — Frontend
- [x] **F3-FE-02 Matrice categorie/listini (Amm. Software)** — chiuso 2026-04-15. Pattern UtilitiesTipiRuolo replicato 1:1 per matrice `anagrafiche.categorie_clienti_listini` sotto Amm. Software. File creati: `amministrazione/api/categorieClientiListini.js`, `stores/categorieClientiListini.js`, `components/CategorieClientiListiniSearchTable.vue`, `components/CategoriaClienteListinoDrawer.vue`, `views/CategorieClientiListiniListView.vue`. Filtri toolbar: categoria (`LookupSelect rel="anagrafiche.categorie_clienti"`), utility (`rel="config.utilities"`), emittente (`useLookup(listEmittentiFiscali)` → `option-value="soggetto_ruolo_id"`), listino (`rel="vendite.listini"`), attivo. Drawer campi: 4 dimensioni (immutabili in edit) + listino + tipo/valore variazione opzionale (coppia coerente anticipata UI) + valido_dal/al + attivo. Drawer readonly cumulativo via `useReadonlyMode('amm_software')` parent + `useInjectReadonly` nel drawer (prop `readonly` combinata). Navigation entry + route `/amm-software/matrice-categorie-listini` + i18n namespace `amministrazione.matrice_categorie_listini.*`. BE minimal: `vendite.listini` aggiunto a whitelist lookup + `list_emittenti_fiscali` ora esporta `soggetto_ruolo_id`. Vite build OK, suite BE 1501/1501.
- [x] **F3-FE-01 Admin categorie_clienti (Amm. Software)** — chiuso 2026-04-15. CRUD minimo (list + filtri + create + edit, no delete; disattivazione soft via `attivo`). File creati: `amministrazione/api/categorieClienti.js`, `stores/categorieClienti.js`, `components/CategorieClientiSearchTable.vue`, `components/CategoriaClienteDrawer.vue`, `views/CategorieClientiListView.vue`. Filtri toolbar: search (min 3), partecipa_promo (yes/no/all), attivo. Drawer campi: codice (immutabile in edit, upper-case in create), descrizione, ordinamento, partecipa_promo, attivo. Drawer readonly cumulativo via `useReadonlyMode('amm_software')` parent + `useInjectReadonly`. Nav entry subito prima della matrice (`/amm-software/categorie-clienti`). Pattern UtilitiesTipiRuolo replicato, `DRAWER_WIDTH.SIMPLE`. Vite build OK (bundle 9.28 kB).
- [x] **F3-FE-03 Admin promo_articoli (Vendite)** — chiuso 2026-04-15. CRUD minimo STADIO 0 resolver v5. Dominio `vendite` (scelta esplicita: operativa-commerciale, non admin config). File creati: `vendite/api/promoArticoli.js`, `stores/promoArticoli.js`, `components/PromoArticoliSearchTable.vue`, `components/PromoArticoloDrawer.vue`, `views/PromoArticoliListView.vue`. Filtri toolbar: search, uom, tipo_variazione, attivo. Drawer campi: codice (immutabile in edit), descrizione, articolo (via `ArticoloLookup` core riusabile), uom (`LookupSelect rel="catalogo.unita_misura"`), tipo_variazione (3 valori incl. `PREZZO_FISSO` unico qui), valore (hint segno firmato per PERC/VF, `>=0` per PREZZO_FISSO), valido_dal/al, attivo. Restore `articolo_obj` da display fields per AutoComplete server-side (`_display: codice — descrizione`). Nav entry `/vendite/promo-articoli` + route + i18n namespace `vendite.promo_articoli.*` (28 chiavi). `useReadonlyMode('vendite')` parent. Vite build OK (bundle 13 kB).
  - **Bug fix BE e DB associato**: rimosso vincolo `valore > 0` per PERCENTUALE/VALORE_FISSO (ora `!= 0`) — coerente col resolver matematico (formula `base * (1 + valore/100)` firma negativo = sconto). DB team ha droppato il CHECK `chk_promo_articoli_valore` nel changeSet `20260415-02`. BE aggiornato in `promo_articoli_service.py` + test regressione `test_create_percentuale_negativo_ok`. Doc v5 §6.1 + §6.3 riallineati.
- [ ] BA + contratti (F3-FE-04..05)
- [ ] Articoli + BoM (F3-FE-06..07)
- [x] ~~Audit pricing commessa (F3-FE-08)~~ — SPOSTATO in `gestione-commesse-v2.md` §28
- [ ] Cleanup + build (F3-FE-09..10)

### Fase 4 — Documentazione
- [ ] Guida gestione-listini riscritta
- [ ] Manuali DB aggiornati
- [ ] API doc aggiornata
- [ ] Archivio WIP

---

## Debito tecnico residuo (da affrontare a chiusura v5)

Lista rilevata durante review critica 2026-04-15 post F3-FE-01/02/03. Non blocca lo sprint corrente; da ripulire prima della chiusura v5 (Fase 4 / gate produzione).

- **Search guard 1-2 char cross-store**: tutti gli store admin FE (incl. quelli pre-esistenti UtilitiesTipiRuolo/TipiRuoloTipiIndirizzo) implementano `if (searchTerm.length > 0 && searchTerm.length < 3) return`. Se l'utente digita "abc" (fetch), poi cancella a "ab", la lista NON si aggiorna ma l'input mostra "ab": incoerenza UX. Refactor globale da proporre: svuotare risultati o forzare fetch con search vuoto sotto soglia.
- **Magic string `useReadonlyMode('amm_software'|'vendite'|...)` + `emitDataChanged('categorie_clienti'|...)`**: chiavi dominio/entita' sparse in componenti e store come stringhe libere. Se un dominio viene rinominato, la readonly mode e il refresh cross-tab si rompono silenziosamente. Soluzione: enum centralizzato in `core/constants.js` (es. `READONLY_DOMAINS.AMM_SOFTWARE`, `TAB_ENTITIES.CATEGORIE_CLIENTI`) referenziato sia dai consumer che dai provider.
- **`boolOptions` / `tipoVariazioneOptions` duplicate**: micro-duplicazioni fra SearchTable admin (3 copie di `[null/true/false]`). Candidato per helper `core/components/options.js` con factory `buildBoolOptions(t)` che prende l'i18n handle.
- **UX cambio tipo variazione**: nei drawer (matrice + promo) il cambio da PERCENTUALE a VALORE_FISSO mantiene il valore numerico ma ne cambia la semantica (10 diventa 10€ invece di 10%). Candidato reset automatico del valore al cambio tipo, con toast info.
- **Guida `gestione-listini.md` da riscrivere**: il doc operativo corrente e' pre-v5 (cita `listini_associazioni`, nessun riferimento alle 3 modalita' contratto A/B/C, convenzione segno variazione non documentata). Riscrittura completa a chiusura Fase 4.
- **Smoke UI end-to-end mancante**: ogni sprint FE ha solo verifica vite build, no test manuale sistematico su flussi admin reali (login, CRUD, readonly). Proporre checklist smoke per F3-FE-10.
- **i18n namespace rigido**: se una feature sposta menu (es. promo_articoli da `vendite/` a `amm-software/`) serve rebase chiavi `vendite.*` → `amministrazione.*`. Pattern progetto, ma degrada in cambi organizzativi.

---

*Sviluppo Listini — ZeroERP (14 aprile 2026, WIP v5 — modello unico base + categoria + contratto + promo, resolver 3 stadi)*

---

## 14) Sprint 22-04-2026 — Completamento v5 + assorbimento autorizzazioni prezzi

> Piano consolidato il **2026-04-22** dopo archiviazione di `listini-commercio.md`
> (storico, contenuto assorbito) e `sviluppo-autorizzazioni-prezzi.md` (L1 chiuso,
> L2+L3 confluiti qui).
>
> Questo è l'**unico documento vivo** per tutto lo sviluppo listini + pricing +
> autorizzazioni prezzi da oggi in avanti.
>
> **Revisione 22-04-2026 (verifica codice)**: durante la review si è scoperto che
> gli Sprint A (FE contratti + BA categoria) e B (FE articoli + BoM) originariamente
> pianificati in questa sezione erano **già stati implementati** nelle sessioni
> 15/16-04 senza aggiornamento del tracking. I §14.2 e §14.3 storici restano per
> documentazione ma sono marcati ✅ DONE. Il nuovo Sprint A è stato ridefinito
> come **cleanup + smoke UI + riscrittura guida** (vedi §14.2bis).

### 14.1 Stato di partenza (reale, verificato sul codice 22-04-2026)

| Area | Chiuso | Residuo |
|---|---|---|
| DB v5 (F1-DB-01..28, pgTAP T1..T6) | ✅ 15-04 | — |
| BE (F2-BE-01..11, 13, 14) | ✅ 15-04 | F2-BE-12 (pipeline compositi), F2-BE-15 (test completi) |
| FE admin pricing (F3-FE-01/02/03) | ✅ 15-04 | — |
| FE BA categoria (F3-FE-04) | ✅ verificato 22-04 ([ClienteDrawer.vue:506](../../../../frontend/src/anagrafiche/components/ClienteDrawer.vue#L506)) | — |
| FE contratti end-to-end (F3-FE-05) | ✅ 16-04 ([ContrattiListView](../../../../frontend/src/vendite/views/ContrattiListView.vue) + 5 componenti + api + store) | — |
| FE articoli tipologia + BoM (F3-FE-06/07) | ✅ 16-04 ([ArticoloDrawer.vue:261](../../../../frontend/src/catalogo/components/ArticoloDrawer.vue#L261) + [ArticoloBomDrawer.vue:330](../../../../frontend/src/catalogo/components/ArticoloBomDrawer.vue#L330)) | — |
| FE cleanup + smoke end-to-end (F3-FE-09/10) | — | 🔴 da fare |
| Autorizzazioni prezzi L1 | ✅ 17-04 | — |
| Autorizzazioni prezzi L2 | — | 🔴 da progettare |
| Autorizzazioni prezzi L3 | — | 🔴 da progettare |
| Guida `gestione-listini.md` | — | 🔴 pre-v5, da riscrivere |
| Debito tecnico FE (enum readonly, helpers, search guard) | — | 🔴 da pulire |

### 14.2 Sprint A (originale) — FE contratti + BA categoria ✅ DONE 16-04

> **Storico**: gli step sotto sono stati implementati nella sessione 16-04
> (handoff_20260416, project_sprint_f3_fe_05_06) ma il tracking era rimasto
> fermo al 15-04. Verificato sul codice il 22-04 in fase di review.

**Obiettivo**: rendere il modello v5 usabile end-to-end dagli operatori FE. Senza
questi sprint il BE è pronto ma il FE non espone le nuove dimensioni.

Solo lavoro **Frontend** (il BE corrispondente è già chiuso).

| Step | Tipo | Prereq. | Descrizione |
|---|---|---|---|
| S14.A-FE-1 ✅ | FE | F2-BE-04 ✅ | `ClienteDrawer`: Select `ba_categoria_cliente_id` (opzionale, default STANDARD da DB). Implementato 15-16/04 |
| S14.A-FE-2 ✅ | FE | F2-BE-05/06 ✅ | `ContrattiListView` + `ContrattoDrawer` da zero + sub-drawer righe/utility. Modalità A/B/C via SelectButton. Implementato 16/04 |
| S14.A-FE-3 ✅ | FE | — | Sub-drawer righe master-detail inline implementato in `ContrattoRigheDrawer.vue` |
| S14.A-FE-4 ✅ | FE | — | Sub-drawer utility in `ContrattoUtilityDrawer.vue` |
| S14.A-FE-5 ✅ | FE | — | vite build OK (ContrattiListView chunk 45.58 kB) |

### 14.3 Sprint B (originale) — FE articoli + BoM ✅ DONE 16-04

> **Storico**: implementato nella sessione 16-04 come F3-FE-06/07.

**Obiettivo**: esporre da FE le ultime due dimensioni introdotte in DB (tipologia
articolo + flag componente esposto). Puro FE.

| Step | Tipo | Prereq. | Descrizione |
|---|---|---|---|
| S14.B-FE-1 ✅ | FE | F2-BE-07 ✅ | `ArticoloDrawer`: Select `listino_tipologia_id` implementato [ArticoloDrawer.vue:261](../../../../frontend/src/catalogo/components/ArticoloDrawer.vue#L261) |
| S14.B-FE-2 ✅ | FE | F2-BE-08 ✅ | Toggle `esposto_in_fattura` + colonna in [ArticoloBomDrawer.vue:330](../../../../frontend/src/catalogo/components/ArticoloBomDrawer.vue#L330) |
| S14.B-FE-3 ✅ | FE | — | vite build OK |

### 14.3bis Sprint A (nuovo 22-04-2026) — Cleanup FE + smoke UI + riscrittura guida

**Obiettivo**: chiudere definitivamente v5 per tutte le parti già implementate
(DB + BE + FE admin + FE operativo) prima di aprire i capitoli nuovi (L2, L3,
compositi). Nessuna nuova feature, solo consolidamento.

**Perché Sprint A e non Sprint F** (come nel piano originale): alla revisione
22-04 si è scoperto che Sprint A/B originali erano già chiusi. Sprint F
(chiusura v5) è diventato il prossimo blocco di lavoro effettivo, quindi
rinumerato come nuovo Sprint A.

Solo lavoro **Frontend** + **Documentazione** (niente DB, niente BE).

#### 14.3bis.1 Frontend cleanup

| Step | Tipo | Descrizione |
|---|---|---|
| S14.nA-FE-1 | FE | Audit residui `listini_associazioni` in FE: grep `frontend/src` + rimozione di API client, store action, componenti, rotte, i18n (F2-BE-13 BE è già chiuso). Verifica che nessun import rotto resti |
| S14.nA-FE-2 | FE | Audit residui `voce_utility` in FE: grep `frontend/src` + rimozione. Verifica AI tool `CercaArticoli` (parametri FE allineati a BE F2-BE-14) |
| S14.nA-FE-3 | FE | Debito tecnico: enum centralizzato `READONLY_DOMAINS` + `TAB_ENTITIES` in `core/constants.js`, migrazione consumer/provider esistenti (admin pricing + vendite) |
| S14.nA-FE-4 | FE | Debito tecnico: helper `buildBoolOptions(t)` in `core/components/options.js`, refactor 3 SearchTable admin (categorie clienti, matrice, promo) |
| S14.nA-FE-5 | FE | Debito tecnico: fix search guard 1-2 char cross-store — pattern unico in `useSearchTable` o in ogni store (decisione: svuotare risultati sotto soglia vs forzare fetch con search vuoto) |
| S14.nA-FE-6 | FE | Debito tecnico: nei drawer matrice + promo, reset automatico del valore al cambio `tipo_variazione` con toast info (PERCENTUALE ↔ VALORE_FISSO ↔ PREZZO_FISSO) |
| S14.nA-FE-7 | FE | `./node_modules/.bin/vite build` pulito (zero warning nuovi) |

#### 14.3bis.2 Smoke UI end-to-end

| Step | Tipo | Descrizione |
|---|---|---|
| S14.nA-SMK-1 | Smoke | Checklist manuale stampabile: login operatore → admin (categorie, matrice, promo) → cliente con categoria → contratto A/B/C → articolo+tipologia → BoM con componente esposto → preventivo con resolver v5 → override L1 |
| S14.nA-SMK-2 | Smoke | Stessa checklist con utente `LETTURA` su `vendite`: verifica badge sola lettura, drawer readonly cumulativo, DrawerFooter nasconde Salva |
| S14.nA-SMK-3 | Smoke | Stessa checklist con utente `BLOCCATO` a livello oggetto (es. `vendite.contratto = BLOCCATO`): verifica `AccessoBloccatoPanel`, no fetch sotto il pannello |

#### 14.3bis.3 Documentazione (Fase 4)

| Step | Tipo | Descrizione |
|---|---|---|
| S14.nA-DOC-1 | DOC | **Riscrittura completa** `docs/it/guide/gestione-listini.md` sul modello v5: 3 stadi resolver (promo→contratto→categoria), no `listini_associazioni`, modalità contratti A/B/C, convenzione segno variazione firmata, pattern promo overlay, riferimenti a L1 (L2/L3 menzionati come roadmap). Archiviare versione pre-v5 in `docs/it/guide/archive/` se esiste |
| S14.nA-DOC-2 | DOC | Verifica manuali DB `docs/it/dbzero/*/manual/*` aggiornati per tutte le tabelle v5 (`categorie_clienti`, `categorie_clienti_listini`, `promo_articoli`, `contratti` estesa, `commesse_attivita` +8 snapshot, `articoli.listino_tipologia_id`, `articoli_componenti.esposto_in_fattura`). Integrare dove mancano |
| S14.nA-DOC-3 | DOC | Verifica `docs/it/backend/vendite/manual/api_*.md`: `api_contratti`, `api_categorie_clienti`, `api_categorie_clienti_listini`, `api_promo_articoli`, `pricing_service` — tutti presenti. Check coerenza |
| S14.nA-DOC-4 | DOC | Aggiornare memoria + indice `MEMORY.md`: chiusura v5 end-to-end (DB+BE+FE+doc), riferimento al piano v5 §14 come "completato fino al nuovo Sprint A" |

**Gate chiusura nuovo Sprint A**:

- vite build pulito
- smoke UI completo senza regressioni
- guida `gestione-listini.md` pubblicata nel formato v5
- 3 tabelle MEMORY.md aggiornate
- zero riferimenti residui a `listini_associazioni` / `voce_utility` in FE + doc

A chiusura: v5 è pronta per produzione. Sprint successivi (L2 + L3 + compositi)
aprono il **post-v5** — nuovi capitoli funzionali, non più "completamento".

---

### 14.4 Sprint C — Pipeline espansione compositi (F2-BE-12)

**Obiettivo**: chiudere l'ultimo pezzo BE del modello BoM + introdurre
immutabilità BoM via versioning con daterange + adeguare UI ArticoloBomDrawer
al pattern "chiudi+inserisci nuova versione".

#### 14.4.1 Decisioni chiuse (sessione 22-04-2026)

| # | Tema | Scelta |
|---|---|---|
| DEC-1 | Lato espansione | **Python** in `BaseSourceHandler._expand_rows` (single-point override). La premessa "Python = più duplicazione" del piano precedente era obsoleta: il pattern hook `_expand_rows` esiste già ed è usato da `HandlerConsumi` per fan-out 1→N. Zero modifiche alle 5 `fn_list_*_da_pushare`. |
| DEC-2 | `segment_key` componenti | Suffix `#CMP:{componente_id}` sulla `segment_key` del padre. Deterministico, idempotente per re-run, leggibile in audit. |
| DEC-3 | Quantità componenti | Piene (no rounding sotto-componenti); `quantita = quantita_padre × coeff_qta`. Rounding 2 decimali solo a `qta×prezzo` in fase fatturazione (rappresentazione fattura). |
| DEC-4 | Mutabilità BoM | **Versionata via `validita` daterange** (opzione 3b). Trigger DB **restrittivo da subito**: blocca UPDATE colonne struttura + DELETE sempre. Ammesso solo `UPDATE valido_al` (chiusura riga) + `INSERT` nuova versione. Pattern admin: chiudi+inserisci. Coerente con immutabilità listini v5. |
| DEC-5 | `tipo_doc_fiscale_id` componente | Ereditato dalla `PushableRow` padre (proprietà sorgente, da `config.sorgenti`, non dell'articolo). Zero DDL. |
| DEC-6 | Componenti non esposti in `commesse_attivita` | Tutti tracciati (dettaglio massimo). Fatturazione filtra `esposto_in_fattura=true` per emettere righe; non esposti restano in commessa per audit/analisi. |

#### 14.4.2 DB

| Step | Stato | Descrizione |
|---|---|---|
| S14.C-DB-1 | ✅ DONE 22-04 (`20260422-01`) | Trigger `catalogo.trgfn_articoli_componenti_block_modifica_struttura` BEFORE UPDATE OR DELETE. Blocca DELETE sempre + UPDATE su `coeff_qta`/`componente_id`/`obbligatorio`/`esposto_in_fattura`/`partecipa_qta`/`determina_qta_padre`/`valido_dal`/`validita`. Ammette UPDATE di `valido_al` (con check `>= valido_dal`), `note_*`, `meta`, `attivo`. Errori `E_BOM_MODIFICA_VIETATA` (id 387) + `E_BOM_VALIDO_AL_INVALIDO` (id 388). |
| S14.C-DB-2 | ✅ DONE 22-04 | pgTAP `test-articoli-componenti-immutabilita` (16 casi: tutti i campi struttura bloccati, valido_al ok/ko, campi non-struttura ok, insert nuova riga no-overlap). |
| S14.C-DB-3 | ✅ DONE 22-04 (`20260422-02`) | Estensione `vendite.fn_resolve_prezzo_composito`: aggiunta `coeff_qta numeric` al `RETURNS TABLE` (in fondo, backward-compat by-position). CASO A legge `ac.coeff_qta` dalla BoM; CASO B1/B2 ritorna `1` (padre neutro nel calcolo quantita). pgTAP esteso da 4 a 7 casi: verifica `coeff_qta` corretto nei 3 casi. Side-fix BE: `PricingRepository.resolve_prezzo_composito` (`backend/apps/vendite/db/pricing_repository.py:94-100`) aggiornato per proiettare la nuova colonna nella SELECT. |

#### 14.4.3 Backend

| Step | Prereq. | Descrizione |
|---|---|---|
| S14.C-BE-1 | DEC-1..6 | `BaseSourceHandler._expand_rows` override: detect `catalogo.articoli.is_composito = true`, chiama `PricingService.resolve_prezzo_composito`, CASO B → pass-through `[row]`, CASO A → genera N `PushableRow` (uno per componente) con `articolo_id=componente_id`, `quantita=padre×coeff_qta`, `prezzo_snapshot=resolver`, `uom_id`+`iva_id` dal componente, `segment_key` con suffix `#CMP:{componente_id}`, `meta.esposto_in_fattura`+`meta.componente_di` per audit, tutti gli altri campi (tipo_doc_fiscale_id, valuta, BA, utility, competenza, sorgente_uid, ecc.) ereditati dal padre. Cache per `(articolo_id, ba_id, utility_id, data)` nel ciclo `_process_rows`. |
| S14.C-BE-2 | S14.C-BE-1 | Test integrazione end-to-end: composito con 3 componenti (2 esposti + 1 non esposto), push da preventivo → 1 commessa con 3 attività con `segment_key` distinti, quantità moltiplicate, `tipo_doc_fiscale_id` ereditato, `esposto_in_fattura` preservato. Re-run idempotente (stessi `segment_key` → upsert no duplicati). Test su tutti e 5 gli handler (preventivi, ordini, contratti, ddt, consumi). |

#### 14.4.4 Frontend

L'adeguamento FE è **prerequisito coerenza dev** (non produzione, vedi §14.4.6): senza S14.C-FE-* dopo l'attivazione del trigger DB-1 ogni save edit della BoM fallirebbe con `E_BOM_MODIFICA_VIETATA`, lasciando il team senza modo di gestire BoM via UI.

| Step | Prereq. | Descrizione |
|---|---|---|
| S14.C-FE-1 | S14.C-DB-1 mergiato | `ArticoloBomDrawer.vue`: rimuovi inline edit dei campi struttura nella DataTable. Mantieni inline solo `valido_al` (azione "chiudi riga") con `useConfirmAction` ("Chiudere questa riga BoM al {data}? Per modificarla, dovrai inserire una nuova versione"). |
| S14.C-FE-2 | S14.C-FE-1 | `ArticoloBomDrawer.vue`: nuova azione di riga "duplica come nuova versione" → form pre-compilato con valori della riga sorgente, `valido_dal = oggi`, campi struttura editabili. Submit = INSERT nuova riga (l'exclusion constraint daterange garantisce non-overlap; il trigger storicizza la riga vecchia). |
| S14.C-FE-3 | S14.C-FE-1/2 | Gestione errore `E_BOM_MODIFICA_VIETATA` con banner inline che spiega il pattern chiudi+inserisci (defense-in-depth UX: anche se la UI è corretta, errore parlante se qualcuno bypassa). |
| S14.C-FE-4 | S14.C-FE-1..3 | Smoke UI: scenario "admin corregge `coeff_qta` di un componente" → chiudi riga corrente + duplica come nuova versione + verifica visualizzazione storia BoM. |
| S14.C-FE-5 | S14.C-FE-1..4 | `vite build` verde, no warning nuovi. |

#### 14.4.5 Documentazione

| Step | Descrizione |
|---|---|
| S14.C-DOC-1 | Aggiornamento `docs/it/dev/backend/catalogo-building-block-backend.md` — nuova sezione `BoMComponentExpander` (mixin/hook in `BaseSourceHandler`). |
| S14.C-DOC-2 | Aggiornamento `docs/it/guide/gestione-listini.md` §BoM — pattern immutabilità + chiudi+inserisci, esempio operativo. |
| S14.C-DOC-3 | Manuale DB `articoli_componenti.md`: aggiornamento sezione trigger con nuovo guard. |

#### 14.4.6 Note di rollout (contesto sviluppo, no produzione)

Il progetto è in sviluppo, nessun cliente reale (vedi memoria progetto). Conseguenze sullo sprint:

* **Sequenziamento**: DB → BE → FE preferito (FE dipende da DB-1 mergiato), ma BE può iniziare in parallelo a DB su mock per il test della logica `_expand_rows` (il trigger non blocca la pipeline di push, blocca l'edit BoM).
* **Niente compat fasi**: il trigger viene attivato all-in. Non c'è grace period né flag di feature gate.
* **Smoke = locale**: nessun environment staging separato. Verifica nel branch prima del merge su `Tito-dev`.
* **Eventuali righe BoM modificate "in volo"** (dev locale): si gestiscono con cleanup/reseed manuale, non con migration di compatibilità.

### 14.5 Sprint D — Autorizzazioni prezzi L2 (limite sconto)

**Obiettivo**: portare L2 come tracciato in `sviluppo-autorizzazioni-prezzi.md` §4.
L1 è già in produzione.

#### 14.5.1 DB

| Step | Descrizione |
|---|---|
| S14.D-DB-1 | Seed `config.parameter_definitions`: nuovo parametro `VENDITE_MAX_SCONTO_PCT` (decimal, default 0, scope cascata user→group→emittente→default) |
| S14.D-DB-2 | Seed `config.parameter_defaults`: riga default globale `VENDITE_MAX_SCONTO_PCT = 0` |
| S14.D-DB-3 | (Opzionale simmetrico) `VENDITE_MAX_MAGGIORAZIONE_PCT` se si vuole limitare anche override positivo — decisione da confermare |
| S14.D-DB-4 | pgTAP resolver parametro multi-scope sul nuovo codice |

#### 14.5.2 Backend

| Step | Prereq. | Descrizione |
|---|---|---|
| S14.D-BE-1 | S14.D-DB-2 | Estendere check override in `preventivi_service.gestisci_riga` / `aggiorna_riga`: dopo L1 OK, se delta negativo → calcola `sconto_pct`, confronta con `ParameterService.get_value('VENDITE_MAX_SCONTO_PCT', user=auth_user_id)` |
| S14.D-BE-2 | S14.D-BE-1 | Nuovo codice errore `E_PREZZO_SCONTO_ECCESSIVO` in `error_policies.py` (HTTP 403, detail con max ammesso e richiesto) |
| S14.D-BE-3 | S14.D-BE-1 | Replicare check in `ordini_vendita_service` (quando esisterà) e `fatture_manuali_service` |
| S14.D-BE-4 | S14.D-BE-1 | Endpoint `GET /api/v1/vendite/pricing/limiti-utente/` che restituisce `max_sconto_pct` effettivo per l'utente corrente (per hint UI senza round-trip) |
| S14.D-BE-5 | S14.D-BE-1..4 | Test Django: utente con override user, utente con default, utente con gruppo, delta al limite, delta oltre limite |

#### 14.5.3 Frontend

| Step | Prereq. | Descrizione |
|---|---|---|
| S14.D-FE-1 | S14.D-BE-4 | Store utente effettivo: cache `max_sconto_pct` ottenuto al login/refresh |
| S14.D-FE-2 | S14.D-FE-1 | Drawer riga preventivo/ordine: mostra hint "sconto max ammesso: X%" accanto al campo prezzo se override in negativo. Colore ambra se prezzo vicino al limite, rosso se oltre |
| S14.D-FE-3 | S14.D-FE-2 | Gestione errore `E_PREZZO_SCONTO_ECCESSIVO`: banner con detail + azione "richiedi approvazione" (disabilitata finché L3 non esiste) |

### 14.6 Sprint E — Autorizzazioni prezzi L3 (approvazione out-of-policy)

**Obiettivo**: workflow approvazione quando L2 blocca. Richiede pratiche +
EmailOutbox già esistenti.

#### 14.6.1 DB

| Step | Descrizione |
|---|---|
| S14.E-DB-1 | Seed `config.tipi_prestazione` (o tabella equivalente pratiche): tipo "Approvazione prezzo commerciale" |
| S14.E-DB-2 | Seed `config.azioni_processo`: nuova azione `approva_prezzo` (area `vendite`, pericolosa=false) |
| S14.E-DB-3 | Decisione modellazione stato "in approvazione" su riga: flag `meta.pending_approval` (no DDL, full semantic) vs nuova colonna `stato_approvazione_prezzo` (tracciabile in query). **Raccomandato**: colonna esplicita su `preventivi_righe` e gemelle |
| S14.E-DB-4 | Se scelta colonna (S14.E-DB-3): `ALTER TABLE preventivi_righe ADD COLUMN stato_approvazione_prezzo varchar NULL CHECK (stato_approvazione_prezzo IN ('PENDING','APPROVED','REJECTED'))` + gemelle ordini/fatture |
| S14.E-DB-5 | Trigger guard `vendite.trgfn_preventivi_guard_transizione_approvazione`: blocca `UPDATE OF stato_doc_preventivo_id` verso `ACCETTATO` se esistono righe con `stato_approvazione_prezzo = 'PENDING'`. Errore `E_PREVENTIVO_RIGHE_PRICING_PENDENTI` |
| S14.E-DB-6 | pgTAP: guard transizione + stato riga |

#### 14.6.2 Backend

| Step | Prereq. | Descrizione |
|---|---|---|
| S14.E-BE-1 | S14.E-DB-1..4 | Estensione `preventivi_service` aggiorna_riga: se override viola L2 + utente ha pratica di approvazione abilitata → invece di errore, salva riga con `stato_approvazione_prezzo = PENDING` + crea pratica via `pratiche_service.crea_pratica` collegata alla riga + invia email al responsabile via `EmailOutboxService` |
| S14.E-BE-2 | S14.E-BE-1 | Nuovo endpoint `POST /api/v1/vendite/righe/<riga_id>/approva-prezzo/` con check azione `approva_prezzo` + `POST /.../rifiuta-prezzo/` |
| S14.E-BE-3 | S14.E-BE-2 | Su approvazione: `stato_approvazione_prezzo = APPROVED`, chiusura pratica con esito OK, notifica richiedente. Su rifiuto: riga resa al prezzo resolver, `stato_approvazione_prezzo = REJECTED`, pratica chiusa con esito KO, notifica |
| S14.E-BE-4 | S14.E-BE-1..3 | Test Django: flusso completo approva + rifiuta + transizione preventivo bloccata con riga PENDING |

#### 14.6.3 Frontend

| Step | Prereq. | Descrizione |
|---|---|---|
| S14.E-FE-1 | S14.E-BE-1 | `PreventivoRigaDrawer`: quando errore L2 → banner con azione "richiedi approvazione" ora attiva → POST con flag `richiesta_approvazione=true` |
| S14.E-FE-2 | S14.E-BE-2/3 | Nuova view `ApprovazioniPrezzoListView` per responsabili: coda pratiche "Approvazione prezzo commerciale" con contesto completo (cliente, articolo, resolver, richiesto, delta%) + azioni approva/rifiuta |
| S14.E-FE-3 | S14.E-BE-1 | Badge "⏳ in approvazione" su riga PENDING nel drawer preventivo. Tooltip con ID pratica collegata. Riga di stato preventivo mostra "Bloccato: N righe pending" |
| S14.E-FE-4 | S14.E-FE-1..3 | vite build + smoke: flusso E2E commerciale junior → oltre limite → approvazione responsabile → conferma preventivo |

### 14.7 Sprint F — Cleanup + documentazione (chiusura v5)

**Obiettivo**: chiudere Fase 3 residua + Fase 4 documentazione. Nessuna nuova
feature.

#### 14.7.1 Frontend cleanup

| Step | Descrizione |
|---|---|
| S14.F-FE-1 | F3-FE-09: rimozione residui UI su `listini_associazioni` (verifica che non sia rimasto nulla dopo F2-BE-13) |
| S14.F-FE-2 | F3-FE-10: smoke UI checklist completa (login → admin pricing → BA+contratto → articolo+BoM → preventivo con resolver → override L1+L2+L3) |
| S14.F-FE-3 | Debito tecnico rilevato 15-04 (doc §Debito tecnico): enum centralizzato `READONLY_DOMAINS` + `TAB_ENTITIES`, helper `buildBoolOptions`, fix search guard 1-2 char cross-store, reset valore al cambio tipo variazione |

#### 14.7.2 Backend test completi

| Step | Descrizione |
|---|---|
| S14.F-BE-1 | F2-BE-15: audit coverage pytest sui service nuovi (categorie_clienti, matrice, promo, contratti, pricing). Soglia minima 85% |

#### 14.7.3 Documentazione (Fase 4)

| Step | Descrizione |
|---|---|
| S14.F-DOC-1 | F4-DOC-01: riscrittura completa `docs/it/guide/gestione-listini.md` sul modello v5 (3 stadi, no associazioni, categoria+contratto+promo, modalità A/B/C, L1/L2/L3) |
| S14.F-DOC-2 | F4-DOC-02: verifica manuali DB auto-generati aggiornati per tutte le tabelle v5 |
| S14.F-DOC-3 | F4-DOC-03: `api_contratti.md` esteso con endpoint L2/L3, nuovo `api_approvazioni_prezzo.md` |
| S14.F-DOC-4 | F4-DOC-04: archiviazione di questo WIP in `work-done/sviluppo-listini-v5.md` una volta chiuso end-to-end |

### 14.8 Ordine di esecuzione (rivisto 22-04-2026)

```
Sprint A originale (FE contratti+BA)  ✅ DONE 16-04
Sprint B originale (FE articoli+BoM)  ✅ DONE 16-04
   │
   ▼
Sprint A nuovo (cleanup+smoke+guida)  ✅ DONE 22-04
   │
   ├─► Sprint C (pipeline compositi)  ◄── decisioni chiuse, DB-PRE da passare team DB
   │     DB-1/DB-2 (team DB)
   │       │
   │       ├─► BE-1/BE-2 (parallelizzabile)
   │       └─► FE-1..FE-5 (dopo DB-1 mergiato)
   │       └─► DOC-1..DOC-3
   │
   ├─► Sprint D (L2 limite sconto)    ✅ DONE 22-04
   │
   ▼
Sprint E (L3 approvazione)            ◄── dopo D: L3 estende L2
```

Sprint C e Sprint E sono indipendenti tra loro. Sprint E dipende da Sprint D
(già chiuso). Sprint C internamente: DB → BE/FE in parallelo dopo land DB-1.

### 14.9 Tracking

- [x] ~~Sprint A originale — FE contratti + BA categoria~~ ✅ DONE 16-04
- [x] ~~Sprint B originale — FE articoli + BoM~~ ✅ DONE 16-04
- [x] ~~**Sprint A nuovo (22-04) — Cleanup FE + smoke UI + riscrittura guida**~~ ✅ DONE 22-04 (13/13 step, vite build verde, guida riscritta, smoke checklist pubblicata, 125 call site migrati a 3 enum centralizzati)
- [x] ~~**Sprint C — Pipeline espansione compositi (F2-BE-12) + immutabilità BoM versionata**~~ ✅ DONE 22-04 (12/12 step). Decisioni DEC-1..DEC-6 chiuse. Riepilogo:
  * DB-1 ✅ `20260422-01` trigger guard + seed err 387/388
  * DB-2 ✅ pgTAP 16 casi immutabilità
  * DB-3 ✅ `20260422-02` `fn_resolve_prezzo_composito` esteso con `coeff_qta` + pgTAP 7 casi (era 4) + side-fix `PricingRepository` projection
  * BE-1 ✅ `BoMComponentExpander` + 13 test unit
  * BE-2 ✅ 6 test integrazione end-to-end mock sui 5 handler
  * FE-1..3 ✅ `ArticoloBomDrawer` chiudi+duplica nuova versione + hint immutabilità + i18n IT/EN
  * FE-4 ✅ vite build 944ms verde
  * FE-5 ✅ smoke checklist §1.7.bis
  * DOC-1..3 ✅ catalogo BB backend + guida §5.3 + manuale DB articoli_componenti
  * Test Django finali: 1642 verdi (era 1621 a fine Sprint D, +21 nuovi)
- [x] ~~**Sprint D — L2 limite sconto + maggiorazione**~~ ✅ DONE 22-04 (12/12 step: 2 parametri VENDITE_MAX_SCONTO_PCT/VENDITE_MAX_MAGGIORAZIONE_PCT default 0, check post-L1 in preventivi_service, endpoint GET /vendite/pricing/limiti-utente/, +6 test Django (1621 totali), composable useLimitiPricing cache modulo, hint drawer riga + banner inline con "richiedi approvazione" disabled roadmap L3, vite build 973ms)
- [ ] **Sprint E — L3 approvazione out-of-policy** — Decisioni A/B/C/D/E/F/G/H + 2 extra confermate 23-04. Avanzamento:
  * DB-E-1..7 ⏳ APERTI — passaggio team DB (azione processo `approva_prezzo` + tipo prestazione `APPROVAZIONE_PREZZO` + ALTER preventivi_righe + 2 trigger guard + seed messaggi 389/390 + pgTAP)
  * BE ✅ DONE 23-04 — `approvazioni_prezzo_service` (crea_richiesta + approva + rifiuta + lista_coda + link_riga_a_pratica) con cache lookup tipo_prestazione/priorita; `gestisci_riga`+`aggiorna_riga` estesi con flag `richiesta_approvazione`; 3 codici errore (`E_PREVENTIVO_RIGHE_PRICING_PENDENTI`, `E_RIGA_PREZZO_PENDENTE`, `E_APPROVAZIONE_PREZZO_NON_AMMESSA`); 3 endpoint API (`/righe/<id>/approva-prezzo/`, `/rifiuta-prezzo/`, `/approvazioni-prezzo/`); 16 test (4 hook L3 in preventivi + 12 ApprovazioniPrezzoService); suite 1662 verdi
  * FE ✅ DONE 23-04 — i18n IT/EN (15 nuove chiavi); api client `approvazioniPrezzo.js`; `PreventiviRigaForm` pulsante "Richiedi approvazione" attivato + flusso `richiesta_approvazione=true`; route `/vendite/approvazioni-prezzo` + `ApprovazioniPrezzoListView` con dialog approva/rifiuta; badge Tag PENDING/APPROVED/REJECTED su righe in `PreventiviRigheTable`; vite build 916ms
  * DOC ✅ DONE 23-04 — catalogo BB BE (`approvazioni_prezzo_service.*`); guida `gestione-listini.md` §6.1 workflow L3 + 3 nuove righe tabella errori; smoke checklist §1.9.bis scenario L3 end-to-end
  * **In attesa land DB-E-* per esecuzione reale.** Tutto il resto chiuso end-to-end.

---

*Piano unificato aggiornato il 2026-04-22 — assorbe `listini-commercio.md` (archiviato) e `sviluppo-autorizzazioni-prezzi.md` (archiviato, L1 in produzione, L2+L3 in Sprint D/E).*
