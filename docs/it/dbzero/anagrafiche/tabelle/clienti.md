# Tabella `clienti`

## Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('anagrafiche.clienti_id_seq'::regclass) |
| soggetto_ruolo_id | integer | NO |  |
| istanza_id | integer | YES |  |
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

## Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | 18368_19754_11_not_null |  |
| CHECK | 18368_19754_13_not_null |  |
| CHECK | 18368_19754_14_not_null |  |
| CHECK | 18368_19754_15_not_null |  |
| CHECK | 18368_19754_16_not_null |  |
| CHECK | 18368_19754_17_not_null |  |
| CHECK | 18368_19754_18_not_null |  |
| CHECK | 18368_19754_19_not_null |  |
| CHECK | 18368_19754_1_not_null |  |
| CHECK | 18368_19754_2_not_null |  |
| CHECK | 18368_19754_4_not_null |  |
| CHECK | 18368_19754_5_not_null |  |
| CHECK | 18368_19754_7_not_null |  |
| CHECK | chk_clienti_pa |  |
| CHECK | chk_clienti_scadenza_logic |  |
| CHECK | chk_clienti_servizio_da_fatturare |  |
| CHECK | chk_clienti_split_payment |  |
| CHECK | chk_clienti_tipo_scadenza |  |
| FOREIGN KEY | fk_istanze_utilities_anagrafiche | istanza_id, istanza_id |
| FOREIGN KEY | fk_iva_config | iva_id |
| FOREIGN KEY | fk_modalita_pagamento_config | modalita_pagamento_id |
| FOREIGN KEY | fk_soggetti_ruoli_anagrafiche | soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id |
| FOREIGN KEY | fk_stati_cliente_config | stato_cliente_id |
| FOREIGN KEY | fk_utilities_config | utility_id, utility_id, utility_id, utility_id |
| PRIMARY KEY | pk_clienti | id |

## Indici
| Nome | Definizione |
|------|-------------|
| ix_cliente_utility | `CREATE INDEX ix_cliente_utility ON anagrafiche.clienti USING btree (utility_id)` |
| ix_clienti_cd_importato | `CREATE INDEX ix_clienti_cd_importato ON anagrafiche.clienti USING btree (cd_cliente_importato)` |
| pk_clienti | `CREATE UNIQUE INDEX pk_clienti ON anagrafiche.clienti USING btree (id)` |

## Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_upd_clienti_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |