### 🏗️ Lo stato del dominio `magazzino` (2026-09-15)

⚠️ **Forma decisa, perimetro armato, in attesa della primitiva.** Il modello è stato messo
nella forma stabilita dalle tre analisi di settembre (carico e scarico, aggancio ai
documenti, commessa e produzione) con il Lotto 1 — `brief-db-magazzino-lotto-1-terreno-vuoto`
— e **non c'è ancora una riga dentro**: tutte le tabelle operative sono vuote, popolati solo
i cataloghi da seed (`magazzino.causali`, 16 righe; le sorgenti di magazzino in
`config.sorgenti`). Non entra né esce merce finché non esiste la **primitiva di scrittura**
(Lotto 2): le pagine descrivono il ruolo di ciascun oggetto e le regole che il database fa
già rispettare, non un processo osservato.

---

### Il disegno in una riga

```
operazione (riga di bolla, di inventario, di rettifica, di trasferimento, evento di un asset)
   └─→ registro  magazzino.movimenti   (sorgente a catalogo · qta firmata in UoM base · identità per tranche)
          ├─→ giacenza       vw_giacenza, vw_giacenza_ubicazione     (somma del registro)
          └─→ valore         magazzino.valore_giacenza               (copia ricostruibile: ri-somma dei costi)
                               └─→ vw_costo_medio, vw_costo_medio_globale, vw_giacenza_valorizzata
attese   magazzino.movimenti_attesi   (blocco manuale, prelievo non uscito: ciò che i documenti non dicono)
```

⭐ **Il registro è l'unica scrittura che conta.** Ogni movimento porta la sua **sorgente**
(quale operazione lo ha generato — obbligatoria, a catalogo, verificata), il **verso**
nella quantità (firmata, coerente con la causale: un guard lo pretende), la quantità in
**unità base**, e un'**identità** che è l'operazione per tranche (lotto, pezzo serializzato,
posizione). Non si spegne: si **storna**, con un movimento contrario legato all'originale.

I due cataloghi che guidano la scrittura: la **causale** (verso, rettifica, stock negativo)
e l'**articolo** (`gestito_a_magazzino`, `requires_lotto`, `requires_serial`).

---

### Le famiglie di oggetti

* **Anagrafiche** — `magazzini` (di un **emittente**: è l'ancora del perimetro),
  `ubicazioni`, `assets` (il pezzo serializzato, anch'esso di un emittente), `lotti` (la
  partita di merce).
* **Documenti interni** — `inventari`, `rettifiche`, `trasferimenti`, `eventi_assets`,
  ciascuno con le proprie righe: sono le **operazioni** che generano movimenti, e ogni riga
  ne è la sorgente. La correzione a mano è una rettifica.
* **Registro e derivati** — `movimenti`, `movimenti_attesi`, `valore_giacenza` e le cinque
  viste, tutte `security_invoker`.
* **Note** — `magazzino.note`, partizionata per famiglia, con il perimetro sul padre e su
  ogni partizione.

---

### Il perimetro

Tutto ciò che porta merce o valore è sotto **row level security** (23 tabelle): un
operatore vede e scrive i magazzini del proprio emittente e tutto ciò che vi risale — dal
magazzino, dall'asset, dalla testata. Nessuna operazione attraversa due emittenti. Restano
fuori, per costruzione, i vocabolari e le definizioni uguali per tutti (`causali`, `lotti`,
`config.tipi_ubicazione`, `config.assets_ownership`). Il meccanismo è quello comune del
progetto: [Linee guida SQL — sezione 10](/linee-guida-sql#10-row-level-security-rls).

---

### Che cosa manca ancora, e dove sta

* la **primitiva di scrittura** e le operazioni (Lotto 2): finché non c'è, il registro è
  scrivibile dall'applicazione — il perimetro c'è, la porta no;
* la **disponibilità** (giacenza meno le attese) e la vista degli **orfani** del catalogo
  delle sorgenti (Lotto 2);
* l'**utility di storno** (Lotto 3); il ricevimento e gli ordini di lavoro (Lotti 4 e 5);
* il **default dell'emittente** su un magazzino creato dal pannello di amministrazione
  (punto aperto, brief §4.7).

---

### Storia in tre righe

* 2026-08-21 — documentazione concettuale scritta leggendo lo schema; primo pgTAP del
  dominio.
* 2026-09-01 → 14 — le analisi: M-1 → M-9 (carico e scarico), D-1 → D-9 (aggancio ai
  documenti), la commessa rinviata.
* 2026-09-14 → 15 — il Lotto 1: il DDL deciso sul terreno vuoto, il guard del verso, il
  perimetro RLS, cinque pgTAP (65 asserzioni). `reservations` → `movimenti_attesi`,
  `costo_medio` → `valore_giacenza`, `ambito_causale` ritirata.
