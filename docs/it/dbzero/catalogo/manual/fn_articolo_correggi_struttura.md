## 📘 Documentazione Concettuale – Funzione `catalogo.fn_articolo_correggi_struttura`

> 👀 **Vedi anche**
>
> [catalogo.trgfn_articoli_guard_struttura_se_usato](/dbzero/catalogo/manual/trgfn_articoli_guard_struttura_se_usato) — la regola di cui questo verbo è la porta
> [catalogo.articoli](/dbzero/catalogo/manual/articoli) — la regola «un articolo usato non cambia la sua struttura»

### 🎯 Scopo Principale

(latest review 2026-10-13, brief-db-articoli-ammessi-per-documento A-10)

Il **SUPER_ADMIN** corregge i flag strutturali di un articolo **anche se usato**. Serve per un
errore di caricamento. Per vendere o gestire un articolo in modo diverso, la via normale resta un
articolo nuovo.

---

### Come si chiama

`catalogo.fn_articolo_correggi_struttura(p_articolo_id, p_campi)`

* `p_campi`: un oggetto JSON con le **sole** colonne da cambiare, fra le otto strutturali
  (`is_composito`, `is_solo_componente`, `natura_vendita_id`, `causale_onere_id`,
  `listino_tipologia_id`, `gestito_a_magazzino`, `requires_lotto`, `requires_serial`). Le
  colonne assenti restano come sono.
  Esempio: `{"natura_vendita_id": 3}`.

| Caso | Esito |
| --- | --- |
| chi chiama non è SUPER_ADMIN (o non è in veste OPERATORE) | `E_PERMESSO_NEGATO` |
| `p_campi` vuoto, non oggetto, o con una colonna fuori dalle otto | `E_PARAMETRO_INVALIDO` |
| articolo inesistente | `E_ARTICOLO_NOT_FOUND` |

Il permesso lo decide `script.fn_guard_super_admin`, la stessa regola del backend.

### Cosa fa e cosa non fa

* Scrive con la porta aperta (GUC `zeroerp.articolo_correggi_struttura`, onorata dal guard solo col
  proprietario della tabella) e la richiude.
* **Non** salta gli altri guard dell'articolo: distinta, onere, listino del composito parlano lo
  stesso.
* **Non** tocca le righe già scritte: la natura è congelata sulla riga, e un documento chiuso resta
  la fotografia di quando è nato.

SECURITY DEFINER, `search_path` bloccato, EXECUTE solo all'app. Il backend lo espone nel giro
BE/FE finale del brief (§9.6).

---
{% include-markdown "signature-core.md" %}
