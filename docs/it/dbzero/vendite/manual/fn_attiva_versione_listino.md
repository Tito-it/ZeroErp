## 📘 Documentazione Concettuale – Funzione `vendite.fn_attiva_versione_listino(p_versione_id)`

> 👀 **Vedi anche**
>
> [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni) ·
> [vendite.fn_versioni_listino_da_chiudere](/dbzero/vendite/funzioni/fn_versioni_listino_da_chiudere) ·
> [script.fn_check_versione_listino_attivabile](/dbzero/script/funzioni/fn_check_versione_listino_attivabile) ·
> [Il modello del documento di vendita](/guide/modello-documento-di-vendita)

### 🎯 Scopo
(28-10-2026 — brief `brief-modello-documento-vendita` §16, L-3 e L-4)

**Il verbo dell'attivazione di una versione di listino** (BOZZA → ATTIVA): mette i suoi prezzi
in uso e chiude le versioni precedenti che si sovrappongono, in una transazione.

### In ordine

1. La versione, presa `FOR UPDATE`, nel perimetro dell'utente
   (`script.fn_scope_ef_whitelist_via_listino_versione`; la funzione è `SECURITY DEFINER`).
   Fuori perimetro o inesistente: `E_VENDITE_LISTINO_VERSIONE_NOT_FOUND`.
2. La prima riga comune (`script.fn_guard_passaggio`): già attiva → `E_DOC_GIA_NELLO_STATO`;
   l'azione `attiva_listino` del passaggio.
3. Prima ciò che vieta: il primo motivo di
   [script.fn_check_versione_listino_attivabile](/dbzero/script/funzioni/fn_check_versione_listino_attivabile)
   (`E_LISTINO_VERSIONE_SPENTA`, `E_LISTINO_VERSIONE_SENZA_RIGHE`), prima di toccare altre versioni.
4. Le versioni attive precedenti che si sovrappongono prendono la fine al giorno prima della
   decorrenza nuova, dal lettore
   [vendite.fn_versioni_listino_da_chiudere](/dbzero/vendite/funzioni/fn_versioni_listino_da_chiudere)
   (lo stesso dell'anteprima: quello che si mostra è quello che si fa).
5. Lo stato ATTIVA dalla scrittura comune (`script.fn_doc_scrivi_stato`), attraverso la porta.

Ritorna la versione, lo stato di prima e quello nuovo (codici) e quante versioni ha chiuso.

---

{% include-markdown "signature-core.md" %}
