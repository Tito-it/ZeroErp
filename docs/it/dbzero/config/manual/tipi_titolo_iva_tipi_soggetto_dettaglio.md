## 📘 Documentazione Concettuale – Tabella `config.tipi_titolo_iva_tipi_soggetto_dettaglio`

> 👀 **Vedi anche**
>
> [config.tipi_titolo_iva](/dbzero/config/tabelle/tipi_titolo_iva) ·
> [config.tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_soggetto_dettaglio) ·
> [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/manual/soggetti_titoli_iva)

### 🎯 Scopo

Dice **chi può essere titolare** di ogni tipo di titolo IVA, per natura di dettaglio del
soggetto. Ogni titolo ha un destinatario preciso: la dichiarazione d'intento la presenta un
esportatore abituale, cioè un soggetto IVA; l'agevolazione per disabilità (L. 104/1992) spetta a
una persona fisica.

| Titolo | Nature che lo ammettono |
| --- | --- |
| Dichiarazione d'intento (`INTENTO`) | ditta individuale, società di persone, società di capitali, ente |
| Uso industriale o agricolo (`USO_INDUSTRIALE`) | ditta individuale, società di persone, società di capitali, ente |
| Agevolazione L. 104 (`AGEVOLATA_104`) | solo il privato |
| Cooperativa sociale o ente del terzo settore (`COOPERATIVA`) | nessuna, finché non è chiarito che cosa registra |

### ⭐ Nessuna riga vuol dire «non ammesso»

Un tipo di titolo senza righe per una natura **non è libero**: è vietato. Una natura che nasce
domani (un dettaglio estero, per esempio) non ammette nessun titolo finché qualcuno non lo
dichiara qui.

### Come si cambia

* Le righe arrivano dal CSV del catalogo (`80_data/sql/config/tipi_titolo_iva_tipi_soggetto_dettaglio.csv`).
* Una riga si **ritira** con `attivo = false` nel CSV, mai cancellandola.
* ⛔ Il ritiro è rifiutato (`E_TITOLO_IVA_AMMISSIONE_IN_USO`) finché esistono titoli **in vigore**
  di quel tipo su soggetti di quella natura: prima si chiudono i titoli, poi si ritira la riga.

### Chi la legge

La domanda «la natura ammette questo titolo?» ha una sede sola,
`anagrafiche.fn_titolo_iva_ammesso`. La usano i tre guard della regola: sul titolo, sul cambio di
natura del soggetto e sul ritiro di una riga di questa tabella (vedi
[anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/manual/soggetti_titoli_iva)).
