## 📘 Documentazione Concettuale – Vista `dbops.vw_riferimenti_morti_rientrati`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.riferimenti_morti_esenzioni](/dbzero/dbops/tabelle/riferimenti_morti_esenzioni) — il registro che la vista rilegge
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — la riga di catalogo del presidio
>
> Approfondimento viste:
>
> * [dbops.vw_riferimenti_morti_da_sanare](/dbzero/dbops/views/vw_riferimenti_morti_da_sanare) — la gemella, dal verso dei difetti
>
> Approfondimento funzioni:
>
> * [dbops.fn_check_funzioni_riferimenti_morti](/dbzero/dbops/funzioni/fn_check_funzioni_riferimenti_morti) — la misura
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — perché un registro ha due versi

---

### 🎯 Scopo Principale

Le voci del registro del debito sui riferimenti morti che non corrispondono più a nessun difetto:
righe da togliere. È ciò che impedisce al registro di diventare un elenco di eccezioni permanenti.

---

### ⚠️ Perché senza questa vista il presidio si degrada da solo

Un registro di esenzioni tende a riempirsi e a non svuotarsi: ogni difetto giudicato accettabile
aggiunge una riga, e quando il difetto si sana nessuno torna a togliere l'esenzione, perché niente
lo segnala. Dopo un po' il guardrail è verde e non presidia quasi nulla. Questa vista rende visibile
l'esenzione diventata inutile: è la ragione per cui il registro si può chiamare «debito».

---

### Come funziona

Per ogni voce del registro verifica se la misura trova ancora un difetto `REALE` o `ORFANA` con lo
stesso schema, la stessa funzione e un esito che corrisponde al pattern. Se non lo trova, la voce è
rientrata. Espone anche il motivo e la data di registrazione, così chi la toglie vede perché era
stata messa e da quanto.

---

### ⚠️ Una riga qui non è sempre «difetto sanato»

* La funzione può essere stata **rinominata o eliminata**, o il messaggio di `plpgsql_check` può
  essere cambiato (un aggiornamento dell'estensione, un ritocco che sposta il testo): il pattern non
  aggancia più. Prima di togliere una voce si controlla che il difetto sia davvero sparito.
* ⛔ Se lo strumento **non ha potuto misurare** la funzione esentata (`NON_MISURATO`), la vista non
  trova il difetto e dà la voce per rientrata. Il guardrail della CI si ferma prima, sulla misura
  mancata, e non arriva a questa domanda; la vista no. Una riga qui insieme a righe `NON_MISURATO`
  nella gemella non dice niente sul registro.

---

### Legge con gli occhi di chi interroga

La vista è `security_invoker`, e la misura sotto vede solo ciò che il chiamante può compilare: da un
ruolo che non possiede gli oggetti ispezionati la risposta cambia. Nel catalogo il suo perimetro è
`DEFINER`: il digest la conta come proprietario e riporta il numero, non le righe. Costa quanto la
gemella: fa girare `plpgsql_check` su tutto il database.

---

### Test

* `db/pgtap/dbops/test-riferimenti-morti-v1.sql` — nessuna voce rientrata nel registro, dallo
  stesso ruolo da cui si misura.

---

### Note di migrazione

* 2026-08-04 — nasce con `brief-db-bonifica-riferimenti-morti` §5, insieme alla gemella.
* 2026-09-10 — la riga di catalogo passa a perimetro `DEFINER`: letta da un ruolo che non possiede
  gli oggetti ispezionati, la vista rispondeva in modo diverso dal proprietario.
* 2026-09-14 — il primo digest settimanale dà rientrata la voce legata a pgAgent: era il ruolo che
  misurava, non la funzione. Da lì una classe nuova nella misura e una voce che segue la macchina.

---

{% include-markdown "signature-core.md" %}
