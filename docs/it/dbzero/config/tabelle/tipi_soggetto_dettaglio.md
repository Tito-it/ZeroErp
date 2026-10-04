{% include-markdown "it/dbzero/config/manual/tipi_soggetto_dettaglio.md" %}
# 📚 Tabella `tipi_soggetto_dettaglio`

> 📝 **Descrizione**
>
> Tipologia dettagliata soggetto con formato CF e P.IVA per paese

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| tipo_soggetto_id | character varying(10) | NO |  |
| stato_iso2 | character varying(2) | NO |  |
| codice_interno | character varying(10) | NO |  |
| descrizione | character varying(100) | YES |  |
| formato_cf | character varying(20) | NO |  |
| formato_piva | character varying(20) | NO |  |
| user_insert | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| user_update | text | YES |  |
| data_update | timestamp with time zone | YES |  |
| stato_id | bigint | YES |  |
| dati_societari_policy | config.dati_societari_policy_enum | NO | 'NONE'::config.dati_societari_policy_enum |
| piva_obbligatoria | boolean | NO | false |
| cf_obbligatorio | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_tipi_soggetto_dettaglio_cf_obbl_vs_formato |  |
| CHECK | chk_tipi_soggetto_dettaglio_formato_cf |  |
| CHECK | chk_tipi_soggetto_dettaglio_formato_piva |  |
| CHECK | chk_tipi_soggetto_dettaglio_piva_obbl_vs_formato |  |
| CHECK | chk_tipi_soggetto_dettaglio_piva_vs_policy |  |
| FOREIGN KEY | fk_tipi_soggetto_dettaglio_stato_id | stato_id |
| FOREIGN KEY | fk_tipi_soggetto_dettaglio_tipi_soggetto_id | tipo_soggetto_id |
| PRIMARY KEY | pk_tipi_soggetto_dettaglio | id |
| UNIQUE | uq_tipi_soggetto_dettaglio_cod_int_tipo_soggetto | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_tipi_soggetto_dettaglio | `CREATE UNIQUE INDEX pk_tipi_soggetto_dettaglio ON config.tipi_soggetto_dettaglio USING btree (id)` |
| uq_tipi_soggetto_dettaglio_cod_int_tipo_soggetto | `CREATE UNIQUE INDEX uq_tipi_soggetto_dettaglio_cod_int_tipo_soggetto ON config.tipi_soggetto_dettaglio USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_soggetto_dettaglio_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_tipi_soggetto_dettaglio_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_tipi_soggetto_dettaglio_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_tipi_soggetto_dettaglio_sync_stato_iso2_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_sync_stato_iso2()` |
| trg_tipi_soggetto_dettaglio_sync_stato_iso2_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_sync_stato_iso2()` |

---
{% include-markdown "signature-core.md" %}
