# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025 Tid (Michele Carlo Titini) 
#
# Rilasciato sotto GNU GPLv3 o versione successiva.
# Vedi LICENSE.md per il testo completo della licenza.
# ------------------------------------------------------------

databaseChangeLog:
  - changeSet:
      id: 20250902-12-create-acquisti-ordini
      author: mctit
      preConditions:
        - onFail: HALT
      
      changes:
        - createTable:
            schemaName: acquisti
            tableName: ordini
            remarks: "Ordini di acquisto (testata) con campi già utili alla ricezione e DDT fornitore."
            columns:
              - column: { name: id, type: BIGINT, autoIncrement: true, generationType: BY DEFAULT, constraints: { primaryKey: true, primaryKeyName: pk_ordini_a, nullable: false }, remarks: "PK" }
            
              - column:
                  name: uid
                  type: UUID
                  remarks: "Identificatore esterno stabile (esposizione API / integrazioni)."
            
              - column: { name: soggetto_ruolo_id, type: BIGINT, constraints: { nullable: false }, remarks: "FK → fornitore/ruolo (anagrafiche.soggetti_ruoli)" }
              - column: { name: serie, type: VARCHAR(8), remarks: "Serie documento" }
              - column: { name: numero, type: VARCHAR(20), remarks: "Numero documento" }
              - column: { name: anno, type: SMALLINT, remarks: "Anno documento" }
              - column: { name: data, type: DATE, defaultValueComputed: CURRENT_DATE, constraints: { nullable: false }, remarks: "Data ordine" }
              - column: { name: stato, type: VARCHAR(16), defaultValue: "DRAFT", constraints: { nullable: false }, remarks: "Stato documento: DRAFT|SENT|CONFIRMED|RECEIVED|CANCELLED|INVOICED" }
              - column: { name: source_tipo, type: VARCHAR(32), remarks: "Origine import (tipo)" }
              - column: { name: source_id, type: UUID, remarks: "Origine import (id)" }
              - column: { name: valuta_id, type: INTEGER, remarks: "FK → config.valute" }
              - column: { name: tasso_cambio, type: NUMERIC(18,8), defaultValueNumeric: 1, constraints: { nullable: false }, remarks: "Tasso di cambio" }
              - column: { name: modalita_pagamento_id, type: INTEGER, remarks: "FK → config.modalita_pagamento" }
              - column: { name: giorni_pagamento, type: SMALLINT, remarks: "Giorni pagamento" }
              - column: { name: fine_mese, type: BOOLEAN, remarks: "Pagamento fine mese" }
              - column: { name: indirizzo_consegna_id, type: INTEGER, remarks: "FK → indirizzo consegna (magazzino)" }
              - column: { name: indirizzo_cons_snapshot, type: JSONB, defaultValue: "{}", constraints: { nullable: false }, remarks: "Snapshot indirizzo consegna" }
              - column: { name: causale_trasporto, type: VARCHAR(40), remarks: "Causale trasporto (DDT fornitore)" }
              - column: { name: aspetto_beni, type: VARCHAR(40), remarks: "Aspetto beni (DDT fornitore)" }
              - column: { name: num_colli, type: INTEGER, remarks: "Numero colli" }
              - column: { name: peso_lordo, type: NUMERIC(18,3), remarks: "Peso lordo" }
              - column: { name: peso_netto, type: NUMERIC(18,3), remarks: "Peso netto" }
              - column: { name: volume, type: NUMERIC(18,3), remarks: "Volume" }
              - column: { name: porto, type: VARCHAR(16), remarks: "FRANCO|ASSEGNATO (per DDT/ordini acquisto)" }
              - column: { name: data_ora_consegna_prev, type: TIMESTAMPTZ, remarks: "Data/ora consegna prevista" }
              - column: { name: imponibile_tot_atteso, type: NUMERIC(18,6), remarks: "Totale imponibile atteso" }
              - column: { name: sconto_tot_atteso, type: NUMERIC(18,6), remarks: "Totale sconto atteso" }
              - column: { name: iva_tot_atteso, type: NUMERIC(18,6), remarks: "Totale IVA atteso" }
              - column: { name: totale_doc_atteso, type: NUMERIC(18,6), remarks: "Totale documento atteso" }
              - column: { name: note, type: TEXT, remarks: "Note ordine" }
              - column: { name: meta, type: JSONB, defaultValue: "{}", constraints: { nullable: false }, remarks: "Estensioni JSON" }
              - column: { name: tx_id, type: UUID, remarks: "Id transazione" }
              - column: { name: storicizza, type: BOOLEAN, defaultValueBoolean: true, constraints: { nullable: false }, remarks: "Snapshot su UPDATE/DELETE" }
              - column: { name: data_insert, type: TIMESTAMPTZ, defaultValueComputed: now(), constraints: { nullable: false }, remarks: "Audit: data inserimento" }
              - column: { name: user_insert, type: VARCHAR(80), defaultValueComputed: CURRENT_USER, constraints: { nullable: false }, remarks: "Audit: utente inserimento" }
              - column: { name: data_update, type: TIMESTAMPTZ, defaultValueComputed: now(), constraints: { nullable: false }, remarks: "Audit: data aggiornamento" }
              - column: { name: user_update, type: VARCHAR(80), defaultValueComputed: CURRENT_USER, remarks: "Audit: utente aggiornamento" }

        # Foreign keys
        - addForeignKeyConstraint:
            baseTableSchemaName: acquisti
            baseTableName: ordini
            baseColumnNames: soggetto_ruolo_id
            constraintName: fk_ordini_a_fornitore_ruolo
            referencedTableSchemaName: anagrafiche
            referencedTableName: soggetti_ruoli
            referencedColumnNames: id
            onUpdate: CASCADE
            onDelete: NO ACTION

        - addForeignKeyConstraint:
            baseTableSchemaName: acquisti
            baseTableName: ordini
            baseColumnNames: valuta_id
            constraintName: fk_ordini_a_valute
            referencedTableSchemaName: config
            referencedTableName: valute
            referencedColumnNames: id
            onUpdate: CASCADE
            onDelete: NO ACTION

        - addForeignKeyConstraint:
            baseTableSchemaName: acquisti
            baseTableName: ordini
            baseColumnNames: modalita_pagamento_id
            constraintName: fk_ordini_a_modpag
            referencedTableSchemaName: config
            referencedTableName: modalita_pagamento
            referencedColumnNames: id
            onUpdate: CASCADE
            onDelete: NO ACTION

        - addForeignKeyConstraint:
            baseTableSchemaName: acquisti
            baseTableName: ordini
            baseColumnNames: indirizzo_consegna_id
            constraintName: fk_ordini_a_indir_cons
            referencedTableSchemaName: anagrafiche
            referencedTableName: indirizzi
            referencedColumnNames: id
            onUpdate: CASCADE
            onDelete: NO ACTION

        # Checks
        - addCheckConstraint:
            schemaName: acquisti
            tableName: ordini
            constraintName: chk_ordini_a_stato
            checkConstraint: "stato IN ('DRAFT','SENT','CONFIRMED','RECEIVED','CANCELLED','INVOICED')"

        - addCheckConstraint:
            schemaName: acquisti
            tableName: ordini
            constraintName: chk_ordini_a_porto
            checkConstraint: "(porto IS NULL OR porto IN ('FRANCO','ASSEGNATO'))"

        - addCheckConstraint:
            schemaName: acquisti
            tableName: ordini
            constraintName: chk_ordini_a_totali_nonneg
            checkConstraint: "((imponibile_tot_atteso IS NULL OR imponibile_tot_atteso >= 0) AND (sconto_tot_atteso IS NULL OR sconto_tot_atteso >= 0) AND (iva_tot_atteso IS NULL OR iva_tot_atteso >= 0) AND (totale_doc_atteso IS NULL OR totale_doc_atteso >= 0))"

        
        - sql:
            splitStatements: false
            sql: |
              COMMENT ON COLUMN acquisti.ordini.uid
                IS 'Identificatore esterno (UUID). Default: gen_random_uuid().';
        - sql:
            splitStatements: false
            sql: |
              ALTER TABLE acquisti.ordini
              ALTER COLUMN uid SET DEFAULT gen_random_uuid();
        - sql:
            splitStatements: false
            sql: |
              UPDATE acquisti.ordini
                 SET uid = gen_random_uuid()
               WHERE uid IS NULL;
        - createIndex:
            schemaName: acquisti
            tableName: ordini
            indexName: uq_ordini_a_uid
            unique: true
            columns:
              - column: { name: uid }
        
        - sql:
            splitStatements: false
            sql: |
              
              -- Numerazione: unico per anno+serie+numero
              DO $$
              BEGIN
                IF NOT EXISTS (
                  SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                  WHERE n.nspname='acquisti' AND c.relname='uq_ordini_a_anno_serie_numero'
                ) THEN
                  CREATE UNIQUE INDEX uq_ordini_a_anno_serie_numero
                    ON acquisti.ordini(anno, serie, numero)
                    WHERE numero IS NOT NULL;
                  COMMENT ON INDEX acquisti.uq_ordini_a_anno_serie_numero IS 'Unicità numerazione (anno, serie, numero) ordini di acquisto.';
                END IF;
              END$$;

              -- Idempotenza import testata
              DO $$
              BEGIN
                IF NOT EXISTS (
                  SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                  WHERE n.nspname='acquisti' AND c.relname='uq_ordini_a_source'
                ) THEN
                  CREATE UNIQUE INDEX uq_ordini_a_source
                    ON acquisti.ordini(source_tipo, source_id)
                    WHERE source_tipo IS NOT NULL;
                  COMMENT ON INDEX acquisti.uq_ordini_a_source IS 'Idempotenza import (source_tipo, source_id).';
                END IF;
              END$$;

              -- Indici operativi
              CREATE INDEX IF NOT EXISTS ix_ordini_a_fornitore_stato_data
                ON acquisti.ordini (soggetto_ruolo_id, stato, data);
              CREATE INDEX IF NOT EXISTS ix_ordini_a_stato
                ON acquisti.ordini (stato);

              
              -- Normalize source_tipo
              CREATE OR REPLACE FUNCTION acquisti.trgfn_ordini_a_norm_source()
              RETURNS trigger LANGUAGE plpgsql AS $$
              BEGIN
                IF NEW.source_tipo IS NOT NULL THEN
                  NEW.source_tipo := upper(btrim(NEW.source_tipo));
                END IF;
                RETURN NEW;
              END$$;

              DROP TRIGGER IF EXISTS trg_ordini_a_norm_source ON acquisti.ordini;
              CREATE TRIGGER trg_ordini_a_norm_source
              BEFORE INSERT OR UPDATE ON acquisti.ordini
              FOR EACH ROW EXECUTE FUNCTION acquisti.trgfn_ordini_a_norm_source();

              -- Protect: dopo CONFIRMED, vieta cambiare numerazione e data
              CREATE OR REPLACE FUNCTION acquisti.trgfn_a10_ordini_a_protect_num()
              RETURNS trigger LANGUAGE plpgsql AS $$
              BEGIN
                IF OLD.stato IN ('CONFIRMED','RECEIVED','INVOICED','CANCELLED','SENT') THEN
                  IF NEW.numero IS DISTINCT FROM OLD.numero OR NEW.serie IS DISTINCT FROM OLD.serie OR NEW.anno IS DISTINCT FROM OLD.anno OR NEW.data IS DISTINCT FROM OLD.data THEN
                    PERFORM script.fn_log_and_raise_error('database', TG_NAME, 'E_NUMERAZIONE_IMMUTABILE',
                      jsonb_build_object('id', OLD.id, 'stato', OLD.stato), NULL::uuid, OLD.id::text);
                  END IF;
                END IF;
                RETURN NEW;
              END$$;

              DROP TRIGGER IF EXISTS trg_a10_ordini_a_protect_num ON acquisti.ordini;
              CREATE TRIGGER trg_a10_ordini_a_protect_num
              BEFORE UPDATE ON acquisti.ordini
              FOR EACH ROW EXECUTE FUNCTION acquisti.trgfn_a10_ordini_a_protect_num();


# Metto un  tag fine modifiche
  - changeSet:
      id: 20250902-90-create-acquisti-ordini
      author: mctit
      changes:
        - tagDatabase:
            tag: 20250902-12-create-acquisti-ordini