### 🏗️ Lo stato del dominio `magazzino` (2026-08-21)

⚠️ **Il dominio è predisposto, non in esercizio.** Misurato: **tutte** le tabelle operative
sono a **zero righe** — movimenti, giacenze, inventari, trasferimenti, rettifiche,
prenotazioni, magazzini, ubicazioni, asset. Le sole popolate sono i due vocabolari di
configurazione caricati dal seed: `magazzino.ambito_causale` (6) e `magazzino.causali` (10).

Va letto per quello che è: **un modello disegnato per intero e mai avviato**. Le pagine di
questo schema descrivono quindi il **ruolo previsto** di ciascun oggetto, non un processo
osservato. Dove il disegno lascia domande aperte, le pagine lo dicono invece di inventare una
risposta.

---

### Il disegno in una riga

```
causale + movimento  →  ledger (magazzino.movimenti)
                          ├─→ costo medio ponderato   (magazzino.costo_medio)
                          └─→ giacenza                (vw_giacenza, vw_giacenza_valorizzata)
```

⭐ **`magazzino.movimenti` è il libro mastro**: l'unica scrittura che conta. Giacenze e valori
non sono dati autonomi — sono **derivati** dal ledger, e questo è ciò che rende il magazzino
ricostruibile. Un saldo che non torna si spiega sempre risalendo ai movimenti; non esiste un
posto dove «correggere la giacenza» senza lasciare traccia.

La **causale** decide come il movimento si comporta: segno (carico/scarico), se richiede
lotto, seriale o magazzino di destinazione, se abilita la fatturazione, e che impatto ha sulla
valorizzazione.

---

### Le tre famiglie di oggetti

* **Anagrafiche** — `magazzini`, `ubicazioni` (i bin, tipizzati da `config.tipi_ubicazione`),
  `assets`.
* **Documenti interni** — `inventari`, `rettifiche`, `trasferimenti`, ciascuno con la propria
  tabella righe. Sono i documenti che *generano* movimenti, non li sostituiscono.
* **Derivati e servizio** — `costo_medio` (stato corrente del CMP), `reservations`
  (impegni di stock), e le quattro viste di giacenza e valorizzazione.

---

### ⚠️ Prima di attivare il dominio

* **La documentazione precede l'uso.** Queste pagine sono state scritte leggendo lo schema, non
  osservando un processo: quando il magazzino entrerà in esercizio andranno riviste contro il
  comportamento reale, e le domande aperte segnate con ⚠️ sono il punto da cui partire.
* **`config.ambiti` non c'entra.** Le causali si qualificano con `magazzino.ambito_causale`,
  un vocabolario autonomo. La tabella `config.ambiti` è vuota e non referenziata da nessuno:
  i nomi si somigliano, il legame non esiste.
* **Copertura documentale.** `magazzino` era, insieme ad `acquisti`, lo schema meno
  documentato del progetto. Queste pagine chiudono quel buco sul piano formale; il buco di
  *conoscenza* si chiude solo usando il dominio.
