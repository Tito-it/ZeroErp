{% include-markdown "it/dbzero/config/manual/forme_giuridiche.md" %}
# 📚 Tabella `forme_giuridiche`

> 📝 **Descrizione**
>
> Dominio forme giuridiche per-paese. Policy REA e capitale sociale. (No SDI/PEC).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| stato_iso2 | character varying(2) | NO |  |
| stato_id | bigint | YES |  |
| codice | character varying(20) | NO |  |
| descrizione | character varying(150) | NO |  |
| rea_policy | text | NO | 'NONE'::text |
| capitale_sociale_policy | text | NO | 'NONE'::text |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| user_insert | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | YES |  |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_forme_giuridiche_capitale_sociale_policy |  |
| CHECK | chk_forme_giuridiche_rea_policy |  |
| FOREIGN KEY | fk_forme_giuridiche_stato_id | stato_id |
| PRIMARY KEY | pk_forme_giuridiche | id |
| UNIQUE | uq_forme_giuridiche_statoiso2_codice | stato_iso2, codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_config_forme_giuridiche_stato_id | `CREATE INDEX ix_config_forme_giuridiche_stato_id ON config.forme_giuridiche USING btree (stato_id)` |
| ix_forme_giuridiche_codice | `CREATE INDEX ix_forme_giuridiche_codice ON config.forme_giuridiche USING btree (codice)` |
| pk_forme_giuridiche | `CREATE UNIQUE INDEX pk_forme_giuridiche ON config.forme_giuridiche USING btree (id)` |
| uq_forme_giuridiche_statoiso2_codice | `CREATE UNIQUE INDEX uq_forme_giuridiche_statoiso2_codice ON config.forme_giuridiche USING btree (stato_iso2, codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_forme_giuridiche_a10_dati_societari_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'dati_societari', 'forma_giuridica_id', 'id', 'attivo')` |
| trg_forme_giuridiche_a10_forme_giuridiche_tipi_soggetto_2335ce | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'forme_giuridiche_tipi_soggetto_dettaglio', 'forma_giuridica_id', 'id', 'attivo')` |
| trg_forme_giuridiche_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_forme_giuridiche_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_forme_giuridiche_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_forme_giuridiche_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_forme_giuridiche_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_forme_giuridiche_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_forme_giuridiche_sync_stato_iso2_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_sync_stato_iso2()` |
| trg_forme_giuridiche_sync_stato_iso2_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_sync_stato_iso2()` |
| trg_forme_giuridiche_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('forme_giuridiche_id')` |
| trg_forme_giuridiche_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('forme_giuridiche_id')` |

---
{% include-markdown "signature-core.md" %}
