# Sviluppo Listini — Acquisizione da flussi esterni (WIP v7)

> Stato: **analisi preliminare.** Documento di ingresso per la prossima
> iterazione dopo v5 (pricing + resolver) e v6 (debiti tecnici).
>
> Ultima revisione: 15 aprile 2026.
>
> Questo documento raccoglie il problema emerso durante la chiusura F3
> dello sprint v5: le promo (e in generale i listini, gli articoli,
> eventualmente altre entita' pricing) arrivano da **flussi esterni di
> acquisizione** (tipicamente fornitori), non sempre creati a mano via
> UI admin. Serve un modello di **tracciabilita' del flusso di origine**
> coerente e applicabile trasversalmente alle entita' coinvolte.
>
> Oggi la tabella `vendite.promo_articoli` (e simili) NON ha colonne
> dedicate al flusso import: chi guarda una riga non sa se proviene da
> UI admin o da un lotto ETL di un fornitore specifico.

Riferimenti:

* [sviluppo-listini-v5.md](../work-done/sviluppo-listini-v5.md) — modello pricing + resolver
* [sviluppo-listini-v6.md](../work-done/sviluppo-listini-v6.md) — debiti tecnici v5 (se presente)
* [dbzero/vendite/tabelle/promo_articoli.md](../../dbzero/vendite/tabelle/promo_articoli.md)
* [dbzero/vendite/tabelle/listini_righe.md](../../dbzero/vendite/tabelle/listini_righe.md)
* [dbzero/catalogo/tabelle/articoli.md](../../dbzero/catalogo/tabelle/articoli.md)

---

## 1) Contesto

Il caricamento massivo di dati pricing (articoli, righe listino, promo) segue
tipicamente questi scenari:

- **Fornitore invia listino aggiornato** (CSV/XML/XLS periodico).
- **Sistema legacy sincronizza** (batch notturno, webhook).
- **Import manuale operatore** (drag-drop su UI) — esecuzione controllata
  di un flusso ETL, comunque tracciabile.

Lo stesso file puo' arrivare **piu' volte** (ri-consegna fornitore), con:
- stessi dati → conferma implicita (il sistema deve riconoscere idempotenza)
- dati modificati → aggiornamento di righe esistenti
- righe nuove → insert
- righe rimosse dall'ultimo invio → decisione: disattivazione? cancellazione?
  soft-flag "non piu' in listino"?

Il flusso TOCCA 3+ entita' DB correlate: `articoli`, `listini_righe`,
`promo_articoli` (piu' eventuali `unita_misura` o articoli_componenti per
BoM fornitore). Ogni riga import ha una **chiave esterna** del fornitore
(es. codice articolo del fornitore, che puo' differire dal codice interno)
e appartiene a un **lotto/flusso** identificabile.

---

## 2) Opzioni di modellazione tracciabilita'

### 2.1 Opzione A — Inline su ciascuna entita'

```sql
ALTER TABLE vendite.promo_articoli
    ADD COLUMN flusso_import_id bigint NULL
        REFERENCES import.flussi(id);
ALTER TABLE vendite.listini_righe
    ADD COLUMN flusso_import_id bigint NULL
        REFERENCES import.flussi(id);
ALTER TABLE catalogo.articoli
    ADD COLUMN flusso_import_id bigint NULL
        REFERENCES import.flussi(id);
```

- Ogni entita' conosce **il suo ultimo flusso di origine**.
- Promo create da UI admin: `flusso_import_id = NULL`.
- Idempotenza: UNIQUE su `(flusso_import_id, external_key_meta)` in una
  staging separata prima del commit definitivo.

**Pro:**

- Un solo JOIN per sapere "chi ha creato/aggiornato questa riga".
- Schema semplice, poco invasivo.
- Adatto se il modello business e' "l'ultimo flusso vince sempre".

**Contro:**

- Perde la sequenza storica: se promo `X` e' stata caricata dal flusso
  `F1`, poi confermata da `F2`, poi modificata da `F3`, resta solo `F3`
  in colonna.
- Nessuna distinzione tra "creata" e "ri-confermata senza modifiche".
- Se servira' in futuro un report "tutti i flussi che hanno toccato questa
  riga" bisognera' fare una join con tabella audit separata — che andra'
  popolata comunque.

### 2.2 Opzione B semplice — Tabella ponte per una sola entita'

```sql
CREATE TABLE vendite.promo_articoli_import_origine (
    id                  bigserial PRIMARY KEY,
    promo_id            bigint NOT NULL REFERENCES vendite.promo_articoli(id),
    flusso_import_id    bigint NOT NULL REFERENCES import.flussi(id),
    external_key        varchar NOT NULL,
    imported_at         timestamptz NOT NULL DEFAULT now(),
    azione              varchar NOT NULL -- CREATED|UPDATED|REAFFIRMED|DEACTIVATED
);
CREATE UNIQUE INDEX uq_promo_import_origine
    ON vendite.promo_articoli_import_origine (flusso_import_id, external_key);
```

- Ogni import lascia traccia dettagliata per la singola entita' coinvolta.
- Supporta multi-flusso per la stessa riga (storico completo).

**Pro:**

- Storico completo per audit.
- Distinzione tra CREATED / UPDATED / REAFFIRMED.

**Contro:**

- **Solo promo**. Se lo stesso flusso porta anche articoli e righe
  listino, servono 3 tabelle ponte gemelle (`articoli_import_origine`,
  `listini_righe_import_origine`, ...).
- Duplicazione di struttura → fragile se cambiano le regole.
- JOIN obbligatorio per sapere la origine: impatto performance se usato
  in query frequenti.

### 2.3 Opzione B polimorfica — Tabella ponte unica cross-entita' **[raccomandata]**

> ⚠️ **Da riscrivere sul modello della provenienza (2026-11-08)** quando l'opzione si riprende. Il progetto ha
> ora una grammatica sola per «una riga che punta a un'entità di tipo variabile» (`brief-db-sorgente-documento-e-riga`,
> guida [Sorgente polimorfa](../../guide/sorgente-polimorfa.md)): il tipo da un catalogo con FK (non
> `entita_schema`/`entita_tabella` in testo), **una** fra le due chiavi tipizzate secondo il `key_selector` del tipo
> (qui `entita_id_bigint` / `entita_id_uuid`), un `CHECK` di forma col nome della tabella, il BB che scrive la coppia e
> il guard unico. Il «polimorfismo soft» qui sotto è la stessa idea: va scritto con quei pezzi, non con colonne sue.
> Il richiamo a `commesse_attivita.sorgente_uid` è superato (la riga di commessa ha la chiave tipizzata).

```sql
CREATE TABLE import.flussi (
    id              bigserial PRIMARY KEY,
    tipo_flusso     varchar NOT NULL,        -- es. 'LISTINO_FORNITORE', 'PROMO_FORNITORE'
    fornitore_id    bigint NULL,             -- FK soggetto fornitore (opz.)
    nome_file       text NOT NULL,
    hash_file       text NOT NULL,           -- sha256 del payload, per idempotenza
    stato           varchar NOT NULL,        -- STAGING|CONFIRMED|APPLIED|FAILED|CANCELED
    stato_data      timestamptz NOT NULL DEFAULT now(),
    user_insert     text NOT NULL DEFAULT CURRENT_USER,
    meta            jsonb NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT uq_flusso_hash UNIQUE (hash_file, tipo_flusso)
);

CREATE TABLE import.flussi_righe (
    id                  bigserial PRIMARY KEY,
    flusso_id           bigint NOT NULL REFERENCES import.flussi(id),
    entita_schema       varchar NOT NULL,    -- 'vendite'|'catalogo'
    entita_tabella      varchar NOT NULL,    -- 'promo_articoli'|'articoli'|'listini_righe'
    entita_id_bigint    bigint NULL,         -- valorizzato se PK e' bigint
    entita_id_uuid      uuid NULL,           -- valorizzato se PK e' uuid (articoli)
    external_key        varchar NOT NULL,    -- codice fornitore o chiave ETL del record
    azione              varchar NOT NULL,    -- CREATED|UPDATED|REAFFIRMED|DEACTIVATED|SKIPPED
    payload_raw         jsonb NULL,          -- snapshot pre-apply (diagnostica)
    applied_at          timestamptz NULL,
    meta                jsonb NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT uq_flussi_righe_ext
        UNIQUE (flusso_id, external_key, entita_tabella),
    CONSTRAINT chk_flussi_righe_pk_xor
        CHECK ((entita_id_bigint IS NULL) <> (entita_id_uuid IS NULL))
);
```

**Pro:**

- **Un solo modello** copre tutte le entita' import-ate (promo, articoli,
  listini_righe, eventualmente altri in futuro).
- Storico completo ordinato per `flusso_id, applied_at`.
- Supporta azioni differenziate (`REAFFIRMED` quando il valore del flusso
  non ha cambiato nulla, utile per audit compliance).
- `external_key` disaccoppia il codice fornitore dal codice interno.
- `hash_file` + UNIQUE previene doppio import dello stesso payload (idempotenza
  end-to-end).
- **Coerente col pattern gia' usato nel progetto** per le sorgenti documento
  (`config.sorgenti` + `commesse_attivita.sorgente_tipo_id + sorgente_uid`):
  stessa logica "entita' polimorfica identificata da chiave di origine".

**Contro:**

- Polimorfismo soft (due colonne `entita_id_bigint` / `entita_id_uuid` con
  CHECK XOR) — meno elegante di una vera FK polimorfica (che PG non ha).
- Serve un piccolo service helper per risolvere la riga puntata
  (`resolve_entita(flussi_righe_id)`).
- JOIN obbligatorio per sapere la origine (come B semplice).

---

## 3) Motivazione della raccomandazione B polimorfica

**Perche' NO ad A (inline)**:

1. Il flusso esterno tocca almeno 3 entita' (articoli + righe listino + promo).
   Mettere `flusso_import_id` inline a ciascuna significa replicare 3 volte
   lo stesso campo + 3 indici FK + 3 colonne audit separate.
2. Perdita di storico: se il fornitore ri-invia 10 volte all'anno lo stesso
   articolo, non sapremo mai "questo articolo e' stato confermato/aggiornato
   10 volte" — solo l'ultimo flusso resta visibile. Per listini pricing questa
   informazione e' richiesta (compliance fornitore, trattativa).
3. Non risolve il problema `external_key`: il codice articolo del fornitore
   non e' il codice interno — dovrebbe finire in `meta` jsonb, degradando
   ulteriormente la tracciabilita'.

**Perche' NO a B semplice**:

1. Il problema e' identico su tutte e 3 le entita' (articoli, righe listino,
   promo). Creare 3 tabelle ponte gemelle e' duplicazione strutturale.
2. Quando domani si aggiunge una 4a entita' (es. `unita_misura` fornitore,
   `articoli_componenti` BoM fornitore), si duplica ancora. Pattern fragile
   alla scala.

**Perche' SI' a B polimorfica**:

1. Un solo modello → zero duplicazioni strutturali quando si aggiungono
   entita' al flusso.
2. Storico completo + idempotenza via `hash_file` + azioni differenziate.
3. Coerente col pattern `config.sorgenti` + `sorgente_tipo_id/uid` gia'
   consolidato in `vendite.commesse_attivita` per l'origine documento.
   Stesso mentale map per chi gia' conosce il progetto.
4. Disaccoppia `external_key` (fornitore) dalla PK interna → permette
   re-import anche dopo rename interno del codice articolo.
5. Il polimorfismo soft (bigint XOR uuid) e' un compromesso noto e
   accettato in PostgreSQL, soprattutto quando le entita' puntate condividono
   la stessa semantica di "riga importata" ma hanno tipi di PK diversi
   (bigint per listini/promo, uuid per articoli).

Trade-off accettato: JOIN extra ogni volta che serve conoscere il flusso
di origine. Mitigabile con view arricchita `vw_<entita>_con_origine_flusso`
se query specifiche diventano hot-path.

---

## 4) Processo: staging → conferma → apply

**Punto chiave operativo richiesto**: l'applicazione dei dati del flusso
alle tabelle destinazione NON deve essere automatica. Passaggi:

1. **Upload file** → parser produce righe in `import.flussi_righe` con
   `stato = 'STAGING'`, `payload_raw` popolato, `entita_id_* = NULL`.
2. **Preview / validazione** → UI mostra delta (nuove righe, righe
   aggiornate, righe non piu' in flusso) + eventuali errori (FK mancanti,
   violazioni, ambiguita' codice).
3. **Conferma esplicita operatore** → setta `flussi.stato = 'CONFIRMED'`.
   Nessuna scrittura sulle tabelle target (`promo_articoli`, `articoli`,
   ecc.) fino a questo punto.
4. **Apply** (sincrono o via job) → per ogni `flussi_righe`:
   - risolve `entita_id_*` via `external_key` (eventuale match su tabella
     esistente) o crea nuovo record;
   - applica mutazione (INSERT/UPDATE/soft-delete);
   - imposta `flussi_righe.applied_at = now()` e `azione` definitiva.
   - al termine: `flussi.stato = 'APPLIED'`.
5. **Rollback** (opz.): se `flussi.stato = 'APPLIED'` ma serve annullare,
   generare un flusso "inverso" o disattivare le righe toccate —
   decisione business da formalizzare.

**Vantaggi del passaggio di conferma**:

- Evita danni da file malformati (errore parser = flusso resta in STAGING,
  tabelle target intatte).
- Permette audit preventivo ("anteprima") dello stato risultante.
- Separa la responsabilita' tra chi carica (operatore) e chi conferma
  (admin / responsabile pricing).
- Rende il processo ri-eseguibile: un flusso STAGING si puo' cancellare e
  ri-caricare senza impatto sul DB core.

Sulle **promo** in particolare: la conferma manuale e' quasi sempre
richiesta (impatto commerciale diretto sul prezzo finale cliente),
quindi il pattern staging e' una hard requirement, non un nice-to-have.

---

## 5) Prossimi passi (analisi)

Prima di implementare serve:

- **Definire tipi_flusso effettivi**: LISTINO_FORNITORE_COMPLETO,
  PROMO_FORNITORE, ARTICOLI_DELTA, ecc. Ognuno ha regole proprie di
  mapping e apply.
- **Definire strategia "righe non piu' in flusso"**: disattivazione
  automatica? richiesta conferma separata? flag "presenza nell'ultimo
  flusso"? → decisione business per tipo di flusso.
- **Stabilire granularita' validazione pre-apply**: FK check + formato
  dati solo in staging, o anche simulazione dry-run dell'apply?
- **Definire schema `import` DB**: nuovo schema dedicato o parte di
  `dbops` / `script`?
- **Parser per formati**: CSV (standard COM fornitore), XLS, XML FatturaPA
  (se arrivano in quel formato), JSON custom.
- **Mapping `external_key` → PK interna**: regole di matching (es. codice
  articolo fornitore + fornitore_id univoco, oppure tabella
  `articoli_codici_fornitore` gia' esistente?).
- **UI flusso**: upload + preview + conferma + audit log delle righe
  applicate. Drawer dedicato sulla riga del flusso per vedere le righe
  generate.
- **Integrazione con v5 resolver**: le promo/listini create da flusso
  seguono la stessa semantica pricing del modello v5 — nessun impatto
  sul resolver, ma gli snapshot audit (`commesse_attivita.promo_id` ecc.)
  devono puntare agli ID "veri" delle entita' (non ai `flussi_righe`).

Ogni punto qui sopra meriterebbe una sessione di analisi dedicata.

---

## 6) Impatto su v5 corrente

Nessun impatto immediato. Il modello v5 (tabelle, resolver, admin UI)
resta valido. Quando v7 partira':

- Aggiunta `import.flussi` + `import.flussi_righe` (nuovo schema).
- Nessuna modifica alle tabelle pricing esistenti (il puntamento e' nella
  tabella ponte, non inline).
- UI admin promo corrente (`PromoArticoloDrawer`) resta in uso per inserimento
  manuale: affiancata da una UI flusso separata per import massivi.

---

*Sviluppo Listini — ZeroERP (15 aprile 2026, WIP v7 — acquisizione da flussi
esterni, analisi preliminare)*
