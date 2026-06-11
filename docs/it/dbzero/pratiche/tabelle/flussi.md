{% include-markdown "it/dbzero/pratiche/manual/flussi.md" %}
# 📚 Tabella `flussi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| pratica_id | bigint | NO |  |
| template_flusso_id | integer | YES |  |
| stato_id | integer | NO |  |
| flusso_padre_id | bigint | YES |  |
| risorsa_umana_id | bigint | YES |  |
| unita_organizzativa_id | integer | YES |  |
| sequenza | integer | NO | 0 |
| esito | character varying | YES |  |
| note_esito | text | YES |  |
| data_scadenza | date | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| data_fine | timestamp with time zone | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_flussi_esito |  |
| FOREIGN KEY | fk_flussi_flusso_padre | flusso_padre_id |
| FOREIGN KEY | fk_flussi_pratica | pratica_id |
| FOREIGN KEY | fk_flussi_risorsa_umana | risorsa_umana_id |
| FOREIGN KEY | fk_flussi_stato | stato_id |
| FOREIGN KEY | fk_flussi_template_flusso | template_flusso_id |
| FOREIGN KEY | fk_flussi_unita_organizzativa | unita_organizzativa_id |
| PRIMARY KEY | pk_pratiche_flussi | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_pratiche_flussi | `CREATE UNIQUE INDEX pk_pratiche_flussi ON pratiche.flussi USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_flussi_a10_guard_esito_completato_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION pratiche.trgfn_flussi_guard_esito_completato()` |
| trg_flussi_a10_guard_esito_completato_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_flussi_guard_esito_completato()` |
| trg_flussi_a10_guard_prerequisiti_ins | BEFORE | INSERT | `EXECUTE FUNCTION pratiche.trgfn_flussi_guard_prerequisiti()` |
| trg_flussi_a10_guard_ripetibilita_ins | BEFORE | INSERT | `EXECUTE FUNCTION pratiche.trgfn_flussi_guard_ripetibilita()` |
| trg_flussi_a10_guard_transizione_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_flussi_guard_transizione()` |
| trg_flussi_z90_calcolo_tempo_completamento_upd | AFTER | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_flussi_calcolo_tempo_completamento()` |
| trg_flussi_z90_generazione_upd | AFTER | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_flussi_generazione()` |
| trg_flussi_z90_giornale_ins | AFTER | INSERT | `EXECUTE FUNCTION pratiche.trgfn_flussi_giornale_ins()` |
| trg_flussi_z90_giornale_stato_upd | AFTER | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_flussi_giornale_stato()` |

---
{% include-markdown "signature-core.md" %}
