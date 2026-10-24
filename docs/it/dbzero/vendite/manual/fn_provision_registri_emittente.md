## 📘 Documentazione Concettuale – Funzione `vendite.fn_provision_registri_emittente`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[vendite.fn_get_registro_documento](/dbzero/vendite/manual/fn_get_registro_documento)
>
Approfondimenti tabelle:
>
[vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)
> • [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
> • [vendite.famiglie_documento](/dbzero/vendite/manual/famiglie_documento)

---
### 🎯 Scopo Principale
(latest review 31-08-2026)

Dà a un emittente **i registri di numerazione che gli mancano**, uno per ogni
tipo di documento non fiscale: documento di trasporto, ordine, commessa, reso.

Non tocca quelli che ci sono già.

---

### Perché serve, e perché scatta da sé

Dal 31 agosto 2026 un documento non fiscale **non nasce** se il suo emittente non
ha il registro giusto. È il verso corretto — meglio fermarsi che consegnare un
numero preso dalla serie di un altro — ma ha una conseguenza precisa: **un
emittente nuovo nascerebbe incapace di produrre documenti**, e se ne accorgerebbe
la prima persona che prova a fare un documento di trasporto, con un errore che
parla di registri a chi stava spedendo della merce.

⭐ Per questo la creazione dei registri non è un passo da ricordarsi: si aggancia
alla **nascita dell'emittente** e alla sua **riattivazione**. Un emittente
spento e poi riacceso passa di nuovo di qui, perché nel frattempo può essere nato
un tipo di documento che allora non esisteva.

---

### 🔄 rev 2026-08-31 (sera) — i registri nascono già **formattati**

Un registro creato qui non nasce nudo: prende prefisso e numero di cifre dal
**default della sua famiglia** (`vendite.famiglie_documento`), che per la commessa
significa `CMM-` e nove cifre.

⛔ **Non è un abbellimento.** Dal 31 agosto 2026 i generatori leggono la forma
**solo** dal registro: un registro creato senza prefisso produce numeri **nudi**,
senza alcun errore. E questo è il punto in cui nascono i registri di ogni emittente
nuovo — cioè il momento in cui nessuno guarda.

⚠️ **La fonte è il catalogo delle famiglie, non quello dei formati**, e la
distinzione è costata un passo del cantiere: finché questa funzione leggeva da
`config.sistema_codici`, togliere di là le quattro righe l'avrebbe lasciata **senza
fonte**. Oggi legge dalla stessa tabella da cui legge la bonifica dei registri
monchi, così nascita e riparazione non possono raccontare due forme diverse.

---

### Ripetibile senza danni

Chiamarla due volte non crea doppioni e non tocca niente: guarda cosa manca e
aggiunge solo quello. È la proprietà che permette di appoggiarla a un evento
ripetibile senza doversi chiedere ogni volta «l'ho già fatto?».

---

### Cosa non fa, ed è voluto

* ~~non crea registri per le fatture~~ — **superato il 18-10-2026** (R-BE-14):
  l'emittente nasce anche col registro delle fatture **standard**, collegato a
  ogni coppia (tipo documento, natura) che non ha un registro. Serie e sezionali
  separati si configurano poi dal CRUD dei registri. Dettaglio in
  [`fn_provision_registri`](/dbzero/vendite/manual/fn_provision_registri);
* **non modifica** un registro esistente. Se qualcuno ha cambiato la serie o le
  regole di reset di un registro, quella è una decisione: non viene riscritta.

---

### Impatto e Vantaggi

* aprire un emittente nuovo non richiede più una lista di passi da ricordare:
  i suoi documenti funzionano dal primo minuto;
* il blocco «senza registro non nasce niente» resta severo dove serve — sulla
  configurazione fiscale — senza trasformarsi in un inciampo su tutto il resto.

---

### 🔄 rev 2026-09-01 — la regola non è più qui dentro

Da oggi questa funzione è un **involucro sottile**: la regola di come nasce un
registro — il codice, la descrizione, il reset, i default di forma presi dalla
famiglia — vive in
[`vendite.fn_provision_registri`](/dbzero/vendite/manual/fn_provision_registri).
Qui resta il **filtro**, e nient'altro.

⭐ **Perché.** È nata la gemella
[`fn_provision_registri_famiglia`](/dbzero/vendite/manual/fn_provision_registri_famiglia),
che fa la stessa cosa dall'altro lato: dà a una famiglia il suo registro su tutti
gli emittenti. La strada facile era copiare la query.

⚠️ Copiata, la prima correzione che ne tocca una sola produce **due registri
diversi per la stessa coppia** — e non si vede subito: si vede mesi dopo, su un
emittente solo, quando qualcuno nota un codice che non segue la regola degli
altri.

⛔ **La firma non è cambiata, ed è deliberato**: questa funzione la chiama un
trigger. Un parametro in più sarebbe stato un *overload*, non una modifica — il
trigger avrebbe continuato a chiamare la versione vecchia, con la regola vecchia
dentro.

⚠️ Il comportamento visibile è identico: stessi registri, stessi codici, stessa
idempotenza. Quello che cambia è **dove** si va a leggere la regola quando la si
deve correggere.
