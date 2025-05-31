# Tabella `modalita_pagamento`

## Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('config.modalita_pagamento_id_seq'::regclass) |
| cod_modalita | character | NO |  |
| descrizione | character varying | NO |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | character varying | NO | CURRENT_USER |

## Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | 16601_19464_1_not_null |  |
| CHECK | 16601_19464_2_not_null |  |
| CHECK | 16601_19464_3_not_null |  |
| CHECK | 16601_19464_4_not_null |  |
| CHECK | 16601_19464_5_not_null |  |
| CHECK | 16601_19464_6_not_null |  |
| CHECK | 16601_19464_7_not_null |  |
| PRIMARY KEY | pk_modalita_pagamento | id |
| UNIQUE | uq_modalita_pagamento_cod | cod_modalita |

## Indici
| Nome | Definizione |
|------|-------------|
| pk_modalita_pagamento | `CREATE UNIQUE INDEX pk_modalita_pagamento ON config.modalita_pagamento USING btree (id)` |
| uq_modalita_pagamento_cod | `CREATE UNIQUE INDEX uq_modalita_pagamento_cod ON config.modalita_pagamento USING btree (cod_modalita)` |

## Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_upd_modalita_pagamento_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |