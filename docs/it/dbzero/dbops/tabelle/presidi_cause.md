{% include-markdown "it/dbzero/dbops/manual/presidi_cause.md" %}
# 📚 Tabella `presidi_cause`

> 📝 **Descrizione**
>
> Le cause di un presidio le cui righe sono guasti diversi (dbops.presidi.colonna_variante valorizzata), ognuna con chi la spegne. La causa ha il suo a-chi-tocca (chi_agisce, stesso dominio di dbops.presidi.chi_agisce) e i suoi testi per lingua (dbops.presidi_testi, FK (vista, variante) -&gt; (vista, causa)): un solo chi_agisce per presidio sarebbe sbagliato per alcune righe, come lo sarebbe un testo unico (il presidio dei processi e' del SISTEMISTA, ma NON_PROGRAMMATO e GIRA_E_NON_REGISTRA toccano allo SVILUPPO). dbops.presidi.chi_agisce resta il valore del presidio nel suo insieme. Completezza nei pgTAP: le cause stanno solo sui presidi che dichiarano colonna_variante, ognuna ha il testo it (dbops/test-presidi-testi-v1); il catalogo coincide con le cause che la vista puo' produrre (il test del presidio). Seed: 80_data/sql/dbops/presidi_cause.csv, caricato dal mirror dei testi prima dei testi.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| vista | text | NO |  |
| causa | text | NO |  |
| chi_agisce | text | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_presidi_cause_causa_non_vuota |  |
| CHECK | chk_presidi_cause_chi_agisce |  |
| FOREIGN KEY | fk_presidi_cause_presidi | vista |
| PRIMARY KEY | pk_presidi_cause | id |
| UNIQUE | uq_presidi_cause_vista_causa | vista, causa |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_presidi_cause | `CREATE UNIQUE INDEX pk_presidi_cause ON dbops.presidi_cause USING btree (id)` |
| uq_presidi_cause_vista_causa | `CREATE UNIQUE INDEX uq_presidi_cause_vista_causa ON dbops.presidi_cause USING btree (vista, causa)` |

---
{% include-markdown "signature-core.md" %}
