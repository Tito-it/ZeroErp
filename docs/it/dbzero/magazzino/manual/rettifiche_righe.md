## 📘 Documentazione Concettuale – Tabella `magazzino.rettifiche_righe`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.rettifiche](/dbzero/magazzino/tabelle/rettifiche) — la testata
> * [magazzino.lotti](/dbzero/magazzino/tabelle/lotti) — il lotto corretto
> * [magazzino.assets](/dbzero/magazzino/tabelle/assets) — il pezzo serializzato corretto
> * [magazzino.ubicazioni](/dbzero/magazzino/tabelle/ubicazioni) — la posizione corretta
>
> Approfondimento funzioni:
>
> * [magazzino.fn_posta_rettifica](/dbzero/magazzino/funzioni/fn_posta_rettifica) — l'operazione che trasforma le righe in movimenti
> * [magazzino.trgfn_documento_interno_righe_guard_testata](/dbzero/magazzino/funzioni/trgfn_documento_interno_righe_guard_testata) — le righe seguono lo stato della testata
>
> Guide:
>
> * [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls) — il meccanismo comune del perimetro

---

### 🎯 Scopo Principale

**Le righe di [magazzino.rettifiche](/dbzero/magazzino/tabelle/rettifiche)**: per ogni
articolo (ed eventualmente lotto, pezzo serializzato, ubicazione) di quanto la giacenza va
corretta (`qta_delta`, con segno, mai zero) e perché (`motivo`).

Ogni riga è il punto preciso da cui nasce un movimento di rettifica (causale `RETT_POS` o
`RETT_NEG` secondo il verso): il movimento cita come sorgente il documento (`RETTIFICA`, la
testata) e, in `sorgente_riga`, questa riga. Una riga citata dal registro non si può cancellare.

---

### Lotto e seriale sono chiavi

`lotto_id` ([magazzino.lotti](/dbzero/magazzino/tabelle/lotti)) e `asset_id`
([magazzino.assets](/dbzero/magazzino/tabelle/assets)) sono riferimenti, non testi liberi:
senza, l'operazione non avrebbe niente da passare alla primitiva del registro. Se l'articolo
li pretende (`requires_lotto`, `requires_serial`) è l'operazione a rifiutare una riga senza;
«il lotto è di questo articolo» lo controlla lei, non un CHECK.

Con un pezzo serializzato la correzione è di **un** pezzo, in più o in meno.

---

### Il costo, solo sulla merce ritrovata

`costo_unitario` (facoltativo, mai negativo) è il costo che chi compila una rettifica
**positiva** (merce ritrovata) può conoscere; senza, l'entrata si valorizza alla media
corrente. Su una rettifica negativa non conta: l'uscita va sempre alla media.

---

### Le righe seguono la testata

Le righe si scrivono con la testata in `DRAFT`; in `CONFIRM` scrive solo l'operazione di
posting; in `POSTED` e `CANCEL` sono congelate (`E_MAG_DOCUMENTO_RIGHE_CONGELATE`).

---

### Chi può vedere e scrivere

Le righe seguono la testata: `rls_rettifiche_righe_ef_whitelist` risale alla rettifica, e
da lì al magazzino e al suo emittente. Meccanismo comune: [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls).

---

### Chi scrive

L'applicazione legge questa tabella e non la scrive: ogni scrittura passa da un **verbo**, che controlla il livello dell'operatore e il perimetro prima di scrivere. Una riga nasce con [fn_aggiungi_riga_rettifica](/dbzero/magazzino/funzioni/fn_aggiungi_riga_rettifica), si modifica con [fn_modifica_riga_documento_interno](/dbzero/magazzino/funzioni/fn_modifica_riga_documento_interno) e si toglie con [fn_togli_riga_documento_interno](/dbzero/magazzino/funzioni/fn_togli_riga_documento_interno), solo con la testata in `DRAFT`.

---

### Codici errore

* `E_MAG_DOCUMENTO_RIGHE_CONGELATE`: una riga scritta, cambiata o cancellata con la testata fuori
  da `DRAFT`, salvo l'operazione di posting in `CONFIRM`.

---

### Note di migrazione

* 2026-09-15 — la tabella entra nel primo lotto del magazzino
  (`brief-db-magazzino-lotto-1-terreno-vuoto`, §4.7); `lotto_id` e `asset_id` prendono il posto
  dei due testi liberi `lotto` e `seriale`.
* 2026-09-18 — arriva `costo_unitario`, con il posting.
* 2026-11-08 — il movimento non cita più la riga come tipo a sé (`RETTIFICA_RIGA`, ritirato da
  `config.sorgenti`): cita il documento e la riga.
* 2026-11-23 — in sola lettura per l'applicazione: la scrivono i verbi (`brief-db-magazzino-tutte-le-scritture-dal-verbo`, Lotto 2).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
