## 📘 Documentazione Concettuale – Funzione `catalogo.fn_articolo_correggi_struttura`

> 👀 **Vedi anche**
>
> [catalogo.trgfn_articoli_guard_struttura_se_usato](/dbzero/catalogo/manual/trgfn_articoli_guard_struttura_se_usato) — la regola di cui questo verbo è la porta
> [catalogo.articoli](/dbzero/catalogo/manual/articoli) — la regola «un articolo usato non cambia la sua struttura»

### 🎯 Scopo Principale

(latest review 2026-10-18, brief-db-articoli-ammessi-per-documento A-10, R-DB-3)

Il **SUPER_ADMIN** corregge i flag strutturali di un articolo **anche se usato**. Serve per un
errore di caricamento. Per vendere o gestire un articolo in modo diverso, la via normale resta un
articolo nuovo.

---

### Come si chiama

`catalogo.fn_articolo_correggi_struttura(p_articolo_id, p_campi)`

* `p_campi`: un oggetto JSON con le **sole** colonne da cambiare, fra quelle strutturali che
  elenca `catalogo.fn_articolo_colonne_struttura()` (oggi `is_composito`, `is_solo_componente`,
  `natura_vendita_id`, `causale_onere_id`, `listino_tipologia_id`, `gestito_a_magazzino`,
  `requires_lotto`, `requires_serial`). Le colonne assenti restano come sono.
  Esempio: `{"natura_vendita_id": 3}`.

| Caso | Esito |
| --- | --- |
| chi chiama non è SUPER_ADMIN (o non è in veste OPERATORE) | `E_PERMESSO_NEGATO` |
| `p_campi` vuoto, non oggetto, o con una colonna fuori dall'elenco | `E_PARAMETRO_INVALIDO` |
| un valore che non è del tipo della colonna (per esempio `"forse"` per un flag) | errore di conversione (`22P02`) |
| con la struttura corretta, l'articolo non sarebbe più ammesso in righe di documenti aperti | `E_ARTICOLO_STRUTTURA_RIGHE_APERTE`, e la correzione si annulla |
| articolo inesistente | `E_ARTICOLO_NOT_FOUND` |

Il permesso lo decide `script.fn_guard_super_admin`, la stessa regola del backend.

### Cosa fa e cosa non fa

* Scrive **solo** le colonne passate, ciascuna convertita col tipo della sua colonna. L'elenco delle
  colonne ammesse e la scrittura vengono dalla stessa sede: una colonna aggiunta all'elenco si
  corregge senza toccare il verbo (rev 2026-10-18, R-DB-3; prima l'elenco era una costante del
  verbo e la scheda articolo lo ricopiava).
* Scrive con la porta aperta (GUC `zeroerp.articolo_correggi_struttura`, onorata dal guard solo col
  proprietario della tabella) e la richiude.
* **Non** salta gli altri guard dell'articolo: distinta, onere, listino del composito parlano lo
  stesso.
* **Non** tocca le righe già scritte: la natura è congelata sulla riga, e un documento chiuso resta
  la fotografia di quando è nato.

### Le righe dei documenti aperti

Il verbo rigiudica le righe **vive** dell'articolo con la stessa check dei guard di riga
(`catalogo.fn_articolo_righe_vive_non_ammesse`, che usa `script.fn_check_articolo_riga` col primo
motivo, la natura e il tipo d'eccezione della riga), **prima** e **dopo** la scrittura. Se la
correzione rende non ammessa anche una sola riga che prima lo era, rifiuta tutta la correzione
(`E_ARTICOLO_STRUTTURA_RIGHE_APERTE`, decisione A-11 di Tid, 2026-10-18). Una riga già non ammessa
prima non blocca: non è la correzione ad averla resa tale.

Una riga è **viva** se è attiva e il suo documento non è chiuso:

| Dove | Documento aperto |
| --- | --- |
| preventivo, ordine, bolla, offerta, contratto | la fase dello stato non è `CHIUSO` |
| versione di listino | lo stato non è `CHIUSA` |
| promo | il periodo non è ancora finito alla data operativa |

Sono le sette tabelle su cui è montato `script.trgfn_righe_guard_articolo_ammesso`; il pgTAP
`catalogo/test-articolo-correzione-righe-aperte-v1` diventa rosso se il guard viene montato su una
tabella che l'elenco non legge.

Perché qui: la porta è l'unica strada da cui un articolo usato cambia struttura. Senza questo
controllo, un ordine confermato con un articolo diventato «solo componente» restava com'era, e la
generazione della bolla falliva a metà.

* Le righe si contano in **tutte** le aziende (il verbo è SECURITY DEFINER, come
  `catalogo.fn_articolo_usato`). Il messaggio dà solo il numero di righe e di documenti; i
  documenti (al più 50 righe, col codice del motivo) stanno nel dettaglio dell'errore.
* Una correzione che non tocca i motivi passa anche con righe vive. Esempio: la natura, che sulle
  righe è congelata.
* **Fuori**: la distinta (un legame non si cancella e non si spegne se le righe dei documenti hanno
  i suoi componenti, e il composito come componente lo ferma
  `trgfn_articoli_guard_flags_struttura_bom_attiva`); magazzino, lotto e matricola, che li giudica
  l'emissione della bolla.

SECURITY DEFINER, `search_path` bloccato, EXECUTE solo all'app. Il backend lo espone nel giro
BE/FE finale del brief (§9.6).

---
{% include-markdown "signature-core.md" %}
