## 📘 Documentazione Concettuale – Funzione `vendite.fn_rettifica_riga_listino(p_listino_riga_id, p_prezzo, p_motivo)`

> **Ultimo aggiornamento**: 15 novembre 2026

> 👀 **Vedi anche**
>
> [script.fn_check_listino_riga_rettificabile](/dbzero/script/manual/fn_check_listino_riga_rettificabile) — la regola ·
> [vendite.trgfn_listini_righe_guard_stato](/dbzero/vendite/manual/trgfn_listini_righe_guard_stato) — la porta ·
> [vendite.vw_listini_righe_azioni](/dbzero/vendite/manual/vw_listini_righe_azioni) — il pulsante ·
> [vendite.fn_programma_chiusura_versione_listino](/dbzero/vendite/manual/fn_programma_chiusura_versione_listino) — l'altra porta della versione

### 🎯 Scopo

**Il verbo «Rettifica» di una riga di listino.** Corregge, col motivo, il prezzo di una riga del
listino in uso, e ne lascia la traccia nella riga. È l'**unica** scrittura di una riga fuori dalla
bozza: in bozza la riga si modifica direttamente, per il resto si clona la versione.

### Il percorso

1. **La riga, nel perimetro**, bloccata (`FOR UPDATE`): un documento non può citarla fra il
   controllo e la scrittura. Non trovata o fuori perimetro: `E_VENDITE_LISTINO_RIGA_NOT_FOUND`.
2. **Prima ciò che vieta**: il primo motivo di
   [`script.fn_check_listino_riga_rettificabile`](/dbzero/script/manual/fn_check_listino_riga_rettificabile),
   sul campo `prezzo` (in bozza, chiusa, non in vigore, già usata).
3. **Il motivo**: obbligatorio, al più 500 caratteri
   (`E_RIGA_LISTINO_RETTIFICA_MOTIVO_OBBLIGATORIO`, campo `motivo`).
4. **Il prezzo e la traccia**: in `meta.rettifiche_controllate[]` si aggiunge una voce con la data,
   l'operatore (`app.current_user_id`), il prezzo di prima, quello nuovo e il motivo. Il prezzo
   zero è un prezzo; uno negativo lo rifiuta il vincolo della tabella.

Ritorna la riga, il prezzo di prima, quello nuovo e il motivo.

### La porta

Il guard delle righe rifiuta ogni scrittura di una versione non in bozza. Il verbo apre una porta
per **questa** riga (variabile di transazione `zeroerp.listino_riga_rettifica` = id della riga) e
la richiude, anche in errore; il guard la onora solo dal proprietario della tabella (il verbo è
`SECURITY DEFINER`) e solo se cambiano il prezzo e `meta`. Una scrittura diretta del prezzo, senza
il verbo, resta rifiutata: il motivo e la traccia non si saltano.

### Sicurezza

`SECURITY DEFINER` con `search_path` bloccato; il perimetro lo dice
`script.fn_scope_ef_whitelist_via_listino_versione`. Il permesso d'area resta al backend. EXECUTE
solo all'applicazione.

---

{% include-markdown "signature-core.md" %}
