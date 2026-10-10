{% include-markdown "it/dbzero/config/manual/email_allegato.md" %}
# 📚 Tabella `email_allegato`

> 📝 **Descrizione**
>
> Allegati email su filesystem. Associati a outbox (bozza) o log (storico invio). ON DELETE CASCADE su outbox.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| email_outbox_id | bigint | YES |  |
| email_log_id | bigint | YES |  |
| nome_file | character varying(255) | NO |  |
| mime_type | character varying(100) | NO |  |
| dimensione_bytes | bigint | NO |  |
| file_path | character varying(512) | NO |  |
| origine | character varying(20) | NO | 'UPLOAD'::character varying |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_email_allegato_dimensione |  |
| CHECK | chk_email_allegato_origine |  |
| FOREIGN KEY | email_allegato_email_log_id_fkey | email_log_id |
| FOREIGN KEY | email_allegato_email_outbox_id_fkey | email_outbox_id |
| PRIMARY KEY | email_allegato_pkey | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| email_allegato_pkey | `CREATE UNIQUE INDEX email_allegato_pkey ON config.email_allegato USING btree (id)` |
| ix_email_allegato_log_id | `CREATE INDEX ix_email_allegato_log_id ON config.email_allegato USING btree (email_log_id)` |
| ix_email_allegato_outbox_id | `CREATE INDEX ix_email_allegato_outbox_id ON config.email_allegato USING btree (email_outbox_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_email_allegato_a10_guard_solo_bozza_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION config.trgfn_email_allegato_guard_solo_bozza()` |
| trg_email_allegato_a10_guard_solo_bozza_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION config.trgfn_email_allegato_guard_solo_bozza()` |
| trg_email_allegato_a10_guard_solo_bozza_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_email_allegato_guard_solo_bozza()` |

---
{% include-markdown "signature-core.md" %}
