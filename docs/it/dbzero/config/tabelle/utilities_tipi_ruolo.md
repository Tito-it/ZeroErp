{% include-markdown "it/dbzero/config/manual/utilities_tipi_ruolo.md" %}
# 📚 Tabella `utilities_tipi_ruolo`

> 📝 **Descrizione**
>
> La matrice delle utility ammesse per tipo di ruolo: una riga accesa e valida oggi ammette il tipo di ruolo per l'utility, e senza riga il tipo di ruolo non la tratta. La leggono script.fn_guard_utility_tipo_ruolo (le scritture delle tabelle del registro dbops.automazione_guard_utility_tipo_ruolo) e anagrafiche.fn_lookup_utilities_per_ba (la tendina delle utility di un billing account). Per l'emittente fiscale la riga non ha data di fine, e non esce dalla matrice finche' un'azienda gestisce l'utility (config.trgfn_utilities_tipi_ruolo_guard_uscita_ef). Seed di primo impianto per riga: il CSV crea le righe e le aggiorna finche' l'installazione non le modifica.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| utility_id | integer | NO |  |
| tipo_ruolo_id | integer | NO |  |
| attivo | boolean | NO | true |
| valido_dal | date | YES |  |
| valido_al | date | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| user_insert | text | NO | CURRENT_USER |
| user_update | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |
| storicizza | boolean | NO | false |
| validita | daterange | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_utilities_tipi_ruolo_validita |  |
| FOREIGN KEY | fk_utilities_tipi_ruolo_tipo_ruolo | tipo_ruolo_id |
| FOREIGN KEY | fk_utilities_tipi_ruolo_utility | utility_id |
| PRIMARY KEY | pk_utilities_tipi_ruolo | id |
| UNIQUE | uq_utilities_tipi_ruolo_utility_tipo_ruolo | utility_id, tipo_ruolo_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_utilities_tipi_ruolo_tipo_ruolo_id | `CREATE INDEX ix_utilities_tipi_ruolo_tipo_ruolo_id ON config.utilities_tipi_ruolo USING btree (tipo_ruolo_id)` |
| pk_utilities_tipi_ruolo | `CREATE UNIQUE INDEX pk_utilities_tipi_ruolo ON config.utilities_tipi_ruolo USING btree (id)` |
| uq_utilities_tipi_ruolo_utility_tipo_ruolo | `CREATE UNIQUE INDEX uq_utilities_tipi_ruolo_utility_tipo_ruolo ON config.utilities_tipi_ruolo USING btree (utility_id, tipo_ruolo_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_utilities_tipi_ruolo_a00_seed_primo_impianto_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_seed_primo_impianto('RIGA')` |
| trg_utilities_tipi_ruolo_a00_seed_primo_impianto_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_seed_primo_impianto('RIGA')` |
| trg_utilities_tipi_ruolo_a00_seed_primo_impianto_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_seed_primo_impianto('RIGA')` |
| trg_utilities_tipi_ruolo_a10_date_validita_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_utilities_tipi_ruolo_a10_date_validita_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_utilities_tipi_ruolo_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('tipo_ruolo_id', 'E_CODICE_NON_MODIFICABILE', 'utility_id', 'E_CODICE_NON_MODIFICABILE')` |
| trg_utilities_tipi_ruolo_a12_guard_uscita_ef_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_utilities_tipi_ruolo_guard_uscita_ef()` |
| trg_utilities_tipi_ruolo_a12_guard_uscita_ef_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION config.trgfn_utilities_tipi_ruolo_guard_uscita_ef()` |
| trg_utilities_tipi_ruolo_a12_guard_uscita_ef_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION config.trgfn_utilities_tipi_ruolo_guard_uscita_ef()` |
| trg_utilities_tipi_ruolo_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_utilities_tipi_ruolo_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_utilities_tipi_ruolo_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('utilities_tipi_ruolo_id')` |
| trg_utilities_tipi_ruolo_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('utilities_tipi_ruolo_id')` |

---
{% include-markdown "signature-core.md" %}
