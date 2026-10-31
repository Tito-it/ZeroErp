## 📘 Documentazione Concettuale – Funzione `script.fn_check_preventivo_accettabile(bigint, date)`

> 👀 **Vedi anche**
>
> [script.fn_check_preventivo_emettibile](/dbzero/script/funzioni/fn_check_preventivo_emettibile) ·
> [script.fn_check_prezzi_autorizzati](/dbzero/script/funzioni/fn_check_prezzi_autorizzati) ·
> [vendite.trgfn_preventivi_guard_transizione](/dbzero/vendite/funzioni/trgfn_preventivi_guard_transizione) ·
> [script.fn_available_actions_preventivo](/dbzero/script/funzioni/fn_available_actions_preventivo) ·
> guida [Gestione preventivi](/guide/gestione-preventivi) §3.1

### 🎯 Scopo
(31-10-2026 — brief `brief-db-scadenza-preventivi` §8.1, D-2; decisione E-2 di Tid)

**Che cosa impedisce di accettare un preventivo.** Una funzione pura: non solleva e non
scrive, elenca i motivi. La leggono in due: il guard di transizione, che entrando in
`ACCETTATO` solleva il primo, e la capability, che spegne «Accetta» e mostra il motivo.
Bottone e database non possono dire due cose diverse.

### I motivi, in ordine

| # | Motivo | Codice | Quando |
| --- | --- | --- | --- |
| 1 | La validità è finita | `E_PREV_VALIDITA_SCADUTA` | «Valido al» è prima di oggi |
| 2 | Un prezzo non autorizzato | dai motivi di `script.fn_check_prezzi_autorizzati` | un prezzo in attesa o rifiutato, su righe o componenti attivi |

* **«Valido al» è l'ultimo giorno valido**: il giorno stesso si accetta, dal giorno dopo no.
  È lo stesso confronto del job delle scadenze.
* **Senza «Valido al» il preventivo non scade.**
* La regola non aspetta il job: fra la fine della validità e la sua corsa il preventivo è
  ancora `EMESSO`, e non si accetta lo stesso. La strada per riproporlo è la revisione.

### La data entra come parametro

Il guard è un trigger `BEFORE ROW` sulla testata che sta cambiando: rileggere «Valido al»
dalla tabella darebbe la riga di prima. Per questo la data è un argomento, senza valore di
default: il guard passa quella della riga nuova, la capability quella della testata.

### Ritorna

`[]` se il preventivo si può accettare; altrimenti un array ordinato di
`{codice, reason, reason_key, dettaglio, valori}`. Un preventivo che non esiste dà `[]`
(decide il chiamante); un id mancante o non positivo, `E_PARAMETRO_INVALIDO`.
