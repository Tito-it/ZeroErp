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

### Ripetibile senza danni

Chiamarla due volte non crea doppioni e non tocca niente: guarda cosa manca e
aggiunge solo quello. È la proprietà che permette di appoggiarla a un evento
ripetibile senza doversi chiedere ogni volta «l'ho già fatto?».

---

### Cosa non fa, ed è voluto

* **non crea registri per le fatture.** Quelli sono sezionali fiscali: hanno
  serie, regole di reset e collegamenti al tipo di documento che una scelta
  automatica non può indovinare. Si configurano a mano, ed è giusto così;
* **non modifica** un registro esistente. Se qualcuno ha cambiato la serie o le
  regole di reset di un registro, quella è una decisione: non viene riscritta.

---

### Impatto e Vantaggi

* aprire un emittente nuovo non richiede più una lista di passi da ricordare:
  i suoi documenti funzionano dal primo minuto;
* il blocco «senza registro non nasce niente» resta severo dove serve — sulla
  configurazione fiscale — senza trasformarsi in un inciampo su tutto il resto.
