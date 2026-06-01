{
    "name": "AR - Demande de Recrutement",
    "version": "1.0.5",
    "summary": "Workflow complet de demande de recrutement avec validation N+1, RH et MD",
    "description": """Module de gestion des demandes de recrutement comprenant""",
    "author": "AR IT Department",
    "website": "",
    "category": "DEMANDE DE RECRUTEMENT",
    "license": "LGPL-3",
    "depends": [
        "base",
        "web",
        "mail",
        "hr",
    ],
    "data": [
        
        "data/sequence.xml",
        "data/mail_templates.xml",
        "data/report_araymond_layout.xml",
        "data/report_candidate_fa.xml",
        "data/ar_demande_recrutement_general_report.xml",

        
        "security/security.xml",
        "security/record_rules.xml",
        "security/ir.model.access.csv",

        
        "views/ar_demande_recrutement_views.xml",
        "views/ar_demande_recrutement_menu.xml",
        "views/recrutement_documentation_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "ar_recrutement/static/src/scss/recrutement_backend.scss",
            "ar_recrutement/static/src/js/recrutement_animations.js",
        ],
    },
    
    "installable": True,
    "application": True,
    "auto_install": False,
}
