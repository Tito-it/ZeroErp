## 📘 Documentazione Concettuale – Tabella `dbops.stati_check_dichiarazioni`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo dei presidi, dove il registro è dichiarato
>
> Approfondimento viste:
>
> * [dbops.vw_stati_check_scrittori](/dbzero/dbops/views/vw_stati_check_scrittori) — la misura che legge questo registro
> * [dbops.vw_stati_check_da_sanare](/dbzero/dbops/views/vw_stati_check_da_sanare) — la lista di lavoro che deve restare vuota
>
> Guide:
>
> * [Presidi e registri del debito — uno stato mai scritto](/guide/presidi-e-registri-del-debito#36-uno-stato-previsto-dal-modello-e-mai-scritto) — il presidio per intero

---

### 🎯 Scopo Principale

L'elenco dei valori di una colonna di stato che il controllo automatico **non trova scritti** da
nessuna funzione del database, ognuno con scritto accanto **chi lo scrive davvero** o **perché
resta così**. È il registro del presidio degli stati mai scritti.

Non è una lista di eccezioni concesse. Una riga dice una di due cose: «questo valore lo scrive il
programma, non il database, e il programma lo verifica», oppure «questo valore il criterio non lo
vede, sappiamo perché». Non dice mai «va bene così».

---

### ⭐ Perché il registro ha un `canale`

Il database vede solo una parte di chi scrive: il valore predefinito di una colonna, una funzione
che scrive la tabella, una funzione che chiama quella funzione. **Non vede il programma**, e molti
stati li scrive proprio il programma.

Se quei valori finissero qui come «esenti», nessuno si accorgerebbe del giorno in cui il programma
smette di scriverli. Per questo la riga dice **chi la verifica**:

| `canale` | Che cosa dichiara | Chi controlla che sia ancora vero |
| --- | --- | --- |
| `APPLICAZIONE` | il valore lo scrive un modulo del programma, anche passandolo a una funzione del database | il **test del backend**: il valore deve comparire in un file che scrive quella tabella; se sparisce, il test è rosso |
| `ESENTE` | il criterio non lo vede: un cantiere aperto, una tabella senza scrittori, un valore **copiato** da un'altra colonna | il **controllo del database**: se una funzione comincia a scriverlo, la riga non serve più (`DEBITO_ESTINTO`) |

⚠️ `ESENTE` non vuol dire «non scritto». Il caso che l'ha insegnato: il diario delle fasi di un
lotto riceve lo stato **copiandolo** dal lotto, senza che il valore compaia mai in una funzione. È
scritto a ogni fase, e il criterio non lo vede. Stringere il vincolo della colonna, la prima idea,
avrebbe rotto il diario.

---

### ⚠️ È un debito, quindi deve calare

Ogni riga ha una data, e una riga ferma da mesi è un'informazione. Quando un lavoro è finito, **la
riga va tolta**: rimasta, continuerebbe a far tacere il controllo su quel valore. Il controllo se ne
accorge da solo e la segnala.

---

### Una riga per valore, non per colonna

La chiave è (schema, tabella, colonna, **valore**). Dichiarare «questa colonna la scrive il
programma» nasconderebbe esattamente il caso per cui il controllo esiste: un valore solo, in una
colonna per il resto scritta bene, che nessuno scrive.

`ragione` dice, per `APPLICAZIONE`, quale modulo scrive il valore; per `ESENTE`, che cosa manca
perché venga scritto o perché il criterio non lo vede, e dove vive quel lavoro. ⛔ Non un'etichetta
e non un rimando nudo.

---

### Che cosa c'è dentro, oggi

Le righe `APPLICAZIONE` sono il ciclo di vita scritto dal programma: le **code** (lavori, stampe,
esiti e fatture dei giri di fatturazione, attività fatturabili), le **bozze email**, le **chiavi di
idempotenza**, il **diario** del lotto, la gravità degli eventi di vendita, i documenti interni di **magazzino**
confermati o annullati dall'operatore, gli esiti di avvertimento della generazione dei documenti.

Le righe `ESENTE` sono di quattro specie: stati che **nessuno scrive ancora** e che il modello
prevede (l'annullamento e l'archiviazione di un documento generato, l'esito negativo della
generazione, gli esiti di calcolo dei consumi, l'errore operativo del lotto), stati che il motore di
**magazzino** scriverà quando i trasferimenti saranno finiti, gli stati dei **mandati SEPA**, una
tabella che oggi nessuno scrive, e i valori **copiati** che il criterio non vede.

---

### Test

* `db/pgtap/dbops/test-stati-check-scrittori-v1.sql` — ogni canale ammesso è un ramo vivo della
  misura; il registro classifica `APPLICAZIONE` e `ESENTE`; una riga che non serve più esce
  `DEBITO_ESTINTO`, nei due versi.

---

### Note di migrazione

* 2026-09-21 — nasce col presidio degli stati mai scritti (`brief-db-presidio-stati-mai-scritti`):
  il caso originale era un esito d'errore ammesso dal vincolo degli esiti dei lotti e mai scritto per
  mesi, mentre le corse chiudevano «completate».
* 2026-11-08 — perde `tx_id`, `data_update`, `user_update` e i due trigger montati a mano che li
  scrivevano: la tabella la scrive solo la migrazione, dal CSV, e le colonne direbbero sempre «il
  migratore» (regola dello scrittore, `automazione-db.md` §1.1; `brief-db-revisione-dbops`, giro 7-bis).

---

{% include-markdown "signature-core.md" %}
