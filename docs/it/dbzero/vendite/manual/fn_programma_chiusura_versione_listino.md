## 📘 Documentazione Concettuale – Funzione `vendite.fn_programma_chiusura_versione_listino(p_versione_id, p_valido_al)`

> **Ultimo aggiornamento**: 29 ottobre 2026

> 👀 **Vedi anche**
>
> [script.fn_check_versione_listino_chiudibile](/dbzero/script/funzioni/fn_check_versione_listino_chiudibile) ·
> [vendite.vw_listini_versioni_azioni](/dbzero/vendite/views/vw_listini_versioni_azioni) ·
> [vendite.fn_chiudi_versioni_listino_scadute](/dbzero/vendite/funzioni/fn_chiudi_versioni_listino_scadute)

### 🎯 Scopo
(29-10-2026 — brief `brief-modello-documento-vendita` §16.14, C-2 e C-3)

**Il verbo «Chiudi» di una versione di listino.** Fissa la fine della validità di una versione
attiva (la chiusura programmata), oppure la toglie (`p_valido_al` vuoto). Prende il posto della
modifica diretta della data che faceva il backend.

### Il percorso

1. La versione, bloccata per la durata dell'operazione, nel perimetro dell'utente
   (`script.fn_scope_ef_whitelist_via_listino_versione`). Non trovata o fuori perimetro:
   `E_VENDITE_LISTINO_VERSIONE_NOT_FOUND`.
2. Prima ciò che vieta: il primo motivo di
   [`script.fn_check_versione_listino_chiudibile`](/dbzero/script/funzioni/fn_check_versione_listino_chiudibile)
   (non attiva; fine nel passato), sul campo `valido_al`.
3. La nuova fine, con la «porta» aperta per questa versione: è il solo modo, insieme
   all'attivazione, di cambiare la fine di una versione attiva.

Restituisce la versione, la fine di prima e quella di adesso.

### Regole

* Lo stato non cambia: «chiusa» la scrive il job a fine validità
  ([`vendite.fn_chiudi_versioni_listino_scadute`](/dbzero/vendite/funzioni/fn_chiudi_versioni_listino_scadute)).
* Una fine prima dell'inizio la rifiuta il controllo comune delle date; togliere la chiusura
  quando dopo c'è già un'altra versione attiva lo rifiuta il vincolo di non sovrapposizione.
* Gira come proprietario della tabella (`SECURITY DEFINER`, dal 29-10-2026): serve per aprire la
  porta. Il perimetro lo controlla nella ricerca della versione, come l'attivazione. Il permesso
  d'area lo chiede il backend.
* Una modifica diretta della fine di una versione attiva la rifiuta la tabella
  (`E_LISTINO_VERSIONE_FINE_SOLO_DAL_VERBO`, il
  [guard per stato](/dbzero/vendite/funzioni/trgfn_listini_versioni_guard_per_stato)).

### 🧪 Il presidio

`db/pgtap/vendite/test-fn-chiudi-clona-versione-listino-v1.sql`.

---

{% include-markdown "signature-core.md" %}
