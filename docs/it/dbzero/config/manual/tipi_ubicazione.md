## 📘 Documentazione Concettuale – Tabella `config.tipi_ubicazione`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.ubicazioni](/dbzero/magazzino/tabelle/ubicazioni)
> • [magazzino.magazzini](/dbzero/magazzino/tabelle/magazzini)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Vocabolario dei **tipi di ubicazione** (bin) dentro un magazzino. Sei voci, che descrivono la
*funzione* di un'area e non la sua posizione:

| Codice | Funzione |
|---|---|
| `PICK` | prelievo |
| `STORAGE` | stoccaggio (bulk/scorta) |
| `STAGING` | baia o area di preparazione |
| `BUFFER` | polmone |
| `IN_TRANSIT` | in transito, per i trasferimenti fra magazzini |
| `DAMAGED` | merce non conforme |

⭐ `IN_TRANSIT` è quello che rivela il disegno: la merce che viaggia fra due magazzini **non
smette di esistere** durante il trasferimento — occupa un'ubicazione di transito. È ciò che
permette a un inventario di tornare anche mentre ci sono trasferimenti aperti.

`DAMAGED` fa un lavoro simile per la merce non conforme: resta in giacenza ma in un'area che
la esclude dal prelievo.

---

### ⚠️ Il vocabolario è popolato, il dominio no

Le sei righe ci sono (misurato il 2026-08-21), ma `magazzino` è lo schema con la copertura
documentale più bassa del progetto e le sue tabelle sono ancora quasi tutte senza
documentazione concettuale.

Va letta quindi come **vocabolario pronto per un dominio che non è ancora in esercizio**: le
voci sono state pensate, il processo che le usa no.

---

### Struttura da catalogo moderno

`codice_interno` (la chiave stabile per il codice), `codice` (quello che l'utente vede),
`descrizione`, `attivo`, `ordine` per la presentazione, `meta` JSONB.

⭐ La doppia chiave `codice_interno` / `codice` è il pattern corretto del progetto: il codice
interno non cambia mai ed è quello che il software nomina; il codice è etichetta, e può essere
riscritto senza rompere nulla.

---

{% include-markdown "signature-core.md" %}
