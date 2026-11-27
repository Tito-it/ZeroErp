{% include-markdown "it/dbzero/anagrafiche/manual/emittenti_fiscali_utilities.md" %}
# 📚 Tabella `emittenti_fiscali_utilities`

> 📝 **Descrizione**
>
> Le utility che ciascuna azienda (emittente fiscale) gestisce: una riga per coppia azienda e utility, e la riga presente vuol dire che l'azienda la gestisce. L'utility dev'essere ammessa per l'emittente fiscale nella matrice config.utilities_tipi_ruolo, e finche' un'azienda la gestisce non ne esce (config.trgfn_utilities_tipi_ruolo_guard_uscita_ef). La riga non ha uno stato suo: attivo e' sempre true, e un'azienda che gestisce un'utility non si spegne finche' ha la sua riga. Sulla stessa riga i parametri d'importo dell'azienda per l'utility, tutti facoltativi: senza valore valgono la policy dell'emittente e quelli di sistema (anagrafiche.fn_parametri_importo_utility). Azienda e utility non si spostano.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| emittente_soggetto_ruolo_id | bigint | NO |  |
| utility_id | integer | NO |  |
| minimo_soglia_min | numeric(20,8) | YES |  |
| minimo_soglia_max | numeric(20,8) | YES |  |
| arrotondamento_importi_dec | smallint | YES |  |
| metodo_arrotondamento_importi | character varying | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_emittenti_fiscali_utilities_arrotondamento_dec |  |
| CHECK | chk_emittenti_fiscali_utilities_attivo |  |
| CHECK | chk_emittenti_fiscali_utilities_metodo_arrotondamento |  |
| CHECK | chk_emittenti_fiscali_utilities_minimo_soglia_max_finito |  |
| CHECK | chk_emittenti_fiscali_utilities_minimo_soglia_min_finito |  |
| CHECK | chk_emittenti_fiscali_utilities_soglie |  |
| CHECK | chk_emittenti_fiscali_utilities_soglie_coppia |  |
| FOREIGN KEY | fk_emittenti_fiscali_utilities_emittente | emittente_soggetto_ruolo_id |
| FOREIGN KEY | fk_emittenti_fiscali_utilities_utility | utility_id |
| PRIMARY KEY | pk_emittenti_fiscali_utilities | id |
| UNIQUE | uq_emittenti_fiscali_utilities_emittente_utility | emittente_soggetto_ruolo_id, utility_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_emittenti_fiscali_utilities | `CREATE UNIQUE INDEX pk_emittenti_fiscali_utilities ON anagrafiche.emittenti_fiscali_utilities USING btree (id)` |
| uq_emittenti_fiscali_utilities_emittente_utility | `CREATE UNIQUE INDEX uq_emittenti_fiscali_utilities_emittente_utility ON anagrafiche.emittenti_fiscali_utilities USING btree (emittente_soggetto_ruolo_id, utility_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_emittenti_fiscali_utilities_a10_emittenti_fiscali_re_62dfda | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_soggetto_ruolo_id', 'soggetto_ruolo_id')` |
| trg_emittenti_fiscali_utilities_a10_emittenti_fiscali_re_62dfda | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_soggetto_ruolo_id', 'soggetto_ruolo_id')` |
| trg_emittenti_fiscali_utilities_a10_guard_utility_tipo_r_cd07ac | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_utility_tipo_ruolo_by_cols('utility_id', 'emittente_soggetto_ruolo_id')` |
| trg_emittenti_fiscali_utilities_a10_guard_utility_tipo_r_cd07ac | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_utility_tipo_ruolo_by_cols('utility_id', 'emittente_soggetto_ruolo_id')` |
| trg_emittenti_fiscali_utilities_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('emittente_soggetto_ruolo_id', 'E_CODICE_NON_MODIFICABILE', 'utility_id', 'E_CODICE_NON_MODIFICABILE')` |
| trg_emittenti_fiscali_utilities_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_emittenti_fiscali_utilities_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
