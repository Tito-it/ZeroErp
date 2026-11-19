{% include-markdown "it/dbzero/dbops/manual/automazione_seed_primo_impianto.md" %}
# 📚 Tabella `automazione_seed_primo_impianto`

> 📝 **Descrizione**
>
> Le tabelle iscritte alla regola del seed di primo impianto: il CSV crea la riga, e dopo che l'installazione l'ha modificata la riga e' sua (linee-guida-sql §11.7). Una riga per tabella; il runner dbops.fn_run_automations_seed_primo_impianto monta script.trgfn_seed_primo_impianto dove la riga e' accesa, lo rigenera se diverge, lo toglie se la riga e' spenta. Tre forme: per riga (i due elenchi NULL, il default), per colonna (i due elenchi, per le righe miste), solo inserimento (per riga, e ogni riga di seed conta come personalizzata). Lo scrive solo la migrazione, dal CSV. ⚠️ Una tabella entra in un rilascio PRECEDENTE al primo ritocco del suo CSV: il trigger nasce dopo 80_data.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| schema_name | text | NO |  |
| table_name | text | NO |  |
| solo_inserimento | boolean | NO | false |
| colonne_software | text[] | YES |  |
| colonne_installazione | text[] | YES |  |
| enabled | boolean | NO | true |
| trigger_name | text | YES |  |
| motivo | text | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_automazione_seed_primo_impianto_elenchi |  |
| CHECK | chk_automazione_seed_primo_impianto_motivo |  |
| CHECK | chk_automazione_seed_primo_impianto_nome_tabella |  |
| CHECK | chk_automazione_seed_primo_impianto_solo_inserimento_per_riga |  |
| CHECK | chk_automazione_seed_primo_impianto_trigger_name |  |
| PRIMARY KEY | pk_automazione_seed_primo_impianto | id |
| UNIQUE | uq_automazione_seed_primo_impianto_tabella | schema_name, table_name |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_automazione_seed_primo_impianto | `CREATE UNIQUE INDEX pk_automazione_seed_primo_impianto ON dbops.automazione_seed_primo_impianto USING btree (id)` |
| uq_automazione_seed_primo_impianto_tabella | `CREATE UNIQUE INDEX uq_automazione_seed_primo_impianto_tabella ON dbops.automazione_seed_primo_impianto USING btree (schema_name, table_name)` |

---
{% include-markdown "signature-core.md" %}
