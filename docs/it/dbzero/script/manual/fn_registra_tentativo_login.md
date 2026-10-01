## 📘 Documentazione Concettuale – Funzione `script.fn_registra_tentativo_login()`

> 👀 **Vedi anche**
>
> **Il modello (tre regole):** [config.credenziali](/dbzero/config/tabelle/credenziali)
>
> **La gemella, prima della password:** [fn_check_blocco_login](/dbzero/script/funzioni/fn_check_blocco_login)

---

### 🎯 Scopo Principale
(riscritta il 25-09-2026)

Registra **com'è andato** un tentativo di accesso, dopo la verifica della
password. Riceve la credenziale (se il nome la trova), l'impronta del nome
tentato, la provenienza (l'IP di chi chiama) e l'esito.

⭐ **Anche un nome che non esiste conta** (dal 2026-09-25, R-7): se il nome non
trova una credenziale, la credenziale arriva vuota e si conta sul nome tentato
([config.nomi_tentati](/dbzero/config/tabelle/nomi_tentati)), con gli stessi
numeri e la stessa risposta. Così chi prova non capisce se il nome esiste. Il
nome in chiaro non arriva mai: solo la sua impronta, calcolata dal backend.

**Accesso riuscito** → azzera i fallimenti di fila della credenziale e toglie il
freno **sulla sola macchina** da cui si è entrati
([fn_azzera_tentativi_credenziale](/dbzero/script/funzioni/fn_azzera_tentativi_credenziale)).
Il freno sulle altre macchine resta.

**Password sbagliata** → due conti, nello stesso giro:

1. la **credenziale**: un fallimento di fila in più, e l'orario. Serve
   all'attesa crescente, che guarda gli errori da qualunque macchina;
2. la **coppia credenziale + macchina**: un tentativo in più; alla soglia
   (`login_max_tentativi_falliti`) la macchina è frenata per
   `login_blocco_minuti`. Se il freno era già scaduto, riparte da uno. La
   regola è [fn_login_freno_passo](/dbzero/script/funzioni/fn_login_freno_passo),
   la stessa per il nome inesistente.

Ogni credenziale conta, anche una che non ha nessuna porta attiva: la password
c'è.

---

### Cosa restituisce

Un oggetto JSON:

| Campo | Significato |
| --- | --- |
| `bloccato` | la macchina è appena stata frenata |
| `minuti_rimanenti` | la durata del freno, se `bloccato` |
| `tentativi` | gli errori di fila **da questa macchina** |
| `attesa_secondi` | quanto dovrà aspettare il prossimo tentativo della credenziale |

Errori: credenziale data ma inesistente → `E_CREDENZIALE_NON_TROVATA`; parametri
mancanti, impronta che non è di 32 byte, un accesso **riuscito** senza credenziale
→ `E_AUTH_CHIAMATA_NON_VALIDA`.

---

### Storia

* 2026-09-25 — riscritta (`20260925-11`): lo stato è della credenziale, arriva la
  provenienza (la firma a due argomenti non esiste più) e `attesa_secondi`. Prima,
  senza una riga `OPERATORE` in `identita_digitali` il tentativo non contava.
* 2026-09-25 — `20260925-61` (R-7): conta anche un nome che non esiste, per
  impronta; la firma prende l'impronta del nome (quella a tre argomenti non esiste
  più).

{% include-markdown "signature-core.md" %}
