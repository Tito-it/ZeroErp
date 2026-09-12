{% include-markdown "it/dbzero/vendite/manual/fatturazione_lotti_gruppi.md" %}
# 📚 Tabella `fatturazione_lotti_gruppi`

> 📝 **Descrizione**
>
> Il PERIMETRO di un lotto: quali documenti quel lotto deve lavorare, una riga per documento. ⛔ La convenzione portante e' che NESSUNA RIGA significa NESSUNA RESTRIZIONE — cioe' il comportamento di un giro schedulato, che lavora tutto cio' che trova. Per questo qui non si scrivono righe «per completezza»: scriverle trasformerebbe un giro di massa in un giro mirato. ⭐ Dal 2026-09-07 questa tabella risponde a UNA domanda sola. Fino al giorno prima portava anche l'esito di ciascun documento, e le due cose divergevano proprio sui giri senza perimetro — dove non c'erano righe, quindi non c'era dove scrivere com'era andata. L'esito ora vive in vendite.fatturazione_lotti_esiti. Brief: brief-db-esito-gruppo-lotto §15.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| lotto_id | bigint | NO |  |
| gruppo_key | text | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_fatturazione_lotti_gruppi_key_non_vuota |  |
| FOREIGN KEY | fk_fatturazione_lotti_gruppi_lotto | lotto_id |
| PRIMARY KEY | pk_fatturazione_lotti_gruppi | id |
| UNIQUE | uq_fatturazione_lotti_gruppi_lotto_key | lotto_id, gruppo_key |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_fatturazione_lotti_gruppi | `CREATE UNIQUE INDEX pk_fatturazione_lotti_gruppi ON vendite.fatturazione_lotti_gruppi USING btree (id)` |
| uq_fatturazione_lotti_gruppi_lotto_key | `CREATE UNIQUE INDEX uq_fatturazione_lotti_gruppi_lotto_key ON vendite.fatturazione_lotti_gruppi USING btree (lotto_id, gruppo_key)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fatturazione_lotti_gruppi_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatturazione_lotti_gruppi_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatturazione_lotti_gruppi_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatturazione_lotti_gruppi_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatturazione_lotti_gruppi_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('fatturazione_lotti_gruppi_id')` |
| trg_fatturazione_lotti_gruppi_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('fatturazione_lotti_gruppi_id')` |

---
{% include-markdown "signature-core.md" %}
