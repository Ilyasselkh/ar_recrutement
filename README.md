# AR - Demande de Recrutement


> Documentation compl?te du processus de demande de recrutement.


## Vue d?ensemble

Le module couvre un processus RH ?tendu : expression du besoin, validations hi?rarchiques, suivi RH, suivi des candidats, annonces, dossiers candidat, p?riode d?essai, offre, refus, rapports et parcours d?int?gration. Il sert ? structurer le cycle complet de recrutement et ? garder les validations et documents au m?me endroit.

## Utilisateurs concern?s

- Demandeur/manager : exprime le besoin et justifie le recrutement.
- RH : contr?le la demande, suit les candidats et pr?pare les documents.
- MD/direction g?n?rale : valide les recrutements selon le niveau requis.
- Responsables d?entretien : compl?tent les ?valuations.
- Administrateur : configure droits, templates et rapports.

## Workflow m?tier

1. Expression du besoin
2. Soumission
3. Validation N+1
4. Validation RH
5. Validation MD
6. Direction g?n?rale si n?cessaire
7. Suivi candidats
8. Offre accept?e ou refus?e
9. P?riode d?essai/int?gration
10. Archivage

## Fonctionnement op?rationnel

- Cr?er une demande avec les informations poste et besoin.
- Soumettre au manager.
- Renseigner ou suivre les candidats dans les lignes d?di?es.
- G?n?rer/t?l?charger les fiches et rapports.
- Valider les ?tapes RH/MD/direction selon le cas.
- G?n?rer et suivre le parcours d?int?gration.
- Archiver une demande termin?e ou refus?e.

## Configuration recommand?e

- V?rifier les employ?s, managers et utilisateurs RH.
- Configurer les groupes et r?gles d?acc?s.
- Contr?ler les templates d?e-mail.
- V?rifier les rapports candidat, fiche annonce et rapport g?n?ral.
- Adapter les donn?es de s?quence si n?cessaire.

## D?pendances Odoo

- `base`
- `web`
- `mail`
- `hr`

## Mod?les techniques

- `ar.demande.de.recrutement` : Demande de Recrutement (`models/ar_demande_recrutement.py`)
- `ar.demande.recrutement.stagiaire.line` : Ligne Sujet / Assurance Stagiaire (`models/ar_demande_recrutement.py`)
- `ar.demande.recrutement.candidate` : Candidats - Demande Recrutement (`models/ar_demande_recrutement.py`)
- `ar.demande.recrutement.annonce` : Lignes Annonce - Demande de Recrutement (`models/ar_demande_recrutement.py`)
- `ar.demande.recrutement.dossier.candidat.line` : Dossier du Candidat - Demande de Recrutement (`models/ar_demande_recrutement.py`)
- `ar.demande.recrutement.integration` : Parcours d (`models/ar_demande_recrutement.py`)
- `ar_demande_recrutement_integration` (`models/ar_demande_recrutement.py`)
- `demande_id` (`models/ar_demande_recrutement.py`)
- `validation_direction_generale` (`models/ar_demande_recrutement.py`)
- `validation_demande_id` (`models/ar_demande_recrutement.py`)
- `ar.demande.recrutement.integration.line` : Ligne parcours d (`models/ar_demande_recrutement.py`)
- `ar.recrutement.documentation` : Documentation - Recrutement (`models/recrutement_documentation.py`)
- `ar.demande.recrutement.action.wizard` : Confirmation action demande recrutement (`wizard/recrutement_action_wizard.py`)

## ?tats d?tect?s dans le code

- `models/ar_demande_recrutement.py` : `demandeur` (EXPRESSION DE BESOIN), `n1` (VALIDATION N+1), `rh` (VALIDATION RH), `md` (VALIDATION MD), `annonce` (ANNONCE), `cv_tech` (CVthèques), `selection_candidats` (Sélection des Candidats), `entretien` (Entretien), `candidat_retenu` (Entretien Technique), `validation_rh` (Entretien RH), `deliberation` (Délibération), `offre_candidat` (Offre du Candidat), `offre_en_cours` (Offre en Cours), `en_cours_stage` (En cours de stage), `matricule_a_renseigner` (Matricule à Renseigner), `dossier_candidat` (Dossier du Candidat), `visite_medicale` (Visite médicale), `envoie_annonce` (Announcement), `feedback_rh` (Feedback RH), `feedback_md` (Feedback MD)

## Actions serveur principales

- `action_print_general_report` (`models/ar_demande_recrutement.py`)
- `action_envoyer_archive_stage` (`models/ar_demande_recrutement.py`)
- `action_archiver_stage` (`models/ar_demande_recrutement.py`)
- `action_archiver_rupture` (`models/ar_demande_recrutement.py`)
- `action_send_announcement_mail` (`models/ar_demande_recrutement.py`)
- `action_open_modify_wizard` (`models/ar_demande_recrutement.py`)
- `action_open_validate_n1_wizard` (`models/ar_demande_recrutement.py`)
- `action_open_submit_wizard` (`models/ar_demande_recrutement.py`)
- `action_open_validate_rh_wizard` (`models/ar_demande_recrutement.py`)
- `action_open_validate_md_wizard` (`models/ar_demande_recrutement.py`)
- `action_open_validate_direction_generale_wizard` (`models/ar_demande_recrutement.py`)
- `action_open_validate_deliberation_finale_wizard` (`models/ar_demande_recrutement.py`)
- `action_open_validate_periode_essai_n1_wizard` (`models/ar_demande_recrutement.py`)
- `action_open_offer_accept_wizard` (`models/ar_demande_recrutement.py`)
- `action_open_offer_refuse_wizard` (`models/ar_demande_recrutement.py`)
- `action_open_refuse_wizard` (`models/ar_demande_recrutement.py`)
- `action_demander_modification` (`models/ar_demande_recrutement.py`)
- `action_refresh_integration_lines` (`models/ar_demande_recrutement.py`)
- `action_soumettre` (`models/ar_demande_recrutement.py`)
- `action_valider_n1` (`models/ar_demande_recrutement.py`)
- `action_valider_periode_essai_n1` (`models/ar_demande_recrutement.py`)
- `action_valider_rh` (`models/ar_demande_recrutement.py`)
- `action_offre_acceptee` (`models/ar_demande_recrutement.py`)
- `action_offre_refusee` (`models/ar_demande_recrutement.py`)
- `action_valider_md` (`models/ar_demande_recrutement.py`)
- `action_refuser` (`models/ar_demande_recrutement.py`)
- `action_valider_direction_generale` (`models/ar_demande_recrutement.py`)
- `action_valider_deliberation_finale` (`models/ar_demande_recrutement.py`)
- `action_open_epe` (`models/ar_demande_recrutement.py`)
- `action_download_epe` (`models/ar_demande_recrutement.py`)
- `action_open_fa` (`models/ar_demande_recrutement.py`)
- `action_open_rh_fa` (`models/ar_demande_recrutement.py`)
- `action_download_fa` (`models/ar_demande_recrutement.py`)
- `action_download_rh_fa` (`models/ar_demande_recrutement.py`)
- `action_save_candidate_popup` (`models/ar_demande_recrutement.py`)
- `action_download_integration` (`models/ar_demande_recrutement.py`)
- `action_open_integration` (`models/ar_demande_recrutement.py`)
- `action_open_epe` (`models/ar_demande_recrutement.py`)
- `action_confirm` (`wizard/recrutement_action_wizard.py`)
- `action_cancel` (`wizard/recrutement_action_wizard.py`)

## Fichiers charg?s par le manifest

- `data/sequence.xml`
- `data/mail_templates.xml`
- `data/report_araymond_layout.xml`
- `data/report_candidate_fa.xml`
- `data/ar_demande_recrutement_general_report.xml`
- `security/security.xml`
- `security/record_rules.xml`
- `security/ir.model.access.csv`
- `views/ar_demande_recrutement_views.xml`
- `views/ar_demande_recrutement_menu.xml`
- `views/recrutement_documentation_views.xml`

## S?curit? et droits

Le module s?appuie sur les fichiers suivants pour d?finir les groupes, r?gles d?enregistrement et droits d?acc?s :

- `security/ir.model.access.csv`
- `security/record_rules.xml`
- `security/security.xml`

## Assets et interface

- `static/src/js/recrutement_animations.js`
- `static/src/scss/recrutement_backend.scss`

## Bonnes pratiques d?utilisation

- V?rifier que chaque utilisateur Odoo est li? au bon employ? lorsque le module d?pend de `hr.employee`.
- Tester le workflow avec un dossier de test avant utilisation en production.
- Contr?ler les groupes de s?curit? apr?s installation afin que seuls les bons r?les voient les boutons de validation.
- Garder les templates e-mail et rapports align?s avec les proc?dures internes.
- Sauvegarder la base avant toute modification structurelle du module.

## Maintenance

- Les ?volutions fonctionnelles doivent ?tre ajout?es dans les mod?les Python, les vues XML et les r?gles de s?curit? correspondantes.
- Apr?s modification des vues, mettre ? jour le module depuis Odoo ou red?marrer le serveur selon le type de changement.
- Apr?s modification des assets, vider le cache navigateur et recompiler les assets si n?cessaire.
- Toute nouvelle ?tape de workflow doit ?tre accompagn?e des droits, boutons, notifications et filtres correspondants.
