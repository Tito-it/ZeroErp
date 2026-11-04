{% include-markdown "it/dbzero/config/manual/registri_giornale.md" %}
# 📚 Tabella `registri_giornale`

> 📝 **Descrizione**
>
> Catalogo dei REGISTRI che script.vw_giornale_entita cuce: una riga per ramo UNION ALL della vista (EVENT_LOG, LOTTO_LOG, TASK_RUN, FATTURA_LOG). E' la sede del vocabolario che la vista emette in `registro`, che il backend valida nel filtro e che il frontend mostra nella tendina — fino al 2026-09-19 tre copie che non si conoscevano, e nessuna con l'etichetta. ⛔ La vista NON fa JOIN qui: il registro resta un letterale nel ramo (e' l'identita' del ramo) e il catalogo lo DESCRIVE. Il legame lo tiene il pgTAP test-giornale-registri-catalogo-v1 nei due versi: ogni letterale della vista e' a catalogo e vivo, ogni riga viva ha il suo ramo. ⇒ Una riga NON si aggiunge dall'applicazione: nasce col ramo, nel CSV del seed. ⛔ Senza colonna attivo, come tipi_entita ed eventi_dominio: un registro non si assegna a niente e le righe vecchie del diario restano leggibili; il ritiro di un ramo e' obsoleto_dal. Stessa forma del lookup generico (dbops.fn_get_lookup_codici). Brief: brief-db-registri-giornale-catalogo, sezione 4.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | text | NO |  |
| codice | text | NO |  |
| descrizione | text | NO |  |
| etichetta_key | text | NO |  |
| sorgente | text | NO |  |
| obsoleto_dal | date | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_registri_giornale_codice_interno_forma |  |
| CHECK | chk_registri_giornale_codice_non_vuoto |  |
| CHECK | chk_registri_giornale_etichetta_key_namespace |  |
| CHECK | chk_registri_giornale_sorgente_qualificata |  |
| PRIMARY KEY | pk_registri_giornale | id |
| UNIQUE | uq_registri_giornale_codice | codice |
| UNIQUE | uq_registri_giornale_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_registri_giornale | `CREATE UNIQUE INDEX pk_registri_giornale ON config.registri_giornale USING btree (id)` |
| uq_registri_giornale_codice | `CREATE UNIQUE INDEX uq_registri_giornale_codice ON config.registri_giornale USING btree (codice)` |
| uq_registri_giornale_codice_interno | `CREATE UNIQUE INDEX uq_registri_giornale_codice_interno ON config.registri_giornale USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_registri_giornale_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_registri_giornale_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_registri_giornale_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_registri_giornale_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_registri_giornale_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
