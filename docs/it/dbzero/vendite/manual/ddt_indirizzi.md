## 📘 Documentazione Concettuale – Tabella vendite.ddt_indirizzi

>👀 Vedi anche
>
>Approfondimento tabelle:
>
> •[vendite.ddt](/dbzero/vendite/tabelle/ddt)     
> •[config.tipi_indirizzi](/dbzero/config/tabelle/tipi_indirizzi)     
> •[anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi)      
> •[anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)      


---
### 🎯 Scopo Principale

vendite.ddt_indirizzi gestisce gli indirizzi associati alla testata DDT tramite snapshot JSON al momento dell’emissione (o conferma logistica). Per ogni DDT è ammesso al più un indirizzo per tipo (es. spedizione, fornitura, residenza), garantito dall’univocità (ddt_id, tipo_indirizzo_id).

Lo snapshot consente di cristallizzare dati variabili (via/numero, CAP, città, provincia, nazione, contatti, e-mail, note di resa, etc.) senza dipendere dalle future modifiche anagrafiche.

---
### 🧱 Modello Dati (estratto)
Campo	Tipo	Note
id	bigint	PK tecnica.
ddt_id	bigint	FK → vendite.ddt(id).
tipo_indirizzo_id	bigint	FK → config.tipi_indirizzi(id).
snapshot	jsonb	Indirizzo cristallizzato al momento del DDT (includere e-mail e recapiti). Default {}.
origine_indirizzo_id	bigint	FK soft → anagrafiche.indirizzi(id) da cui lo snapshot è stato generato. SET NULL su delete.
origine_soggetto_ruolo_id	bigint	FK → anagrafiche.soggetti_ruoli(id). SET NULL su delete.
data_insert, user_insert, data_update, user_update	audit	Convenzioni ZeroERP.

Vincoli

PRIMARY KEY (id)

UNIQUE (ddt_id, tipo_indirizzo_id)

FK ddt_id → vendite.ddt(id) (CASCADE on delete/update)

FK tipo_indirizzo_id → config.tipi_indirizzi(id) (NO ACTION on delete)

FK origine_indirizzo_id → anagrafiche.indirizzi(id) (SET NULL)

FK origine_soggetto_ruolo_id → anagrafiche.soggetti_ruoli(id) (SET NULL)

Indici

ix_ddt_indirizzo_ordine (ddt_id)

ix_ddt_indirizzi_origine_indirizzo (origine_indirizzo_id)

ix_ddt_indirizzi_origine_sog_ruolo (origine_soggetto_ruolo_id)

---

### 🧮 Regole & Trigger
Trigger	Timing	Evento	Azione
trg_ddt_indirizzi_a10_ins_upd_only_allowed_tipi	BEFORE	INSERT/UPDATE OF tipo_indirizzo_id	vendite.trgfn_tipi_indirizzi_only_allowed('DDT') → whitelist dei tipi ammessi per i DDT.

Comportamento atteso della funzione collegata:

Verifica che tipo_indirizzo_id sia compreso nel set “ammessi per DDT” (es.: spedizione, fornitura…).

In caso contrario registra su dbops.error_log e solleva errore applicativo.

---

**✅ Esempi d’uso**

A) Inserimento indirizzo di spedizione

INSERT INTO vendite.ddt_indirizzi (
  ddt_id, tipo_indirizzo_id, snapshot,
  origine_indirizzo_id, origine_soggetto_ruolo_id
) VALUES (
  :ddt_id, :tipo_spedizione_id,
  jsonb_build_object(
    'intestazione', 'ACME S.p.A.',
    'via', 'Via Roma, 10', 'cap','00100', 'citta','Roma', 'prov','RM', 'stato','IT',
    'email','magazzino@acme.it',
    'telefono','06-123456',
    'note','Consegna piano strada'
  ),
  :indirizzo_id, :soggetto_ruolo_id
);

B) Aggiornamento tipo indirizzo (controllo whitelist)

UPDATE vendite.ddt_indirizzi
   SET tipo_indirizzo_id = :tipo_fornitura_id
 WHERE id = :id;  -- Se il tipo non è consentito per i DDT → errore dal trigger

---

### 📘 Linee guida per lo snapshot

Suggerito un formato minimale comune (espandibile):

{
  "intestazione": "string",
  "via": "string",
  "cap": "string",
  "citta": "string",
  "prov": "string",
  "stato": "IT|...",
  "email": "string",
  "telefono": "string",
  "note": "string"
}

Per indirizzi internazionali aggiungere campi opzionali (es. line2, line3, county, state, iso3).

---

### 👓 Ruolo nel sistema

vendite.ddt_indirizzi è fondamentale per la logistica di consegna e per la stampa documentale: garantisce che il luogo/recapito di spedizione/fornitura stampato sul DDT sia quello effettivamente usato durante la spedizione, a prescindere da successive variazioni in anagrafica.

---
