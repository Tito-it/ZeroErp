## 📘 Documentazione Concettuale – Tabella `dbops.processi_bersagli`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [dbops.processi](/dbzero/dbops/manual/processi)
>
**Approfondimento funzioni:**
>
• [script.trgfn_guard_emittente_scope](/dbzero/script/manual/trgfn_guard_emittente_scope)
>

### 🎯 Scopo Principale
(latest review 04-09-2026)

Per ogni processo di **dominio**, elenca le tabelle che tocca e — per ciascuna
— **come si arriva dall'a riga al suo emittente**.

È la risposta scritta a una domanda che altrimenti vive solo nella testa di chi
ha scritto il codice:

> **Questa riga di chi è?**

Senza una risposta scritta, un processo automatico può lavorare righe di
un'azienda mentre crede di lavorare le proprie, e nessuno se ne accorge finché
non arriva la fattura sbagliata.

---

### ⭐ Il percorso all'emittente non è sempre una colonna

È il motivo per cui la tabella ha **due** campi e non uno.

| `emittente_via` | Che cosa contiene la colonna indicata |
| --- | --- |
| `fiscale` | è **già** l'id dell'emittente |
| `soggetto_ruolo` | l'id del soggetto-ruolo dell'emittente |
| `fattura` | l'id di una fattura, da cui si risale |
| `contabile` | l'id di una distinta, da cui si risale al conto di incasso |
| `padre` | il legame passa da una riga padre (es. il listino sopra la versione) |

⚠️ **I due campi vivono o muoiono insieme** — un CHECK lo impone: o si dichiara
sia la via sia la colonna, o nessuna delle due. ⛔ Una via senza colonna sarebbe
un'affermazione senza contenuto: sembrerebbe una dichiarazione fatta, e non
direbbe niente.

---

### Che cosa succede se il percorso manca

La riga finisce in
[vw_processi_dominio_senza_emittente](/dbzero/dbops/manual/vw_processi_dominio_senza_emittente),
che **deve restare vuota**.

⭐ E quella vista non si limita a controllare che il campo sia pieno: verifica
anche che la colonna dichiarata **esista davvero**. È la differenza fra un
presidio e un modulo da compilare — un percorso verso una colonna cancellata è
peggio di un percorso assente, perché sembra a posto.

---

### Che cosa succede se il percorso c'è ma nessuno lo applica

La riga finisce in
[vw_processi_dominio_senza_difesa](/dbzero/dbops/manual/vw_processi_dominio_senza_difesa).

⚠️ È un livello diverso, e va letto diversamente: qui il modello sa **dove** sta
l'emittente, ma nessuna policy e nessun guard usa quell'informazione per
filtrare. È un **debito dichiarato**, non un errore da correggere entro sera —
ma deve calare, e la vista lo tiene sotto gli occhi invece di lasciarlo alla
memoria.

---

### Campi chiave

* `processo_id`: hard FK verso [processi](/dbzero/dbops/manual/processi).
* `schema_tabella` / `nome_tabella`: la tabella toccata. UNIQUE con il
  processo: una tabella compare una volta sola per processo.
* `emittente_via` / `emittente_colonna`: il percorso, come sopra.
* `note`: perché quel percorso, quando non è ovvio.

---

### ⭐ La matrice è VOLUTAMENTE incompleta, e non è una svista

Non tutti i processi hanno i loro bersagli censiti: la tabella copre i processi
di **dominio**, che sono quelli in cui sbagliare costa.

⛔ Censire anche manutenzione e amministrazione avrebbe prodotto un elenco
lungo, sempre indietro rispetto al codice, e **nessuno l'avrebbe letto** — che
è il modo in cui una documentazione smette di essere un presidio e diventa
arredamento.

Origine: `docs/it/dev/work-in-progress/brief-db-processi-automatici-identita-e-perimetro.md` §2.3.

---

{% include-markdown "signature-core.md" %}
