# 📚 Tabella `causali`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| segno | smallint | NO | 0 |
| richiede_lotto | boolean | NO | false |
| richiede_seriale | boolean | NO | false |
| richiede_magazzino_dest | boolean | NO | false |
| abilita_billing | boolean | NO | false |
| impatto_valorizzazione | character varying | NO | 'cmp'::character varying |
| ordine | smallint | NO | 0 |
| attivo | boolean | NO | true |
| extra_info | jsonb | YES | '{}'::jsonb |
| tx_id | uuid | YES |  |
| user_insert | character varying | YES |  |
| user_update | character varying | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | YES |  |
| storicizza | boolean | NO | false |
| ambito_causale_id | bigint | YES |  |
| is_installazione_asset | boolean | NO | false |
| is_rettifica | boolean | NO | false |
| consente_stock_negativo | boolean | NO | false |
| richiede_odl | boolean | NO | false |
| contabilizza_cdc | boolean | NO | false |
| codice_interno | character varying | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_mag_causali_codice_interno_nonvuoto |  |
| CHECK | chk_magazzino_causali_imp_val |  |
| CHECK | chk_magazzino_causali_segno |  |
| FOREIGN KEY | fk_mag_causali_ambito | ambito_causale_id |
| PRIMARY KEY | pk_magazzino_causali | id |
| UNIQUE | uq_mag_causali_codice_interno | codice_interno |
| UNIQUE | uq_magazzino_causali_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_mag_causali_ambito_id | `CREATE INDEX ix_mag_causali_ambito_id ON magazzino.causali USING btree (ambito_causale_id)` |
| ix_magazzino_causali_attivo | `CREATE INDEX ix_magazzino_causali_attivo ON magazzino.causali USING btree (attivo)` |
| pk_magazzino_causali | `CREATE UNIQUE INDEX pk_magazzino_causali ON magazzino.causali USING btree (id)` |
| uq_mag_causali_codice_interno | `CREATE UNIQUE INDEX uq_mag_causali_codice_interno ON magazzino.causali USING btree (codice_interno)` |
| uq_magazzino_causali_codice | `CREATE UNIQUE INDEX uq_magazzino_causali_codice ON magazzino.causali USING btree (codice)` |

---
{% include-markdown "signature-core.md" %}
