## 📘 Documentazione Concettuale – Tabella `magazzino.inventari_righe`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.inventari](/dbzero/magazzino/tabelle/inventari) — la testata
> * [magazzino.lotti](/dbzero/magazzino/tabelle/lotti) — il lotto contato
> * [magazzino.assets](/dbzero/magazzino/tabelle/assets) — il pezzo serializzato contato
> * [magazzino.ubicazioni](/dbzero/magazzino/tabelle/ubicazioni) — la posizione contata
>
> Approfondimento viste:
>
> * [dbops.vw_magazzino_movimenti_senza_costo](/dbzero/dbops/views/vw_magazzino_movimenti_senza_costo) — la spia delle entrate senza costo
>
> Approfondimento funzioni:
>
> * [magazzino.fn_posta_inventario](/dbzero/magazzino/funzioni/fn_posta_inventario) — l'operazione che trasforma le righe in movimenti
> * [magazzino.trgfn_documento_interno_righe_guard_testata](/dbzero/magazzino/funzioni/trgfn_documento_interno_righe_guard_testata) — le righe seguono lo stato della testata
>
> Guide:
>
> * [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls) — il meccanismo comune del perimetro

---

### 🎯 Scopo Principale

**Le righe di [magazzino.inventari](/dbzero/magazzino/tabelle/inventari)**: per ogni
articolo (ed eventualmente lotto, pezzo serializzato, ubicazione) quanto è stato contato
(`qta_contata`, mai negativa) e quanto il sistema si aspettava (`qta_sistema`). Una riga da
sola non ha contesto: data, magazzino e stato stanno nella testata.

Ogni riga è il punto preciso da cui nasce il movimento di allineamento che il conteggio
produce: il movimento cita come sorgente il documento (`INVENTARIO`, la testata) e, in
`sorgente_riga`, questa riga. Una riga citata dal registro non si può cancellare.

---

### Lotto e seriale sono chiavi

`lotto_id` ([magazzino.lotti](/dbzero/magazzino/tabelle/lotti)) e `asset_id`
([magazzino.assets](/dbzero/magazzino/tabelle/assets)) sono riferimenti, non testi liberi:
senza, l'operazione non avrebbe niente da passare alla primitiva del registro. Se l'articolo
li pretende (`requires_lotto`, `requires_serial`) è l'operazione a rifiutare una riga senza;
«il lotto è di questo articolo» lo controlla lei, non un CHECK.

Con un pezzo serializzato il conteggio è zero o uno: c'è o non c'è.

---

### Una posizione si conta una volta sola

Dentro un inventario non possono esistere due righe sulla stessa posizione, cioè con lo stesso
articolo, ubicazione, lotto e seriale (`uq_mag_inventari_righe_posizione`); anche un campo
vuoto conta come uguale a un altro campo vuoto. Due righe sulla stessa posizione posterebbero
due differenze contro la stessa giacenza.

---

### Che cosa scrive chi conta, che cosa scrive l'operazione

* `costo_unitario` (facoltativo, mai negativo): la **valorizzazione iniziale** che chi conta può
  conoscere. Il primo carico in assoluto non ha un costo, e senza questa colonna entrerebbe senza
  valore. Su un'entrata la primitiva usa il costo della riga se c'è, altrimenti la media
  corrente. Vuoto non è un errore: la media si diluisce, e la spia
  [dbops.vw_magazzino_movimenti_senza_costo](/dbzero/dbops/views/vw_magazzino_movimenti_senza_costo)
  lo mostra.
* `qta_sistema` la scrive il **posting dal piano**, prima di postare: è la fotografia contro cui
  il conteggio è stato posto, e resta.
* Le righe si scrivono con la testata in `DRAFT`; in `CONFIRM` scrive solo il posting; in
  `POSTED` e `CANCEL` sono congelate (`E_MAG_DOCUMENTO_RIGHE_CONGELATE`).

---

### Chi può vedere e scrivere

Le righe seguono la testata: `rls_inventari_righe_ef_whitelist` risale all'inventario, e
da lì al magazzino e al suo emittente. Meccanismo comune: [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls).

---

### Codici errore

* `E_MAG_DOCUMENTO_RIGHE_CONGELATE`: una riga scritta, cambiata o cancellata con la testata fuori
  da `DRAFT`, salvo l'operazione di posting in `CONFIRM`.

---

### Note di migrazione

* 2026-09-15 — la tabella entra nel primo lotto del magazzino
  (`brief-db-magazzino-lotto-1-terreno-vuoto`, §4.7); `lotto_id` e `asset_id` prendono il posto
  dei due testi liberi `lotto` e `seriale`.
* 2026-09-18 — arrivano `costo_unitario`, la scrittura di `qta_sistema` dal posting e l'unicità
  della posizione.
* 2026-11-08 — il movimento non cita più la riga come tipo a sé (`INVENTARIO_RIGA`, ritirato da
  `config.sorgenti`): cita il documento e la riga.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
