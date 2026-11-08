## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_sorgente_documento_ref`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il catalogo: tabella, chiave ed etichetta di ogni tipo
>
> Approfondimento viste:
>
> * [vendite.vw_dash_competenza_gruppi](/dbzero/vendite/views/vw_dash_competenza_gruppi) — il riferimento leggibile di ogni gruppo fatturabile
>
> Approfondimento funzioni:
>
> * [script.fn_sorgente_documento_da_chiave](/dbzero/script/funzioni/fn_sorgente_documento_da_chiave) — il ponte per le chiavi in testo, a cui questa funzione passa
> * [script.fn_sorgente_documento](/dbzero/script/funzioni/fn_sorgente_documento) — il BB che risolve, per chi ha le colonne tipizzate
> * [vendite.fn_riferimento_gruppo_fatturabile](/dbzero/vendite/funzioni/fn_riferimento_gruppo_fatturabile) — il riferimento di un gruppo, dalla sua chiave
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — §5, le chiavi in testo

---

### 🎯 Scopo Principale

Dice **qual è il documento di origine** quando la chiave del documento è **testo**: l'id su cui
il frontend costruisce l'azione «apri documento sorgente» (`documento_id`) e il numero che
l'operatore **legge** (`documento_numero`: `DDT0010839`, `ORD0000227`, `PRV0000081`), in una
sola lettura.

---

### Chi la usa: le chiavi che sono testo per costruzione

Le tabelle scrivono la provenienza nelle colonne tipizzate (`sorgente_id` / `sorgente_uid`), e
chi le legge usa il BB che risolve, `script.fn_sorgente_documento`. Questa funzione serve dove
la chiave **è testo per costruzione**: la chiave di un gruppo fatturabile, che porta l'uid del
documento in testo anche per i tipi a chiave `id`. La leggono il riferimento leggibile dei gruppi
(`vendite.vw_dash_competenza_gruppi`) e `vendite.fn_riferimento_gruppo_fatturabile`, che la
compone con lo split della chiave del gruppo.

Non ha logica propria: passa al ponte `script.fn_sorgente_documento_da_chiave`, che riconosce la
chiave in forma **canonica** (`id::text` o `uuid::text`, con `script.fn_sorgente_chiave_id` /
`script.fn_sorgente_chiave_uuid`) e risolve col BB che risolve. Stessa regola per tutti i
lettori: una chiave scritta in una forma diversa (maiuscole, zeri davanti, spazi) **non si
risolve**, e un numero troppo grande non fa fallire la lista, lascia la riga vuota.

---

### ⭐ L'etichetta si **dichiara**, non si indovina

La colonna che porta il numero leggibile arriva da `config.sorgenti.label_selector`, gemella di
`key_selector`, e non è uniforme: `numero` per i documenti numerati (preventivo, ordine, bolla,
contratto, fattura, reso), `codice` per offerta e commessa, nessuna per i tipi che un numero non
ce l'hanno (i consumi). `label_selector` vuoto ⇒ `documento_numero` è `NULL` e basta: **non** è
un errore e **non** spegne `documento_id`.

> ⚠️ Un `COALESCE(numero, codice)` funzionerebbe **oggi** e diventerebbe una colonna vuota **in
> silenzio** alla terza convenzione: è lo stesso *«non si indovina»* che vale per la chiave.

---

### Le cose da sapere

1. ⚠️ **Non solleva mai.** Una sorgente irrisolvibile è il caso **normale**: le voci manuali, gli
   **oneri** e le **rettifiche** un documento a monte non ce l'hanno per progetto. Qui si risponde
   a una **lista**, e l'esito giusto è l'azione «apri» che sparisce: *fail-closed dove si scrive,
   silenzioso dove si guarda.*
2. ⭐ **Restituisce sempre una riga**, anche tutta a `NULL`. Una funzione che a volte torna zero
   righe funziona con `LEFT JOIN LATERAL … ON TRUE` e **cancella la riga chiamante** il giorno in
   cui qualcuno scrive `CROSS JOIN LATERAL` per distrazione: una riga sempre presente rende
   quell'errore impossibile.
3. ⚠️ **`SECURITY INVOKER`**: le tabelle di destinazione hanno la RLS operatori. `NULL` significa
   «non risolvibile **o** non visibile a chi chiede», **non** «non esiste».
4. ⚠️ **Se il catalogo mente, cade tutto — di proposito.** Un `label_selector` che nomina una
   colonna inesistente fa cadere la riga intera, id compreso: un ripiego che salvasse l'id e
   perdesse il solo numero renderebbe il refuso più difficile da vedere. Così sparisce anche
   l'azione «apri», e qualcuno lo nota.

---

### Test

* `db/pgtap/vendite/test-vw-dash-competenza-gruppi-riferimento-sorgente-v1.sql` e
  `db/pgtap/vendite/test-riferimento-gruppo-fatturabile-v1.sql` — il riferimento dei gruppi.
* `db/pgtap/script/test-sorgente-documento-e-chiave-v1.sql` — il ponte e il BB che risolve.

---

### Note di migrazione

* 2026-08-20 — nasce al posto di `vendite.fn_get_sorgente_documento_id`, con id e numero in una
  sola lettura e l'etichetta da `config.sorgenti.label_selector`
  (brief-design-note-credito-resi §40.1.4).
* 2026-10-05 — la chiave si riconosce con `script.fn_sorgente_chiave_uuid` / `_id`.
* 2026-11-06 — il corpo passa al ponte `script.fn_sorgente_documento_da_chiave`
  (brief-db-sorgente-documento-e-riga).
* 2026-11-07 — la lista delle attività di commessa e l'annullo di una riga di commessa, che la
  chiamavano sulla chiave testuale `sorgente_uid` della riga, passano al BB che risolve sulle
  colonne tipizzate. Restano i lettori delle chiavi che sono testo per costruzione
  (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
