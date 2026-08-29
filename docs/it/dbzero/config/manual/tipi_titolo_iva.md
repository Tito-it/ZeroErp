## 📘 Documentazione Concettuale – Tabella `config.tipi_titolo_iva`

> 👀 **Vedi anche**
>
> [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva) ·
> [config.iva_natura](/dbzero/config/tabelle/iva_natura) ·
> [config.tipi_reso](/dbzero/config/tabelle/tipi_reso) — lo stampo di questo vocabolario

---

### 🎯 Scopo Principale

(rev 2026-08-29 — tabella nata il 2026-08-29)

Il vocabolario delle **specie di titolo** per cui un cliente non paga l'IVA
ordinaria. Quattro voci a seed, tutte nominate dal cantiere:

| `codice_interno` | Cos'è | Vale per | Ha un tetto? | La prova |
| --- | --- | --- | --- | --- |
| `INTENTO` | dichiarazione d'intento dell'esportatore abituale | tutto | **sì**, il plafond | protocollo dell'Agenzia delle Entrate |
| `USO_INDUSTRIALE` | dichiarazione di uso industriale o agricolo (gas ed energia) | quella fornitura | no | dichiarazione resa al fornitore |
| `AGEVOLATA_104` | agevolazione per disabilità (L. 104/1992) | certe merci | no | certificazione o prescrizione |
| `COOPERATIVA` | cooperativa sociale o ente del terzo settore | certe prestazioni | no | iscrizione all'albo |

---

### ⭐ Perché un vocabolario, e non una tabella «dichiarazioni d'intento»

Il cantiere era partito chiedendo *«una tabella per la dichiarazione d'intento»*.
Guardando i casi uno accanto all'altro si è visto che **non è un caso unico: è il
primo di una famiglia**, e tutti e quattro rispondono allo stesso schema —

> *chi* × *per cosa vale* × *da quando a quando* × *con quale prova* → **quale
> codice IVA prende il posto di quello ordinario**.

⛔ Nascere col nome `soggetti_intento` avrebbe scambiato il caso particolare per la
regola, e allargare dopo una tabella nata come caso unico è il modo in cui si
ottengono **due meccanismi per la stessa cosa**.

---

### ⚠️ `ha_plafond` è la sola colonna che porta informazione

Solo la dichiarazione d'intento ha un **contatore che si consuma**: ogni fattura ne
mangia un pezzo, ogni nota di credito ne restituisce uno. Gli altri tre
sostituiscono l'aliquota e basta.

⭐ Ne discende una cosa che è facile leggere al contrario: **il plafond non è la
colonna portante dei titoli** — è la proprietà di *un tipo*. La riga di titolo porta
il **valore** del tetto (quanto), il tipo dice **se** il tetto esiste.

⚠️ La colonna è `NOT NULL` **senza default**, apposta: chi conia un tipo nuovo deve
dire di quale delle due specie è. Con un default lo erediterebbe per distrazione, e
la specie sbagliata si vedrebbe solo su un plafond che non si consuma — o su un
tetto che nessuno ha messo.

---

### ⛔ Perché non c'è un flag «richiede il protocollo»

Tutti e quattro i titoli hanno una prova documentale, ma di natura diversa: solo
l'intento ha un **protocollo** dell'Agenzia delle Entrate, gli altri hanno una carta
di altro genere. La tentazione era una seconda colonna di flag.

Non si è messa: nessuna regola la leggerebbe, e **una colonna che nessuno legge è
esattamente il difetto che questo cantiere sta chiudendo** — un campo che promette
una cosa che non succede. Se un giorno servirà obbligare il protocollo su un tipo,
la colonna nasce allora, con il suo controllo.

---

### Regola d'oro

**Mono-lingua**: la `descrizione` è il label reso a video, come i vocabolari gemelli
(`tipi_reso`, `causali_onere`, `motivi_fermo`) — nessun `label_key`. **Nessun `IF`
hardcoded**: chi legge si aggancia al `codice_interno`, che è immutabile (il lock si
auto-provisiona dalla sola presenza della colonna).

Aggiungere un tipo = **una riga nel CSV** `80_data/sql/config/tipi_titolo_iva.csv`,
senza toccare il codice.

---

### 📌 Un titolo non è attivabile finché non ha un codice IVA da applicare

`anagrafiche.soggetti_titoli_iva.iva_id` è obbligatoria: un titolo che non dice cosa
applicare non è un titolo.

Per l'`INTENTO` il codice è nato con lo stesso cantiere — **`NI35`**, aliquota zero e
natura `N3.5` («non imponibili a seguito di dichiarazioni d'intento»), che fino al
2026-08-29 era **seminata e orfana**: nessun codice IVA la usava.

⚠️ Per gli altri tre **non si è coniato niente al buio**: si sceglie fra i codici già
a catalogo quando si registrerà il primo titolo di quella specie.

Cantiere: `brief-db-be-iva-risolutore-e-regime-cliente.md`, `I7` / `D10`.

---

{% include-markdown "signature-core.md" %}
