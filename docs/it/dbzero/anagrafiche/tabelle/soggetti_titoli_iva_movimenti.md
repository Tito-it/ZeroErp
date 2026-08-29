# 📚 Tabella `soggetti_titoli_iva_movimenti`

> 📝 **Descrizione**
>
> Il REGISTRO del consumo di plafond di un titolo IVA (D5 di brief-db-be-iva-risolutore-e-regime-cliente, approvata da Tid il 2026-08-27). Ogni fattura, ogni nota di credito e ogni forzatura manuale e' una riga; anagrafiche.soggetti_titoli_iva.imponibile_utilizzato e' la loro somma, mantenuta dal trigger dell'accumulatore. ⭐ Perche' un registro e non una colonna: P3 chiede un valore MEMORIZZATO — serve a poterlo ridurre a mano quando esistono fatturazioni fuori dal sistema — ma un numero memorizzato E forzabile diverge in silenzio da cio' che rappresenta, e su un plafond quel numero e' precisamente quello che l'Agenzia delle Entrate verifica. Col registro la forzatura ha un motivo, un autore e una data; il consumo e' algebrico senza casi speciali per la nota di credito (P4); e la riconciliazione col fatturato e' una query, non un'indagine. Non e' un pattern nuovo: vendite.resi_righe_riconsegne e le rettifiche di vw_partite_merce fanno gia' cosi'. ⚠️ Una FORZATURA non nomina nessuna fattura, ed e' il suo senso: registra cio' che il sistema NON ha fatturato. Senza il CHECK diventerebbe la scorciatoia per scrivere un consumo di fattura saltando anagrafiche.fn_consuma_plafond_titolo_iva, che e' l'unica a prendere il lock e a calcolare la spezzatura di P2. ⭐ La UNIQUE parziale e' la rete sotto al lock di D15-bis: il lock serializza due transizioni a DEFINITIVA in corsa, questa ferma la ripetizione a distanza di tempo. Sulle forzature non si applica, perche' due correzioni identiche nello stesso giorno possono essere due fatti distinti. ⚠️ data_movimento e' NOT NULL SENZA default: nessun now(), la data la porta chi scrive. Stesso vincolo di firma di D14 sul risolutore, e per la stessa ragione — il lotto puo' girare il giorno dopo. ⛔ Nessun ON DELETE CASCADE verso il titolo, al contrario degli AMBITI: un ambito e' una clausola, un movimento e' un fatto contabile. rev 2026-08-29.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| titolo_iva_id | bigint | NO |  |
| tipo_movimento | character varying | NO |  |
| imponibile | numeric | NO |  |
| data_movimento | date | NO |  |
| fattura_id | bigint | YES |  |
| fattura_riga_id | bigint | YES |  |
| motivo | character varying | YES |  |
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
| CHECK | chk_stiva_movimenti_documento |  |
| CHECK | chk_stiva_movimenti_motivo_forzatura |  |
| CHECK | chk_stiva_movimenti_riga_con_fattura |  |
| CHECK | chk_stiva_movimenti_segno |  |
| CHECK | chk_stiva_movimenti_tipo |  |
| FOREIGN KEY | fk_soggetti_titoli_iva_movimenti_fattura | fattura_id |
| FOREIGN KEY | fk_soggetti_titoli_iva_movimenti_fattura_riga | fattura_riga_id |
| FOREIGN KEY | fk_soggetti_titoli_iva_movimenti_titolo | titolo_iva_id |
| PRIMARY KEY | pk_soggetti_titoli_iva_movimenti | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_stiva_movimenti_fattura_id | `CREATE INDEX ix_stiva_movimenti_fattura_id ON anagrafiche.soggetti_titoli_iva_movimenti USING btree (fattura_id) WHERE (fattura_id IS NOT NULL)` |
| ix_stiva_movimenti_titolo | `CREATE INDEX ix_stiva_movimenti_titolo ON anagrafiche.soggetti_titoli_iva_movimenti USING btree (titolo_iva_id, data_movimento)` |
| pk_soggetti_titoli_iva_movimenti | `CREATE UNIQUE INDEX pk_soggetti_titoli_iva_movimenti ON anagrafiche.soggetti_titoli_iva_movimenti USING btree (id)` |
| uq_stiva_movimenti_documento | `CREATE UNIQUE INDEX uq_stiva_movimenti_documento ON anagrafiche.soggetti_titoli_iva_movimenti USING btree (titolo_iva_id, tipo_movimento, fattura_id, fattura_riga_id) NULLS NOT DISTINCT WHERE (fattura_id IS NOT NULL)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stiva_movimenti_z90_accumulatore_ins_upd_dlt | AFTER | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_titoli_iva_movimenti_accumulatore()` |
| trg_stiva_movimenti_z90_accumulatore_ins_upd_dlt | AFTER | DELETE | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_titoli_iva_movimenti_accumulatore()` |
| trg_stiva_movimenti_z90_accumulatore_ins_upd_dlt | AFTER | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_titoli_iva_movimenti_accumulatore()` |

---
{% include-markdown "signature-core.md" %}
