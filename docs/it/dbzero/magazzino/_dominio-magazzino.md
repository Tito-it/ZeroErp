> **Ultimo aggiornamento**: 1 novembre 2026

### 🏗️ Lo stato del dominio `magazzino`

La merce ha **una porta sola** per entrare e uscire: la primitiva
`magazzino.fn_scrivi_movimento`. Il registro dei movimenti e la copia del valore non sono
scrivibili dall'applicazione: ci arrivano soltanto le **operazioni**, ciascuna con il proprio
verbo, che chiamano la porta una volta per movimento nella stessa transazione.

Le operazioni che oggi muovono merce:

* l'**inventario** (`fn_posta_inventario`), che registra le differenze fra il contato e il
  registro, e il primo carico di un articolo;
* la **rettifica** (`fn_posta_rettifica`), la correzione a mano;
* il **trasferimento interno** (`fn_posta_trasferimento`), fra due ubicazioni dello stesso
  magazzino o fra due magazzini dello stesso emittente, senza trasporto;
* la **bolla di vendita** (`vendite.fn_posta_ddt`): lo scarico all'emissione e, per la bolla
  di trasferimento, l'arrivo alla consegna;
* il **reso** (`vendite.fn_posta_reso`): il carico della merce che rientra, al costo al quale
  era uscita.

Lo **storno** di un'operazione registrata lo scrive `fn_storna_movimenti_sorgente`, che i
verbi di annullo (della bolla, del reso) chiamano. Il **blocco manuale** di merce per
qualcuno si apre e si libera con `fn_apri_blocco` e `fn_libera_blocco`. La **disponibilità**
ha una vista e un controllo con la stessa formula.

---

### Il disegno in una riga

```text
operazione (riga di inventario, di rettifica, di trasferimento · prelievo di bolla · rientro di reso)
   └─→ PORTA     magazzino.fn_scrivi_movimento   (l'unica scrittura: controlla, blocca, valorizza)
          └─→ registro  magazzino.movimenti   (sorgente a catalogo · quantità con segno in unità base · identità per tranche)
                 ├─→ giacenza       vw_giacenza, vw_giacenza_ubicazione     (somma del registro)
                 ├─→ valore         magazzino.valore_giacenza               (copia ricostruibile: fn_ricalcola_valore_giacenza)
                 │                    └─→ vw_costo_medio, vw_costo_medio_globale, vw_giacenza_valorizzata
                 └─→ disponibilità  vw_disponibilita, vw_disponibilita_articolo   (giacenza + blocchi aperti)
attese   magazzino.movimenti_attesi   (blocco manuale: ciò che i documenti non dicono)
```

⭐ **Il registro è l'unica scrittura che conta.** Ogni movimento porta la sua **sorgente**
(quale operazione lo ha generato: obbligatoria, a catalogo, verificata), il **verso** nella
quantità (con il segno, coerente con la causale: un guard lo pretende), la quantità in
**unità base**, e un'**identità** che è l'operazione per tranche (lotto, pezzo serializzato,
posizione). Un movimento non si spegne: si **storna**, con un movimento contrario legato
all'originale.

I due cataloghi che guidano la scrittura: la **causale** (verso, rettifica, stock negativo)
e l'**articolo** (`gestito_a_magazzino`, `requires_lotto`, `requires_serial`), più il
**magazzino** (`usa_ubicazioni`: la grana del suo registro, che si cambia solo a registro
vuoto).

⭐ **La porta** (`fn_scrivi_movimento`, `SECURITY DEFINER`): controlla i parametri, la
causale, il verso, il magazzino, la **riga** (lotto, seriale, ubicazione:
`script.fn_check_riga_magazzino`), lo storno, la **posizione del pezzo serializzato**,
l'identità; in uscita blocca la coppia magazzino e articolo e rifiuta se manca merce o se è
**bloccata per altri** (`script.fn_check_disponibilita_uscita`); valorizza (la media
corrente in uscita, il costo dato o la media in entrata, il costo dell'uscita gemella
nell'arrivo di un trasferimento, il costo dell'originale nello storno) e scrive registro e
copia in un colpo.

---

### ⭐ Il registro non conosce chi lo usa

Il magazzino è un servizio per gli altri domini: chi muove merce scrive il **proprio**
posting e chiama la porta, e il registro non legge le tabelle di un documento. Per questo i
posting della bolla e del reso stanno in `vendite`, non qui. Nessun oggetto dello schema
`magazzino` nomina uno schema di processo (`vendite`, `acquisti`, `pagamenti`): lo presidia
la spia `dbops.vw_magazzino_dipendenze_inverse`, che deve restare vuota.

---

### Le famiglie di oggetti

* **Anagrafiche** — `magazzini` (di un **emittente**: è l'ancora del perimetro; si creano
  con `fn_crea_magazzino`), `ubicazioni`, `assets` (il pezzo serializzato, anch'esso di un
  emittente; la sua posizione la dice il registro), `lotti` (la partita di merce).
* **Documenti interni** — `inventari`, `rettifiche`, `trasferimenti`, ciascuno con le
  proprie righe: sono le **operazioni** del magazzino, e ogni riga è la sorgente dei suoi
  movimenti. Le tre famiglie hanno lo stesso ciclo: dalla bozza (`DRAFT`) alla conferma
  (`CONFIRM`), da cui si registra (`POSTED`), si annulla (`CANCEL`) o si riapre in bozza.
  * La matrice degli stati sta in una sede sola, `fn_documento_interno_transizioni`: la
    leggono il guard che la fa rispettare e la capability che disegna i pulsanti
    (`script.fn_available_actions_documento_interno`).
  * `POSTED` lo scrive solo il verbo dell'operazione; se il documento si può registrare lo
    dice `script.fn_check_documento_interno_registrabile`, la stessa check che il verbo
    solleva e che dà il motivo al pulsante «Registra».
  * Le righe si scrivono solo in bozza e si congelano con la testata; si cancella solo una
    bozza.
  * Il **magazzino** di un inventario o di una rettifica non si cambia in nessuno stato: è
    l'identità del documento, non un suo attributo. La `data` invece resta modificabile.
  * L'inventario ha un **piano** (`fn_inventario_piano`): per ogni posizione, il contato,
    il registro, la differenza e che cosa la registrazione ne farà. È la stessa sede per il
    video e per la registrazione.
* **Eventi degli asset** — `eventi_assets`: la vita di un pezzo serializzato (installazione,
  rientro, sostituzione, manutenzione). Oggi non c'è un'operazione che li registri a
  magazzino.
* **Registro e derivati** — `movimenti`, `movimenti_attesi`, `valore_giacenza` e le sette
  viste (giacenza, giacenza per ubicazione, costo medio, costo medio globale, giacenza
  valorizzata, disponibilità, disponibilità per articolo), tutte `security_invoker`.
* **Note** — `magazzino.note`, partizionata per bersaglio, con il perimetro sul padre e su
  ogni partizione.

---

### Il perimetro

Tutto ciò che porta merce o valore è sotto **row level security**: un operatore vede e scrive
i magazzini del proprio emittente e tutto ciò che vi risale, dal magazzino, dall'asset, dalla
testata. Nessuna operazione attraversa due emittenti: un trasferimento fra magazzini di
emittenti diversi si rifiuta. Restano fuori, per costruzione, i vocabolari e le definizioni
uguali per tutti (`causali`, `lotti`, `config.tipi_ubicazione`, `config.assets_ownership`).
Il meccanismo è quello comune del progetto:
[Linee guida SQL — sezione 10](/linee-guida-sql#10-row-level-security-rls).

---

### ⚠️ La porta: un dominio a metà

Il modello dei permessi vuole che ogni scrittura passi da un **verbo**, cioè una funzione
del database che prima controlla il permesso di chi agisce, e che l'applicazione non possa
scrivere le tabelle da sola
([guida dei permessi §7.4](/guide/architettura-permessi-e-autorizzazioni#74-il-permesso-nel-verbo-di-scrittura)).
`magazzino` ci è arrivato **solo in parte**, e la regola chiede di dirlo qui, con l'elenco.

**Chiuse all'applicazione** (le scrive solo un verbo):

| Tabella | Chi la scrive |
| --- | --- |
| `movimenti`, `valore_giacenza` | la porta del registro, attraverso i verbi che registrano (inventario, rettifica, trasferimento, bolla, reso, storno) |
| `movimenti_attesi` | i verbi del blocco manuale (`fn_apri_blocco`, `fn_libera_blocco`) |
| `causali` | il verbo del pannello di configurazione (`config.fn_pannello_scrivi`) |

**Ancora scrivibili dall'applicazione** (il permesso lo controlla solo il backend):

| Tabella | Oggi la scrive |
| --- | --- |
| `magazzini`, `ubicazioni`, `lotti` | il backend, dalle anagrafiche di magazzino (il magazzino nasce con `fn_crea_magazzino`, che non controlla un permesso) |
| `inventari`, `rettifiche` e le loro righe | il backend: la testata, le righe in bozza e i cambi di stato prima della registrazione. Già chiusi: il passaggio a «registrato» e le righe di un documento confermato, che tocca solo il verbo |
| `trasferimenti` e le sue righe | nessuno dall'applicazione; il passaggio a «registrato» è già chiuso |
| `assets`, `eventi_assets` e le tabelle delle note | nessuno dall'applicazione |

Il lavoro che chiude il resto è aperto. Quando sarà fatto, questa sezione si riduce a una
riga.

---

### Che cosa manca ancora

* le **operazioni** degli eventi degli asset e il **ricevimento** della merce da fornitore
  (il carico del ciclo acquisti);
* le colonne «impegnata» e «in arrivo» della disponibilità: arrivano con i satelliti che le
  sanno riempire (acquisti);
* il verbo per le scritture che l'applicazione fa ancora da sola (sezione precedente).
