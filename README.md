# AR - Demande de Recrutement

Module Odoo de gestion complète des demandes de recrutement, depuis l'expression du besoin jusqu'à la sélection, l'offre, l'intégration et l'archivage.

## Objectif

Ce module structure le processus de recrutement interne avec validations hiérarchiques, suivi RH, suivi des candidats, génération de rapports et parcours d'intégration.

## Dépendances

- `base`
- `web`
- `mail`
- `hr`

## Modèles principaux

- `ar.demande.de.recrutement` : demande de recrutement.
- `ar.demande.recrutement.candidate` : candidats rattachés à une demande.
- `ar.demande.recrutement.stagiaire.line` : sujets/assurances pour stagiaires.
- `ar.demande.recrutement.annonce` : lignes d'annonce.
- `ar.demande.recrutement.dossier.candidat.line` : dossier candidat.
- `ar.demande.recrutement.integration` et `ar.demande.recrutement.integration.line` : parcours d'intégration.
- `ar.recrutement.documentation` : documentation métier.
- `ar.demande.recrutement.action.wizard` : assistant de confirmation.

## Fonctionnement général

1. Le demandeur saisit le besoin de recrutement et les informations du poste.
2. La demande est soumise au manager N+1.
3. Les étapes RH, MD, direction générale ou délibération finale sont déclenchées selon le type de demande et les règles métier.
4. Les candidats sont suivis dans des lignes dédiées avec documents, évaluations et fiches associées.
5. Les offres peuvent être acceptées ou refusées.
6. Le parcours d'intégration est généré et suivi après validation.
7. Les demandes peuvent être archivées ou refusées avec motif.

## Actions clés

Le module contient des actions pour soumettre, valider N+1, valider RH, valider MD, valider direction générale, gérer la période d'essai, accepter/refuser une offre, imprimer les rapports et télécharger les documents candidat.

## Rapports et e-mails

Le module charge :

- des templates e-mail,
- des rapports candidat,
- un rapport général de recrutement,
- une mise en page dédiée.

## Sécurité

Les groupes, règles d'enregistrement et droits d'accès sont définis dans :

- `security/security.xml`
- `security/record_rules.xml`
- `security/ir.model.access.csv`

## Interface

Des vues formulaire, liste, documentation et menus dédiés sont inclus. Des assets backend ajoutent le style et les animations du workflow.

