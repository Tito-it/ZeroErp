# Sviluppo Listini — Pricing ZeroERP (WIP v4)

> Stato: **STATO CHIUSO 15-04-2026. Questo documento è stato inglobato nel documento sviluppo-listini-v5.**
>
> Ultima revisione: 13 aprile 2026
>
> Questo documento e` un addendum al v3. Copre esclusivamente:
> * Rimozione del campo `dominio` da `vendite.listini` (completata)
> * Introduzione di `utility_id NOT NULL` come dimensione obbligatoria (completata, id=5 Base)
> * Introduzione di `tipologia_id` e relativa tabella `config.listini_tipologie`
> * **[NUOVO] Matrice ammissibilita` utility x tipologia (`config.listini_tipologie_utilities`)**
>
> Tutti gli altri contenuti (fix F1/F2, operazioni O1-O3, integrazioni N1-N8)
> rimangono invariati nel documento v3.
>
> Riferimenti:
> * [sviluppo-listini-v3.md](sviluppo-listini-v3.md) — documento padre
> * [dbzero/vendite/tabelle/listini.md](/dbzero/vendite/tabelle/listini) — schema listini

---

## 1) Contesto e motivazione

### 1.1 Situazione precedente

Il campo `dominio` su `vendite.listini` con valori `UTILITY` / `COMMERCIO`
era l'unico discriminante per classificare i listini. Era insufficiente per
due motivi:

1. Non distingueva tra i diversi servizi utility (gas, idrico, energia)
2. Non distingueva la natura delle voci di listino (consumi, quote fisse,
   imposte, prodotti, servizi)

### 1.2 Situazione attuale

Il campo `dominio` e` stato **eliminato** (12 aprile 2026). Al suo posto:

* `utility_id` — gia` presente sul listino, **NOT NULL**. Ogni installazione
  ZeroERP ha sempre almeno una utility "Base" (id=5 nel seed `config.utilities`),
  quindi ogni listino appartiene sempre a un contesto utility. Listini
  commerciali usano `utility_id = 5` (Base).

* `tipologia_id` — **da aggiungere**, FK a `config.listini_tipologie`. **NOT NULL**:
  ogni listino ha sempre una tipologia esplicita. Niente NULL.

### 1.3 Perche` una tabella dedicata e non un enum

* Nuove tipologie si aggiungono con un INSERT, non con una migration DDL
* La tabella porta flag semantici usati dalla pipeline di fatturazione
* Estensibile senza toccare il resolver o il backend listini

---

## 2) Nuova tabella: `config.listini_tipologie`

### 2.1 DDL

```sql
CREATE TABLE config.listini_tipologie (
    id              smallserial PRIMARY KEY,
    codice          varchar     NOT NULL UNIQUE,
    descrizione     varchar     NOT NULL,
    -- flag semantici per pipeline di fatturazione
    -- esattamente uno deve essere TRUE (vedi constraint)
    e_consumo       boolean     NOT NULL DEFAULT false,
    e_quota_fissa   boolean     NOT NULL DEFAULT false,
    e_imposta       boolean     NOT NULL DEFAULT false,
    e_onere         boolean     NOT NULL DEFAULT false,
    e_prodotto      boolean     NOT NULL DEFAULT false,
    e_servizio      boolean     NOT NULL DEFAULT false,
    -- ordinamento per display in UI
    ordinamento     smallint    NOT NULL DEFAULT 100,
    meta            jsonb       NOT NULL DEFAULT '{}'::jsonb,
    attivo          boolean     NOT NULL DEFAULT true,
    data_insert     timestamptz NOT NULL DEFAULT now(),
    user_insert     text        NOT NULL DEFAULT CURRENT_USER,
    data_update     timestamptz NOT NULL DEFAULT now(),
    user_update     text        NOT NULL DEFAULT CURRENT_USER,
    tx_id           uuid        NULL,
    -- esattamente un flag semantico attivo per tipologia
    CONSTRAINT chk_listini_tipologie_flag_esclusivi CHECK (
        (e_consumo::int + e_quota_fissa::int + e_imposta::int +
         e_onere::int + e_prodotto::int + e_servizio::int) = 1
    )
);
```

### 2.2 Seed iniziale

```sql
INSERT INTO config.listini_tipologie
    (codice, descrizione, e_consumo, e_quota_fissa, e_imposta,
     e_onere, e_prodotto, e_servizio, ordinamento)
VALUES
    ('CONSUMO',       'Consumi',             true,  false, false, false, false, false, 10),
    ('QUOTA_FISSA',   'Quote fisse',         false, true,  false, false, false, false, 20),
    ('IMPOSTA',       'Imposte e accise',    false, false, true,  false, false, false, 30),
    ('ONERE_SISTEMA', 'Oneri di sistema',    false, false, false, true,  false, false, 40),
    ('PRODOTTI',      'Prodotti e ricambi',  false, false, false, false, true,  false, 50),
    ('SERVIZI',       'Servizi e assistenza',false, false, false, false, false, true,  60);
```

### 2.3 Significato dei flag

| Flag            | Significato operativo                             | Contesto tipico          |
| --------------- | ------------------------------------------------- | ------------------------ |
| `e_consumo`     | Voce di consumo misurabile (mc, kWh, mc acqua)    | Gas, energia, idrico     |
| `e_quota_fissa` | Canone o quota periodica indipendente dal consumo | Gas, energia, idrico     |
| `e_imposta`     | Imposta, accisa, componente fiscale               | Gas, energia, idrico     |
| `e_onere`       | Onere di sistema (es. componenti Arera)           | Energia elettrica        |
| `e_prodotto`    | Articolo fisico, ricambio, materiale              | Commercio, ricambi       |
| `e_servizio`    | Prestazione, intervento tecnico, assistenza       | Assistenza, manutenzione |

Il constraint `chk_listini_tipologie_flag_esclusivi` garantisce che ogni
tipologia abbia **esattamente un flag** a true.

---

## 3) Matrice ammissibilita` utility x tipologia

### 3.1 Motivazione

Non tutte le combinazioni utility/tipologia hanno senso operativo. Un listino
"Gas + PRODOTTI" e` incoerente, cosi` come "Base + ONERE_SISTEMA". Senza una
matrice di ammissibilita`, l'operatore puo` creare combinazioni errate che
inquinano il sistema e complicano la fatturazione.

### 3.2 DDL

```sql
CREATE TABLE config.listini_tipologie_utilities (
    id              serial      PRIMARY KEY,
    utility_id      integer     NOT NULL REFERENCES config.utilities(id),
    tipologia_id    smallint    NOT NULL REFERENCES config.listini_tipologie(id),
    attivo          boolean     NOT NULL DEFAULT true,
    data_insert     timestamptz NOT NULL DEFAULT now(),
    user_insert     text        NOT NULL DEFAULT CURRENT_USER,
    data_update     timestamptz NOT NULL DEFAULT now(),
    user_update     text        NOT NULL DEFAULT CURRENT_USER,
    tx_id           uuid        NULL,
    CONSTRAINT uq_listini_tipologie_utilities UNIQUE (utility_id, tipologia_id)
);
```

### 3.3 Seed iniziale

| Utility (id)          | Tipologie ammesse                            |
| --------------------- | -------------------------------------------- |
| Gas (1)               | CONSUMO, QUOTA_FISSA, IMPOSTA, ONERE_SISTEMA |
| Energia (2)           | CONSUMO, QUOTA_FISSA, IMPOSTA, ONERE_SISTEMA |
| Idrico (3)            | CONSUMO, QUOTA_FISSA, IMPOSTA                |
| Teleriscaldamento (4) | CONSUMO, QUOTA_FISSA, IMPOSTA                |
| Base (5)              | PRODOTTI, SERVIZI                            |

> **Nota**: gli ID utility e l'elenco sopra sono indicativi e dipendono dal seed
> `config.utilities` dell'installazione. Il pattern e` lo stesso di
> `config.utilities_tipi_ruolo` — matrice N:M con attivo.

### 3.4 Trigger guard su `vendite.listini`

Defense-in-depth: un trigger su `vendite.listini` verifica all'INSERT/UPDATE che
la coppia `(utility_id, tipologia_id)` esista in `config.listini_tipologie_utilities`
con `attivo = true`. Se non esiste, rifiuta con errore.

```sql
-- Pseudocodice trigger
IF NOT EXISTS (
    SELECT 1 FROM config.listini_tipologie_utilities
     WHERE utility_id = NEW.utility_id
       AND tipologia_id = NEW.tipologia_id
       AND attivo = true
) THEN
    RAISE EXCEPTION 'Combinazione utility/tipologia non ammessa';
END IF;
```

### 3.5 Impatto frontend

Alla selezione dell'utility nel drawer, il frontend carica le tipologie ammesse
per quell'utility e popola il Select tipologia. Se l'utility cambia, il Select
tipologia si resetta e ricarica.

Pattern: stesso di `UtilityPerRuoloSelect` — un endpoint che filtra per FK.

---

## 4) Modifiche a `vendite.listini`

### 4.1 Struttura risultante

| Campo          | Tipo              | Note                                              |
| -------------- | ----------------- | ------------------------------------------------- |
| `id`           | bigint PK         |                                                   |
| `codice`       | varchar UNIQUE    | Immutabile dopo create                            |
| `descrizione`  | varchar           |                                                   |
| `utility_id`   | integer NOT NULL  | FK `config.utilities` — id=5 (Base) per commercio |
| `tipologia_id` | smallint NOT NULL | FK `config.listini_tipologie`                     |
| `attivo`       | boolean           |                                                   |
| `meta`         | jsonb             |                                                   |

`dominio` rimosso. `utility_id` NOT NULL (gia` fatto). `tipologia_id` da aggiungere.

### 4.2 Combinazioni operative tipiche

| Utility | Tipologia     | Esempio listino                |
| ------- | ------------- | ------------------------------ |
| Gas     | CONSUMO       | "Tariffe consumo gas 2026"     |
| Gas     | QUOTA_FISSA   | "Quote fisse gas 2026"         |
| Gas     | IMPOSTA       | "Imposte gas 2026"             |
| Energia | CONSUMO       | "Tariffe consumo energia 2026" |
| Energia | ONERE_SISTEMA | "Oneri sistema energia 2026"   |
| Idrico  | QUOTA_FISSA   | "Quote fisse idrico 2026"      |
| Base    | PRODOTTI      | "Listino ricambi 2026"         |
| Base    | SERVIZI       | "Listino assistenza 2026"      |

---

## 5) Impatto sul resolver

Il resolver `fn_resolve_prezzo_listino` **non cambia**. Filtra i listini
candidati tramite `listini_associazioni`, che non coinvolge ne` `utility_id`
ne` `tipologia_id` del listino.

`utility_id` e `tipologia_id` sono dimensioni di **classificazione** del listino,
non dimensioni di **risoluzione** del prezzo. La risoluzione per contesto utility
avviene gia` tramite le dimensioni sulle righe/associazioni.

---

## 6) Piano di esecuzione

### Fase DB (branch `dev/db-tid`)

| #   | Task                                                                                   | Dipendenze |
| --- | -------------------------------------------------------------------------------------- | ---------- |
| D1  | `CREATE TABLE config.listini_tipologie` + seed 6 tipologie                             | —          |
| D2  | `CREATE TABLE config.listini_tipologie_utilities` + seed matrice                       | D1         |
| D3  | `ALTER TABLE vendite.listini ADD COLUMN tipologia_id` + migrazione dati esistenti      | D1         |
| D4  | `ALTER TABLE vendite.listini ALTER COLUMN utility_id SET NOT NULL` (se non gia` fatto) | —          |
| D5  | Trigger guard coerenza matrice su `vendite.listini` INSERT/UPDATE                      | D2, D3     |
| D6  | Aggiungere `config.listini_tipologie` alla whitelist lookup generico                   | D1         |
| D7  | Test pgTAP: constraint flag esclusivi, matrice ammissibilita`, trigger guard           | D5         |

### Fase Backend (branch `dev/backend-tid`)

| #   | Task                                                                                                                                             | Dipendenze DB |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ------------- |
| B1  | `listini_repository.py`: JOIN `config.listini_tipologie` in `list_listini` e `get_listino`, filtro `tipologia_id`                                | D3            |
| B2  | `listini_service.py`: `tipologia_id` obbligatorio in create, ammesso in update                                                                   | D3            |
| B3  | `listini_service.py`: rimuovere `utility_id` da `_LISTINO_NULLABLE_FIELDS` (ora NOT NULL)                                                        | D4            |
| B4  | Endpoint lookup: `GET /api/v1/core/lookup/codici/?rel=config.listini_tipologie` (whitelist gia` gestita da D6)                                   | D6            |
| B5  | Endpoint dedicato: `GET /api/v1/vendite/listini/tipologie-per-utility/?utility_id=X` — restituisce tipologie ammesse dalla matrice per l'utility | D2            |
| B6  | `views_listini.py`: aggiungere `tipologia_id` nel query param lista e nel serializer create/update                                               | B1            |
| B7  | Test unitari service + API                                                                                                                       | B2, B6        |

### Fase Frontend (branch `dev/backend-tid`)

| #   | Task                                                                                                                                       | Dipendenze BE |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------ | ------------- |
| F1  | `ListinoDrawer.vue`: aggiungere Select tipologia, filtrato per utility selezionata. Al cambio utility → reset e ricarica tipologie ammesse | B5            |
| F2  | `ListiniSearchTable.vue`: aggiungere filtro tipologia (Select da lookup generico) e colonna "Tipologia"                                    | B4            |
| F3  | `ListinoDrawer.vue`: `utility_id` non piu` nullable — rimuovere `show-clear`, rendere obbligatorio                                         | B3            |
| F4  | i18n: chiavi per tipologie                                                                                                                 | —             |
| F5  | Build + test UI                                                                                                                            | F1-F4         |

---

## 7) Test da aggiungere

| Test                                                                            | Tipo                 | Fase    |
| ------------------------------------------------------------------------------- | -------------------- | ------- |
| Creazione listino senza `tipologia_id` → atteso 400                             | Unit service + API   | B7      |
| Creazione listino senza `utility_id` → atteso 400                               | Unit service + API   | B7      |
| Creazione listino con coppia utility/tipologia non ammessa → atteso errore      | Unit service + pgTAP | B7 + D7 |
| Lista listini filtrata per `tipologia_id`                                       | Unit API             | B7      |
| Tipologie per utility: verifica che restituisca solo le ammesse                 | Unit API             | B7      |
| Seed tipologie: verifica constraint flag esclusivi su ogni riga                 | pgTAP                | D7      |
| Tentativo INSERT tipologia con due flag a true → atteso errore DB               | pgTAP                | D7      |
| Tentativo INSERT tipologia con zero flag a true → atteso errore DB              | pgTAP                | D7      |
| Tentativo INSERT listino con coppia non in matrice → trigger rifiuta            | pgTAP                | D7      |
| Cambio utility su listino esistente con tipologia non ammessa → trigger rifiuta | pgTAP                | D7      |

---

## 8) Tracking

### Fase DB

- [ ] **D1** — `config.listini_tipologie` + seed
- [ ] **D2** — `config.listini_tipologie_utilities` (matrice ammissibilita`) + seed
- [ ] **D3** — `vendite.listini`: ADD `tipologia_id NOT NULL`
- [ ] **D4** — `vendite.listini`: ALTER `utility_id SET NOT NULL` (verifica se gia` fatto)
- [ ] **D5** — Trigger guard coerenza matrice utility x tipologia
- [ ] **D6** — Whitelist lookup `config.listini_tipologie`
- [ ] **D7** — Test pgTAP

### Fase Backend

- [ ] **B1** — Repository: JOIN + filtro tipologia
- [ ] **B2** — Service: `tipologia_id` obbligatorio create
- [ ] **B3** — Service: `utility_id` NOT NULL (rimuovere da nullable)
- [ ] **B4** — Lookup generico tipologie (whitelist)
- [ ] **B5** — Endpoint tipologie-per-utility (matrice filtrata)
- [ ] **B6** — Views: schema + query param
- [ ] **B7** — Test unitari

### Fase Frontend

- [ ] **F1** — Drawer: Select tipologia filtrato da utility
- [ ] **F2** — Lista: filtro + colonna tipologia
- [ ] **F3** — Drawer: utility obbligatorio (no show-clear)
- [ ] **F4** — i18n
- [ ] **F5** — Build + test UI

---

## 9) Aggiornamenti alla guida gestione-listini

La guida `docs/it/guide/gestione-listini.md` va aggiornata:

* Sezione "Listino (testata)": sostituire "dominio (`UTILITY` o `COMMERCIO`)" con
  "utility + tipologia"
* Sezione "Creazione": "nasce con codice, descrizione, utility e tipologia"
* Aggiungere sottosezione "Classificazione listini" che spiega utility x tipologia
  e la matrice di ammissibilita`
* Aggiornare diagramma ER con FK a `config.listini_tipologie`

---

*Sviluppo Listini — ZeroERP (13 aprile 2026, WIP v4 — utility_id NOT NULL + tipologia_id + matrice ammissibilita`)*
