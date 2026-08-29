## 📘 Documentazione Concettuale – Tabella `anagrafiche.soggetti_titoli_iva_ambiti`

> 👀 **Vedi anche**
>
> [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva) — il titolo padre ·
> [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) ·
> [vendite.articoli_gruppi](/dbzero/vendite/tabelle/articoli_gruppi) ·
> [vendite.articoli_tipologie](/dbzero/vendite/tabelle/articoli_tipologie) ·
> [anagrafiche.fn_check_titolo_iva_ambito](/dbzero/anagrafiche/funzioni/fn_check_titolo_iva_ambito)

---

### 👀 Chi legge questa tabella

⭐ [`vendite.fn_resolve_iva_riga`](/dbzero/vendite/funzioni/fn_resolve_iva_riga),
nel suo stadio B. L'ambito e` cio` che rende un titolo applicabile **a questa riga
e non a tutte**: senza, un titolo sarebbe il vecchio «codice IVA del cliente» con
un altro nome.

⚠️ E decide anche **chi vince** quando i titoli sono piu` d'uno: il risolutore
sceglie il **piu` specifico** — un titolo sul singolo articolo batte uno che vale
per tutto — e a parita` di specificita` **solleva**, invece di scegliere a caso.

---

### 🎯 Scopo Principale

(rev 2026-08-29 — tabella nata il 2026-08-29)

Dice **per cosa vale** un titolo IVA ristretto: una riga per ogni articolo o
categoria di merce coperta.

Serve per i titoli che non valgono su tutto. Un'agevolazione per disabilità copre
certi prodotti e non l'intero listino; una qualifica di cooperativa copre certe
prestazioni. Chi calcola l'IVA guarda **riga per riga** se l'articolo di quella riga
ricade qui dentro.

---

### 🔴 Perché questa tabella è la differenza fra un titolo e il difetto appena rimosso

Il rischio l'ha nominato Tid mentre si leggeva il disegno:

> *«alcune aliquote agevolate, esempio quelle per disabilità, si possono applicare
> solo su alcune categorie di prodotti; se alla seconda passata vince quella del
> soggetto il rischio è che si applichi a tutto»*

⭐ È il difetto giusto da temere. **Senza l'ambito, un titolo sarebbe
`anagrafiche.clienti.iva_id` — la colonna tolta il 2026-08-29 — spostata di un
piano**: un valore che vince su tutto perché nessuno gli ha detto dove fermarsi.

Un documento di dieci righe con un titolo ristretto a due articoli deve produrre
**due righe agevolate e otto ordinarie**. Queste righe sono ciò che lo rende
possibile.

---

### I tre livelli, e sono già tutti nel modello

| `livello` | Colonna valorizzata | Punta a |
| --- | --- | --- |
| `ARTICOLO` | `articolo_id` | `catalogo.articoli` |
| `GRUPPO_VOCE` | `gruppo_voce_id` | `vendite.articoli_gruppi` |
| `TIPO_VOCE` | `tipo_voce_id` | `vendite.articoli_tipologie` |

Sono esattamente le due classificazioni che `catalogo.articoli` porta già
(`gruppo_voce_id`, `tipo_voce_id`) più l'articolo stesso: **nessun livello è stato
inventato per l'occasione**.

⚠️ Le due classificazioni stanno nello schema `vendite`, non in `catalogo`: è la sede
che hanno da sempre, e le chiavi esterne di `catalogo.articoli` puntano lì.

⭐ Il livello è anche la **specificità** con cui si arbitra un titolo contro un
altro: **articolo > categoria di merce > tutto**, la stessa cascata degli indirizzi.

---

### ⚠️ Il livello è dichiarato, non dedotto da quale colonna è piena

Si potrebbe fare a meno della colonna `livello` e guardare quale delle tre chiavi è
valorizzata. Non si fa, e sono le due trappole gemelle del valore vuoto in una
chiave:

* una riga con **due** colonne piene sarebbe un'ambiguità che non vede nessuno;
* una riga con **zero** colonne piene sarebbe un ambito che non nomina niente.

`livello` obbligatorio più un controllo che lo lega alla sua colonna — e impone il
silenzio alle altre due — chiudono entrambi i casi. E chi legge non deve indovinare.

⚠️ Per la stessa ragione l'unicità è dichiarata `NULLS NOT DISTINCT`: con la regola
standard due righe **identiche** che portano valori vuoti nelle stesse colonne non
si accorgerebbero l'una dell'altra, e la stessa categoria si potrebbe dichiarare due
volte sullo stesso titolo.

---

### ⚠️ Non c'è una colonna `attivo`, ed è voluto

L'ambito è la **definizione** del titolo, non un'entità con un ciclo di vita suo: si
aggiunge o si toglie. Una riga di ambito «non attiva» vorrebbe dire un titolo che
vale per una cosa a metà, che non è un caso del dominio. A spegnere il titolo intero
c'è `soggetti_titoli_iva.attivo`.

---

### ⛔ Le righe seguono il titolo, e spariscono con lui

`ON DELETE CASCADE`, al contrario del registro dei movimenti. La differenza è di
natura: **un ambito è una clausola**, un movimento di plafond è un **fatto
contabile**. Una clausola senza il suo titolo non significa niente; un movimento sì.

---

### Il guard, e i due lati che deve coprire

`trgfn_soggetti_titoli_iva_ambiti_guard` rifiuta due cose:

1. una riga di ambito su un titolo che vale per **tutto** — la tabella direbbe due
   cose opposte, e chi calcola ne leggerebbe una sola;
2. **il pareggio**: due titoli dello stesso tipo, dello stesso cliente, verso lo
   stesso emittente, validi insieme, che coprono lo **stesso oggetto allo stesso
   livello**. Lì nessuno dei due è più specifico, e non c'è niente da scegliere.

⚠️ **Livelli diversi non sono un pareggio e non vanno bloccati**: un titolo
sull'articolo e uno sulla sua categoria convivono, e vince il primo. Un guard scritto
largo rifiuterebbe la configurazione più normale che esista.

⭐ E il guard è **doppio**: la stessa regola gira anche quando a cambiare è il
**titolo** invece delle sue righe — si allarga una data, si riattiva un titolo
spento. In quei casi questa tabella non viene toccata affatto, e un controllo scritto
solo qui non se ne accorgerebbe mai. La regola sta in **una** funzione pura che
entrambi i trigger chiamano.

Cantiere: `brief-db-be-iva-risolutore-e-regime-cliente.md`, `I7` / `D10` / `D12`.

---

{% include-markdown "signature-core.md" %}
