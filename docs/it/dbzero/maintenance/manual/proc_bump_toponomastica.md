## 📘 Documentazione Concettuale – Procedura `maintenance.proc_bump_toponomastica`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.toponomastica](/dbzero/config/tabelle/toponomastica) — il tipo di toponimo (Via, Piazza, Corso…) che la procedura corregge
> * [config.stradario_generale](/dbzero/config/tabelle/stradario_generale) — i nomi di strada che lo usano, e il loro indirizzo normalizzato
>
> Approfondimento funzioni:
>
> * [config.trgfn_toponomastica_protect_update](/dbzero/config/funzioni/trgfn_toponomastica_protect_update) — il guard sulla descrizione di un toponimo in uso, che il flag apre
> * [config.trgfn_toponomastica_bump_normalize](/dbzero/config/funzioni/trgfn_toponomastica_bump_normalize) — l'aggiornamento neutro sullo stradario generale
> * [config.trgfn_stradario_generale_normalize](/dbzero/config/funzioni/trgfn_stradario_generale_normalize) — il ricalcolo di `indirizzo_normalizzato`
> * [maintenance.proc_bump_indirizzi_dettaglio](/dbzero/maintenance/funzioni/proc_bump_indirizzi_dettaglio) — la gemella sugli indirizzi di dettaglio
>
> Guide:
>
> * [Riclassificazione vie e toponomastica](/guide/riclassificazione-vie) — la procedura operativa in cui si inserisce

---

### 🎯 Scopo Principale

Corregge la descrizione di un toponimo già usato dallo stradario generale, passando il guard che
fuori manutenzione la blocca, e lascia che i trigger rinormalizzino i nomi di strada che lo
usano.

---

### Il guard blocca solo la descrizione di un toponimo in uso

Sulla tabella `config.toponomastica` il guard dell'aggiornamento rifiuta con
`E_COLONNA_NON_MODIFICABILE` un solo cambiamento: la `descrizione` di un toponimo che almeno una
riga di `config.stradario_generale` usa. Un toponimo non ancora usato si corregge liberamente; le
altre colonne non sono sorvegliate da questo guard (la disattivazione di un toponimo in uso la
rifiuta un altro trigger, quello che impedisce di spegnere un padre con figli attivi).

La procedura accende il flag `zeroerp.maintenance_toponomastica`, con cui il guard lascia passare
qualunque aggiornamento, e scrive la nuova descrizione sul toponimo indicato.

---

### La rinormalizzazione la fanno i trigger dello stradario generale

Scritta la descrizione, il trigger `AFTER UPDATE` del toponimo esegue un aggiornamento neutro su
tutte le righe di `config.stradario_generale` che lo usano: riscrive lo stesso
`toponomastica_id`, senza cambiare niente. È quell'aggiornamento a far girare, su ciascuna riga,
il trigger di normalizzazione dello stradario generale, che rilegge la descrizione del toponimo e
ricalcola `indirizzo_normalizzato`.

Il guard dello stradario generale non si oppone: protegge descrizione, descrizione breve e
`toponomastica_id`, e l'aggiornamento neutro non ne cambia nessuno.

⚠️ La catena si ferma allo stradario generale. Gli indirizzi di dettaglio che stanno su quelle
vie conservano la via normalizzata calcolata con la descrizione vecchia finché qualcuno non li
riscrive, per esempio con `maintenance.proc_bump_indirizzi_dettaglio` via per via.

---

### ⚠️ Il flag resta acceso fino alla fine della transazione

Il flag vale per la **transazione**, e la procedura lo accende senza spegnerlo prima di uscire:
resta acceso fino alla fine della transazione che la chiama. Ogni aggiornamento successivo a
`config.toponomastica` nella stessa transazione passa quindi senza il guard.

Chiamata da sola, in autocommit, la transazione finisce con la procedura e il flag con lei.
Dentro un'unità di lavoro più grande, ciò che segue la chiamata gira senza protezione.

---

### Gira coi diritti di chi la chiama

La procedura è `SECURITY INVOKER`, non ha un job pgAgent e nessuna funzione del database la
chiama: si lancia a mano, in manutenzione controllata. Un id che non esiste non aggiorna niente e
non solleva errori.

---

### Test

`db/pgtap/config/test-toponomastica-stradario-generale.sql` — la normalizzazione dello stradario
generale col toponimo; il guard che rifiuta la modifica della descrizione di un toponimo in uso;
la procedura che la fa passare e l'`indirizzo_normalizzato` delle vie che torna a contenere la
descrizione nuova; la disattivazione di un toponimo in uso rifiutata e quella di uno non in uso
ammessa. Il file non verifica lo stato del flag dopo la procedura.

---

### Note di migrazione

* 2026-01-02 — nasce, insieme al guard sui toponimi in uso.

---

{% include-markdown "signature-core.md" %}
