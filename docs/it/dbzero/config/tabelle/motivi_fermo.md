{% include-markdown "it/dbzero/config/manual/motivi_fermo.md" %}
# 📚 Tabella `motivi_fermo`

> 📝 **Descrizione**
>
> Vocabolario dei motivi di fermo della dashboard fatturazione (due lenti). Una riga per codice motivo_fermo emesso dai resolver vw_dash_fatturazione_* con la sua classe di azionabilita' (FISIOLOGICO=verde nessuna azione, RECUPERABILE=arancio lavoro interno, ANOMALIA=rosso da rivedere, SOLLECITO_CLIENTE=blu palla al cliente). Consumata da vendite.vw_dash_backlog_documenti (LEFT JOIN fail-visible: motivo non mappato -&gt; classe ANOMALIA) e dal FE per colore/filtro. Nuovo codice = append al CSV seed + mappatura classe PRIMA di emetterlo da una vista (pgTAP di coerenza in test-vw-dash-backlog-v1.sql).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice_interno | character varying(50) | NO |  |
| codice | character varying(50) | NO |  |
| descrizione | text | NO |  |
| classe | character varying(30) | NO |  |
| azione | character varying(200) | YES |  |
| ordine | smallint | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_motivi_fermo_classe |  |
| PRIMARY KEY | pk_motivi_fermo | id |
| UNIQUE | uq_motivi_fermo_codice | codice |
| UNIQUE | uq_motivi_fermo_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_motivi_fermo | `CREATE UNIQUE INDEX pk_motivi_fermo ON config.motivi_fermo USING btree (id)` |
| uq_motivi_fermo_codice | `CREATE UNIQUE INDEX uq_motivi_fermo_codice ON config.motivi_fermo USING btree (codice)` |
| uq_motivi_fermo_codice_interno | `CREATE UNIQUE INDEX uq_motivi_fermo_codice_interno ON config.motivi_fermo USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_motivi_fermo_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_motivi_fermo_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_motivi_fermo_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_motivi_fermo_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_motivi_fermo_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
