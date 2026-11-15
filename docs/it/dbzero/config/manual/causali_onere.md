## 📘 Documentazione Concettuale – Tabella `config.causali_onere`

> **Ultimo aggiornamento**: 13 novembre 2026
>
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
I consumatori leggono il `codice_interno`, che non si modifica dopo l'inserimento
(lock auto-provisionato). Una sola causale è nominata dal programma: `TRASPORTO`, che il controllo
di emissione del DDT (`script.fn_check_ddt_emittibile`) cerca per decidere se il trasporto è
dovuto. Il lock la protegge anche dal pannello.

### Dove nasce una causale

Dal **pannello delle tabelle di configurazione** (13-11-2026): la tabella è in
[config.tabelle_gestibili](/dbzero/config/tabelle/tabelle_gestibili) con `pannello = true`. Il
flusso di un onere nuovo è: si crea la causale dal pannello, poi l'articolo che la porta dal drawer
articolo, la cui tendina offre solo le causali libere
([catalogo.vw_causali_onere_assegnabili](/dbzero/catalogo/views/vw_causali_onere_assegnabili)).
Tendina e pannello sono lo stesso oggetto `('config', 'causali_onere')`, quindi chiedono lo stesso
permesso.

Il pannello non aggiunge controlli: `codice` in maiuscolo, `codice_interno` bloccato e il divieto di
disattivare una causale che un articolo o una riga di commessa usa sono trigger della tabella.

⚠️ Le causali del seed (`80_data/sql/config/causali_onere.csv`) restano del CSV: il caricamento è un
mirror, e quando il file cambia riscrive le sue righe per `id`. Una modifica fatta dal pannello su
una di quelle righe dura fino al caricamento successivo. Le causali create dal pannello non sono nel
file e il caricamento non le tocca, purché una riga aggiunta al CSV non ne riusi l'`id`.
