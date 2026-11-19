{% include-markdown "it/dbzero/dbops/manual/seed_righe.md" %}
# 📚 Tabella `seed_righe`

> 📝 **Descrizione**
>
> Le righe nate dal seed sulle tabelle iscritte al seed di primo impianto (dbops.automazione_seed_primo_impianto). La presenza della riga e' il segno «nata dal seed»: una riga di una tabella iscritta che qui non c'e' l'ha creata l'installazione, e il CSV non la riscrive mai. Una riga di seed non si cancella (si spegne) e, dopo che l'installazione l'ha personalizzata, il CSV non le riscrive piu' le colonne dell'installazione. La scrive solo script.trgfn_seed_primo_impianto (all'INSERT della sessione del migratore) e il runner dbops.fn_run_automations_seed_primo_impianto (all'iscrizione della tabella); l'app la legge soltanto. Il passaggio dalla porta di manutenzione si legge da dbops.porte_manutenzione_passaggi.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| schema_name | text | NO |  |
| table_name | text | NO |  |
| riga_id | text | NO |  |
| segnata_da | text | NO |  |
| personalizzata_il | timestamp with time zone | YES |  |
| personalizzata_da | text | YES |  |
| scartati | jsonb | YES |  |
| scartati_il | timestamp with time zone | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_seed_righe_nome_tabella |  |
| CHECK | chk_seed_righe_personalizzata |  |
| CHECK | chk_seed_righe_riga_id |  |
| CHECK | chk_seed_righe_scartati |  |
| CHECK | chk_seed_righe_segnata_da |  |
| PRIMARY KEY | pk_seed_righe | id |
| UNIQUE | uq_seed_righe_tabella_riga | schema_name, table_name, riga_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_seed_righe | `CREATE UNIQUE INDEX pk_seed_righe ON dbops.seed_righe USING btree (id)` |
| uq_seed_righe_tabella_riga | `CREATE UNIQUE INDEX uq_seed_righe_tabella_riga ON dbops.seed_righe USING btree (schema_name, table_name, riga_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_seed_righe_audit_data_user_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_seed_righe_audit_data_user_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_seed_righe_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_seed_righe_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
