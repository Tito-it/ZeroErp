# WIP — Listini fornitori: mappatura articoli e prezzi di riferimento

> Documento di analisi e pianificazione per l'introduzione della mappatura
> articoli-fornitori e dei listini "sorgente" provenienti dai fornitori, usati
> come base per generare listini clienti.
>
> Data creazione: 2026-04-11
> Ultima revisione: aprile 2026 (v2 — integrazioni critiche da analisi esterna,
> evidenziate con tag `[NUOVO v2]` in tutto il documento)
>
> Stato: **ANALISI** — nessuna migration, nessun backend. Da approvare prima di aprire il cantiere.
>
> Branch DB target (futuro): `dev/db-tid`
> Branch backend target (futuro): `dev/backend-tid`

---

## 1. Contesto e motivazione

### 1.1 Il problema operativo

Alcune attività che usano (o useranno) ZeroErp ricevono periodicamente dai propri
fornitori un file (Excel / CSV) contenente l'elenco degli articoli e i relativi
prezzi. Il file è tipicamente strutturato come:

```
codice_articolo_fornitore | descrizione | uom | prezzo_pubblico | prezzo_rivenditore | ...
```

Questi file alimentano due flussi operativi distinti:

1. **Anagrafica articoli del fornitore**: per ogni articolo che l'azienda tratta,
   serve sapere come quel fornitore lo identifica (codice, descrizione propria,
   unità di misura eventualmente diversa).
2. **Generazione del listino di vendita clienti**: il listino ricevuto NON è un
   listino di costo di acquisto — è il **listino dei prezzi di vendita suggeriti**
   (PVC / MSRP / listino al pubblico). L'azienda lo usa come base per calcolare
   i propri listini clienti applicando sconti o maggiorazioni.

### 1.2 Perché non basta il modello `vendite.listini` attuale

Il modello attuale `vendite.listini` → `listini_versioni` → `listini_associazioni`
→ `listini_righe` è progettato per rappresentare listini **operativi** di vendita,
selezionati da un resolver a 7 match_level (`fn_resolve_prezzo_listino`).

Il listino ricevuto dal fornitore è qualcosa di diverso:

- **Non passa dal resolver vendite** — è un ingresso al sistema, non un listino
  che il motore di pricing consulta per fatturare
- **Non ha semantica di scope** (BA, utility, emittente) — il contesto è
  implicitamente il fornitore stesso
- **Può contenere più prezzi per articolo** (pubblico, rivenditore, distributore)
  mentre `listini_righe` ha una sola colonna prezzo
- **Ha una relazione diretta con l'anagrafica fornitore e col suo codice articolo**,
  concetti che non esistono in `vendite.listini`

Usare il modello vendite per accogliere questi dati lo deformerebbe. Serve un
modello parallelo, più semplice ma adatto a questa semantica.

### 1.3 Cosa NON è questo WIP

- **Non è il listino acquisti** (costi reali negoziati con il fornitore).
  Quello è un progetto separato (`acquisti.listini`). Questo WIP lascia
  intenzionalmente libero quel naming.
- **Non è il motore di import Excel/CSV**. Il parser è fuori scope: qui si
  progettano solo le tabelle che lo accoglieranno.
- **Non è il meccanismo di derivazione del listino clienti** (regole sconto/
  maggiorazione). Rimandato: il modello sorgente deve solo non vincolarlo.

---

## 2. Decisioni architetturali

### 2.1 Schema di destinazione: `catalogo`

Il listino del fornitore è dato di riferimento che appartiene all'articolo.
Non è ciclo vendite (non viene risolto dal pricing) e non è ciclo acquisti
(non è il costo reale). Sta quindi in `catalogo`, schema neutro tra i due cicli.

Questa scelta lascia `acquisti.listini` libero per il futuro listino dei costi
d'acquisto reali.

### 2.2 Pattern 3 livelli replicato da vendite, ma semplificato

Si riusa lo schema **testata → versione → righe** consolidato in `vendite.listini_*`,
perché risolve correttamente storicità, staging controllato, no-overlap temporale
e cascata di guard.

**Non si replica** `listini_associazioni` (nessun multi-contesto: il fornitore
è il contesto) né il resolver a match_level (lookup banale
`(fornitore_id, articolo_id, data) → prezzo`).

### 2.3 Normalizzazione dei tipi di prezzo

Un listino fornitore può contenere più colonne prezzo (pubblico, rivenditore,
distributore, netto). Si sceglie la **normalizzazione**: sotto-tabella
`listini_fornitori_righe_prezzi` con FK a `config.tipi_prezzo_fornitore`.
Seed iniziale minimo: `PUBBLICO`, `RIVENDITORE`, `NETTO`.

### 2.4 Mappatura articoli come entità di prima classe

La tabella `catalogo.articoli_fornitori` è il cardine del sistema. È una N:M
tra `catalogo.articoli` e `anagrafiche.fornitori` arricchita con
`codice_articolo_fornitore`, `descrizione_fornitore`, `uom_fornitore_id` e
attributi logistici opzionali.

Vincoli chiave:
- `UNIQUE (articolo_id, fornitore_id)` — un solo legame per coppia
- `UNIQUE (fornitore_id, codice_articolo_fornitore)` — il fornitore non può
  riusare lo stesso codice su articoli interni diversi
- `UNIQUE (articolo_id) WHERE preferito IS TRUE` — massimo un fornitore
  preferito per articolo

> **[NUOVO v2 — vedi §6.2]**: il vincolo UNIQUE sul codice fornitore è più
> fragile di quanto sembri. I fornitori con cataloghi sporchi sono la norma.
> Vedi la sezione criticità per la proposta di abbassarlo a livello versione.

### 2.5 Multi-fornitore per stesso articolo pienamente supportato

Lo stesso articolo può avere mappature verso più fornitori. Ogni fornitore ha
il proprio listino con i propri prezzi. La decisione "quale fornitore usare
come base per derivare il listino clienti" è responsabilità della derivazione
(fuori scope).

### 2.6 Snapshot del codice fornitore sulla riga listino

Le righe conservano `codice_fornitore_snapshot` e `descrizione_fornitore_snapshot`
come fotografia al momento dell'import. Questo permette diff mese-su-mese e
audit indipendentemente da come cambia la mappatura master.

### 2.7 Altre scelte

- **Valuta sulla versione** (`valuta char(3)` NOT NULL DEFAULT `'EUR'`): futuro-proof
- **IVA**: prezzi sempre netti imponibili, nessun flag `prezzo_ivato`
- **Scaglioni quantità**: non inclusi (YAGNI v1)
- **Soft-delete**: `attivo=false` ovunque
- **PK**: bigint per tabelle tecniche; `articolo_id` resta uuid

### [NUOVO v2] 2.8 Staging come requisito della fase 1, non ottimizzazione futura

> **Integrazione critica rispetto alla versione precedente.**

Il documento originale trattava la tabella di staging come componente opzionale
da aggiungere in una fase successiva. Questa posizione è **rivista**.

Senza staging, la prima implementazione non ha nessun meccanismo per gestire
import parziali, rollback o riconciliazione. Per un'azienda con anche solo
3-4 fornitori e 300-500 articoli ciascuno, l'inserimento completamente manuale
non è praticabile nemmeno nella fase pilota.

**Decisione**: la tabella di staging entra in scope dalla Fase 1, anche in
forma semplificata (senza il parser Excel automatico, che rimane rimandato).
Il flusso minimo della fase 1 diventa:

1. Inserimento manuale delle righe nella staging (o import CSV grezzo)
2. Risoluzione manuale assistita (mappatura articoli)
3. Commit batch nelle tabelle definitive

Le tabelle definitive rimangono pulite e vincolate dal giorno 1. La staging
assorbe la sporcizia del processo di caricamento.

### [NUOVO v2] 2.9 Derivazione: progettata ora, implementata dopo

> **Integrazione critica rispetto alla versione precedente.**

Il documento originale rimandava completamente la progettazione della
derivazione. Il problema è che senza almeno la struttura delle regole di
derivazione definita, il listino fornitore importato è un dato morto: non
produce nessun effetto sui prezzi di vendita finché la derivazione non viene
implementata. Nel periodo intermedio l'operatore deve continuare a gestire
i listini di vendita a mano.

**Decisione**: nella stessa finestra di analisi di questo WIP, definire almeno:
- La struttura della tabella regole di derivazione
- I tipi di regola previsti (1:1, sconto %, sconto per segmento, maggiorazione)
- Il formato del link tracciabile tra versione fornitore e versione vendite derivata

L'implementazione rimane rimandata. Ma il modello sorgente non deve essere
approvato senza sapere come verrà consumato.

Vedi §5.3 per il dettaglio della struttura proposta.

---

## 3. Modello dati proposto

### 3.1 Mappatura master: `catalogo.articoli_fornitori`

```sql
CREATE TABLE catalogo.articoli_fornitori (
    id                         bigserial   PRIMARY KEY,
    articolo_id                uuid        NOT NULL REFERENCES catalogo.articoli(id),
    fornitore_id               bigint      NOT NULL REFERENCES anagrafiche.fornitori(id),
    codice_articolo_fornitore  varchar     NOT NULL,
    descrizione_fornitore      varchar     NULL,
    uom_fornitore_id           bigint      NULL REFERENCES catalogo.unita_misura(id),
    preferito                  boolean     NOT NULL DEFAULT false,
    moq                        numeric     NULL,
    lotto_multiplo             numeric     NULL,
    lead_time_giorni           integer     NULL,
    meta                       jsonb       NOT NULL DEFAULT '{}'::jsonb,
    attivo                     boolean     NOT NULL DEFAULT true,
    data_insert                timestamptz NOT NULL DEFAULT now(),
    user_insert                text        NOT NULL DEFAULT CURRENT_USER,
    data_update                timestamptz NOT NULL DEFAULT now(),
    user_update                text        NOT NULL DEFAULT CURRENT_USER,
    tx_id                      uuid        NULL,
    CONSTRAINT uq_articoli_fornitori_articolo_fornitore
        UNIQUE (articolo_id, fornitore_id),
    CONSTRAINT uq_articoli_fornitori_codice_fornitore
        UNIQUE (fornitore_id, codice_articolo_fornitore)
);

CREATE UNIQUE INDEX uq_articoli_fornitori_preferito
    ON catalogo.articoli_fornitori (articolo_id)
    WHERE preferito IS TRUE AND attivo IS TRUE;
```

> **[NUOVO v2]** Il vincolo `uq_articoli_fornitori_codice_fornitore` è dichiarato
> sulla mappatura master (stato corrente). Le righe listino conservano lo snapshot
> storico del codice indipendentemente. Se un fornitore riusa un codice per un
> articolo diverso in un listino successivo, questo va gestito come eccezione
> manuale con soft-delete della mappatura vecchia e creazione della nuova.
> Vedi §6.2 per la proposta di abbassare il vincolo a livello versione.

### 3.2 Testata listino: `catalogo.listini_fornitori`

```sql
CREATE TABLE catalogo.listini_fornitori (
    id             bigserial   PRIMARY KEY,
    fornitore_id   bigint      NOT NULL REFERENCES anagrafiche.fornitori(id),
    codice         varchar     NOT NULL,
    descrizione    varchar     NOT NULL,
    meta           jsonb       NOT NULL DEFAULT '{}'::jsonb,
    attivo         boolean     NOT NULL DEFAULT true,
    data_insert    timestamptz NOT NULL DEFAULT now(),
    user_insert    text        NOT NULL DEFAULT CURRENT_USER,
    data_update    timestamptz NOT NULL DEFAULT now(),
    user_update    text        NOT NULL DEFAULT CURRENT_USER,
    tx_id          uuid        NULL,
    CONSTRAINT uq_listini_fornitori_codice UNIQUE (fornitore_id, codice)
);
```

### 3.3 Versione temporale: `catalogo.listini_fornitori_versioni`

```sql
CREATE TABLE catalogo.listini_fornitori_versioni (
    id                      bigserial   PRIMARY KEY,
    listino_fornitore_id    bigint      NOT NULL
        REFERENCES catalogo.listini_fornitori(id),
    codice_versione         varchar     NOT NULL,
    valido_dal              date        NOT NULL,
    valido_al               date        NULL,
    valuta                  char(3)     NOT NULL DEFAULT 'EUR',
    stato                   varchar     NOT NULL DEFAULT 'BOZZA'
        CHECK (stato IN ('BOZZA', 'ATTIVA', 'CHIUSA')),
    meta                    jsonb       NOT NULL DEFAULT '{}'::jsonb,
    attivo                  boolean     NOT NULL DEFAULT true,
    data_insert             timestamptz NOT NULL DEFAULT now(),
    user_insert             text        NOT NULL DEFAULT CURRENT_USER,
    data_update             timestamptz NOT NULL DEFAULT now(),
    user_update             text        NOT NULL DEFAULT CURRENT_USER,
    tx_id                   uuid        NULL,
    CONSTRAINT chk_listini_fornitori_versioni_date
        CHECK (valido_al IS NULL OR valido_al >= valido_dal),
    CONSTRAINT uq_listini_fornitori_versioni_codice
        UNIQUE (listino_fornitore_id, codice_versione)
);

CREATE INDEX ex_listini_fornitori_versioni_no_overlap
    ON catalogo.listini_fornitori_versioni
    USING gist (
        listino_fornitore_id,
        daterange(valido_dal, COALESCE(valido_al, 'infinity'::date), '[]')
    )
    WHERE attivo IS TRUE AND stato = 'ATTIVA';
```

### 3.4 Riga articolo: `catalogo.listini_fornitori_righe`

```sql
CREATE TABLE catalogo.listini_fornitori_righe (
    id                              bigserial   PRIMARY KEY,
    listino_fornitore_versione_id   bigint      NOT NULL
        REFERENCES catalogo.listini_fornitori_versioni(id),
    articolo_id                     uuid        NOT NULL
        REFERENCES catalogo.articoli(id),
    uom_id                          bigint      NOT NULL
        REFERENCES catalogo.unita_misura(id),
    codice_fornitore_snapshot       varchar     NOT NULL,
    descrizione_fornitore_snapshot  varchar     NULL,
    -- [NUOVO v2] flag conversione UoM mancante
    uom_conversione_disponibile     boolean     NOT NULL DEFAULT true,
    meta                            jsonb       NOT NULL DEFAULT '{}'::jsonb,
    attivo                          boolean     NOT NULL DEFAULT true,
    data_insert                     timestamptz NOT NULL DEFAULT now(),
    user_insert                     text        NOT NULL DEFAULT CURRENT_USER,
    data_update                     timestamptz NOT NULL DEFAULT now(),
    user_update                     text        NOT NULL DEFAULT CURRENT_USER,
    tx_id                           uuid        NULL
);

CREATE UNIQUE INDEX uq_listini_fornitori_righe_key_attiva
    ON catalogo.listini_fornitori_righe
        (listino_fornitore_versione_id, articolo_id, uom_id)
    WHERE attivo IS TRUE;
```

> **[NUOVO v2]** Il campo `uom_conversione_disponibile` segnala se al momento
> dell'import esisteva una conversione valida tra `uom_fornitore_id` (dalla
> mappatura) e la UoM interna. Se FALSE, la riga è importata ma non è
> derivabile automaticamente verso il listino clienti finché la conversione
> non viene aggiunta. Questo evita di bloccare l'intero import per una UoM
> mancante. Vedi §6.7 per il dettaglio.

### 3.5 Sotto-riga prezzi: `catalogo.listini_fornitori_righe_prezzi`

```sql
CREATE TABLE catalogo.listini_fornitori_righe_prezzi (
    id                           bigserial   PRIMARY KEY,
    listino_fornitore_riga_id    bigint      NOT NULL
        REFERENCES catalogo.listini_fornitori_righe(id),
    tipo_prezzo_id               smallint    NOT NULL
        REFERENCES config.tipi_prezzo_fornitore(id),
    valore                       numeric     NOT NULL CHECK (valore >= 0),
    attivo                       boolean     NOT NULL DEFAULT true,
    data_insert                  timestamptz NOT NULL DEFAULT now(),
    user_insert                  text        NOT NULL DEFAULT CURRENT_USER,
    data_update                  timestamptz NOT NULL DEFAULT now(),
    user_update                  text        NOT NULL DEFAULT CURRENT_USER,
    tx_id                        uuid        NULL
);

CREATE UNIQUE INDEX uq_listini_fornitori_righe_prezzi_tipo
    ON catalogo.listini_fornitori_righe_prezzi
        (listino_fornitore_riga_id, tipo_prezzo_id)
    WHERE attivo IS TRUE;
```

### 3.6 Catalogo tipi prezzo: `config.tipi_prezzo_fornitore`

```sql
CREATE TABLE config.tipi_prezzo_fornitore (
    id            smallserial PRIMARY KEY,
    codice        varchar     NOT NULL UNIQUE,
    descrizione   varchar     NOT NULL,
    attivo        boolean     NOT NULL DEFAULT true,
    meta          jsonb       NOT NULL DEFAULT '{}'::jsonb,
    data_insert   timestamptz NOT NULL DEFAULT now(),
    user_insert   text        NOT NULL DEFAULT CURRENT_USER,
    data_update   timestamptz NOT NULL DEFAULT now(),
    user_update   text        NOT NULL DEFAULT CURRENT_USER,
    tx_id         uuid        NULL
);
```

Seed minimo: `PUBBLICO`, `RIVENDITORE`, `NETTO`.

---

## 4. Flusso di gestione degli articoli non mappati

### 4.1 Scenari all'arrivo del file

1. **Articolo interno esiste E mappatura esiste** → caso felice
2. **Articolo interno esiste MA mappatura non esiste** → creare mappatura, poi importare
3. **Articolo interno NON esiste** → creare articolo, poi mappatura, poi importare
4. **Riga ambigua o sporca** → scarto con motivazione

### [NUOVO v2] 4.2 Staging come componente di fase 1

> **Revisione rispetto al documento originale**: la staging non è più opzionale.
> Entra in scope dalla Fase 1 in forma semplificata. Vedi decisione §2.8.

```sql
CREATE TABLE catalogo.listini_fornitori_import_staging (
    id                         bigserial   PRIMARY KEY,
    fornitore_id               bigint      NOT NULL
        REFERENCES anagrafiche.fornitori(id),
    batch_id                   uuid        NOT NULL,
    origine_file               varchar     NULL,
    riga_numero                integer     NOT NULL,
    codice_articolo_fornitore  varchar     NOT NULL,
    descrizione_grezza         varchar     NULL,
    uom_grezza                 varchar     NULL,
    prezzi_grezzi              jsonb       NOT NULL DEFAULT '{}'::jsonb,
    articolo_id_risolto        uuid        NULL REFERENCES catalogo.articoli(id),
    uom_id_risolta             bigint      NULL REFERENCES catalogo.unita_misura(id),
    -- [NUOVO v2] flag UoM non convertibile
    uom_conversione_mancante   boolean     NOT NULL DEFAULT false,
    stato                      varchar     NOT NULL DEFAULT 'NUOVA'
        CHECK (stato IN ('NUOVA', 'RISOLTA', 'RISOLTA_UOM_MANCANTE',
                         'SCARTATA', 'IMPORTATA')),
    motivo_scarto              varchar     NULL,
    meta                       jsonb       NOT NULL DEFAULT '{}'::jsonb,
    attivo                     boolean     NOT NULL DEFAULT true,
    data_insert                timestamptz NOT NULL DEFAULT now(),
    user_insert                text        NOT NULL DEFAULT CURRENT_USER,
    data_update                timestamptz NOT NULL DEFAULT now(),
    user_update                text        NOT NULL DEFAULT CURRENT_USER,
    tx_id                      uuid        NULL
);
```

> **[NUOVO v2]** Aggiunto stato `RISOLTA_UOM_MANCANTE`: la riga è risolta
> (articolo e mappatura esistono) ma la conversione UoM non è disponibile.
> Viene importata nelle tabelle definitive con `uom_conversione_disponibile = false`.
> Non blocca il commit del batch. L'operatore può aggiungere la conversione
> in seguito e rielaborare solo queste righe.

**Semantica degli stati**:

| Stato                  | Significato                                                        |
| ---------------------- | ------------------------------------------------------------------ |
| `NUOVA`                | Appena caricata, non ancora elaborata                              |
| `RISOLTA`              | Articolo e UoM risolti, conversione disponibile, pronta per commit |
| `RISOLTA_UOM_MANCANTE` | Articolo risolto, UoM mancante — importabile con flag              |
| `SCARTATA`             | Non importabile, motivo registrato                                 |
| `IMPORTATA`            | Committed nelle tabelle definitive                                 |

### 4.3 Riconciliazione manuale

Per le righe orfane, l'utente deve poter:

1. Creare l'articolo in `catalogo.articoli` se non esiste
2. Creare la mappatura in `catalogo.articoli_fornitori` con precompilazione
   da staging
3. Aggiungere la conversione UoM mancante se necessario
4. Rielaborare il batch sulle righe ancora in stato `NUOVA` o
   `RISOLTA_UOM_MANCANTE`

---

## 5. Integrazione con il modello listini esistente

### 5.1 Separazione netta dai `vendite.listini`

Il listino fornitore **non** viene letto dal resolver `fn_resolve_prezzo_listino`.
Il resolver continua a operare esclusivamente sulle tabelle in `vendite`. Le due
strutture sono collegate solo via un processo esplicito di derivazione.

Questa separazione garantisce:
1. Il resolver vendite resta intatto
2. Pricing mode diversi tra i due domini
3. Performance: il resolver non conosce fonti dati esterne durante la fatturazione

### 5.2 Collegamento con `catalogo.articoli`

L'unico punto di contatto forte è `catalogo.articoli.id` (uuid), referenziato da
`articoli_fornitori.articolo_id` e `listini_fornitori_righe.articolo_id`.

Il trigger `trgfn_child_requires_active_parent` già usato in `vendite.listini_righe`
va replicato su entrambe le nuove tabelle.

### [NUOVO v2] 5.3 Struttura della derivazione — progettata ora

> **Integrazione critica rispetto alla versione precedente.** Vedi decisione §2.9.

Il flusso target a regime:

```
catalogo.listini_fornitori_versioni  (sorgente)
      │
      │  fn_deriva_listino_clienti(versione_id, regole_id, target_listino_id)
      │
      ▼
vendite.listini_versioni  (target, BOZZA)
vendite.listini_righe     (target, prezzi derivati)
```

#### Tabella regole di derivazione

```sql
CREATE TABLE catalogo.regole_derivazione_listino (
    id                              bigserial   PRIMARY KEY,
    codice                          varchar     NOT NULL UNIQUE,
    descrizione                     varchar     NOT NULL,
    listino_fornitore_id            bigint      NOT NULL
        REFERENCES catalogo.listini_fornitori(id),
    listino_vendita_target_id       bigint      NOT NULL
        REFERENCES vendite.listini(id),
    tipo_prezzo_base_id             smallint    NOT NULL
        REFERENCES config.tipi_prezzo_fornitore(id),
    -- tipo regola: COPIA_1A1, SCONTO_GLOBALE, MAGGIORAZIONE_GLOBALE
    tipo_regola                     varchar     NOT NULL
        CHECK (tipo_regola IN ('COPIA_1A1', 'SCONTO_GLOBALE',
                               'MAGGIORAZIONE_GLOBALE')),
    variazione_percentuale          numeric     NULL,
    -- segmentazione per BA (opzionale, per regole per-cliente)
    billing_account_id              bigint      NULL,
    meta                            jsonb       NOT NULL DEFAULT '{}'::jsonb,
    attivo                          boolean     NOT NULL DEFAULT true,
    data_insert                     timestamptz NOT NULL DEFAULT now(),
    user_insert                     text        NOT NULL DEFAULT CURRENT_USER,
    data_update                     timestamptz NOT NULL DEFAULT now(),
    user_update                     text        NOT NULL DEFAULT CURRENT_USER,
    tx_id                           uuid        NULL
);
```

#### Link tracciabile tra versione fornitore e versione vendite

La versione `vendite.listini_versioni` derivata registra l'origine in `meta`:

```json
{
  "derivazione": {
    "listino_fornitore_versione_id": 42,
    "regola_id": 7,
    "data_derivazione": "2026-04-15T10:00:00Z",
    "operatore": "mario.rossi",
    "variazione_percentuale_applicata": -15.0,
    "righe_derivate": 487,
    "righe_skippate_uom_mancante": 3
  }
}
```

#### Tipi di regola previsti

| Tipo                    | Comportamento                                                                 |
| ----------------------- | ----------------------------------------------------------------------------- |
| `COPIA_1A1`             | Il prezzo del tipo base (es. PUBBLICO) entra direttamente nelle righe vendita |
| `SCONTO_GLOBALE`        | Prezzo base * (1 - variazione/100)                                            |
| `MAGGIORAZIONE_GLOBALE` | Prezzo base * (1 + variazione/100)                                            |

Regole per-cliente: se `billing_account_id` è valorizzato, la riga vendita
derivata avrà quel BA come dimensione di contesto (match_level 4 nel resolver).

**[NUOVO v2 — variazione su BOZZA]**: dopo la derivazione, la versione
`vendite.listini_versioni` target è in stato BOZZA. Prima di attivarla,
l'operatore può applicare una variazione percentuale massa (aumento/riduzione)
con l'operazione `applica-variazione` già definita in `sviluppo-listini-v3.md §N8`.
Questo permette di correggere l'intera derivazione prima che diventi operativa,
senza modificare le regole di derivazione.

### 5.4 Relazione con il futuro `acquisti.listini`

| Aspetto          | `catalogo.listini_fornitori`              | `acquisti.listini` (futuro)              |
| ---------------- | ----------------------------------------- | ---------------------------------------- |
| Cosa rappresenta | Prezzi di vendita suggeriti dal fornitore | Costi d'acquisto reali negoziati         |
| Fonte            | File ricevuto dal fornitore               | Conferme d'ordine, fatture, negoziazione |
| Usato per        | Derivare listino clienti                  | Calcolare margine, valorizzare magazzino |
| Referenziato da  | Derivazione → `vendite.listini`           | Analisi margine, valorizzazione stock    |

---

## 6. Criticità e punti di attenzione

### 6.1 Confusione semantica "listino fornitore"

**Rischio**: chi legge la tabella `listini_fornitori` può pensare a costi
d'acquisto.

**Mitigazione**:
- Documentazione manuale `docs/it/dbzero/catalogo/manual/` con semantica esplicita
- Il futuro `acquisti.listini` userà naming che differenzia chiaramente
- Aggiungere commento DDL esplicito sulla tabella:
  `COMMENT ON TABLE catalogo.listini_fornitori IS 'Prezzi di vendita suggeriti dal fornitore (PVC/MSRP). NON sono costi d acquisto reali.'`

### [NUOVO v2] 6.2 Vincolo UNIQUE sul codice fornitore: troppo ottimista

> **Integrazione critica rispetto alla versione precedente.**

Il vincolo `UNIQUE (fornitore_id, codice_articolo_fornitore)` sulla mappatura
master assume che un fornitore non riusi mai lo stesso codice per articoli
diversi. Nella realtà B2B i fornitori con cataloghi sporchi sono la norma:
codici duplicati, codici riusati tra listini diversi, varianti di formato
dello stesso codice.

**Proposta**: abbassare la garanzia di unicità dal livello mappatura master
al livello versione listino.

In pratica:
- La mappatura master (`articoli_fornitori`) mantiene il vincolo UNIQUE come
  rappresentazione dello stato corrente — best-effort, gestibile come
  eccezione manuale se violato
- Il vincolo forte di unicità `(fornitore_id, codice_articolo_fornitore)`
  viene aggiunto anche su `listini_fornitori_righe` a livello di versione,
  dove è semanticamente più corretto:

```sql
CREATE UNIQUE INDEX uq_listini_fornitori_righe_codice_versione
    ON catalogo.listini_fornitori_righe
        (listino_fornitore_versione_id, codice_fornitore_snapshot)
    WHERE attivo IS TRUE;
```

Questo garantisce che dentro una versione un codice fornitore appaia una sola
volta, senza bloccare l'evoluzione storica del catalogo fornitore tra versioni
diverse.

### 6.3 Doppia verità sul codice fornitore

Il codice articolo del fornitore vive in due posti:
1. `articoli_fornitori.codice_articolo_fornitore` — mappatura corrente
2. `listini_fornitori_righe.codice_fornitore_snapshot` — fotografia storica

Non è una duplicazione: hanno significato diverso. La documentazione delle
colonne deve chiarirlo esplicitamente.

### 6.4 Cambio mappatura fornitore

Se l'utente soft-delete la mappatura, i listini storici rimangono validi
perché `articolo_id` continua a puntare correttamente all'articolo.
**Decisione**: non blocca, ma la UI mostra un warning "esistono N righe
listino storiche che fanno riferimento a questo codice fornitore".

### 6.5 Multi-fornitore e derivazione ambigua

Quando un articolo ha più fornitori preferiti, la derivazione deve decidere
quale listino usare come base. Default: fornitore `preferito=true`.
Parametrizzabile nella regola di derivazione (§5.3). Da definire nella
fase di implementazione della derivazione.

### 6.6 Import parziale e stato BOZZA

Se il processo di import fallisce a metà, la versione rimane BOZZA con righe
parziali. Serve idempotenza dell'import (ripartire senza duplicare) o pulizia
delle BOZZA abbandonate. Problema del motore di import, non del modello.

### [NUOVO v2] 6.7 UoM non convertibile: non blocca l'import

> **Integrazione critica rispetto alla versione precedente.**

Se il fornitore usa una UoM per cui non esiste conversione verso la UoM
interna, il documento originale non prevedeva una soluzione concreta.

**Proposta**: l'import non viene bloccato. La riga viene importata nelle
tabelle definitive con `uom_conversione_disponibile = false`. Questo significa:

- La riga è visibile e consultabile
- Non può essere usata dalla funzione di derivazione per generare righe
  `vendite.listini_righe` finché la conversione non è disponibile
- L'UI segnala chiaramente le righe con questo flag
- Quando l'operatore aggiunge la conversione mancante, può rielaborare
  selettivamente solo queste righe

La funzione di derivazione skippa le righe con `uom_conversione_disponibile = false`
e le registra nel campo `righe_skippate_uom_mancante` del log in `meta`.

### 6.8 Tipi prezzo e standardizzazione cross-fornitore

Due fornitori possono usare nomi diversi per lo stesso tipo di prezzo.
La tabella `config.tipi_prezzo_fornitore` è unica. Il mapping
`stringa_fornitore → tipo_prezzo_id` avviene al momento dell'import.
Per ora YAGNI: se il volume lo richiede, si aggiunge una tabella di
configurazione per fornitore.

### [NUOVO v2] 6.9 Diff versioni consecutive: articoli scomparsi

> **Gap non presente nel documento originale.**

Quando arriva un nuovo listino mensile, alcuni articoli presenti nella
versione precedente potrebbero non comparire più. Il sistema attuale
non segnala nulla — quelle righe semplicemente non esistono nella nuova
versione.

**Impatto operativo**: un articolo discontinuato dal fornitore rimane
silenziosamente nel listino attivo finché qualcuno non se ne accorge.

**Proposta**: funzione di diff tra versioni consecutive.

```sql
-- Articoli presenti in V_old ma assenti in V_new
SELECT r.articolo_id, r.codice_fornitore_snapshot, r.descrizione_fornitore_snapshot
FROM catalogo.listini_fornitori_righe r
WHERE r.listino_fornitore_versione_id = %(v_old_id)s
  AND r.attivo IS TRUE
  AND NOT EXISTS (
    SELECT 1 FROM catalogo.listini_fornitori_righe r2
    WHERE r2.listino_fornitore_versione_id = %(v_new_id)s
      AND r2.articolo_id = r.articolo_id
      AND r2.attivo IS TRUE
  );
```

Implementazione:

- Endpoint API: `GET /api/v1/catalogo/listini-fornitori/{id}/versioni/{ver_id}/diff/?confronta_con={ver_old_id}`
- Response: liste separate di articoli aggiunti, rimossi, modificati (prezzo cambiato), invariati
- Il diff viene mostrato in UI prima del commit del batch e prima dell'attivazione
- Le righe rimosse vengono evidenziate con un warning: "questi articoli erano
  nel listino precedente e non compaiono in quello nuovo"

---

## 7. Roadmap implementativa

### Fase 1 — Anagrafica mappatura + staging (RIVISTA)

> **[NUOVO v2]**: staging inclusa in questa fase, non rimandata.

- Migration `catalogo.articoli_fornitori` + trigger standard
- Migration `catalogo.listini_fornitori_import_staging` (forma semplificata)
- Backend: CRUD mappatura + gestione batch staging
- Frontend: pagina mappatura (da scheda articolo e da scheda fornitore)
- Test: pgtap invarianti + Django unit

### Fase 2 — Config tipi prezzo

- Migration `config.tipi_prezzo_fornitore` + seed iniziale
- Backend: CRUD (read-only inizialmente)

### Fase 3 — Listini fornitori (testata/versione/riga/prezzi)

- 4 migration con trigger standard e cascade guard
- Aggiunta indice `uq_listini_fornitori_righe_codice_versione` (§6.2)
- Backend: CRUD per gestione manuale (senza import automatico)
- Frontend: UI data entry manuale
- Test: pgtap invarianti (no-overlap, stati, attivo parent)

### Fase 4 — Funzione di attivazione atomica

- `catalogo.fn_activate_listino_fornitore_versione(versione_id)` con
  auto-close della precedente nella stessa transazione

### [NUOVO v2] Fase 4b — Diff versioni

- Funzione DB diff tra versioni consecutive
- Endpoint API diff
- UI: mostra diff prima del commit batch e prima dell'attivazione

### Fase 5 — Regole di derivazione (ANTICIPATA RISPETTO ALL'IMPORT)

> **[NUOVO v2]**: la struttura della derivazione viene progettata e
> implementata prima del motore di import, non dopo. Vedi §2.9 e §5.3.

- Migration `catalogo.regole_derivazione_listino`
- Funzione `catalogo.fn_deriva_listino_clienti(versione_id, regola_id)`
- Backend + frontend per gestione regole e avvio derivazione
- Integrazione con `applica-variazione` di `vendite.listini_versioni`
  per correzioni post-derivazione in BOZZA

### Fase 6 — Motore di import Excel/CSV

- Tabella staging completa con tutti gli stati
- Parser file + risoluzione batch automatica
- UI riconciliazione orfani e UoM mancanti
- Gestione articoli non mappati e creazione mappatura assistita

---

## 8. Aperti espliciti (non decisi in questo WIP)

- **Derivazione listino clienti**: regole per-segmento, override manuali righe
  derivate, ripetibilità. Struttura definita in §5.3, implementazione da schedulare.
- **Motore di import Excel/CSV**: parser, validazione, risoluzione automatica,
  UI riconciliazione. Fase 6.
- **Mapping tipi prezzo per fornitore**: dizionario per-fornitore se la
  nomenclatura diverge significativamente. Da valutare alla prima integrazione.
- **Scaglioni quantità**: rimandato a necessità reale.
- **Multi-valuta avanzata**: supporto base con `valuta char(3)` sulla versione;
  conversione valutaria e storico cambi è problema separato.
- **Relazione con `acquisti.listini` futuro**: coesistenza prevista, modello
  acquisti non progettato qui.
- **Variazione percentuale massa su versione fornitore BOZZA**: coerente con
  quanto definito per `vendite.listini` in `sviluppo-listini-v3.md §N8`.
  Da valutare se implementare anche qui con lo stesso pattern o se è
  sufficiente agire sulla versione vendite dopo la derivazione.

---

## 9. Riepilogo decisionale

| Decisione                    | Valore                                               | Motivazione                                                                                   |
| ---------------------------- | ---------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Schema                       | `catalogo`                                           | Dato di riferimento, neutro vendite/acquisti                                                  |
| Pattern                      | Testata/versione/riga + sotto-prezzi                 | Riuso controllato da vendite, senza resolver/associazioni                                     |
| Tipi prezzo                  | Normalizzati via `config.tipi_prezzo_fornitore`      | Estensibile senza DDL                                                                         |
| Mappatura                    | `articoli_fornitori` N:M con preferito unico         | Supporto multi-fornitore                                                                      |
| Snapshot codice fornitore    | Sulla riga listino                                   | Audit e diff storici                                                                          |
| Valuta                       | `char(3)` sulla versione, default EUR                | Futuro-proof                                                                                  |
| Scaglioni quantità           | Esclusi v1                                           | YAGNI                                                                                         |
| **Staging**                  | **Fase 1, non opzionale**                            | **[NUOVO v2] Requisito funzionale, non ottimizzazione**                                       |
| **Vincolo codice fornitore** | **UNIQUE su versione, non solo mappatura master**    | **[NUOVO v2] Fornitori con cataloghi sporchi sono la norma**                                  |
| **UoM non convertibile**     | **Import con flag, non blocco**                      | **[NUOVO v2] Evita di bloccare batch per singola UoM mancante**                               |
| **Diff versioni**            | **Funzione dedicata, mostrata prima del commit**     | **[NUOVO v2] Articoli scomparsi devono essere segnalati**                                     |
| **Derivazione**              | **Struttura progettata ora, implementata in Fase 5** | **[NUOVO v2] Il modello sorgente non può essere approvato senza sapere come verrà consumato** |
| Motore import                | Staging predisposta, implementazione Fase 6          | Granularità fasi                                                                              |
| PK                           | bigint per tabelle tecniche                          | Coerente con linee-guida-sql                                                                  |
| Soft-delete                  | `attivo=false` ovunque                               | Coerente con il resto del modello                                                             |

---

*WIP Listini fornitori — ZeroERP (aprile 2026, v2 — consolidato con integrazioni critiche)*