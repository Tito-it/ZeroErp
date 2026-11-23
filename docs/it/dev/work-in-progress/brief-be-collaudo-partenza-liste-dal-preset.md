# Brief BE/FE — Il collaudo a video: le liste partono dall'ordinamento e dalla misura del preset

## ⏭️ Chi riparte — aggiornato al 2026-11-23

**Riparte: il team BE/FE**, con il copione del collaudo e poi il collaudo a video di Tid. Aperto, non iniziato.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | team BE/FE | Il copione: le superfici da aprire e cosa deve succedere su ognuna | §2 | — |
| 2 | Tid | Il collaudo a video, col copione | §2 | 1 |
| 3 | team BE/FE | Le correzioni che il collaudo trova; poi l'archiviazione in `work-done/` | §3 | 2 |

**Decisioni aperte di Tid:** nessuna. Niente da committare oltre a questo brief.

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-11-23, alla chiusura di
> [brief-db-revisione-ui](../work-done/2026/brief-db-revisione-ui.md). **A chi:** team BE/FE e Tid.
> **Origine:** il residuo di quel brief, righe 8-ter e 9: il controllo a video di BE29 e del residuo di BE25 (2).
> Deciso da Tid il 2026-11-23: passa a un brief BE.
> **Brief vicini verificati:** [sviluppo-personalizzazioni-liste_def](sviluppo-personalizzazioni-liste_def.md) tiene
> funzionalità nuove delle liste (viste nominate, condivisione), non il collaudo di ciò che è fatto;
> [piano-be-fe-endpoint-senza-porta](piano-be-fe-endpoint-senza-porta.md) cita una lista di `ui` solo come fatto.
> Nessuno dei due copre questo collaudo.
> **Guide verificate:** [configurazione-liste](../../guide/configurazione-liste.md): coerente. Descrive la partenza della
> lista dal preset (ordinamento e misura), ed è ciò che il collaudo guarda.

## 1. Che cosa si collauda

Il 2026-11-22 il team BE/FE ha portato la partenza delle liste configurabili al preset:

* **BE25 (2)**: quando la richiesta non porta `order_by`, il BE ordina con l'ordinamento della configurazione risolta
  dell'utente, e la risposta dice l'ordinamento applicato; il FE accende l'intestazione da lì;
* **BE10**: una lista configurabile chiamata senza `limit` prende la misura risolta dal DB (`ui.fn_misura_lista`);
* **BE29**: ritirate le copie FE dell'ordinamento di partenza (`orderBy` degli store, `defaultSortField` dei componenti)
  sulle liste a cui il seed dà il preset (U40), e con il residuo di BE25 (2) su altre 18 liste e 21 superfici di
  catalogo.

Il dettaglio, con l'elenco delle superfici, sta nelle voci BE10, BE25 (2) e BE29 di §6 del brief archiviato. Le prove
automatiche sono verdi (suite BE, vitest). Nessun test, però, apre le superfici a video: un'intestazione che non si
accende, o una lista che parte nell'ordine sbagliato, non fa fallire niente.

## 2. Il copione (da scrivere, team BE/FE)

Per ogni superficie toccata da BE29 e dal residuo di BE25 (2): aprirla senza preferenza salvata e vedere che

* le righe arrivano nell'ordine dell'`ordinamento_default` del preset;
* l'intestazione della colonna di partenza è accesa, col verso giusto;
* il numero di righe per pagina è la misura del preset, o il default `PAGINA` del catalogo;
* un clic sull'intestazione riordina, e alla riapertura la lista riparte dal preset (Q39 (b): il clic non si ricorda);
* sulle liste di BE30 (`magazzino.disponibilita`, `magazzino.disponibilita_articoli`, `magazzino.inventario_piano`,
  `vendite.resi_da_accreditare`, `vendite.resi_da_riconsegnare`) lo spareggio segue i criteri del repository.

## 3. Alla chiusura

Il brief va in `work-done/` quando il collaudo è fatto e le correzioni che ha trovato sono chiuse.
