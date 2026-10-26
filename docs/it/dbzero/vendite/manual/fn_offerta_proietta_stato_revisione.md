## 📘 Documentazione Concettuale – Funzione `vendite.fn_offerta_proietta_stato_revisione(bigint)`

> 👀 **Vedi anche**
>
> [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali) ·
> [config.stati_doc_offerte](/dbzero/config/tabelle/stati_doc_offerte) ·
> [vendite.trgfn_offerte_commerciali_revisione](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_revisione) ·
> [vendite.trgfn_offerte_commerciali_rientro_padre](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_rientro_padre) ·
> guida [Il modello del documento di vendita](/guide/modello-documento-di-vendita) §5 (i passaggi di processo)

### 🎯 Scopo
(26-10-2026 — brief `brief-modello-documento-vendita` §13, giro dell'offerta)

**I passaggi di processo della revisione.** Lo stato di un'offerta che ha revisioni è la
conseguenza delle sue revisioni **vive** (non annullate), non una scelta di chi scrive:

| L'offerta | Le sue revisioni | Diventa |
| --- | --- | --- |
| non superata | almeno una viva | superata (lo stato `is_superato` del vocabolario) |
| superata | nessuna viva | emessa (lo stato d'emissione del vocabolario) |
| altrimenti | | resta com'è |

È la gemella delle proiezioni del preventivo
([`vendite.fn_preventivo_proietta_stato_smistamento`](/dbzero/vendite/funzioni/fn_preventivo_proietta_stato_smistamento))
e dell'ordine.

### Regole

* Scrive lo stato attraverso la porta, con la sola scrittura comune: i due passaggi sono di
  processo e nessun operatore li chiede.
* La **matrice** la giudica il guard di transizione: un superamento chiesto da uno stato che la
  matrice non ammette (una revisione inserita su un padre in bozza) è rifiutato
  (`E_OFFERTA_TRANSIZIONE_NON_AMMESSA`). La regola «si torna emessi solo senza una revisione
  viva» resta anche nel guard, per chiunque scriva.
* Il vocabolario deve dichiarare esattamente uno stato di superamento e uno d'emissione;
  altrimenti `E_CONFIG_MANCANTE`.
* Gira coi diritti del proprietario: lo stato dipende dalle revisioni, non da ciò che vede chi
  le crea o le annulla.

### Chi la chiama

I due trigger della testata, che prendono la causa su ogni strada: la nascita di una revisione
([`vendite.trgfn_offerte_commerciali_revisione`](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_revisione))
e l'annullo di una revisione
([`vendite.trgfn_offerte_commerciali_rientro_padre`](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_rientro_padre)).
L'annullo che fa tornare emessa la revisione precedente si conferma prima, col verbo
[`vendite.fn_annulla_offerta`](/dbzero/vendite/funzioni/fn_annulla_offerta).
