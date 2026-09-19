## 📘 Documentazione Concettuale – View `dbops.vw_lotti_fermi_da_guardare`

> 👀 **Vedi anche**
>
Approfondimenti viste:
>
[vendite.vw_lotti_segnalazioni_summary](/dbzero/vendite/manual/vw_lotti_segnalazioni_summary) — *la sede: da lì vengono `fermo`, il motivo e l'orologio*
> [vendite.vw_lotti_fase](/dbzero/vendite/manual/vw_lotti_fase) — *l'asse pre-fiscale*
> [vendite.vw_lotti_chiusi_con_gruppi_in_errore](/dbzero/vendite/views/vw_lotti_chiusi_con_gruppi_in_errore) — *l'altra metà dell'asse: chiuso e in errore*
> [dbops.vw_coda_lavori_da_guardare](/dbzero/dbops/manual/vw_coda_lavori_da_guardare) — *la stessa soglia di un'ora, per la stessa ragione*
>
Approfondimenti tabelle:
>
[dbops.presidi](/dbzero/dbops/manual/presidi)
>
Approfondimenti funzioni:
>
[dbops.fn_conta_presidio](/dbzero/dbops/manual/fn_conta_presidio)

---
### 🎯 Scopo Principale
(latest review 19-09-2026)

Elenca i giri di fatturazione **pre-fiscali** che sono **fermi da oltre un'ora** e
che nessuno ha rilanciato né sciolto. Deve restare vuota.

Il banner lo dice a chi **apre** il lotto; questa riga lo dice a chi **non lo
apre**: è la sorgente «lotto fermo» che mancava al Passo C dell'osservabilità
([analisi-osservabilita-log](/dev/work-in-progress/analisi-osservabilita-log)),
e da qui arriva al digest dei presidi, al pannello «Processi automatici» e al
pallino della topbar.

---

### ⭐ È un lettore, non una sede

`fermo`, `motivo` e `fermo_da` **non si calcolano qui**: sono le colonne di
[`vw_lotti_segnalazioni_summary`](/dbzero/vendite/manual/vw_lotti_segnalazioni_summary),
la stessa riga che il backend legge per il banner. Questa vista applica due
cose soltanto — la spartizione sull'asse pre-fiscale e la soglia — e se domani
il verdetto prende un addendo nuovo, il banner e il digest lo vedono **insieme**.

È la ragione per cui la sede esiste (decisione di Tid, 18-09-2026: *«la regola
va a DB»*): un presidio scritto sopra una copia dei tre addendi avrebbe detto
«tutto a posto» mentre il banner diceva «fermo», al primo addendo aggiunto in un
posto solo.

---

### Le colonne

| Colonna | Che cosa dice |
| --- | --- |
| `lotto_id`, `lotto_codice`, `lotto_competenza_mese`, `stato_codice_interno` | il lotto e la sua fase (da `vw_lotti_fase`) |
| `emittente_soggetto_ruolo_id`, `emittente_codice` | l'azienda — il codice per chi legge la riga a mano |
| `motivo` | **quale addendo** lo ferma, con la precedenza del banner: `CRITICHE` › `FATTURE_IN_ERRORE` › `ESITI_IN_ERRORE` |
| `fermo_da`, `da_quanto` | il fatto più recente che lo ferma, e da quanto |
| `critiche_vive`, `fatture_stato_esecuzione_errore_count`, `esiti_stato_esecuzione_errore_count`, `documenti_bloccanti_count`, `documenti_presi_in_carico_count` | i numeri della sede, per capire la riga senza aprire il lotto |

---

### ⭐ Solo i lotti pre-fiscali: la spartizione

Un lotto non pre-fiscale non è mai «fermo» in questo senso: un `DEFINITIVA`
con un esito `ERRORE` è la **contraddizione** di
[`vw_lotti_chiusi_con_gruppi_in_errore`](/dbzero/vendite/views/vw_lotti_chiusi_con_gruppi_in_errore),
che c'è già. I due presidi si spartiscono l'asse `pre_fiscale` senza
sovrapporsi: qui «si può ancora agire e nessuno agisce», là «è chiuso e non
doveva».

⚠️ `pre_fiscale` è **fail-closed sull'ignoto** (`COALESCE` a `false`, vedi il
manuale di `vw_lotti_fase`): un lotto senza stato risolvibile non compare qui.
Non è un buco — sul settimo caso la prudenza dice «non si tocca», e un presidio
che invitasse a rilanciarlo direbbe la cosa sbagliata.

---

### ⚠️ Un'ora è una scelta, non una misura

Il rilancio è il gesto di una **persona**, e le tre viste delle code usano la
stessa soglia per la stessa ragione: un lotto fallito due minuti fa e già in
rilancio non è un allarme.

L'orologio è `fermo_da`, il fatto **più recente** che lo ferma. Un rilancio che
fallisce di nuovo scrive un fatto nuovo e riparte l'orologio: la domanda resta
*«da quanto nessuno ci mette le mani»*. La soglia sta **qui**, come da manuale
del catalogo: non in `dbops.presidi`.

---

### ⛔ Perimetro `DEFINER`

`fatturazione_lotti` e le sue quattro figlie hanno la row level security, e la
sede è `security_invoker`: da una sessione **senza veste** questa vista risponde
**zero per cecità**, e «zero righe» e «non ho potuto vedere» si scrivono
uguale. Il digest la **conta** con
[`fn_conta_presidio`](/dbzero/dbops/manual/fn_conta_presidio) da proprietario e
riporta il numero; una persona la legge col proprio perimetro.

Sta in `dbops` e non in `vendite` perché il catalogo dei presidi pretende a
catalogo ogni vista degli schemi che vi compaiono, e `vendite` porterebbe dentro
tutte le `vw_*_lista`.

---

### Fatto datato (dbdev, 19-09-2026)

Il presidio **nasce pieno** su dev: 16 lotti pre-fiscali fermi da 6 a 91 giorni,
tutti per critiche — giri di prova lasciati a metà. È esattamente ciò che deve
dire, e il pregresso non si esclude per farlo partire verde.

---

### Verifica

`db/pgtap/vendite/test-lotti-fermi-verdetto-a-db-v1.sql` (test 15-19): la
soglia nei due versi, la spartizione, il `DEFINER` onesto (senza veste la vista
è vuota **e** il contatore conta la riga costruita), la riga a catalogo.
`db/pgtap/dbops/test-catalogo-presidi-v1.sql` fa rosso se vista e riga non
combaciano.

Origine: `docs/it/dev/work-done/brief-db-osservabilita-lotto-fermo-r6-indici.md` §2;
changeSet `20260919-03` + riga in `presidi.csv`.

{% include-markdown "signature-core.md" %}
