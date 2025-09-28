# 📚 Tabella `ddt`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | gen_random_uuid() |
| anno | smallint | YES |  |
| serie | character varying | YES |  |
| numero | character varying | YES |  |
| data | date | NO | CURRENT_DATE |
| stato_doc_ddt_id | bigint | NO |  |
| mittente_soggetto_ruolo_id | bigint | YES |  |
| destinatario_soggetto_ruolo_id | bigint | NO |  |
| vettore_soggetto_ruolo_id | bigint | YES |  |
| causale_trasporto_id | bigint | YES |  |
| aspetto_bene_id | bigint | YES |  |
| modalita_addebito_trasporto_id | bigint | YES |  |
| num_colli | integer | YES |  |
| peso_lordo | numeric | YES |  |
| peso_netto | numeric | YES |  |
| volume | numeric | YES |  |
| targa | character varying | YES |  |
| autista | character varying | YES |  |
| data_ora_partenza | timestamp with time zone | YES |  |
| data_ora_consegna_prev | timestamp with time zone | YES |  |
| tracking_code | character varying | YES |  |
| ordine_id | bigint | YES |  |
| source_tipo_id | bigint | YES |  |
| source_id | uuid | YES |  |
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
| FOREIGN KEY | fk_ddt_v_aspetto_bene | aspetto_bene_id |
| FOREIGN KEY | fk_ddt_v_causale_trasporto | causale_trasporto_id |
| FOREIGN KEY | fk_ddt_v_mod_add_trasporto | modalita_addebito_trasporto_id |
| FOREIGN KEY | fk_ddt_v_source_tipo | source_tipo_id |
| FOREIGN KEY | fk_ddt_v_stato_ddt | stato_doc_ddt_id |
| FOREIGN KEY | fk_ddt_vendita_destinatario_ruolo | destinatario_soggetto_ruolo_id |
| FOREIGN KEY | fk_ddt_vendita_mittente_ruolo | mittente_soggetto_ruolo_id |
| FOREIGN KEY | fk_ddt_vendita_ordine | ordine_id |
| FOREIGN KEY | fk_ddt_vendita_vettore_ruolo | vettore_soggetto_ruolo_id |
| PRIMARY KEY | pk_ddtv | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ddt_vendita_dest_stato_data | `CREATE INDEX ix_ddt_vendita_dest_stato_data ON vendite.ddt USING btree (destinatario_soggetto_ruolo_id, stato_doc_ddt_id, data)` |
| ix_ddt_vendita_stato | `CREATE INDEX ix_ddt_vendita_stato ON vendite.ddt USING btree (stato_doc_ddt_id)` |
| pk_ddtv | `CREATE UNIQUE INDEX pk_ddtv ON vendite.ddt USING btree (id)` |
| uq_ddt_v_anno_serie_numero | `CREATE UNIQUE INDEX uq_ddt_v_anno_serie_numero ON vendite.ddt USING btree (anno, serie, numero) WHERE (numero IS NOT NULL)` |
| uq_ddt_v_source_fk | `CREATE UNIQUE INDEX uq_ddt_v_source_fk ON vendite.ddt USING btree (source_tipo_id, source_id) WHERE (source_tipo_id IS NOT NULL)` |
| uq_ddt_vendita_uid | `CREATE UNIQUE INDEX uq_ddt_vendita_uid ON vendite.ddt USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ddt_a10_upd_v_protect_num | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_a10_v_ddt_protect_num()` |

---
{% include-markdown "signature-core.md" %}
