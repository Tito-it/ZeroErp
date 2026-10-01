## 📘 Documentazione Concettuale – View `dbops.vw_magazzino_dipendenze_inverse`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) ·
[magazzino.assets](/dbzero/magazzino/manual/assets) ·
[dbops.presidi](/dbzero/dbops/manual/presidi)
>
Approfondimenti funzioni:
>
[magazzino.fn_scrivi_movimento](/dbzero/magazzino/funzioni/fn_scrivi_movimento) ·
[vendite.fn_posta_ddt](/dbzero/vendite/funzioni/fn_posta_ddt) ·
[vendite.fn_posta_reso](/dbzero/vendite/funzioni/fn_posta_reso)
>
Mappa: [Mappa concentrica — anello 2 e matrice delle dipendenze](/mappa-concentrica)

---
### 🎯 Scopo Principale
(latest review 01-10-2026)

Elenca le cose del **magazzino** che conoscono per nome un **processo** che lo usa:
le vendite, gli acquisti, i pagamenti. L'elenco dei processi sta scritto dentro la
vista stessa.

> ⛔ È un **cancello**: deve restare **vuota**. Una riga fa fallire il controllo
> automatico, non un promemoria.

---

### ⭐ Perché esiste, detto sul modello

Il magazzino contiene due cose diverse. Il **registro** dice dove sta la merce e
quanto vale, e ha una porta sola per scriverci. È un **servizio**, come il motore
che stampa i documenti: chi muove merce — una bolla, un reso, domani un carico da
fornitore — lo usa, e il registro non deve sapere chi è.

Quando il registro conosce un suo cliente, ogni nuovo cliente lo costringe a
cambiare, e due parti del programma che dovrebbero stare una dentro l'altra si
tengono a vicenda. È successo davvero: con la bolla e il reso, due funzioni del
registro leggevano le tabelle delle vendite, e nessun controllo se n'è accorto,
perché la regola «mai dipendenze all'indietro» era **scritta** ma nessuno la
**leggeva**. Il 1° ottobre 2026 le due funzioni sono passate nelle vendite, e da
quel giorno questa vista legge la regola al posto nostro.

⚠️ Al primo giro ha trovato anche una cosa che nessuno cercava: il seriale di un
bene sapeva sotto quale **contratto** di vendita stava. Anche quel legame è stato
tolto: se servirà, sarà il contratto a dire quali beni ha.

---

### Che cosa guarda, e che cosa no

La vista guarda il magazzino con **due lenti**:

| Lente | Che cosa vede |
| --- | --- |
| **il catalogo del database** (`come = CATALOGO`) | i legami che il database registra da solo: un collegamento fra tabelle, una vista costruita su un'altra tabella, un controllo automatico che esegue una funzione altrui, una regola di visibilità, un valore predefinito. È esatta: non legge testo |
| **il testo delle funzioni** (`come = CORPO`) | le funzioni scritte come programma, di cui il database non registra i legami. Il testo si legge **senza i commenti**, così una spiegazione che nomina le vendite non fa scattare il cancello |

| Conta | Non conta |
| --- | --- |
| una funzione del magazzino che legge una tabella delle vendite | una funzione delle **vendite** che usa il magazzino: è il verso giusto |
| un collegamento da una tabella del magazzino verso un documento | un commento che nomina le vendite |
| una vista del magazzino costruita su una tabella degli acquisti | i controlli automatici che impediscono di spegnere un magazzino ancora usato da una bolla: li genera il database dal legame **della bolla verso il magazzino**, il verso giusto |

Legge solo il catalogo del database, con i permessi di chi la interroga: non
tocca dati.

---

### Se compare una riga

La riga dice **che cosa** nel magazzino (`oggetto`), **in che modo** (`come`,
`tipo_oggetto`) e **quale processo** nomina (`schema_nominato`, `nominati`).

L'esito atteso è uno solo: **la conoscenza si sposta dal lato di chi usa**. Il
processo scrive nel proprio spazio ciò che gli serve e chiama il registro dalla
sua porta; un legame fra dati lo porta il documento, non il registro.

⛔ Non si allarga l'elenco dei processi per far tornare vuota la vista: l'elenco
cresce solo quando nasce un **processo nuovo**, ed è un cambiamento di questa
vista, firmato e motivato.

---

### Esempio d'uso

```sql
-- Deve tornare zero righe. Se no, la prima colonna dice che cosa, l'ultima chi nomina.
SELECT oggetto, tipo_oggetto, come, schema_nominato, nominati
FROM dbops.vw_magazzino_dipendenze_inverse;
```

Presidio: `db/pgtap/magazzino/test-registro-non-nomina-i-consumatori-v1.sql` (in
CI), che oltre a pretendere la vista vuota costruisce sei testimoni — una
funzione, una vista, un collegamento, un controllo automatico, una regola di
visibilità e un valore predefinito che nominano un processo — e verifica che la
vista li veda tutti, e che non veda una funzione che nomina le vendite solo in un
commento. A catalogo in `dbops.presidi` con natura `CANCELLO`.
Origine: `docs/it/dev/work-in-progress/brief-db-magazzino-registro-anello-interno.md`.

---

{% include-markdown "signature-core.md" %}
