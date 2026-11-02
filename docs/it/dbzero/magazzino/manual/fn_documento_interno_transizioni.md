## 📘 Documentazione Concettuale – Funzione `magazzino.fn_documento_interno_transizioni`

> **Ultimo aggiornamento**: 1 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.inventari](/dbzero/magazzino/tabelle/inventari) — colonna `stato_mag_inventario`
> * [magazzino.rettifiche](/dbzero/magazzino/tabelle/rettifiche) — colonna `stato_mag_rettifiche`
> * [magazzino.trasferimenti](/dbzero/magazzino/tabelle/trasferimenti) — colonna `stato_trasferimento`
>
> Approfondimento funzioni:
>
> * [magazzino.trgfn_documento_interno_guard_transizione](/dbzero/magazzino/funzioni/trgfn_documento_interno_guard_transizione) — il guard che la fa **rispettare**
> * [script.fn_available_actions_documento_interno](/dbzero/script/funzioni/fn_available_actions_documento_interno) — la capability che ne **disegna i pulsanti**
>
> Guide:
>
> * [Linee guida SQL](/linee-guida-sql) — §12, le capability

---

### 🎯 Scopo Principale

Dice quali **destinazioni** sono ammesse a partire da uno stato, per i
documenti interni di magazzino — l'inventario, la rettifica e il trasferimento
interno, che hanno la stessa matrice.

| Da | Si può andare a | Perché |
| --- | --- | --- |
| `DRAFT` | `CONFIRM`, `CANCEL` | una bozza si conferma o si butta |
| `CONFIRM` | `POSTED`, `CANCEL`, `DRAFT` | si registra, si annulla, o si **riapre** per correggerla |
| `POSTED` | — | i movimenti sono a registro: si corregge con una rettifica, non tornando indietro |
| `CANCEL` | — | chiuso |

Uno stato che non esiste risponde con un elenco vuoto, come uno terminale:
**non è un errore**, e non deve esserlo. Il cancello sui valori ammessi è il
vincolo `CHECK` della tabella (per esempio `chk_mag_inventari_stato`), non
questa funzione — che ha un compito solo.

---

### ⭐ Perché una funzione, e non due righe dentro il guard

Prima questa matrice **stava dentro il guard**. Andava bene finché il guard era
il solo a doverla conoscere. Poi è arrivato il primo drawer, e il frontend monta
le azioni di stato **solo** da `available_actions`: senza una sede condivisa le
uscite erano due, e tutte e due una **seconda copia** della regola, scritta nel
backend o nel frontend.

> Il guard fa rispettare la matrice; la capability la disegna. Sono due
> mestieri diversi sulla **stessa** frase, e una frase sola non può stare in due
> posti: il giorno in cui cambiasse, cambierebbe in uno.

È la regola generale delle capability (linee-guida-sql §12.2 punto 1: *«il
predicato è lo STESSO del guard che rifiuterebbe»*), applicata prima che il
difetto esista.

---

### ⚠️ `POSTED` è nella matrice, ma non è un pulsante

La matrice ammette il passaggio da `CONFIRM` a `POSTED`, eppure nessun operatore
vedrà mai un bottone «porta a POSTED»: quella porta la apre **solo**
l'operazione di registrazione, che si firma con un'impostazione di sessione
valida per la sola transazione. Un aggiornamento diretto — anche legittimo
secondo la matrice — prende `E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE`.

Sono **due cancelli in fila**, e la distinzione conta quando si legge un rifiuto:

| Cancello | Chi lo tiene | Che cosa dice |
| --- | --- | --- |
| la matrice | questa funzione, letta dal guard | «da qui non si va là» |
| la porta `POSTED` | il guard | «là ci si va, ma solo passando dall'operazione» |

⇒ La capability toglie `POSTED` dalle azioni e lo espone come `can_registra`.

---

### ⭐ Perché non è una tabella di catalogo

Gli stati dei documenti interni non hanno **attributi**: niente etichetta,
niente ordine, niente bandiere. Una tabella avrebbe portato una riga per
transizione, un CSV, un mirror e un pgTAP che ne conta le righe — per rendere
configurabile una cosa che il `CHECK` di tabella tiene comunque ferma. La
funzione è la sede **più piccola** che due lettori possono condividere.

⚠️ Il giorno in cui una transizione dovesse dipendere da un dato (un profilo, un
parametro), la sede cambia natura e diventa un catalogo: cambierebbe *dove* sta
la matrice, non chi la fa rispettare.

---

### Non legge niente

La funzione è dichiarata immutabile: non legge tabelle, e non deve — la matrice
è una costante del modello. È scritta in plpgsql e non in SQL semplice per
restare dentro il presidio dei riferimenti morti, che compila solo il plpgsql.

---

### Test

`db/pgtap/magazzino/test-capability-documenti-interni-v1.sql`, test 3: costruisce
**tutte e dodici** le transizioni fra i quattro stati e confronta, una per una,
ciò che questa funzione ammette con ciò che il guard lascia davvero passare. Un
elenco scritto a mano nel test sarebbe stato una terza copia.

---

### Note di migrazione

* 2026-09-22 — nasce con `brief-db-magazzino-lotto-2-bis-be-fe` (R-1), dalla
  decisione D-L2-h di `brief-db-magazzino-lotto-2-motore`: la matrice esce dal
  corpo del guard, dove stava scritta come scelta multipla, e diventa la sede
  comune di guard e capability.

---

{% include-markdown "signature-core.md" %}
