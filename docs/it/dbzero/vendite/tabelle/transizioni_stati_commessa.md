{% include-markdown "it/dbzero/vendite/manual/transizioni_stati_commessa.md" %}
# 📚 Tabella `transizioni_stati_commessa`

> 📝 **Descrizione**
>
> Matrice transizioni ammesse tra stati commessa. Grafo per vendite.trgfn_commesse_guard_transizione (enforcement BEFORE UPDATE OF stato_commessa_id). Salti diretti BOZZA/APERTA-&gt; PRONTA_FATTURAZIONE per il percorso push (commessa nata confermata dal preventivo accettato). rev 2026-06-07.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| stato_da_id | bigint | NO |  |
| stato_a_id | bigint | NO |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| azione_processo_codename | character varying(100) | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | ck_transizioni_stati_comm_da_diverso_a |  |
| CHECK | ck_transizioni_stati_comm_meta_ui |  |
| CHECK | ck_transizioni_stati_commessa_meta_manuale_dichiarato |  |
| FOREIGN KEY | fk_transizioni_stati_commessa_azioni_processo | azione_processo_codename |
| FOREIGN KEY | fk_tsc_a | stato_a_id |
| FOREIGN KEY | fk_tsc_da | stato_da_id |
| PRIMARY KEY | pk_transizioni_stati_commessa | id |
| UNIQUE | uq_transizioni_stati_commessa | stato_da_id, stato_a_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_transizioni_stati_commessa | `CREATE UNIQUE INDEX pk_transizioni_stati_commessa ON vendite.transizioni_stati_commessa USING btree (id)` |
| uq_transizioni_stati_commessa | `CREATE UNIQUE INDEX uq_transizioni_stati_commessa ON vendite.transizioni_stati_commessa USING btree (stato_da_id, stato_a_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_transizioni_stati_commessa_a10_stati_commessa_requir_22e024 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'stati_commessa', 'attivo', 'stato_a_id', 'id')` |
| trg_transizioni_stati_commessa_a10_stati_commessa_requir_22e024 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'stati_commessa', 'attivo', 'stato_a_id', 'id')` |
| trg_transizioni_stati_commessa_a10_stati_commessa_requir_97909d | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'stati_commessa', 'attivo', 'stato_da_id', 'id')` |
| trg_transizioni_stati_commessa_a10_stati_commessa_requir_97909d | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'stati_commessa', 'attivo', 'stato_da_id', 'id')` |
| trg_transizioni_stati_commessa_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_transizioni_stati_commessa_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
