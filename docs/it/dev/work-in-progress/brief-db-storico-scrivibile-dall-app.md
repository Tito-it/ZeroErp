# Brief DB — lo schema `storico` scrivibile dall'app

> **⏭️ Chi riparte — aggiornato al 2026-11-27**
>
> **Riparte: nessuno, per ora.** Il brief è **aperto e non iniziato**: l'ha aperto D-AL **a** (Tid, 2026-11-27) del
> giro 10-quater di [brief-db-porte-aperte-dalla-sola-guc](../work-done/2026/brief-db-porte-aperte-dalla-sola-guc.md) §15.4, che ha
> tenuto il tema fuori da quel giro. Parte quando Tid lo mette in coda.
>
> | # | Chi | Che cosa | Dove | Aspetta |
> | --- | --- | --- | --- | --- |
> | 1 | Tid | quando partire | — | — |
> | 2 | team DB | analisi sul modello: chi deve poter scrivere lo storico, e con quale privilegio scrive il trigger | §3 | 1 |
> | 3 | Tid | le decisioni dell'analisi, il via | §4 | 2 |
>
> Decisioni aperte di Tid: quando partire; le altre le scrive l'analisi (§4). Niente da committare oltre a questo file.
>
> **Brief vicini verificati** (2026-11-27, ricerca su `storico`, `trgfn_storico_generic`, `fn_ensure_storico_table`,
> `storico_set_storicizza` in `work-in-progress/`):
> * `brief-db-porte-aperte-dalla-sola-guc`: chiude le tabelle dei permessi in sola lettura per l'app, non lo storico;
>   da lì nasce questo brief (D-AL **a**). Non basta: il tema è di tutto lo schema.
> * `brief-db-revisione-anagrafiche` (§18, giro 1): ha reso continuo lo storico di indirizzi, civici e vie, e lascia
>   un debito «per la revisione di quello schema»: le pagine `storico/manual/indirizzi.md`, `indirizzi_dettaglio.md`,
>   `stradario.md` sono nel formato vecchio e dicono cose non vere (il trigger solleva l'eccezione, non la logga).
>   Quel debito è di questo schema: si riprende qui quando il brief parte. Il brief è di un'altra sessione e non si tocca.
> * `valutazione-modello-di-dominio-db`: il tipo di `data_insert` delle shadow, già chiuso (`20260920-03`, `20260921-01`).
>   Non riguarda i privilegi.
> * `integrazione-ai-sviluppo-v2`: un campo `ai_initiated` nelle tabelle `storico.*`, sviluppo futuro. Non riguarda i
>   privilegi, ma tocca le stesse tabelle: si rilegge all'analisi.
>
> **Guide verificate** (`scripts/guide_coinvolte.py --oggetti script.trgfn_storico_generic dbops.fn_ensure_storico_table
> config.storico_set_storicizza`, 2026-11-27). Esito preliminare, da confermare all'analisi:
> * `storicizzazione-tabelle`: dice che l'applicazione non cancella mai una versione, «è un privilegio, non una
>   convenzione» (manca il `DELETE`: **coerente**). Sull'`UPDATE` non dice niente: da rileggere.
> * nota di dominio `dbzero/storico/_tabelle-storico`: «append-only per destinazione d'uso. Le righe non si
>   aggiornano e non si cancellano». L'`UPDATE` concesso all'app rende l'archivio riscrivibile: la nota descrive l'uso,
>   il privilegio non lo garantisce. **Da decidere** se è la nota che va corretta o il privilegio.
> * `audit-e-tracciabilita`, `automazione-db`, `gestione-degli-indirizzi`, `catasto-delle-istanze`,
>   `generazione-cliente`: nominano il trigger o il registro; si rileggono all'analisi.

## 1. Il problema, sul modello

Lo storico è l'archivio delle versioni precedenti: vale come prova di chi ha cambiato cosa e quando, e l'audit dei
permessi lo legge (`architettura-permessi-e-autorizzazioni` §13.2). Un archivio che chi lo produce può riscrivere non
prova niente.

Oggi lo scrive il trigger generico `script.trgfn_storico_generic`, agganciato a ogni tabella madre. Il trigger è
`INVOKER`: scrive coi privilegi di chi modifica la tabella madre, cioè quasi sempre l'app. Per questo l'app ha
`INSERT` e `UPDATE` sulle tabelle di `storico`: senza, la modifica della tabella madre si fermerebbe. Con quei
privilegi, però, l'app può anche scrivere nello storico **direttamente**, senza il trigger: aggiungere una versione
che non c'è stata, o cambiarne una vera.

Il modello «una scrittura = un verbo» chiude le tabelle che danno poteri. Lo storico non dà poteri, ma è la traccia
su cui si controllano: è un caso diverso, e non si chiude con la regola dei giri delle porte.

## 2. Fatti datati

* 2026-11-26 (catalogo di dbdev, analisi del giro 10-quater): l'app ha `INSERT` e `UPDATE` su **116 tabelle di
  `storico` su 116**, nessun `DELETE`. Fra queste lo storico di override, profili, legami e scope (otto tabelle
  dell'accesso).
* `script.trgfn_storico_generic` è `INVOKER`.

## 3. L'analisi da fare

* Chi deve poter scrivere lo storico: solo il trigger? Anche altri (backfill, `fn_storico_backfill_scope`, la sync di
  `storico_set_storicizza`, i lavori notturni)?
* Con quale privilegio scrive il trigger, se l'app non ha più `INSERT`/`UPDATE`: una funzione DEFINER chiamata dal
  trigger, il trigger stesso DEFINER, o un'altra strada. Che cosa resta vero di `user_insert = CURRENT_USER` (la
  colonna che dice chi ha generato la versione) quando scrive il proprietario.
* Perché serve l'`UPDATE`: se il trigger chiude la versione aperta (la data di fine), è un `UPDATE` legittimo; se no,
  l'`UPDATE` si toglie e basta.
* Le tabelle che la madre ha già chiuse in sola lettura (giri 10-bis e 10-quater): i verbi DEFINER scrivono già come
  proprietario, quindi lì l'app non ha bisogno dei privilegi sullo storico.
* La nota di dominio e la guida: che cosa promettono, e se lo promettono come privilegio o come uso.
* Il debito di `brief-db-revisione-anagrafiche` sulle tre pagine `manual/` delle shadow.

## 4. Le decisioni attese

Le scrive l'analisi. Fra quelle prevedibili: chi scrive lo storico; il privilegio del trigger; se lo schema intero
diventa in sola lettura per l'app.

## Piano

- [ ] Quando partire (Tid)
- [ ] Analisi sul modello e sul catalogo, guide (§3)
- [ ] Le decisioni e il via (Tid)

## Registro

| Data | Chi | Che cosa |
| --- | --- | --- |
| 2026-11-27 | DB | Brief aperto, non iniziato, da D-AL **a** (Tid) del giro 10-quater di `brief-db-porte-aperte-dalla-sola-guc` |
