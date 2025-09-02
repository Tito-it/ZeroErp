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
      id: 20250902-10-create-vendite-ordini
      author: mctit
      preConditions:
        - onFail: HALT
        - schemaExists: { schemaName: vendite }
      changes:
        - createTable:
            schemaName: vendite
            tableName: ordini
            remarks: "Ordini di vendita (testata) con campi già utili alla futura emissione di DDT."
            columns:
              - column: { name: id, type: BIGINT, autoIncrement: true, generationType: BY DEFAULT, constraints: { primaryKey: true, primaryKeyName: pk_ordini, nullable: false }, remarks: "PK" }
              - addColumn:
                  schemaName: vendite
                  tableName: ordini
                  columns:
                    - column:
                        name: uid
                        type: UUID
                        remarks: "Identificatore esterno stabile (esposizione API / integrazioni)."
              - column: { name: soggetto_ruolo_id, type: BIGINT, constraints: { nullable: false }, remarks: "FK → cliente/ruolo (anagrafiche.soggetti_ruoli)" }
              - column: { name: billing_account_id, type: INTEGER, remarks: "FK → account di fatturazione (opzionale)" }
              - column: { name: serie, type: VARCHAR(8), remarks: "Serie documento" }
              - column: { name: numero, type: VARCHAR(20), remarks: "Numero documento" }
              - column: { name: anno, type: SMALLINT, remarks: "Anno documento" }
              - column: { name: data, type: DATE, defaultValueComputed: CURRENT_DATE, constraints: { nullable: false }, remarks: "Data ordine" }
              - column: { name: stato, type: VARCHAR(16), defaultValue: "DRAFT", constraints: { nullable: false }, remarks: "Stato documento: DRAFT|CONFIRMED|ALLOCATED|SHIPPED|DELIVERED|CANCELLED|INVOICED" }
              - column: { name: source_tipo, type: VARCHAR(32), remarks: "Origine import (tipo)" }
              - column: { name: source_id, type: UUID, remarks: "Origine import (id)" }
              - column: { name: valuta_id, type: INTEGER, remarks: "FK → config.valute" }
              - column: { name: tasso_cambio, type: NUMERIC("18,8"), defaultValueNumeric: 1, constraints: { nullable: false }, remarks: "Tasso di cambio" }
              - column: { name: modalita_pagamento_id, type: INTEGER, remarks: "FK → config.modalita_pagamento" }
              - column: { name: giorni_pagamento, type: SMALLINT, remarks: "Giorni pagamento" }
              - column: { name: fine_mese, type: BOOLEAN, remarks: "Pagamento fine mese" }
              - column: { name: indirizzo_fatt_id, type: INTEGER, remarks: "FK → indirizzo fatturazione" }
              - column: { name: indirizzo_fatt_snapshot, type: JSONB, defaultValue: "{}", remarks: "Snapshot indirizzo fatturazione" }
              - column: { name: indirizzo_cons_id, type: INTEGER, remarks: "FK → indirizzo consegna" }
              - column: { name: indirizzo_cons_snapshot, type: JSONB, defaultValue: "{}", remarks: "Snapshot indirizzo consegna" }
              - column: { name: causale_trasporto, type: VARCHAR(40), remarks: "Causale trasporto (DDT)" }
              - column: { name: aspetto_beni, type: VARCHAR(40), remarks: "Aspetto beni (DDT)" }
              - column: { name: vettore_soggetto_ruolo_id, type: BIGINT, remarks: "FK → vettore come ruolo anagrafico" }
              - column: { name: num_colli, type: INTEGER, remarks: "Numero colli" }
              - column: { name: peso_lordo, type: NUMERIC("18,3"), remarks: "Peso lordo" }
              - column: { name: peso_netto, type: NUMERIC("18,3"), remarks: "Peso netto" }
              - column: { name: volume, type: NUMERIC("18,3"), remarks: "Volume" }
              - column: { name: porto, type: VARCHAR(16), remarks: "FRANCO|ASSEGNATO (per DDT/fattura differita)" }
              - column: { name: targa, type: VARCHAR(20), remarks: "Targa veicolo" }
              - column: { name: data_ora_partenza, type: TIMESTAMPTZ, remarks: "Data/ora partenza" }
              - column: { name: data_ora_consegna_prev, type: TIMESTAMPTZ, remarks: "Data/ora consegna prevista" }
              - column: { name: imponibile_tot, type: NUMERIC("18,6"), remarks: "Totale imponibile" }
              - column: { name: sconto_tot, type: NUMERIC("18,6"), remarks: "Totale sconto" }
              - column: { name: iva_tot, type: NUMERIC("18,6"), remarks: "Totale IVA" }
              - column: { name: totale_doc, type: NUMERIC("18,6"), remarks: "Totale documento" }
              - column: { name: note, type: TEXT, remarks: "Note documento" }
              - column: { name: meta, type: JSONB, defaultValue: "{}", remarks: "Estensioni JSON" }
              - column: { name: tx_id, type: UUID, remarks: "Id transazione" }
              - column: { name: storicizza, type: BOOLEAN, defaultValueBoolean: true, constraints: { nullable: false }, remarks: "Snapshot su UPDATE/DELETE" }
              - column: { name: data_insert, type: TIMESTAMPTZ, defaultValueComputed: now(), constraints: { nullable: false }, remarks: "Audit: data inserimento" }
              - column: { name: user_insert, type: VARCHAR(80), defaultValueComputed: CURRENT_USER, constraints: { nullable: false }, remarks: "Audit: utente inserimento" }
              - column: { name: data_update, type: TIMESTAMPTZ, defaultValueComputed: now(), constraints: { nullable: false }, remarks: "Audit: data aggiornamento" }
              - column: { name: user_update, type: VARCHAR(80), defaultValueComputed: CURRENT_USER, remarks: "Audit: utente aggiornamento" }

        # Foreign keys
        - addForeignKeyConstraint:
            baseTableSchemaName: vendite
            baseTableName: ordini
            baseColumnNames: soggetto_ruolo_id
            constraintName: fk_ordini_v_cliente_ruolo
            referencedTableSchemaName: anagrafiche
            referencedTableName: soggetti_ruoli
            referencedColumnNames: id
            onUpdate: CASCADE
            onDelete: NO ACTION

        - addForeignKeyConstraint:
            baseTableSchemaName: vendite
            baseTableName: ordini
            baseColumnNames: billing_account_id
            constraintName: fk_ordini_v_billing_account
            referencedTableSchemaName: anagrafiche
            referencedTableName: billing_account
            referencedColumnNames: id
            onUpdate: CASCADE
            onDelete: NO ACTION

        - addForeignKeyConstraint:
            baseTableSchemaName: vendite
            baseTableName: ordini
            baseColumnNames: valuta_id
            constraintName: fk_ordini_v_valute
            referencedTableSchemaName: config
            referencedTableName: valute
            referencedColumnNames: id
            onUpdate: CASCADE
            onDelete: NO ACTION

        - addForeignKeyConstraint:
            baseTableSchemaName: vendite
            baseTableName: ordini
            baseColumnNames: modalita_pagamento_id
            constraintName: fk_ordini_v_modpag
            referencedTableSchemaName: config
            referencedTableName: modalita_pagamento
            referencedColumnNames: id
            onUpdate: CASCADE
            onDelete: NO ACTION

        - addForeignKeyConstraint:
            baseTableSchemaName: vendite
            baseTableName: ordini
            baseColumnNames: indirizzo_fatt_id
            constraintName: fk_ordini_v_indir_fatt
            referencedTableSchemaName: anagrafiche
            referencedTableName: indirizzi
            referencedColumnNames: id
            onUpdate: CASCADE
            onDelete: NO ACTION

        - addForeignKeyConstraint:
            baseTableSchemaName: vendite
            baseTableName: ordini
            baseColumnNames: indirizzo_cons_id
            constraintName: fk_ordini_v_indir_cons
            referencedTableSchemaName: anagrafiche
            referencedTableName: indirizzi
            referencedColumnNames: id
            onUpdate: CASCADE
            onDelete: NO ACTION

        - addForeignKeyConstraint:
            baseTableSchemaName: vendite
            baseTableName: ordini
            baseColumnNames: vettore_soggetto_ruolo_id
            constraintName: fk_ordini_v_vettore_ruolo
            referencedTableSchemaName: anagrafiche
            referencedTableName: soggetti_ruoli
            referencedColumnNames: id
            onUpdate: CASCADE
            onDelete: NO ACTION

        # Checks
        - addCheckConstraint:
            schemaName: vendite
            tableName: ordini
            constraintName: chk_ordini_v_stato
            checkConstraint: "stato IN ('DRAFT','CONFIRMED','ALLOCATED','SHIPPED','DELIVERED','CANCELLED','INVOICED')"

        - addCheckConstraint:
            schemaName: vendite
            tableName: ordini
            constraintName: chk_ordini_v_porto
            checkConstraint: "(porto IS NULL OR porto IN ('FRANCO','ASSEGNATO'))"

        - addCheckConstraint:
            schemaName: vendite
            tableName: ordini
            constraintName: chk_ordini_v_totali_nonneg
            checkConstraint: "((imponibile_tot IS NULL OR imponibile_tot >= 0) AND (sconto_tot IS NULL OR sconto_tot >= 0) AND (iva_tot IS NULL OR iva_tot >= 0) AND (totale_doc IS NULL OR totale_doc >= 0))"

        - sql:
            splitStatements: false
            sql: |
              COMMENT ON COLUMN vendite.ordini.uid
                IS 'Identificatore esterno (UUID). Default: gen_random_uuid().';
        # Default su gen_random_uuid() (pgcrypto); puoi cambiare in futuro a uuid v7
        - sql:
            splitStatements: false
            sql: |
              ALTER TABLE vendite.ordini
              ALTER COLUMN uid SET DEFAULT gen_random_uuid();

        - createIndex:
            schemaName: vendite
            tableName: ordini
            indexName: uq_ordini_v_uid
            unique: true
            columns:
              - column:
                  name: uid



        - sql:
            splitStatements: false
            sql: |
              -- Numerazione: unico per anno+serie+numero, permettendo bozza senza numero/serie
              DO $$
              BEGIN
                IF NOT EXISTS (
                  SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                  WHERE n.nspname='vendite' AND c.relname='uq_ordini_v_anno_serie_numero'
                ) THEN
                  CREATE UNIQUE INDEX uq_ordini_v_anno_serie_numero
                    ON vendite.ordini(anno, serie, numero)
                    WHERE numero IS NOT NULL;
                  COMMENT ON INDEX vendite.uq_ordini_v_anno_serie_numero IS 'Unicità numerazione (anno, serie, numero) per ordini numerati.';
                END IF;
              END$$;

              -- Idempotenza import testata
              DO $$
              BEGIN
                IF NOT EXISTS (
                  SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                  WHERE n.nspname='vendite' AND c.relname='uq_ordini_v_source'
                ) THEN
                  CREATE UNIQUE INDEX uq_ordini_v_source
                    ON vendite.ordini(source_tipo, source_id)
                    WHERE source_tipo IS NOT NULL;
                  COMMENT ON INDEX vendite.uq_ordini_v_source IS 'Idempotenza import (source_tipo, source_id).';
                END IF;
              END$$;

              -- Indici operativi
              CREATE INDEX IF NOT EXISTS ix_ordini_v_cliente_stato_data
                ON vendite.ordini (soggetto_ruolo_id, stato, data);
              CREATE INDEX IF NOT EXISTS ix_ordini_v_stato
                ON vendite.ordini (stato);

              
              -- Normalize: UPPER/trim su source_tipo
              CREATE OR REPLACE FUNCTION vendite.trgfn_ordini_v_norm_source()
              RETURNS trigger LANGUAGE plpgsql AS $$
              BEGIN
                IF NEW.source_tipo IS NOT NULL THEN
                  NEW.source_tipo := upper(btrim(NEW.source_tipo));
                END IF;
                RETURN NEW;
              END$$;

              DROP TRIGGER IF EXISTS trg_ordini_v_norm_source ON vendite.ordini;
              CREATE TRIGGER trg_ordini_v_norm_source
              BEFORE INSERT OR UPDATE ON vendite.ordini
              FOR EACH ROW EXECUTE FUNCTION vendite.trgfn_ordini_v_norm_source();

              -- Protect: dopo CONFIRMED, vieta cambiare numerazione e data
              CREATE OR REPLACE FUNCTION vendite.trgfn_a10_ordini_v_protect_num()
              RETURNS trigger LANGUAGE plpgsql AS $$
              BEGIN
                IF OLD.stato IN ('CONFIRMED','ALLOCATED','SHIPPED','DELIVERED','INVOICED','CANCELLED') THEN
                  IF NEW.numero IS DISTINCT FROM OLD.numero OR NEW.serie IS DISTINCT FROM OLD.serie OR NEW.anno IS DISTINCT FROM OLD.anno OR NEW.data IS DISTINCT FROM OLD.data THEN
                    PERFORM script.fn_log_and_raise_error('database', TG_NAME, 'E_NUMERAZIONE_IMMUTABILE',
                      jsonb_build_object('id', OLD.id, 'stato', OLD.stato), NULL::uuid, OLD.id::text);
                  END IF;
                END IF;
                RETURN NEW;
              END$$;

              DROP TRIGGER IF EXISTS trg_a10_ordini_v_protect_num ON vendite.ordini;
              CREATE TRIGGER trg_a10_ordini_v_protect_num
              BEFORE UPDATE ON vendite.ordini
              FOR EACH ROW EXECUTE FUNCTION vendite.trgfn_a10_ordini_v_protect_num();

# Metto un  tag fine modifiche
  - changeSet:
      id: 20250902-90-create-vendite-ordini
      author: mctit
      changes:
        - tagDatabase:
            tag: 20250902-10-create-vendite-ordini