## 📘 Documentazione Concettuale – Funzione `script.fn_check_legame_distinta_chiudibile`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [vendite.fn_prezzi_legame_oltre_la_fine](/dbzero/vendite/funzioni/fn_prezzi_legame_oltre_la_fine) — i prezzi da cui legge
> * [catalogo.fn_chiudi_legame_distinta](/dbzero/catalogo/funzioni/fn_chiudi_legame_distinta) — il verbo che la chiama
> * [catalogo.trgfn_articoli_componenti_block_modifica_struttura](/dbzero/catalogo/funzioni/trgfn_articoli_componenti_block_modifica_struttura) — il guard che la chiama
> * [script.fn_raise_primo_motivo_se_presente](/dbzero/script/funzioni/fn_raise_primo_motivo_se_presente) — come i chiamanti sollevano il primo motivo

---

### 🎯 Scopo Principale

Dice **perché un legame di distinta non si chiude a una data**, per via dei suoi prezzi bundle. Restituisce un
array di motivi; vuoto vuol dire che, per i prezzi, il legame si chiude (con la conferma, se ce ne sono da chiudere
o da togliere). Non solleva: il primo motivo lo sollevano il guard della distinta e il verbo di chiusura, sul campo
`valido_al`.

---

### I motivi, nell'ordine

1. **`E_BOM_CHIUSURA_PREZZI_ALTRE_AZIENDE`** — il legame ha prezzi da chiudere in listini che chi chiude non vede.
   La distinta è comune a tutte le aziende, i listini no: chi non può toccare un listino non lo tocca nemmeno dalla
   distinta. Valori: componente, kit, numero di prezzi (non quali).
2. **`E_BOM_CHIUSURA_PRIMA_DEI_PREZZI`** — un prezzo di una versione non in bozza comincia dopo la fine: non si
   accorcia e non si cancella. Valori: componente, kit, prima fine ammessa, cioè l'inizio più tardo di quei
   prezzi; il dettaglio la porta anche come data (`valido_al_min`).

Legame assente o data vuota: nessun motivo.

---

### Test

* `db/pgtap/catalogo/test-chiudi-legame-con-prezzi-v1.sql` — nessun motivo, la prima fine ammessa, i prezzi di
  un'altra azienda.

---

### Note di migrazione

* 2026-11-09 — nasce con il verbo di chiusura del legame (brief-db-revisione-catalogo, giro 3).

---

{% include-markdown "signature-core.md" %}
