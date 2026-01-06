{% include-markdown "it/dbzero/anagrafiche/manual/risorse_umane.md" %}
# 📚 Tabella `risorse_umane`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| soggetto_ruolo_id | bigint | NO |  |
| qualifica_id | integer | NO |  |
| unita_organizzativa_id | integer | YES |  |
| valido_dal | date | NO |  |
| valido_al | date | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| soggetto_id | uuid | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_risorse_umane_date |  |
| FOREIGN KEY | fk_risorse_umane_qualifiche | qualifica_id |
| FOREIGN KEY | fk_risorse_umane_soggetti | soggetto_id |
| FOREIGN KEY | fk_risorse_umane_soggetti_ruoli | soggetto_ruolo_id |
| FOREIGN KEY | fk_risorse_umane_unita_organizzative | unita_organizzativa_id |
| PRIMARY KEY | pk_risorse_umane | id |
| UNIQUE | uq_risorse_umane_soggetto_ruolo | soggetto_ruolo_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_risorse_umane_qualifica_id | `CREATE INDEX ix_risorse_umane_qualifica_id ON anagrafiche.risorse_umane USING btree (qualifica_id)` |
| ix_risorse_umane_soggetto_id | `CREATE INDEX ix_risorse_umane_soggetto_id ON anagrafiche.risorse_umane USING btree (soggetto_id)` |
| ix_risorse_umane_unita_organizzativa_id | `CREATE INDEX ix_risorse_umane_unita_organizzativa_id ON anagrafiche.risorse_umane USING btree (unita_organizzativa_id)` |
| pk_risorse_umane | `CREATE UNIQUE INDEX pk_risorse_umane ON anagrafiche.risorse_umane USING btree (id)` |
| uq_risorse_umane_soggetto_ruolo | `CREATE UNIQUE INDEX uq_risorse_umane_soggetto_ruolo ON anagrafiche.risorse_umane USING btree (soggetto_ruolo_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_risorse_umane_a10_guard_ruolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_risorse_umane_guard_ruolo()` |
| trg_risorse_umane_a10_guard_ruolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_risorse_umane_guard_ruolo()` |

---
{% include-markdown "signature-core.md" %}
