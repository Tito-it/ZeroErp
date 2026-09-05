# Brief DB — un job morto da sei mesi, e il registro che dice «done»

> **Destinatario:** team DB (`dev/db-tid`).
>
> **Origine.** Trovato dal team DB stesso guardando `dbops.vw_run_senza_attore`
> durante il cantiere dei processi automatici, e registrato come **R-12** nel
> vostro registro dei residui
> ([brief-db-processi-automatici-residui-be.md](brief-db-processi-automatici-residui-be.md)
> §1-quinquies). Qui c'è la **misura del backend**, che aggiunge tre fatti che
> cambiano la forma del problema.
>
> **Stato:** 🔴 aperto. ⚠️ **Non blocca il backend**, e non è di questo cantiere:
> lo scriviamo perché è la **sola cosa** che tiene `dbops.vw_run_senza_attore`
> lontana dallo zero, cioè dal criterio con cui voi stessi chiudete **DB-5**.
>
> ⛔ **Questo brief dice che cosa serve e perché, non come farlo.** Forma, DDL e
> changeSet sono decisioni vostre.

---

## 0. In due parole

`apply_storicizza_weekly` gira ogni settimana e muore ogni settimana da **sei
mesi**. Nessuno se n'è accorto, e non per distrazione: muore **prima di
scrivere**, quindi l'ultima cosa che il giornale dice di lui è che è andato
**bene**.

La causa immediata sono tre righe di configurazione che puntano a tabelle che non
esistono più. La causa vera è che quelle righe le mette un'automazione e **non le
toglie nessuno**.

---

## 1. I fatti, misurati il 2026-09-05

### 🔴 Il giornale non tace: dice il falso

```
jobname                 | started_at | ok | message
apply_storicizza_weekly | 2026-02-21 | t  | done
apply_storicizza_weekly | 2026-02-14 | t  | done
apply_storicizza_weekly | 2026-02-07 | t  | done
```

⛔ **Ogni corsa registrata è `ok = true`.** Non c'è una sola riga di errore in
tutta la storia di questo job: muore prima che `fn_run_and_log` scriva, quindi
l'ultimo verdetto agli atti resta *«done»*.

⚠️ **È peggio di un buco.** Un giornale che non dice niente si nota; un giornale
che dice «done» di un job morto **risponde alla domanda sbagliata con sicurezza**.
Chi guardasse quella riga concluderebbe «vecchio ma sano», che è esattamente il
contrario.

⭐ **E non riguarda solo questo job**: qualunque processo che muoia prima della
propria registrazione lascia lo stesso verde. È una proprietà del meccanismo, non
di questa configurazione.

### Le tre righe

`config.storico_set_storicizza` ha **104** righe; **3** puntano a niente:

| `table_name` | esiste? | `insert_manuale` | inserita il | da |
| --- | --- | --- | --- | --- |
| `vendite.attivita_fatturabili_lotti` | ⛔ no | `false` | 2026-01-31 | `postgres` |
| `config.profili_reparto_aree` | ⛔ no | `false` | 2026-03-07 | `postgres` |
| `config.profili_reparto_azioni` | ⛔ no | `false` | 2026-03-07 | `postgres` |

⭐ **Le date raccontano la sequenza**: l'ultima corsa buona è del **2026-02-21**,
e due delle tre righe sono nate il **2026-03-07**. Il primo giro dopo quella data
è quello in cui il job ha smesso di arrivare in fondo.

🔵 **E c'è una quarta riga da guardare, ma non so se sia un problema**:
`anagrafiche.risorse_umane_auth_user` esiste come **vista**, non come tabella. Se
la storicizzazione si aspetta una tabella, è un caso diverso dagli altri tre e
non lo classifico io.

---

## 2. Che cosa serve

### 2.1 Che il job torni a girare

Le tre righe non hanno più un bersaglio. ⚠️ **Toglierle è però il tampone**: se il
problema fosse solo quello, tornerebbe alla prossima tabella ritirata.

### 2.2 ⭐ Che una riga sparisca quando sparisce la sua tabella

`insert_manuale = false` e `user_insert = postgres` dicono che quelle righe le ha
messe un'**automazione** — non una persona. ⇒ Il set si popola da solo e **non si
pota da solo**: sono due metà di uno stesso meccanismo, e ne esiste una.

⛔ **È qui il difetto di modello**, e per questo lo segnaliamo invece di
proporvi una `DELETE` di tre righe: finché la potatura non esiste, la prossima
tabella ritirata rifà lo stesso guasto, e lo rifà **in silenzio per sei mesi**.

**Come si vede che è chiuso.** Si ritira una tabella che era nel set, e il giro
notturno successivo **passa** — o si ferma dicendo perché.

### 2.3 Che un job che muore prima di registrarsi si veda

⚠️ Questa è la più larga delle tre, e forse non è di questo brief. La segnaliamo
perché il cantiere appena chiuso ha comprato **visibilità** — l'attore sui run, i
presidi, la coda che dice chi ha fallito — e questo job è il caso che quella
visibilità **non copre**: non ha fallito nel giornale, ha smesso di comparirci.

🔵 Non proponiamo la forma. Diciamo la domanda: *un job che non arriva a
`fn_run_and_log` come si distingue da un job che non è mai partito?*

---

## 3. Perché al backend interessa

Solo per una ragione, e indiretta: `dbops.vw_run_senza_attore` non può arrivare a
zero finché questo job non gira, perché la sua riga si toglie **alla prossima
corsa** — e la prossima corsa non arriva mai.

⇒ È l'ultimo ostacolo al criterio con cui **DB-5** si dichiara chiusa. Le altre
tre righe della vista hanno ormai `processo_registrato = true` e si tolgono da
sole.

⛔ **Il backend non tocca niente qui**: `config.storico_set_storicizza` e i job
pgAgent sono vostri, e nessuna riga di Python li nomina.

---

## 4. Riferimenti

* [brief-db-processi-automatici-residui-be.md](brief-db-processi-automatici-residui-be.md)
  — §1-quinquies, dove R-12 è nato
* [piano-be-fe-processi-automatici-identita-e-perimetro.md](piano-be-fe-processi-automatici-identita-e-perimetro.md)
  — §8, il quadro dei presidi in cui questa riga resta accesa
