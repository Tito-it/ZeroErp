# 📚 Tabella `conti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| iban | character varying | NO |  |
| bic_swift | character varying | YES |  |
| intestatario_predefinito | character varying | YES |  |
| paese | character | YES |  |
| banca_nome | character varying | YES |  |
| attivo | boolean | NO | true |
| verificato | boolean | NO | false |
| meta | jsonb | YES | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_conti_bic_fmt |  |
| CHECK | chk_conti_iban_fmt |  |
| CHECK | chk_conti_paese_fmt |  |
| PRIMARY KEY | pk_conti | id |
| UNIQUE | uq_conti_iban | iban |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_conti | `CREATE UNIQUE INDEX pk_conti ON anagrafiche.conti USING btree (id)` |
| uq_conti_iban | `CREATE UNIQUE INDEX uq_conti_iban ON anagrafiche.conti USING btree (iban)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_conti_ins_upd_normalize | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_conti_ins_upd_normalize()` |
| trg_conti_ins_upd_normalize | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_conti_ins_upd_normalize()` |

---
{% include-markdown "signature-core.md" %}
