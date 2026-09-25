## 📘 Documentazione Concettuale – Tabella `config.credenziali`

> 👀 **Vedi anche**
>
> **La figlia:** [config.credenziali_provenienze](/dbzero/config/tabelle/credenziali_provenienze) — il freno sulla provenienza
>
> **Le funzioni del login:** [fn_check_blocco_login](/dbzero/script/funzioni/fn_check_blocco_login) · [fn_registra_tentativo_login](/dbzero/script/funzioni/fn_registra_tentativo_login) · [fn_azzera_tentativi_credenziale](/dbzero/script/funzioni/fn_azzera_tentativi_credenziale)
>
> **Il blocco dell'amministratore:** [fn_blocca_credenziale](/dbzero/script/funzioni/fn_blocca_credenziale) · [fn_sblocca_credenziale](/dbzero/script/funzioni/fn_sblocca_credenziale)
>
> **Il cambio password obbligatorio:** [fn_get_deve_cambiare_password](/dbzero/script/funzioni/fn_get_deve_cambiare_password) · [fn_imposta_deve_cambiare_password](/dbzero/script/funzioni/fn_imposta_deve_cambiare_password)
>
> **Le vesti:** [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)

---

### 🎯 Scopo Principale
(scritta il 25-09-2026)

Una persona ha **una sola password**, e la usa per entrare da tutte le porte:
il gestionale (operatore), il portale clienti e fornitori, lo shop. Questa
tabella tiene ciò che appartiene a quella password — alla **credenziale** — e
non alla singola porta:

* quanti tentativi sbagliati di fila ha subito, e quando l'ultimo;
* se un amministratore l'ha **bloccata**, chi, quando e perché;
* se al prossimo accesso deve **cambiare la password**.

Fino al 2026-09-25 queste informazioni stavano su `anagrafiche.identita_digitali`,
cioè su una riga **per porta**: lo stato di una cosa sola era sparso su più righe,
e il login contava solo la riga del gestionale. Chi aveva soltanto il portale o lo
shop non veniva mai frenato.

---

### Tre regole diverse, per tre casi diversi

| Regola | Chi la fa scattare | Cosa succede |
| --- | --- | --- |
| **Freno sulla provenienza** | le password sbagliate da **una stessa macchina** | quella macchina, per quella credenziale, viene fermata per qualche minuto. Il titolare entra dalla sua. Sta nella figlia, [credenziali_provenienze](/dbzero/config/tabelle/credenziali_provenienze) |
| **Attesa crescente** | tante password sbagliate di fila, **da qualunque macchina** | ogni tentativo deve aspettare qualche secondo, sempre di più fino a un massimo. **Rallenta, non chiude mai** |
| **Blocco dell'amministratore** | un **SUPER_ADMIN**, con un gesto esplicito e un motivo | la credenziale non entra più da nessuna porta finché qualcuno non la sblocca |

⭐ **Perché così.** Un blocco che scatta per le password sbagliate di *chiunque*
permetterebbe a uno sconosciuto di chiudere fuori il titolare: basta conoscere il
nome utente, e quelli del portale e dello shop si ricavano dall'email. Per questo
le password sbagliate frenano **chi le prova**, non il titolare; e chiudere
davvero una credenziale è una **decisione**, che ha un autore.

I numeri (quanti errori prima del freno, quanti minuti, dopo quanti errori parte
l'attesa, quanti secondi al massimo) sono parametri: `login_max_tentativi_falliti`,
`login_blocco_minuti`, `login_tetto_credenziale`, `login_attesa_base_secondi`,
`login_attesa_max_secondi`. Li legge [fn_login_parametri](/dbzero/script/funzioni/fn_login_parametri).

---

### Cosa azzera cosa

| Evento | Fallimenti di fila | Freno sulle macchine | Blocco dell'admin | Cambio password obbligatorio |
| --- | --- | --- | --- | --- |
| Accesso riuscito da una macchina | azzerati | tolto **solo** su quella macchina | resta | resta |
| Reset della password riuscito | azzerati | tolto su **tutte** | ⛔ **resta** | a cura del cambio password |
| Sblocco dell'amministratore | restano | restano | tolto | resta |

⚠️ **Il reset non toglie il blocco dell'amministratore.** Il reset dimostra che la
persona possiede l'email; non annulla la decisione di chi ha bloccato.

⚠️ **Un accesso riuscito non toglie il freno sulle altre macchine.** Quella è la
macchina di chi sta provando la password: se un accesso del titolare la
liberasse, l'attaccante ripartirebbe da capo a ogni login riuscito.

---

### Quando la riga esiste

La riga **nasce la prima volta che serve**: al primo errore, al primo blocco, al
primo «deve cambiare la password». Una credenziale che non ha mai sbagliato non
ha una riga, e **l'assenza vale** «nessun errore, non bloccata, nessun obbligo».

Per questo nessuno, fuori dal database, legge o scrive direttamente la tabella:
chi ha bisogno di sapere qualcosa chiede alle funzioni elencate sopra, che
conoscono il significato dell'assenza. L'applicazione può leggere la tabella, ma
**non scriverla**: scrivono solo quelle funzioni.

---

### Limiti da conoscere

* **Sotto un attacco continuo da molte macchine** il titolare può trovare il
  turno già preso da un tentativo altrui e dover aspettare più di una volta. Il
  rimedio è il reset della password.
* **Nessuno storico riga per riga.** La riga cambia a ogni password sbagliata:
  tenerne la storia vorrebbe dire registrare ogni tentativo. Del blocco
  dell'amministratore resta l'ultimo stato (chi, quando, perché).
* **Il legame con `django.auth_user`** (la cancellazione dell'utente si porta via
  la riga) esiste solo dove Django ha già creato le sue tabelle quando gira
  Liquibase: in CI no. Per questo le funzioni che scrivono controllano da sé che
  l'utente esista.

---

### Storia

* 2026-09-25 — nasce con il cantiere «la credenziale» (`20260925-01`): le colonne
  `tentativi_falliti`, `bloccato_fino_a`, `deve_cambiare_password` e
  `totp_obbligatorio` escono da `identita_digitali` (`20260925-25`). Brief:
  brief-db-blocco-login-per-credenziale.

{% include-markdown "signature-core.md" %}
