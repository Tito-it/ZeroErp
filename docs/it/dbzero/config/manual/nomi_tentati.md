## 📘 Documentazione Concettuale – Tabella `config.nomi_tentati`

> 👀 **Vedi anche**
>
> **La gemella per le credenziali vere:** [config.credenziali](/dbzero/config/tabelle/credenziali)
>
> **Le coppie con la provenienza:** [config.nomi_tentati_provenienze](/dbzero/config/tabelle/nomi_tentati_provenienze)
>
> **Chi la scrive:** [fn_registra_tentativo_login](/dbzero/script/funzioni/fn_registra_tentativo_login) · [fn_check_blocco_login](/dbzero/script/funzioni/fn_check_blocco_login)

---

### 🎯 Scopo Principale
(scritta il 25-09-2026)

Ricorda gli errori di accesso su un **nome che non esiste**: qualcuno ha scritto
un nome utente che non corrisponde a nessuna credenziale, e ha sbagliato.

Serve a non dire a chi prova **se il nome esiste**. Senza questa tabella un nome
inesistente rispondeva sempre «credenziali errate», mentre uno vero, dopo qualche
errore, rispondeva «troppi tentativi»: bastavano sei prove per sapere se
l'utente c'era. Ora il freno e l'attesa valgono **per il nome tentato**, esista o
no, con gli stessi numeri e le stesse frasi.

Quando il nome corrisponde a una credenziale si conta sulla credenziale
([config.credenziali](/dbzero/config/tabelle/credenziali)): così gli errori fatti
con lo username e con l'email della stessa persona si sommano.

---

### ⛔ Il nome non si salva

Nel campo del nome utente finiscono anche password digitate per sbaglio. Per
questo la tabella non contiene il nome ma una sua **impronta** (`nome_digest`, 32
byte), calcolata dal backend con una chiave che il database non conosce. Il nome
in chiaro non arriva mai al database.

---

### Il ciclo di una riga

| Momento | Cosa succede |
| --- | --- |
| primo errore su un nome inesistente | la riga nasce |
| errori successivi | il conto cresce; oltre il tetto ogni tentativo deve aspettare (come per una credenziale) |
| nessun errore per 30 giorni | la riga scade (`cleanup_at`), e con lei le sue coppie |

Un nome inesistente non entra mai, quindi non si azzera: scade.

⚠️ **Il limite, dichiarato** (brief §13.1): chi prova lo username e l'email della
stessa persona vede i conti sommarsi, dove per due nomi inesistenti resterebbero
separati. Impara che i due nomi sono della stessa persona, non che uno dei due
esiste. E dopo 30 giorni di silenzio il conto di un nome inesistente riparte,
quello di una credenziale no. Il blocco deciso dall'amministratore esiste solo
sulle credenziali, e la sua frase rivela che il nome c'è: accettato, perché al
titolare serve sapere a chi rivolgersi.

---

### Storia

* 2026-09-25 — nasce (`20260925-55`), R-7 del cantiere «la credenziale». Brief:
  brief-db-blocco-login-per-credenziale §13.

{% include-markdown "signature-core.md" %}
