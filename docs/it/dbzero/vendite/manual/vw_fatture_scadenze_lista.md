## 📘 Documentazione Concettuale – Vista `vendite.vw_fatture_scadenze_lista`

> 👀 **Vedi anche**
>
> • [vendite.fatture_scadenze](/dbzero/vendite/tabelle/fatture_scadenze) — la tabella delle rate, con le sue due policy (operatore e portale)
> • [vendite.vw_fatture_lista](/dbzero/vendite/views/vw_fatture_lista) — la sorella del documento, con gli stessi nomi canonici
> • [pagamenti.fn_get_saldi_rate](/dbzero/pagamenti/funzioni/fn_get_saldi_rate) e [pagamenti.vw_saldi_rate](/dbzero/pagamenti/views/vw_saldi_rate) — **i saldi**, che qui non ci sono
> • **Brief:** [brief-db-distinta-ricerca-rate](/dev/work-in-progress/brief-db-distinta-ricerca-rate) §4-bis.3 (P-2)

---

### 🎯 Scopo Principale

(rev 2026-09-17)

La vista d'**identità** delle rate: **una riga per rata** di
`vendite.fatture_scadenze`, col suo documento (numero parlante dalla sede unica
`fn_numero_documento_fattura`, registro, date, natura, tipo, stato, totali,
valuta), il cliente e l'emittente. È la sorgente della lista `pagamenti.rate` e
del picker delle rate della distinta (D19-c), e domani dello scadenzario e del
portale.

### ⛔ Nessun saldo, e nessuna colonna derivata dal saldo

Il residuo è di `pagamenti` e vive nel nucleo `fn_get_saldi_rate`: chi legge una
pagina chiama il nucleo con gli id della pagina; chi legge tutto affianca
`vw_saldi_rate`. «Scaduta» e «insoluta» sono derivate dal residuo, e non stanno
qui.

### Regole principali

* La chiave si chiama **`scadenza_id`**: è il vocabolario di `pagamenti`
  (`vw_rate_fuori_capienza`, il contesto di `E_RATA_NON_TROVATA`, il
  `modelValue` di `RataSelect`). `<ListaConfigurabile>` ha `dataKey` di default
  `id`: il frontend passa `dataKey="scadenza_id"`.
* `numero` (il contatore) resta accanto a `numero_documento`, perché il picker
  filtra per numero **esatto** (101 non porta 1010); `numero_documento` è
  `NULL` sulla non numerata, mai la stringa vuota.
* `security_invoker=on`: la vista non filtra e non fa scope, a mordere è la RLS
  di `fatture_scadenze` — l'operatore via whitelist emittente, il cliente del
  portale via proprietà del billing account, entrambe attraverso la testata.
* **Due** JOIN interni dimostrabili (la testata, la natura del documento: FK
  `NOT NULL`, e la policy della rata è lo stesso `EXISTS` sulla testata), tutto
  il resto è `LEFT`: una rata su una bozza senza stato o numero compare senza,
  non sparisce.
* I JOIN sono **scritti**, non ereditati da `vw_fatture_lista`: impilarsi su
  quella vista trascina la CTE ricorsiva del lineage in ogni lettura delle rate.

### Presidio

`db/pgtap/vendite/test-vw-fatture-scadenze-lista-v1.sql` (8): reloption, nomi
canonici, nessun saldo, nessun fan-out, due soli INNER nel corpo, la rata sulla
bozza prima e dopo la numerazione, il perimetro uguale a quello della tabella.

{% include-markdown "signature-core.md" %}
