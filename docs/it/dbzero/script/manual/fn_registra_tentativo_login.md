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
password. Riceve la credenziale, la provenienza (l'IP di chi chiama) e l'esito.

**Accesso riuscito** → azzera i fallimenti di fila della credenziale e toglie il
freno **sulla sola macchina** da cui si è entrati
([fn_azzera_tentativi_credenziale](/dbzero/script/funzioni/fn_azzera_tentativi_credenziale)).
Il freno sulle altre macchine resta.

**Password sbagliata** → due conti, nello stesso giro:

1. la **credenziale**: un fallimento di fila in più, e l'orario. Serve
   all'attesa crescente, che guarda gli errori da qualunque macchina;
2. la **coppia credenziale + macchina**: un tentativo in più; alla soglia
   (`login_max_tentativi_falliti`) la macchina è frenata per
   `login_blocco_minuti`. Se il freno era già scaduto, riparte da uno.

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

Errori: credenziale inesistente → `E_CREDENZIALE_NON_TROVATA`; parametri mancanti
→ `E_AUTH_CHIAMATA_NON_VALIDA`.

---

### Storia

* 2026-09-25 — riscritta (`20260925-11`): lo stato è della credenziale, arriva la
  provenienza (la firma a due argomenti non esiste più) e `attesa_secondi`. Prima,
  senza una riga `OPERATORE` in `identita_digitali` il tentativo non contava.

{% include-markdown "signature-core.md" %}
