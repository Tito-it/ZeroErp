## 📘 Documentazione Concettuale – Funzione Trigger `anagrafiche.trgfn_soggetti_titoli_iva_guard_coerenza`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva)
> • [config.tipi_titolo_iva](/dbzero/config/tabelle/tipi_titolo_iva)

---

### 🎯 Scopo Principale

(rev 2026-08-29 — funzione nata il 2026-08-29)

Tiene le due regole del titolo IVA che un controllo di colonna **non può
esprimere**, perché guardano fuori dalla riga:

1. **il plafond esiste se e solo se il tipo ne prevede uno** → deve leggere
   `config.tipi_titolo_iva.ha_plafond`, cioè un'**altra tabella**;
2. **un titolo che vale per tutto non ha righe di ambito** → deve contare le righe
   **figlie**.

---

### Contesto di Esecuzione

* **Tipo**: trigger `BEFORE INSERT OR UPDATE OF tipo_titolo_iva_id, plafond, ambito`
* **Fascia**: `a10` (guard, prima della scrittura)

---

### ⭐ La regola del plafond vale sui **due** versi

| Caso | Cosa succederebbe senza |
| --- | --- |
| tipo **con** tetto, plafond **assente** | la primitiva di consumo non avrebbe capienza da confrontare: coprirebbe zero o tutto, secondo come è scritta |
| tipo **senza** tetto, plafond **valorizzato** | il numero c'è, **nessuno lo consuma**, e chi lo guarda crede che quel titolo abbia un limite |

⭐ Il secondo è il verso che si dimentica, ed è la voce di partenza di questo cantiere
in miniatura: *un campo che promette una cosa che non succede*.

---

### ⚠️ Perché controlla l'ambito solo in aggiornamento

Il caso «vale per tutto **e** ha un elenco di voci» si crea in due modi, e questo
trigger ne copre uno solo:

* **aggiungendo una riga di ambito** a un titolo totale → lo ferma il guard sulle
  righe figlie;
* **riportando a `TUTTO`** un titolo che le righe ce l'ha già → lo ferma questo, ed è
  il verso che il guard sulle figlie non vedrebbe mai, perché lì non si tocca niente.

---

### ⚠️ Gira con i privilegi di chi lo chiama, ed è motivato

Un guard che legge sotto row security di solito non distingue *«non lo vedo»* da
*«è di un altro»*. Qui non serve elevarlo: le righe contate sono le **figlie della
riga stessa**, e la loro policy passa dallo stesso emittente del padre — chi può
scrivere il padre le vede **tutte**. Non esiste il caso «ce n'è una che non vedo».

---

### ⚠️ Il nome sceglie l'ordine, e non è estetica

I trigger che scattano prima della scrittura girano in ordine **alfabetico**. Le
chiavi esterne verso `config.iva` e `config.tipi_titolo_iva` faranno nascere dalle
automazioni dei guard `..._require_attivo_...`; `guard_coerenza` viene prima, quindi
**il messaggio che l'operatore legge è quello di dominio** e non quello generico.

---

### Codici errore

| Codice | Motivo |
| --- | --- |
| `E_TITOLO_IVA_PLAFOND_MANCANTE` | tipo con tetto, plafond assente (`DATO_ERRATO`, 400) |
| `E_TITOLO_IVA_PLAFOND_NON_AMMESSO` | tipo senza tetto, plafond valorizzato (`DATO_ERRATO`, 400) |
| `E_TITOLO_IVA_AMBITO_NON_AMMESSO` | titolo riportato a «vale per tutto» con righe di ambito ancora presenti (`DATO_ERRATO`, 400) |

⚠️ Se il tipo non esiste il guard **non inventa un secondo errore**: lascia parlare
la chiave esterna, che ha la sua voce.

Cantiere: `brief-db-be-iva-risolutore-e-regime-cliente.md`, `I7` / `D10`.

---

{% include-markdown "signature-core.md" %}
