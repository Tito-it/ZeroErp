# 📚 Tabella `tipi_entita`

> 📝 **Descrizione**
>
> Catalogo di «che cosa e' questa entita'», condiviso dal perimetro del giornale (vendite.event_log.entity_type), dal bersaglio degli errori e, col lotto 3 della grammatica unica, dalle note (G-7). ⛔ SENZA colonna attivo, e non e' una dimenticanza: una FK verso un padre con attivo fa generare a dbops.fn_run_automations_attivo un lucchetto require_attivo, e il diario smetterebbe di scrivere per una voce di elenco disattivata — la D-12 violata da un'automazione, alle 21:00. La deprecazione si fa con obsoleto_dal. ⭐ Rev 2026-10-19 (20261019-15, brief-db-grammatica-unica-documenti G-1): il tipo di documento ha UN nome, il codice_interno di config.sorgenti. Un'entita' che e' anche una sorgente lo dichiara (is_sorgente) e la FK fk_tipi_entita_sorgenti lega il codice; le entita' che non sono sorgenti (LOTTO, TASK_RUN, FLUSSO, ARTICOLO...) restano solo qui. Fino a questa revisione il commento diceva «non ci si aggancia»: era la scelta di prima, superata da G-1.

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

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_tipi_entita_key_selector |  |
| CHECK | chk_tipi_entita_modo |  |
| FOREIGN KEY | fk_tipi_entita_sorgenti | sorgente_codice_interno |
| PRIMARY KEY | pk_tipi_entita | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_tipi_entita | `CREATE UNIQUE INDEX pk_tipi_entita ON config.tipi_entita USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_entita_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_tipi_entita_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_tipi_entita_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_tipi_entita_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
