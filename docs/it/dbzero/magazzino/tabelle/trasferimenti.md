# 📚 Tabella `trasferimenti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | gen_random_uuid() |
| data | date | NO | CURRENT_DATE |
| stato_trasferimento | character varying | NO | 'DRAFT'::character varying |
| magazzino_id_from | bigint | NO |  |
| magazzino_id_to | bigint | NO |  |
| sorgenti_tipo_id | bigint | YES |  |
| sorgenti_uid | uuid | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_mag_trasferimenti_stato |  |
| FOREIGN KEY | fk_mag_rettifiche_sorgenti_tipo | sorgenti_tipo_id |
| FOREIGN KEY | fk_mag_trasferimenti_magazzino_from | magazzino_id_from |
| FOREIGN KEY | fk_mag_trasferimenti_magazzino_to | magazzino_id_to |
| FOREIGN KEY | fk_mag_trasferimenti_sorgenti_tipo | sorgenti_tipo_id |
| PRIMARY KEY | pk_mag_trasferimenti | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_mag_trasferimenti_data | `CREATE INDEX ix_mag_trasferimenti_data ON magazzino.trasferimenti USING btree (data)` |
| ix_mag_trasferimenti_from_to | `CREATE INDEX ix_mag_trasferimenti_from_to ON magazzino.trasferimenti USING btree (magazzino_id_from, magazzino_id_to)` |
| ix_mag_trasferimenti_stato | `CREATE INDEX ix_mag_trasferimenti_stato ON magazzino.trasferimenti USING btree (stato_trasferimento)` |
| pk_mag_trasferimenti | `CREATE UNIQUE INDEX pk_mag_trasferimenti ON magazzino.trasferimenti USING btree (id)` |
| uq_mag_trasferimenti_sorgenti_fk | `CREATE UNIQUE INDEX uq_mag_trasferimenti_sorgenti_fk ON magazzino.trasferimenti USING btree (sorgenti_tipo_id, sorgenti_uid) WHERE ((sorgenti_tipo_id IS NOT NULL) AND (sorgenti_uid IS NOT NULL))` |

---
{% include-markdown "signature-core.md" %}
