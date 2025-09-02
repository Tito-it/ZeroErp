# 📚 Tabella `preventivi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| numero_preventivo | character varying | NO |  |
| rev | integer | NO | 0 |
| is_revision_attiva | boolean | NO | false |
| stato | character varying | YES | 'BOZZA'::character varying |
| billing_account_id | integer | YES |  |
| istanza_utility_id | integer | YES |  |
| utility_id | integer | NO |  |
| validita_dal | date | YES |  |
| validita_al | date | YES |  |
| totale_imponibile | numeric | YES | 0 |
| totale_iva | numeric | YES | 0 |
| totale_documento | numeric | YES | 0 |
| valuta_id | integer | YES |  |
| note | text | YES |  |
| meta | jsonb | YES | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |
| competenza_mese | date | YES |  |
| fatturazione_immediata | boolean | YES | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_preventivi_competenza_mese_primo |  |
| CHECK | chk_preventivi_stato |  |
| CHECK | chk_preventivi_validita |  |
| FOREIGN KEY | fk_preventivi_billing_account | billing_account_id |
| FOREIGN KEY | fk_preventivi_istanza | istanza_utility_id |
| FOREIGN KEY | fk_preventivi_utility | utility_id |
| FOREIGN KEY | fk_preventivi_valuta | valuta_id |
| PRIMARY KEY | pk_preventivi | id |
| UNIQUE | uq_preventivi_numero_rev | numero_preventivo, rev |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_preventivi_numero | `CREATE INDEX ix_preventivi_numero ON vendite.preventivi USING btree (numero_preventivo)` |
| ix_preventivi_stato | `CREATE INDEX ix_preventivi_stato ON vendite.preventivi USING btree (stato)` |
| pk_preventivi | `CREATE UNIQUE INDEX pk_preventivi ON vendite.preventivi USING btree (id)` |
| uq_preventivi_numero_rev | `CREATE UNIQUE INDEX uq_preventivi_numero_rev ON vendite.preventivi USING btree (numero_preventivo, rev)` |
| ux_preventivi_numero_attiva | `CREATE UNIQUE INDEX ux_preventivi_numero_attiva ON vendite.preventivi USING btree (numero_preventivo) WHERE (is_revision_attiva = true)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_preventivi_ins_upd_norm | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_preventivi_norm()` |
| trg_preventivi_ins_upd_norm | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_preventivi_norm()` |
| trg_upd_preventivi_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
