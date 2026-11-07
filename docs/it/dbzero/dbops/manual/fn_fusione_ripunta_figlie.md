## 📘 Documentazione Concettuale – Funzione `dbops.fn_fusione_ripunta_figlie`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_fusione_figlie](/dbzero/dbops/funzioni/fn_fusione_figlie) — le tabelle che ripunta
> * [dbops.fn_fusione_righe_doppie](/dbzero/dbops/funzioni/fn_fusione_righe_doppie) — il controllo che fa prima di scrivere
> * [dbops.fn_admin_merge_comune](/dbzero/dbops/funzioni/fn_admin_merge_comune) — la fusione dei comuni
> * [dbops.fn_admin_merge_stradario](/dbzero/dbops/funzioni/fn_admin_merge_stradario) — la fusione delle vie

---

### 🎯 Scopo Principale

Sposta sulla destinazione **tutto ciò che riferiva l'origine**, quando due righe di una tabella si
fondono: una modifica per ogni tabella figlia, che porta le colonne della chiave esterna ai valori
della destinazione. È il passo comune alle fusioni di comuni e di vie.

---

### In due tempi

1. **Prima i doppi.** Chiede a `dbops.fn_fusione_righe_doppie` se qualche riga diventerebbe
   uguale a una che la destinazione ha già. Se ce n'è anche una, si ferma **prima di scrivere**
   con `E_MERGE_RIGHE_DOPPIE`, e mette nel dettaglio dell'errore il conteggio e l'elenco (le prime
   cento coppie). Non unisce niente da sola: chi fonde decide.
2. **Poi il ripuntamento**, figlia per figlia. Un doppio che il controllo non sapeva vedere (un
   indice su un'espressione) risponde allo stesso modo, `E_MERGE_RIGHE_DOPPIE`, con il nome del
   vincolo e il dettaglio di PostgreSQL. Il rifiuto annulla anche le figlie già ripuntate.

Ogni altro rifiuto di una figlia (il suo guard, un vincolo di controllo) arriva col suo codice.

Restituisce, per ogni figlia, quante righe ha ripuntato, anche zero.

---

### ⚠️ Non apre le porte delle figlie

Una figlia può proteggere la sua chiave esterna con un guard: gli indirizzi, per esempio, non
cambiano via fuori dalla manutenzione. Quale porta aprire lo sa la fusione che chiama, non questa
funzione: la fusione delle vie la apre attorno a questa chiamata e la richiude subito dopo.

---

### Test

`db/pgtap/dbops/test-fusioni-comune-stradario-v1.sql`, test 3-8, 15-18 (attraverso le due
fusioni) e 23, 24, 27, 28: l'indice su espressione intercettato alla scrittura, le figlie già
ripuntate che tornano indietro, le righe ripuntate per figlia, la chiave esterna di due colonne.

---

{% include-markdown "signature-core.md" %}
