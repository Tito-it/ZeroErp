{% include-markdown "it/dbzero/anagrafiche/manual/soggetti_titoli_iva_ambiti.md" %}
# 📚 Tabella `soggetti_titoli_iva_ambiti`

> 📝 **Descrizione**
>
> PER COSA vale un titolo IVA ristretto (D10/D12 di brief-db-be-iva-risolutore-e-regime-cliente): una riga per oggetto coperto, su tre livelli — articolo, gruppo voce, tipologia voce. 🔴 E' la differenza fra un titolo e il difetto appena rimosso: senza l'ambito un titolo sarebbe anagrafiche.clienti.iva_id spostato di un piano, cioe' un valore che vince su tutto perche' nessuno gli ha detto dove fermarsi. Il rilievo e' di Tid: un'agevolazione per disabilita' vale su certe merci, e applicata a tutto il documento produrrebbe otto righe agevolate che non lo sono. ⭐ I tre livelli sono gia' nel modello e nessuno va inventato: catalogo.articoli.id, vendite.articoli_gruppi.id e vendite.articoli_tipologie.id, cioe' esattamente le due classificazioni che catalogo.articoli porta gia' (gruppo_voce_id, tipo_voce_id). ⚠️ `livello` e' DICHIARATO e non dedotto da quale FK e' piena: cosi' non esistono ne' righe con due colonne piene ne' righe che non nominano niente — le due trappole gemelle del NULL in una chiave. E la UNIQUE e' NULLS NOT DISTINCT perche' con la regola standard due righe identiche con gli stessi NULL non collidono. ⚠️ Nessuna colonna `attivo`: l'ambito e' la definizione del titolo, non un'entita' con un ciclo di vita — si aggiunge o si toglie, e a spegnere il titolo intero c'e' soggetti_titoli_iva.attivo. ⛔ ON DELETE CASCADE, a differenza del registro dei movimenti: una clausola senza il suo titolo non significa niente, un movimento di plafond invece e' un fatto contabile. Il livello e' anche la SPECIFICITA' con cui D13 arbitra due titoli sulla stessa riga: articolo &gt; categoria di merce &gt; tutto. rev 2026-08-29.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| titolo_iva_id | bigint | NO |  |
| livello | character varying(16) | NO |  |
| articolo_id | uuid | YES |  |
| gruppo_voce_id | bigint | YES |  |
| tipo_voce_id | bigint | YES |  |
| note | character varying(255) | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_soggetti_titoli_iva_ambiti_livello |  |
| FOREIGN KEY | fk_soggetti_titoli_iva_ambiti_articolo | articolo_id |
| FOREIGN KEY | fk_soggetti_titoli_iva_ambiti_gruppo | gruppo_voce_id |
| FOREIGN KEY | fk_soggetti_titoli_iva_ambiti_tipo_voce | tipo_voce_id |
| FOREIGN KEY | fk_soggetti_titoli_iva_ambiti_titolo | titolo_iva_id |
| PRIMARY KEY | pk_soggetti_titoli_iva_ambiti | id |
| UNIQUE | uq_soggetti_titoli_iva_ambiti_oggetto | titolo_iva_id, livello, articolo_id, gruppo_voce_id, tipo_voce_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_soggetti_titoli_iva_ambiti | `CREATE UNIQUE INDEX pk_soggetti_titoli_iva_ambiti ON anagrafiche.soggetti_titoli_iva_ambiti USING btree (id)` |
| uq_soggetti_titoli_iva_ambiti_oggetto | `CREATE UNIQUE INDEX uq_soggetti_titoli_iva_ambiti_oggetto ON anagrafiche.soggetti_titoli_iva_ambiti USING btree (titolo_iva_id, livello, articolo_id, gruppo_voce_id, tipo_voce_id) NULLS NOT DISTINCT` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_soggetti_titoli_iva_ambiti_a10_articoli_gruppi_requi_a02454 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'articoli_gruppi', 'attivo', 'gruppo_voce_id', 'id')` |
| trg_soggetti_titoli_iva_ambiti_a10_articoli_gruppi_requi_a02454 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'articoli_gruppi', 'attivo', 'gruppo_voce_id', 'id')` |
| trg_soggetti_titoli_iva_ambiti_a10_articoli_require_atti_b48ce2 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_soggetti_titoli_iva_ambiti_a10_articoli_require_atti_b48ce2 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_soggetti_titoli_iva_ambiti_a10_articoli_tipologie_re_30578a | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'articoli_tipologie', 'attivo', 'tipo_voce_id', 'id')` |
| trg_soggetti_titoli_iva_ambiti_a10_articoli_tipologie_re_30578a | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'articoli_tipologie', 'attivo', 'tipo_voce_id', 'id')` |
| trg_soggetti_titoli_iva_ambiti_a10_soggetti_titoli_iva_r_ead690 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'soggetti_titoli_iva', 'attivo', 'titolo_iva_id', 'id')` |
| trg_soggetti_titoli_iva_ambiti_a10_soggetti_titoli_iva_r_ead690 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'soggetti_titoli_iva', 'attivo', 'titolo_iva_id', 'id')` |
| trg_soggetti_titoli_iva_ambiti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_soggetti_titoli_iva_ambiti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_soggetti_titoli_iva_ambiti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_soggetti_titoli_iva_ambiti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_soggetti_titoli_iva_ambiti_z90_guard_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_titoli_iva_ambiti_guard()` |
| trg_soggetti_titoli_iva_ambiti_z90_guard_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_titoli_iva_ambiti_guard()` |
| trg_soggetti_titoli_iva_ambiti_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('soggetti_titoli_iva_ambiti_id')` |
| trg_soggetti_titoli_iva_ambiti_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('soggetti_titoli_iva_ambiti_id')` |

---
{% include-markdown "signature-core.md" %}
