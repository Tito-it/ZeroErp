## 📘 Documentazione Concettuale – Tabella `vendite.resi`

> 👀 **Vedi anche**
>
> Tabelle:
> [vendite.resi_righe](/dbzero/vendite/tabelle/resi_righe)
> [vendite.ddt](/dbzero/vendite/tabelle/ddt) (sorgente)
> [config.stati_doc_reso](/dbzero/config/tabelle/stati_doc_reso)
> [vendite.resi_righe_rientri](/dbzero/vendite/tabelle/resi_righe_rientri) (la merce che rientra)
>
> Funzioni:
> [vendite.fn_conferma_reso](/dbzero/vendite/funzioni/fn_conferma_reso)
> [vendite.fn_annulla_reso](/dbzero/vendite/funzioni/fn_annulla_reso)

---

### 🎯 Scopo Principale

(rev 2026-07-13)

Testata del **documento reso di vendita**: entità autonoma che registra il rientro di merce da un
DDT consegnato. Il reso è un **ibrido** — le sue righe possono essere *a credito* (verso nota di
credito) o *per ri-consegna* (merce da rifare e ri-spedire). Brief: `brief-db-resi-vendita.md`.

### Regole chiave

- **Sorgente data-driven** (`sorgente_tipo_id` + `sorgente_uid`, `NOT NULL`): in questa slice
  l'unica sorgente è `DDT_VENDITA`, risolta per **`uid`** (`sorgente_uid = ddt.uid`). Predisposto
  per una futura sorgente `FATTURA` senza rework.
- **Solo da DDT CONSEGNATO** — guard `trgfn_resi_guard_ddt_consegnato` all'INSERT
  (`E_RESO_DDT_NON_CONSEGNATO`): «non si rende ciò che non è stato consegnato».
- **Denormalizzati ereditati** dal DDT sorgente via `trgfn_resi_normalize`
  (`billing_account_id`, `destinatario_soggetto_ruolo_id`, `utility_id`, `valuta_id`,
  `emittente_fiscale_id`). `emittente_fiscale_id` è `NOT NULL`.
- **Scope emittente**: RLS `rls_resi_ef_whitelist` + guard scrittura
  `script.trgfn_doc_guard_emittente_ba` (`z10`, dopo il normalize).
- **Macchina a stati** data-driven (`config.stati_doc_reso` + `transizioni_stati_reso`),
  enforcement `trgfn_resi_guard_transizione`. `DRAFT → CONFERMATO → (ANNULLATO)`.
- **Numero** assegnato alla **CONFERMA** (NULL in DRAFT) da `trgfn_resi_gen_numero` +
  immutabilità `trgfn_v_resi_protect_num`.
- Storico/audit/tx_id auto-provisioning `dbops`.

---

### La merce rientra in magazzino (dal 2026-09-29, Lotto 3-bis)

Col Lotto 3 la merce **esce** dal magazzino quando si emette la bolla. Il reso chiude il giro:
alla **conferma** la merce resa **rientra** nel registro di magazzino, e se il reso si annulla
riesce con una riga opposta. Brief: `brief-db-magazzino-lotto-3-bis-carico-da-reso`.

**In quale magazzino** — `magazzino_id`, sulla testata. Quando il reso nasce prende il magazzino
da cui era partita la bolla d'origine; in bozza lo si cambia. Chi riceve merce da controllare o
rotta può metterla in un magazzino a parte («resi da verificare»): **dove la metti dice in che
stato è**. Dev'essere un magazzino della stessa azienda del reso, e dopo la conferma non cambia
più (`E_RESO_MAGAZZINO_INCOERENTE`, `E_RESO_MAGAZZINO_IMMUTABILE`). È obbligatorio alla
conferma solo se il reso fa rientrare merce.

**Che cosa rientra** — i rientri, sotto le righe
([vendite.resi_righe_rientri](/dbzero/vendite/tabelle/resi_righe_rientri)). Il reso non sceglie
di nuovo lotto e seriale: li **ritrova** da ciò che era uscito con la bolla. Un reso da una bolla
che non aveva mosso merce (articoli non gestiti, causale che non muove merce) non fa rientrare
niente.

**Quando** — alla conferma: la conferma è la presa in carico della merce, alla data del reso.
Per questo la conferma e l'annullo sono due **operazioni del database**. Il permesso lo dice la riga
del passaggio nella matrice: *Conferma reso* (`conferma_reso`) per la conferma e per l'annullo di un
reso confermato; l'annullo di una bozza chiede solo il permesso sul reso (guida
[Il modello del documento di vendita](/guide/modello-documento-di-vendita) §6):

* [vendite.fn_conferma_reso](/dbzero/vendite/funzioni/fn_conferma_reso) — controlla la merce (il
  pulsante «Conferma» è spento col motivo quando manca qualcosa), crea da sé i rientri dove non
  c'è niente da scegliere, porta il reso a `CONFERMATO` e scrive i carichi, tutto insieme. Ogni
  carico ha il **costo dell'uscita d'origine**: la merce rientra al valore al quale era uscita;
* [vendite.fn_annulla_reso](/dbzero/vendite/funzioni/fn_annulla_reso) — su un reso confermato
  scrive gli storni dei carichi. Se la merce nel frattempo è già uscita di nuovo, l'annullo è
  rifiutato: il magazzino non va sotto zero per un annullo.

Nessun reso cambia stato con una modifica diretta: lo impedisce la porta comune
[script.trgfn_doc_stato_solo_dal_verbo](/dbzero/script/funzioni/trgfn_doc_stato_solo_dal_verbo). Se un
reso confermato restasse senza carico, lo segnala il presidio
[dbops.vw_resi_confermati_senza_carico](/dbzero/dbops/views/vw_resi_confermati_senza_carico).
