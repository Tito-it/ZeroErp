## 📘 Documentazione Concettuale – Tabella `magazzino.ubicazioni`

> **Ultimo aggiornamento**: 1 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.magazzini](/dbzero/magazzino/tabelle/magazzini) — di chi è l'ubicazione
> * [config.tipi_ubicazione](/dbzero/config/tabelle/tipi_ubicazione) — il tipo di posizione
>
> Approfondimento viste:
>
> * [magazzino.vw_giacenza_ubicazione](/dbzero/magazzino/views/vw_giacenza_ubicazione) — che cosa c'è in ogni posizione
>
> Approfondimento funzioni:
>
> * [magazzino.trgfn_ubicazioni_guard_parent](/dbzero/magazzino/funzioni/trgfn_ubicazioni_guard_parent) — il padre nello stesso magazzino, niente cicli

---

### 🎯 Scopo Principale

**Le posizioni dentro un magazzino**: dove fisicamente sta la merce. La posizione è
descritta da coordinate progressive — `area`, `corsia`, `scaffale` e seguenti — e il **tipo**
viene da `config.tipi_ubicazione` (`PICK`, `STORAGE`, `STAGING`, `BUFFER`, `IN_TRANSIT`,
`DAMAGED`). `parent_id` rende le ubicazioni gerarchiche: un'area contiene corsie, che
contengono scaffali.

`tipo_id` è obbligatorio, `parent_id` no (le ubicazioni di primo livello non hanno padre).
Il codice è unico dentro il magazzino.

---

### La gerarchia vive dentro un magazzino

Il padre di un'ubicazione è **dello stesso magazzino**, e la catena dei padri non torna mai
su sé stessa: lo fa rispettare
[trgfn_ubicazioni_guard_parent](/dbzero/magazzino/funzioni/trgfn_ubicazioni_guard_parent).
Le query ricorsive possono contare sull'assenza di cicli. Il picker del drawer propone solo le
ubicazioni del magazzino: rispecchia la regola, non la sostituisce.

**`magazzino_id` non si cambia** dopo la creazione (lock delle colonne): un'ubicazione è una
posizione *dentro* un magazzino, e le figlie e i movimenti registrati la nominano insieme a
lui. Per spostarla si disattiva e se ne crea una nel magazzino giusto.

---

### Una posizione per movimento

Un movimento del registro porta **una** ubicazione (`movimenti.ubicazione_id`): uno
spostamento fra due posizioni dello stesso magazzino è una coppia di righe, un'uscita
dall'una e un'entrata nell'altra, e
[vw_giacenza_ubicazione](/dbzero/magazzino/views/vw_giacenza_ubicazione) mostra che cosa c'è
in ciascuna. Che l'ubicazione appartenga al magazzino della riga lo controlla la primitiva di
scrittura. Un asset non porta la propria ubicazione: dove si trova lo dice il registro.

Un'ubicazione nominata da movimenti, attese, righe di inventario o di rettifica, prelievi o
rientri, o che ha figlie, non si spegne.

---

### Chi può vedere e scrivere

Un'ubicazione appartiene all'emittente del suo magazzino (`rls_ubicazioni_ef_whitelist`, via
magazzino). Meccanismo comune: [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls).

---

### Codici errore

* `E_MAG_UBICAZIONE_PADRE_DI_ALTRO_MAGAZZINO` — il padre sta in un altro magazzino (campo
  `parent_id`);
* `E_MAG_UBICAZIONE_PADRE_CICLICO` — il padre scelto chiuderebbe un ciclo (campo `parent_id`);
* `E_MAG_UBICAZIONE_MAGAZZINO_IMMUTABILE` — si prova a cambiare `magazzino_id`.

---

### Test

* `db/pgtap/magazzino/test-ubicazioni-guard-parent-v1.sql` — il padre nello stesso
  magazzino, i cicli di ogni lunghezza, `magazzino_id` immutabile.

---

### Note di migrazione

* 2026-09-15 — `brief-db-magazzino-lotto-1-terreno-vuoto` (§4.10): il movimento passa a una
  sola ubicazione per riga; l'asset smette di portare la propria.
* 2026-09-21 — `brief-db-magazzino-anagrafiche-guard-ubicazioni-e-codici` (R-1): il guard sul padre e il
  lock di `magazzino_id`.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
