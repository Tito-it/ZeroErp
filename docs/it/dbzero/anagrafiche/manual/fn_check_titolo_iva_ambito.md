## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_check_titolo_iva_ambito()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva)
> • [anagrafiche.soggetti_titoli_iva_ambiti](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva_ambiti)
>
Approfondimento funzioni:
> • [anagrafiche.trgfn_soggetti_titoli_iva_ambiti_guard](/dbzero/anagrafiche/funzioni/trgfn_soggetti_titoli_iva_ambiti_guard) — chi la chiama dalle righe figlie
> • [anagrafiche.trgfn_soggetti_titoli_iva_guard_ambito](/dbzero/anagrafiche/funzioni/trgfn_soggetti_titoli_iva_guard_ambito) — chi la chiama dal titolo

---

### 🎯 Scopo Principale

(rev 2026-08-29 — funzione nata il 2026-08-29)

Elenca i motivi per cui l'**ambito** di un titolo IVA non sta in piedi. Ne ha due:

1. un titolo che vale per **tutto** porta anche un elenco di voci — la registrazione
   direbbe due cose opposte, e chi calcola l'IVA ne leggerebbe una sola;
2. **il pareggio**: due titoli dello stesso tipo, dello stesso cliente, verso lo
   stesso emittente, validi insieme, che coprono lo **stesso oggetto allo stesso
   livello**.

Funzione **pura**: non solleva e non scrive. Ritorna `[]` se l'ambito è coerente,
altrimenti un elenco ordinato di motivi; chi solleva prende il **primo**.

---

### ⭐ Perché è una funzione, e non il corpo di un trigger

Perché i trigger che ne hanno bisogno sono **due**, e sono su tabelle diverse:

| Trigger | Su cosa | Serve quando |
| --- | --- | --- |
| `trgfn_soggetti_titoli_iva_ambiti_guard` | le righe di ambito | si aggiunge o si sposta una voce coperta |
| `trgfn_soggetti_titoli_iva_guard_ambito` | il titolo | si allarga una **data**, si **riattiva** un titolo spento, si cambia il **tipo** |

🔴 **Il secondo è il lato che si dimentica.** Due titoli diventano sovrapposti anche
senza che nessuno tocchi le righe di ambito: basta allungare una validità. Un
controllo scritto solo sulla tabella figlia sarebbe **cieco metà del tempo**.

⭐ E i due trigger la **chiamano** invece di riscriverla. La differenza vale la riga:
un test che confrontasse due predicati proverebbe che *oggi* coincidono; così invece
si prova che **non possono divergere**, perché la regola sta scritta in un posto
solo. Il presidio da mantenere non è «gli esiti coincidono», è *«il guard non
contiene più il predicato»*.

---

### ⚠️ Cosa è un pareggio, e cosa invece si risolve da sé

Non tutte le coppie di titoli che coprono la stessa riga sono un errore:

| due titoli, stesso cliente / emittente / tipo, periodi che si toccano | esito |
| --- | --- |
| entrambi valgono per **tutto** | ⛔ lo ferma il vincolo `ex_soggetti_titoli_iva_no_overlap` |
| uno per tutto + uno su un **articolo** | ✅ vince il più specifico |
| uno su un **articolo** + uno su una **categoria** | ✅ vince l'articolo |
| entrambi sullo **stesso oggetto, stesso livello** | ⛔ **questa funzione** |

⭐ Solo l'ultima riga è un pareggio: due titoli **indistinguibili per specificità**. A
parità di specificità non c'è niente da scegliere — è un errore di configurazione, e
si solleva invece di prenderne uno a caso. *Un'ambiguità che si risolve sull'ordine
degli identificativi non è una scelta: è un difetto del modello.*

⚠️ **Livelli diversi non vanno bloccati**, ed è il caso più normale che esista:
articolo > categoria di merce > tutto è la stessa cascata degli indirizzi. Un
controllo scritto largo passerebbe ogni altra verifica e rifiuterebbe una
configurazione perfettamente legittima — per questo esiste il test gemello che
pretende che quel caso **passi**.

---

### ⚠️ Perché copre solo i titoli ristretti

Per i titoli che valgono per **tutto** la sovrapposizione la chiude un vincolo di
database vero (`EXCLUDE USING gist`), che è più forte di qualunque guard. Questa
funzione copre l'altra metà — quella che un vincolo non può raggiungere, perché la
chiave passa da una **tabella figlia**.

La divisione è **dichiarata**: vincolo dove è esprimibile, guard dove non lo è.
Scriverli entrambi come guard avrebbe indebolito il caso forte.

---

### ⚠️ Gira con i privilegi di chi la chiama, ed è motivato

Un guard che legge sotto row security di solito non distingue *«non lo vedo»* da
*«è di un altro»*, e per questo si scrive con privilegi elevati.

⭐ Qui no: il confronto è fra titoli verso lo **stesso emittente**, quindi la policy
è la stessa per entrambi — chi vede uno vede l'altro. Non esiste il conflitto
invisibile che renderebbe cieco il controllo, e una funzione privilegiata in più non
chiuderebbe nessun buco.

---

### Codici errore nominati

| Codice | Motivo |
| --- | --- |
| `E_TITOLO_IVA_AMBITO_NON_AMMESSO` | righe di ambito su un titolo che vale per tutto (`DATO_ERRATO`, 400) |
| `E_TITOLO_IVA_AMBITO_SOVRAPPOSTO` | il pareggio (`DATO_ERRATO`, 400) |

⚠️ La funzione **nomina** i codici, non li solleva: sollevare è mestiere di chi la
chiama. L'**ordine** dell'elenco è il contratto — se divergesse, il codice sollevato
e il motivo mostrato direbbero cose diverse.

⚠️ Un titolo inesistente ritorna `[]`, cioè «nessun ostacolo»: una `fn_check_*`
elenca motivi, non arbitra l'esistenza.

Cantiere: `brief-db-be-iva-risolutore-e-regime-cliente.md`, `I7` / `D10` / `D13`.

---

{% include-markdown "signature-core.md" %}
