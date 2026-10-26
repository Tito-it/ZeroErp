## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_offerte_commerciali_revisione()`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
> [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali)
> [config.stati_doc_offerte](/dbzero/config/tabelle/stati_doc_offerte)
> [config.stati_doc_offerte_transizioni](/dbzero/config/tabelle/stati_doc_offerte_transizioni)
>
> Funzioni correlate:
> [vendite.fn_offerta_proietta_stato_revisione](/dbzero/vendite/funzioni/fn_offerta_proietta_stato_revisione) ·
> [vendite.trgfn_offerte_commerciali_rientro_padre](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_rientro_padre) ·
> [vendite.trgfn_offerte_commerciali_guard_transizione](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_guard_transizione)
>
> Guida: [Il modello del documento di vendita](/guide/modello-documento-di-vendita) §5 (i passaggi di processo)

---

### 🎯 Scopo Principale

(rev 2026-05-24; ultima revisione 2026-10-26)

Quando nasce una revisione di un'offerta (rev.N+1), la revisione precedente (rev.N) passa
nello stato di **superamento** (`SUPERATA`). Questa funzione prende la **causa** — l'inserimento
di una revisione, da qualunque strada arrivi — e chiede alla proiezione
[`vendite.fn_offerta_proietta_stato_revisione`](/dbzero/vendite/funzioni/fn_offerta_proietta_stato_revisione)
di portare il padre nello stato che le sue revisioni vive dicono.

E' applicata dal trigger `trg_offerte_commerciali_z90_revisione_ins` (fase `_z90_`,
`AFTER INSERT ON vendite.offerte_commerciali`).

---

### Logica operativa

1. Se la riga inserita non ha `revisione_padre_id`, e' una prima revisione: niente da fare.
2. Altrimenti chiama la proiezione sul padre. La proiezione legge lo stato di superamento dal
   vocabolario (`is_superato`, esattamente uno) e lo scrive attraverso la porta
   (`script.fn_doc_scrivi_stato`); la matrice la giudica il guard di transizione del padre.

Fino al 2026-10-26 la funzione scriveva il padre con un aggiornamento suo: con la porta sulla
colonna di stato (lo stato si cambia solo dai verbi) quell'aggiornamento sarebbe rifiutato,
perche' il trigger gira come chi inserisce la revisione.

---

### Note operative

* La funzione non giudica lo stato del padre: se il padre non e' `EMESSA` (per esempio una
  revisione inserita su un padre in bozza, fuori da `vendite.fn_crea_revisione_offerta`, che lo
  rifiuta gia'), il superamento lo rifiuta la matrice con `E_OFFERTA_TRANSIZIONE_NON_AMMESSA`.
* L'inverso — il padre che torna emesso quando si annulla l'ultima revisione viva — lo chiede
  [`vendite.trgfn_offerte_commerciali_rientro_padre`](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_rientro_padre),
  alla stessa proiezione.

---

{% include-markdown "signature-core.md" %}

---
