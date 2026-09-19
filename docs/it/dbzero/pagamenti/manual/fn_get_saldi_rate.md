## 📘 Documentazione Concettuale – Funzione `pagamenti.fn_get_saldi_rate`

> 👀 **Vedi anche**
>
> **Le tre porte dello stesso nucleo:**
>
> • [pagamenti.fn_get_saldo_rata](/dbzero/pagamenti/funzioni/fn_get_saldo_rata) — la porta a **un elemento**: guard di parametro ed `E_RATA_NON_TROVATA`
> • [pagamenti.vw_saldi_rate](/dbzero/pagamenti/views/vw_saldi_rate) — la porta dello **scadenzario**: tutte le rate visibili
> • la chiamata con l'array degli id della **pagina**, dal backend (`saldi_service`)
>
> **Chi la usa:**
>
> • `pagamenti.trgfn_vendite_contabili_righe_guard_rata` — per sapere quanto spazio c'è, attraverso la porta 1
> • [pagamenti.vw_rate_fuori_capienza](/dbzero/pagamenti/views/vw_rate_fuori_capienza) — in una chiamata sull'insieme dei candidati
>
> **La regola dei saldi, per chi non è tecnico:** [Gestione dei pagamenti](/guide/gestione-dei-pagamenti)
>
> **Brief:** [brief-db-distinta-ricerca-rate](/dev/work-in-progress/brief-db-distinta-ricerca-rate) §4-bis.4 (P-3) e §4-bis.6 (Q-A/γ)

---

### 🎯 Scopo Principale

(rev 2026-09-17)

È **il nucleo** dei saldi delle rate: la formula scritta **una volta**, in forma
set-based, per N rate. Risponde con quattro numeri per `scadenza_id`:

| Colonna | Domanda |
| --- | --- |
| `saldo` | quanto manca ancora da **registrare** su questa rata |
| `in_lavorazione` | quanto è già stato **dichiarato** e non ancora registrato |
| `incassato` | quanto di ciò che è registrato è **denaro davvero arrivato** |
| `has_movimenti` | se almeno un movimento ha toccato la rata |

Il significato delle colonne è quello della porta a un elemento
(`fn_get_saldo_rata`), che questa scheda non ripete.

---

### ⭐ Una formula, tre porte

Fino al 17-09-2026 il saldo di una rata aveva una porta sola, per rata, plpgsql
a tre letture. Su una fattura regge; su uno **scadenzario** — tutte le rate
aperte, e «aperta» *è* un predicato sul residuo — sono N × 3 letture prima di
poter filtrare. Non è una misura: uno scadenzario è il perimetro intero per
costruzione.

Le tre porte leggono lo stesso nucleo, quindi **non possono divergere**: due sedi
del residuo divergono alla prima regola nuova, e sono numeri su cui si sollecita
un cliente.

---

### ⭐ L'imputazione dei movimenti senza rata (Q-A/γ, Tid 17-09-2026)

Il saldo di una **fattura** somma i movimenti per `fattura_id`; quello di una
rata, fino a questa rev, solo i movimenti che la **nominano**. Un incasso
registrato «sulla fattura, senza rata» — il fondo fattura lo scrive sempre così,
e l'operatore può farlo dal lookup — abbassava il saldo del documento e **non**
quello delle rate: una fattura a rata unica pagata senza rata aveva saldo
documento 0 e saldo rata 100. Era il **punto cieco della rata**.

La regola, derivata e mai scritta (è D2 fino in fondo):

* i movimenti attivi del documento **senza** `scadenza_id` si attribuiscono alle
  sue rate in ordine di `data_scadenza` (poi `numero_rata`, `id`), fino alla
  capienza di ciascuna al netto dei movimenti diretti; **l'ultima rata assorbe
  l'eccedenza**, così Σ saldi delle rate = saldo del documento, sempre;
* lo stesso, in un secondo stadio, per le righe postabili senza rata
  (`in_lavorazione`): così il guard di capienza vede lo spazio che il documento
  sa anche **prima** del posting (la riga del fondo è in lavorazione finché non
  si registra);
* `incassato` segue l'imputazione in proporzione; `has_movimenti` è vero anche
  se la rata è toccata solo da una quota imputata;
* il verso è quello del **documento**: su una nota di credito le rate sono
  negative e la capienza è in valore assoluto (la forma di D14-c). Un
  non-imputato di verso contrario va tutto sulla **prima** rata, dove resta
  visibile come anomalia.

⚠️ **L'ordine dei fatti conta, ed è una scelta.** Su un piano 30/70 un acconto
di 20 senza rata va sulla rata 1; una riga diretta da 30 sulla rata 1 che arriva
*dopo* trova 10, e il guard la respinge coi numeri. Nell'ordine inverso l'acconto
scivola sulla rata 2. Non è un difetto: il picker delle rate mostra **esattamente**
i numeri del nucleo, quindi l'operatore vede «10» e il guard accetta «10». Far
accettare al guard ciò che il picker non mostra sarebbe la divergenza
tooltip/rifiuto che le linee guida vietano. La forzatura a due tempi resta la
via per il caso vero.

---

### Regole principali

* `p_scadenza_ids` è **obbligatorio** e si filtra con `= ANY` nudo: `NULL` =
  zero righe. ⛔ Non «NULL = tutte» con un `p IS NULL OR …`: provato con
  `EXPLAIN`, in `LATERAL` o con un parametro plpgsql in piano generico il ramo
  `IS NULL` non si piega e l'`OR` diventa una scansione intera dei movimenti per
  rata — sul percorso del guard di capienza. Per tutte le rate c'è
  `vw_saldi_rate`, che costruisce l'array.
* Per imputare servono **tutte** le rate del documento: il nucleo legge il piano
  intero dei documenti delle rate chieste e restituisce le chieste.
* Una rata **senza movimenti torna lo stesso**, con `has_movimenti = false`:
  senza, il picker perderebbe le rate mai toccate.
* `p_escludi_contabile_riga_id` toglie la riga che sta scrivendo, diretta o
  senza rata («quanto spazio c'era prima di me»).
* `STABLE` e `LANGUAGE sql`: **non solleva mai** (una rata invisibile è zero
  righe; a dire `E_RATA_NON_TROVATA` è la porta 1) e il planner può inlinarla.
  `INVOKER`: somma ciò che chi legge vede, le tre tabelle lette hanno la RLS.

### Presidio

`db/pgtap/pagamenti/test-fn-get-saldi-rate-v1.sql` (17): le tre porte danno gli
stessi numeri, e i casi dell'imputazione sono **costruiti** — rata unica pagata
senza rata → 0; FIFO su tre rate; Σ rate = documento; la riga in lavorazione
occupa lo spazio e il guard la vede; il verso contrario resta visibile;
l'eccedenza resta sull'ultima.

{% include-markdown "signature-core.md" %}
