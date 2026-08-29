## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_consuma_plafond_titolo_iva()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva)
> • [anagrafiche.soggetti_titoli_iva_movimenti](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva_movimenti)
> • [config.tipi_titolo_iva](/dbzero/config/tabelle/tipi_titolo_iva)
>
Approfondimento funzioni:
> • [anagrafiche.trgfn_soggetti_titoli_iva_movimenti_accumulatore](/dbzero/anagrafiche/funzioni/trgfn_soggetti_titoli_iva_movimenti_accumulatore) — chi riporta la somma sul titolo

---

### 🎯 Scopo Principale

(rev 2026-08-29 — funzione nata il 2026-08-29)

Consuma la capienza di un titolo IVA che ha un tetto, e restituisce **come si divide
l'imponibile** fra la parte coperta dal titolo e quella che torna all'aliquota
ordinaria.

**Invariante**: `quota_coperta + quota_ordinaria = imponibile passato`, sempre e su
tutti i rami.

---

### ⭐ Ritorna una ripartizione, non un codice IVA

Il plafond può finire **a metà riga**: si chiede di coprire 1000, ne restano 700 →
700 non imponibili e 300 ad aliquota ordinaria.

Una funzione che restituisse la sola quota coperta obbligherebbe chi la chiama a
ricostruire l'altra metà per conto suo — cioè farebbe **uscire la regola proprio nel
caso per cui esiste**. È la stessa ragione per cui anche il risolutore IVA ritornerà
una ripartizione e non un codice.

---

### 🔴 Il lock non è prudenziale: è la ragione per cui questa funzione esiste

Finché due fatture sono in bozza, entrambe **proiettano** sullo stesso residuo non
ancora consumato — ed è corretto, sono anteprime.

⛔ Ma se diventano definitive **nello stesso momento**, senza lock consumano la stessa
capienza e **il plafond va sotto zero in silenzio**: nessun errore, nessun sintomo,
su precisamente il numero che l'Agenzia delle Entrate verifica.

Il blocco della riga del titolo (`FOR UPDATE`) mette in fila le due transazioni: la
seconda legge il residuo **già aggiornato** dalla prima.

---

### ⚠️ Il lock non basta, e la seconda metà è dichiarata

Serve anche un **ordine deterministico** — *chi arriva prima si prende la capienza* —
e «prima» dev'essere una regola del dominio (data documento, poi numero), non
l'ordine di arrivo dei processi.

⛔ **Quella metà non è realizzabile qui**, e dirlo è meglio che finirlo: un lock non
può sapere che esiste una fattura precedente **non ancora arrivata**.

⭐ Divisione del lavoro, e ciascuna metà vive dove è esprimibile:

| Chi | Cosa garantisce |
| --- | --- |
| il **database** | che il conto non vada sotto (lock + capienza) |
| il **chiamante** | **chi** prende la capienza — il giro di fatturazione deve iterare le fatture in ordine di data documento, poi numero |

⚠️ La seconda è una richiesta esplicita al backend, scritta nel cantiere e da
onorare quando il consumo entrerà nella transizione a definitiva. Il registro rende
comunque l'ordine **verificabile a posteriori**.

---

### ⛔ Non è il risolutore, e non fa la restituzione

* **Non è il risolutore IVA**: quello è in sola lettura e non consuma. Un risolutore
  che consumasse non si potrebbe chiamare per mostrare un'**anteprima** — che è
  precisamente l'uso che ne fa il documento a monte;
* **non fa la nota di credito**: restituire plafond è una riga di registro con
  importo negativo, senza capienza da calcolare e senza spezzatura da decidere.
  Metterla qui avrebbe prodotto una funzione con **due comportamenti opposti sotto
  lo stesso nome**.

---

### I rami, e cosa fanno

| Situazione | Esito |
| --- | --- |
| titolo **senza tetto** (uso industriale, agevolata, cooperativa) | copre tutto, **non scrive nessun movimento** |
| capienza sufficiente | copre tutto, scrive un movimento |
| capienza insufficiente | **si spezza**: copre fino a capienza, il resto torna ordinario |
| stessa fattura, seconda chiamata | **idempotente**: rilegge il movimento che c'è, non ne scrive un secondo |

⚠️ Su un titolo senza tetto non si scrive un movimento «a saldo zero»: allungherebbe
il registro senza dire niente, e la riconciliazione dovrebbe imparare a ignorare
delle righe.

⚠️ Su un titolo già sfondato da una forzatura il residuo è negativo, e la capienza si
legge come **zero e non come un numero al contrario** — altrimenti un consumo
*restituirebbe* capienza.

---

### Codici errore

| Codice | Motivo |
| --- | --- |
| `E_TITOLO_IVA_CONSUMO_NON_INVOCABILE` | parametro assente o non valido, o titolo inesistente (`TECNICO`, 500) |
| `E_TITOLO_IVA_CONSUMO_FUORI_VALIDITA` | si consuma a una data fuori dalla validità del titolo (`TECNICO`, 500) |

⚠️ Entrambi **tecnici**, e non è una svista: nessuno dei due può essere prodotto da
una persona che compila un form — li produce chi chiama male. Ne discende che nel
contesto **non** va la chiave `campo`: su un 500 non c'è nessun campo da accendere.

⭐ Il secondo sembra impossibile e va tenuto lo stesso: chi sceglie il titolo guarda
la data del documento, quindi per una strada normale non ci si arriva. Ma senza
cancello sarebbe un **plafond consumato da una fattura che quel titolo non copre
più** — invisibile.

Cantiere: `brief-db-be-iva-risolutore-e-regime-cliente.md`, `I7` / `D15-bis` / `P2`.

---

{% include-markdown "signature-core.md" %}
