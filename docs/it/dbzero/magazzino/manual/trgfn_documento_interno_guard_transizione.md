## 📘 Documentazione Concettuale – Trigger function `magazzino.trgfn_documento_interno_guard_transizione`

> **Ultimo aggiornamento**: 1 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.inventari](/dbzero/magazzino/tabelle/inventari) — dove è montato
> * [magazzino.rettifiche](/dbzero/magazzino/tabelle/rettifiche) — dove è montato
> * [magazzino.trasferimenti](/dbzero/magazzino/tabelle/trasferimenti) — dove è montato
>
> Approfondimento funzioni:
>
> * [magazzino.fn_documento_interno_transizioni](/dbzero/magazzino/funzioni/fn_documento_interno_transizioni) — la matrice che legge
> * [magazzino.trgfn_documento_interno_righe_guard_testata](/dbzero/magazzino/funzioni/trgfn_documento_interno_righe_guard_testata) — il gemello sulle righe
> * [magazzino.fn_posta_inventario](/dbzero/magazzino/funzioni/fn_posta_inventario) — chi apre la porta per l'inventario
> * [magazzino.fn_posta_rettifica](/dbzero/magazzino/funzioni/fn_posta_rettifica) — chi apre la porta per la rettifica
> * [magazzino.fn_posta_trasferimento](/dbzero/magazzino/funzioni/fn_posta_trasferimento) — chi apre la porta per il trasferimento
> * [script.fn_is_proprietario_tabella](/dbzero/script/funzioni/fn_is_proprietario_tabella) — «chi scrive è un verbo»
>
> Guide:
>
> * [Linee guida SQL](/linee-guida-sql) — §12.2, il predicato della capability è quello del guard

---

### 🎯 Scopo Principale

**Fa rispettare la matrice degli stati** dei documenti interni di magazzino — inventari,
rettifiche e trasferimenti — e tiene la porta `POSTED` e il cestino. Una funzione sola per le
tre famiglie: ogni tabella le passa il nome della propria colonna di stato e quello della
propria impostazione di registrazione. È montata prima dell'aggiornamento della colonna di
stato e prima della cancellazione.

---

### ⭐ La matrice non sta qui: la legge

Il guard non contiene la matrice: la legge da
[magazzino.fn_documento_interno_transizioni](/dbzero/magazzino/funzioni/fn_documento_interno_transizioni),
la stessa sede da cui la capability del drawer disegna i pulsanti. I lettori sono **due**:
una matrice scritta nel corpo del guard avrebbe costretto il frontend a scriverne una seconda
copia (linee-guida-sql §12.2 punto 1). Il cestino e la porta `POSTED` restano qui: sono regole
di questo guard, non della matrice.

In sintesi la matrice dice: una bozza (`DRAFT`) si conferma o si annulla; un documento
confermato (`CONFIRM`) si registra (solo dall'operazione), si annulla o torna in bozza;
`POSTED` e `CANCEL` sono terminali. Riscrivere lo stesso stato non è una transizione.

Il ritorno in bozza esiste perché il piano dell'inventario si legge in `CONFIRM` e le righe si
correggono in `DRAFT`: senza, l'unica uscita da una riga sbagliata sarebbe annullare e rifare.

---

### La porta `POSTED`

Un documento «registrato» senza movimenti dietro direbbe il falso. `POSTED` è ammesso solo se
valgono **due condizioni insieme**:

1. l'impostazione di registrazione della famiglia (per esempio
   `zeroerp.magazzino_posting_inventario`), valida per la sola transazione, porta l'id del
   documento. La impostano le funzioni di registrazione e la azzerano in coda. Dice **quale
   operazione e quale documento**;
2. chi esegue è il proprietario della tabella
   ([script.fn_is_proprietario_tabella](/dbzero/script/funzioni/fn_is_proprietario_tabella)).
   Dice **che la scrittura passa da un verbo**: i verbi girano con i privilegi del
   proprietario, l'applicazione no.

La seconda condizione serve perché l'impostazione l'applicazione può accenderla da sola: da
sola non apre niente, altrimenti si potrebbe segnare un documento come registrato senza
movimenti e senza il permesso.

Un aggiornamento diretto a `POSTED` è `E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE` (tecnico:
nessuna interfaccia lo produce). Nel contesto dell'errore `dentro_verbo` e `db_user` dicono
quale delle due condizioni è mancata.

---

### Il cestino

Le righe cascano con la testata; cancellare un documento registrato lascerebbe i movimenti con
una sorgente sparita. Si elimina **solo una bozza**: da `CONFIRM` in poi l'uscita è `CANCEL`.

---

### ⭐ Matrice in una funzione, non in una tabella

Gli stati sono un vincolo `CHECK` a valori chiusi, senza attributi. Se un giorno serviranno
stati configurabili, cambierà dove sta la matrice, non chi la fa rispettare.

---

### Codici errore

* `E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA` — transizione fuori matrice; la frase nomina i due
  stati.
* `E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE` — `POSTED` senza l'impostazione
  dell'operazione, o fuori da un verbo.
* `E_MAG_DOCUMENTO_NON_ELIMINABILE` — cancellazione di un documento che non è in bozza.

---

### Test

`db/pgtap/magazzino/test-documenti-interni-guard-v1.sql`.

---

### Note di migrazione

* 2026-09-18 — nasce con `brief-db-magazzino-lotto-2-motore` (§3 D-L2-h, §6-ter C3, C13), con
  la matrice scritta nel corpo.
* 2026-09-22 — `brief-db-magazzino-lotto-2-bis-be-fe` (R-1): la matrice esce dal corpo e passa
  a `fn_documento_interno_transizioni`. Comportamento, codici e frasi invariati.
* 2026-09-25 — `brief-db-magazzino-verbi-con-permesso` (D-V1): la porta `POSTED` chiede anche
  che a scrivere sia il proprietario. Prima bastava l'impostazione di registrazione.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
