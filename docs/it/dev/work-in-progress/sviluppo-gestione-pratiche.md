# ZeroERP - Schema `pratiche` (1/3) - Catalogo e Esecuzione


valutare utilizzo di emeittente_fiscale.


## Modulo Gestione Pratiche / Workflow Engine

### Filosofia

Tutto e' una pratica. Ogni operazione in ZeroERP transita dal motore pratiche.
Chi configura prestazioni e flussi ottiene un workflow engine con controllo sequenza rigoroso.
Chi non configura ottiene comunque un giornale di bordo completo con tracciabilita' totale.

---

## Diagramma dipendenze

```
tipo_prestazione
    |
    +-- template_flusso ---- template_flusso_prerequisito
    |
    v
pratica -------------------- nota_pratica
    |                        allegato_pratica
    |
    +-- flusso ------------- nota_flusso
    |     |                  allegato_flusso
    |     +-- flusso (padre -> figlio)
    |
    +-- giornale
```

---

## 1. Catalogo - Configurazione

### 1.1 pratiche.tipo_prestazione

Catalogo dei tipi di prestazione. Macro-categorie di attivita gestibili.

```sql
CREATE TABLE pratiche.tipo_prestazione (
    id                  SERIAL PRIMARY KEY,
    codice              VARCHAR(20) NOT NULL UNIQUE,
    descrizione         VARCHAR(200) NOT NULL,
    categoria           VARCHAR(50),
    flussi_vincolanti   BOOLEAN NOT NULL DEFAULT FALSE,
    attivo              BOOLEAN NOT NULL DEFAULT TRUE,
    note                TEXT,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by          VARCHAR(50) NOT NULL,
    updated_by          VARCHAR(50) NOT NULL
);
```

- **categoria**: es. UTILITIES, COMMERCIALE, AMMINISTRATIVO
- **flussi_vincolanti**: TRUE = controllo sequenza attivo, FALSE = giornale senza vincoli

### 1.2 pratiche.template_flusso

Template dei flussi previsti per ogni tipo di prestazione.

```sql
CREATE TABLE pratiche.template_flusso (
    id                  SERIAL PRIMARY KEY,
    tipo_prestazione_id INTEGER NOT NULL REFERENCES pratiche.tipo_prestazione(id),
    codice              VARCHAR(20) NOT NULL,
    descrizione         VARCHAR(200) NOT NULL,
    sequenza            INTEGER NOT NULL,
    obbligatorio        BOOLEAN NOT NULL DEFAULT TRUE,
    sequenza_limite     INTEGER,
    handler             VARCHAR(200),
    giorni_previsti     INTEGER,
    attivo              BOOLEAN NOT NULL DEFAULT TRUE,
    note                TEXT,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by          VARCHAR(50) NOT NULL,
    updated_by          VARCHAR(50) NOT NULL,
    UNIQUE (tipo_prestazione_id, codice),
    UNIQUE (tipo_prestazione_id, sequenza)
);
```

- **sequenza**: ordine logico (10, 20, 30...). Il controllo effettivo e' sui prerequisiti espliciti
- **sequenza_limite**: oltre questo numero il flusso non e' piu' eseguibile
- **handler**: componente Django, es. `pratiche.handlers.AppuntamentoHandler`

### 1.3 pratiche.template_flusso_prerequisito

Prerequisiti espliciti tra flussi. Supporta paralleli e convergenze.

```sql
CREATE TABLE pratiche.template_flusso_prerequisito (
    id                      SERIAL PRIMARY KEY,
    template_flusso_id      INTEGER NOT NULL REFERENCES pratiche.template_flusso(id),
    prerequisito_flusso_id  INTEGER NOT NULL REFERENCES pratiche.template_flusso(id),
    obbligatorio            BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by              VARCHAR(50) NOT NULL,
    UNIQUE (template_flusso_id, prerequisito_flusso_id),
    CHECK (template_flusso_id <> prerequisito_flusso_id)
);
```

- **obbligatorio**: TRUE = bloccante, FALSE = consigliato (warning senza blocco)

---

## 2. Esecuzione - Istanze operative

### 2.1 pratiche.pratica

Istanza concreta di una pratica. Testata.

```sql
CREATE TABLE pratiche.pratica (
    id                  SERIAL PRIMARY KEY,
    emittente_fiscale_id          INTEGER NOT NULL,
    tipo_prestazione_id INTEGER NOT NULL REFERENCES pratiche.tipo_prestazione(id),
    numero              VARCHAR(30) NOT NULL,
    anno                INTEGER NOT NULL,
    oggetto             VARCHAR(500),
    soggetto_id         INTEGER,
    stato               VARCHAR(20) NOT NULL DEFAULT 'APERTA'
                        CHECK (stato IN ('BOZZA','APERTA','SOSPESA','CHIUSA','ANNULLATA')),
    priorita            VARCHAR(10) DEFAULT 'NORMALE'
                        CHECK (priorita IN ('BASSA','NORMALE','ALTA','URGENTE')),
    data_apertura       DATE NOT NULL DEFAULT CURRENT_DATE,
    data_scadenza       DATE,
    data_chiusura       DATE,
    operatore_id        INTEGER,
    unita_org_id        INTEGER,
    pratica_padre_id    INTEGER REFERENCES pratiche.pratica(id),
    riferimento_esterno VARCHAR(100),
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by          VARCHAR(50) NOT NULL,
    updated_by          VARCHAR(50) NOT NULL,
    UNIQUE (emittente_fiscale_id, anno, numero)
);

CREATE INDEX idx_pratica_azienda ON pratiche.pratica(emittente_fiscale_id);
CREATE INDEX idx_pratica_tipo ON pratiche.pratica(tipo_prestazione_id);
CREATE INDEX idx_pratica_soggetto ON pratiche.pratica(soggetto_id);
CREATE INDEX idx_pratica_stato ON pratiche.pratica(stato);
CREATE INDEX idx_pratica_data ON pratiche.pratica(data_apertura);
CREATE INDEX idx_pratica_padre ON pratiche.pratica(pratica_padre_id);
```

- **pratica_padre_id**: per sotto-pratiche e pratiche collegate
- **riferimento_esterno**: protocollo esterno, n. ticket, ecc.

### 2.2 pratiche.flusso

Step/fase operativo dentro una pratica. Riga.

```sql
CREATE TABLE pratiche.flusso (
    id                      SERIAL PRIMARY KEY,
    pratica_id              INTEGER NOT NULL REFERENCES pratiche.pratica(id),
    template_flusso_id      INTEGER REFERENCES pratiche.template_flusso(id),
    codice                  VARCHAR(20) NOT NULL,
    descrizione             VARCHAR(200) NOT NULL,
    sequenza                INTEGER NOT NULL,
    stato                   VARCHAR(20) NOT NULL DEFAULT 'DA_ESEGUIRE'
                            CHECK (stato IN ('DA_ESEGUIRE','IN_CORSO','COMPLETATO',
                                             'SOSPESO','ANNULLATO','ERRORE')),
    esito                   VARCHAR(20)
                            CHECK (esito IN ('POSITIVO','NEGATIVO','PARZIALE')),
    flusso_padre_id         INTEGER REFERENCES pratiche.flusso(id),
    operatore_id            INTEGER,
    unita_org_id            INTEGER,
    data_prevista_inizio    DATE,
    data_prevista_fine      DATE,
    data_inizio             TIMESTAMP,
    data_fine               TIMESTAMP,
    note_esito              TEXT,
    created_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by              VARCHAR(50) NOT NULL,
    updated_by              VARCHAR(50) NOT NULL,
    UNIQUE (pratica_id, codice)
);

CREATE INDEX idx_flusso_pratica ON pratiche.flusso(pratica_id);
CREATE INDEX idx_flusso_stato ON pratiche.flusso(stato);
CREATE INDEX idx_flusso_padre ON pratiche.flusso(flusso_padre_id);
CREATE INDEX idx_flusso_operatore ON pratiche.flusso(operatore_id);
CREATE INDEX idx_flusso_template ON pratiche.flusso(template_flusso_id);
```

- **flusso_padre_id**: flusso che ha generato questo. Permette albero di attivita e sotto-flussi
- **template_flusso_id**: NULL per flussi aggiunti manualmente su pratiche libere



# ZeroERP - Schema `pratiche` (2/3) - Documentale e Giornale

## 3. Documentale - Note e Allegati

### 3.1 pratiche.nota_pratica

Note associate alla testata pratica.

```sql
CREATE TABLE pratiche.nota_pratica (
    id               SERIAL PRIMARY KEY,
    pratica_id       INTEGER NOT NULL REFERENCES pratiche.pratica(id),
    tipo_nota        VARCHAR(20) NOT NULL DEFAULT 'GENERALE'
                     CHECK (tipo_nota IN ('GENERALE','INTERNA','CLIENTE','TECNICA','LEGALE')),
    oggetto          VARCHAR(200),
    testo            TEXT NOT NULL,
    visibile_esterno BOOLEAN NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by       VARCHAR(50) NOT NULL,
    updated_by       VARCHAR(50) NOT NULL
);

CREATE INDEX idx_nota_pratica ON pratiche.nota_pratica(pratica_id);
```

- **tipo_nota**: GENERALE, INTERNA, CLIENTE, TECNICA, LEGALE
- **visibile_esterno**: se visibile su portale/cliente

### 3.2 pratiche.nota_flusso

Note associate al singolo flusso/riga.

```sql
CREATE TABLE pratiche.nota_flusso (
    id               SERIAL PRIMARY KEY,
    flusso_id        INTEGER NOT NULL REFERENCES pratiche.flusso(id),
    tipo_nota        VARCHAR(20) NOT NULL DEFAULT 'GENERALE'
                     CHECK (tipo_nota IN ('GENERALE','INTERNA','CLIENTE','TECNICA','LEGALE')),
    oggetto          VARCHAR(200),
    testo            TEXT NOT NULL,
    visibile_esterno BOOLEAN NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by       VARCHAR(50) NOT NULL,
    updated_by       VARCHAR(50) NOT NULL
);

CREATE INDEX idx_nota_flusso ON pratiche.nota_flusso(flusso_id);
```

---

### 3.3 pratiche.allegato_pratica

Documenti e immagini allegati alla testata pratica. Supporta versionamento.

```sql
CREATE TABLE pratiche.allegato_pratica (
    id                SERIAL PRIMARY KEY,
    pratica_id        INTEGER NOT NULL REFERENCES pratiche.pratica(id),
    tipo_allegato     VARCHAR(20) NOT NULL
                      CHECK (tipo_allegato IN ('DOCUMENTO','IMMAGINE','MODULO',
                             'CONTRATTO','FATTURA','VERBALE','CERTIFICATO','ALTRO')),
    nome_file         VARCHAR(255) NOT NULL,
    nome_originale    VARCHAR(255) NOT NULL,
    mime_type         VARCHAR(100) NOT NULL,
    dimensione        BIGINT,
    percorso          VARCHAR(500) NOT NULL,
    hash_file         VARCHAR(64),
    descrizione       VARCHAR(500),
    versione          INTEGER NOT NULL DEFAULT 1,
    allegato_padre_id INTEGER REFERENCES pratiche.allegato_pratica(id),
    created_at        TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by        VARCHAR(50) NOT NULL
);

CREATE INDEX idx_allegato_pratica ON pratiche.allegato_pratica(pratica_id);
CREATE INDEX idx_allegato_pratica_tipo ON pratiche.allegato_pratica(tipo_allegato);
CREATE INDEX idx_allegato_pratica_hash ON pratiche.allegato_pratica(hash_file);
```

- **tipo_allegato**: DOCUMENTO, IMMAGINE, MODULO, CONTRATTO, FATTURA, VERBALE, CERTIFICATO, ALTRO
- **mime_type**: es. application/pdf, image/jpeg, image/png, application/vnd.oasis...
- **hash_file**: SHA-256 per integrita e deduplicazione storage
- **allegato_padre_id**: versione precedente dello stesso documento (storico versioni)
- **percorso**: path nello storage (filesystem o object storage tipo S3/MinIO)

### 3.4 pratiche.allegato_flusso

Documenti e immagini allegati al singolo flusso/riga. Stessa struttura degli allegati pratica.

```sql
CREATE TABLE pratiche.allegato_flusso (
    id                SERIAL PRIMARY KEY,
    flusso_id         INTEGER NOT NULL REFERENCES pratiche.flusso(id),
    tipo_allegato     VARCHAR(20) NOT NULL
                      CHECK (tipo_allegato IN ('DOCUMENTO','IMMAGINE','MODULO',
                             'CONTRATTO','FATTURA','VERBALE','CERTIFICATO','ALTRO')),
    nome_file         VARCHAR(255) NOT NULL,
    nome_originale    VARCHAR(255) NOT NULL,
    mime_type         VARCHAR(100) NOT NULL,
    dimensione        BIGINT,
    percorso          VARCHAR(500) NOT NULL,
    hash_file         VARCHAR(64),
    descrizione       VARCHAR(500),
    versione          INTEGER NOT NULL DEFAULT 1,
    allegato_padre_id INTEGER REFERENCES pratiche.allegato_flusso(id),
    created_at        TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by        VARCHAR(50) NOT NULL
);

CREATE INDEX idx_allegato_flusso ON pratiche.allegato_flusso(flusso_id);
CREATE INDEX idx_allegato_flusso_tipo ON pratiche.allegato_flusso(tipo_allegato);
CREATE INDEX idx_allegato_flusso_hash ON pratiche.allegato_flusso(hash_file);
```

---

## 4. Giornale di Bordo - Audit Trail

### 4.1 pratiche.giornale

Log immutabile di ogni azione. Si alimenta automaticamente via trigger.
Non si modifica, non si cancella.

```sql
CREATE TABLE pratiche.giornale (
    id              BIGSERIAL PRIMARY KEY,
    pratica_id      INTEGER NOT NULL REFERENCES pratiche.pratica(id),
    flusso_id       INTEGER REFERENCES pratiche.flusso(id),
    azione          VARCHAR(30) NOT NULL
                    CHECK (azione IN (
                        'PRATICA_CREATA','PRATICA_MODIFICATA','PRATICA_CHIUSA',
                        'PRATICA_ANNULLATA','PRATICA_SOSPESA','PRATICA_RIAPERTA',
                        'FLUSSO_CREATO','FLUSSO_AVVIATO','FLUSSO_COMPLETATO',
                        'FLUSSO_SOSPESO','FLUSSO_ANNULLATO','FLUSSO_ERRORE',
                        'NOTA_AGGIUNTA','ALLEGATO_AGGIUNTO',
                        'ASSEGNAZIONE_CAMBIATA','PRIORITA_CAMBIATA',
                        'EVENTO_ESTERNO'
                    )),
    dettaglio       JSONB,
    descrizione     TEXT,
    origine         VARCHAR(20) NOT NULL DEFAULT 'UTENTE'
                    CHECK (origine IN ('UTENTE','SISTEMA','ESTERNO','TRIGGER')),
    ip_address      INET,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by      VARCHAR(50) NOT NULL
);

CREATE INDEX idx_giornale_pratica ON pratiche.giornale(pratica_id);
CREATE INDEX idx_giornale_flusso ON pratiche.giornale(flusso_id);
CREATE INDEX idx_giornale_azione ON pratiche.giornale(azione);
CREATE INDEX idx_giornale_data ON pratiche.giornale(created_at);
```

- **dettaglio**: JSONB con valori precedenti/nuovi. Ricostruzione completa della storia
- **origine**: UTENTE (operatore), SISTEMA (automatismo), ESTERNO (API), TRIGGER (DB)
- **flusso_id**: NULL se azione su testata pratica
- **BIGSERIAL**: per supportare volumi elevati di log


# ZeroERP - Schema `pratiche` (3/3) - Funzioni e Riepilogo

## 5. Funzioni DB - Controllo Sequenza

### 5.1 Verifica prerequisiti

Funzione centralizzata che valida se un flusso puo essere avviato.
Controlla prerequisiti espliciti e sequenza limite.
Se il tipo prestazione non e vincolante, passa sempre.

```sql
CREATE OR REPLACE FUNCTION pratiche.verifica_prerequisiti(
    p_pratica_id INTEGER,
    p_template_flusso_id INTEGER
) RETURNS TABLE (
    esito BOOLEAN,
    messaggio TEXT,
    prerequisiti_mancanti TEXT[]
) AS $$
DECLARE
    v_tipo_vincolante BOOLEAN;
    v_mancanti TEXT[] := '{}';
    v_flusso_sequenza INTEGER;
    v_sequenza_limite INTEGER;
    v_max_sequenza_completata INTEGER;
BEGIN
    -- Verifica se il tipo prestazione ha flussi vincolanti
    SELECT tp.flussi_vincolanti
    INTO v_tipo_vincolante
    FROM pratiche.pratica p
    JOIN pratiche.tipo_prestazione tp ON tp.id = p.tipo_prestazione_id
    WHERE p.id = p_pratica_id;

    -- Se non vincolante, passa sempre
    IF NOT v_tipo_vincolante THEN
        RETURN QUERY SELECT TRUE, 'Flussi non vincolanti'::TEXT, '{}'::TEXT[];
        RETURN;
    END IF;

    -- Recupera sequenza e limite del flusso
    SELECT tf.sequenza, tf.sequenza_limite
    INTO v_flusso_sequenza, v_sequenza_limite
    FROM pratiche.template_flusso tf
    WHERE tf.id = p_template_flusso_id;

    -- Controlla prerequisito massimo (sequenza_limite)
    IF v_sequenza_limite IS NOT NULL THEN
        SELECT COALESCE(MAX(f.sequenza), 0)
        INTO v_max_sequenza_completata
        FROM pratiche.flusso f
        WHERE f.pratica_id = p_pratica_id
          AND f.stato = 'COMPLETATO';

        IF v_max_sequenza_completata >= v_sequenza_limite THEN
            RETURN QUERY SELECT FALSE,
                FORMAT('Flusso non piu eseguibile: superata sequenza limite %s',
                       v_sequenza_limite)::TEXT,
                '{}'::TEXT[];
            RETURN;
        END IF;
    END IF;

    -- Controlla prerequisiti espliciti obbligatori
    SELECT ARRAY_AGG(tf_pre.codice)
    INTO v_mancanti
    FROM pratiche.template_flusso_prerequisito tfp
    JOIN pratiche.template_flusso tf_pre ON tf_pre.id = tfp.prerequisito_flusso_id
    WHERE tfp.template_flusso_id = p_template_flusso_id
      AND tfp.obbligatorio = TRUE
      AND NOT EXISTS (
          SELECT 1 FROM pratiche.flusso f
          WHERE f.pratica_id = p_pratica_id
            AND f.template_flusso_id = tfp.prerequisito_flusso_id
            AND f.stato = 'COMPLETATO'
      );

    IF v_mancanti IS NOT NULL AND ARRAY_LENGTH(v_mancanti, 1) > 0 THEN
        RETURN QUERY SELECT FALSE,
            'Prerequisiti obbligatori non completati'::TEXT,
            v_mancanti;
        RETURN;
    END IF;

    RETURN QUERY SELECT TRUE, 'Tutti i prerequisiti soddisfatti'::TEXT, '{}'::TEXT[];
END;
$$ LANGUAGE plpgsql;
```

---

## 6. Riepilogo Tabelle

| #   | Tabella                      | Ruolo                       | Relazioni principali                     |
| --- | ---------------------------- | --------------------------- | ---------------------------------------- |
| 1   | tipo_prestazione             | Catalogo tipi pratica       | -> template_flusso                       |
| 2   | template_flusso              | Template flussi con regole  | -> tipo_prestazione, -> prerequisiti     |
| 3   | template_flusso_prerequisito | Prerequisiti tra flussi     | -> template_flusso (2x)                  |
| 4   | pratica                      | Istanza operativa (testata) | -> tipo_prestazione, -> pratica padre    |
| 5   | flusso                       | Step operativo (riga)       | -> pratica, -> template, -> flusso padre |
| 6   | nota_pratica                 | Note su testata             | -> pratica                               |
| 7   | nota_flusso                  | Note su flusso              | -> flusso                                |
| 8   | allegato_pratica             | Documenti/immagini testata  | -> pratica, -> allegato padre            |
| 9   | allegato_flusso              | Documenti/immagini flusso   | -> flusso, -> allegato padre             |
| 10  | giornale                     | Audit trail immutabile      | -> pratica, -> flusso                    |

**Totale: 10 tabelle nucleo** + funzione verifica prerequisiti

---

## 7. Estensioni Future (non incluse)

Tabelle specifiche per tipo di flusso, da implementare mano a mano.
Ogni estensione avra FK verso `pratiche.flusso(id)` e vivra autonomamente.

- **pratiche.ext_appuntamento**: fascia oraria, data/ora, esito, tecnico assegnato
- **pratiche.ext_preventivo**: importi, voci, stato accettazione
- **pratiche.ext_sopralluogo**: dati tecnici, foto, misurazioni
- **pratiche.ext_comunicazione**: canale, destinatario, contenuto, conferma ricezione
- **pratiche.ext_spedizione**: corriere, tracking, stato consegna (per aziende commerciali)

---

## 8. Note Architetturali

**Business logic nel DB.**
La funzione `verifica_prerequisiti` centralizza il controllo nel database.
Nessun bypass possibile, ne da interfaccia ne da API esterna.

**Giornale via trigger.**
I trigger su pratica, flusso, note e allegati alimentano automaticamente
il giornale. Django non deve preoccuparsi di loggare: il DB lo fa da solo.

**Handler Django.**
Il campo `handler` nel template_flusso e il ponte verso l'applicazione.
Django legge il template, istanzia l'handler corretto e gestisce la logica specifica.
Il nucleo DB resta agnostico rispetto all'implementazione.

**Multi-company.**
Il campo `emittente_fiscale_id` sulla pratica garantisce la segregazione dei dati.
Le query filtrano sempre per azienda.
Il catalogo (tipo_prestazione, template) puo essere condiviso o per azienda.

**Versionamento allegati.**
Il campo `allegato_padre_id` mantiene lo storico versioni senza sovrascrivere.
L'hash SHA-256 previene duplicati a livello storage.

**Flussi paralleli.**
I prerequisiti espliciti permettono rami paralleli, convergenze e flussi opzionali.
Il numero di sequenza resta come ordine logico/visivo, non come vincolo.

**Flussi che generano flussi.**
Il campo `flusso_padre_id` nella tabella flusso permette che un flusso
generi uno o piu sotto-flussi, assegnabili a operatori/reparti diversi.
Di fatto un albero di attivita.
