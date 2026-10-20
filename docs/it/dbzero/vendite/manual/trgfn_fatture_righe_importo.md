## ⚙️ Documentazione Concettuale – Trigger `vendite.trgfn_fatture_righe_importo`

> **Versione**: 2026-07-28 (brief-fix-importi-riga-fattura-zero §4.1, D1 ·
> migration `20260728-09` funzione, `20260728-10` armamento)

> **Vedi anche**
>
[vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe)
> [script.fn_arrotonda_importo](/dbzero/script/funzioni/fn_arrotonda_importo)
> [vendite.articolo_regole_fatturazione](/dbzero/vendite/tabelle/articolo_regole_fatturazione)

---

### 🎯 Scopo Principale

Garantire che **l'importo di una riga di fattura esista sempre e sia coerente**
con quantità, prezzo e sconto della riga stessa.

Armato come `BEFORE INSERT OR UPDATE FOR EACH ROW`, fase `a20`:

```
imponibile_riga = script.fn_arrotonda_importo(
      qta × prezzo_unitario × (1 − COALESCE(sconto_percentuale,0)/100),
      decimali,   ← vendite.fn_parametri_importo_riga(articolo, emittente, utility)
      metodo      ← idem: la regola dell'articolo, altrimenti i parametri
                    effettivi dell'emittente per l'utility della fattura
  )
```

---

### Il difetto che chiude

La colonna `imponibile_riga` esisteva dal principio, ma **nessuno la scriveva**:
né `fn_generate_fatture_righe`, né il repository Python, né un trigger. Sette
righe su sette a `NULL`, che `fn_ricalcola_riepilogo_iva_fattura` trasformava in
zero con un `COALESCE`, fino a produrre fatture con **totale 0,00 €** — il 100%
di quelle emesse dal sistema.

La regola era persino già scritta nel manuale della tabella, ma classificata come
voce *«opzionale»* di roadmap: mai implementata, mentre il backend la dava per
fatta.

---

### Perché un trigger e non una colonna generata

La prima soluzione applicata fu una `GENERATED ALWAYS AS … STORED`, che è il
presidio più forte in assoluto — lo calcola il motore, nessuno può scriverla
diversa. È stata **revocata** per un vincolo tecnico: una colonna generata può
usare **solo dati della propria riga**, e non può quindi leggere
`vendite.articolo_regole_fatturazione`, che configura decimali e metodo **per
articolo**.

Poiché `articolo_id` è una colonna della riga, un trigger ci arriva. Si perde la
garanzia del motore, ma poco: un `BEFORE INSERT OR UPDATE` scatta comunque per
**ogni** scrittore, funzione DB o Python che sia. La differenza è teorica — un
trigger si può disabilitare, il motore no — non pratica.

---

### ⚠️ Cosa si è perso, e come è compensato

Con la colonna generata un valore di `imponibile_riga` passato dall'esterno
faceva **fallire** la scrittura. Con il trigger viene **sovrascritto in
silenzio**: il risultato finale è lo stesso — il valore esterno non sopravvive
mai — ma la segnalazione sparisce.

La compensazione è un test dedicato in
`db/pgtap/vendite/test-fatture-righe-importo-e-kit-v1.sql` (caso 7), che verifica
proprio che un valore imposto non sopravviva. È ciò che tiene oneste le fixture,
che fino al 2026-07-28 iniettavano l'importo a mano — ed è il motivo per cui il
difetto è sopravvissuto a una suite verde.

---

### Cosa NON fa

**Non tocca `qta`.** La quantità arriva già pronta da chi scrive la riga, e con
l'aggregazione è la somma **esatta** delle attività che la compongono.
`arrotondamento_quantita_dec` si applica alla quantità della **singola attività**,
a monte, mai all'aggregato: arrotondare la somma perderebbe precisione dove
nessuno la cerca.

---

### Fallback e ordine

Le regole per articolo sono opzionali. Dal 21-10-2026 (brief-db-modelli-documento-standard
§10.7 R-3) i parametri li dice il BB
[vendite.fn_parametri_importo_riga](/dbzero/vendite/funzioni/fn_parametri_importo_riga): la
regola dell'articolo se c'è, altrimenti i parametri effettivi dell'emittente per l'utility della
fattura (la sua riga, poi per il metodo la policy generale, poi il valore di sistema), cioè la
stessa catena del totale. Prima era il letterale `2 / HALF_UP`, ripetuto anche nel servizio Python
(`_GROUP_ATTIVITA_SELECT`), che passa al BB nello stesso giro.

Senza regole dell'articolo e su una fattura **senza utility** non c'è da dove prendere i
parametri: `E_CONFIG_MANCANTE`, come il ricalcolo dei totali. Nell'applicazione non succede: la
testata non nasce senza utility.

Ordine dei trigger `BEFORE` sulla tabella:

```
a10  guard_congelamento   → può respingere l'operazione
a20  importo              → calcola l'imponibile          ← questo
---  audit / tx_id / guard_normalize
z90  storico
```

Un'operazione respinta dal guard non arriva mai al calcolo.

---

<!-- rev-2026-09-28-liste-righe -->
### 🔄 rev 2026-09-28 — brief-db-liste-righe-documento

L'imponibile **pieno** viene da [script.fn_imponibile_riga](/dbzero/script/funzioni/fn_imponibile_riga) (`20260928-26`); l'arrotondamento configurato per articolo (decimali e metodo, ripiego sui parametri dell'emittente per l'utility dal 21-10-2026) resta esattamente dov'era: è la politica del documento fiscale, non della formula. Il valore scritto non cambia.
