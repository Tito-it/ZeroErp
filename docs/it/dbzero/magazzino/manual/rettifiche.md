## 📘 Documentazione Concettuale – Tabella `magazzino.rettifiche`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.rettifiche_righe](/dbzero/magazzino/tabelle/rettifiche_righe) — il dettaglio
> • [magazzino.magazzini](/dbzero/magazzino/tabelle/magazzini) — l'ancora del perimetro
> • [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — dove la rettifica finisce
>
Guide: brief `brief-db-magazzino-lotto-1-terreno-vuoto` (§4.7)

---
### 🎯 Scopo Principale

(rev 2026-09-15 — Lotto 1 del magazzino)

**Il documento di rettifica**: la correzione dichiarata di una giacenza, in un magazzino, a
una data, con uno stato (`DRAFT` → `CONFIRM` → `POSTED`, o `CANCEL`). Il dettaglio — quanto
in più o in meno, per articolo — sta nelle righe.

⭐ Dal 14-09 **la correzione a mano è una rettifica**: non esiste un movimento senza
operazione a monte, quindi chi deve sistemare una giacenza scrive qui, e le righe diventano
la sorgente dei movimenti (`RETTIFICA_RIGA`, causali `RETT_POS` / `RETT_NEG`).

### La sorgente, come sul registro

`sorgente_tipo_id` (una riga di [config.sorgenti](/dbzero/config/tabelle/sorgenti)) più
**esattamente una** chiave fra `sorgente_riga` e `sorgente_uid`, secondo quanto il catalogo
dichiara per quel tipo; senza tipo, nessuna chiave. Il guard tipizzato
(`script.trgfn_guard_sorgente_polimorfa_tipizzata`) verifica che il record esista. Qui la
sorgente è **facoltativa**: dice da quale documento l'operazione è nata, se ce n'è uno.

⚠️ Fino al 14-09 `sorgente_tipo_id` **non aveva la FK** verso il catalogo: poteva puntare a
un tipo inesistente. Ora c'è, insieme al guard.

### Il magazzino si sceglie alla nascita

**`magazzino_id` non si cambia** dopo la creazione, in nessuno stato (lock delle colonne,
`E_MAG_DOCUMENTO_MAGAZZINO_IMMUTABILE`, dal 22-09): il magazzino di una correzione è
**identità**, non un attributo. Le righe nominano le ubicazioni *di quel* magazzino e il
posting scrive il delta sulla giacenza *di quel* magazzino; spostando la testata le righe
resterebbero a puntare a posizioni che nel magazzino nuovo non esistono, e il database se
ne accorgerebbe solo al posting, con un errore che racconta un'altra storia
(`E_MAG_UBICAZIONE_DI_ALTRO_MAGAZZINO`). Se il magazzino è sbagliato la rettifica si
annulla e se ne apre una dove la merce sta davvero.

⚠️ La **`data`** invece resta modificabile, ed è una decisione esplicita (Q-2 del piano
BE/FE, confermata il 22-09): il database non congela la testata oltre il magazzino. Il
trigger del lock non lo scrive un changeSet — lo **genera l'automazione** dalla riga in
[dbops.automation_lock_columns](/dbzero/dbops/tabelle/automation_lock_columns).

### Chi può vedere e scrivere

Un operatore vede e scrive le rettifiche dei magazzini del **proprio emittente**
(`rls_rettifiche_ef_whitelist`, via magazzino); righe e note risalgono alla testata.
Meccanismo comune: [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls).

### Il motore (dal 18-09, Lotto 2)

[fn_posta_rettifica](/dbzero/magazzino/funzioni/fn_posta_rettifica) posta il delta **dato** di ogni
riga (`RETT_POS`/`RETT_NEG` dal segno), in una transazione; una rettifica negativa ignora i
blocchi (una promessa) ma non il fisico (`is_rettifica`, primo consumatore). La matrice degli
stati è la stessa degli inventari, con la porta `POSTED` aperta solo dall'operazione e il
`DELETE` solo in `DRAFT`
([trgfn_documento_interno_guard_transizione](/dbzero/magazzino/funzioni/trgfn_documento_interno_guard_transizione)).

---

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
