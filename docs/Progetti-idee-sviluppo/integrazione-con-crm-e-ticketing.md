# Zero ERP — Integrazione **CRM & Ticketing** → **Vendite**

> Versione: 2025‑08‑30 · Autore: mctit · Stato: **bozza operativa**

---

## 🎯 Scopo

Definire un’architettura pratica per alimentare **Preventivi, Contratti, Attività Fatturabili e Fatture** a partire da eventi di **CRM** (opportunità) e **Ticketing** (assistenza), riusando al massimo le tabelle già presenti in *catalogo* e *vendite*.

---

## 🧭 Contesto & Principi

* **Fonte unica prezzi/articoli**: `catalogo.articoli` come anagrafica unica di materiali/servizi/spese.
* **Documenti gestionali**: `vendite.preventivi*`, `vendite.contratti*`, `vendite.attivita_fatturabili`, `vendite.fatture*`.
* **Tracciabilità end‑to‑end**: ogni riga derivata da CRM/Ticketing porta con sé **fonte\_tipo/fonte\_id/fonte\_riga\_id**.
* **Idempotenza**: unique parziale su `(fonte_tipo, fonte_riga_id)`.
* **FK policy**: default `NO ACTION` (deferibile ove serve), `RESTRICT` dove non vogliamo cancellazioni con figli.
* **No partizionamento per tipi piccoli** (es. tipo indirizzo): preferire tabelle di lookup + indici composti.

---

## 🏗️ Modello Dati (nuovi schemi/tabelle)

### 📈 `crm`

* **`crm.opportunita`**
  `id, billing_account_id, istanza_utility_id?, stadio, valore, probabilita, referente_contatto_id?, owner_user, meta jsonb, data_*, user_*, tx_id, storicizza`
  *Uso*: pipeline commerciale; genera *preventivi*.

* **`crm.opportunita_prodotti`**
  `id, opportunita_id → crm.opportunita, articolo_id → catalogo.articoli, quantita, prezzo?, note, audit`

### 🛠️ `assistenza` (ticketing)

* **`assistenza.ticket`**
  `id, billing_account_id, istanza_utility_id, titolo, descrizione, priorita, stato, categoria, assegnato_a, sla_id?, meta jsonb, audit`

* **`assistenza.ticket_worklog`** (tempo)
  `id, ticket_id, data, inizio, fine, minuti, articolo_id(servizio), approvato bool, note, audit`

* **`assistenza.ticket_materiali`** (materiali)
  `id, ticket_id, data, articolo_id, quantita, approvato bool, note, audit`

> **FK chiave**: `ticket_*` → `ticket`; `*._account/istanza` coerenti con le tabelle *anagrafiche*.

---

## 🔗 Ponte verso Vendite

### `vendite.attivita_fatturabili` (esistente)

Aggiungere (se mancanti):

* `fonte_tipo VARCHAR(32)` → `TICKET_WORKLOG | TICKET_MATERIALE | MANUALE | ...`
* `fonte_id BIGINT NULL` → es. `ticket_id`
* `fonte_riga_id BIGINT NULL` → es. `ticket_worklog.id`
* **Unique parziale**: `UNIQUE (fonte_tipo, fonte_riga_id) WHERE fonte_riga_id IS NOT NULL`

> **Regola**: creare riga in `attivita_fatturabili` quando `worklog/materiale.approvato = true`.

---

## 🔄 Flussi principali

### 1) CRM → Preventivo → Contratto

1. **Opportunità** in stadio “Offerta” crea `vendite.preventivi` + `preventivi_righe` da `opportunita_prodotti`.
2. Accettazione → genera `vendite.contratti` + `contratti_righe` (prezzi, periodicità, regole).
   *Colonne utili*: `tipo_erogazione`, `periodicita`, `fonte_quantita_attesa`.

### 2) Ticketing → Attività Fatturabili → Fattura

1. Tecnico registra **worklog** e **materiali** sul ticket (con `articolo_id`).
2. Supervisor **approva** le righe.
3. Job o trigger crea righe in `vendite.attivita_fatturabili` con campi **fonte**\*.
4. Motore di fatturazione legge `attivita_fatturabili` (`approvato=true AND fatturato=false`) e genera **fatture** applicando:

   * `vendite.regole_fatturazione_articolo` (decimali, bundle, visibilità, arrotondamenti)
   * logica del **contratto** (prezzi/periodicità/competenza).

---

## ⚙️ Automazioni (pgAgent / trigger)

* **Job A**: *Import attività* (ogni 5–15 min)

  * Inserisce in `attivita_fatturabili` le righe `worklog/materiali` approvate **non ancora importate** (verifica unique parziale).
* **Job B**: *Fatturazione periodica* (mensile/settimanale)

  * Raggruppa per `billing_account_id`, applica regole, genera `fatture*`.
* **Trigger** (facoltativi):

  * On `ticket_*` `AFTER UPDATE` (campo `approvato` → true): upsert in `attivita_fatturabili`.
  * Guard‑rail su `attivita_fatturabili` per coerenza `billing_account_id/istanza_utility_id` (se presenti già nei tuoi trigger *guard*).

---

## 🧱 FK & Regole d’integrità

* **Default**: `NO ACTION` (deferibile se pipeline complessa).
* **RESTRICT**: su relazioni dove non vogliamo cancellazioni con figli (es. `ticket` con `worklog`/`materiali`).
* **CASCADE**: raro; solo su surrogate key stabili e se il business lo consente.

---

## 📦 Indici consigliati

* `assistenza.ticket_worklog(ticket_id, data)`
* `assistenza.ticket_materiali(ticket_id, data)`
* `vendite.attivita_fatturabili(billing_account_id, data_attivita)`
* `vendite.attivita_fatturabili(fonte_tipo, fonte_riga_id) WHERE fonte_riga_id IS NOT NULL`
* Per ricerche contract‑driven: `contratti_righe(contratto_id, articolo_id)`

---

## 🧰 Changelog Liquibase (estratti pronti)

**Bridge attivita\_fatturabili (campi fonte + unique parziale)**

```yaml
- changeSet:
    id: 20250830-bridge-attivita-fonte
    author: mctit
    preConditions:
      - onFail: CONTINUE
      - tableExists: { schemaName: vendite, tableName: attivita_fatturabili }
    changes:
      - addColumn:
          schemaName: vendite
          tableName: attivita_fatturabili
          columns:
            - column: { name: fonte_tipo, type: VARCHAR(32) }
            - column: { name: fonte_id, type: BIGINT }
            - column: { name: fonte_riga_id, type: BIGINT }
      - sql:
          splitStatements: false
          sql: |
            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname='vendite' AND indexname='uq_attivita_fonte_riga'
              ) THEN
                EXECUTE 'CREATE UNIQUE INDEX uq_attivita_fonte_riga
                           ON vendite.attivita_fatturabili (fonte_tipo, fonte_riga_id)
                         WHERE fonte_riga_id IS NOT NULL';
              END IF;
            END$$;
```

**Schemi `crm` e `assistenza` (placeholder sintetici)**

```yaml
- changeSet:
    id: 20250830-01-create-schema-crm-assistenza
    author: mctit
    changes:
      - sql:
          splitStatements: false
          sql: |
            CREATE SCHEMA IF NOT EXISTS crm;
            CREATE SCHEMA IF NOT EXISTS assistenza;
```

> Vedi allegato “Strutture tabelle” a fine documento per definizioni estese.

---

## 🧪 Esempio flusso end‑to‑end (pseudo‑SQL)

```sql
-- 1) Opportunità → Preventivo
INSERT INTO vendite.preventivi (...)
SELECT ... FROM crm.opportunita o WHERE o.id = :opp_id;

-- 2) Ticketing → Attività Fatturabili
INSERT INTO vendite.attivita_fatturabili (..., fonte_tipo, fonte_id, fonte_riga_id)
SELECT ..., 'TICKET_WORKLOG', w.ticket_id, w.id
  FROM assistenza.ticket_worklog w
 WHERE w.approvato = true
   AND NOT EXISTS (
         SELECT 1 FROM vendite.attivita_fatturabili a
          WHERE a.fonte_tipo='TICKET_WORKLOG' AND a.fonte_riga_id=w.id
       );

-- 3) Fatturazione (scheletro)
SELECT *
  FROM vendite.attivita_fatturabili a
 WHERE a.fatturato = false
 ORDER BY a.billing_account_id, a.data_attivita;
```

---

## 🔐 Sicurezza & Permessi

* Ruoli applicativi dedicati: `crm_rw`, `assistenza_rw`, `vendite_ops`.
* GRANT minimi per job pgAgent.
* Audit/tx\_id/storico: riusa i tuoi trigger `dbops.trgfn_tx_id_managed`, `script.trgfn_upd_audit_data_user_generic`, `script.trgfn_upd_dlt_storico_generic`.

---

## 🧭 Roadmap di adozione

1. Creare schemi `crm` e `assistenza` + tabelle minime.
2. Aggiungere campi **fonte** su `vendite.attivita_fatturabili` e unique parziale.
3. Job *Import attività* (pgAgent) + filtro `approvato`.
4. Allineare `contratti_righe` con regole di valorizzazione.
5. Attivare ciclo fatturazione.

---

## 📝 Glossario

* **BA**: Billing Account (conto di fatturazione).
* **Worklog**: registrazione del tempo lavorato su un ticket.
* **Attività fatturabile**: riga pronta alla generazione fattura.

---

## 📎 Allegato — Strutture tabelle (bozze estese)

**crm.opportunita**

```sql
CREATE TABLE IF NOT EXISTS crm.opportunita (
  id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  billing_account_id INT NOT NULL,
  istanza_utility_id INT,
  stadio VARCHAR(32) NOT NULL,
  valore NUMERIC(12,2),
  probabilita SMALLINT,
  referente_contatto_id INT,
  owner_user VARCHAR(80),
  meta JSONB NOT NULL DEFAULT '{}',
  data_insert timestamptz NOT NULL DEFAULT now(),
  user_insert varchar(80) NOT NULL DEFAULT CURRENT_USER,
  data_update timestamptz NOT NULL DEFAULT now(),
  user_update varchar(80) DEFAULT CURRENT_USER,
  tx_id uuid,
  storicizza boolean NOT NULL DEFAULT false
);
```

**assistenza.ticket**

```sql
CREATE TABLE IF NOT EXISTS assistenza.ticket (
  id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  billing_account_id INT NOT NULL,
  istanza_utility_id INT,
  titolo VARCHAR(200) NOT NULL,
  descrizione TEXT,
  priorita VARCHAR(16),
  stato VARCHAR(16) NOT NULL,
  categoria VARCHAR(32),
  assegnato_a VARCHAR(80),
  sla_id INT,
  meta JSONB NOT NULL DEFAULT '{}',
  data_insert timestamptz NOT NULL DEFAULT now(),
  user_insert varchar(80) NOT NULL DEFAULT CURRENT_USER,
  data_update timestamptz NOT NULL DEFAULT now(),
  user_update varchar(80) DEFAULT CURRENT_USER
);
```

**assistenza.ticket\_worklog**

```sql
CREATE TABLE IF NOT EXISTS assistenza.ticket_worklog (
  id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  ticket_id BIGINT NOT NULL REFERENCES assistenza.ticket(id) ON DELETE RESTRICT,
  data date NOT NULL,
  inizio timestamptz,
  fine timestamptz,
  minuti int NOT NULL CHECK (minuti > 0),
  articolo_id UUID NOT NULL REFERENCES catalogo.articoli(id),
  approvato boolean NOT NULL DEFAULT false,
  note varchar(250),
  data_insert timestamptz NOT NULL DEFAULT now(),
  user_insert varchar(80) NOT NULL DEFAULT CURRENT_USER,
  data_update timestamptz NOT NULL DEFAULT now(),
  user_update varchar(80) DEFAULT CURRENT_USER
);
```

**assistenza.ticket\_materiali**

```sql
CREATE TABLE IF NOT EXISTS assistenza.ticket_materiali (
  id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  ticket_id BIGINT NOT NULL REFERENCES assistenza.ticket(id) ON DELETE RESTRICT,
  data date NOT NULL,
  articolo_id UUID NOT NULL REFERENCES catalogo.articoli(id),
  quantita numeric(12,3) NOT NULL CHECK (quantita > 0),
  approvato boolean NOT NULL DEFAULT false,
  note varchar(250),
  data_insert timestamptz NOT NULL DEFAULT now(),
  user_insert varchar(80) NOT NULL DEFAULT CURRENT_USER,
  data_update timestamptz NOT NULL DEFAULT now(),
  user_update varchar(80) DEFAULT CURRENT_USER
);
```

---

> **Note**: Adattare nomi colonne/chiavi allineandosi alle convenzioni di Zero ERP (prefissi trigger/funzioni, `*_id`, audit, `tx_id`, `storicizza`, ecc.).
