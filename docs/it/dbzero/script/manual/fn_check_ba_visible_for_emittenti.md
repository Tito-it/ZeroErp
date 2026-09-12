## 📘 Documentazione Concettuale – Funzione `script.fn_check_ba_visible_for_emittenti`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[script.fn_get_ba_emittente_sr_id](/dbzero/script/manual/fn_get_ba_emittente_sr_id)
>
[script.fn_get_emittenti_scope_sr_effettivo](/dbzero/script/manual/fn_get_emittenti_scope_sr_effettivo)
>
[script.fn_search_soggetti_universale](/dbzero/script/manual/fn_search_soggetti_universale)

---
### 🎯 Scopo Principale
(latest review 18-08-26)

Risponde sì o no a:

> **Questo billing account è visibile per questo insieme di emittenti
> autorizzati?**

È un `fn_check_*`: booleano puro, nessun errore sollevato. Chi la chiama decide
cosa farne.

---

### Logica Operativa

Dal 18-08-2026 la funzione è diventata **due righe di senso**:

1. se l'insieme degli emittenti autorizzati è vuoto o `NULL`, la risposta è
   **no**, e arriva subito;
2. altrimenti si chiede a
   [`fn_get_ba_emittente_sr_id`](/dbzero/script/manual/fn_get_ba_emittente_sr_id)
   *quale* emittente fattura quel billing account, e si guarda se sta fra gli
   autorizzati.

La regola a due livelli (mapping specifico → fallback sul default) **non è più
scritta qui**: vive nella funzione delegata, in un posto solo.

---

### ⚠️ `NULL` qui significa «nessuno», non «tutti»

È l'unico punto in cui questa funzione si scosta dalla convenzione a tre stati
usata altrove, e va saputo.

Nel resto della famiglia dello scope, `NULL` significa *«nessuna
restrizione»*. Qui no: `NULL` e `'{}'` danno entrambi **false**. Il motivo è che
questa funzione risponde a una domanda *puntuale* — «è fra i miei?» — e senza un
insieme di riferimento quella domanda non ha una risposta affermativa onesta.

> **La convenzione a tre stati la legge il chiamante, prima di arrivare qui.**
> È quello che fa `fn_search_soggetti_universale`: accende il filtro solo se lo
> scope effettivo *non* è `NULL`, e in quel caso `'{}'` produce zero risultati —
> fail-closed.

---

### ⚠️ Perché la delega, e perché adesso

La risposta non è cambiata di una virgola. È cambiato **da dove viene**.

Il motivo è che la stessa regola serviva anche per **mostrare** il nome
dell'emittente nella riga della ricerca universale, non solo per filtrare. Con
la sola forma booleana, l'unico modo di ottenere il nome sarebbe stato
riscrivere la regola una seconda volta — e due copie della stessa regola non
restano uguali. Alla prima modifica, il filtro e l'etichetta avrebbero iniziato
a raccontare cose diverse sullo stesso billing account, in silenzio.

**L'equivalenza fra la vecchia forma e la nuova è esatta**, e vale la pena
vederla scritta perché non è ovvia a colpo d'occhio:

| Vecchio | Perché equivale |
| --- | --- |
| «esiste una riga di mapping su questo BA verso uno degli autorizzati» | `uq_emittenti_fiscali_ba` rende la riga per BA **al massimo una**: «esiste una riga verso uno di essi» ⇔ «l'unica riga punta a uno di essi» |
| «il BA non ha nessun mapping **e** uno degli autorizzati è `is_default`» | `uq_emittenti_fiscali_ba_default` rende il default **al massimo uno**: ⇔ «il default esiste ed è fra gli autorizzati» |

In entrambi i casi: *«l'emittente risolto del BA sta fra gli autorizzati»*.

⚠️ L'equivalenza poggia sui **due indici univoci**. È una dimostrazione, non un
presidio: se domani uno dei due sparisse, la dimostrazione cadrebbe senza che
nessuno se ne accorga. Per questo l'equivalenza è anche **esercitata su dati
costruiti**, nei test `6` e `7` di
`db/pgtap/script/test-ba-emittente-risoluzione-v1.sql`.

⭐ **Dal 2026-09-13 la regola delegata ha un livello in più, e questo check lo
ha ereditato senza una riga di modifica** (D13, changeSet `20260913-01`): per un
BA senza legame, *in sessione*, l'emittente risolto è quello dell'operatore che
sta agendo — la stessa risposta che il trigger `z90_link_ef` sta per scrivere;
il default resta per chi una sessione non ce l'ha. È ciò che fa passare
l'`INSERT … RETURNING` di un billing account a un operatore di un emittente
non di default: la policy `via_efba` chiama questo check *prima* che il
trigger AFTER abbia legato la riga. È esattamente il motivo per cui la regola
sta in un posto solo: se fosse rimasta qui in forma booleana, il RETURNING
sarebbe rimasto rotto o la si sarebbe corretta due volte.

---

### Impatto e Vantaggi

* usata dal ramo `CL` di `fn_search_soggetti_universale` e di
  `fn_get_search_detail`: è il punto dove il perimetro emittente entra nella
  ricerca;
* `STABLE`, e **non più `PARALLEL SAFE`** dal `20260913-02`: la delegata
  `fn_get_ba_emittente_sr_id` legge la GUC di sessione e chiama
  `fn_resolve_emittente_for_user`, che non è `SAFE` — tenere la marcatura qui
  sarebbe stata una dichiarazione falsa al planner, la stessa già tolta il
  18-08 su `fn_search_soggetti_universale`. Costo ~zero: la query dinamica
  della ricerca è paginata e un piano parallelo non lo ha mai scelto;
* il ramo «nessun autorizzato → false» resta **prima** di qualunque
  risoluzione. Senza, si finirebbe su `x = ANY(NULL)`, che vale `NULL`: e un
  `NULL` in un `WHERE` non nega — sparisce.
