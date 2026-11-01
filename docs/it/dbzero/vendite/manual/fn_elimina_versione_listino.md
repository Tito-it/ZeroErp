## 📘 Documentazione Concettuale – Funzione `vendite.fn_elimina_versione_listino(p_versione_id)`

> 👀 **Vedi anche**
>
> [script.fn_check_versione_listino_eliminabile](/dbzero/script/funzioni/fn_check_versione_listino_eliminabile) ·
> [vendite.vw_listini_versioni_azioni](/dbzero/vendite/views/vw_listini_versioni_azioni) ·
> [vendite.fn_attiva_versione_listino](/dbzero/vendite/funzioni/fn_attiva_versione_listino)

### 🎯 Scopo
(28-10-2026 — brief `brief-modello-documento-vendita` §16.11, opzione a; rivisto il 1-11-2026)

**Il verbo dell'eliminazione di una versione di listino.** Elimina una versione in bozza con i
suoi prezzi (righe e componenti dei compositi) e i suoi kit, in una sola transazione. Prende il posto dei tre
DELETE che il backend faceva da sé.

### Il percorso

1. La versione, bloccata per la durata dell'operazione: chi intanto la cita o le aggiunge righe
   aspetta. Non trovata o fuori perimetro: `E_VENDITE_LISTINO_VERSIONE_NOT_FOUND`.
2. Prima ciò che vieta: il primo motivo di
   [`script.fn_check_versione_listino_eliminabile`](/dbzero/script/funzioni/fn_check_versione_listino_eliminabile)
   (non in bozza; usata da un documento), lo stesso che il pulsante «Elimina» mostra.
3. Kit ([`vendite.listini_kit`](/dbzero/vendite/manual/listini_kit)), componenti, righe, versione.

Restituisce la versione e quante righe e quanti componenti ha cancellato.

### Regole

* Gira con i permessi di chi la chiama (`SECURITY INVOKER`): vede e cancella solo nel suo
  perimetro. Il permesso d'area lo chiede il backend.
* I guard delle quattro tabelle restano la difesa di chi scrive a mano: tutti accettano il DELETE in
  bozza e lo rifiutano fuori.

### 🧪 Il presidio

`db/pgtap/vendite/test-fn-elimina-versione-listino-v1.sql`.

---

{% include-markdown "signature-core.md" %}
