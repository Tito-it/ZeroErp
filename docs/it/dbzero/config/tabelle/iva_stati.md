{% include-markdown "it/dbzero/config/manual/iva_stati.md" %}
# Tabella `iva_stati`

## Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| iva_id | integer | NO |  |
| stato_id | integer | NO |  |
| aliquota_override | numeric | NO |  |
| assoggettamento_override | character | NO |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | text | NO | CURRENT_USER |

## Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | 16601_19831_1_not_null |  |
| CHECK | 16601_19831_2_not_null |  |
| CHECK | 16601_19831_3_not_null |  |
| CHECK | 16601_19831_4_not_null |  |
| CHECK | 16601_19831_5_not_null |  |
| CHECK | 16601_19831_6_not_null |  |
| CHECK | 16601_19831_7_not_null |  |
| CHECK | 16601_19831_8_not_null |  |
| CHECK | chk_iva_stati_assoggettamento_override |  |
| FOREIGN KEY | fk_iva_stati_iva | iva_id |
| FOREIGN KEY | fk_iva_stati_stato | stato_id |
| PRIMARY KEY | pk_iva_stati | stato_id, iva_id |

## Indici
| Nome | Definizione |
|------|-------------|
| ix_iva_stati_stato | `CREATE INDEX ix_iva_stati_stato ON config.iva_stati USING btree (stato_id)` |
| pk_iva_stati | `CREATE UNIQUE INDEX pk_iva_stati ON config.iva_stati USING btree (iva_id, stato_id)` |

## Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_upd_iva_stati_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |