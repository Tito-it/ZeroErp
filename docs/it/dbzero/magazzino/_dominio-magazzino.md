### 🏗️ Lo stato del dominio `magazzino` (2026-09-18)

⚠️ **Primitiva e prime due operazioni in esercizio, porta chiusa.** Il modello è stato messo
nella forma stabilita dalle tre analisi di settembre (carico e scarico, aggancio ai
documenti, commessa e produzione) con il Lotto 1 — `brief-db-magazzino-lotto-1-terreno-vuoto`
— e con il Lotto 2 — `brief-db-magazzino-lotto-2-motore` — la merce ha **una porta sola**
per entrare e uscire: `magazzino.fn_scrivi_movimento`. Il registro e la copia del valore
non sono più scrivibili dall'applicazione (`REVOKE`), l'**inventario** e la **rettifica**
sono le prime due operazioni che passano dalla porta (`fn_posta_inventario`,
`fn_posta_rettifica`), la **disponibilità** ha una vista e una check con la stessa formula.
Le tabelle operative restano vuote fino al primo uso: le pagine descrivono il ruolo di
ciascun oggetto e le regole che il database fa rispettare, non un processo osservato.

---

### Il disegno in una riga

```
operazione (riga di inventario, di rettifica · poi bolla, trasferimento, evento di un asset)
   └─→ PORTA     magazzino.fn_scrivi_movimento   (l'unica scrittura: controlla, blocca, valorizza)
          └─→ registro  magazzino.movimenti   (sorgente a catalogo · qta firmata in UoM base · identità per tranche)
                 ├─→ giacenza       vw_giacenza, vw_giacenza_ubicazione     (somma del registro)
                 ├─→ valore         magazzino.valore_giacenza               (copia ricostruibile: fn_ricalcola_valore_giacenza)
                 │                    └─→ vw_costo_medio, vw_costo_medio_globale, vw_giacenza_valorizzata
                 └─→ disponibilità  vw_disponibilita, vw_disponibilita_articolo   (giacenza + blocchi aperti)
attese   magazzino.movimenti_attesi   (blocco manuale, prelievo non uscito: ciò che i documenti non dicono)
```

⭐ **Il registro è l'unica scrittura che conta.** Ogni movimento porta la sua **sorgente**
(quale operazione lo ha generato — obbligatoria, a catalogo, verificata), il **verso**
nella quantità (firmata, coerente con la causale: un guard lo pretende), la quantità in
**unità base**, e un'**identità** che è l'operazione per tranche (lotto, pezzo serializzato,
posizione). Non si spegne: si **storna**, con un movimento contrario legato all'originale.

I due cataloghi che guidano la scrittura: la **causale** (verso, rettifica, stock negativo)
e l'**articolo** (`gestito_a_magazzino`, `requires_lotto`, `requires_serial`), più il
**magazzino** (`usa_ubicazioni`: la grana del suo registro, decisa alla nascita).

⭐ **La porta** (`fn_scrivi_movimento`, `SECURITY DEFINER`): controlla i parametri, la
causale, il verso, il magazzino, la **riga** (lotto, seriale, ubicazione: `fn_check_riga_magazzino`),
lo storno, la **posizione del pezzo serializzato**, l'identità; in uscita prende un lock per
`(magazzino, articolo)` e rifiuta se manca merce o se è **bloccata per altri**
(`fn_check_disponibilita_uscita`); valorizza (media corrente in uscita, costo dato o media in
entrata, la gemella nel trasferimento) e scrive registro e copia in un colpo. Un'operazione
che genera N movimenti la chiama N volte nella stessa transazione.

---

### Le famiglie di oggetti

* **Anagrafiche** — `magazzini` (di un **emittente**: è l'ancora del perimetro),
  `ubicazioni`, `assets` (il pezzo serializzato, anch'esso di un emittente), `lotti` (la
  partita di merce).
* **Documenti interni** — `inventari`, `rettifiche`, `trasferimenti`, `eventi_assets`,
  ciascuno con le proprie righe: sono le **operazioni** che generano movimenti, e ogni riga
  ne è la sorgente. La correzione a mano è una rettifica. Inventari e rettifiche hanno il
  ciclo `DRAFT → CONFIRM → POSTED` (o `CANCEL`) fatto rispettare da un guard, `POSTED` lo
  scrive solo l'operazione (`fn_posta_inventario`, `fn_posta_rettifica`), le righe si
  congelano con la testata, si cancella solo una bozza. Il **magazzino** della testata non
  si cambia in nessuno stato (lock di colonna, dal 22-09): è l'identità del documento, non
  un suo attributo — la `data` invece resta modificabile, per decisione.
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

* le **operazioni** oltre a inventario e rettifica: trasferimento (la gemella è già prevista
  dalla porta), eventi degli asset, il ricevimento e la bolla (Lotti 3-5);
* l'**utility di storno** (Lotto 3): la porta sa già scrivere uno storno, manca il verbo che
  lo chiede dal documento;
* le colonne «impegnata», «in arrivo» della disponibilità: arrivano con i satelliti che le
  sanno riempire (acquisti).

✅ **Non manca più, dal 22-09-2026**: la **capability** dei documenti interni
(`script.fn_available_actions_inventario` / `_rettifica`), con la matrice degli
stati uscita dal guard in una sede che guard e pulsanti condividono
(`magazzino.fn_documento_interno_transizioni`) e la terna «Registra» dalla check
che le due madri del posting sollevano
(`script.fn_check_documento_interno_registrabile`). Era R-1 del Lotto 2-bis, e
senza il drawer non aveva da dove prendere i propri pulsanti.

✅ **Non manca più, dal 18-09-2026**: `requires_lotto` nel **drawer** dell'articolo
(richiesta del Lotto 2 §4.9, Pezzo 0 del piano BE/FE).

✅ **Non manca più, dal 23-09-2026**: il **lato applicativo** del Lotto 2 —
inventario e rettifica da video (lista, drawer, righe, piano, «Registra» dalla
capability), disponibilità e registro dei movimenti. Pagina API:
[api_magazzino](/backend/magazzino/manual/api_magazzino). ⏳ Il collaudo a video
è di Tid ([copione](/dev/work-in-progress/collaudo-in-app-magazzino-inventario-e-rettifica)).

---

### Storia in tre righe

* 2026-08-21 — documentazione concettuale scritta leggendo lo schema; primo pgTAP del
  dominio.
* 2026-09-01 → 14 — le analisi: M-1 → M-9 (carico e scarico), D-1 → D-9 (aggancio ai
  documenti), la commessa rinviata.
* 2026-09-14 → 15 — il Lotto 1: il DDL deciso sul terreno vuoto, il guard del verso, il
  perimetro RLS, cinque pgTAP (65 asserzioni). `reservations` → `movimenti_attesi`,
  `costo_medio` → `valore_giacenza`, `ambito_causale` ritirata.
* 2026-09-18 — il Lotto 2: la porta (`fn_scrivi_movimento`), il `REVOKE` all'app sul registro
  (tre sedi), inventario e rettifica postati dalla porta, disponibilità, ricalcolo del valore,
  quattro spie in `dbops.presidi`, 27 codici `E_MAG_*`, dodici pgTAP nuovi.
* 2026-09-22 → 25 — il Lotto 2-bis (capability, codici, `registra_magazzino`), i verbi
  che controllano il permesso, e il lato BE/FE: il primo carico si fa da video.
