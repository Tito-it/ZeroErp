{% include-markdown "it/dbzero/config/manual/lingue.md" %}
# 📚 Tabella `lingue`

> 📝 **Descrizione**
>
> Dominio centralizzato delle lingue (ISO 639-1 / 3166-1). Usato per messaggi, note e localizzazioni di sistema.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_iso | character varying(5) | NO |  |
| descrizione | text | NO |  |
| descrizione_locale | text | NO |  |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_cfg_lingue_codice_iso_len |  |
| PRIMARY KEY | pk_config_lingue | id |
| UNIQUE | uq_cfg_lingue_codice_iso | codice_iso |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_cfg_lingue_attivo | `CREATE INDEX ix_cfg_lingue_attivo ON config.lingue USING btree (attivo)` |
| pk_config_lingue | `CREATE UNIQUE INDEX pk_config_lingue ON config.lingue USING btree (id)` |
| uq_cfg_lingue_codice_iso | `CREATE UNIQUE INDEX uq_cfg_lingue_codice_iso ON config.lingue USING btree (codice_iso)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_lingue_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_lingue_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
