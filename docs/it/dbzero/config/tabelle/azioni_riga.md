{% include-markdown "it/dbzero/config/manual/azioni_riga.md" %}
# 📚 Tabella `azioni_riga`

> 📝 **Descrizione**
>
> Registro delle AZIONI DI RIGA (D-N1, F-5): per ogni azione che un pulsante esegue su una riga di elenco, la superficie che il frontend legge (superficie, una vista con una riga per riga dell'elenco), le due colonne che dicono perche' il pulsante e' spento (colonna_motivo, il testo; colonna_motivo_chiave, la chiave i18n; NULL = azione viva), la fn_check pura che calcola i motivi e il verbo che rifiuta sollevando il primo (linee guida SQL §12.5). Il presidio db/pgtap/config/test-azioni-riga-registro-v1 verifica che superficie, colonne, fn_check e verbo esistano, che la vista dipenda dalla fn_check e che il verbo la chiami: tooltip ed errore non possono dire due cose diverse. Il frontend legge le colonne dal registro (un BB del pulsante di riga). Seed dal CSV 80_data/sql/config/azioni_riga.csv. Brief: brief-modello-documento-vendita §15.10 (Q-F5 = vista DB, Tid 2026-10-27).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | text | NO |  |
| descrizione | character varying(200) | NO |  |
| superficie | text | NO |  |
| colonna_motivo | text | NO |  |
| colonna_motivo_chiave | text | NO |  |
| fn_check | text | NO |  |
| verbo | text | NO |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_azioni_riga_colonne_identificatori |  |
| CHECK | chk_azioni_riga_fn_check_qualificata |  |
| CHECK | chk_azioni_riga_superficie_qualificata |  |
| CHECK | chk_azioni_riga_verbo_qualificato |  |
| PRIMARY KEY | pk_azioni_riga | id |
| UNIQUE | uq_azioni_riga_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_azioni_riga | `CREATE UNIQUE INDEX pk_azioni_riga ON config.azioni_riga USING btree (id)` |
| uq_azioni_riga_codice_interno | `CREATE UNIQUE INDEX uq_azioni_riga_codice_interno ON config.azioni_riga USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_azioni_riga_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_azioni_riga_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_azioni_riga_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
