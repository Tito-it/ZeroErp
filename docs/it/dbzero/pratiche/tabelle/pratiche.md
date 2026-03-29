{% include-markdown "it/dbzero/pratiche/manual/pratiche.md" %}
# 📚 Tabella `pratiche`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| emittente_fiscale_id | bigint | NO |  |
| tipo_prestazione_id | integer | NO |  |
| soggetto_id | uuid | YES |  |
| stato_id | integer | NO |  |
| priorita_id | integer | NO |  |
| risorsa_umana_id | bigint | YES |  |
| unita_organizzativa_id | integer | YES |  |
| pratica_padre_id | bigint | YES |  |
| flusso_origine_id | bigint | YES |  |
| canale_origine_id | integer | YES |  |
| codice | text | YES |  |
| descrizione | text | YES |  |
| data_scadenza | date | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| soggetto_ruolo_id | bigint | YES |  |
| istanza_utility_id | bigint | YES |  |
| data_apertura | date | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_pratiche_canale_origine | canale_origine_id |
| FOREIGN KEY | fk_pratiche_emittente_fiscale | emittente_fiscale_id |
| FOREIGN KEY | fk_pratiche_flusso_origine | flusso_origine_id |
| FOREIGN KEY | fk_pratiche_istanza_utility | istanza_utility_id |
| FOREIGN KEY | fk_pratiche_pratica_padre | pratica_padre_id |
| FOREIGN KEY | fk_pratiche_priorita | priorita_id |
| FOREIGN KEY | fk_pratiche_risorsa_umana | risorsa_umana_id |
| FOREIGN KEY | fk_pratiche_soggetto | soggetto_id |
| FOREIGN KEY | fk_pratiche_soggetto_ruolo | soggetto_ruolo_id |
| FOREIGN KEY | fk_pratiche_stato | stato_id |
| FOREIGN KEY | fk_pratiche_tipo_prestazione | tipo_prestazione_id |
| FOREIGN KEY | fk_pratiche_unita_organizzativa | unita_organizzativa_id |
| PRIMARY KEY | pk_pratiche_pratiche | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_pratiche_pratiche | `CREATE UNIQUE INDEX pk_pratiche_pratiche ON pratiche.pratiche USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_pratiche_a10_gen_codice_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_pratiche_gen_codice()` |
| trg_pratiche_a10_gen_codice_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION pratiche.trgfn_pratiche_gen_codice()` |
| trg_pratiche_a10_guard_contesto_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION pratiche.trgfn_pratiche_guard_contesto()` |
| trg_pratiche_a10_guard_contesto_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_pratiche_guard_contesto()` |
| trg_pratiche_a10_guard_transizione_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_pratiche_guard_transizione()` |
| trg_pratiche_m50_set_data_apertura_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_pratiche_set_data_apertura()` |
| trg_pratiche_z90_giornale_assegnazione_upd | AFTER | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_pratiche_giornale_assegnazione()` |
| trg_pratiche_z90_giornale_ins | AFTER | INSERT | `EXECUTE FUNCTION pratiche.trgfn_pratiche_giornale_ins()` |
| trg_pratiche_z90_giornale_priorita_upd | AFTER | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_pratiche_giornale_priorita()` |
| trg_pratiche_z90_giornale_stato_upd | AFTER | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_pratiche_giornale_stato()` |

---
{% include-markdown "signature-core.md" %}
