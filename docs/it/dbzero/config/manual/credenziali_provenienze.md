## 📘 Documentazione Concettuale – Tabella `config.credenziali_provenienze`

> 👀 **Vedi anche**
>
> **La madre, e il modello completo:** [config.credenziali](/dbzero/config/tabelle/credenziali)
>
> **Chi la scrive:** [fn_registra_tentativo_login](/dbzero/script/funzioni/fn_registra_tentativo_login) · [fn_check_blocco_login](/dbzero/script/funzioni/fn_check_blocco_login) · [fn_azzera_tentativi_credenziale](/dbzero/script/funzioni/fn_azzera_tentativi_credenziale)

---

### 🎯 Scopo Principale
(scritta il 25-09-2026)

Il **freno sulla provenienza**: una riga per ogni coppia *credenziale + macchina
da cui qualcuno ha sbagliato la password*. La macchina è l'indirizzo IP da cui
arriva il tentativo.

Dopo un certo numero di errori di fila dalla stessa macchina
(`login_max_tentativi_falliti`), quella macchina viene fermata per qualche
minuto (`login_blocco_minuti`) — **solo per quella credenziale**. Il titolare,
che entra dalla sua, non se ne accorge. Il modello completo, con le altre due
regole, è nella pagina di [config.credenziali](/dbzero/config/tabelle/credenziali).

---

### Il ciclo di una riga

| Momento | Cosa succede |
| --- | --- |
| primo errore da una macchina | la riga nasce |
| errori successivi | il contatore cresce; alla soglia la macchina è frenata fino a `bloccato_fino_a` |
| freno scaduto | al tentativo successivo la coppia **riparte da zero** |
| accesso riuscito **da quella macchina** | la riga si cancella |
| reset della password | si cancellano **tutte** le righe della credenziale |
| la macchina non riprova più | la riga scade da sola (`cleanup_at`, un giorno dopo l'ultimo errore) |

⚠️ La provenienza è **obbligatoria**: un tentativo senza indirizzo non si può
registrare. Ricavare l'indirizzo vero di chi chiama, anche dietro un proxy, è
compito del backend.

---

### Storia

* 2026-09-25 — nasce con il cantiere «la credenziale» (`20260925-02`). Brief:
  brief-db-blocco-login-per-credenziale.

{% include-markdown "signature-core.md" %}
