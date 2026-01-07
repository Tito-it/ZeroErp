{% include-markdown "it/dbzero/config/manual/forme_giuridiche_tipi_soggetto_dettaglio.md" %}
# 📚 Tabella `forme_giuridiche_tipi_soggetto_dettaglio`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| forma_giuridica_id | bigint | NO |  |
| tipo_soggetto_dettaglio_id | bigint | NO |  |
| attivo | boolean | NO | true |
| valido_dal | date | YES |  |
| valido_al | date | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| user_insert | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| user_update | text | YES |  |
| data_update | timestamp with time zone | YES |  |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_fg_tsd_validita |  |
| FOREIGN KEY | fk_fg_tsd_forma_giuridica | forma_giuridica_id |
| FOREIGN KEY | fk_fg_tsd_tipo_soggetto_dettaglio | tipo_soggetto_dettaglio_id |
| PRIMARY KEY | pk_forme_giuridiche_tsd | forma_giuridica_id, tipo_soggetto_dettaglio_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_fg_tsd_forma_giuridica_id | `CREATE INDEX ix_fg_tsd_forma_giuridica_id ON config.forme_giuridiche_tipi_soggetto_dettaglio USING btree (forma_giuridica_id)` |
| ix_fg_tsd_tipo_soggetto_dettaglio_id | `CREATE INDEX ix_fg_tsd_tipo_soggetto_dettaglio_id ON config.forme_giuridiche_tipi_soggetto_dettaglio USING btree (tipo_soggetto_dettaglio_id)` |
| pk_forme_giuridiche_tsd | `CREATE UNIQUE INDEX pk_forme_giuridiche_tsd ON config.forme_giuridiche_tipi_soggetto_dettaglio USING btree (forma_giuridica_id, tipo_soggetto_dettaglio_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_forme_giuridiche_tipi_soggetto_dettaglio_audit_data__eaaf9f | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_forme_giuridiche_tipi_soggetto_dettaglio_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_forme_giuridiche_tipi_soggetto_dettaglio_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
