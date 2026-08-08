{% include-markdown "it/dbzero/vendite/manual/fatturazione_lotti_gruppi.md" %}
# 📚 Tabella `fatturazione_lotti_gruppi`

> 📝 **Descrizione**
>
> Perimetro di un lotto MIRATO: i gruppi fatturabili che quel lotto ha il permesso di lavorare (brief-db-emissione-fattura-per-documento-sorgente A2, decisione D-3). CONVENZIONE PORTANTE: nessuna riga per un lotto = NESSUNA restrizione = esattamente il comportamento odierno del giro schedulato (vincolo di retro-compatibilita', garanzia G1). Non esiste un flag "lotto mirato": l'assenza di criterio E' il criterio storico. Perche' una tabella e non un parametro di chiamata: gli step della pipeline ricevono solo lotto_id e ricostruiscono tutto dalla riga del lotto, quindi il perimetro DEVE essere persistito o non arriva agli step; in piu' i verbi Rerun/Avanza step del drawer ri-eseguono su un lotto esistente, e senza persistenza allargherebbero in silenzio il perimetro di un lotto mirato (garanzia G11). Scartato fatturazione_lotti.meta: e' gia' il canale di configurazione della pipeline, e il filtro serve dentro il SQL dinamico di fn_select_attivita_fatturabili. gruppo_key non e' una FK: e' una chiave di dominio calcolata da vendite.fn_build_gruppo_fatturabile_key. Popolata dal BE alla creazione del lotto, nella stessa transazione. rev 2026-07-27.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| lotto_id | bigint | NO |  |
| gruppo_key | text | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_fatturazione_lotti_gruppi_key_non_vuota |  |
| FOREIGN KEY | fk_fatturazione_lotti_gruppi_lotto | lotto_id |
| PRIMARY KEY | pk_fatturazione_lotti_gruppi | id |
| UNIQUE | uq_fatturazione_lotti_gruppi_lotto_key | lotto_id, gruppo_key |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_fatturazione_lotti_gruppi | `CREATE UNIQUE INDEX pk_fatturazione_lotti_gruppi ON vendite.fatturazione_lotti_gruppi USING btree (id)` |
| uq_fatturazione_lotti_gruppi_lotto_key | `CREATE UNIQUE INDEX uq_fatturazione_lotti_gruppi_lotto_key ON vendite.fatturazione_lotti_gruppi USING btree (lotto_id, gruppo_key)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fatturazione_lotti_gruppi_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatturazione_lotti_gruppi_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatturazione_lotti_gruppi_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatturazione_lotti_gruppi_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatturazione_lotti_gruppi_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('fatturazione_lotti_gruppi_id')` |
| trg_fatturazione_lotti_gruppi_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('fatturazione_lotti_gruppi_id')` |

---
{% include-markdown "signature-core.md" %}
