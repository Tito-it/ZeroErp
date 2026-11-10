# 📚 Tabella `tipi_entita`

> 📝 **Descrizione**
>
> Catalogo di «che cosa e' questa entita'», condiviso dal perimetro del giornale (vendite.event_log.entity_type), dal bersaglio degli errori e dalle note. Senza colonna attivo, per scelta: una FK verso un padre con attivo farebbe generare a dbops.fn_run_automations_attivo un lucchetto require, e il giornale smetterebbe di scrivere per una voce di elenco disattivata; la deprecazione si fa con obsoleto_dal. Il tipo di un documento ha un nome solo, il codice_interno di config.sorgenti: un'entita' che e' anche una sorgente lo dichiara (is_sorgente) e fk_tipi_entita_sorgenti lega il codice; le altre (LOTTO, TASK_RUN, FLUSSO, ARTICOLO, ...) stanno solo qui. Da quale tabella vengono le righe di un tipo lo dice tabella, o config.sorgenti.target_table per un tipo sorgente.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| codice | text | NO |  |
| etichetta_key | text | NO |  |
| modo_risoluzione_emittente | text | YES |  |
| obsoleto_dal | date | YES |  |
| note | text | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| key_selector | text | NO |  |
| is_sorgente | boolean | NO | false |
| sorgente_codice_interno | text | YES |  |
| tabella | text | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_tipi_entita_key_selector |  |
| CHECK | chk_tipi_entita_modo |  |
| CHECK | chk_tipi_entita_tabella_forma |  |
| CHECK | chk_tipi_entita_tabella_non_sorgente |  |
| FOREIGN KEY | fk_tipi_entita_sorgenti | sorgente_codice_interno |
| PRIMARY KEY | pk_tipi_entita | codice |
| UNIQUE | uq_tipi_entita_tabella | tabella |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_tipi_entita | `CREATE UNIQUE INDEX pk_tipi_entita ON config.tipi_entita USING btree (codice)` |
| uq_tipi_entita_tabella | `CREATE UNIQUE INDEX uq_tipi_entita_tabella ON config.tipi_entita USING btree (tabella)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_entita_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_tipi_entita_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_tipi_entita_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_tipi_entita_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
