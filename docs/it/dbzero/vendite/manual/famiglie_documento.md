## 📘 Documentazione Concettuale – Tabella `vendite.famiglie_documento`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)
> • [config.sistema_codici](/dbzero/config/tabelle/sistema_codici)
>
**Approfondimento funzioni:**
>
• [vendite.fn_get_registro_documento](/dbzero/vendite/manual/fn_get_registro_documento)
> • [anagrafiche.fn_ba_ha_storia_emittente](/dbzero/anagrafiche/manual/fn_ba_ha_storia_emittente)

---
### 🎯 Scopo Principale
(latest review 31-08-2026)

È l'**elenco dei tipi di documento che prendono il numero da un registro**:
fattura, documento di trasporto, ordine, commessa, reso.

Per ognuno dice **dove vive**: in quale tabella stanno i suoi documenti, come si
chiama la colonna che ne porta il numero, e come si chiama quella che porta il
cliente.

---

### Perché non è un semplice elenco di parole

Sarebbe stato più veloce scrivere quei cinque nomi dentro il campo del registro e
finirla lì. Non basta, e la ragione non è «un domani potrebbero servirne altri».

La ragione è che **un'altra regola deve leggerli**. Un cliente non si sposta da un
emittente a un altro quando ha già un documento numerato: quel numero viene dal
registro di quell'emittente e nessuno lo rifà. Per rispondere «questo cliente ha
già dei documenti numerati?» bisogna guardare in cinque tabelle diverse.

Se quell'elenco di cinque tabelle fosse **ricopiato** dentro la regola, il giorno
in cui un sesto documento entrasse nei registri qualcuno dovrebbe ricordarsi di
aggiungerlo. Chi se ne dimentica non rompe niente: la regola continua a
funzionare, semplicemente **smette di guardare** dove dovrebbe. È il difetto
peggiore, perché non si vede.

⭐ Leggendo l'elenco da qui, il sesto documento entra nella regola **il giorno in
cui si registra la sua famiglia**. Non c'è nessuna copia da tenere allineata,
perché non c'è nessuna copia.

---

### Le due colonne che sembrano ripetute e non lo sono

* **la colonna del numero** non si chiama allo stesso modo dappertutto: è
  *numero* per fattura, documento di trasporto, ordine e reso, ma è *codice* per
  la commessa. È esattamente il genere di dettaglio che non si può indovinare;
* **la colonna del cliente** è obbligatoria su fattura e commessa, mentre su
  documento di trasporto, ordine e reso può mancare. Chi legge deve saperlo, e
  non ha modo di dedurlo.

---

### Cosa qui non c'è, ed è una decisione

Non esiste una casella «questa famiglia blocca lo spostamento del cliente, questa
no». La regola è **categorica**: se un tipo di documento prende il numero da un
registro, quel numero appartiene a un emittente, punto. Una casella che nessuno
avrebbe mai messo a «no» sarebbe una promessa che il resto del programma non
mantiene.

---

### Una famiglia ritirata resta scritta

Si può spegnere una famiglia senza cancellarla, ed è il modo giusto di ritirarla:
la riga resta come traccia del fatto che quel documento è esistito. Una famiglia
spenta può anche nominare una tabella che non c'è più — è storia, non
configurazione — mentre una famiglia accesa **deve** nominare cose che esistono
davvero, e c'è un controllo apposta che se ne accerta.

---

### Impatto e Vantaggi

* una sola sede dice quali documenti si numerano sui registri, e tutti la
  leggono;
* aggiungere un tipo di documento è **una riga**, non una caccia ai posti da
  aggiornare;
* il messaggio che spiega perché un cliente non si può spostare usa le parole di
  questa tabella, quindi resta corretto da sé.
