## 📘 Documentazione Concettuale – Funzione `pagamenti.trgfn_vendite_contabili_righe_guard_transizione`

### 🎯 Scopo Principale
(rev 2026-08-21)

Enforcement **DB-first** del grafo degli stati della **riga contabile**, letto da
`pagamenti.transizioni_stati_contabile_riga`. Gemello della funzione sulla testata.

### Regole applicate
* No-op se lo stato non cambia davvero.
* La transizione deve esistere ed essere attiva in matrice.
* ⭐ **`POSTATA` è terminale**, e non è un dettaglio: è l'unico stato dopo il quale
  esiste un fatto — il movimento contabile.

### 🔴 Chiude un difetto misurato
Il giro dei fondi fattura (`vendite.fn_sync_contabili_fondo_fattura`) cerca la
propria riga contabile **senza filtrare lo stato** e, trovandola, la riporta ad
`ABBINATA`. Su una riga già registrata questo faceva **contare lo stesso denaro
due volte** — nel saldo contabile *e* nel saldo movimenti — su una fattura che
nessuno stava guardando. Ed è su percorso vivo: il ricalcolo dei totali della
fattura chiama quel giro **sempre**.

Da adesso il database **rifiuta** quel passaggio.

⚠️ Non rende inutile la difesa prevista lato fondi: lì il fondo esce dal ciclo con
uno stato dedicato e il giro **non arriva più** a quella riga; qui ci arriva e si
ferma con un errore, il che su percorso vivo significa una pipeline che cade. Le
due cose vanno insieme.

### Quando si attiva
* `BEFORE UPDATE OF stato_id` su `pagamenti.vendite_contabili_righe`.
* ⚠️ Mai sull'INSERT: il giro dei fondi crea le sue righe direttamente in
  `ABBINATA`.

### ⚠️ Error handling
* `E_RIGA_CONTABILE_TRANSIZIONE_NON_AMMESSA` (`CONFLITTO_STATO`, 409).

### ⚠️ Ordine fra i guard della stessa tabella
I `BEFORE ROW` scattano in ordine **alfabetico**. Su `vendite_contabili_righe`:
`guard_distinta_finale` → `guard_stato_dati` → `guard_transizione`. È l'ordine
giusto: se la distinta è chiusa non ha senso discutere del bagaglio della riga.

{% include-markdown "signature-core.md" %}
