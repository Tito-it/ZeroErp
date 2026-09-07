## 📘 Documentazione Concettuale – Vista `dbops.vw_codici_errore_forme_condizione`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [config.codici_errore](/dbzero/config/tabelle/codici_errore)
> • [config.classi_errore](/dbzero/config/tabelle/classi_errore)
>
Approfondimento viste:
> • [dbops.vw_codici_errore_da_dichiarare](/dbzero/dbops/views/vw_codici_errore_da_dichiarare)

---
### 🎯 Scopo Principale

(rev 2026-09-07)

Misura gli **accumulatori**: i codici errore usati in punti che fanno cose diverse fra loro.
Un codice che serve a troppe situazioni smette di dire qualcosa, e chi lo riceve non sa che
fare.

⭐ **L'asse di misura è la FORMA DELLA CONDIZIONE al punto che solleva** — cioè che cosa
verifica l'`IF` sopra la chiamata — **non il dominio della funzione**. La scelta viene da un
tentativo fallito: misurando per dominio, l'asse segnalava `E_VALIDAZIONE`, che è precisamente
il caso su cui la risposta è *no, va bene così*. Un codice di validazione compare ovunque
**per definizione**; è la forma del controllo a dire se sta accumulando significati diversi.

La vista **non filtra di proposito**: chi filtra decide cosa non vedere.

---

### Come funziona: isole fra due guardie

Il corpo di ogni funzione `plpgsql` viene spezzato riga per riga, e ogni riga marcata come:

* **guardia** — inizia con `IF`, `ELSIF`, `ELSE`, `EXCEPTION WHEN`, `WHEN OTHERS`,
  `WHEN SQLSTATE`;
* **chiamata** — nomina `fn_log_and_raise_error`;
* **codice** — contiene un letterale `'E_...'` (fuori dai commenti).

Le guardie delimitano le **isole**: ogni codice viene attribuito alla guardia che lo precede,
e una finestra mobile di 6 righe collega la guardia alla chiamata. Da lì si ricava la
*famiglia* della condizione.

---

### Le cinque famiglie, e il loro ordine

L'ordine del `CASE` è portante, non estetico: una guardia che somiglia a due famiglie finisce
nella **prima** che la riconosce.

| # | Famiglia | Che cosa verifica la guardia |
|---|----------|------------------------------|
| 1 | `ECCEZIONE` | è un gestore d'eccezione (`EXCEPTION WHEN`, `WHEN OTHERS`, `WHEN SQLSTATE`) |
| 2 | `NOT_FOUND` | una riga che doveva esserci non c'è (`IF NOT FOUND`) |
| 3 | `PARAMETRO` | un parametro è nullo o non positivo (`p_x IS NULL`, `<= 0`) |
| 4 | `ENUM` | il valore è fuori da un insieme ammesso (`NOT IN (…)`) |
| 5 | `VALORE_ATTESO` | il valore letto **non è quello ammesso** (`x <> 'LETTERALE'`) |
| — | `IGNOTO` | nessuna regola sa leggere quella guardia |

⭐ **`VALORE_ATTESO` è entrata il 2026-09-07**, ed è la forma di **ogni guardia di stato o di
perimetro** del progetto: *«questo documento non è in bozza»*, *«questa non è una email di
sistema»*. Non era un caso di nicchia — era una famiglia intera che l'asse non nominava, e
che finiva tutta in `IGNOTO`.

⛔ **Perché una famiglia nuova e non un `ENUM` allargato** (un `<> 'X'` è, in fondo, un
insieme di uno): le letture di questa vista sono **datate e si confrontano nel tempo**.
Cambiare che cosa significa `ENUM` renderebbe la lettura del 2026-08-08 incomparabile con la
prossima, e **in silenzio**. Il nome nuovo dice esattamente che cosa si è reso visibile, e
quando.

⚠️ **Il segnale che l'ha resa necessaria.** `E_VALIDAZIONE` leggeva
`famiglie = {IGNOTO, PARAMETRO}` con `n_famiglie_note = 1`: quindi **non compariva** fra i
candidati della query (1), che filtra `> 1`. La sua seconda forma era la terza guardia di
`config.fn_chiudi_email_sistema` — *«qualcuno sta usando la porta di sistema per l'email di
un'azienda»*, il punto più pericoloso di quella funzione e l'unico momento in cui lo si nota.
⇒ **Il rubinetto era cieco su qualunque codice la cui SECONDA forma fosse una che il
classificatore non sapeva leggere.** Segnalato dal backend: `brief-db-sveglia-dei-processi`
§3.2, risposta §8.4.

⚠️ **Imprecisione dichiarata**: la forma prende anche del normale control-flow che capita
entro venticinque righe da un `RAISE` — `IF TG_OP = 'DELETE'`, `IF v_id_type = 'uuid'`. Sta
dentro la natura di questa vista (*una misura, non un cancello*), ma va saputo leggendo la
query (1).

Verifica: `db/pgtap/dbops/test-vw-codici-errore-valore-atteso.sql` — quattro forme
**costruite**, quattro risposte attese, compreso il verso che pretende che una guardia
illeggibile resti `IGNOTO`.

---

### ⚠️ Le tre query canoniche vanno usate **insieme**

Il `COMMENT` della vista le riporta per esteso. La ragione per cui sono tre:

**(1) Candidati** — `WHERE n_famiglie_note > 1 ORDER BY n_punti DESC`: i codici usati sotto
guardie di forma diversa.

**(2) Copertura** — quanti codici sono classificati e quanti restano `solo_ignoto`. ⚠️ Senza
la (2), **la (1) si legge come una verità**: se metà dei punti non è classificabile, l'assenza
di un codice dalla lista dei candidati non significa che sia pulito — significa che non si sa.

**(3) La classe è ancora vera?** — incrocia le due letture indipendenti dello stesso codice:
la **guardia** (che cosa *fa* il punto) e la **classe** (che cosa *dice* il catalogo). È la
query che ha trovato `E_ERRORE_PARAMETRI`: 4 punti su 13 dicevano il falso.

---

### ⚠️ È una misura, non un cancello

Non c'è soglia, non c'è verdetto. Serve a **guardare**, e le sue risposte vanno interpretate:
un codice con più famiglie può essere un accumulatore da spezzare, oppure un codice
legittimamente trasversale.

**Le letture, datate** — vanno confrontate fra loro, ed è il motivo per cui portano la data:

| quando | codici | classificati | invisibili | candidati (1) |
|---|---:|---:|---:|---:|
| 2026-08-08 | 344 | 75 | 269 | — |
| 2026-09-06, prima di `VALORE_ATTESO` | 453 | 96 | 357 | 6 |
| 2026-09-07, subito dopo | 453 | **148** | **305** | **10** |

⚠️ Fra le prime due righe il buco **cresceva**: la copertura non sale da sola.

Condivide i punti ciechi della gemella `vw_codici_errore_da_dichiarare`: legge **letterali**
in corpi `plpgsql`, quindi non vede i codici costruiti per concatenazione né i
`RAISE EXCEPTION` diretti.

---

### Scope

`WITH (security_invoker = true)`. Legge i cataloghi di sistema. Da ri-specificare a ogni
`CREATE OR REPLACE VIEW`.

---

{% include-markdown "signature-core.md" %}
