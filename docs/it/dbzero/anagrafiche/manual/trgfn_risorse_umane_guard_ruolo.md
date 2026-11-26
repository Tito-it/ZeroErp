## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_risorse_umane_guard_ruolo`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane) — il rapporto di lavoro che il guard presidia
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo `RIS_UMANA` a cui il rapporto punta
>
> Approfondimento funzioni:
>
> * [script.fn_guard_soggetto_ruolo](/dbzero/script/funzioni/fn_guard_soggetto_ruolo) — il controllo del tipo di ruolo, a cui il guard delega
> * [anagrafiche.fn_crea_risorsa_umana](/dbzero/anagrafiche/funzioni/fn_crea_risorsa_umana) — la porta che scrive il rapporto
>
> Guide:
>
> * [Soggetti e ruoli anagrafici](/guide/soggetti-e-ruoli-anagrafici) — il soggetto, i ruoli e le loro specializzazioni
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — il rapporto di lavoro e la veste operatore

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_risorse_umane_guard_ruolo` impedisce che un rapporto di lavoro punti a un ruolo che non è una
risorsa umana (`RIS_UMANA`), o a un ruolo di un soggetto diverso da quello scritto sulla riga.

---

### Il ruolo giusto, del soggetto giusto

Il rapporto di lavoro è una specializzazione di ruolo, come il fornitore o il vettore: nomina con
`soggetto_ruolo_id` la riga di `anagrafiche.soggetti_ruoli` che dice «questo soggetto è una risorsa umana». La
prima metà del guard è quella di tutta la famiglia dei guard di ruolo: passa il ruolo e il codice `RIS_UMANA` a
`script.fn_guard_soggetto_ruolo`, che lo verifica, e riscrive la colonna col valore che riceve.

La seconda metà è sua. Il rapporto porta anche `soggetto_id`, una copia del soggetto del ruolo che serve ai
lettori senza passare dal ruolo. Il guard legge il soggetto del ruolo e rifiuta la riga se le due colonne non
coincidono: la copia non può divergere dall'originale.

---

### Quando scatta

Prima di ogni inserimento e di ogni modifica del rapporto, qualunque colonna cambi: anche una modifica che non
tocca il ruolo lo ricontrolla.

Non crea il ruolo: lo crea chi scrive il rapporto, prima.

---

### ⚠️ Che cosa oggi non copre

* **Il ruolo che cambia tipo.** Come per tutte le specializzazioni, il guard scatta sul rapporto e non su
  `soggetti_ruoli`: un ruolo `RIS_UMANA` portato a un altro tipo lascia il rapporto su un ruolo che non è più una
  risorsa umana, finché la riga non si riscrive e il guard la rifiuta.

---

### Codici errore

* `E_SOGGETTI_RUOLI` — il ruolo manca, non esiste o non è `RIS_UMANA`. Lo solleva `script.fn_guard_soggetto_ruolo`.
* `E_COD_INT_RUOLO` — il codice `RIS_UMANA` non è in `config.tipi_ruoli`: un difetto di configurazione. Lo solleva
  `script.fn_guard_soggetto_ruolo`.
* `E_RISORSA_UMANA_SOGGETTO_MISMATCH` — il soggetto del ruolo non è il soggetto scritto sulla riga. Il messaggio
  nomina il ruolo; il contesto porta i due soggetti e indica come campo `soggetto_ruolo_id`.

---

### Test

* `db/pgtap/dbops/test-punti-canale-campo-v1.sql` — legge il corpo, non lo esegue: il rifiuto
  `E_RISORSA_UMANA_SOGGETTO_MISMATCH` porta nel contesto il campo che l'interfaccia evidenzia.

Nessun test esegue i rifiuti del guard: né il ruolo di un altro tipo, né il soggetto che non coincide. Il caso
buono lo attraversa ogni test che crea una risorsa umana.

---

{% include-markdown "signature-core.md" %}
