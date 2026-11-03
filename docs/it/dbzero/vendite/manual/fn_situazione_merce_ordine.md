## 📘 Documentazione Concettuale – Funzione `vendite.fn_situazione_merce_ordine(p_ddt_ids, p_ordine_ids)`

> **Ultimo aggiornamento**: 3 novembre 2026

> 👀 **Vedi anche**
>
> [vendite.vw_situazione_merce_ordine](/dbzero/vendite/views/vw_situazione_merce_ordine) — la stessa cosa, senza filtro
> [vendite.fn_partite_merce](/dbzero/vendite/funzioni/fn_partite_merce) — la partita da cui somma
> [vendite.fn_af_merce_per_riga](/dbzero/vendite/funzioni/fn_af_merce_per_riga) — il fatturato d'ordine, letto per le chiavi delle righe in uscita
> [vendite.vw_af_merce_per_riga](/dbzero/vendite/views/vw_af_merce_per_riga)
> Brief: `docs/it/dev/work-done/brief-db-partita-merce-per-documento.md` (giro 2, D3)

---
### 🎯 Scopo Principale
(latest review 2026-11-03)

`vendite.fn_situazione_merce_ordine` è **la situazione della merce per riga
d'ordine** — lo stesso aggregato parlante di
[`vw_situazione_merce_ordine`](vw_situazione_merce_ordine.md), che ne è la
proiezione senza filtro — calcolato **per i documenti che si chiedono**, non per
tutte le righe d'ordine del database.

Nasce dallo stesso difetto di forma della partita: il pannello «Situazione
merce» legge **sempre** per documento (un ordine, o un DDT), e la vista — che non
ha un parametro — sommava le partite di **tutti** gli ordini per poi scartare le
righe che non servivano. Dal giro 1 la partita ha una funzione con un seme
([`fn_partite_merce`](fn_partite_merce.md)); questa è la stessa mossa un livello
sopra.

⭐ **Solo merce** (rev 2026-11-03, `20261103-24`, brief-db-addebito-trasporto-ordine
§8.1): le righe-onere dell'ordine non hanno una situazione merce — non si
spediscono, non entrano in partita. Ogni seme le esclude
(`script.fn_natura_e_merce` sulla natura congelata della riga), anche quando una
bolla le ha toccate col legame dell'onere copiato.

---

### I semi

Gli stessi due, **nello stesso ordine**, di `fn_partite_merce`:

| Parametro | Cosa semina |
|---|---|
| `p_ddt_ids` | i DDT: le righe d'ordine che quelle spedizioni hanno **toccato** (un fulfillment di una loro riga) |
| `p_ordine_ids` | gli ordini: tutte le loro righe attive di merce |

* **Entrambi `NULL` = tutte le righe attive di merce.** È il modo in cui la vista chiama
  la funzione.
* **Un array vuoto semina zero righe.** Vuoto non è «tutte».
* Con entrambi valorizzati l'uscita è l'**unione** dei due insiemi.

⚠️ **Il seme per DDT non è «la partita di quel DDT»**: è la situazione
**intera** delle righe d'ordine che quel DDT ha toccato. Un ordine spedito in tre
volte, chiesto dal DDT di mezzo, risponde *consegnato 30, tre partite* — non
*10, una*. È la semantica che il pannello ha dal 2026-08-19 («per DDT = le righe
d'ordine che quella spedizione ha toccato»), e il presidio la costruisce.

---

### Perché il numero è giusto anche leggendo poco

L'aggregato di una riga d'ordine è la somma delle partite con quel
`ordine_riga_id` — che nella partita è la riga **minima** fra quelle evase (una
riga `MULTIPLA` conta sotto una sola). Le partite si chiedono a
`fn_partite_merce` **per ordine**: escono tutte quelle con `ordine_id` fra gli
ordini della chiusura, cioè tutte quelle delle righe dell'uscita. È completo per
costruzione, non per confronto.

| Pezzo | Con un seme legge |
|---|---|
| le righe d'ordine dell'uscita (`orr_in`) | quelle degli ordini chiesti, più le toccate dai DDT chiesti — dagli indici, due rami distinti e non un `OR` |
| le partite (`pm`) | `fn_partite_merce(NULL, <gli ordini della chiusura>)` |
| l'evaso (`ful`) | i fulfillment delle sole righe dell'uscita |
| il fatturato «sull'ordine» (`ord`) | [`fn_af_merce_per_riga`](/dbzero/vendite/funzioni/fn_af_merce_per_riga) con **una chiave `ORD:<uid>:R:<riga>` per riga in uscita** (giro 4, D5): prima leggeva la vista intera, il pezzo che cresce con le fatture |
| il residuo ri-consegnabile | `fn_ordine_riga_qta_riconsegna`, per riga |

---

### ⚠️ Due scelte di forma che non sono stile

**Il corpo è `BEGIN ATOMIC`**, come `fn_partite_merce`: le dipendenze — la
partita compresa — stanno in `pg_depend`, e il presidio che pretende
`security_invoker` su ogni vista che tocca dati riservati
(`rls/test-rls-viste-security-invoker`) attraversa funzione → funzione →
tabelle. Conseguenza: una colonna nuova nel `RETURNS TABLE` è un `DROP
FUNCTION` a cascata sulla vista.

**I due modi sono rami in `UNION ALL`**, mai `p IS NULL OR …`. Sulla lettura
della partita c'è una ragione in più: il seme degli ordini della chiusura è
**calcolato** (un `array_agg` sulla CTE dei semi), e il planner **non inlina**
una funzione di tabella il cui argomento contiene un sub-select — quel ramo è un
`Function Scan`, che regge (la forma di `fn_partite_merce` è provata in piano
generico) ma non è «le stesse scansioni della vista». Il ramo «tutte» chiama
`fn_partite_merce(NULL, NULL)` con due letterali e resta inlinato: la vista di
prima, scansione per scansione (33 su 33, provato il 21-09).

⚠️ `COALESCE(array_agg(…), '{}')` sul seme calcolato: un DDT senza fulfillment
darebbe `array_agg = NULL`, e `fn_partite_merce(NULL, NULL)` è «tutte» — il costo
che si voleva togliere, restituito in silenzio. Vuoto semina zero righe, ed è la
risposta giusta: quel DDT non ha toccato nessuna riga d'ordine.

---

### Chi la chiama

| Lettore | Come |
|---|---|
| `vw_situazione_merce_ordine` | `fn_situazione_merce_ordine(NULL, NULL)` — tutte |
| BE `list_situazione_merce_ordine` (pannello «Situazione merce», livello 1) | ⏳ richiesta BE nel brief: per ordine `(NULL, ARRAY[%s])`, per DDT `(ARRAY[%s], NULL)`, **senza** il `WHERE`/`EXISTS` di oggi; oggi legge la vista, che risponde giusto ma paga tutto |

---

### Esempio d'uso

```sql
-- Il pannello di un ordine: una riga per riga d'ordine attiva.
SELECT ordine_riga_id, riga_nr, ordinato, consegnato, tenuti, fatturato, da_spedire, stato
  FROM vendite.fn_situazione_merce_ordine(NULL, ARRAY[18586])
 ORDER BY riga_nr;

-- Dal DDT: le righe d'ordine che QUELLA spedizione ha toccato, con la loro
-- situazione intera (tutte le spedizioni, non solo questa).
SELECT ordine_id, ordine_riga_id, consegnato, partite_merce, stato
  FROM vendite.fn_situazione_merce_ordine(ARRAY[15854], NULL);
```

---

### Presidio

`db/pgtap/vendite/test-fn-situazione-merce-ordine-chiusura-v1.sql` (12 test).
I casi che contano sono costruiti, non letti dai dati:

* un ordine spedito su **tre DDT**, chiesto dal DDT di mezzo: la riga d'ordine
  esce con la situazione **intera** (30 consegnati, tre partite), non con la
  sola partita di quel DDT;
* la riga **mai spedita** e l'ordine **in bozza**: per seme ordine ci sono
  (`NON_SPEDITA` con il suo da spedire; `NON_IMPEGNATA` con `da_spedire` NULL),
  per seme DDT la prima non esce;
* una riga che evade **due ordini**: per il DDT escono entrambe le righe
  toccate, una `NON_MISURABILE` e l'altra senza partite — come dalla vista;
* la ri-consegna: consegnato 13, reso 5, tenuti 8, 2 da spedire;
* più i pin di forma (la vista nomina la funzione e nessuna tabella; 21 colonne
  con `ordinato numeric(18,6)`; `security_invoker`), il vuoto che non è «tutte»,
  lo scope.

---

{% include-markdown "signature-core.md" %}
