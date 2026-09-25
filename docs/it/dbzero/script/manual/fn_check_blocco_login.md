## 📘 Documentazione Concettuale – Funzione `script.fn_check_blocco_login()`

> 👀 **Vedi anche**
>
> **Il modello (tre regole):** [config.credenziali](/dbzero/config/tabelle/credenziali)
>
> **La gemella, dopo la password:** [fn_registra_tentativo_login](/dbzero/script/funzioni/fn_registra_tentativo_login)

---

### 🎯 Scopo Principale
(riscritta il 25-09-2026)

Dice se una credenziale **può provare ad entrare** da una certa macchina. Il
backend la chiama **prima** di verificare la password: se risponde con un
errore, la password non viene nemmeno guardata e il tentativo non conta.

Riceve la credenziale (`auth_user.id`, vuota se il nome non ne trova nessuna),
l'**impronta del nome tentato** e la **provenienza** (l'indirizzo IP di chi
chiama). Non guarda da quale porta si entra — gestionale, portale, shop: la
password è una sola.

⭐ **Vale anche per un nome che non esiste** (dal 2026-09-25, R-7): allora i
controlli 2 e 3 si fanno sul nome tentato
([config.nomi_tentati](/dbzero/config/tabelle/nomi_tentati)), con gli stessi numeri
e le stesse frasi. Chi prova non capisce se il nome esiste. Il controllo 1 esiste
solo per le credenziali: la sua frase rivela che il nome c'è, ed è accettato
perché al titolare serve sapere a chi rivolgersi.

---

### Cosa controlla, in quest'ordine

Il primo che scatta vince:

| # | Controllo | Esito |
| --- | --- | --- |
| 1 | la credenziale è **bloccata dall'amministratore** | `E_CREDENZIALE_BLOCCATA` — «Accesso bloccato dall'amministratore.» |
| 2 | **questa macchina** è frenata per troppi errori | `E_UTENTE_BLOCCATO`: il messaggio dice fra quanti minuti riprovare (i minuti sono anche nel contesto). Se il freno è già scaduto, la macchina riparte da zero e il controllo passa |
| 3 | la credenziale ha sbagliato troppe volte di fila e l'**attesa** non è finita | `E_LOGIN_ATTESA` — «riprovare fra N secondi» |

Una credenziale che non ha mai sbagliato non ha una riga in `config.credenziali`:
passa subito.

Provenienza mancante, impronta mancante o non di 32 byte, credenziale non
positiva → `E_AUTH_CHIAMATA_NON_VALIDA`: è un errore di chi chiama.

---

### Storia

* 2026-09-25 — riscritta (`20260925-10`): lo stato è della credenziale, non della
  riga `OPERATORE` di `identita_digitali`; arriva la provenienza (la firma a un
  solo argomento non esiste più), il blocco dell'amministratore e l'attesa
  crescente. Prima, chi aveva solo il portale o lo shop non veniva mai frenato.
* 2026-09-25 — `20260925-52`: il messaggio del freno porta i minuti rimanenti,
  come quello dell'attesa porta i secondi. Prima diceva «Account temporaneamente
  bloccato», ma il freno riguarda la sola postazione, e i minuti non arrivavano a
  chi stava provando.
* 2026-09-25 — `20260925-60` (R-7): vale anche per un nome che non esiste, per
  impronta; la firma prende l'impronta del nome (quella a due argomenti non esiste
  più).

{% include-markdown "signature-core.md" %}
