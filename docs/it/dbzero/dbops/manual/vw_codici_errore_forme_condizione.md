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

(rev 2026-08-21)

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

Condivide i punti ciechi della gemella `vw_codici_errore_da_dichiarare`: legge **letterali**
in corpi `plpgsql`, quindi non vede i codici costruiti per concatenazione né i
`RAISE EXCEPTION` diretti.

---

### Scope

`WITH (security_invoker = true)`. Legge i cataloghi di sistema. Da ri-specificare a ogni
`CREATE OR REPLACE VIEW`.

---

{% include-markdown "signature-core.md" %}
