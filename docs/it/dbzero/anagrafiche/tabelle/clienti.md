{% include-markdown "it/dbzero/anagrafiche/manual/clienti.md" %}
# 📚 Tabella `clienti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('anagrafiche.clienti_id_seq'::regclass) |
| soggetto_ruolo_id | integer | NO |  |
| istanza_utility_id | integer | NO |  |
| tipo_gg_scadenza_ft | character | NO | 'N'::bpchar |
| nr_giorni_scadenza | integer | NO | 0 |
| modalita_pagamento_id | integer | YES |  |
| cliente_pa | character | NO | 'N'::bpchar |
| codice_cig | character varying | YES |  |
| codice_cup | character varying | YES |  |
| cod_commessa | character varying | YES |  |
| split_payment | character | NO | 'N'::bpchar |
| cd_cliente_importato | character varying | YES |  |
| stato_cliente_id | integer | NO |  |
| iva_id | integer | NO |  |
| servizio_da_fatturare | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | NO | CURRENT_USER |
| utility_id | integer | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_clienti_pa |  |
| CHECK | chk_clienti_scadenza_logic |  |
| CHECK | chk_clienti_servizio_da_fatturare |  |
| CHECK | chk_clienti_split_payment |  |
| CHECK | chk_clienti_tipo_scadenza |  |
| FOREIGN KEY | fk_clienti_istanze_utilities | istanza_utility_id |
| FOREIGN KEY | fk_iva_config | iva_id |
| FOREIGN KEY | fk_modalita_pagamento_config | modalita_pagamento_id |
| FOREIGN KEY | fk_soggetti_ruoli_anagrafiche | soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id |
| FOREIGN KEY | fk_stati_cliente_config | stato_cliente_id |
| FOREIGN KEY | fk_utilities_config | utility_id, utility_id, utility_id, utility_id |
| PRIMARY KEY | pk_clienti | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_clienti_cd_importato | `CREATE INDEX ix_clienti_cd_importato ON anagrafiche.clienti USING btree (cd_cliente_importato)` |
| ix_clienti_iva_id | `CREATE INDEX ix_clienti_iva_id ON anagrafiche.clienti USING btree (iva_id)` |
| ix_clienti_modalita_pagamento_id | `CREATE INDEX ix_clienti_modalita_pagamento_id ON anagrafiche.clienti USING btree (modalita_pagamento_id)` |
| ix_clienti_soggetto_ruolo_id | `CREATE INDEX ix_clienti_soggetto_ruolo_id ON anagrafiche.clienti USING btree (soggetto_ruolo_id)` |
| ix_clienti_stato_cliente_id | `CREATE INDEX ix_clienti_stato_cliente_id ON anagrafiche.clienti USING btree (stato_cliente_id)` |
| ix_clienti_utility_id | `CREATE INDEX ix_clienti_utility_id ON anagrafiche.clienti USING btree (utility_id)` |
| pk_clienti | `CREATE UNIQUE INDEX pk_clienti ON anagrafiche.clienti USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_upd_clienti_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
---
{% include-markdown "signature-core.md" %}
