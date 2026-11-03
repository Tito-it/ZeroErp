## 📘 Documentazione Concettuale – Procedura `maintenance.proc_bump_toponomastica`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.toponomastica](/dbzero/config/tabelle/toponomastica) — il tipo di toponimo (Via, Piazza, Corso…) che la procedura corregge
> * [config.stradario_generale](/dbzero/config/tabelle/stradario_generale) — i nomi di strada che lo usano, e il loro indirizzo normalizzato
> * [config.stradario](/dbzero/config/tabelle/stradario) — le vie di quei nomi di strada, una per una
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio) — gli indirizzi su quelle vie, dove arriva la cascata
>
> Approfondimento funzioni:
>
> * [config.trgfn_toponomastica_protect_update](/dbzero/config/funzioni/trgfn_toponomastica_protect_update) — il guard sulla descrizione di un toponimo in uso, che il flag apre
> * [config.trgfn_toponomastica_bump_normalize](/dbzero/config/funzioni/trgfn_toponomastica_bump_normalize) — l'aggiornamento neutro sullo stradario generale
> * [config.trgfn_stradario_generale_normalize](/dbzero/config/funzioni/trgfn_stradario_generale_normalize) — il ricalcolo di `indirizzo_normalizzato`
> * [maintenance.proc_bump_indirizzi_dettaglio](/dbzero/maintenance/funzioni/proc_bump_indirizzi_dettaglio) — la rinormalizzazione degli indirizzi di una via, che la procedura chiama per ogni via del toponimo
>
> Guide:
>
> * [Riclassificazione vie e toponomastica](/guide/riclassificazione-vie) — la procedura operativa in cui si inserisce

---

### 🎯 Scopo Principale

Corregge la descrizione di un toponimo già usato dallo stradario generale, passando il guard che
fuori manutenzione la blocca, e porta la correzione fino agli indirizzi: i nomi di strada che lo
usano e gli indirizzi di dettaglio sulle loro vie.

---

### Il guard blocca solo la descrizione di un toponimo in uso

Sulla tabella `config.toponomastica` il guard dell'aggiornamento rifiuta con
`E_COLONNA_NON_MODIFICABILE` un solo cambiamento: la `descrizione` di un toponimo che almeno una
riga di `config.stradario_generale` usa. Un toponimo non ancora usato si corregge liberamente; le
altre colonne non sono sorvegliate da questo guard (la disattivazione di un toponimo in uso la
rifiuta un altro trigger, quello che impedisce di spegnere un padre con figli attivi).

La procedura accende il flag `zeroerp.maintenance_toponomastica`, con cui il guard lascia passare
qualunque aggiornamento, scrive la nuova descrizione sul toponimo indicato e spegne il flag prima
di proseguire.

---

### La rinormalizzazione dello stradario generale la fanno i suoi trigger

Scritta la descrizione, il trigger `AFTER UPDATE` del toponimo esegue un aggiornamento neutro su
tutte le righe di `config.stradario_generale` che lo usano: riscrive lo stesso
`toponomastica_id`, senza cambiare niente. È quell'aggiornamento a far girare, su ciascuna riga,
il trigger di normalizzazione dello stradario generale, che rilegge la descrizione del toponimo e
ricalcola `indirizzo_normalizzato`.

Il guard dello stradario generale non si oppone: protegge descrizione, descrizione breve e
`toponomastica_id`, e l'aggiornamento neutro non ne cambia nessuno.

---

### ⭐ La correzione arriva fino agli indirizzi di dettaglio

La via normalizzata di un indirizzo di dettaglio non segue da sola il toponimo: si calcola solo
quando la riga viene scritta. Senza un passo in più, gli indirizzi sulle vie del toponimo
resterebbero con la descrizione vecchia, e nessun presidio lo segnalerebbe.

La procedura è il gesto di manutenzione, e lo completa: dopo lo stradario generale prende, una per
una, le vie di `config.stradario` il cui nome di strada usa il toponimo, e per ciascuna chiama
`maintenance.proc_bump_indirizzi_dettaglio`, nella stessa transazione. Non ricopia la sua
rinormalizzazione: quella di una via ha una sede sola. Se un indirizzo fallisce, per esempio
perché la normalizzazione produce un doppione della chiave, fallisce la procedura intera e anche
la correzione del toponimo si annulla.

---

### ⛔ Il flag si spegne prima di proseguire

Il flag vale per la **transazione**, non per la sessione. Lasciato acceso, ogni aggiornamento
successivo a `config.toponomastica` nella stessa transazione passerebbe senza il guard. Per
questo la procedura lo tiene acceso solo per la scrittura della descrizione e lo rimette a `off`
subito dopo, **anche quando la scrittura fallisce**: in caso di errore lo spegne e poi rilancia
l'errore.

La cascata sugli indirizzi di dettaglio gira a flag già spento: non le serve, perché non tocca la
descrizione del toponimo.

---

### Gira coi diritti di chi la chiama

La procedura è `SECURITY INVOKER`, non ha un job pgAgent e nessuna funzione del database la
chiama: si lancia a mano, in manutenzione controllata. Chi la chiama deve poter scrivere anche gli
indirizzi di dettaglio che la cascata riscrive. Un id che non esiste non aggiorna niente e non
solleva errori.

---

### Test

`db/pgtap/config/test-toponomastica-stradario-generale.sql` — la normalizzazione dello stradario
generale col toponimo; il guard che rifiuta la modifica della descrizione di un toponimo in uso;
la procedura che la fa passare e l'`indirizzo_normalizzato` delle vie che torna a contenere la
descrizione nuova; la disattivazione di un toponimo in uso rifiutata e quella di uno non in uso
ammessa.

`db/pgtap/maintenance/test-bump-toponomastica-v1.sql` — su una fixture costruita apposta
(toponimo, nome di strada, via e indirizzo, che prima della correzione ha la descrizione
vecchia): dopo la procedura il flag non è acceso e, nella stessa transazione, il guard rifiuta
ancora il cambio a mano della descrizione; lo stradario generale e l'indirizzo di dettaglio, in
`via_norm` e in `indirizzo_normalizzato`, hanno la descrizione nuova;
`maintenance.proc_bump_indirizzi_dettaglio` non lascia acceso il flag degli indirizzi.

---

### Note di migrazione

* 2026-01-02 — nasce, insieme al guard sui toponimi in uso.
* 2026-11-03 — il flag si spegne prima di proseguire, anche in errore. Prima restava acceso fino
  alla fine della transazione che chiamava la procedura, e ogni modifica successiva ai toponimi
  nella stessa transazione passava senza guard (`brief-db-revisione-maintenance` D1).
* 2026-11-03 — la correzione arriva agli indirizzi di dettaglio: la procedura chiama
  `maintenance.proc_bump_indirizzi_dettaglio` per ogni via del toponimo. Prima la catena si
  fermava allo stradario generale, e gli indirizzi restavano con la descrizione vecchia finché
  qualcuno non li riscriveva (`brief-db-revisione-maintenance` D9).

---

{% include-markdown "signature-core.md" %}
