## 📘 Documentazione Concettuale – Funzione `vendite.fn_partite_merce(p_ddt_ids, p_ordine_ids)`

> 👀 **Vedi anche**
>
> [vendite.vw_partite_merce](/dbzero/vendite/views/vw_partite_merce) — la stessa cosa, senza filtro
> [vendite.vw_af_merce_per_riga](/dbzero/vendite/views/vw_af_merce_per_riga)
> [vendite.fn_list_ddt_da_pushare](/dbzero/vendite/funzioni/fn_list_ddt_da_pushare)
> [vendite.fn_ddt_push_diagnosi](/dbzero/vendite/funzioni/fn_ddt_push_diagnosi)
> Brief: `docs/it/dev/work-in-progress/brief-db-partita-merce-per-documento.md`

---
### 🎯 Scopo Principale
(latest review 2026-09-21)

`vendite.fn_partite_merce` è **il conto della merce** — lo stesso di
[`vw_partite_merce`](vw_partite_merce.md), che ne è la proiezione senza filtro —
calcolato **per i documenti che si chiedono**, non per tutti.

Nasce per un difetto di forma, non di numeri: una vista non ha un parametro, e
quando il drawer di un DDT chiedeva *«le partite di questo documento»* il
database calcolava le partite di **tutti** i documenti e scartava le altre. Con
cinquanta DDT non si nota; il modello ne ammette cinquantamila e non ha
retention, quindi quel costo cresce con la storia dell'azienda — e sotto RLS
ogni riga scandita paga la propria policy.

---

### I semi

| Parametro | Cosa semina |
|---|---|
| `p_ddt_ids` | i DDT: tutte le loro righe |
| `p_ordine_ids` | gli ordini: le righe di DDT che ne evadono le righe |

* **Entrambi `NULL` = tutte le partite.** È il modo in cui la vista chiama la
  funzione.
* **Un array vuoto semina zero righe.** Vuoto non è «tutte»: chi passa `{}`
  ottiene nulla, e lo ottiene di proposito.
* Con entrambi valorizzati l'uscita è l'**unione**: le righe dei DDT chiesti
  *oppure* le righe il cui ordine è fra quelli chiesti.

⚠️ **Il filtro d'uscita per ordine è sulla colonna proiettata** `ordine_id`,
che è la riga d'ordine **minima** fra quelle che la riga di DDT evade. Una riga
`MULTIPLA` (due ordini evasi insieme) esce quindi **sotto uno solo** dei due,
esattamente come la legge il backend dalla vista (`WHERE ordine_id = …`). Il
seme, invece, la prende in entrambi i casi: serve alla chiusura, non
all'uscita.

---

### La chiusura: perché il numero è giusto anche leggendo poco

La partita di una riga non dipende da *tutte* le altre, ma da un insieme
piccolo e nominabile — lo dicono le chiavi delle finestre della vista:

| Pezzo del conto | Da cosa dipende, per la riga `r` |
|---|---|
| il fatturato «dall'ordine» (`alloc`, greedy dalla spedizione più vecchia) | **tutte le spedizioni della stessa riga d'ordine**, in ordine di data |
| i pezzi che cambiano casa dopo una nota di credito (`migra`) | **tutte le ri-consegne della stessa origine**, in ordine di data |
| il sospetto di riga duplicata (`sospetto`) | le righe **dello stesso DDT** e i loro ordini |
| resi, rettifiche, fatturato di spedizione | la riga stessa |

Ne discende la **chiusura**, a due salti:

1. **R0** — le righe dei semi;
2. **R1** — le righe che condividono con una di R0 la riga d'ordine: così la
   partizione della greedy è **completa** (senza R1 il secondo DDT di un ordine
   spedito in tre volte si crederebbe il primo, e prenderebbe il fatturato che
   spetta al più vecchio);
3. **O** — R0 ∪ R1 più le **origini** di ri-consegna delle loro righe: così,
   per ogni origine, la funzione vede **tutte** le sue ri-consegne (le
   «sorelle»), e la ripartizione dell'accredito fra loro è quella vera.

`riga` e `orig` si calcolano su R0 ∪ R1; `sospetto` sui DDT di R0 ∪ R1;
`af` — il contatore delle attività fatturabili — resta **intero** anche con un
seme (è il passo D5 del brief: cresce con le fatture, non con i DDT).

⭐ **È equivalente alla vista per costruzione**, non per confronto: ogni
colonna di una riga di R0 dipende solo da righe che la chiusura conserva. Il
presidio ([`test-fn-partite-merce-chiusura-v1`](#presidio)) lo prova
**costruendo** i casi in cui, senza un pezzo della chiusura, il numero sarebbe
sbagliato — non confrontando le righe di oggi.

> ⛔ **La regola per chi tocca la partita.** Chi aggiunge alla vista una
> finestra o un insieme con una chiave **nuova** — per articolo, per cliente,
> per commessa — **deve allargare la chiusura** in questa funzione, e costruire
> nel presidio il caso che la richiede. Altrimenti la funzione sbaglia **solo
> quando è chiamata con un seme**, mentre la vista (senza seme) resta giusta:
> nessun confronto fra le due lo vedrebbe.

---

### ⚠️ Due scelte di forma che non sono stile

**Il corpo è `BEGIN ATOMIC`**, non una stringa. Così le tabelle e le viste che
la funzione legge sono registrate nel catalogo (`pg_depend`): una rinomina a
monte viene **rifiutata** invece di lasciare la funzione «viva ma rotta»; e il
presidio che pretende `security_invoker` su ogni vista che tocca dati riservati
(`rls/test-rls-viste-security-invoker`) può **attraversare** la funzione e
continuare a vedere `vw_partite_merce` — con un corpo a stringa la vista
sarebbe uscita dal perimetro in silenzio. ⚠️ Conseguenza: una colonna nuova
nel `RETURNS TABLE` è un `DROP FUNCTION` a cascata sulle **quattro** viste
(`vw_partite_merce`, `vw_contatore_merce`, `vw_resi_da_accreditare`,
`vw_situazione_merce_ordine`).

**I due modi — per seme e «tutte» — sono rami separati in `UNION ALL`**, mai
un `p IS NULL OR colonna = ANY(p)`. Quell'`OR`, quando il chiamante è plpgsql
e il piano diventa generico, è una scansione intera sotto policy — proprio il
costo che la funzione doveva togliere. Con i due rami, quello «tutte» ha un
predicato senza colonne che il planner tratta come *One-Time Filter*: quando è
falso non viene nemmeno eseguito; quello per seme entra dall'indice. Provato
con `PREPARE` e piano generico forzato. E in modo «tutte» le scansioni sono le
**stesse** della vista di prima: nessuna in più sotto RLS.

---

### Chi la chiama

| Lettore | Come |
|---|---|
| `vw_partite_merce` | `fn_partite_merce(NULL, NULL)` — tutte |
| `fn_list_ddt_da_pushare(p_ddt_id)` | `ARRAY[p_ddt_id]`, o `NULL` se il lister è chiamato senza documento (lista push, cockpit) |
| `fn_ddt_push_diagnosi(p_ddt_id)` | idem |
| BE `list_partite_merce` (pannello «Situazione merce») | ⏳ richiesta BE nel brief: per DDT `ARRAY[%s]`, per ordine `(NULL, ARRAY[%s])`; oggi legge la vista, che risponde giusto ma paga tutto |
| `vw_situazione_merce_ordine`, `vw_contatore_merce`, i verbi dei resi | ancora la vista: sono il **giro D3** del brief, «prima possibile» |

---

### Esempio d'uso

```sql
-- La situazione della merce di una spedizione, riga per riga.
SELECT ddt_riga_id, consegnato, reso, tenuti, fatturato, stato
  FROM vendite.fn_partite_merce(ARRAY[15854])
 ORDER BY ddt_riga_id;

-- Tutte le spedizioni di un ordine, comprese le righe aggiunte a mano ai suoi DDT.
SELECT ddt_id, ddt_riga_id, origine, stato, differenza
  FROM vendite.fn_partite_merce(NULL, ARRAY[18586]);
```

---

### Presidio

`db/pgtap/vendite/test-fn-partite-merce-chiusura-v1.sql` (14 test). I casi
che contano sono costruiti, non letti dai dati:

* un ordine spedito su **tre DDT** e fatturato dall'ordine per metà: il DDT di
  mezzo chiesto da solo deve sapere che il primo ha già preso la sua parte (R1);
* un reso con **accredito parziale** e **due ri-spedizioni**: la seconda
  chiesta da sola deve sapere che la prima ha preso l'unico pezzo accreditato
  (le sorelle, O);
* una riga che evade **due ordini**: esce sotto uno solo, come dalla vista;
* più i pin di forma: la vista nomina la funzione e nessuna tabella (un corpo
  solo), le 23 colonne coi loro tipi (`consegnato` resta `numeric(18,6)`: un
  `SELECT *` dalla funzione lo perderebbe in silenzio), lo scope.

---

{% include-markdown "signature-core.md" %}
