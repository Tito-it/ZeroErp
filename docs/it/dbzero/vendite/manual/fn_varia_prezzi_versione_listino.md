## 📘 Documentazione Concettuale – Funzione `vendite.fn_varia_prezzi_versione_listino(p_listino_versione_id, p_variazione_pct, p_decimali, p_filtro_articoli, p_dry_run)`

> **Ultimo aggiornamento**: 15 novembre 2026

> 👀 **Vedi anche**
>
> [script.fn_check_listino_riga_scrivibile](/dbzero/script/manual/fn_check_listino_riga_scrivibile) — la regola ·
> [vendite.vw_listini_versioni_azioni](/dbzero/vendite/manual/vw_listini_versioni_azioni) — il pulsante ·
> [vendite.trgfn_listini_righe_guard_stato](/dbzero/vendite/manual/trgfn_listini_righe_guard_stato) — il guard delle righe ·
> [config.azioni_riga](/dbzero/config/manual/azioni_riga) — il registro

### 🎯 Scopo

**Il verbo «Variazione %» di una versione di listino.** Aumenta o diminuisce in percentuale i
prezzi delle righe attive della versione: tutte, o quelle degli articoli scelti. Con
`p_dry_run` mostra l'anteprima e non scrive niente. Si fa solo in bozza.

⭐ **Il gesto lo giudica la versione, non le righe che prende.** Un guard di riga scatta solo sulle
righe che si scrivono: una variazione che non ne prende nessuna, perché il filtro non trova
articoli o la versione non ha righe attive, non lo farebbe scattare. Il verbo chiede alla versione
prima di toccare le righe, quindi la risposta non dipende da quante righe ci sono.

### Il percorso

1. **I parametri**: versione, percentuale, decimali e `p_dry_run` obbligatori
   (`E_VENDITE_CHIAMATA_NON_VALIDA`).
2. **La versione, nel perimetro**, bloccata (`FOR UPDATE`) nel gesto vero: fra il controllo e la
   scrittura non si attiva. Non trovata o fuori perimetro: `E_VENDITE_LISTINO_VERSIONE_NOT_FOUND`.
3. **Prima ciò che vieta**, anche nell'anteprima: il primo motivo di
   [`script.fn_check_listino_riga_scrivibile`](/dbzero/script/manual/fn_check_listino_riga_scrivibile)
   della versione, senza riga, lo stesso che spegne il pulsante (versione chiusa, versione non in
   bozza). L'anteprima di un gesto vietato è vietata, con lo stesso codice.
4. **Gli intervalli**: la percentuale da −99 a 1000, i decimali dell'arrotondamento da 0 a 10,
   estremi compresi (`E_LISTINO_VARIAZIONE_FUORI_INTERVALLO`, col campo da correggere).
5. **Il prezzo nuovo** è il prezzo per (1 + percentuale / 100), arrotondato ai decimali scelti. Si
   calcola in un posto solo: l'anteprima lo restituisce, il gesto lo scrive. Un prezzo negativo lo
   rifiuta il vincolo della tabella.
6. **La traccia**: il gesto vero aggiunge a `meta.variazioni_percentuali[]` della versione una voce
   con la data, l'operatore (`app.current_user_id`), la percentuale, i decimali, le righe
   aggiornate e il filtro. Anche a righe zero: il gesto c'è stato.

Ritorna una riga per ogni riga presa, in ordine di codice articolo: la riga, l'articolo (id,
codice, descrizione), il prezzo di prima e quello nuovo. Nel gesto vero il prezzo nuovo è quello
salvato, alla scala della colonna.

### Il filtro

`p_filtro_articoli` è un elenco di articoli: `NULL` prende tutte le righe attive, un elenco vuoto
non ne prende nessuna.

### Nessuna porta

La traccia si scrive dopo il controllo, cioè solo in bozza, dove il guard della versione
(`vendite.trgfn_listini_versioni_guard_per_stato`) lascia cambiare tutto. Le righe passano dal loro
guard, che in bozza le lascia scrivere.

### Sicurezza

`SECURITY DEFINER` con `search_path` bloccato; il perimetro lo dice
`script.fn_scope_ef_whitelist_via_listino_versione`. Il permesso d'area resta al backend. EXECUTE
solo all'applicazione.

### Test

* `db/pgtap/vendite/test-listino-variazione-percentuale-v1.sql` — la regola anche a righe zero,
  nell'anteprima e nel gesto; parametri, intervalli, prezzi, traccia, forma, sicurezza e la marca
  spostata.

---

{% include-markdown "signature-core.md" %}
