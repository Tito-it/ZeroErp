## 📘 Documentazione Concettuale – View `vendite.vw_lotti_segnalazioni_summary`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[vendite.fn_get_lotto_segnalazioni_summary](/dbzero/vendite/manual/fn_get_lotto_segnalazioni_summary) — *il lettore per un lotto, quello che il backend chiama*
>
Approfondimenti viste:
>
[dbops.vw_lotti_fermi_da_guardare](/dbzero/dbops/manual/vw_lotti_fermi_da_guardare) — *il lettore del presidio: i lotti pre-fiscali fermi da oltre un'ora*
> [vendite.vw_lotti_fase](/dbzero/vendite/manual/vw_lotti_fase) — *«in che fase è questo lotto?»: l'asse pre-fiscale*
> [vendite.vw_lotti_congelati_con_gruppi_in_errore](/dbzero/vendite/views/vw_lotti_congelati_con_gruppi_in_errore) — *la contraddizione opposta: congelato e in errore*
>
Approfondimenti tabelle:
>
[vendite.fatturazione_lotti_log](/dbzero/vendite/tabelle/fatturazione_lotti_log) · [vendite.fatture_log](/dbzero/vendite/tabelle/fatture_log) · [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture) · [vendite.fatturazione_lotti_esiti](/dbzero/vendite/tabelle/fatturazione_lotti_esiti)

---
### 🎯 Scopo Principale
(latest review 19-09-2026)

È la **sede unica** di due cose che prima vivevano in due posti diversi:

* il **riepilogo delle segnalazioni** di un lotto — i dieci conteggi che
  [`fn_get_lotto_segnalazioni_summary`](/dbzero/vendite/manual/fn_get_lotto_segnalazioni_summary)
  calcolava dentro di sé, per un lotto alla volta;
* il **verdetto «fermo»** — che fino al 19-09-2026 viveva in Python
  (`LottoSegnalazioniService.evaluate_lotto_status`, `blocks_next_step`).

Una riga per lotto, **tutti** i lotti, set-based. La funzione e il presidio
sono due **lettori** di questa vista, non due copie.

---

### ⭐ Perché una sede sola (D-1 di Tid, 18-09-2026: «la regola va a DB»)

Il Passo C dell'osservabilità chiedeva un presidio «lotto fermo da troppo tempo».
Scriverlo come vista **sopra i tre addendi** era facile e sbagliato: da quel
giorno il predicato avrebbe avuto due sedi — il Python per il banner e il
runner, la vista per il digest e il pallino — e le due sarebbero divergute al
primo addendo nuovo (il decimo conteggio, del 12-09, era stato aggiunto in
Python). Il sintomo non è un errore: è il banner che dice «fermo» e il digest
che dice «tutto a posto».

E lo stesso vale **dentro** il database: se la funzione avesse tenuto i suoi
aggregati e il presidio ne avesse scritto una copia set-based, le sedi sarebbero
state due lo stesso. ⇒ Gli aggregati stanno **qui**; un addendo nuovo si aggiunge
in un posto e lo vedono insieme banner, digest e pallino.

---

### Le colonne

| Colonna | Che cosa dice |
| --- | --- |
| `lotto_id` | il lotto |
| i **dieci conteggi**, nello stesso ordine della funzione | vedi il manuale della [funzione](/dbzero/vendite/manual/fn_get_lotto_segnalazioni_summary): sei storici (segnalazioni `C`/`W`/`I` per canale, righe di ponte in `ERRORE`), tre del banner (gesti, non allarmi), il decimo (esiti `ERRORE`) |
| `fermo` | **il verdetto**: `(fatture_critical + lotto_critical) > 0 OR fatture_stato_esecuzione_errore > 0 OR esiti_stato_esecuzione_errore > 0` |
| `fermo_motivo` | **quale** addendo, con la precedenza del banner: `CRITICHE` › `FATTURE_IN_ERRORE` › `ESITI_IN_ERRORE`. `NULL` se non è fermo. Vocabolario chiuso di tre valori — è una colonna di vista, un `CHECK` non può averlo |
| `fermo_da` | il fatto **più recente** che lo ferma: `data_ora` della critica viva, `data_update` della riga di ponte in `ERRORE`, `errore_quando` dell'esito (con `data_update` a ripiego). Valorizzata ogni volta che `fermo` è vero |

⚠️ **`fermo` è il verdetto su ogni lotto, qualunque sia il suo stato fiscale.**
Un `DEFINITIVA` con un esito `ERRORE` è `fermo` qui come lo era per il Python.
La spartizione sull'asse `pre_fiscale` la fanno i due **presidi**
(`dbops.vw_lotti_fermi_da_guardare` per i pre-fiscali,
`vw_lotti_congelati_con_gruppi_in_errore` per i congelati), non questa vista:
una sede risponde a una domanda.

#### ⭐ Perché il fatto più recente, e non il più vecchio

Il presidio chiede *«da quanto nessuno lo rilancia né lo scioglie»*. Un rilancio
che fallisce di nuovo scrive un fatto nuovo (un esito, una critica) e riparte
l'orologio: chi ci sta mettendo le mani adesso non è un allarme. Il fatto più
vecchio direbbe «da quando è rotto», che è un'altra domanda.

---

### Gli stessi filtri della funzione, uno per uno

* `disabilitato IS FALSE` sui due registri di segnalazioni;
* nel canale lotto, il `NOT EXISTS` su `ESCLUSO`: la segnalazione di un
  documento **uscito dal giro** non conta più. ⚠️ Con `gruppo_key NULL` il `NOT
  EXISTS` è vero e la riga **conta**: la critica del giro ferma il giro;
* il denominatore (`documenti_presi_in_carico_count`) si conta sugli **esiti**,
  non sul perimetro, che è vuoto sui giri di massa;
* `ESCLUSO` non conta fra gli errori: è la via d'uscita dichiarata.

Provata in `ROLLBACK` il 19-09 contro la funzione viva: 95 lotti su 95 con la
stessa riga (fatto datato, dbdev).

---

### Come si legge, e quanto costa

```sql
-- Un lotto: il predicato lotto_id = $1 viene spinto dentro le quattro GROUP BY
SELECT * FROM vendite.vw_lotti_segnalazioni_summary WHERE lotto_id = 6260;

-- Chi è fermo adesso, senza soglia
SELECT lotto_id, fermo_motivo, now() - fermo_da AS da_quanto
  FROM vendite.vw_lotti_segnalazioni_summary
 WHERE fermo;
```

Le quattro sottoquery sono `GROUP BY lotto_id` in `FROM` (non CTE): il planner
spinge `lotto_id = $1` dentro ciascuna, e la lettura per un lotto è la stessa
delle vecchie CTE — quattro letture per chiave, con l'indice FK di
`fatturazione_lotti_log(lotto_id)` acceso lo stesso giorno. La lettura di tutti i
lotti (il presidio) aggrega i quattro registri interi: è una lettura da digest e
da pallino, non da riga di lista.

---

### Chi vede che cosa

`security_invoker`: le quattro tabelle sono sotto RLS (via lotto, via fattura) e
una persona legge il riepilogo dei **propri** lotti. Un lotto fuori perimetro
**non è nella vista**, e la funzione lettrice risponde zeri e `fermo = false` —
come prima. Il presidio in `dbops` la attraversa da proprietario con
[`fn_conta_presidio`](/dbzero/dbops/manual/fn_conta_presidio).

---

### Verifica

`db/pgtap/vendite/test-lotti-fermi-verdetto-a-db-v1.sql` — coi builder, mai
iterando sull'esistente: un caso per addendo, la ritirata, l'`ESCLUSO`, la
precedenza, l'orologio, la parità funzione ↔ vista, la spartizione, la soglia, il
`DEFINER` onesto.

Origine: `docs/it/dev/work-done/brief-db-osservabilita-lotto-fermo-r6-indici.md` §2;
changeSet `20260919-01`.

{% include-markdown "signature-core.md" %}
