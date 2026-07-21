## 📘 Documentazione Concettuale – Tabella `config.causali_onere`

> 👀 **Vedi anche**
>
> [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) ·
> [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita) ·
> [vendite.fn_aggiungi_onere_commessa](/dbzero/vendite/funzioni/fn_aggiungi_onere_commessa)

---

### 🎯 Scopo Principale

(rev 2026-07-21)

Vocabolario della **causale onere**: la classificazione *business* di una voce di valore
manuale caricata su una commessa dalla «porta oneri». Nomina il **perché** dell'importo
(`brief-db-immutabilita-quantita-e-porta-oneri` §4c).

Una riga di commessa con `tipo_movimento = 'ONERE'` porta **valore, non merce** (`quantita = 1`,
il prezzo È l'importo): da sola è semanticamente opaca. La causale la qualifica — trasferta,
penale, spese amministrative… — così che riconciliazione, reporting e dashboard leggano
l'intento invece di indovinarlo.

### Modello articolo↔causale (1:1)

La causale **non vive da sola** sulla riga di commessa: è collegata a un **articolo-onere**
(`catalogo.articoli.causale_onere_id`, legame **1:1**). Un articolo è un onere ⟺ ha una causale.
Conseguenza importante:

- l'**IVA vive sull'articolo** (la sua `iva_id`), non sulla causale → **ogni onere ha la propria
  aliquota** (es. spese/trasferte al 22%, penale fuori campo art.15);
- la madre `fn_aggiungi_onere_commessa` riceve l'articolo-onere e **deriva** la causale da esso,
  poi la *snapshotta* su `commesse_attivita.causale_onere_id` (reporting senza join + CHECK
  biconditional `tipo_movimento='ONERE' ⇔ causale valorizzata`).

### Regola d'oro

**Mono-lingua**: la `descrizione` è il label (resa a video via `LookupSelect`), come i
vocabolari gemelli (`tipi_reso`, `motivi_fermo`, `causali_trasporto`) — nessun `label_key`.
**Nessun `IF` hardcoded**: i consumatori leggono il codice. `codice_interno` immutabile (lock
auto-provisionato). Aggiungere una causale = una riga di seed CSV, senza toccare il codice.
